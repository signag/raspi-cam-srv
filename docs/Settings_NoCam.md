# raspiCamSrv Settings (No Camera)

[![Up](img/goup.gif)](./UserGuide_NoCam.md)

This is a variant of the general [Settings](./Settings.md) screen, which shows up when no camera is available.

Other sections focus on
- [Server Configuration](./SettingsConfiguration.md)
- [User Management](./SettingsUsers.md)
- [API Management](./API.md)
- [Versatile Buttons](./SettingsVButtons.md)
- [Action Buttons](./SettingsAButtons.md)
- [Devices](./SettingsDevices.md)

*Users* and/or *API* may be invisible, depending on context.

![Settings](img/Settings_no_cam.jpg)

The General Paramenters include

- *Use USB Cameras* This option is only visible if the system has detected at least one USB camera (see [Info](./Information.md)).   
Activating the checkbox will activate the connected cameras for **raspiCamSrv**.
- *Allow access through API* shows whether the installed libraries allow secure [API access](#api-access).<br>Also if it is supported, it can be deactivated.
- The geo-coordinates *Latitude*, *Longitute*, *Elevation* as well as the *Time Zone* are not currently used when there are no cameras.

## Enabling Use of USB Cameras

If this option is shown, **raspiCamSrv** has identified at least one USB camera, but currently this is not available.

If you enable use of USB cameras, the system will select one of the USB cameras as *Active Camera* and another one, if present, as *Second Camera*

The UI will then automatically switch to the mode with cameras ([Information](./Information.md))

## API Access

API access to **raspiCamSrv** is protected through JSON Web Tokens (JWT).<br>This requires the module ```flask_jwt_extended```, which is first used in **raspiCamSrv V2.11**.

If the upgrade to this version has been done without installing this module (see [Release Notes V2.11](./ReleaseNotes.md#v2110)), the system will show a hint
![SettingsAPI](./img/Settings_API_na.jpg)
and also hide the *API* section

In this case, the module can be installed (see [Release Notes V2.11](./ReleaseNotes.md#v2110)) and after the server has been restarted, it shows as 
![SettingsAPI](./img/Settings_API_a.jpg)
which now allows activating or deactivating API support.

If the setting is changed, it is necessary to

1. [Store the configuration](./SettingsConfiguration.md)
2. Make sure that the server is configured to [Start with stored Configuration](./SettingsConfiguration.md)
3. Restart the server (see [Update Procedure, step 4](./ReleaseNotes.md#update-procedure))

This will be indicated through the hint

![SettingsAPI](./img/Settings_API_change.jpg)
