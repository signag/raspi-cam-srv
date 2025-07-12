# Release Notes

[![Up](img/goup.gif)](../README.md)

## Update Procedure

Before updating, make sure that
- [video recording](./Phototaking.md#video) is stopped
- there are no active [photoseries](./PhotoSeries.md)
- [triggered capture](./Trigger.md) (motion tracking) is stopped
- server will not [start with stored configuration](./SettingsConfiguration.md)

For update, proceed as follows:    
(If running a Docker container see [Update Procedure for Docker Container](./SetupDocker.md#update-procedure))

1. Within a SSH session go to the **raspiCamSrv** root directory    
```cd ~/prg/raspi-cam-srv```
2. If you have made local changes (e.g. logging), you may need to reset the workspace with   
```git reset --hard```
3. Use [git pull](https://git-scm.com/docs/git-pull) to update to the latest version     
```git pull```    
As a result, you will see a summary of changes with respect to the previously installed version.
4. Restart the service, depending on [how the service was installed](../README.md#service-configuration)    
```sudo systemctl restart raspiCamSrv.service```    
or    
```systemctl --user restart raspiCamSrv.service```
5. Check that the service started correctly     
```sudo journalctl -e```    
or    
```journalctl --user -e```
6. If you used [start with stored configuration](./SettingsConfiguration.md) before updating, you may now try to activate this again.<br>In cases where configuration parameters were not modified with the update, this will usually work.<br>If not, you will need to prepare and store your preferred configuration again.

In case that the server did not start correctly or if you see an unexpected behavior in the UI, you may have forgotten to deactivate [start with stored configuration](./SettingsConfiguration.md)<br>In this case, you can do the following:

- ```cd ~/prg/raspi-cam-srv/raspiCamSrv/static/config```
- Check whether a file ```_loadConfigOnStart.txt``` exists in this folder.
- If it exists, remove it:<br>```rm _loadConfigOnStart.txt```
- Then repeat step 4, above

## V3.5.5

### Bugfixes

- Thread-safe handling of last live stream access. The last access of a client to a camera stream controls automatic shutdown of the streaming server after 10 sec of inactivity (see [Streaming](./UserGuide.md#streaming)).    
Since streaming clients and servers are executed in different threads, it could happen in rare cases that a client has tried to access a stream in a phase where the server has started but not yet completed to shut down because of inactivity.    
Since the camera is closed when streaming is shut down, different camera errors could occur, depending on camera shutdown status.   
This could occur in particular when taking photos or taking [Photo Snapshots](./Webcam.md#photo-snapshot) through the Web URL.   
Now, access to the time of last stream access has been made thread-safe by holding locks while a process is evaluating or changing this value and, in cases where inactivity is detected by the server, the lock is only released after the server has completely shut down.    
(Fixes [raspi-cam-srv issue #61](https://github.com/signag/raspi-cam-srv/issues/61))

- After an OS upgrade, *Kernel Version* and *Debian Version* in the [Info/Installed Cameras screen](./Information.md) did not show the correct values if the server was configured to [start with the stored configuration](./SettingsConfiguration.md). Instead, the values from the stored configuration were shown.   
This has been fixed.   
The entry in the [server configuration storage file](./SettingsConfiguration.md#server-configuration-storage) will have the old value until the configuration has been stored.

### Changes

- Information on the *Debian Version* in the [Info/Installed Cameras screen](./Information.md) now includes information on the system architecture (32-/64-bit) of the installed OS.

### New Features

- A new [API](./API.md) WebService endpoint is provided:   
```GET api probe``` allows probing oject properties of live objects of an active **raspiCamSrv** server.   
**NOTE:** This service is mainly intended for error analysis within a live system and requires detailed knowledge of the raspiCamSrv object model.   
You can specify a set of object attributes for which attribute values shall be queried.   
As objects, you select from the base singleton objects {Camera(), CameraCfg(), MotionDetector(), PhotoSeriesCfg() or TriggerHandler()} and then specify valid properties with dot-notation.    
The result is returned in JSON format. Error messages are shown if an attribute is not JSON serializable.

## V3.5.4

### Bugfixes

- Corrected deprecated log level for Picamera2 logging from ```Picamera2.ERROR``` to ```logging.ERROR```   
(See [raspi-cam-srv Issue #62](https://github.com/signag/raspi-cam-srv/issues/62))

## V3.5.3

### Changes

In dialog [Web Cam](./Webcam.md), the button **Memorize Configuration and Controls for Camera Change** was renamed to **Save Active Camera Settings for Camera Switch** in order to more clearly express its functionality.   
See [raspi-cam-srv Issue #60](https://github.com/signag/raspi-cam-srv/issues/60)

## V3.5.2

### Bugfixes

- Fixed a bug which caused [motion detection](./TriggerMotion.md) to be stalled after booting the Raspberry Pi.<br>The error was caused by a race condition between start of the raspiCamSrv server and syncronization of system time with a time server.<br>When time synchronization resets the system time while the live view is already active, this will signal inactivity for more than 10 sec and, therefore, immediately stop the live stream and subsequently close the camera.<br>Since motion detection relies on an active live stream, this could cause blocking of the motion detection thread which then cannot be stopped except by restarting the server.<br>Now, the system checks the system time synchronization status at startup and, if necessary, waits until time is syncronized with the time server.<br>This resolves [raspiCamSrv Issue #28: raspi-cam-srv seems to be frozen sometimes](https://github.com/signag/raspi-cam-srv/issues/28)<br>**NOTE**: This fix does not currently work when running raspiCamSrv as [Docker Container](./SetupDocker.md)

- Fixed missing [Config](./Configuration.md) screen for [Docker installations](./SetupDocker.md)

### New Feature

- The [Info](./Information.md) screen now shows the time when **raspiCamSrv** has recognized time synchronization, which can be considered as the server start time.

## V3.5.1

### Bugfixes

- Fixed video recording during motion tracking for Raspberry Pi models 1, 2, 3:<br>For models Pi 4 and lower, video recording during motion tracking should use the *Live View* [Configuration](./Configuration.md) because this is usually set to lower resolution and should, therefore, not cause memory issues with these devices.<br>Only for Pi 5, the *Video* Configuration should be used.<br>Unfortunately, in versions up to V3.5.0, this was only applied to Pi 4 and Pi Zero, whereas for Pi 1, Pi 2 and Pi 3 the *Video* configuration was used.<br>This is now corrected and for all models <= Pi 4 the *Live View* configuration is used.

## V3.5.0

### New Features

- [StepperMotor](./gpioDevices/StepperMotor.md) has got new functionality. In addition to the new methods ```swing()``` and ```rotate_to(angle)```, the ```current_angle``` of rotation is tracked and can be set and queried.<br>```swing()``` allows stepwise rotations within given boundaries whereas ```rotate_to(angle)``` rotates to a specified angle.<br>This functionality relies on [Calibration](./SettingsDevices.md#calibrating-a-device) and device status tracking.<br>**NOTE**: If you have already a StepperMotor configured, it will not inherit the new functions. You will need to recreate it.
- [Device Configuration](./SettingsDevices.md) for StepperMotor allows [Calibration](./SettingsDevices.md#calibrating-a-device) to set a specific orientation as zero reference.
- For devices requiring [Calibration](./SettingsDevices.md#calibrating-a-device) (currently only StepperMotor), the status is continuously tracked and memorized so that it can be restored after a restart or a renewed device access.<br>**NOTE**: This may not work if the **raspiCamSrv** server is stopped while the StepperMotor is active.
- A new Camera [Trigger] is available: ```when_series_photo_taken``` allows assigning [Actions](./TriggerActions.md) when a photo has been taken within a [Photo Series](./PhotoSeries.md).<br>The trigger does not fire in case of an [Exposure Series](./PhotoSeriesExp.md) or a [Focus Stack](./PhotoSeriesFocus.md)

### Changes

- Camera [Actions](./TriggerActions.md) do no longer trigger events. This means: if, for example, a [Trigger](./TriggerTriggers.md) has been specified when a Photo is taken, this trigger will no longer fire if the photo is taken as an action of another trigger.

### Bugfixes

- [API](./API.md) endpoint ```api/start_triggered_capture``` now also starts event handling and not only motion detection
- [API](./API.md) endpoint ```api/stop_triggered_capture``` now also stops event handling and not only motion detection
- Fixed error ```Camera.frames - Exception: argument of type 'NoneType' is not iterable``` which could occur if button [Load Stored Configuration](./SettingsConfiguration.md) has been pressed.
- Fixed [Load Stored Configuration](./SettingsConfiguration.md): Now, all background processes are stopped before the stored configuration is loaded, and they are restarted afterwards, if they had been active before.
- Fixed [Reset Server](./SettingsConfiguration.md): Now, all background processes are stopped before the configuration is set to default, and they are restarted afterwards, if they had been active before. Some missing configurations which may have led to errors have also been fixed.
- Made ```table-layout:fixed``` for [Versatile Buttons](./ConsoleVButtons.md) and [Action Buttons](./ConsoleActionButtons.md) so that all columns have equal width and empty rows are shown.
- Multiple SMTP mails for the same [Trigger](./TriggerTriggers.md) are avoided.
- Fixed event notification. Due to a timing issue, sent mails could be incomplete and attachments may have been missing.

## V3.4.0

### New Features

- Under [Actions](./TriggerActions.md), it is now possible to configure camera actions:<br>take_photo<br>start_video<br>stop_video<br>record_video with a configurable duration.
- [Actions](./TriggerActions.md) now support SMTP action for sending a mail in case of an event.
- [Trigger](./TriggerTriggers.md) allow configuring *MotionDetector* trigger for *CAM-1*: *when_motion_detected*.<br>This trigger fires when a motion is detected by the cameras [motion detection](./TriggerMotion.md) algorithms.
- [Device Types](./SettingsDevices.md#device-type-configuration) for GPIO devices include now additional GPIO base classes which allows integrating more general devices:<br>- DigitalInputDevice<br>- DigitalOutputDevice<br>- OutputDevice
- An [indicator](./UserGuide.md#title-bar) has been added which indicates unsaved configuration changes.
- The [event log](./TriggerActive.md#log-file) can now be downloaded from the [Calendar view](./TriggerEventViewer.md#calendar)

### Changes

- For [Triggers](./TriggerTriggers.md) with *Source* "Camera" the device names were changed:<br>"Active Camera" -> "CAM-1"<br>"Second Camera" -> "CAM-2"<br>If triggers have been created with the old *Device* names, they will be renamed automatically when data are loaded from the stored configuration.
- For [Versatile Buttons](./SettingsVButtons.md) and [Action Buttons](./SettingsAButtons.md) the maximum number of rows and columns was changed from 9 to 99.
- Added favicon for browser tab

### Bugfixes

- Fixed error<br>```ERROR in camCfg: Error loading from /home/pi/server/raspi-cam-srv/raspiCamSrv/static/config/serverConfig.json: 'NoneType' object is not subscriptable```<br>reported in [raspi-cam-srv Issue #55](https://github.com/signag/raspi-cam-srv/issues/55)
- Bugfixes and improvements for Class [StepperMotor](./gpioDevices/StepperMotor.md):<br>For full-step mode, the waiting time is now doubled while speed range is unchanged. (1ms does not work)<br>New methods *step(steps)* and *rotate(angle)* have been added, which allow positive and negative arguments.<br>Rotations are now with higher precision. They are now in integers of motor steps rather than geared steps.<br>For full-step mode, now two coils are activated in each step, instead of only one, which increases torque.
- Several tables which can become large, can now be scrolled with fixed headers.

## V3.3.0

### New Features

- Configuration of access to [GPIO-connected devices](./SettingsDevices.md) through the [gpiozero](https://gpiozero.readthedocs.io/en/stable/index.html) library.
- Extension of ```gpiozero.OutputDevice``` for support of [Stepper Motors](./gpioDevices/StepperMotor.md)
- Configuration of [Triggers](./TriggerTriggers.md) for events from GPIO-connected input devices, such as sensors and buttons.
- Implementation of callback hooks for photo-related events ('when_photo_taken', 'when_recording_starts', 'when_recording_stops', 'when_streaming_*_starts', 'when_streaming_*_stops') for integration with the new event handling infrastructure.
- Configuring of [Actions](./TriggerActions.md) for GPIO-connected output devices.
- [Configuration of Action Buttons](./SettingsAButtons.md) and [Console / Action Buttons](./ConsoleActionButtons.md) for the direct manual execution of [Actions](./TriggerActions.md) with GPIO-connected output devices such as LEDs, motors and servos. This includes also the control of Stepper Motors.
- An option *On Dial Marks* has been added to [Photo Series](./PhotoSeries.md) which assures that photos will be taken exactly (within tolerances) at every full hour, half hour, quarter, minute, ..., depending on the chosen interval.

## V3.2.0

### New Features

- The [Settings for Versatile Buttons](./SettingsVButtons.md) now allows setting the commandline in [Versatile Buttons](./Console.md) to be interactive, which allows entering commands directly.

- Access to Online Help added to the different application screens.<br>The *Online Help* button opens the document page on GitHub related to the active dialog.

## V3.1.0

### New Features

- Functionality has bee added for configuration of [Versatile Buttons](./Console.md) for execution of commands on the level of the Raspberry Pi's Linux OS.<br>This covers part of the request in [Discussion #47](https://github.com/signag/raspi-cam-srv/discussions/47).

## V3.0.0

## Package version upgrade

- Released for Flask 3.1.0<br>raspiCamSrv can use the current Flask version 3.x<br>Upgrading Flask in an existing installation is not mandatory.<br>In order to upgrade from Flask 3.0.0 to the latest version 3.x, proceed as follows:<br>```cd prg/raspi-cam-srv/```<br>```source .venv/bin/activate```<br>```pip install --upgrade "Flask>=3,<4"```

## V2.13.0

### New Feature

- RaspiCamSrv can now also be deployed in Docker.<br>See [Running raspiCamSrv as Docker Container](./SetupDocker.md)

## V2.12.0

### New Features

- The [Info Screen](./Information.md) has been extended by a section [Streaming Clients](./Information.md#streaming-clients) which shows a list of clients which are currently using any of the camera streams. 

### Bugfixes

- Fixed TypeError which could occur if a paused [Photo Series](./PhotoSeries.md), for which no photos had been taken, was continued. 

- Fixed an error where for a [Photo Series](./PhotoSeries.md) with *Interval* > 60 sec. an additional photo could have been taken about 1.5 sec. before the expected time when the regular photo is taken. If the waiting time between successive photos is > 60 sec. and if no other process requires the camera, the camera is closed to minimize resource consumption. The waiting time is then shortened by 1.5 sec., to account for the time required for camera wakeup. If, however, the live stream is activated within 60 sec. before the time for the next photo, the camera is already active and this additional time is not required. 

- Fixed an error for [Photo Series](./PhotoSeries.md) with *Interval* >> 60 sec. for the case when the series was started while the live stream was still active. In this case, the photo series did not stop the camera during the waiting period because it was required by the live stream. If the photo series continued taking the next photo, it did not recognize that the camera was closed in the meantime. An attempt to take a photo caused the thread to stop without error notification.<br>As a result, the series seemed to be active while it was actually dead.

- Fixed an error for [Photo Series](./PhotoSeries.md) with *Interval* > 60 sec. where controls (e.g. zoom/ScalerCrop) were not applied to the photos of the series, except probably for the first one.<br>The reason was that the camera is closed if the waiting time for the next photo is > 60 sec. and after restart the camara wasn't given time to pick up the controls settings. Now, an additional waiting time of 1 sec. has been added which resolves the issue.

## V2.11.4

### Bugfix

- Fixed [initialization of the raspiCamSrv API](./SettingsAPI.md) which did not work when a secrets file did not yet exist.

## V2.11.3

### Bugfix

- Fixed "TypeError: can only concatenate str", which might occur in special cases for a [Sun-controlled timelapse series](./PhotoSeriesTimelapse.md#).

- Fixed wrong display of *Sunset* in [Timelapse series](./PhotoSeriesTimelapse.md#).

- Fixed "KeyError: 'UnitCellSize'" for cases where camera_properties do not include information on the physical size of the sensor’s pixels

### Doc

- Added [description for setup of stanalone systems](./bp_PiZero_Standalone.md)

## V2.11.2

### Bugfix

- Fixed an issue where photos and videos could not be taken if the [Transform](./Configuration.md#transform) settings for the different configuration were different.<br>Now, when modifying the *Transform (flip <> or flip v)* are changed in one configuration this change is also applied to all other configurations.<br>This covers raspiCamSrv Issue #33 [Errors after changing Transform settings](https://github.com/signag/raspi-cam-srv/issues/33)

## V2.11.1

### Bugfix

- Fixed an import error which occurred after having upgraded to V2.11 when package ```flask-jwt-extended``` has not yet been installed.

## V2.11.0

### New Features

- V2.11.0 introduces the new [raspiCamSrv API](./API.md) for interoperability of raspiCamSrv with other software packages.<br>This resolves the feature request raspi-cam-srv issue #34 [API?](https://github.com/signag/raspi-cam-srv/discussions/34)

- Required installation actions:<br>In order to allow API support, it is necessary to install an additional package.<br>This can be done before or after the [Update Procedure](#update-procedure):<br>```cd ~/prg/raspi-cam-srv```<br>```source .venv/bin/activate```<br>```pip install flask-jwt-extended```

### Changes

- The [Settings](./Settings.md) screen has been restructured to incorporate the additional settings required for the API


## V2.10.5

### Bugfixes

- Allowed port range in [Trigger - Notification](./TriggerNotification.md) extended to [1 ... 65535]<br>Partly resolves raspi-cam-srv issue #42 [SMTP port issue](https://github.com/signag/raspi-cam-srv/issues/42)

- Fixed [Trigger Notification](./TriggerNotification.md) for SMTP servers which do not require authentication.<br>It can now be specified whether or not the server requires authentication.<br>Within the connection test it is checked whether the SMTP server requires SSL and authentication.<br>If the requirements are not consistent with the settings on the [Notification](./TriggerNotification.md) screen, an error message is shown.<br>Resolves raspi-cam-srv issue #42 [SMTP port issue](https://github.com/signag/raspi-cam-srv/issues/42)


## V2.10.4

### Bugfix

- Fixed function [Load Stored Configuration](./SettingsConfiguration.md) on the [Settings](./Settings.md) screen.<br>After execution of this function, values shown on the [Settings](./Settings.md) screen were only updated to the values loaded from the stored configuration after the page has been refreshed. <br>Resolves raspi-cam-srv issue #39 [load_config route assumes LiveStream2 exists (causes crash if non-existent)](https://github.com/signag/raspi-cam-srv/issues/39)

## V2.10.3

### Bugfixes

- Fixed function [Load Stored Configuration](./SettingsConfiguration.md) on the [Settings](./Settings.md) screen.<br>This function failed in cases when only a single camera is connected to a Raspberry Pi.<br>Resolves raspi-cam-srv issue #39 [load_config route assumes LiveStream2 exists (causes crash if non-existent)](https://github.com/signag/raspi-cam-srv/issues/39)

- Fixed [Switch Cameras](./Webcam.md#-switch-cameras-) on the [Web Cam](./Webcam.md) screen.<br>If working with two cameras, this function caused an error when [Triggered Capture of Videos and Photos](./Trigger.md), a [Photo Series](./PhotoSeries.md) or [Video Recording](./Phototaking.md#video) is currently active.<br>The user is now asked to stop either of these processes before switching cameras.

## V2.10.2

### New Features

- Added kernel version and Debian version to [Info](./Information.md) screen.

## V2.10.1

### Bugfix

- Fixed an issue with platform-specific search of tuning files.

## V2.10.0

### New Features

- Support of [Camera Tuning](./Tuning.md) by selection of alternate tuning files.<br>Resolves raspi-cam-srv issue #26 [NoIR camera settings](https://github.com/signag/raspi-cam-srv/issues/26)<br>**Note:** There is still an issue when streaming two cameras. (See Picamera2 Issue #1103 [Tuning file support not thread-safe?](https://github.com/raspberrypi/picamera2/issues/1103))

### Bugfixes

- Fixed error ```The browser (or proxy) sent a request that this server could not understand.``` which ocurred when pressing *Submit* in the [Control](./Trigger.md#control) tab of the [Trigger](./Trigger.md) menu.<br>Resolves raspi-cam-srv issue #27 [Trigger Control Submit make server error](https://github.com/signag/raspi-cam-srv/issues/27)

## V2.9.2

### Bugdixes

- Disallow changing parameters of a [Photo Series](./PhotoSeries.md) after it had already been started.

## V2.9.1

### New Feature

- [Photo Series](./PhotoSeries.md) can be downloaded (see [Downloading a Series](./PhotoSeries.md#downloading-a-series))

## V2.9.0

### New Features

- The [Photo Viewer](./PhotoViewer.md) has been enabled to download photos and to delete photos from the Raspberry Pi.

## V2.8.4

### Bugfixes
- When a [Sun-controlled Photo Series](./PhotoSeriesTimelapse.md) was started, it could happen that the series end was recalculated without considering the configured time periods.<br>Typically, this happened when the configured start time was earlier than the time when the series was actually started.<br>Because this end time was in many cases earlier than the start of the next time slot, the series may have immediately stopped when the next period started.<br>This is now fixed.
- In some cases when a series was finished because the configured end time has been reached, the background process did not stop and continued to produce photos with zero interval until the configured number of shots has been reached.
- When a [Photo Series](./PhotoSeries.md) was paused and continued afterwards, the **Current shots** was incremented without taking a photo with this number. Therefore **current shots** did not represent the real number of photos and the series would be stopped before reaching the configured **Number of shots**<br>Now, **Current shots** is only incremented if a photo has been taken.
- When the waiting time for the next shot in a [Photo Series](./PhotoSeries.md) is larger than 60 sec, RaspiCamSrv stops the camera and restarts it when the time is reached.<br>However, the restart requires 1.5 sec waiting time to allow the camera to collect statistics for auto-exposure algos.<br>Therefore, the phototaking is delayed by at least 1.5 sec with respect to the expected times.<br>This is now compensated.<br>The observed delay is now considerable smaller and ranges from ~0.2 sec for the first photo to ~0.04 sec for the next ones.

## Changes

- When a new [Photo Series](./PhotoSeries.md) is created, the start time is delayed by 1 minute with respect to the current time to give time for further configurations.

## V2.8.3

### Bugfix
- Fixed layout issues in screen [Settings](./Settings.md) for cases where **Show Histograms** and/or **Ext Motion Detection** are not supportet.

## V2.8.2

### Bugfix
- The Bugfix introduced in [V2.8.0](#v280) caused an error on systems like Pi Zero where modules cv2, matplotlib or numpy cannot be installed.<br>This error is now fixed.<br>If in your system the [Settings](./Settings.md) screen shows that **Ext. Motion Detection supported** is checked and in screen [Trigger/Motion](./TriggerMotion.md) the **Motion Detection Algorithm** list only shows "Mean Square Diff", you can try the following:<br>Edit file ```prg/raspi-cam-srv/raspiCamSrv/static/config/triggerConfig.json```<br>Remove the part highlighted in the following screenshot, if it exists:<br>![Fix282](./img/RN282_img1.jpg)

## V2.8.1

### Changes
- Removed alternate type hints in module sun.<br>These were introduced in Python 3.10.<br>However in Raspberry Pi Zero systems Python 3.9 is installed.

## V2.8.0

### New Features

- For [Photo Series](./PhotoSeries.md), the page [Timelapse Series](./PhotoSeriesTimelapse.md) now allows specification of up to two daily periods depending on sunrise and sunset.<br>Refers to [Discussion #21](https://github.com/signag/raspi-cam-srv/discussions/21).
- On the [Settings](./Settings.md) screen, new parameters for geographical latitude, longitude and elevation as well as a time zone selector have been added.<br>Non-zero settings for these parameters are required for using [Sun-controlled Photo Series](./PhotoSeriesTimelapse.md)

### Bugfixes
- For [Motion Detection](./TriggerMotion.md), the list of supported algorithms had shown only "Mean Square Diff", even if **Ext. Motion Detection supported** was activated in the [Settings](./Settings.md) screen.<br>Now all available algorithms can be selected and used if the modules cv2, matplotlib and numpy are installed on the system (see [RaspiCamSrv Installation](../README.md#raspicamsrv-installation), step 10)

## V2.7.1

### Bugfixes

- Images from a photo snapshot URL (see [Web Cam](./Webcam.md)) could not be saved using 'save as' from the context menu.   
The reason was that these images still contained the framing and mime type from MJPEG streaming.   
This is now fixed.   
This solves [raspi-cam-srv Issue #22](https://github.com/signag/raspi-cam-srv/issues/22)

## V2.7.0

### New Features

- For streaming access, it can now be configured in the [Settings](./Settings.md) screen whether authentication is required or not.   
The default is that authentication is not required, as before.   
This modification has been made for Feature Request [#20](https://github.com/signag/raspi-cam-srv/issues/20)

### Changes
- The default log level for libcamera was set to ERROR instead of WARNING in order to suppress V4L2 pixel format warnings.

## V2.6.3

### Bugfixes

- Fixed ```Error starting camera: main stream should be a dictionary``` which accurred at server start, if an active [Photoseries](./PhotoSeries.md) with *Photo Type* "raw+jpg" was configured to be *Continued on Server Start*.
- When a [Photoseries](./PhotoSeries.md) is automatically continued on server start/restart, previous versions did not allow seeing the live stream while the Photoseries was active. Now, if the photo series configuration is compatible with live stream configuration, you will see the live stream also after automatic continuation of the series.

## V2.6.2

### Bugfixes

- Fixed ```Exception: 'NoneType' object has no attribute 'get'``` which occurred when taking a video which requres exclusive camera access.     
The reason was that, while stopping the live stream, it was not recognized that video recording was intended. As a result, the camera was closed and access to the camera during video recording lead to this error.   
Refers to: [raspi-cam-srv Issue #18](https://github.com/signag/raspi-cam-srv/issues/18).
- Fixed ```AttributeError: 'NoneType' object has no attribute 'requestStop'``` which could occur after applying *Reset Server* in the [Settings](./Settings.md) screen.

### Changes

- For Raspberry Pi models lower than model 5 (Zero, 1, 2, 3, 4),    
the [Configuration](./Configuration.md) for *Photo* is initialized with the lowest *Sensor Mode*    
and the *Buffer Count* for *Video* is set to 2, identical with *Live View*.    
This makes all configurations compatible and allows for the Live Stream parallel to Video Recording, when using the default configuration.    
Refers to: [raspi-cam-srv Issue #18](https://github.com/signag/raspi-cam-srv/issues/18).

## V2.6.1

### Bugfixes

- With deactivated [Sync Aspect Ratio](./Configuration.md), the aspect ratio of different configurations was nevertheless synced. This is now fixed.
- When activating [Sync Aspect Ratio](./Configuration.md), after it was previously deactivated, all aspect ratios were set to the one of *Live View* and not to the currently selected configuration.
- When activating [Sync Aspect Ratio](./Configuration.md), after it was previously deactivated, ScalerCrop was not automatically updated.

## V2.6.0

### New Features

- [Zoom and Pan](./ZoomPan.md) has been completely reworked.   
It now takes regard of the [ScalerCrop](./ScalerCrop.md) specifics of Raspberry Pi cameras.    
This allows full control of image areas also for cases with extreme aspect ratios.    
**Note**: For cases where the height of the *Stream Size* is considerably larger than its width, the live stream in the [Live](./LiveScreen.md) screen may exceed the page height. This cannot currently be avoided without loosing the capability of graphical [focus](./FocusHandling.md#autofocus-windows) and [zoom](./ZoomPan.md#graphically-setting-the-zoom-window).
- The [Config](./Configuration.md) screen now has an option to synchronize aspect reatios of *Stream Size*s across all configurations.    
If this is activated and a non-standard aspect ratio is configured, for example, for the *Live View*, the *Stream Size*s for the other configurations will be adjusted to the same aspect ratio.    
Then the Live Stream will no longer be distorted because the camera system will select a *ScalerCrop* with the same aspect ratio.
- The [Info](./Information.md) screen in section [Camera x](./Information.md#camera-x) now shows the Sensor Mode in which the camera is currently operating if the camera is currently started.

### Changes

- Camera [Configuration](./Configuration.md#) for *Raw Photo* now allows *Custom* *Stream Size*.    
However, if a *Stream Size* is specified which does not correspond to the output_size of one of the cameras Sensor Modes, the camera will automatically select a suitable Sensor Mode and produce a .dng file with the corresponding size.    
The reason for this change was that the new option to automatically syncronize aspect ratios across configurations can lead to a *custom* *Stream Size* also for the *Raw Photo* configuration.
- The parameter *Stream Size aligned with Sensor Modes* in the [Configuration](./Configuration.md#) now dafaults to False.    
The reason for this change is that, when specifying identical *Stream Sizes* for *lores* and *main* streams, the camera could produce an error ```Error starting camera: lores stream dimensions may not exceed main stream``` because the automatic alignment might produce effective *Stream Sizes* which violate tis restriction.

### Bugfixes
- [Zooming](./ZoomPan.md) did not preserv image center


## V2.5.4

### Bugfixes

- Avoid ```Error starting camera: lores stream dimensions may not exceed main stream```   
Now, when specifying any [Camera Configuration](./Configuration.md), it is checked whether the specified *Stream Size* for the different use cases obey the restriction that stream size for 'lores' must be less than stream size for 'main' stream.    
If the restriction is violated, an error message is shown and the previous values are restored.
- In [Camera Configuration](./Configuration.md) for *Photo*, *Stream* could be changed to 'lores' in the dialog, but this change has not been stored. Now fixed
- Fixed: --- Logging error --- ... camera_pi.py", line 793, in clearConfig


## V2.5.3

### Bugfixes

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
- Error status for [Triggered Capture of Videos and Photos](./Trigger.md) which had been stored with [Store Configuration](./SettingsConfiguration.md) are now cleared if server is started with stored configuration

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

- Starting server with stored Configuration ([Settings](./SettingsConfiguration.md)) did not correctly set a previously configured [Zoom](./ZoomPan.md) (*ScalerCrop*). Instead, *ScalerCrop* was set to the active camera's pixel array size (see [raspiCamSrv Issue #7](https://github.com/signag/raspi-cam-srv/issues/7)). This was done only during initial system start and not after manually applying **Load Stored Configuration** in [Settings](./SettingsConfiguration.md).   
Now, the stored *ScalerCrop* is no longer overwritten, if a zoom (<>100%) has been explicitely applied ("include_scalerCrop": true in controls.json).


## V2.3.2

### Improvements

- Error handling has been improved. Server errors, also from background threads, are routed to the web client.   
This does not apply to errors occurring in encoders which are running in own threads. Exceptions thrown in these threads are currently not handled by **raspiCamSrv**.   
Error reasons are mostly invalid combinations of [Configuration](./Configuration.md) parameters, especially with *Stream Format*

### Bugfixes

- After applying **Swith Cameras** in page *Web Cam*, Title and metadata for the second camera were identical to those of the first camera.
- [Reset Server](./SettingsConfiguration.md) may have caused errors in streaming or other functions
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
- Streaming configurations for both cameras are stored together with the entire configuration (see [Settings](./SettingsConfiguration.md-storage)) and can be loaded on server restart.

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
