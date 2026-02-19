# Cam - Camera Usage

[![Up](img/goup.gif)](./UserGuide.md)

![Cam Menu](img/CamMenu.jpg)

This menu gives access to the available high-level camera usage scenarios, in particular in the case of multiple cameras connected to a Raspberry Pi (currently only Pi 5 can connect two CSI cameras).

When connecting USB cameras, in addition to CSI cameras, you can in principle, get access to as many cameras as you can connect. However, raspiCamSrv can only operate up to 2 cameras simultaneusly. 

So, you will need to select which of the connected cameras (see [Info/Cameras](./Information_Cam.md)) shall be used as *Active Camera* and as *Second Camera*.

- The [Web Cam](./CamWebcam.md) dialog demonstrates how to stream video or image from your cameras.
- The [Multi-Cam](./CamMulticam.md) dialog allows controlling both cameras individually or synchronously.     
(This dialog is only available for multi-camera systems)
- The [Camera Calibration](./CamCalibration.md) dialog can be used for calibration and rectification of stereo cameras.    
(This dialog is only available if *Stereo Vision* is activated in the [Settings](./Settings.md#activating-and-deactivating-stereo-vision) dialog)
- The [Stereo-Cam](./CamStereo.md) dialog can be used for visualization of depth maps as well as for viewing and recording of 3D videos.      
(This dialog is only available if *Stereo Vision* is activated in the [Settings](./Settings.md#activating-and-deactivating-stereo-vision)) 