# raspiCamSrv Zoom & Pan

![ZoonAndPan](img/Zoom.jpg)

This tab allows zooming and panning the image area within the dimensions supported by the camera pixel array size.

## Current zoom factor in %

This value shows the current zoom factor.   
It cannot be modified manually but only through the **Zoom in**, **Zoom out** or **Full** buttons.

The value is given in % of the maximum pixel array size.

## Zoon & pan step in %

This value can be adjusted.   
It specifies the step size by which every click on **Zoom in** or **Zoom out** will change the *Current zoom factor*.

## Current ScalerCrop (Zoom)

This rectangle, given in pixels, shows the visible area for cases where resolutions (see [Configuration](./Configuration.md)) are chosen which exceed these limits.

The rectangle is given as tuple (x_offset, y_offset, width, height).

## Current ScalerCrop (Live View)

This shows the scaler crop rectangle which is currently active for the live view and which can be set in the [Configuration](./Configuration.md).

Often, the live stream shows only a smaller window compared to the sensor's pixel array size.   
Therefore, zooming in may not be immediately seen in the live view as long as the *Current ScalerCrop (Live View)* is inside the *Current ScalerCrop (Zoom)* area. 

The *Current ScalerCrop (Live View)* is the base for determining offset and size of the *Autofocus Windows* when drawing rectangles on the canvas (see [Focus](./FocusHandling.md)).