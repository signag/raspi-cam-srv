
## Feature Overview V4.2.0

For more details, see the [User Guide](./UserGuide.md).    

![Live Overview](./img/Live.jpg)

- The [Live screen](./LiveScreen.md) shows a live stream of the active camera and allows individually selecting and setting all [camera controls](./CameraControls.md) supported by Picamera2.
- The **live stream** (MJPEG stream) can also be directly accessed through the endpoint ```http://<server>:<port>/video_feed```.   
It can be configured whether or not authentication is required.
- Web access to photo snapshots is achieved through the URL ```http://<server>:<port>/photo_feed```.   
The setting for necessity of authentication applies also to photo snapshots.
- For systems with 2 Raspberry Pi cameras (currently Pi 5) both cameras can stream and record simultaneously.    
The non-active camera stream and photo can be accessed through endpoints ```http://<server>:<port>/video_feed2``` and ```http://<server>:<port>/photo_feed2```, respectively.
- The second camera can be used in parallel to the active camera for taking photos, raw photos and videos.<br>(Sound recording with videos is restricted to the active camera)
- The second camera can be controlled through the [API](./API.md) as well as through the [Multi-Cam](./CamMulticam.md) dialog.
- Support of USB cameras with seamless integration with CSI cameras (only if OpenCV is installed)
- Hot plug-in/-out of USB cameras without server restart
- [Digital Pan / Tilt / Zoom](./ZoomPan.md) is also available for USB cameras
- [Camera Controls](./CameraControls_UsbCams.md) are also available for USB cameras 
- The server can be used without connected cameras for controlling [GPIO devices](./SettingsDevices.md) with the [Event handling system](./Trigger.md) or from the [Console](./Console.md)
- Photo taking and video recording can be started synchronously with both cameras.- Clients which are currently streaming through **raspiCamSrv** are shown on the [Info Screen](./Information.md#streaming-clients) together with their IP address and the streams they are using.
- [Stereo Vision](./CamStereo.md) allows generation of 3D videos and depth maps
- [Camera Calibration](./CamCalibration.md) supports calibration of a stereo-camera pair as well as rectification based on [OpenCV](https://opencv.org/)
- Support of [Tuning](./Tuning.md) by selection and management of tuning files.
- Triggered capture of videos and photos (see [Triggered Capture of Videos and Photos](./Trigger.md)) with motion detection
- Support for interaction with GPIO-connected devices based on the [gpiozero](https://gpiozero.readthedocs.io/en/stable/index.html) library. All basic input and output devices provided by *gpiozero* are supported and can be configured in the [Settings / Devices](./SettingsDevices.md) dialog. In addition, also support for [Stepper Motor](./gpioDevices/StepperMotor.md) is provided.
- State tracking and calibration for output [Devices](./SettingsDevices.md) available for [StepperMotor](./gpioDevices/StepperMotor.md)
- Events occurring on Input [Devices](./SettingsDevices.md), such as sensors or buttons, can be configured as [Triggers](./TriggerTriggers.md) for the execution of [Actions](./TriggerActions.md). Various actors, such as LEDs, buzzers, motors and servos can thus be integrated. All this integrates well with available functionality of the camera system.
- [Event Handling](./Trigger.md#event-handling-infrastructure) fully integrates Camera with GPIO-connected devices 
- Besides [Trigger](./TriggerTriggers.md)-based [Action](./TriggerActions.md) execution, actions can also be envoked through flexibly configurable [Action Buttons](./ConsoleActionButtons.md).
- [Event viewer](./TriggerEventViewer.md) with calendar overview
- Notification on captured events by e-Mail (see [Notification](./TriggerNotification.md))
- [Extended Motion Capturing Algorithms](./TriggerMotion.md) are available, including [Frame Differencing](./TriggerMotion.md#test-for-frame-differencing-algorithm), [Optical Flow](./TriggerMotion.md#test-for-optical-flow-algorithm) and [Background Subtraction](./TriggerMotion.md#test-for-background-subtraction-algorithm)
- The [Extended Motion Capturing Algorithms](./TriggerMotion.md) can be run in a testing mode, showing live views of intermediate image processing results which can help for a better understanding of the algorithms and adjustment of their variable parameters.
- For cameras with focus control (camera 3), it is also possible to graphically draw autofocus windows and trigger the autofocus to measure the LensPosition which is translated into a focal distance (see [Focus handling](./FocusHandling.md)).
- For zooming, the intended image section can be [drawn graphically](./ZoomPan.md#graphically-setting-the-zoom-window) on the live stream area.
- Photos, raw photos and videos can be taken, which are shown in the lower part of the [Live screen](./LiveScreen.md) together with their metadata or alternatively with their histogram (see [Photo taking](./Phototaking.md)).
- Videos can be recorded along with audio if a microphone (e.g. USB microphone) is connected to the Raspberry Pi (see [Recording Audio along with Video](./Settings.md#recording-audio-along-with-video))
- "Intelligent" camera control supporting simultaneous camera access from different tasks as long as the requested configurations are compatible (see [raspiCamSrv Tasks and Background Processes](./Background%20Processes.md)).   
This includes a continuous live stream while taking photos, videos or photo series.   
- For raw photos and videos, a jpeg placeholder is shown
- The photos taken may be added to a display buffer for inspection of photos and metadata and for comparison (see [Photo Display](./Phototaking.md#photo-display))
- On the [Config screen](./Configuration.md), camera configurations can be specified for four different use cases (Live View, Photo, Raw Photo and Video). These will be applied together with the selected controls when photos or videos will be taken. The *Live view* configuration will also be immediately applied to the Live stream.
- When modifying [Stream Sizes](./Configuration.md#stream-size-width-height) to non-standard aspect ratios, an option can assure that this is syncronously done for all camera configurations, so that Live Stream, Photos, Raw Photos and Videos have all the same aspect ratio and are not distorted.
- The [Info screen](./Information.md) shows the installed cameras, and, for the active camera, the camera properties as well as the available sensor modes.
- The [Photos screen](./PhotoViewer.md) allows scrolling through all available photos and videos with detail views of selected items.
- This screen allows also photo/video download and deletion.
- With the [Photo Series](./PhotoSeries.md) screen, different kinds of photo series ([Timelapse Series](./PhotoSeriesTimelapse.md), [Exposure Series](./PhotoSeriesExp.md), [Focus Stacks](./PhotoSeriesFocus.md)) can be configured, executed and monitored during their progress.
- For [Timelapse Series](./PhotoSeriesTimelapse.md), it is possible to define active periods depending on sunrise and sunset.
- The [Photo Series](./PhotoSeries.md) screen allows also to persist specific [Camera Configurations](./Configuration.md) together with [Camera Controls](./CameraControls.md) in the file system for later reuse.
- Photo Series can be set to be [automatically continued](./PhotoSeries.md#series-configuration) on server start if they had been interrupted by a server stop or system shutdown or reboot.
- On the [Console](./Console.md), configurable buttons allow execution of arbitrary OS commands and scripts including restart of the Flask service or reboot of the Raspberry Pi.
- The [Settings screen](./Settings.md) allows a few configuration settings such as selection of the active camera as well as selecting the type of photos, raw photos and videos in the range supported by Picamera2
- The Settings screen includes also functions to control the **raspiCamSrv** [Server Configuration](./SettingsConfiguration.md).<br>The entire configuration can be persisted or loaded from stored configuration files.
- It is also possible to configure the server to use the persisted configuration on server startup.
- Access to the server requires [registration and authentification](./Authentication.md).
- Generator for executable Python code including the entire interface to Picamera2 of a **raspiCamSrv** session.   
(See [Generation of Python Code for Camera](./Troubelshooting.md#generation-of-python-code-for-camera))
- The [raspiCamSrv API](./API.md) allows integration of the Raspberry Pi cameras with automated systems allowing these to take photos, start/stop video recording, start/stop motion detection, switching cameras and query status information.<br>Server access to the API endpoints is protected through JSON Web Tokens (JWT).

**New in V4.2**

- [Regions of Interest / Regions of NO Interest](./TriggerMotion.md#regions-of-interest-and-regions-of-no-interest) can be specified for [Motion Detection](./TriggerMotion.md).
- [Backup and Restorage](./SettingsConfiguration.md) of configuration and other stored data.



## Known Issues

- In **Safari** (e.g. on an iPad), there is still an issue with the Live Screen:    
 Due to the specific timing of the onload event, [AF Windows](./FocusHandling.md#autofocus-windows) may not be visible immediately after the page has been loaded. If you just 'pull' the entire window down for a short time (don't touch the AF Windows canvas), they will show up.   
 If the Live stream does not show up (e.g. after visiting another screen), take a photo and then push **Hide**/**Show**. This will show the live stream.
 - There may be an issue configuring specific sensor modes or stream sizes for the *Live View* in [Config](./Configuration.md). As a result, the live view will not show up and the server log will show an exception. You may need to reset the server (see [Reset Server](./SettingsConfiguration.md))<br>This is already fixed but may not yet be available in your environment (see [picamera2 Issue #959](https://github.com/raspberrypi/picamera2/issues/959))

## Limitations
The software is still being tested and extended.

- Hot plug of CSI cameras is not supported. This will require rebooting the Raspberry Pi (Hot plug of USB cameras is supported).
- Hot plug of USB cameras is possible but requires to [Reload Cameras](./SettingsConfiguration.md#reloading-cameras).     
Hot plug-out of a USB camera should be avoided when the camera is active. This will produce exceptions.
- Although the layout is responsive, it may not be "good-looking" with all sizes of browser windows

## Credits
- Most technical information on Picamera2 (<https://github.com/raspberrypi/picamera2>) has been taken from the [Raspberry Pi - The Picamera2 Library](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf) document.
- The implementation of live streaming with Flask has been inspired by <https://blog.miguelgrinberg.com/post/video-streaming-with-flask>
- The detailed solution for the mjpeg_server is based on the example [mjpeg_server.py](https://github.com/raspberrypi/picamera2/blob/main/examples/mjpeg_server.py) of the [picamera2 repository](https://github.com/raspberrypi/picamera2)
- The solution for drawing on the canvas for definition of AF Windows has been inspired by <https://codepen.io/AllenT871/pen/GVyXKp>
- The [Extended Motion Capturing Algorithms](./TriggerMotion.md) are based on work done by Isaac Berrios, published under [Introduction to Motion Detection: Part 1 - 3](https://medium.com/@itberrios6/introduction-to-motion-detection-part-1-e031b0bb9bb2)   
The algorithm code has been taken from this source as well as its [GitHub Repository](https://github.com/itberrios/CV_projects/tree/main/motion_detection) and integrated into the **raspiCamSrv** environment.
- raspiCamSrv uses the [gpiozero](https://gpiozero.readthedocs.io/en/stable/index.html) library for interfacing GPIO-connected devices.
