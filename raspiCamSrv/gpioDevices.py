from gpiozero import OutputDevice
import time
import math

class StepperMotor():
    """ This class implements a stepper motor
    
        Developped and tested with
        Stepper motor: 28BYJ-48
        Motor driver : ULN2003A
    """
    
    def __init__(self, in1:int, in2:int, in3:int, in4:int, mode:int=0, speed:float=1.0, stride_angle:float=5.625, gear_reduction:int=64):
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
            stride_angle (float, optional)
                angle per step in half-step mode
        """
        # Constant waiting times for highest (1) and lowest (0) speed
        self._WAIT_HIGH_SPEED = 0.001
        self._WAIT_LOW_SPEED = 0.004
        
        # Set the pins
        self._in1 = OutputDevice(in1)
        self._in2 = OutputDevice(in2)
        self._in3 = OutputDevice(in3)
        self._in4 = OutputDevice(in4)
        self._pins = [self._in1, self._in2, self._in3, self._in4]
        
        # Step sequence for half-step operation
        self._seq_half_step = [ \
            [1,0,0,1], 
            [1,0,0,0], 
            [1,1,0,0],
            [0,1,0,0],
            [0,1,1,0],
            [0,0,1,0],
            [0,0,1,1],
            [0,0,0,1]
        ]
        # Step sequence for full-step operation
        self._seq_full_step = [ \
            [1,0,0,0], 
            [0,1,0,0],
            [0,0,1,0],
            [0,0,0,1]
        ]
        self._seq = self._seq_half_step
        self._seq_len = len(self._seq)
        
        # Set the sequence depending on the mode
        self.mode = mode
            
        # Set the waiting time tepending on the speed
        self.speed = speed
        
        # Set the current step
        self._current_step = 0
        
        # Set stride angle
        self._stride_angle = stride_angle

        # Set gear reduction
        self._gear_reduction = gear_reduction

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

        self._wait = self._WAIT_HIGH_SPEED - self._speed * (self._WAIT_HIGH_SPEED - self._WAIT_LOW_SPEED)

    @property
    def stride_angle(self) -> float:
        return self._stride_angle

    @property
    def gear_reduction(self) -> float:
        return self._gear_reduction

    def _step(self, direction:int):
        """ Do one step in the current direction
        
        Args:
            direction (int):
                 1: forward
                -1: backward
        """
        for motor_step in range(0, self._gear_reduction):
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
            
    def rotate_right(self, angle:float):
        """ Rotate right by the given angle

        Args:
            angle (float): angle to rotate
        """
        if self.mode == 0:
            steps = round(angle / self._stride_angle)
        else:
            steps = round(angle / 2 * self._stride_angle)
        self.step_forward(steps)
            
    def rotate_left(self, angle:float):
        """ Rotate left by the given angle

        Args:
            angle (float): angle to rotate
        """
        if self.mode == 0:
            steps = round(angle / self._stride_angle)
        else:
            steps = round(angle / 2 * self._stride_angle)
        self.step_backward(steps)
        
    def close(self):
        """ Close gpiozero resources associated with pins
        
        """
        for pin in range(0, 4):
            self._pins[pin].close()
        
if __name__ == "__main__":
    print("==== Test StepperMotor ======")
    for mode in range(0, 2):
        for ispeed in range(1, -1, -1):
            speed = float(ispeed)
            print(f"==== mode={mode} == speed={speed } ====")
            sm = StepperMotor(10, 9, 11, 0, mode=0, speed=1)
            print(f"==== step_forward(64) =======")
            sm.step_forward(64)
            print(f"==== step_backward(64)")
            sm.step_backward(64) 
            time.sleep(2)
            print(f"==== rotate_right(90) =======")
            sm.rotate_right(90) 
            time.sleep(2)
            print(f"==== rotate_left(90) =======")
            sm.rotate_left(90) 
            time.sleep(2)
            print(f"==== close ====")
            sm.close()
    print(f"==== Test completed ====")
