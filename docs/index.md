**raspiCamSrv** is a Web server for Raspberry Pi systems providing an App for control and streaming of CSI and USB cameras as well as for controlling a large variety of connected [GPIO devices](./SettingsDevices.md).

While all currently connected cameras are accessible by the system, up to two cameras can be operated simultaneously at a time, supporting multi-camera features like [Stereo Vision](./CamStereo.md).

Interoperability between Cameras and GPIO devices is achieved through the freely configurable [event handling infrastructure](./Trigger.md).

**raspiCamSrv** supports all Raspberry Pi platforms from Pi Zero to Pi 5, running Bullseye, Bookworm or Trixie OS.

Besides the currently available Raspberry Pi cameras, also compatible CSI cameras from other providers can be used. USB web cams are seamlessly integrated.

**raspiCamSrv** is built with [Flask 3.x](https://flask.palletsprojects.com/en/stable/) and uses the [Picamera2 library](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf).    
Due to responsive layout from [W3.CSS](https://www.w3schools.com/w3css/), all modern browsers on PC, Mac or mobile devices can be used as clients.

For resources and latest version, refer to the [raspiCamSrv GitHub Repository](https://github.com/signag/raspi-cam-srv)

![Live Overview](./img/Live.jpg)