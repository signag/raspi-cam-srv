
# Features V4.6.x

[![Up](img/goup.gif)](./index.md)

For more details, see the [User Guide](./UserGuide.md).    

![Live Overview](./img/Live.jpg)

## Feature Overview

### Platform Support

- raspiCamSrv can be run on all currenly known Raspberry Pi **hardware platforms** (except microcontroller boards) from Raspberry [Pi Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero-w/) to [Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/)
- Supported **Operating Systems** are the **Raspberry Pi** OS versions Bullseye, Bookworm and Trixie.
- The recommended variant for all of these is the full 64-Bit variant recommended by [**Raspberry Pi** Imager](https://www.raspberrypi.com/software/)


### Camera Support

- raspiCamSrv supports the currently available [Raspberry Pi Cameras](https://www.raspberrypi.com/documentation/accessories/camera.html).
- **NEW**: With the [Raspberry Pi AI Camera](https://www.raspberrypi.com/documentation/accessories/ai-camera.html) (imx500), you can study inference of neural network models for specific tasks (Classification, Object Detection, Pose Estimation, Segmentation) within the Web UI of **raspiCamSrv** (see [AI Camera Support](./AiCameraSupport.md)).
- CSI Cameras from other providers can be used as long as they are supported by Picamera2.
- USB cameras connected through the Pi's USB ports are seamlessly integrated, however control options are limited, depending on their capabilities.

### Camera Management

- raspiCamSrv can detect and use all **CSI** and **USB** cameras connected to a Raspberry Pi, as long as they are identified by Picamera2, which is usually the case.
- One of these cameras must be selected as *Active Camera*.    
[Camera configuration](./Configuration.md) (e.g. stream size colour space or flipping) as well as [controls](./CameraControls.md) (e.g. focus, zoom/pan/tilt, exposure- and image-control) can be actively modified only for the *Active Camera*.
- Another camera, if available, can be selected as *Second Camera* by [Multi Camera Control](./CamMulticam.md).
- All settings for the *Active Camera* can be preserved before it is replaced by another camera (e.g. by switching cameras). They will be restored/applied when this camera is set as *Active Camera* or as *Second Camera*.
- Function [Reload Cameras](./SettingsConfiguration.md) allows hot plug-in/-out of USB cameras without server restart

### Camera Configuration

- raspiCamSrv supports all [camera configuration options](./Configuration.md#configuration-tab) which are foreseen by Picamera2.
- Individual configuration sets can be specified for 4 different use-cases: Live View, Photo, Raw Photo and Video.
- Before the camera is started, raspiCamSrv configures all three camera streams (lowres, main, raw) for the most likely use-cases. This allows to keep the live stream (lowres) active while the camera is being used for phototaking (main), raw photo taking (raw) or video recording (main)
- If necessary, specific applications can request the camera for exclusive use.
- Support of Camera [Tuning](./Tuning.md) by selection and management of tuning files.

### Camera Control

- raspiCamSrv supports all [Camera Control options](./CameraControls.md) foreseen by Picamera2.
- [Focus control](./FocusHandling.md) if supported by the camera (e.g. camera module 3 or specific USB cameras).
- Graphically drawing *Autofocus Windows* for CSI cameras.
- [Pan / Tilt / Zoom](./ZoomPan.md) for CSI as well as for USB cameras.
- [Auto Exposure Control](./CameraControls_AutoExposure.md) for CSI cameras.
- [Exposure Control](./CameraControls_Exposure.md) for CSI cameras.
- [Image Control](./CameraControls_Image.md) for CSI cameras as well as for USB cameras (if supported by the camera).
- Panel for [Direct Control](./LiveDirectControl.md) of numeric control parameters.

### Photo Taking / Video Recording

- Taking [Photos / Raw Photos](./Phototaking.md).
- Recording [Video](./Phototaking.md#video).
- Recording [Audio along with the Video](./Settings.md#recording-audio-along-with-video).
- Photo/Video [metadata](./Phototaking.md#metadata) display.
- Photo [histogram](./Phototaking.md) generation and display.
- [Display buffer](./Phototaking.md#photo-display) for comparison of photos and metadata/histogram.
- [Photo Viewer](./PhotoViewer.md)
- [Photo Download](./PhotoViewer.md)
- Photos/videos are enabled for being inspected in a separate [Media Viewer](./UserGuide.md#media-viewer) window.

### Streaming

- Endpoint for [streaming](./CamWebcam.md) (MJPEG) the active camera.
- Endpoint for [streaming](./CamWebcam.md) the second camera.
- Endpoints for photo snapshots of active and second camera with low resolution.
- Endpoints for photo snapshots of active and second camera with high resolution.
- Option for activating / deactivating authentication for streaming and snapshots.

### Multi-Camera Features

- [Selection](./CamMulticam.md) of *Active Camera* and *Second Camera* out of connected CSI and USB cameras.
- [Simultaneous streaming](./CamWebcam.md) of both cameras.
- [Simultaneous photo taking or video recording](./CamMulticam.md#buttons) for both cameras.
- [Camera switch](./CamMulticam.md#switch-cameras).
- [Preserving active camera configuration and controls](./CamMulticam.md#configuring-mjpeg-stream-and-jpeg-photo) for later reuse.
- [Stereo vision support](./Settings.md#activating-and-deactivating-stereo-vision) for two cameras of same model.
- [Synchronization of settings](./CamMulticam.md#synchronize-configurations) for stereo cameras
- [Camera calibration](./CamCalibration.md) for stereo cameras.
- [Depth Maps](./CamStereo.md#depth-maps)
- [3D Video](./CamStereo.md#3d-video)

### Photo Series

- [Definition of Photo Series](./PhotoSeries.md) (# shots, interval etc.).
- [Control of Photo Series](./PhotoSeries.md) (start, stop, pause, resume).
- [Download of Photo Series](./PhotoSeries.md).
- [Timelapse Series](./PhotoSeriesTimelapse.md) with optional sunrise/sunset restrictions.
- [Exposure Series](./PhotoSeriesExp.md) with varying exposure time or gain (ISO).
- [Exposure Series Result](./PhotoSeriesExp.md#result) showing histograms.
- [Focus Stack Series](./PhotoSeriesFocus.md) iterating through a range of focus settings.
- Capability for [auto restart](./PhotoSeries.md#series-configuration) of series when Server or Raspi is restarted.

### Motion Detection

- [Scheduled Detection of Motion](./TriggerActive.md).
- Support for [different algorithms](./TriggerMotion.md) for motion detection.
- [Adjustable Sensitivity](./TriggerMotion.md) for motion detection.
- Support for [Regions of Interest](./TriggerMotion.md#regions-of-interest-and-regions-of-no-interest).
- Support for [Regions of NO Interest](./TriggerMotion.md#regions-of-interest-and-regions-of-no-interest)
- [Test Mode for Motion Detection](./TriggerMotion.md#testing-motion-capturing).

### GPIO Device Management

- Configuration of [GPIO Devices](./SettingsDevices.md).
- [Testing](./SettingsDevices.md#testing-a-device) of GPIO Devices
- [Device Calibration](./SettingsDevices.md#calibrating-a-device) for devices which rquire state tracking (e.g. stepper motor)
- Device control through [gpiozero](https://gpiozero.readthedocs.io/en/stable/index.html)
- All gpiozero device types are supported in raspiCamSrv
- Own device types can be added by [configuration](./SettingsDevices.md#device-type-configuration) (see [Stepper Motor](./gpioDevices/StepperMotor.md))

### Event Handling - Triggers and Actions

- [Configuration of Triggers](./TriggerTriggers.md)
- Triggering by [GPIO Input Devices](./SettingsDevices.md) (button, sensors)
- Triggering by [Motion Detection](./TriggerMotion.md)
- Triggering by Camera events (photo taken, video start, video stop)
- [Configuration of Actions](./TriggerActions.md)
- Actions by [GPIO Output Devices](./SettingsDevices.md) (LED, buzzer, servo, motor)
- Actions by Camera (take photo, start/stop video)
- [Camera Actions](./TriggerCameraActions.md) in case of motion detection (video duration, photo burst)
- [Notification](./TriggerNotification.md) actions (mail, mail attachments)
- [Action-to-Trigger Association](./TriggerTriggerActions.md)
- [Event Viewer](./TriggerEventViewer.md#events)
- [Event Calendar](./TriggerEventViewer.md)
- [Detailed Event Information](./TriggerEventViewer.md#events)
- Event Photos / Videos with motion detection frame
- Event Photos / Videos with RoI RoNI

### Console Functions

- Freely configurable [Array of Versatile Buttons](./ConsoleVButtons.md)
- Freely configurable [Array of Action Buttons](./ConsoleActionButtons.md) for execution of configured [Actions](./TriggerActions.md).

### API

- Selected functions of raspiCamSrv are accessible through specific [Web Service End Points](./API.md)
- API access is secured through JSON Web Tokens (JWT).
- A Postman collection is available for testing
- A specific API (probe) is available for 'probing' attribute values of raspiCamSrv live objects.

### Privacy Protection

- raspiCamSrv access requires registered [users](./Authentication.md)
- The Superuser can manage other users: create, remove, reset password
- Login requires a password
- For streaming, it is possible to disable the necessity of authentication
- API access is secured through JSON Web Tokens (JWT).
- Secrets (mail account, JWT secret key) are held in a separate secrets store which is not part of the persisted configuration data.

### Configuration Management

- Configuration Management refers to the way how raspiCamSrv handles its operational data which may be modified during user sessions.
- [On request](./SettingsConfiguration.md), all data of the raspiCamSrv server can be [persisted as JSON files](./SettingsConfiguration.md#server-configuration-storage)
- Optionally, the server can start with the stored configuration or with an initialized setup.
- An [indicator](./UserGuide.md#elements) shows when configuration data have been modified during a session.
- All modifications, which have not yet been saved, are [listed in a dialog](./SettingsConfiguration.md).
- You can create backups of entire configuration sets and restore them at another time.

### System Information

- Information on the Raspberry Pi System, the raspiCamSrv software stack and the connected cameras is shown on the [Info / Installed Cameras](./Information.md#installed-cameras) screen.
- [Properties of the Active Camera](./Information.md#camera-properties) are also shown.
- In addition, the Info Menu provides also details for the individual [Sensor Modes](./Information.md#sensor-modes) of the *Active Camera*.

### No Camera

- raspiCamSrv can operate in a special mode when [no camera is connected](./UserGuide_NoCam.md).
- In this case, all camera-related features are invisible.
- Functions which do not require a camera, remain available: [GPIO devices](./SettingsDevices.md), [Event Handling](./Trigger.md), [Console](./Console.md).

### Supervision

- For error analysis, [Logging](./Troubelshooting.md#logging) can be activated on module level.
- In order to inspect the interface of raspiCamSrv with Picamera2, it is possible to activate [Generation of Python Code for the Camera](./Troubelshooting.md#generation-of-python-code-for-camera). This will create an executable Python file including all Picamera2 calls.



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
