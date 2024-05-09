# Release Notes

[![Up](img/goup.gif)](../README.md)

## Update Procedure

1. Within a SSH session go to the **raspiCamSrv** root directory    
```cd ~/prg/raspi-cam-srv```
2. Use [git pull](https://git-scm.com/docs/git-pull) to update to the latest version     
```git pull```    
As a result, you will see a summary of changes with respect to the previously installed version.
3. Restart the service, depending on [how the service was installed](../README.md#service-configuration)    
```sudo systemctl restart raspiCamSrv.service```    
or    
```systemctl --user restart raspiCamSrv.service```
4. Check that the service started correctly     
```sudo journalctl -e```    
or    
```journalctl --user -e```

## V2.5.3

## Bugfixes

- The previous fix was not robust enough and really worked only with debugging activated..    
Now, the camera is given a second more time after different steps of switching.

## V2.5.2

### Bugfixes

- Switching the camera caused ```RuntimeError: Unable to stop preview.``` (see [raspi-cam-srv Issue #14](https://github.com/signag/raspi-cam-srv/issues/14)).    
This is now fixed. Switching the camera can be done from the [Settings](./Settings.md#switching-the-active-camera) screen as well as from the [WebCam](./Webcam.md#-switch-cameras-) screen.

## V2.5.1

### New Features

- During [Motion Capture](./TriggerMotion.md), framerates are also reported for the *Mean Square Diff* algorithm.    
See [Testing Motion Capturing](./TriggerMotion.md#testing-motion-capturing)

## V2.5.0

### New Features

- [Extended Motion Capturing Algorithms](./TriggerMotion.md) are available, including [Frame Differencing](./TriggerMotion.md#test-for-frame-differencing-algorithm), [Optical Flow](./TriggerMotion.md#test-for-optical-flow-algorithm) and [Background Subtraction](./TriggerMotion.md#test-for-background-subtraction-algorithm)
- The [Extended Motion Capturing Algorithms](./TriggerMotion.md) can be run in a testing mode, showing live views of intermediate image processing results which can help for a better understanding of the algorithms and adjustment of their variable parameters.

### Changes

- For Motion Detection, Trigger Parameters (see [Database for Events](./TriggerActive.md#database)) have been changed from format "string" to Python Dictionary, allowing multiple parameters for the [Extended Motion Capturing Algorithms](./TriggerMotion.md).    
Existing database entries with string format are still supported.

## V2.4.3

### Bugfixes

- When data for an ACTIVE [Photo Series](./PhotoSeries.md) were changed, the [status](./PhotoSeries.md#photo-series-state-chart) of the series was set back to "READY" but the thread was still active.    
Now, for an ACTIVE or PAUSED series, the *Photo Type* and *Start* can no longer be changed.    
The status will be promoted only for a NEW series.    
For a series in status FINISHED, data can no longer be modified.
- The ERROR ```Could not import SensorConfiguration from picamera2.configuration```, which occured on Bullseye systems was changed to INFO

## V2.4.2

### Bugfixes

- If livestream terminates, camera is closed if a [Photo Series](./PhotoSeries.md) is active (no [Exposure Series](./PhotoSeriesExp.md) or [Focus Stack](./PhotoSeriesFocus.md)) and if the time to the next shot is larger than 60 sec.    
In the previous version, the camera would not have been closed if a Photo Series was active at the time when the livestream terminated.    
If, for example, the interval for the Photo Series would have been 1 hour and if the livestream would have been activated shortly after a shot was taken, the camera would have been open and started for about one hour and only be closed after the next shot of the series.

## V2.4.1

### New Features

- Process information for the Flask server process and its threads has been added to the [Info screen](./Information.md) 
- Camera status information has been added to the [Info screen](./Information.md)

### Improvements
- Cameras are now stopped and closed in times when they are not active.   
As a consequence, the number of active threads and CPU utilization is reduced in phases when cameras are not streaming and no other background processes (video recording, photo series, motion capturing) are active.    
For more details, see [Camera Status and Number of Threads](./Information.md#camera-status-and-number-of-threads)


### Bugfixes

- [Code Generation](./Troubelshooting.md#generation-of-python-code-for-camera) did not generate import statements.
- Error status for [Triggered Capture of Videos and Photos](./Trigger.md) which had been stored with [Store Configuration](./Settings.md#server-configuration) are now cleared if server is started with stored configuration

## V2.4.0

### New Features

- Photo Series can be set to be [automatically continued](./PhotoSeries.md#series-configuration) on server start if they had been interrupted by a server stop or system shotdown or reboot.

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
