[![Up](img/goup.gif)](../README.md)

# Running **raspiCamSrv** as Docker Container

A container image is available for **raspiCamSrv** at [https://hub.docker.com/repository/docker/signag/raspi-cam-srv/general](https://hub.docker.com/repository/docker/signag/raspi-cam-srv/general)

**ATTENTION**: Running raspiCamSrv in Docker is still somehow 'experimental'. Successful tests have been done only on Pi 4 and Pi 5. However, not all functions have so far been systematically tested. On Pi Zero W and Pi Zero 2 W, deployment of the image was not successful, probably because of its size (~475 MB).

**1. Preconditions**
- [Installation of Docker on a Raspberry Pi](#installation-of-docker-on-a-raspberry-pi)
- [Check Contiguous Memory (CMA)](#checking-contiguous-memory-cma)
- [Deactivate raspiCamSrv Service from manual Installation](#deactivate-raspicamsrv-service-from-manual-installation)

**2. Compose Service Definition**

In an arbitrary working directory (e.g. ```~/docker```), create

```compose.yaml```:

```yml
services:
  raspi-cam-srv:
    image: signag/raspi-cam-srv
    container_name: raspi-cam-srv
    network_mode: "host"
    ports:
      - "5000:5000"
    devices:
      - /dev/video0:/dev/video0
      - /dev/gpiochip0:/dev/gpiochip0
    volumes:
      # Uncomment resource mappings, if required
      # Configure and prepare container-external folders
      #- ./resources/database/:/app/instance/
      #- ./resources/config/:/app/raspiCamSrv/static/config/
      #- ./resources/events/:/app/raspiCamSrv/static/events/
      #- ./resources/photos/:/app/raspiCamSrv/static/photos/
      #- ./resources/photoseries/:/app/raspiCamSrv/static/photoseries/
      #- ./resources/tuning/:/app/raspiCamSrv/static/tuning/
      - /run/udev/:/run/udev:ro
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
```

The *volumes* attribute includes prepared mappings of resource folders for database, [configuration](./SettingsConfiguration.md), [events](./TriggerActive.md), [photos](./PhotoViewer.md), [photoseries](./PhotoSeries.md#photo-series-in-the-file-system) and [tuning](./Tuning.md), which can/should be mapped to container-external folders in order to allow easy access and preserve the data also in case the container is removed or reset after a new image version has been pulled.<br>**NOTE**: For a quick test, the container can also be run without these mappings.

Consider that the database holds [user data](./Authentication.md) as well as [event data](./TriggerActive.md) which will be lost if the database exists only within the container and if the container is removed.

**3. Pull raspi-cam-srv Image**

```docker compose pull raspi-cam-srv```

Wait until all pulls are completed.

**4. Create Container**

```docker compose create raspi-cam-srv```

![Create Container](./img/docker_CreateContainer.jpg)

**5. Start Container**

```docker compose start raspi-cam-srv```

![Start Container](./img/docker_StartContainer.jpg)

**6. Initialize Database**

This step is only required if the ```/app/instance/``` folder, containing the database, has been mapped to a container-external folder.

The image includes already an initialized database. However, if the ```/app/instance/``` is mapped, this database is not visible for the container and an empty database is created which needs to be initialized.

This can be done on an interactive command prompt for the container:

```docker compose exec raspi-cam-srv sh```

```flask --app raspiCamSrv init-db```

![Initialize DB](./img/docker_InitDb.jpg)


**7. Connect to raspiCamSrv**

For usage of **raspiCamSrv** see the [User Guide](./UserGuide.md)

## Useful Docker commands

See [Docker Reference](https://docs.docker.com/reference/cli/docker/compose/)

- Stop Container<br>```docker compose stop raspi-cam-srv```
- Start Container<br>```docker compose start raspi-cam-srv```
- Show server logs<br>```docker compose logs raspi-cam-srv```
- Open shell for interactive prompt<br>```docker compose exec raspi-cam-srv sh```
- List Containers<br>```docker container ls```
- List images<br>```docker compose images```
- Pull latest image<br>```docker compose pull raspi-cam-srv```

## Update Procedure

Changes in the [raspi-cam-srv Git repository](https://github.com/signag/raspi-cam-srv) will automatically trigger a new build of the [raspi-cam-srv Docker Image](https://hub.docker.com/repository/docker/signag/raspi-cam-srv).

To update to the latest version, proceed as follows:

1. cd to your working directory, e.g. ```cd ~/docker```
2. ```docker compose pull raspi-cam-srv```
3. ```docker compose stop raspi-cam-srv```
4. ```docker compose rm raspi-cam-srv```
5. ```docker compose create raspi-cam-srv```
6. ```docker compose start raspi-cam-srv```

## Installation of Docker on a Raspberry Pi

The [Docker](https://www.docker.com/) documentation includes descriptions on how to [Install Docker Engine on Raspberry Pi OS](https://docs.docker.com/engine/install/raspberry-pi-os/)

The most convenient way is using the [convenience script](https://docs.docker.com/engine/install/raspberry-pi-os/#install-using-the-convenience-script) provided by the Docker team:


|Step|Action
|----|--------------------------------------------------
|1.  | Connect to the Pi using SSH: <br>```ssh <user>@<host>```<br>with \<user> and \<host> as specified during setup with Imager.
|2.  | Update the system<br>```sudo apt update``` <br>```sudo apt full-upgrade```
|3.  | Install Docker using the [convenience script](https://docs.docker.com/engine/install/raspberry-pi-os/#install-using-the-convenience-script):<br>```curl -sSL https://get.docker.com \| sh```
|4.  | Add current user to the ```docker``` group:<br>```sudo usermod -aG docker $USER```
|5.  | Log out and log in to activate the modified group assignment:<br>```logout```<br>```ssh <user>@<host>```
|6.  | Check that Docker is working correctly:<br>```docker run hello-world```

## Checking Contiguous Memory (CMA)

Cameras on Raspberry Pi use CMA memory (see [Picamera2 Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf), chapter 8.3).
The default size of CMA memory is different for different Raspberry Pi models and can be shown with
```cat /proc/meminfo```

On a Pi 5, the available CMA memory (~65 MB) was found to be too small for accessing cameras from a Docker container when larger image sizes are used.

The value for ```CmaTotal``` should be at least the value found for Raspberry Pi Zero of 262144 kB.

If the value on your system is smaller, it needs to be increased:

|Step|Action
|----|--------------------------------------------------
|1.  | Edit the Raspberry Pi configuration file:<br>```sudo nano /boot/firmware/config.txt```
|2   | Find the line<br>```dtoverlay=vc4-kms-v3d```<br>and replace it with<br>```dtoverlay=vc4-kms-v3d,cma-512``` for > 2GB systems<br>```dtoverlay=vc4-kms-v3d,cma-384``` for > 1GB systems<br>```dtoverlay=vc4-kms-v3d,cma-320``` for smaller systems
|3.  | Reboot<br>```sudo reboot```

## Deactivate raspiCamSrv Service from manual Installation

If you have installed raspiCamSrv manually, you need to deactivate the service:


|Step|Action
|----|--------------------------------------------------
|1.  | Stop the service:<br>```sudo systemctl stop raspiCamSrv.service```<br>or<br>```systemctl --user stop raspiCamSrv.service```
|2.  | Disable the service so that it does not automatically start with boot:<br>```sudo systemctl disable raspiCamSrv.service```<br>or<br>```systemctl --user disable raspiCamSrv.service```

