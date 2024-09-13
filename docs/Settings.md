# raspiCamSrv Settings

[![Up](img/goup.gif)](./UserGuide.md)

This screen allows for some basic configurations, such as selecting the standard file types for photos, raw photos and videos.

Also the geo-coordinates and timezone, required for sun-calculations in [Sun-controlled Timelapse Photo Series](./PhotoSeriesTimelapse.md) need to be specified here.

![Settings](img/Settings.jpg)

## Switching the active Camera

On systems which allow connection of multiple cameras (e.g. Pi 5), it is possible to switch the active camera.   
Only non-USB cameras are offered for selection (see also [Information](./Information.md#cameras))

![Camera Switch](img/Settings_CamSel.jpg)

## Configuring Authentication for Streaming

It can be configured whether streaming of videos or photos requires authentication:

![Settings](img/Settings_Auth_Streaming.jpg)

- If the checkbox is not checked, the system allows access to video streams or photos for everybody without authentication.
- If the checkbox is checked, video streams or photos can only be accessed if a valid session is active.   
If a streaming URL is entered in a browser and there is no valid Flask session, the login screen is shown and, after having entered valid credentials, the [Live](./LiveScreen.md) screen is shown. Now, the desired streaming URL can be directly entered or selected from the [Web Cam](./Webcam.md) screen.   
A valid Flask session exists, if login has been passed once within an active browser instance, either in another tab of the browser window intended for streaming or within another window of the **same** browser.   
Closing all windows of a browser kills the session. 


## Activating / Deactivating Histograms

**raspiCamSrv** can show histograms for photos.   
Histograms are generated with [OpenCV](https://de.wikipedia.org/wiki/OpenCV).  
This requires that the packages OpenCV, numpy and matplotlib are installed (see [RaspiCamSrv Installation](../README.md#raspicamsrv-installation) Step 9)   


If these packages are installed, you can select whether or not to *Show Histograms*.   
The default on first server start is to show histograms.

It may be necessary on smaller systems (Raspberry Pi Zero W, Raspberry Pi Zero 2 W) to deactivate this option because of memory restrictions.   
If the option is deactivated, the modules are not loaded and histograms will not be displayed, even if all packages are installed.

The system will automatically detect whether or not the required packages are installed and accessible. If this is not the case, this will be indicated:

![NoHistograms](img/Settings_noHistogram.jpg)

## Extended Motion Detection Support

In all installations, [Motion Capturing](./TriggerMotion.md) with the *Mean Square Difference* algorithm are supported.

In order to also be able to use the extended algorithms, the following modules must be installed (see [Installation procedure, Step 10](../README.md#raspicamsrv-installation)):

- OpenCV
- numpy
- matplotlib

When the server starts up, it will be checked whether these modules can be imported.   
If the import had failed, this will be indicated on the Settings screen in the same way as for [Histograms](#activating--deactivating-histograms), above.   
Then, only the *Mean Square Difference* algorithm will be offered  for choice on the [Trigger/Motion](./TriggerMotion.md) tab.

## Recording Audio along with Video

### Preconditions

If a microphone, such as a USB microphone is connected to the Raspberry Pi, it is possible to record audio along with videos.

Picamera2 accesses the microphone through [PulseAudio](https://wiki.archlinux.org/title/PulseAudio).
PulseAudio daemons (```pulseaudio.socket``` and ```pulseaudio.service```) are running as [user units](https://wiki.archlinux.org/title/Systemd/User) and not as system units.

In order to access the microphone, **raspiCamSrv** needs to run in the user environment, too.   
This is automatically the case when the Flask service is directly started from the command line in the **raspiCamSrv** virtual environment with   
```flask --app raspiCamSrv run --debug --host=0.0.0.0```

Alternatively, **raspiCamSrv** can be configured as **user** service as described in [README](../README.md#service-configuration-for-audio-support)

### Configuration

**raspiCamSrv** will automatically detect whether a microphone is connected and accessible through PulseAudio.

If this is the case, the default microphone will be shown in the Settings screen:
![SettingsMic](img/Settings_microphone.jpg)    
Also the checkbox *Record Audio along with Video* is enabled for change.

If the checkbox is checked, audio will be recorded when a video will be recorded.

If no microphone is connected or the microphone is not accessible through PulseAudio (because **raspiCamSrv** runs as system service), this will be indicated as   
![SettingsMic](img/Settings_no_microphone.jpg)    
and the *Record Audio along with Video* checkbox is disabled.

Microphones can be plugged in/out without stopping the system. After a refresh of the *Settings* screen, the system will detect the changed setup.

If multiple microphones are plugged in, PulseAudio will automatically select a default microphone.   
If the selected microphone is not the intended one, plug it out temporarily. Pulse Audio will automatically select another default and keep it.


### Audio/Video Synchronization

Due to timing issues of audio and video subsystems, there may be a delay between video and audio.   
The discrepancy is typically in subsecond range.

Test videos should be made with something like a clapperboard. In case of delays, the *Audio Timeshift* value should be adjusted (it can be positive or negative) until video and audio are in sync.

### Server Configuration

The *Settings* screen includes a *Configuration* section with functions to control the **raspiCamSrv** configuration:

![Configuration](./img/Settings_Config.jpg)

- Button *Store Configuration* generates a set of JSON files which include the entire configuration of the **raspiCamSrv** server (see [below](#configuration-storage)).
- Button *Load Stored Configuration* replaces the current configuration with a previaously stored configuration.
- Button *Reset Server* stops any background activity (live stream, video, photo series) and replaces the current configuration with the default configuration.
- *Start server with stored Configuration* controls whether a server start shall use the default configuration or the stored configuration.

#### Server Configuration Storage

When the configuration is stored with the *Store Configuration* button, a set of files is created/replaced in the ```raspi-cam-srv/raspiCamSrv/static/config``` folder:

![Config](./img/Settings_ConfigStore.jpg)

- _loadConfigOnStart.txt<br>This is just an empty marker file. If the file exists, the server will initiate its configuration with configuration data stored in the other files.<br>Otherwise, default configuration settings will be applied.
- cameraConfigs.json<br>This is currently not used
- cameraProperties.json<br>This file contains the camera properties of the actice camera, which are shown in [Camera Properties](./Information.md#camera-properties).<br>Camera properties are always read directly from the camera.
- cameras.json<br>This file contains the installed cameras with information shown in [Installed Cameras](./Information.md#cameras)<br>Installed cameras are always directly queried from the camera system.
- controls.json<br>This file includes all the camera configuration settings as shown in the upper right part of the Live screen [Camera Controls](./LiveScreen.md#top-right-quarter)
- LiveViewConfig.json, photoConfig.json, rawConfig.json, videoConfig.json<br>contain the camera configuration settings for the different use cases as shown in the [Config screen](./Configuration.md)
- rawFormats.json<br>contain a list of formats which can be used for raw photos.<br>This information is extracted from the different [Sensor Modes](./Information.md#sensor-modes) and is always directly obtained from the camera system.
- serverConfig.json<br>This file includes configuration settings for the **raspiCamSrv** dialog system, such as information included in the [Settings](./Settings.md) dialog, or the configuration of the [Display Buffer](./LiveScreen.md#bottom-left-quarter) and some navigation details.
- streamingCfg.json contains, for each camera, the [Tuning](./Tuning.md) configuration, the [Live View Configuration](./Configuration.md) settings and the [Camera Controls](./CameraControls.md) which will be used for streaming. The included Video Configuration is stored because Picamera2 always requires the *main* stream to be configured. This will not be used for streaming.
- triggerConfig.json contains the configuration settings for triggered capture of videos and photos (motion capture)
- tuningConfig.json contains the settings maintained in the [Tuning](./Tuning.md) dialog
