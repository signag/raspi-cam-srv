# ServoPWM

## Overview

```
class ServoPWM(*args, **kwargs)
```

implements control of servo motors with hardware PWM.

Development of this class was motivated by the fact that software-based PWM,
as provided by the default RPi.GPIO pin factory in gpiozero, results in significant jitter for servo motors.
The alternative pigpio pin factory does support hardware PWM, but it is currently not compatible
with the latest Debian release (Trixie) for Raspberry Pi. 

In this class, hardware PWM support makes use of the [rpi-hardware-pwm](https://github.com/Pioreactor/rpi_hardware_pwm) library which needs to be installed with     
```pip install rpi-hardware-pwm```

On Raspberry Pi, hardware PWM is only supported for the GPIO pins 12, 13, 18 and 19.

Routing of the PWM signal to one or several of these pins needs to be configured through device tree
overlays in ```/boot/firmware/config.txt``` (Trixie or Bookworm) or ```/boot/config.txt``` (Bullseye):   
for example:    
```
[all]
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
```

On RPI 4 and earlier only up to 2 pins can be configured for PWM simultaneously.

On RPI 5, you can configure up to 4 pins, e.g.
```
[pi5]
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2
```

You need to reboot after dtoverlay changes.

Which pins are enabled for PWM can be checked with    
```pinctrl get 12,13,18,19```

You will get something like     
```
12: a0    pd | lo // GPIO12 = PWM0_CHAN0
13: a0    pd | lo // GPIO13 = PWM0_CHAN1
18: no    pd | -- // GPIO18 = none
19: no    pd | -- // GPIO19 = none
```

ServoPWM checks PWM enabling for the specified pin.    
ServoPWM will translate the GPIO pin number to the correct PWM channel.

Setup:

1. Connect the signal cable of the servo to the chosen GPIO pin
2. Connect the power input of the servo to Raspberry Pi 5V and GND pins with the correct polarity.

The following code will rotate the servo clockwise (from the perspective of the servo) by 15°:
```
from raspiCamSrv.gpioDevices import ServoPWM
servo = ServoPWM(12)
servo.rotate(15)
servo.stop()
```

The class was tested with a KY66 servo.

## Parameters

- **pin** (*int*) - The GPIO pin that the servo signal input is connected to
- **min_angle** - (*float*) The minimum angle, the servo can drive to. Defaults to -90.0
- **max_angle** - (*float*) The maximum angle, the servo can drive to. Defaults to  90.0
- **min_pulse_width_us** - (*int*) The minimum PWM pulse width in microseconds. Defaults to 500
- **max_pulse_width_us** - (*int*) The maximum PWM pulse width in microseconds. Defaults to 2500
- **frame_width_us** - (*int*) The frame width of the PWM signal in microseconds. Defaults to 20000
<br>(frequency = 1000000/frame_width_us)
- **speed** (*float*) - Speed of the servo: time (in sec) required for a 360° turn. Defaults to 2.8
<br>This parameter is only used in case of *idle_off*=True to calculate the time for a requested rotation before the signal can be set to low.
- **idle_off** - (*bool*) If True, the PWM pulse width is set to 0 after a requested rotation has been finished. Defaults to False
<br>If jitter occurs in idle phases, this can be activated to eliminate jitter.
<br>Normally, this is not required for hardware PWM.
- **calibration** (*float*) - Calibration angle which will be considered as 0 position of the servo. Defaults to 0.0
<br>Must be between *min_angle* and *max_angle*.

## Properties and Methods

### *property* **current_angle**

Returns or sets the current angle relative to *calibration* angle.    
Any rotations are limited to the range within *min_angle* and *max_angle*.

### *property* **value**

Synonym for *current_angle*

### **min**()

Rotate to the minimum position of the servo.     
The minimum position is the position to which the servo drives with the specified *min_pulse_width_us*
The absolute angle at this position (without calibration) is assumed to be *min_angle*

### **max**()

Rotate to the maximum position of the servo.     
The maximum position is the position to which the servo drives with the specified *max_pulse_width_us*
The absolute angle at this position (without calibration) is assumed to be *max_angle*

### **mid**()

Rotate to the mid position of the servo.    
This is the position halfway between *min_angle* and *max_angle*.

Note that for non-zero *calibration*, this position is different from *current_angle*=0.0.

### **rotate_to**(*angle=?*)

Rotate to the given angle relative to *calibration*.

**Parameters**:

- **angle** (*float*) Angle to rotate to

### **rotate_by**(*angle=?*)

Rotate by the given angle relative to *current_angle.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive or negative)

### **rotate_right**(*angle=?*)

Rotate right (clockwise from the pespective of the servo) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive)

### **rotate_left**(*angle=?*)

Rotate left (anti-clockwise from the pespective of the servo) by the given angle.

**Parameters**:

- **angle** (*float*) Angle to rotate (positive)


### **stop()***

Stop PWM.

### **close()***

Stop PWM.
