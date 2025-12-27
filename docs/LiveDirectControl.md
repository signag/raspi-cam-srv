# raspiCamSrv Live Direct Control

[![Up](img/goup.gif)](./LiveScreen.md)

This screen is opened by clicking on the [Live Stream area](./LiveScreen.md#accessing-the-direct-control-panel). It allows direct control of selected control parameters.   
Control parameters with numeric values are accessible if they have been activated on the [Camera Controls](./CameraControls.md) screens.    
When finished with parameter tuning, return to the [Live](./LiveScreen.md) screen or select any other menu option.

![DirctControl](./img/LiveDirectControl.jpg)

## Focal Distance

The slider for *Focal Distance* is mapped to a range from 0 to 1.

If you drag the slider to a value below the minimum focal distance, it will snap back to the minimum.

Scaling uses an x**3 behavior so that lower values can be selected with higher precision.

## Left and Right Sliders

The sliders for all parameters are mapped to a range from -1 to 1 with the default at 0, following an x**3 function:

![Scaling](./img/LiveDirectControlSlider.jpg)

Therefore, values closer to the default value can be selected with higher precision.

Because of the mapping, you will always see the same sliders, independently from the real value ranges which are significantly different for CSI and USB cameras and which can also vary between different USB camera models.

For some parameters, e.g. *Analogue Gain*, the default value is at the minimum of the parameter range.   
In this case, negative slider positions can not be set; the slider will snap back to 0.

## Zoom Factor

The slider for the *Zoom Factor* directly shows the *Zoom Factor* with linear scaling.

If you previously have selected a specific image region (Scaler Crop) with the [Zoom and Pan](./ZoomPan.md) dialog, the resulting *Zoom Factor* will be the maximum which ca be set with the slider. Selecting a larger value will always snap back to this maximum.

However, you can zoom into this area until the lowest zoom factor is reached.
