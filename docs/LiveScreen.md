# raspiCamSrv Live Screen

[![Up](img/goup.gif)](./UserGuide.md)

The **Live** screen is the central part of the application.   
After photos or videos have been taken in the current session, its layout is as shown below:

![Live Screen](img/Live0.jpg)

## Layout

### Top Left Quarter
This is the area where a Live stream is shown, except for phases when videos are recorded and when [Configuration](./Configuration.md) for Live View and Video are not compatible..

### Top Right Quarter
This area allows selecting and configuration of all [Camera Controls](./CameraControls.md) supported by Picamera2. These are parameters which affect the characteristics of images and outputs of the camera and which can be modified while the camera is running.   
The menu row of this section groups the controls into several categories.

### Bottom Left Quarter
The bottom part of the screen is only shown if a Photo or video has been taken within the server's life time and if the user did not decide to hide this area.

The bottom left quarter presents function buttons for [Photo/Video taking](./Phototaking.md)   
In addition, there are also buttons controlling the photo buffer to which users can add or remove individual photos and navigate between them.

Raw photos or videos are not shown directly. Instead a placeholder in the configured photo format is shown.

### Bottom Right Quarter
Here, the metadata of the currently visible photo/video are shown.
The metadata are captured within the same **Capturing Request** together with the photo itself.   
In the case of videos, the metadata are captured immediately before recording starts.

Alternatively to metadata, the histogram of the photo can be shown.

## Accessing the Direct Control Panel

For fine tuning all numeric control parameters (e.g. *Focal Distance*, *Zoom Factor*, *Contrast*, etc.), you can use the [Direct Control Panel](./LiveDirectControl.md).

When hovering with the mouse over the Live Stream area, you will get a hint:

![Direct Control hint](./img/LiveDirectControlOpen.jpg)

Before clicking on the Live Stream, you will need to activate those control parameters which you want to adjust:

- [Focal Distance](./FocusHandling.md)
- [Zoom Factor](./ZoomPan.md) (does not require activation)
- [Exposure Time](./CameraControls_Exposure.md)
- [Exposure Value](./CameraControls_Exposure.md)
- [Analogue Gain](./CameraControls_Exposure.md)
- [Colour Gain](./CameraControls_Exposure.md)
- [Sharpness](./CameraControls_Image.md)
- [Contrast](./CameraControls_Image.md)
- [Saturation](./CameraControls_Image.md)
- [Brightness](./CameraControls_Image.md)

Some of these parameters might not be available if the Active Camera is a USB camera.

Furthermore, if you want to restrict to a specific image section, you need specify this on the [Zoom](./ZoomPan.md) window first.   
The [Direct Control Panel](./LiveDirectControl.md) allows only zooming into that window but not changing the window itself.
