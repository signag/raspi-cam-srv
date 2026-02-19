# RaspiCamSrv Installation

[![Up](img/goup.gif)](./getting_started_overview.md)


The following description refers to the initial installation.    
If you want to update an existing installation to the latest version, see [Update Procedure](./updating_raspiCamSrv.md).


1. Connect to the Pi using SSH: <br>```ssh <user>@<host>```<br>with ```<user>``` and ```<host>``` as specified during setup with Imager.
2. Make sure that the system is up to date<br>```sudo apt update``` <br>```sudo apt full-upgrade```
3. Run the automatic installer with:      
```bash <(curl -fsSL https://raw.githubusercontent.com/signag/raspi-cam-srv/main/scripts/install_raspiCamSrv.sh)```    
Follow instructions given by the installer (see [below](#installer))
4. When the installer has finished successfully, open a browser and connect to raspiCamSrv using the indicated URL.
5. Before you can login, you first need to [register](./Authentication.md).<br>The first user will automatically be SuperUser who can later register other users ([User Management](./Authentication.md#user-management))
6. After successful log-in, the [Live screen](./LiveScreen.md) will be shown, if at least one camera is connected, otherwise the [Info](./Information.md) screen.
7. For usage of **raspiCamSrv**, please refer to the [User Guide](./UserGuide.md)

## Installer

**NOTE**: You can run the installer multiple times without any risk, also over an existing installation.

So, if you want to switch the [WSGI server](./Information_Sys.md#wsgi-server) or need more [threads for Gunicorn](./installation_man.md#gunicorn-settings), just rerun the installer. It will not touch your existing data, but just update the installation to the latest version and adjust the service configuration to your requirements.

### Starting the Installer

The installer will inform about an existing installation (if available) and request confirmation of default settings:

```
==========================================
=== raspiCamSrv Automated Installer    ===
==========================================

Detected OS codename: trixie full
Hostname            : raspi06

Running as user     : sn
Installing at       : /home/sn/prg

Service 'raspiCamSrv.service' is already running.

If you continue, the existing service will be stopped and replaced.

Do you want to continue with the installation? [Y/n]:

Stopping running service 'raspiCamSrv.service'...

System service 'raspiCamSrv.service' stopped successfully.

======================
Installation Defaults:
======================
Installation Root : /home/sn/prg/raspi-cam-srv
WSGI Server       : Gunicorn
Gunicorn Threads  : 6
Audio Recording   : Disabled (Installing system service)
AI Camera Support : Disabled

Do you want to install with these settings? [Y/n]:

```

If defaults are confirmed, the installer will complete the installation.

### Custom Installation

If a custom installation is required, necessary information is requested step by step:

```
Available WSGI servers:
1) Gunicorn (recommended for publicly accessible systems) - default
2) Flask built-in server (OK for testing and private networks)
Choose WSGI server [1/2]: 2

Using WSGI server: werkzeug

Do you need to record audio along with videos? [y/N]: y

Audio recording enabled: true

Do you intend to use the Raspberry Pi AI Camera (imx500)? [y/N]:

AI Camera support enabled: false

```

- For WSGI server selection, see the [WSGI Server section](./Information_Sys.md#wsgi-server) of the [Info/System](./Information_Sys.md) screen.
- For Gunicorn, especially setting *Number of Threads*, see [Gunicorn Settings](./installation_man.md#gunicorn-settings).
- For recording audio, see [Recording Audio along with Video](./Settings.md#recording-audio-along-with-video).
- For support of AI features for the imx500 camera, see [AI Camera Support](./AiCameraSupport.md).    
(This is not available for Bullseye systems)


### Installation Process

The installer will automatically execute the procedure described for [manual installation](./installation_man.md) as well as [service configuration](./service_configuration.md).


The steps shown in the installer protocol correspond to the steps of [manual installation](./installation_man.md).

In case of problems during installation and usage, see [Troubleshooting](./Troubelshooting.md) or try the [manual installation procedure](./installation_man.md).

### Finalization

```
Step 13: Checking Flask service port ...
Trying port 5000 ...
Using port 5000

Cleaning up existing service before reinstalling ...
System service 'raspiCamSrv.service' disabled.
System service 'raspiCamSrv.service' configuration removed.

Installing 'raspiCamSrv.service' as user unit for WSGI Server werkzeug ...
User service installed and started.

==========================================
=== raspiCamSrv installation completed ===
===                                    ===
=== Access via http://raspi06:5000
==========================================

```

## Supervision

You can check the system logs with    
```sudo journalctl -ef```

### For 'Werkzeug' WSGI server:

When the Flask server starts up, it will show a warning that this is a development server.   
This is, in general, fine for private environments.   
How to deploy with a production WSGI server, is described in the [Flask documentation](https://flask.palletsprojects.com/en/stable/deploying/)

```
Dec 09 18:49:19 raspi06 python[9642]:  * Serving Flask app 'raspiCamSrv'
Dec 09 18:49:19 raspi06 python[9642]:  * Debug mode: off
Dec 09 18:49:19 raspi06 python[9642]: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
Dec 09 18:49:19 raspi06 python[9642]:  * Running on all addresses (0.0.0.0)
Dec 09 18:49:19 raspi06 python[9642]:  * Running on http://127.0.0.1:5000
Dec 09 18:49:19 raspi06 python[9642]:  * Running on http://192.168.178.72:5000
Dec 09 18:49:19 raspi06 python[9642]: Press CTRL+C to quit

```

### For Gunicorn WSGI server

When Gunicorn starts, it will output Info messages like

```
Feb 18 14:09:29 raspi06 systemd[1197]: Started raspiCamSrv.service - raspiCamSrv.
Feb 18 14:09:30 raspi06 gunicorn[7906]: [2026-02-18 14:09:30 +0100] [7906] [INFO] Starting gunicorn 25.1.0
Feb 18 14:09:30 raspi06 gunicorn[7906]: [2026-02-18 14:09:30 +0100] [7906] [INFO] Listening at: http://0.0.0.0:5000 (7906)
Feb 18 14:09:30 raspi06 gunicorn[7906]: [2026-02-18 14:09:30 +0100] [7906] [INFO] Using worker: gthread
Feb 18 14:09:30 raspi06 gunicorn[7906]: [2026-02-18 14:09:30 +0100] [7906] [INFO] Control socket listening at /home/sn/prg/raspi-cam-srv/gunicorn.ctl
Feb 18 14:09:30 raspi06 gunicorn[7908]: [2026-02-18 14:09:30 +0100] [7908] [INFO] Booting worker with pid: 7908

```

The PID of the worker process is also shown in the [Info/System screen](./Information_Sys.md#process-info)

**NOTE**: When starting, the Gunicorn master process creates a control socket file ```gunicorn.ctl``` in the working directory, which will be removed when the server stops.

## Manually Starting the Server

1. Stop the service    
```sudo systemctl stop raspiCamSrv```  (In case of a system unit)    
```systemctl --user stop raspiCamSrv```  (In case of a user unit)
2. Go to the install directory    
```cd ~/prg/raspi-cam-srv```
3. Activate the virtual environment    
```.venv/bin/activate```
4. Start raspiCamSrv    
either with the Flask built-in development server (werkzeug):    
```python -m flask --app raspiCamSrv run --port 5000 --host=0.0.0.0```    
or with the Gunicorn production server:     
```gunicorn -b 0.0.0.0:5000 -w 1 -k gthread --threads 6 --timeout 0 --log-level info 'raspiCamSrv:create_app()```

## Uninstalling raspiCamSrv

1. Connect to the Pi using SSH: <br>```ssh <user>@<host>```
2. Run the automatic uninstaller with:    
```bash <(curl -fsSL https://raw.githubusercontent.com/signag/raspi-cam-srv/main/scripts/uninstall_raspiCamSrv.sh)```
