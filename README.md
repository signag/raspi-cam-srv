# raspiCamSrv

The Raspberry Pi Camera Server (raspiCamSrv) is a web server which can be deployed on a Raspberry Pi device giving access to installed cameras and allows to control these.

It can be installed on all Raspberry Pi platforms which allow connection of one or multiple cameras and supports the currently existing camera types.
Up to now, it was tested on Pi Zero W, Pi Zero 2 W, Pi 4 and Pi 5 running Bullseye as well as Bookworm together with camera modules 1, 2 and 3. On Pi 5, also parallel installation of two different cameras was tested.

raspiCamSrv is built with [Flask 3.0](https://flask.palletsprojects.com/en/3.0.x/) and uses the [Picamera2 library](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf).

Due to responsive layout from [W3.CSS](https://www.w3schools.com/w3css/), clients can be all modern browsers as well as mobile devices.

## Feature Overview
For more details, see the [User Guide](docs/UserGuide.md)

![Live Overview](docs/img/Live.jpg)

- The [Live screen](docs/LiveScreen.md) shows a live stream of the active camera and allows individually selecting and setting all [camera controls](docs/CameraControls.md) supported by Picamera2.
- For cameras with focus control (camera 3), it is also possible to graphically draw autofocus windows and trigger the autofocus to measure the LensPosition which is translated into a focal distance (see [Focus handling](docs/FocusHandling.md)).
- Photos, raw photos and videos can be taken, which are shown in the lower part of the [Live screen](docs/LiveScreen.md) together with their metadata (see [Photo taking](docs/Phototaking.md)).
- For raw photos and videos, a jpeg placeholder is shown
- The photos taken may be added to a display buffer for inspection of photos and metadata and for comparison (see [Photo Display](docs/Phototaking.md#photo-display))
- On the [Config screen](docs/Configuration.md), camera configurations can be specified for four different use cases (Live View, Photo, Raw Photo and Video). These will be applied together with the selected controls when photos or videos will be taken. The *Live view* configuration will also be immediately applied to the Live stream.
- The [Info screen](docs/Information.md) shows the installed cameras, and, for the active camera, the camera properties as well as the available sensor modes.
- The [Photos screen](docs/PhotoViewer.md) allows scrolling through all available photos and videos with detail views of selected items.
- The [Settings screen](docs/Settings.md) allows a few configuration settings such as selection of the active camera as well as selecting the type of photos, raw photos and videos in the range supported by Picamera2
- Access to the server requires [registration and authentification](docs/Authentication.md).

## Limitations
The software is still being tested and extended.

- Timelapse features are envisaged. <br>It was actually the starting point for this project to develop a Pi Zero + Camera solution, based on actual software and hardware, which can be used for long runnting time lapse series.
- The entire configuration is still transient and will be reinitialized with server restart. It is intended to save the configuration in the database and restore it when the server is restarted.
- Although the layout is responsive, it may not be "good-looking" with all sizes of browser windows

## Credits
- Most technical information on Picamera2 (<https://github.com/raspberrypi/picamera2>) has been taken from the [Raspberry Pi - The Picamera2 Library](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf) document.
- The implementation of live streaming with Flask has been inspired by <https://blog.miguelgrinberg.com/post/video-streaming-with-flask>
- The detailed solution for the mjpeg_server is based on the example [mjpeg_server.py](https://github.com/raspberrypi/picamera2/blob/main/examples/mjpeg_server.py) of the [picamera2 repository](https://github.com/raspberrypi/picamera2)
- The solution for drawing on the canvas for definition of AF Windows has been inspired by <https://codepen.io/AllenT871/pen/GVyXKp>

## Setup / Getting Started

### Required
- A **Raspberry Pi** ([Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero-w/), [Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/), [Pi 1](https://www.raspberrypi.com/products/raspberry-pi-1-model-b-plus/), [Pi 3](https://www.raspberrypi.com/products/raspberry-pi-3-model-b-plus/), [Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/), [Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/))
- A [Raspberry Pi camera](https://www.raspberrypi.com/documentation/accessories/camera.html)
- A suitable **camera cable** <br>(Pi Zero W, Pi Zero 2 W and Pi 5 have the small CSI-2 camera port, requiring a special cable which is usually not shipped with the camera)
- A **microSD card**
- A suitable **power supply**<br>For Pi Zero W or Pi Zero 2 W, a normal mobile phone charger is sufficient as long as it has a Micro-USB connector
- Optionally, a **case** for the specific model may ease handling.<br>For Pi Zero W or Zero 2 W, offerings for the official case (e.g. [here](https://www.reichelt.de/gehaeuse-fuer-raspberry-pi-zero-rot-weiss-rpiz-case-whrd-p223607.html?PROVID=2788&gclid=EAIaIQobChMI2JfM3vjcgwMVSxYGAB1pSQBOEAYYASABEgL_GPD_BwE)) should include a special short camera cable.<br>The cover for the camera is fine for camera models 1 and 2. For camera model 3, some handwork is necessary to enlarge the hole to a square for the camera body.
- A **Wifi network** with internet access and known access credentials (**SSID**, **password**)
- A **PC** with network access and **(micro)SD** card reader

The setup description, below, assumes a completely autonomous or 'headless' setup, where the Raspberry Pi requires nothing but a power supply cable without any necessity to ever connect it to a display, keyboard or mouse.   
![Pi Zero Cover](docs/img/pi_zero_cover.jpg)<br>Here, the camera model 2 is installed.

The described steps were successfully executed with Raspberry Pi Imager version 1.8.4 and a Raspberry Pi Zero W.

### System Setup
For system setup, follow the instructions of the [Raspberry Pi Getting Started Documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html#install-using-imager) for OS installation using Imager.   
Make sure that SSH is enabled on the Services tab.

Once the SD card is written, insert it into the Raspberry Pi and power it up.   
Initially, it will take several minutes until it is visible in the network.

### RaspiCamSrv Installation

|Step|Action
|----|--------------------------------------------------
|1.  | Connect to the Pi using SSH: <br>```ssh <user>@<host>```<br>with user and host as specified during setup with Imager.
|2.  | Update the system<br>```sudo apt update``` <br>```sudo apt full-upgrade```
|3.  | Create a root directory under which you will install programs (e.g. 'prg')<br>```mkdir prg```<br>```cd prg```
|4.  | Check that git is installed (which is usually the case in current Bullseye and Bookworm distributions)<br>```git --version```<br>If git is not installed, install it with<br>```sudo apt install git```
|5.  | Clone the raspi-cam-srv repository:<br>```git clone https://github.com/signag/raspi-cam-srv```
|6.  | Create a virtual environment ('.venv') on the 'raspi-cam-srv' folder:<br>```cd raspi-cam-srv```<br>```python -m venv --system-site-packages .venv```<br>For the reasoning to include system site packages, see the [picamera2-manual.pdf](./picamera2-manual.pdf), chapter 9.5.
|7.  | Activate the virtual environment<br>```source .venv/bin/activate```<br>The active virtual environment is indicated by ```(.venv)``` preceeding the system prompt
|8.  | Install Flask 3.0 within the virtual environment.<br>Raspberry Pi OS distributions come with Flask preinstalled, however with versions 1.1 or 2.2.<br>RaspiCamSrv requires Flask 3.0, which can be installed with<br>```pip install Flask==3.0.0```<br>If you want to check the Flask version, you may need to deactivate/activate the virtual environment first:<br>```deactivate```<br>```source .venv/bin/activate```<br>```flask --version```<br>This should reveal version 'Flask 3.0.0'.
|9.  | Initialize the database for Flask:<br>```flask --app raspiCamSrv init-db```
|10. | Start the server:<br>```flask --app raspiCamSrv run --host=0.0.0.0```
|11. | Connect to the server from a browser:<br>```http://<raspi_host>:5000```<br>This will open the [Login](docs/Authentication.md#log-in) screen.
|12. | Before you can login, you first need to [register](docs/Authentication.md#registration).
|13. | After successful log-in, the [Live](docs/LiveScreen.md) will be shown
|14. | Done!


When the Flask server starts up, it will show a warning that this is a development server.   
This is, in general, fine for private environments.   
How to deploy with a production WSGI server, is described in the [Flask documentation](https://flask.palletsprojects.com/en/3.0.x/deploying/)

### Service Configuration

When the Flask server is started in a SSH session as described in step 10, above, it will terminate with the SSH session.

Instead, you may want the server to start up independently from any user sessions, restart after a failure and automatically start up when the device is powered up.

In order to achieve this, the Flask server start can be configured as service under control of systemd.

|Step|Action
|----|-----------------------------------------------
|1.  | Open a SSH session on the Raspberry Pi
|2.  | Copy the service template *raspiCamSrv.service* which is provided with **raspiCamSrv** to your home directory<br>```cp ~/prg/raspi-cam-srv/config/raspiCamSrv.service ~``` 
|3.  | Adjust the service configuration:<br>```nano raspiCamSrv.service```<br>Replace '\<user>' with the user ID, specified during [System Setup](#system-setup)
|4.  | Stage the service configuration file to systemd:<br>```sudo cp raspiCamSrv.service /etc/systemd/system```
|5.  | Start the service:<br>```sudo systemctl start raspiCamSrv.service```
|6.  | Check that the Flask server has started as service:<br>```sudo journalctl -e```
|7.  | Enable the service so that it automatically starts with system boot:<br>```sudo systemctl enable raspiCamSrv.service```
|8.  | Reboot the system to test automatic server start:<br>```sudo reboot```