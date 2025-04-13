from gpiozero import OutputDevice
import time
import math

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
        self._WAIT_LOW_SPEED = 0.004
        
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
        
    def close(self):
        """ Close gpiozero resources associated with pins
        
        """
        for pin in range(0, 4):
            self._pins[pin].close()
        
if __name__ == "__main__":
    test = 3
    print("==== Test StepperMotor ======")
    sm = StepperMotor(10, 9, 11, 0, 0, 1)
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
    if test == 1:
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
    print(f"==== close ====")
    sm.close()
    print(f"==== Test completed ====")
