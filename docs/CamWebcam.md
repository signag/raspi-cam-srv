# Web Cam Access

[![Up](img/goup.gif)](./Cam.md)

**raspiCamSrv** enables webcam functionalities with Raspberry Pi cameras as well as with USB cameras.

For Pi 5 with two camera ports, both cameras can be streamed simultaneously.    
Alternatively, you can choose one of the connected USB cameras as *Active* or *Second* camera.

This page shows the URLS for MJPEG streaming as well as for photo snapshots:

![Webcam](./img/CamWebcam2.jpg)

The left side of the page always shows the active camera.   
If an additional camera is available, video stream and photo are shown on the right side.

When switching the cameras, either with the **Switch Cameras** button in [Multi-Cam](./CamMulticam.md) or by changing the camera in the [Settings](./Settings.md#switching-the-active-camera), the streams will be exchanged.   
The *video_feed* endpoint will always refer to the active camera, which is also shown in the title bar.    
The *video_feed2* endpoint will always refer to the other camera, if available.

The configuration and camera stream used for video and photo capture are indicated.

The links shown on the page open a new browser window.

## Video Stream

The video stream will always use the LIVE configuration.   
By default, this configuration uses the *lores* camera stream.   
The camera stream as well as its *stream size* can be configured in the [Configuration](./Configuration.md) screen.

## Photo Snapshot

For the photo snapshot, you can choose between using the [LIVE configuration](./Configuration.md), usually configured with the *lores* stream with low resolution and a snapshot using the [FOTO configuration](./Configuration.md), usually configured with the *main* stream with high resolution.

**NOTE**: Photo snapshots with high resolution assume an active live stream where the *lores* and the *main* streams of the camera are **simultaneously** configured (see [raspiCamSrv Tasks](./Background%20Processes.md)). 

If your [configurations](./Configuration.md) for LIVE and FOTO are incompatible (for example using a different *Colour Space* or when both use the *main* stream with different resolutions), the live stream will request exclusive camera access with only the LIVE configuration activated. In this case, the URL for the high resolution photo snapshot will return an image with the resolution configured for LIVE.

If the live stream is active at the time when the photo snapshot is triggered, the snapshot will be taken immediately.    
Otherwise, the live stream will be activated before the snapshot is taken. This requres starting the camera and giving it time to gather sufficient information for the auto-algorithms, which results in larger latency (1 to 1.5 sec).

