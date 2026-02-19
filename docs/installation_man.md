# Manual raspiCamSrv Installation

[![Up](img/goup.gif)](./getting_started_overview.md)


The following procedure describes a manual step by step installation.    
For automatic installation, see [RaspiCamSrv Installation](./installation.md).

If you want to update an existing installation to the latest version, see [Update Procedure](./updating_raspiCamSrv.md).

In case of problems during installation and usage, see [Troubleshooting](./Troubelshooting.md)

**NOTE**: For Debian-**Trixie**, some of the required packages are already preinstalled. To ensure everything is consistently installed in and run from the **raspiCamSrv** virtual environment, the respective ```pip install``` commands, below, have been extended with a ```--ignore-installed``` clause and the Flask server is started with ```python -m flask ...```

## Step by Step

1. Connect to the Pi using SSH: <br>```ssh <user>@<host>```<br>with <user> and <host> as specified during setup with Imager.
2. Update the system<br>```sudo apt update``` <br>```sudo apt full-upgrade```
3. If you intend to take videos and have installed a *lite* version of the OS, you may need to install *ffmpeg*:<br>Check whether ffmpeg is installed with<br>```which ffmpeg```<br>If you get an empty response, install with<br>```sudo apt install ffmpeg```
4. Create a root directory under which you will install programs (e.g. 'prg')<br>```mkdir prg```<br>```cd prg```
5. Check that git is installed (which is usually the case in current Bullseye, Bookworm or Trixie distributions)<br>```git --version```<br>If git is not installed, install it with<br>```sudo apt install git```
6. Clone the raspi-cam-srv repository:<br>```git clone --branch main --single-branch --depth 1 https://github.com/signag/raspi-cam-srv```
7. Create a virtual environment ('.venv') on the 'raspi-cam-srv' folder:<br>```cd raspi-cam-srv```<br>```python -m venv --system-site-packages .venv```<br>For the reasoning to include system site packages, see the [picamera2-manual.pdf](./picamera2-manual.pdf), chapter 9.5.
8. Activate the virtual environment<br>```cd ~/prg/raspi-cam-srv```<br>```source .venv/bin/activate```<br>The active virtual environment is indicated by ```(.venv)``` preceeding the system prompt.<br>(If you need to leave the virtual environment at some time, use ```deactivate```)
9. **Trixie**: Skip this step!<br>Make sure that picamera2 is available on the system:<br>```python```<br>```>>>import picamera2```<br>```>>>quit()```<br>If you get a 'ModuleNotFoundError', see the [picamera2 Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf), chapter 2.2, how to install picamera2.<br>For **raspiCamSrv** it would be sufficient to install without GUI dependencies:<br>```sudo apt install -y python3-picamera2 --no-install-recommends```
10. Install Flask 3.x **with the virtual environment activated (Step 8)**.<br>Raspberry Pi OS distributions come with Flask preinstalled, however we need to run Flask from the virtual environment in order to see other packages which will be located there.<br>```pip install --ignore-installed "Flask>=3,<4"```<br><br>Make sure that Flask is really installed in the virtual environment:<br>```which flask``` should output<br>```/home/<user>/prg/raspi-cam-srv/.venv/bin/flask```
11. **Optional** installations:
<br>The following installations are only required if you need to visualize histograms of photos or if you are interested in using [Extended Motion Capturing Algorithms](./TriggerMotion.md) or [Stereo Vision](./CamStereo.md).<br>For use of USB cameras, OpenCV is required.
<br>
<br>All installations must be done with the virtual environment activated (Step 8)
<br>
<br>Install [OpenCV](https://de.wikipedia.org/wiki/OpenCV):
<br>```sudo apt-get install python3-opencv```
<br>
<br>Install [numpy](https://numpy.org/):
<br>```pip install --ignore-installed numpy```
<br>(There may be errors, which normally can be ignored)
<br>
<br>Install [matplotlib](https://de.wikipedia.org/wiki/Matplotlib):
<br>**Trixie**:```pip install --ignore-installed matplotlib```
<br>(There may be errors, which normally can be ignored)
<br>**Bookworm**: ```pip install --ignore-installed "matplotlib<3.8"```
<br>(The version restriction assures compatibility with numpy 1.x which is [required for Picamera2](https://github.com/raspberrypi/picamera2/issues/1211))
<br>
<br>The following installation is required for enabling the [raspiCamSrv API](./API.md)
<br>Install [flask-jwt-extended](https://flask-jwt-extended.readthedocs.io/en/stable/)
<br>```pip install --ignore-installed flask-jwt-extended```
<br>(There may be errors, which normally can be ignored)
<br>
<br>The following installation is only required if you are using a Lite variant of the Debian OS:
<br>```pip install --ignore-installed psutil```
<br>
<br>The following installations are only required if you intend to use a Raspberry Pi AI Camera:
<br>
<br>Install the imx500-all package:
<br>```sudo apt install imx500-all```
<br>
<br>Install [munkres](https://pypi.org/project/munkres/)
<br>```pip install --break-system-packages munkres```
<br>(There may be errors, which normally can be ignored)
<br>
<br>If you intend to use the [Gunicorn](https://gunicorn.org/) WSGI server instead of the development WSGI server integrated in Flask ([Werkzeug](https://werkzeug.palletsprojects.com/en/stable/)), you need to install Gunicorn:
<br>```pip install --break-system-packages gunicorn```
<br>(There may be errors, which normally can be ignored)
<br><br>
12. Initialize the database for Flask <br>(with ```raspi-cam-srv``` as active directory and the virual environment activated - see step 8):<br>```python -m flask --app raspiCamSrv init-db```
13. Check that the Flask default port 5000 is available<br>```sudo netstat -nlp | grep 5000```<br>If an entry is shown, find another free port (e.g. 5001) <br>and replace ```port 5000``` by your port in all ```flask``` commands, below and also in the URL in step 12.
14. Start the server<br>(with ```raspi-cam-srv``` as active directory and the virual environment activated - see step 8):<br>Either use the Flask built-in development server:<br>```python -m flask --app raspiCamSrv run --port 5000 --host=0.0.0.0```<br>or use [Gunicorn](https://gunicorn.org/) as productive server:<br>```gunicorn -b 0.0.0.0:5000 -w 1 -k gthread --threads 6 --timeout 0 --log-level info 'raspiCamSrv:create_app()'```
15. Connect to the server from a browser:<br>```http://<raspi_host>:5000```<br>This will open the [Login](./Authentication.md) screen.
16. Before you can login, you first need to [register](./Authentication.md).<br>The first user will automatically be SuperUser who can later register other users ([User Management](./Authentication.md#user-management))
17. After successful log-in, the [Live screen](./LiveScreen.md) will be shown, if at least one camera is connected, otherwise the [Info](./Information.md) screen.
18. Done!
19. For usage of **raspiCamSrv**, please refer to the [User Guide](./UserGuide.md)


When the Flask server starts up, it will show a warning that this is a development server.   
This is, in general, fine for private environments.   
How to deploy with an alternative production WSGI server, is described in the [Flask documentation](https://flask.palletsprojects.com/en/stable/deploying/)

## Gunicorn Settings

When using the [Gunicorn](https://gunicorn.org/) WSGI server, specific settings must be used with the raspiCamSrv Flask application.

### Number of Workers

**Command line**: ```-w 1```

Only a single worker must be configured.

Each worker will be a separate process. Multiple workers would run multiple raspiCamSrv Flask processes in parallel.    
This would cause conflicts when accessing Raspberry Pi resources, such as cameras and GPIO devices.    

### Port Binding

By default, Gunicorn binds to ```127.0.0.1:8080```

It is recommended using the same port as the Flask-internal WSGI server (5000).

**Command line**: ```-b 0.0.0.0:5000```

### Worker Type

Gunicorn supports different [Worker Types](https://gunicorn.org/design/?h=design#worker-types) to be used.   
From these, only ```gthread``` works for raspiCamSrv, because

- keep-alive connections are supported, which is essential for MJPEG streaming
- it uses real OS threads which is essential for multi-threading in raspiCamSrv, Picamera2 and OpenCV

**Command line**: ```-k gthread```

### Numer of Threads

With the ```gthread``` worker type, it is necessary to specify the number of threads which can be simultaneously active, because each request will be handled by an own worker thread.

Therefore, the number of threads limits the number of simultaneous MJPEG streams.

On the other hand, when a worker is started, the worker process will pre-create the specified number of threads, regardless of how many clients are connected.

**Command line**: ```--threads 6```

Every MJPEG stream uses one thread, for example:

- [Live screen](./LiveScreen.md): 1 thread
- [Web Cam screen](./CamWebcam.md) with 2 cameras: 2 threads
- [Stereo Cam screen](./CamStereo.md): 3 threads
- Every client streaming from a ```video_feed``` endpoint uses 1 thread

So, with ```--threads 4``` and 2 clients showing the [Web Cam screen](./CamWebcam.md), the 4 threads are used up and another client, trying to stream from a ```video_feed``` endpoint, would wait.

### Timeout

Gunicorn kills and restarts worker threads which are silent for more than the number of seconds specified in the ```timeout``` option.

The default is 30 seconds.

For raspiCamSrv, timout should be avoided.

**Command line**: ```--timeout 0```

### Logging

**Command line**: ```--log-level info```

'info' is the default log level.

Other valid level names are:

- debug
- warning
- error
- critical

### WSGI APP

raspiCamSrv uses a factory pattern to create the Flask application.

Therefore, the raspiCamSrv WSGI app needs to be ecposed to Gunicorn in the form

**Command Line**: ```'raspiCamSrv:create_app()'```