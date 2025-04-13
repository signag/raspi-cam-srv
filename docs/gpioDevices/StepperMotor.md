# StepperMotor

```
class StepperMotor(*args, **kwargs)
```

extends ```gpiozero.OutputDevice``` and represents a generic stepper motor connected to a stepper motor driver.    
An example combination, for which this class has been developped and tested, is the stepper motor **28BYJ-48** with the motor driver **ULN2003A**.

1. Plug in the 5-cable jack of the motor into the socket of the motor driver.   
2. Connect the 4 inputs on the motor driver (IN1 ... IN4) to 4 GPIO pins of the Raspberry Pi.<br>It is important to correctly memorize which pin is connected to which input.
3. Connect the power input of the motor driver to Raspberry Pi 5V and GND pins with the correct polarity.

The following code will rotate the motor counter-clockwise (from the perspective of the motor) by 15°:
```
from raspiCamSrv.gpioDevices import StepperMotor
stepper = StepperMotor(6, 13, 19, 26)
stepper.rotate(-15)
stepper.close()
```

## Parameters

- **in1** (*int*) - The GPIO pin that the motor drivers **IN1** pin is connected to
- **in2** (*int*) - The GPIO pin that the motor drivers **IN2** pin is connected to
- **in3** (*int*) - The GPIO pin that the motor drivers **IN3** pin is connected to
- **in4** (*int*) - The GPIO pin that the motor drivers **IN4** pin is connected to
- **mode** (*int*) The mode in which the motor is operated.<br>Can be ```0``` (the default) for selecting half step mode with a resolution of 8 steps per full turn or ```1``` for full step mode with 4 steps per turn.
- **speed** (*float*) - The speed with which the motor is operated. The speed is controlled through waiting times between successive steps.<br>A value of ```0.0``` results in the lowest speed with a waiting time of 4 ms and a value of ```1.0``` (the default) results in the highest speed with a waiting time of 1ms.<br>Values outside of this interval will be set to the nearest interval border.
- **current_angle** - (*float*) The current angle of the motor. Defaults to 0.0
- **swing_from** - (*float*) left boundary angle for swinging. Defaults to -45.0
- **swing_to** - (*float*) right boundary angle for swinging. Defaults to 45.0
- **swing_step** - (*float*) step width for swinging. Defaults to 9.0
- **swing_direction** - (*int*) current swing direction. 1 (default) clockwise, 0 counter-clockwise.
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

### *property* **current_angle**

Returns or sets the current angle.    
When the class is initiated, the angle is set to zero.    
Every motor movement will update the current angle.   
For **step**, **step_forward** and **step_backward**, the current angle will stay within (-360 <= *current_angle* <= 360).    
For the **rotate*** and **swing** methods, *current_angle* is not restricted to these limits, which allows tracking of multiple turns.

### *property* **value**

Returns or sets the current angle.    

### *property* **swing_from**

Returns or sets the left boundary for swinging in degree (-360 - 0).    

### *property* **swing_to**

Returns or sets the right boundary for swinging in degree (0 - 360).    

### *property* **swing_step**

Returns or sets the step width for swinging in degree (0 - 360).

### *property* **swing_direction**

Returns or sets the current swinging direction. 1=right, -1=left

### **step**(*steps=?*)

Steps forward for positive and backward for negative argument by the given number of steps.    
Thus, the angle is changed by *steps x stride_angle*.   
When using this method, 

**Parameters**:

- **steps** (*int*) Number of steps to move (positive or negative)

### **step_forward**(*steps=?*)

Steps forward (clockwise rotation) by the given number of steps.    
Thus, the angle is increased by *steps x stride_angle*

**Parameters**:

- **steps** (*int*) Number of steps to move forward (positive value)

### **step_backward**(*steps=?*)

Steps backward (anti-clockwise rotation) by the given number of steps.    
Thus, the angle is decreased by *steps x stride_angle*

**Parameters**:

- **steps** (*int*) Number of steps to move backward (positive palue)

### **rotate**(*angle=?*)

Rotate clockwise (for positive angle) or counter-clockwise (for negative angle) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive or negative)

### **rotate_right**(*angle=?*)

Rotate right (clockwise from the pespective of the motor) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive)

### **rotate_left**(*angle=?*)

Rotate left (anti-clockwise from the pespective of the motor) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive)

### **rotate_to**(*target=?*)

Rotate to the given angle.

**Parameters**:

- **target** (*float*) Angle to rotate to

### **swing**()

Do one swing step in the current *swing_direction* with the current *swing_step*.
If the *current_angle* would exceed *swing_from* or *swing_to*, rotation will reverse its direction at the border.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive)

### **close()**

Shut down the device and release all associated resources (such as GPIO pins). 
