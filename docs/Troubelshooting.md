# raspiCamSrv Troubleshooting

[![Up](img/goup.gif)](./UserGuide.md)

This page intends to collect information on how to deal with errors which may occur while running **raspiCamSrv**.

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
