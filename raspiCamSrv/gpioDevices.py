from gpiozero import OutputDevice, PWMOutputDevice
import threading
from _thread import allocate_lock
import time
from datetime import datetime
import math
import subprocess
from subprocess import CalledProcessError
import logging
# Try to import rpi_hardware_pwm
try:
    from rpi_hardware_pwm import HardwarePWM
    useHardwarePwm = True
except ImportError:
    useHardwarePwm = False

logger = logging.getLogger(__name__)

class StepperMotor():
    """ This class implements a stepper motor
    
        Developped and tested with
        Stepper motor: 28BYJ-48
        Motor driver : ULN2003A
    """

    def __init__(self, \
            in1:int, \
            in2:int, \
            in3:int, \
            in4:int, \
            mode:int=0, \
            speed:float=1.0, \
            current_angle:float=0.0, \
            swing_from:float=-45.0, \
            swing_to:float=45.0, \
            swing_step:float=9.0, \
            swing_direction:int=1, \
            stride_angle:float=5.625, \
            gear_reduction:int=64
            ):
        """ Constructor for StepperMotor

        Args:
            in1 (int): GPIO Pin connected to IN1
            in2 (int): GPIO Pin connected to IN2
            in3 (int): GPIO Pin connected to IN3
            in4 (int): GPIO Pin connected to IN4
            mode (int, optional): 
                0: half-step mode
                1: full-step mode
                Defaults to 0.
            speed (float, optional):
                0.0 : lowest speed
                1.0 : highest speed
                Defaults to 1.0.
            current_angle (float, optional):
                current angle of the motor
                Defaults to 0.0.
            swing_from (float, optional):
                left limit of the swing (-360.0 to 0.0)
                Defaults to -45.0.
            swing_to (float, optional):
                right limit of the swing (0.0 to 360.0)
                Defaults to 45.0.
            swing_step (float, optional):
                step size of the swing (0.0 to 360.0)
                Defaults to 9.0.
            swing_direction (int, optional):
                1: clockwise
                -1: counter-clockwise
                Defaults to 1.
            stride_angle (float, optional)
                angle per step in half-step mode
                Defaults to 5.625.
            gear_reduction (int, optional)
                gear reduction ratio
                Defaults to 64.
        """
        # Constant waiting times for highest (1) and lowest (0) speed
        self._WAIT_HIGH_SPEED = 0.001
        self._WAIT_LOW_SPEED = 0.040

        # Set the pins
        self._in1 = OutputDevice(in1)
        self._in2 = OutputDevice(in2)
        self._in3 = OutputDevice(in3)
        self._in4 = OutputDevice(in4)
        self._mode = mode
        self._speed = speed
        self._stride_angle = stride_angle
        self._gear_reduction = gear_reduction
        self._wait = self._WAIT_HIGH_SPEED

        self._pins = [self._in1, self._in2, self._in3, self._in4]

        # Step sequence for half-step operation
        self._seq_half_step = [ \
            [1,0,0,0], 
            [1,1,0,0],
            [0,1,0,0],
            [0,1,1,0],
            [0,0,1,0],
            [0,0,1,1],
            [0,0,0,1],
            [1,0,0,1],
        ]
        # Step sequence for full-step operation
        self._seq_full_step = [ \
            [1,1,0,0], 
            [0,1,1,0],
            [0,0,1,1],
            [1,0,0,1]
        ]
        if self._mode == 0:
            self._seq = self._seq_half_step
        else:
            self._seq = self._seq_full_step
        self._seq_len = len(self._seq)

        # Set the waiting time tepending on the speed
        if self._speed < 0.0:
            self._speed = 0.0
        if self._speed > 1.0:
            self._speed = 1.0

        self._wait = self._WAIT_LOW_SPEED + self._speed * (self._WAIT_HIGH_SPEED - self._WAIT_LOW_SPEED)
        # For full-step mode, the wait time is doubled
        if self._mode == 1:
            self._wait = self._wait * 2

        # Set the current step
        self._current_step = 0

        # Set parameters for swinging
        self._current_angle = current_angle
        self._swing_from = swing_from
        self._swing_to = swing_to
        self._swing_step = swing_step
        self._swing_direction = swing_direction

        # Set parameters for swiping
        self.wipe_active = False
        self.wipeLock = allocate_lock()  # lock for wipe status
        self.wipeThread = None  # thread for wipe operation

    @property
    def in1(self) -> int:
        return self._in1

    @in1.setter
    def in1(self, value: int):
        self._in1 = value

    @property
    def in2(self) -> int:
        return self._in2

    @in2.setter
    def in2(self, value: int):
        self._in2 = value

    @property
    def in3(self) -> int:
        return self._in3

    @in3.setter
    def in3(self, value: int):
        self._in3 = value

    @property
    def in4(self) -> int:
        return self._in4

    @in4.setter
    def in4(self, value: int):
        self._in4 = value

    @property
    def mode(self) -> int:
        return self._mode

    @mode.setter
    def mode(self, value: int):
        self._mode = value
        if self._mode == 0:
            self._seq = self._seq_half_step
        else:
            self._seq = self._seq_full_step
        self._seq_len = len(self._seq)
        # Set the waiting time tepending on the speed
        self.speed = self.speed

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, value: float):
        self._speed = value

        if self._speed < 0.0:
            self._speed = 0.0
        if self._speed > 1.0:
            self._speed = 1.0

        self._wait = self._WAIT_LOW_SPEED + self._speed * (self._WAIT_HIGH_SPEED - self._WAIT_LOW_SPEED)
        # For full-step mode, the wait time is doubled
        if self._mode == 1:
            self._wait = self._wait * 2

    @property
    def stride_angle(self) -> float:
        return self._stride_angle

    @property
    def gear_reduction(self) -> float:
        return self._gear_reduction

    @property
    def current_angle(self) -> float:
        return self._current_angle

    @current_angle.setter
    def current_angle(self, value: float):
        self._current_angle = value

    @property
    def value(self) -> float:
        return self._current_angle

    @value.setter
    def value(self, value: float):
        self._current_angle = value

    @property
    def swing_from(self) -> float:
        return self._swing_from

    @swing_from.setter
    def swing_from(self, value: float):
        self._swing_from = value

    @property
    def swing_to(self) -> float:
        return self._swing_to

    @swing_to.setter
    def swing_to(self, value: float):
        self._swing_to = value

    @property
    def swing_step(self) -> float:
        return self._swing_step

    @swing_step.setter
    def swing_step(self, value: float):
        self._swing_step = value

    @property
    def swing_direction(self) -> float:
        return self._swing_direction

    @swing_direction.setter
    def swing_direction(self, value: float):
        self._swing_direction = value

    def _motor_step(self, direction:int):
        """ Do one motor step in the current direction
        
        Args:
            direction (int):
                 1: forward
                -1: backward
        """
        # Move
        for pin in range(0, 4):
            if self._seq[self._current_step][pin] != 0:
                self._pins[pin].on()
            else:
                self._pins[pin].off()

        # Proceed
        self._current_step += direction
        if self._current_step >= self._seq_len:
            self._current_step = 0
        if self._current_step < 0:
            self._current_step = self._seq_len - 1

        # Wait
        time.sleep(self._wait)

    def _step(self, direction:int):
        """ Do one step in the current direction
        
        Args:
            direction (int):
                 1: forward
                -1: backward
        """
        for motor_step in range(0, self._gear_reduction):
            self._motor_step(direction)
        # Update the current angle
        if self._mode == 0:
            self._current_angle += direction * self._stride_angle
        else:
            self._current_angle += direction * self._stride_angle * 2
        if self._current_angle > 360.0:
            self._current_angle -= 360.0
        if self._current_angle < -360.0:
            self._current_angle += 360.0

    def step(self, steps:int):
        """ step forward or backward by a given number of steps

        Args:
            steps (int): number of steps to step forward (positive) or backward (negative)
        """
        nrSteps = abs(steps)
        if steps < 0:
            direction = -1
        else:
            direction = 1
        for step in range(0, nrSteps):
            self._step(direction)

    def step_forward(self, steps:int):
        """ step forward by a given number of steps

        Args:
            steps (int): number of steps to step forward
        """
        for step in range(0, steps):
            self._step(1)

    def step_backward(self, steps:int):
        """ step forward by a given number of steps

        Args:
            steps (int): number of steps to step forward
        """
        for step in range(0, steps):
            self._step(-1)

    def rotate(self, angle:float):
        """ Rotate right by the given angle

        Args:
            angle (float): angle to rotate. Positive angle is clockwise, negative angle is counter-clockwise
        """
        abs_angle = abs(angle)
        dir = 1
        if angle < 0:
            dir = -1
        motor_steps = round(self.gear_reduction * abs_angle / self._stride_angle)
        if self.mode == 1:
            motor_steps = round(motor_steps / 2)

        for motor_step in range(0, motor_steps):
            self._motor_step(dir)

        self._current_angle += angle

    def rotate_right(self, angle:float):
        """ Rotate right by the given angle

        Args:
            angle (float): angle to rotate
        """
        self.rotate(angle)

    def rotate_left(self, angle:float):
        """ Rotate left by the given angle

        Args:
            angle (float): angle to rotate
        """
        self.rotate(-angle)

    def rotate_to(self, target:float):
        """ Rotate to a given angle
        Args:
            angle (float): angle to rotate to
        """
        angle = target - self._current_angle
        self.rotate(angle)

    def swing(self):
        """ Swing the motor back and forth between the given angles
        """
        angle_rest = 0.0
        angle_step = self._swing_direction * self._swing_step
        angle_new = self._current_angle + angle_step
        if angle_new > self._swing_to:
            angle_rest = angle_new - self._swing_to
            angle_step = self._swing_to - self._current_angle
        elif angle_new < self._swing_from:
            angle_rest = angle_new - self._swing_from
            angle_step = self._swing_from - self._current_angle
        self.rotate(angle_step)
        if angle_rest != 0.0:
            self._swing_direction = -self._swing_direction
            angle_step = -angle_rest
            self.rotate(angle_step)

    def wipe(self, angle_from:float=-45, angle_to:float=45, speed:float=1.0, count:int=1):
        """Start swiping in a separate thread
        Args:
            angle_from (float): left limit of the wipe
            angle_to (float): right limit of the wipe
            duration (float): duration of the wipe in seconds
            count (int): number of wipes
        """
        if self.wipeThread is not None and self.wipeThread.is_alive():
            return
        self.wipeThread = threading.Thread(target=self._do_wipe, args=(angle_from, angle_to, speed, count))
        self.wipeThread.start()

    def _do_wipe(self, angle_from, angle_to, speed, count):
        """ Wipe the motor back and forth between the given angles
        Args:
            angle_from (float): left limit of the wipe
            angle_to (float): right limit of the wipe
            duration (float): duration of the wipe in seconds
            count (int): number of wipes
        """
        self.wipe_active = True
        current_angle = self._current_angle
        current_speed = self._speed
        self.speed = speed
        self.rotate_to(angle_from)
        i = count
        if i == 0:
            i = 1
        while i > 0:
            self.rotate_to(angle_to)
            with self.wipeLock:
                if self.wipe_active == False:
                    i = 0
            if i > 0:
                self.rotate_to(angle_from)
                if count > 0:
                    i -= 1
                with self.wipeLock:
                    if self.wipe_active == False:
                        i = 0
        self.speed = current_speed
        self.rotate_to(current_angle)

        self.wipe_active = False
        self.wipeThread = None

    def stop(self):
        """ Stop any activity
        
        """
        with self.wipeLock:
            self.wipe_active = False

        while self.wipeThread is not None and self.wipeThread.is_alive():
            time.sleep(0.1)

    def close(self):
        """ Close gpiozero resources associated with pins
        
        """
        self.stop()
        for pin in range(0, 4):
            self._pins[pin].close()            

class ServoPWM():
    """ This class implements a servo motor using PWM signal
    
        Developped and tested with
        Servo motor: KY66

        Development of this class was motivated by the fact that software-based PWM,
        provided by the default RPi.GPIO pin factory in gpiozero results in significant jitter for servo motors.
        The alternative pigpio pin factory does support hardware PWM, but it is currently not compatible
        with the latest Debian release (Trixie) for Raspberry Pi. 
        Therefore, this class implements the control of the servo motor using the rpi-hardware-pwm library, 
        which provides access to the hardware PWM channels of the Raspberry Pi.
        (https://github.com/Pioreactor/rpi_hardware_pwm)
    """
    def __init__(self, 
            pin:int,
            min_angle:float=-90.0,
            max_angle:float= 90.0,
            min_pulse_width_us:int=500, 
            max_pulse_width_us:int=2500,
            frame_width_us:int=20000,
            speed:float=2.8,
            idle_off:bool=False,
            calibration:float=0.0
            ):
        """ Constructor for ServoPWM

        Args:
            pin (int): GPIO Pin connected to the servo signal line
            min_angle (float, optional): minimum angle of the servo. Defaults to -90.0.
            max_angle (float, optional): maximum angle of the servo. Defaults to 90.0.
            min_pulse_width_us (int, optional): minimum pulse width corresponding to 0 degree in microseconds. Defaults to 500.
            max_pulse_width_us (int, optional): maximum pulse width corresponding to 180 degree in microseconds. Defaults to 2500.
            frame_width_us (int, optional): duration of one PWM frame in microseconds. Defaults to 20000.
            speed (float, optional): speed of the servo [sec/360°]. Defaults to 0.72.
            idle_off (bool, optional): whether to turn off the signal when idle. Defaults to True.
            calibration (float, optional): calibration angle of the servo. Defaults to 0.0.
        """
        logger.debug("ServoPWM.__init__: Initializing on pin %d with calibration=%s, min_angle=%s, max_angle=%s, min_pulse_width_us=%s, max_pulse_width_us=%s, frame_width_us=%s, speed=%s, idle_off=%s", pin, calibration, min_angle, max_angle, min_pulse_width_us, max_pulse_width_us, frame_width_us, speed, idle_off)
        if useHardwarePwm == False:
            raise ImportError("rpi_hardware_pwm library is not available. Please run: pip install rpi_hardware_pwm")

        self._pin = pin
        match pin:
            case 12:
                self._pwm_channel = 0
            case 13:
                self._pwm_channel = 1
            case 18:
                self._pwm_channel = 2
            case 19:
                self._pwm_channel = 3
            case _:
                raise ValueError(f"Invalid pin {pin}. Valid pins are 12, 13, 18, 19.")
        if not self.is_pin_ok(pin):
            raise ValueError(f"PWM is not routed to pin {pin}. Please check dtoverlay configuration and verify with 'pinctrl get {pin}' command.")
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._min_pulse_width_us = min_pulse_width_us
        self._max_pulse_width_us = max_pulse_width_us
        self._frame_width_us = frame_width_us
        self._current_angle = 0.0
        self._current_duty_cycle = 0.0
        self._frequency = int(1000000 / self._frame_width_us)
        self._speed = speed
        self._idle_off = idle_off
        self._calib_angle = calibration
        self._pwm = HardwarePWM(pwm_channel=self._pwm_channel, hz=self._frequency)
        self._pwm.start(0)
        logger.debug("ServoPWM.__init__: Initialization complete. Current duty cycle: %s", self._current_duty_cycle)

    def is_pin_ok(self, pin:int) -> bool:
        """ Check if the given pin is valid for hardware PWM

        Args:
            pin (int): GPIO pin number to check

        Returns:
            bool: True if the pin is valid for hardware PWM, False otherwise
        """
        try:
            result = subprocess.run(
                    ["pinctrl", "get", f"{pin}"],
                    capture_output=True, text=True
                ).stdout.strip()
            if result.find("PWM") >= 0:
                return True
            else:
                return False
        except CalledProcessError as e:
            logger.error("Error checking pin %d: %s", pin, e)
            return False

    @property
    def current_angle(self) -> float:
        return self._current_angle

    @current_angle.setter
    def current_angle(self, value: float):
        """ Set the new current angle and rotate servo to the given value

        Given limits are regarded

        Args:
            value (float): target angle to rotate to relative to calibration zero
        """
        logger.debug("ServoPWM.current_angle: Setting current_angle to %s. Actually: %s", value, self._current_angle)
        value = value + self._calib_angle
        logger.debug("ServoPWM.current_angle: calibration correction %s", value)
        if value < self._min_angle:
            value = self._min_angle
        if value > self._max_angle:
            value = self._max_angle
        logger.debug("ServoPWM.current_angle: Limited to min/max %s", value)
        diff = abs(value - self._calib_angle - self._current_angle)
        logger.debug("ServoPWM.current_angle: Difference to current angle %s", diff)
        self._current_angle = value - self._calib_angle
        logger.debug("ServoPWM.current_angle: New current angle %s", self._current_angle)
        self._current_duty_cycle = self._angle_to_duty_cycle(value)
        logger.debug("ServoPWM.current_angle: New current duty cycle %s", self._current_duty_cycle)
        self._pwm.change_duty_cycle(self._current_duty_cycle)
        logger.debug("ServoPWM.current_angle: New duty cycle set: %s", self._current_duty_cycle)
        if self._idle_off:
            duration = diff * self._speed / 360.0 
            if duration < 0.1:
                duration = 0.1
            logger.debug("ServoPWM.current_angle: Waiting for %s sec", duration)
            time.sleep(duration)
            self._pwm.change_duty_cycle(0)
        logger.debug("ServoPWM.current_angle: Done")

    @property
    def value(self) -> float:
        return self._current_angle

    @value.setter
    def value(self, value: float):
        self.current_angle = value

    def _angle_to_duty_cycle(self, angle:float) -> float:
        """ Convert angle to duty cycle

        Args:
            angle (float): angle to convert

        Returns:
            float: duty cycle corresponding to the given angle
        """
        pulse_width_us = self._min_pulse_width_us + (angle - self._min_angle) * (self._max_pulse_width_us - self._min_pulse_width_us) / (self._max_angle - self._min_angle)
        duty_cycle = 100 * pulse_width_us / self._frame_width_us
        return duty_cycle

    def _duty_cycle_to_angle(self, duty_cycle:float) -> float:
        """ Convert duty cycle to angle

        Args:
            duty_cycle (float): duty cycle to convert

        Returns:
            float: angle corresponding to the given duty cycle
        """
        pulse_width_us = duty_cycle * self._frame_width_us
        angle = self._min_angle + (pulse_width_us - self._min_pulse_width_us) * (self._max_angle - self._min_angle) / (self._max_pulse_width_us - self._min_pulse_width_us)
        if angle < self._min_angle:
            angle = self._min_angle
        if angle > self._max_angle:
            angle = self._max_angle
        return angle

    def min(self):
        """ Rotate the servo to the minimum angle
        """
        self.current_angle = self._min_angle - self._calib_angle

    def max(self):
        """ Rotate the servo to the maximum angle
        """
        self.current_angle = self._max_angle - self._calib_angle

    def mid(self):
        """ Rotate the servo to the middle angle
        """
        self.current_angle = (self._min_angle + self._max_angle) / 2.0 - self._calib_angle

    def rotate_to(self, angle:float):
        """ Rotate the servo to the given angle

        Args:
            angle (float): angle to rotate to
        """
        self.current_angle = angle

    def rotate_by(self, angle:float):
        """ Rotate the servo by the given angle

        Args:
            angle (float): angle to rotate by
        """
        self.current_angle = self.current_angle + angle

    def rotate_left(self, angle:float):
        """ Rotate the servo left by the given angle

        Args:
            angle (float): angle to rotate left by
        """
        self.rotate_by(-angle)

    def rotate_right(self, angle:float):
        """ Rotate the servo right by the given angle

        Args:
            angle (float): angle to rotate right by
        """
        self.rotate_by(angle)

    def stop(self):
        """ Stop any activity
        
        """
        self._pwm.stop()

    def close(self):
        """ Stop any activity
        
        """
        self._pwm.stop()

if __name__ == "__main__":
    testClass="ServoPWM"
    if testClass == "StepperMotor":
        test = 6
        print("==== Test StepperMotor ======")
        sm = StepperMotor(10, 9, 11, 0, 0, 1)
        #    sm = StepperMotor(14, 15, 18, 23, 0, 1)
        if test == 3:
            print(f"==== Test Calibration ====")
            print (f"==== 1. current_angle:{sm.current_angle}")
            sm.step(8)
            print (f"==== 2. step(8) ====")
            time.sleep(2)
            print (f"==== 3. current_angle:{sm.current_angle}")
            sm.value = 0.0
            print (f"==== 4. value=0.0 ====")
            sm.rotate_to(-45.0)
            print (f"==== 5. rotate_to(-90.0) ====")
            print (f"==== 6. current_angle:{sm.current_angle}")
        if test == 2:
            print(f"==== Test swinging ====")
            for i in range(0, 40):
                print (f"==== Step {i + 1} Start {sm.current_angle} ====")
                sm.swing()
                print (f"==== Step {i + 1} End   {sm.current_angle} ====")
                print(" ")
        if test == 3:
            print(f"==== Test mode & speed ====")
            for mode in range(0, 2):
                sm.mode = mode
                for ispeed in range(1, -1, -1):
                    speed = float(ispeed)
                    sm.speed = speed
                    print(f"==== mode={sm.mode} == speed={sm.speed } ====")
                    print(f"==== step_forward(64) =======")
                    sm.step_forward(64)
                    time.sleep(2)
                    print(f"==== step_backward(64)")
                    sm.step_backward(64) 
                    time.sleep(2)
                    print(f"==== step(64)")
                    sm.step(64) 
                    time.sleep(2)
                    print(f"==== step(-64)")
                    sm.step(-64) 
                    time.sleep(2)
                    print(f"==== rotate_right(90) =======")
                    sm.rotate_right(90) 
                    time.sleep(2)
                    print(f"==== rotate_left(90) =======")
                    sm.rotate_left(90) 
                    time.sleep(2)
                    print(f"==== rotate(360) =======")
                    sm.rotate(360) 
                    time.sleep(2)
                    print(f"==== rotate(-360) =======")
                    sm.rotate(-360) 
                    time.sleep(2)
        if test == 4:
            sm.value = 0.0
            sm.rotate_to(0)
            sm.mode = 0
            sm.speed = 1.0
            for a in range(0, -91, -15):
                sm.rotate_to(a)
                time.sleep(0.5)
            for a in range(-80, 91, 15):
                sm.rotate_to(a)
                time.sleep(0.5)
            sm.rotate_to(0)
            
        if test == 5:
            print(f"==== Test wipe ====")
            sm.value = 0.0
            sm.rotate_to(0)
            sm.mode = 0
            sm.speed = 0.0
            sm.wipe(angle_from=-45, angle_to=45, speed=0, count=3)
            time.sleep(5)
            sm.stop()
            
        if test == 5:
            print(f"==== Measuring  Angular Velocity ====")
            sm.value = 0.0
            sm.rotate_to(0)
            print("")
            print(f"==== Half-Step Mode ====")
            sm.mode = 0
            print(f"==== Slow (speed=0) ====")
            sm.speed = 0.0
            startTime = datetime.now()
            sm.rotate_to(360)
            endTime = datetime.now()
            duration = (endTime - startTime).total_seconds()
            print(f"==== Duration: {duration} seconds ====")
            print(f"==== Angular Velocity: {360 / duration} degrees/second ====")
            print(f"==== Fast (speed=1) ====")
            sm.speed = 1.0
            startTime = datetime.now()
            sm.rotate_to(0)
            endTime = datetime.now()
            duration = (endTime - startTime).total_seconds()
            print(f"==== Duration: {duration} seconds ====")
            print(f"==== Angular Velocity: {360 / duration} degrees/second ====")
            print("")
            print(f"==== Full-Step Mode ====")
            sm.mode = 1
            print(f"==== Slow (speed=0) ====")
            sm.speed = 0.0
            startTime = datetime.now()
            sm.rotate_to(360)
            endTime = datetime.now()
            duration = (endTime - startTime).total_seconds()
            print(f"==== Duration: {duration} seconds ====")
            print(f"==== Angular Velocity: {360 / duration} degrees/second ====")
            print(f"==== Fast (speed=1) ====")
            sm.speed = 1.0
            startTime = datetime.now()
            sm.rotate_to(0)
            endTime = datetime.now()
            duration = (endTime - startTime).total_seconds()
            print(f"==== Duration: {duration} seconds ====")
            print(f"==== Angular Velocity: {360 / duration} degrees/second ====")
        print(f"==== close ====")
        sm.close()
        print(f"==== Test completed ====")

    if testClass == "ServoPWM":
        print("==== Test ServoPWM ======")
        servo = ServoPWM(pin=12, idle_off=True)
        print(f"==== Rotate to Min ====")
        servo.min()
        time.sleep(2)
        print(f"==== Rotate to Max ====")
        servo.max()
        time.sleep(2)
        print(f"==== Rotate to Mid ====")
        servo.mid()
        time.sleep(2)

        for angle in range(-90, 91, 30):
            print(f"==== Rotate to {angle} ====")
            servo.rotate_to(angle)
            time.sleep(2)
        for angle in range(60, -91, -30):
            print(f"==== Rotate to {angle} ====")
            servo.rotate_to(angle)
            time.sleep(1)
        print(f"==== Rotate by 45 ====")
        servo.rotate_by(45)
        time.sleep(2)
        print(f"==== Rotate by 45 ====")
        servo.rotate_by(45)
        time.sleep(2)
        print(f"==== Rotate left by 90 ====")
        servo.rotate_left(90)
        time.sleep(2)
        print(f"==== Rotate right by 90 ====")
        servo.rotate_right(90)
        time.sleep(2)

        print(f"==== stop ====")
        servo.stop()
        print(f"==== Test completed ====")
