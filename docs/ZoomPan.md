# raspiCamSrv Zoom & Pan

[![Up](img/goup.gif)](./LiveScreen.md)

![ZoomAndPan](img/Zoom.jpg)

This tab allows zooming and panning the image area within the dimensions supported by the camera pixel array size.

## Current zoom factor in %

This value shows the current zoom factor.   
It cannot be modified manually but only through the **Zoom in**, **Zoom out** or **Full** buttons.

The value is given in % of the maximum pixel array size.

## Zoom & pan step in %

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

## Graphically setting the Zoom Window

Pushing the **Draw** button will switch into graphical mode where the zoom window can be drawn on a canvas over the Live Stream area.   
All other buttons, except **Full** will be disabled in this mode.

![ZoomGraphically](img/Zoom_Graph.jpg)

**Attention:** With Safari (e.g. on an iPad), due to the issue with onload events, the canvas will not be directly visible. It needs to trigger window resize by shortly 'pulling' down the window.

While drawing a rectangle for the intended image section, the original aspect ratio will be preserved.   
After drawing is finished, the *Current ScalerCrop (Zoom)* will be updated with offset and dimensions of the zoom window.

After pressing **Draw**, the button has changed to **Submit** which must be pressed in order to apply the ScalerCrop setting to the preview and store it for later photo or video taking.

Pressing **Submit** terminates the graphic mode.

When the **Full** button is pressed in the graphic mode, the dialog returns to normal mode without applying a previously drawn zoom window.

**Note:**   
Usually, **raspiCamSrv** starts with a 640x[width] live view with the aspect ratio of the pixel array size. This does not cover the entire sensor range.   
In order to see the full range in the live view, you need to select a sensor mode with a larger size in the [Live View configuration](./Configuration.md).
