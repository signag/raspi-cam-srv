# Camera Controls for USB Cameras

[![Up](img/goup.gif)](./CameraControls.md)


**raspiCamSrv** supports a limited set of controls for USB Cameras:

- Switch between auto focus and manual focus
- Adjustment of focal distance
- Zoom, pan, tilt
- Enabling/disabling automatic white balance
- Adjusting the color temperature in case of manual white balance
- Adjusting the sharpness
- Adjusting the contrast
- Adjusting color saturation
- adjusting brightness

Whereas zoom/pan/tilt, as well as horizontal and vertical flipping, is controlled through OpenCV by modifying each individual frame delivered by the camera, the other controls are affected through the V4l2 (Video for Linux) interface to the camera.

Every camera advertises the supported controls along with the related range of valid values.   
This information is [queried from the USB camera](./Information_Cam.md#determining-supported-controls) while **raspiCamSrv** initializes the camera information.

The list of supported controls as well as their minimum, maximum, step and default values are used tho customize the individual controls screens to the currently active camera.

### Focus Handling USB Cameras

![Focus USB](./img/Focus_USB.jpg)

### Image Control USB Cameras

![Image](./img/Image_USB.jpg)

In these dialogs, the input fields have value ranges and defaults appropriate for the active camera type.   
Value ranges and default values are also visible in the tooltips.

### Applying Controls to USB Cameras

The supported controls ara applied to USB cameras through v4l2 commands, such as:

```v4l2-ctl --set-ctrl=contrast=50```
