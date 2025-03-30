# StepperMotor

```
class StepperMotor(*args, **kwargs)
```

extends ```gpiozero.OutputDevice``` and represents a generic stepper motor connected to a stepper motor driver.    
An example combination, for which this class has been developped and tested, is the stepper motor **28BYJ-48** with the motor driver **ULN2003A**.

1. Plug in the 5-cable jack of the motor into the socket of the motor driver.   
2. Connect the 4 inputs on the motor driver (IN1 ... IN4) to 4 GPIO pins of the Raspberry Pi.<br>It is important to correctly memorize which pin is connected to which input.
3. Connect the power input of the motor driver to Raspberry Pi 5V and GND pins with the correct polarity.

The following code will step the motor forwards by a specific number of steps:
```
from raspiCamSrv.gpioDevoces import StepperMotor
stepper = StepperMotor(6, 13, 19, 26)
motor.rotate(90)
motor.close()
```

## Parameters

- **in1** (*int*) - The GPIO pin that the motor drivers **IN1** pin is connected to
- **in2** (*int*) - The GPIO pin that the motor drivers **IN2** pin is connected to
- **in3** (*int*) - The GPIO pin that the motor drivers **IN3** pin is connected to
- **in4** (*int*) - The GPIO pin that the motor drivers **IN4** pin is connected to
- **mode** (*int*) The mode in which the motor is operated.<br>Can be ```0``` (the default) for selecting half step mode with a resolution of 8 steps per full turn or ```1``` for full step mode with 4 steps per turn.
- **speed** (*float*) - The speed with which the motor is operated. The speed is controlled through waiting times between successive steps.<br>A value of ```0.0``` results in the lowest speed with a waiting time of 4 ms and a value of ```1.0``` (the default) results in the highest speed with a waiting time of 1ms.<br>Values outside of this interval will be set to the nearest interval border.
- **stride_angle** - (*float*) The angle incremet for a single step after gearing.<br>The default value of 5.625 is the value for the **28BYJ-48** motor.
- **gear_reduction** (*int*) - The inverse of the transmission ratio of the gear box.<br>The default value of 64 is the value of the 1/64 ratio for the **28BYJ-48** motor.

### *property* **mode**

Returns or sets the mode of operation.

### *property* **speed**

Returns or sets the speed.

### *property* **stride_angle**

Returns the stride angle.

### *property* **gear_reduction**

Returns the gear_reduction

### **step_forward**(*steps=?*)

Steps forward (clockwise rotation) by the given number of steps.    
Thus, the angle is increased by *steps x stride_angle*

**Parameters**:

- **steps** (*int*) Numner of steps to move forward

### **step_backward**(*steps=?*)

Steps backward (anti-clockwise rotation) by the given number of steps.    
Thus, the angle is decreased by *steps x stride_angle*

**Parameters**:

- **steps** (*int*) Numner of steps to move backward

### **rotate_right**(*angle=?*)

Rotate right (clockwise from the pespective of the motor) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate

### **rotate_left**(*angle=?*)

Rotate left (anti-clockwise from the pespective of the motor) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate

### **close()**

Shut down the device and release all associated resources (such as GPIO pins). 
