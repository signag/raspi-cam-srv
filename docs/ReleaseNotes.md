# Release Notes

[![Up](img/goup.gif)](../README.md)

## V2.4.0

### New Features

- Photo Series can be set to be [automatically continued](./docs/PhotoSeries.md#series-configuration) on server start if they had been interrupted by a server stop or system shotdown or reboot.

### Bugfixes

- The active [Photo Series](./PhotoSeries.md) had always been set to the alphabetically last series in case of a server start/restart, even if another series had been active at the time when the server was stopped.    
Now, if a series with status "ACTIVE" is found when the server is started, this series will be set as active series.

## V2.3.6

### Bugfixes

- Fixed error ```[Errno 12] Cannot allocate memory``` for Raspberry Pi 3.    
(See [raspi-cam-srv Issue #9](https://github.com/signag/raspi-cam-srv/issues/9))    
Lower values for buffer_count are now also used for Pi 3, Pi 2 and Pi 1. in the same way as for Pi 4 and Pi Zero.

## V2.3.5

### Bugfixes

- Fixed issue with **endpoints photo_feed and photo_feed2**:    
These endpoints use the live streams for the available cameras. However, if the live stream was not active at the time when a client requested this endpoint, no photo was shown. Only when live streams were activated through the **raspiCamSrv** Web UI, photos were shown.   
Now, when these endpoints are requested, the system automatically starts a live stream if it is currently not active and delivers a photo.

## V2.3.4

### New Features

- e-Mail notification on motion capturing events (see [Notification](./TriggerNotification.md))

## V2.3.3

### Bugfixes

- Starting server with stored Configuration ([Settings](./Settings.md#server-configuration)) did not correctly set a previously configured [Zoom](./ZoomPan.md) (*ScalerCrop*). Instead, *ScalerCrop* was set to the active camera's pixel array size (see [raspiCamSrv Issue #7](https://github.com/signag/raspi-cam-srv/issues/7)). This was done only during initial system start and not after manually applying **Load Stored Configuration** in [Settings](./Settings.md#server-configuration).   
Now, the stored *ScalerCrop* is no longer overwritten, if a zoom (<>100%) has been explicitely applied ("include_scalerCrop": true in controls.json).


## V2.3.2

### Improvements

- Error handling has been improved. Server errors, also from background threads, are routed to the web client.   
This does not apply to errors occurring in encoders which are running in own threads. Exceptions thrown in these threads are currently not handled by **raspiCamSrv**.   
Error reasons are mostly invalid combinations of [Configuration](./Configuration.md) parameters, especially with *Stream Format*

### Bugfixes

- After applying **Swith Cameras** in page *Web Cam*, Title and metadata for the second camera were identical to those of the first camera.
- [Reset Server](./Settings.md#server-configuration) may have caused errors in streaming or other functions
- In [Config](./Configuration.md), *raw* stream can no longer be configured for *Live View*, *Photo*, and *Video*

## V2.3.1

### Bugfixes

- Avoid flooding with console error message "Motion detection thread did not stop within 5 sec".    
Now assuming that thread does no longer exist.
- Fixed error ```TypeError: can only concatenate str (not "NoneType") to str``` which could occur in ```motionDetector.py``` if video recording failed after motion detection.   
In this case, there has been an error message in [events logfile](./TriggerActive.md#log-file)
- Encoder Bitrate is no longer specified when recording a video (before it was set to 10000000)
- Changed loglevel from ```debug``` to ```error``` when an exception occurred during video recording
- Added error log when encoder could not be started after motion capture.   
Previously, the error was only shown in the [events logfile](./TriggerActive.md#log-file)
- For Raspberry Pi 4, the default sensor mode is set to 0 (lowest resolution) in order to avoid encoder errors.
- For Raspberry Pi 4, motion capture videos are recorded from the *lowres* stream with *Live View* configuration
- For Raspberry Pi 4, default buffer count was reduced to 2 for live view and 4 for video

## V2.3.0

### New Features

- Streaming of second camera added (see [Webcam](./Webcam.md) page). A single **raspiCamSrv** server can now simultaneously stream both cameras connected to a Raspberry Pi 5.
- The camera configuration and controls for the active camera can be preserved also for a situation when this camera acts as "other" camera.
- Streaming configurations for both cameras are stored together with the entire configuration (see [Settings](./Settings.md#server-configuration-storage)) and can be loaded on server restart.

## V2.2.3

### Bugfixes

- For Raspberry Pi Zero, use the *lowres* stream (Live View Configuration) for recording videos during motion capture.   
During motion capture, the *Live View* camera configuration is used because the live stream is required for detecting motion. However, the *Buffer Count* of 2, used for this configuration for Pi Zero (see [V2.1.2](#v212)), is too small for video recording with the resolution of the *Video* configuration.
- Fixed an error which could occur when [viewing events](./TriggerEventViewer.md#events) when placeholder photos for videos were not yet read from the database.

## V2.2.2

### New Feature

- Added an option to automatically start motion capture with the Flask server.   
Thus, if server start is done in a service, motion capturing will automatically be active if the device is booted.   
(See [Triggered Capture of Videos and Photos](./Trigger.md))

## V2.2.1

### Bugfixes

- Prevent changing settings while the trigger-capture process is active
- Prevent changing camera configuration while the trigger-capture process is active
- Prevent starting an Exposure Series or a Focus Stack Series while the trigger-capture process is active
- Fixed "ValueError: could not convert string to float: ''" which may have ocurred for Exposure Series or Focus Stack Series with a camera having no focus support

## V2.2.0

### Installation Hints

This version has a new database schema with tables used for captured events.

After an update with ```git pull```, you need to initialize the database with   
```flask --app raspiCamSrv init-db```   
before starting the server.   
This will also recreate the user database and requires new registration.

Services should be stopped during upgrade

### New Feature

- Introduced basic motion capturing (see [Triggered Capture of Videos and Photo](./Trigger.md))

## V2.1.2

### Bugfix

- For Raspberry Pi Zero, the "Buffer Count* in the [Configuration](./Configuration.md) for *Live View* and *Video* has been reduced to 2 and 4, respectively because of memory issues.   
Also, the default *Sensor Mode* for *Video* has been set to the lowest (0) mode, rather than to the highest.

## V2.1.1

### Known issues

- On Pi Zero, there seems to be issues with parallel live stream on *lores* and video recording or phototaking on *main*.   
Got ```Camera frontend has timed out!``` exception.   
Probably, this feature needs to be deactivated on these platforms. Need to study in more details.

### New Features

- The Camera [Information](./Information.md) screen now shows also information on the Raspberry Pi version and board version.

### Bugfix

- For Raspberry Py systems Pi 4 and earlier, the *Stream Format* for *Live view* is initialized with "YUV420".    
According to the [Picamera2 Manual](./picamera2-manual.pdf) ch. 4.2, p. 16, this format must be used for these systems for the *lowres* stream which is now the default for *Live View*.   
The list of values for the *lowres* stream in the [Config](./Configuration.md) dialog is not restricted to YUV format, however, if an other format is selected, an error message is shown and the parameter remains at "YUV420".
- On Bullseye systems (Pi Zero), the package *picamera2.configuration* does not currently include the class *SensorConfiguration*. Also the *CameraConfiguration* class does not contain the element *sensor*.   
This caused an "Import Error" when starting the server.   
This error is now captured and, if it occurs, the *sensor* element in the configuration is ignored.


## V2.1.0

### New Features

- Added endpoint for photo snapshots ([raspi-cam-srv Issue #5](https://github.com/signag/raspi-cam-srv/issues/5))  
(see [Web Cam](./Webcam.md))

## V2.0.0


### New Features

- Major modification of camera control to allow non-exclusive access to the camera from parallel tasks.   
Phototaking, video recording and photoseries do no longer interrupt the live stream if the required camera configurations are compatible.    
(See [raspiCamSrv Tasks and Background Processes](./Background%20Processes.md))
- Added code generation to the camera module.   
The code used for interaction of **raspiCamSrv** with Picamera2 is logged into a file specific for each server run. This generates executable Python code, suitable to 'replay' the entire camera interaction of a raspiCam Server run.    
This can be used for testing and error analysis.   
(See [Generation of Python Code for Camera](./Troubelshooting.md#generation-of-python-code-for-camera))

### Changes

- The camera configuration for VIDEO is now initialized with the sensor mode with the largest stream size in order to allow simultaneous use of main stream for Photo and Video.

### Refactoring

- General refactoring of "Timelapse series" to "Photo Series".   
Timelapse series are now just a special kind of photo series.
- The folder ```raspi-cam-srv/raspiCamSrv/static/timelapse``` is no longer used.   
Instead, photo series are now stored in folder ```raspi-cam-srv/raspiCamSrv/static/photoseries```   
This folder will be automatically created at the first server start.   
If you have stored photoseries under the ```timelapse``` folder, you can move them to the ```photoseries``` folder and then delete the ```timelapse``` folder.   
For each series, you need to exchange ```/timelapse/``` with ```/photoseries/``` in the ```*_cfg.json``` files
