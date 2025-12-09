# RaspiCamSrv Installation

[![Up](img/goup.gif)](./getting_started_overview.md)


The following description refers to the initial installation.    
If you want to update an existing installation to the latest version, see [Update Procedure](./updating_raspiCamSrv.md).


1. Connect to the Pi using SSH: <br>```ssh <user>@<host>```<br>with ```<user>``` and ```<host>``` as specified during setup with Imager.
2. Make sure that the system is up to date<br>```sudo apt update``` <br>```sudo apt full-upgrade```
3. Run the automatic installer with:      
```bash <(curl -fsSL https://raw.githubusercontent.com/signag/raspi-cam-srv/main/scripts/install_raspiCamSrv.sh)```
4. When the installer has finished successfully, open a browser and connect to raspiCamSrv using the indicated URL.
5. Before you can login, you first need to [register](./Authentication.md).<br>The first user will automatically be SuperUser who can later register other users ([User Management](./Authentication.md#user-management))
6. After successful log-in, the [Live screen](./LiveScreen.md) will be shown, if at least one camera is connected, otherwise the [Info](./Information.md) screen.
7. For usage of **raspiCamSrv**, please refer to the [User Guide](./UserGuide.md)

## Installer
The installer will automatically execute the procedure described for [manual installation](./installation_man.md) as well as [service configuration](./service_configuration.md).

At the beginning, you will be asked if you need to record audio along with video.    
If you answer "y", the installer will install raspiCamSrv as user service, otherwise as system service.    
(See [Recording Audio along with Video](./Settings.md#recording-audio-along-with-video)).

The steps shown in the installer protocol correspond to the steps of [manual installation](./installation_man.md).

You can run the installer multiple times without any risk.    
It will skip steps which were already completed and complete or update the installation.

In case of problems during installation and usage, see [Troubleshooting](./Troubelshooting.md) or try the [manual installation procedure](./installation_man.md).

## Supervision

You can check the system logs with    
```sudo journalctl -ef```

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

## Manually Starting the Server

1. Stop the service    
```sudo systemctl stop raspiCamSrv```  (In case of a system unit)    
```systemctl --user stop raspiCamSrv```  (In case of a user unit)
2. Go to the install directory    
```cd ~/prg/raspi-cam-srv```
3. Activate the virtual environment    
```.venv/bin/activate```
4. Start raspiCamSrv    
```python -m flask --app raspiCamSrv run --port 5000 --host=0.0.0.0```


## Uninstalling raspiCamSrv

1. Connect to the Pi using SSH: <br>```ssh <user>@<host>```
2. Run the automatic uninstaller with:    
```bash <(curl -fsSL https://raw.githubusercontent.com/signag/raspi-cam-srv/main/scripts/uninstall_raspiCamSrv.sh)```
