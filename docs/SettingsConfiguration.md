# Settings / Server Configuration

[![Up](img/goup.gif)](./Settings.md)


The *Settings* screen includes a *Configuration* section with functions to control the **raspiCamSrv** configuration.

The list of *Unsaved Configuration Changes* lists all actions with their time of execution, which have been made during the current session and which have not yet been saved to the server.

![Configuration](./img/Settings_Config.jpg)

- Button *Store Configuration* generates a set of JSON files which include the entire configuration of the **raspiCamSrv** server (see [below](#server-configuration-storage)).<br>**NOTE**: This does not include [Photo Series](./PhotoSeries.md). These are persisted automatically and independently. It also does not include [Events](./TriggerActive.md).
- Button *Load Stored Configuration* replaces the current configuration with the previously stored configuration.<br>[Photo Series](./PhotoSeries.md) and [Events](./TriggerEventViewer.md) are not affected.<br>**NOTE**: If you had activated [API](./SettingsAPI.md) access before, this will be deactivated when the stored configuration is loaded. You need to restart the server to activate it again.
- Button *Reload Cameras* resets and reloads the entire camera configuration (see [Reloading Cameras](#reloading-cameras)). This fuction must be applied when USB cameras have been unplugged or new USB cameras plugged in while the server was active (hot plug). This will adjust the entire camera configuration to the new setup.<br>**NOTE**: Use this function **immediately** after unplugging a USB camera. Otherwise errors can occur when using other functions<br>**NOTE**: This has no effect when CSI cameras have been plugged in or out. This requires rebooting the Raspberry Pi, to be effective.
- Button *Reset Server* stops any background activity (live stream, video, photo series, motion capturing and event handling) and replaces the current configuration with the default configuration.<br>[Photo Series](./PhotoSeries.md) and [Events](./TriggerEventViewer.md) are not affected. Any associated resources remain unchanged. However, an active [Photo Series](./PhotoSeries.md) will be paused and needs to be continued.<br>**NOTE**: If you had activated [API](./SettingsAPI.md) access before, this will no longer be available when the configuration is reset.<br>The same applies to [Notification Settings](./TriggerNotification.md) which need to be reconfigured.<br>**NOTE**: If you had activated *Start Server with Stored Configuration*, this will be deactivated. Probably, you might want to store the new configuration bofore activating this again.
- *Start server with stored Configuration* controls whether a server start shall use the default configuration or the stored configuration.
- Button *Backup Stored Data*   
With this button, you can create a [backup](#backups) of all data currently stored in the file system.   
Before pressing the button, you need to enter a unique name for the backup.
- Button *Restore Backup*    
With this button, you can restore the selected backup.   
After restore is completed and confirmed by the status message, you need to restart the server with the *Restart Server* button.
- Button *Remove Backup*   
With this button, you can remove the selected Backup.
- Button *Restart Server*   
will restart the raspiCamSrv Flask server.    
The system will automatically detect whether the server was started as system unit, as user unit or from the command line.    
In the latter case, you are asked to stop the server manually.   
When the server restarts, the browser will lose connection.    
Press the browser's **Back** button until you see the recently used raspiCamSrv screen and then push any of the upper menu options to reconnect with the restored configuration.

#### Server Configuration Storage

When the configuration is stored with the *Store Configuration* button, a set of files is created/replaced in the ```raspi-cam-srv/raspiCamSrv/static/config``` folder:

![Config](./img/Settings_ConfigStore.jpg)

- _loadConfigOnStart.txt<br>This is just an empty marker file. If the file exists, the server will initiate its configuration with configuration data stored in the other files.<br>Otherwise, default configuration settings will be applied.
- cameraConfigs.json<br>This is currently not used
- cameraProperties.json<br>This file contains the camera properties of the actice camera, which are shown in [Camera Properties](./Information.md#camera-properties).<br>Camera properties are always read directly from the camera.
- cameras.json<br>This file contains the installed cameras with information shown in [Installed Cameras](./Information.md#installed-cameras)<br>Installed cameras are always directly queried from the camera system.
- controls.json<br>This file includes all the camera configuration settings as shown in the upper right part of the Live screen [Camera Controls](./LiveScreen.md#top-right-quarter)
- LiveViewConfig.json, photoConfig.json, rawConfig.json, videoConfig.json<br>contain the camera configuration settings for the different use cases as shown in the [Config screen](./Configuration.md)
- rawFormats.json<br>contain a list of formats which can be used for raw photos.<br>This information is extracted from the different [Sensor Modes](./Information.md#sensor-modes) and is always directly obtained from the camera system.
- serverConfig.json<br>This file includes configuration settings for the **raspiCamSrv** dialog system, such as information included in the [Settings](./Settings.md) dialog, or the configuration of the [Display Buffer](./LiveScreen.md#bottom-left-quarter) and some navigation details.
- streamingCfg.json contains, for each camera, the [Tuning](./Tuning.md) configuration, the [Live View Configuration](./Configuration.md) settings and the [Camera Controls](./CameraControls.md) which will be used for streaming. The included Video Configuration is stored because Picamera2 always requires the *main* stream to be configured. This will not be used for streaming.
- triggerConfig.json contains the configuration settings for triggered capture of videos and photos (motion capture)
- tuningConfig.json contains the settings maintained in the [Tuning](./Tuning.md) dialog

## Reloading Cameras

When the function **Reload Cameras** is applied, the system will 

1. [Detect](./Information.md#detection-of-cameras) the currently connected cameras
2. [Identify](./Information.md#identification-of-usb-cameras) USB cameras, if connected 
3. Then determine Camera Properties (e.g. model) and Sensor Modes for CSI and [USB](./Information.md#determining-camera-properties-for-usb-cameras) cameras.
4. Create a list of supported cameras, considering whether [Use of USB cameras is disabled](./Settings.md#disabling-use-of-usb-cameras).

Before applying the function the list of supported cameras may look like

| Num | Model                  | USB | Device      |
|-----|------------------------|-----|-------------|
| 0   | imx708                 | No  |             |
| 1   | imx219                 | No  |             |
| 2   | Logi 4K Stream Edition | Yes | /dev/video0 |
| 3   | C922 Pro Stream Webcam | Yes | /dev/video4 |

After remofing the *imx219* and unplugging the *Logi 4K*, the list will be: 

| Num | Model                  | USB | Device      |
|-----|------------------------|-----|-------------|
| 0   | imx708                 | No  |             |
| 1   | C922 Pro Stream Webcam | Yes | /dev/video4 |

When comparing the lists, the system will look for matching Num, Model, USB and Device.   
If one of these parameters differs, the camera with that number will be initialized based on the current Camera Properties and Sensor Modes. Any previously specified [Configuration](./Configuration.md) or [Controls](./CameraControls.md) will be reset to default values for the respective camera type.

In the example above, Camera 0 will keep their settings and Camera 1 will be reset.

## Backups

Backups preserve the currently stored data structures of **raspiCamSrv** so that they can be consistently restored later.

This includes:

- all [configuration data](#server-configuration-storage) stored under folder ```~/prg/raspi-cam-srv/raspi-cam-srv/static/config```
- all photos stored under folder ```~/prg/raspi-cam-srv/raspi-cam-srv/static/photos```
- all [photo series](./PhotoSeries.md#photo-series-in-the-file-system) stored under folder ```~/prg/raspi-cam-srv/raspi-cam-srv/static/photoseries```
- all [event data](./TriggerActive.md#event-data) stored under folder ```~/prg/raspi-cam-srv/raspi-cam-srv/static/events```
- The [Camera calipration photos](./CamCalibration.md#calibration-data-storage) for a [Stereo Camera System](./CamStereo.md) stored under folder ```~/prg/raspi-cam-srv/raspi-cam-srv/static/calib_photos```
- The Stereo Camera calibration parameters stored under folder ```~/prg/raspi-cam-srv/raspi-cam-srv/static/calib_data```
- The SQLite database with [User data](./Authentication.md) and [Event data](./TriggerActive.md#database) stored as ```~/prg/raspi-cam-srv/instance/raspiCamSrv.sqlite```

When a backup is created, all these data are stored underneath ```~/prg/raspi-cam-srv/backups/<backup-name>``` where ```<backup-name>``` is the name given to the backup:

![Backup](./img/Settings_Backup.jpg)