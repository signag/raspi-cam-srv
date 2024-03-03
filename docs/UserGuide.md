# RaspiCamSrv User Guide

[![Up](img/goup.gif)](../README.md)

**NOTE**     
For a full understanding of application details, users should familiarize with the official document [Raspberry Pi - The Picamera2 Library](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf).  
The document version, on which this raspiCamSrv release is based, is also included in this documentation: [picamera2-manual.pdf](./picamera2-manual.pdf)

When the server on a Pi is running and the Pi is reacheable through the network (usually WiFi), you can connect with a browser using the Pi address ('raspi05' in the example below) with the Flask port number, usually 5000, e.g.:  
```http://raspi05:5000```

The system will request an initial [registration and a login](./Authentication.md) and subsequently open the **Live** application screen.

For error handling, see [raspiCamSrv Troubleshooting](./Troubelshooting.md)

## Application Screen
![Main Screen](img/Live_start.jpg)

### Elements

#### Title bar
On the right side, the title bar shows
- the current server connection
- the active camera as advertised by Picamera2
- the active user

On the left side, the title bar shows the application name (raspiCamSrv) and the current screen.

#### Main Menu
The main menu (black background) allows navigation to different screens
- **Live** shows the [Live Screen](./LiveScreen.md) which includes functionality for image control as well as photo- and video taking
- **Config** gives access to camera [Configuration](./Configuration.md) where basic camera configurations can be specified for different scenarios.
- **Info** opens the [Camera Information](./Information.md) page with information on installed cameras as well as Properties and Sensor Modes of the active camera.
- **Photos** shows the [Photos](./PhotoViewer.md) where the currently available photos and videos can be browsed and inspected in detail.
- **Photoseries** opens the [Photo Series](./PhotoSeries.md) page for control of photo series.
- **Trigger** Allows configuring triggered video and/or photo taking (not yet available)
- **Web Cam** opens the [Web Cam](./Webcam.md) page showing web cam features of **raspiCamSrv**
- **Settings** opens the [Settings](./Settings.md) page where some basic server parameters can be configured and where the active camera can be switched in case the Raspberry Pi device supprts multiple cameras (such as Pi 5).
- **Log Out** will log the active user out and direct to the [Log-In Screen](./Authentication.md#log-in)

#### Process Status indicators

On the right side of the menu bar there is a group of statis indicators for the different [background ptocesses](./Background%20Processes.md):

![Status Indicators](./img/ProcessIndicator1.jpg)

![Status Indicators](./img/ProcessIndicator3.jpg)

From right to left, these indicate the status of

- Live stream thread
- Video thread
- Recording [audio](./Settings.md#recording-audio-along-with-video) along with video
- [Photo Series](./PhotoSeries.md) thread

Red color indicates that a process is active whereas gray indicates that it is inactive.

#### Message Line
At the bottom of the screen, there is a message line where application messages will be shown when necessary.

## Streaming

**raspiCamSrv** supports streaming MJPEG video.

The straming URL is   
```http://<server>:<port>/video_feed``` for MJPEG video   
```http://<server>:<port>/photo_feed``` for photo snapshots      
Both URLs can be accessed without authentication.

In the web client, an active streaming server is indicated with the process status indicators as    
![ProcessStatusIndicator](./img/ProcessIndicator1.jpg)   
A live stream is shown in in the [Live Screen](./LiveScreen.md)

The streaming server is automatically shut down if no client has been streaming within the last 10 seconds.   
For example if one is working in other dialogs rather than *Live Screen*, straming is not used and the streaming server is shut down, which is indicated by   
![ProcessStatusIndicator](./img/ProcessIndicator7.jpg)   
Streaming is automatically reactivated, if a streaming client connects, for example if the *Live Screen* is activated.

Other clients, either connecting directly through the streaming URL or by using the **raspiCamSrv** web client, will also activate the streaming server.

Streaming can be deactivated, if a **raspiCamSrv** task is executed which requires exclusive access to the camera because of a specific [Configuration](./Configuration.md) which is not compliant with the configuration required for streaming (for more details, see [raspiCamSrv Tasks and Background Processes](./Background%20Processes.md)).
