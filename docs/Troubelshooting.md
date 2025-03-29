# raspiCamSrv Troubleshooting

[![Up](img/goup.gif)](./UserGuide.md)

This page intends to collect information on how to deal with errors or problems which may occur while running **raspiCamSrv**.

- **Password forgotten**    
If you have your password forgotten, there are two alternatives:<br>1. Somone else is Superuser:<br>Ask him to remove your user entry and create a new one (See [Settings / Users](./SettingsUsers.md)).<br>2. You are the Superuser.<br>You need to reset the database where user entries are stored.<br>You do this with with ```flask --app raspiCamSrv init-db``` (see [RaspiCamSrv Installation](../README.md#raspicamsrv-installation) Step 11).<br>At the next Login, you need to Register as new Superuser (see [Authorization](./Authentication.md))

- **ERROR in motionDetector: Exception in _motionThread: OpenCV(4.6.0)**   
This error may occur when trying to use [extended motion capturing](./TriggerMotion.md) while the 'YUV420' stream format is set for the [Live View Configuration](./Configuration.md). <br>It seems that OpenCV is not capable to handle images with this format.    
This error is typically observed on Pi3 and Pi4 where the YUV stream format is mandatory for the lores stream according to the [Picamera2 Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf), ch. 4.2.<br>
As a workaround, you may try setting the "main" stream for the Live View configuration with "RGB888" Stream Format.   
To avoid performance issues, also a low Stream Size (e.g. 640x400) should be chosen.<br>
See [raspi-cam-srv Issue #48](https://github.com/signag/raspi-cam-srv/issues/48)

- **No Connection to server although server has been started as service**.    
This may happen (see [raspi-cam-srv Issue #8](https://github.com/signag/raspi-cam-srv/issues/8)) if the service has been started before the network interfaces are ready.   
The systemd journal will indicate that the Flask server is only listening to *localhost* (127.0.0.1)   
In this case, more restrictive settings in the *After* clause of the [service configuration](../README.md#service-configuration) file may be required (see [systemd Network Configuration Synchronization Points](https://systemd.io/NETWORK_ONLINE/)) 
- **SystemError: No cameras were found on the server's device**   
See [raspi-cam-srv Issue #6](https://github.com/signag/raspi-cam-srv/issues/6)
- **ERROR in camera_pi: Could not import SensorConfiguration from picamera2.configuration. Bypassing sensor configuration**   
This message may occur when running on Bullseye systems.   
Currently, it can be ignored because the missing *SensorConfiguration* class has currently no impact on **raspiCamSrv** functionality.   
*SensorConfiguration* is a class in Picamera2 which is referenced in the CameraConfiguration (see [Picamera2 Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf) chapter 4.3)    
It includes information on the output size and bit depth of a stream.    
In Bullseye systems, this class is missing.         
Currently, raspiCamSrv does not require the *SensorConfigiuration* but it is included in the data model because Picamera2 uses it.   
The error occurs when trying to import the class.   

- **WARN RPiSdn sdn.cpp:39 Using legacy SDN tuning - please consider moving SDN inside rpi.denoise**   
This is just a warning from the libcamera system that the tuning file should be updated.      
It is currently not known that there is an impact on raspiCamSrv functionality.


- **ERROR V4L2 v4l2_videodevice.cpp:1906 /dev/video4[16:cap]: Failed to start streaming: Broken pipe**  
See [picamera2 Issue #104](https://github.com/raspberrypi/libcamera/issues/104) from Feb 1, 2024   
The recommended solution was to go back to kernel release 6.1.65 with ```sudo rpi-update d16727d```
- **ModuleNotFoundError: No module named 'picamera2'**   
See [raspi-cam-srv Issue #4](https://github.com/signag/raspi-cam-srv/issues/4)
- **TypeError: memoryview: casts are restricted to C-contiguous views**   
See [picamera2 Issue #959](https://github.com/raspberrypi/picamera2/issues/959)

## Logging

The **raspiCamSrv** server uses Python logging.

Logging is initialized in module ```__init__.py```.   
All lines controlling the way of logging or [code generation](#generation-of-python-code-for-camera) are preceeded with a comment line, starting with   
```#>>>>>```

By default, a StreamingHandler is added to all loggers which outputs log information to sys.stderr.   
If desired, the prepared FileHandler can be activated.

The log level for all loggers is initialized with level ERROR.   
This can be modified for all or for specific modules.

### Flask logging

Flask logging is controlled by ```app.logger```

### Werkzeug logging

Werkzeug implements WSGI, the standard Python interface between applications and servers.

Werkzeug logs basic request/response information.

Werkzeug logging is controlled by ```logging.getLogger("werkzeug")```.

The log level is initialized in ```__init__.py``` with INFO, in order to enable informative logging during server start.

After the server has been started, the log level is raised to ERROR.   
This is done in ```auth.py``` in function ```login_required(view)```.

### raspiCamSrv Logging

Logging can be controlled individually for each module.

### libcamera logging

The libcamera library is the basic C++ camera library on which Picamera2 is based.

The log level is controlled through an environment variable LIBCAMERA_LOG_LEVELS.   
This is set in ```__init__.py``` to WARNING.   
Other allowed log levels are listed in the comment.

For more details, see [Picamera2 manual](./picamera2-manual.pdf), chapter 8.6.2

### Picamera2 logging

Picamera2 logging is initialized in ```__init__.py``` with ERROR

For more details, see [Picamera2 manual](./picamera2-manual.pdf), chapter 8.6.1

## Generation of Python Code for Camera

The system can generate a file with Python code including the entire interaction of **raspiCamSrv** with Picamera2.   
This file can then be used for debugging and error analysis.

A specific logger ("pc2_prg") with with level DEBUG is used for code generation.   
The logger can be activated by setting   
```prgLogger.setLevel(logging.DEBUG)```   
in ```__init___.py```

The code file is located in   
```/home/<user>/prg/raspi-cam-srv/logs```   
with name   
```prgLog_YYYYMMDD_hhmmss.log```

A new file will be generatet at every server start.

To run the files, you neet to change the file type from ```.log``` to ```.py```   
Generating the files with ```.py``` extension does not work because Flask seems to recognize these files and does strange things.

All photo and video output generated by these files will be located at    
```/home/<user>/prg/raspi-cam-srv/output```   
with the same file names as in the original session.
