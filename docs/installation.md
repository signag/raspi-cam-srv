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

So, if you want to switch the [WSGI server](./Information_Sys.md#wsgi-server) or need more [threads for Gunicorn](./installation_man.md#gunicorn-settings), or if you want to extend the softwarestack with a missing package, just rerun the installer. It will not touch your existing data, but just update the installation to the latest version and adjust the service configuration to your requirements.

### Starting the Installer

#### For Fresh Installation

```
==========================================
=== raspiCamSrv Automated Installer    ===
===                                    ===
=== Exit at any step with Ctrl+C       ===
==========================================

RPI Model           : Raspberry Pi 4 Model B Rev 1.1
Detected OS codename: trixie full
Hostname            : raspi03

Running as user     : sn
Installing at       : /home/sn/prg

=====================
Installation Defaults
=====================
Installation Path   : /home/sn/prg/raspi-cam-srv
WSGI Server         : Gunicorn
Gunicorn Threads    : 6
Service Port        : 5000 (default, will be adjusted if already in use)
Audio Recording     : Disabled (Installing system service)
Advanced Features   : Enabled
                      USB Cams, Histograms, Stereo Vision, extended Motion Detection
                      (Requires OpenCV, numpy, matplotlib)
AI Camera Support   : Disabled

Do you want to install with these settings? [Y/n]:


No more questions! Ready to start installation? [Y/n]:
```

Confirming both times with ```y``` or ```[Enter]``` will run the installer with the default settings.

Confirming with ```n``` will allow for individual settings.

#### Fresh Installation with existing Backup from previous Installation

If saved backups from a previous installation exist at ```~/prg/raspi-cam-srv_backups``` (see [Retaining backups when uninstalling](#retaining-backups)), the installer will automatically restore these for the new installation. If they are not required, you can remove them in dialog [Settings/Configuration](./SettingsConfiguration.md).

```
==========================================
=== raspiCamSrv Automated Installer    ===
===                                    ===
=== Exit at any step with Ctrl+C       ===
==========================================

RPI Model           : Raspberry Pi Zero 2 W Rev 1.0
Detected OS codename: bookworm lite
Hostname            : raspi05

Running as user     : sn
Installing at       : /home/sn/prg

=====================
Installation Defaults
=====================
Installation Path   : /home/sn/prg/raspi-cam-srv
Backup              : Restoring backup from a previous installation
WSGI Server         : Gunicorn
Gunicorn Threads    : 6
Service Port        : 5000 (default, will be adjusted if already in use)
Audio Recording     : Disabled (Installing system service)
Advanced Features   : Enabled
                      USB Cams, Histograms, Stereo Vision, extended Motion Detection
                      (Requires OpenCV, numpy, matplotlib)
AI Camera Support   : Disabled

Do you want to install with these settings? [Y/n]:


```

#### Installing over existing Installation

If the installation path ```~/prg/raspi-cam-srv``` exists already, it is assumed that a raspiCamSrv installation exists already on the system.

```
==========================================
=== raspiCamSrv Automated Installer    ===
===                                    ===
=== Exit at any step with Ctrl+C       ===
==========================================

RPI Model           : Raspberry Pi Zero 2 W Rev 1.0
Detected OS codename: bookworm lite
Hostname            : raspi05

Running as user     : sn
Installing at       : /home/sn/prg

=====================
Installation Mode
=====================
Installation Path   : /home/sn/prg/raspi-cam-srv (exists)
Service Status      : raspiCamSrv.service (running, will be stopped)

A raspiCamSrv installation exists already.

Do you want to skip update of raspiCamSrv and software stack and only reconfigure the service[Y/n]:


Only installing/replacing service for existing installation

=====================
Installation Defaults
=====================
WSGI Server         : Gunicorn
Gunicorn Threads    : 6
Service Port        : 5000 (default, will be adjusted if already in use)
Audio Recording     : Disabled (Installing system service)

Do you want to install with these settings? [Y/n]:


No more questions! Ready to start installation? [Y/n]:

```

Confirming all questions with ```y``` or ```[Enter]```  will

- stop a running raspiCamSrv service
- skip updating the raspiCamSrv repository
- skip installation of software packages
- try to initialize the database in case this did not complete in the previous installation run
- reconfigure a system service (no audio recording)

Alternatively, you can allow updating raspiCamSrv and software stack and/or run a customized installation.

### Custom Installation

If a custom installation is required, necessary information is requested step by step:

```
Do you want to install with these settings? [Y/n]: n


Available WSGI servers:
1) Gunicorn (recommended for publicly accessible systems) - default
2) Flask built-in server (OK for testing and private networks)
Choose WSGI server [1/2]:

Using WSGI server: gunicorn

How many parallel video streams do you require? [default: 6]:

Using 6 threads for Gunicorn worker process

Do you need to record audio along with videos? [y/N]:

Audio recording enabled: false

Do you want to enable advanced features (USB Cams, Histograms, Stereo Vision, extended Motion Detection)? [Y/n]:

Advanced features enabled: true

Do you intend to use the Raspberry Pi AI Camera (imx500)? [y/N]: y

AI Camera support enabled: true

No more questions! Ready to start installation? [Y/n]:
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

#### Step 12: Initializing database for Raspberry Pi Zero Systems

Recent (per ~02/2026) updates of Bookworm and Trixie on Raspberry Pi Zero / Zero 2 devices seem to have an issue with allocation of CMA memory by Picamera2 (see also [Checking Contiguous Memory (CMA)](./SetupDocker.md#checking-contiguous-memory-cma)). The issue may be due to CMA fragmentation or revious processes not releasing its buffers cleanly or fast enough. This issue does not exist for Bullseye systems on RPI Zero and also not for RPI 1, ... 5.

When the Flask raspiCamSrv application is created (which is also the case while initializing the database during installation), raspiCamSrv instantiates the active camera through Picamera2. During this process, Picamera2 tries to allocate CMA memory.

It has been observed on RPI Zero Bookworm and Trixie systems, that this allocation may fail at one time and be successful later.

Therefore, in this specific setup, the raspiCamSrv installer will try database initialization for up to 5 times with a pause of 5 sec in case of a failure.

The example, below, shows success in the second attempt:

```
Step 12: Initializing database ...
Attempt 1 of 5...
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/flask/__main__.py", line 3, in <module>
    main()
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/flask/cli.py", line 1131, in main
    cli.main()
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/click/core.py", line 1406, in main
    rv = self.invoke(ctx)
         ^^^^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/click/core.py", line 1867, in invoke
    cmd_name, cmd, args = self.resolve_command(ctx, args)
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/click/core.py", line 1914, in resolve_command
    cmd = self.get_command(ctx, cmd_name)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/flask/cli.py", line 631, in get_command
    app = info.load_app()
          ^^^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/flask/cli.py", line 349, in load_app
    app = locate_app(import_name, name)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/flask/cli.py", line 262, in locate_app
    return find_best_app(module)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/.venv/lib/python3.11/site-packages/flask/cli.py", line 72, in find_best_app
    app = app_factory()
          ^^^^^^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/raspiCamSrv/__init__.py", line 155, in create_app
    cam = Camera()
          ^^^^^^^^
  File "/home/sn/prg/raspi-cam-srv/raspiCamSrv/camera_pi.py", line 1713, in __new__
    cls.initCamera()
  File "/home/sn/prg/raspi-cam-srv/raspiCamSrv/camera_pi.py", line 1953, in initCamera
    cls.loadCameraSpecifics()
  File "/home/sn/prg/raspi-cam-srv/raspiCamSrv/camera_pi.py", line 2945, in loadCameraSpecifics
    sensorModes = Camera.cam.sensor_modes
                  ^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/picamera2/picamera2.py", line 599, in sensor_modes
    self.configure(temp_config)
  File "/usr/lib/python3/dist-packages/picamera2/picamera2.py", line 1221, in configure
    self.configure_("preview" if camera_config is None else camera_config)
  File "/usr/lib/python3/dist-packages/picamera2/picamera2.py", line 1193, in configure_
    self.allocator.allocate(libcamera_config, camera_config.get("use_case"))
  File "/usr/lib/python3/dist-packages/picamera2/allocators/dmaallocator.py", line 43, in allocate
    fd = self.dmaHeap.alloc(f"picamera2-{i}", stream_config.frame_size)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/picamera2/dma_heap.py", line 98, in alloc
    ret = fcntl.ioctl(self.__dmaHeapHandle.get(), DMA_HEAP_IOCTL_ALLOC, alloc)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 12] Cannot allocate memory
Failed. Waiting 5s before retry...
Attempt 2 of 5...
Initialized the database.

```

A similar behavior may be observed at server start.    
However, since the raspiCamSrv service is configured to restart automatically, server start will usually be successful after some time.

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

### Uninstaller

The uninstaller will request confirmation:

```
==========================================
=== raspiCamSrv Automated Uninstaller  ===
===                                    ===
=== Exit at any step with Ctrl+C       ===
==========================================

RPI Model           : Raspberry Pi Zero 2 W Rev 1.0
Detected OS codename: bookworm lite
Hostname            : raspi05

Running as user     : sn
Uninstalling from   : /home/sn/prg/raspi-cam-srv

raspiCamSrv will be completely removed from raspi05. Continue? [yes/NO]:
```

To uninstall, you need to reply with ```yes```.

### Retaining Backups

If you had created [backups](./SettingsConfiguration.md#backups), these can be preserved for a possible reuse in a new installation.

```
Backups found in /home/sn/prg/raspi-cam-srv/backups:
total 8
drwxr-xr-x 4 sn sn 4096 Feb 28 16:50 2026-02-28-16:49
drwxr-xr-x 4 sn sn 4096 Feb 28 17:05 2026-02-28-17:05

Do you want to keep these backups? [y/N]:y

Backups saved at /home/sn/prg/raspi-cam-srv_backups

Uninstalling raspiCamSrv service ...

```
