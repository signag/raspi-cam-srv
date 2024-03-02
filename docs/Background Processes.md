# raspiCamSrv Tasks and Background Processes

[![Up](img/goup.gif)](./UserGuide.md)

The figure below gives an overview of the different tasks available in **raspiCamSrv** and their relation to **raspiCamSrv** [Configurations](./Configuration.md) and camera strams.   
For more information on the components, see the [Picamera2 manual](./picamera2-manual.pdf), chapter 4.2.

![stream usage](./img/CameraStreamUsage.jpg)

The tasks marked in green are executed in background processes (Threads) and may run simultaneously.

The status of each of these processes is indicated with [status indicators](./UserGuide.md#process-status-indicators):

![Status Indicator](./img/ProcessIndicator4.jpg)


## Default Configuration

The association between **raspiCamSrv** [Configurations](./Configuration.md) and camera streams shown in the figure above, is the default configuration.

In addition, default values for other configuration parameters are harmonized in such a way that all background processes can run simultaneously.   
This is especially important for the live stream which will remain active while a video is recorded, while photos are taken or while a Photo Series is executed.

**raspiCamSrv** merges the different configurations to a single one which is applied when the camera is started.

This requires that the following configuration parameters must have the same values for the different configurations:

- *Transform*
- *Colour Space*
- *Queue*

The values for *Buffer Count* can be different. In the merge process, the largest number of buffers will be selected.

## Configuration Changes

All configuration scan be changed, including the association between configuration and camera stream (except raw).

If a configuration change, for example Transform, is made for a single configuration, for example *Video*, it is no longer possible to use a common configuration for all tasks.   

If then, for example, a video is recorded, the video thread needs to run in exclusive mode because it cannot share configuration with the Live Stream. For this purpose:

1. The Live Stream must be stopped and paused during video recording
2. The Encoder for the Live Stream must be stopped
3. The camera must be stopped
4. The camera must be configured with the Video configuration
5. The camera must be started
6. The encoder for video must be started while the video is being recorded
7. The encoder must be stopped when video recording is finished
8. The camera must be stopped
9. The camera must be configured for the LiveStream, including eventally compatible configurations
10. The camera must be started
11. The MJPEG encoder for Live Stream must be started
12. The Live Stream Thread must be started

In case of harmonized configurations, only steps 7 and 8 would have been required.
