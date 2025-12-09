# Service Configuration

[![Up](img/goup.gif)](./getting_started_overview.md)

**NOTE**: This installation step is included in the [automatic installation](./installation.md)

When the Flask server is started in a SSH session as described in [Installation Step 11](./installation.md), it will terminate with the SSH session.

Instead, you may want the server to start up independently from any user sessions, restart after a failure and automatically start up when the device is powered up.

In order to achieve this, the Flask server start can be configured as service under control of systemd.

The following procedure is for the case where **audio recording** with video is **not required**. Otherwise, see [next](#service-configuration-for-audio-support) section.

1. Open a SSH session on the Raspberry Pi
2. Copy the service template *raspiCamSrv.service* which is provided with **raspiCamSrv** to your home directory<br>```cp ~/prg/raspi-cam-srv/config/raspiCamSrv.service ~``` 
3. Adjust the service configuration:<br>```nano ~/raspiCamSrv.service```<br>Replace all (4) occurrences of '\<user>' with the user ID, specified during [System Setup](./system_setup.md)<br>If you need a port different from 5000 (see [RaspiCamSrv Installation](./installation.md), step 11), replace also ```port 5000``` by your port.
4. Stage the service configuration file to systemd:<br>```sudo cp ~/raspiCamSrv.service /etc/systemd/system```
5. Start the service:<br>```sudo systemctl start raspiCamSrv.service```
6. Check that the Flask server has started as service:<br>```sudo journalctl -ef```
7. Enable the service so that it automatically starts with system boot:<br>```sudo systemctl enable raspiCamSrv.service```
8. Reboot the system to test automatic server start:<br>```sudo reboot```


## Service Configuration for Audio Support

If it is intended to record audio along with videos, a slightly different setup is required (see [Settings](./Settings.md#recording-audio-along-with-video)):   
Instead of installing the service as a system unit, it needs to be installed as user unit (see [systemd/User](https://wiki.archlinux.org/title/Systemd/User)) in order to get access to [PulseAudio](https://wiki.archlinux.org/title/PulseAudio).

## Trixie and Bookworm Systems

If your system is a trixie or a bookworm system (```lsb_release -a```) follow these steps:

1. Open a SSH session on the Raspberry Pi
2. Copy the service template *raspiCamSrv.service* which is provided with **raspiCamSrv** to your home directory<br>```cp ~/prg/raspi-cam-srv/config/raspiCamSrv.service ~``` 
3. Adjust the service configuration:<br>```nano ~/raspiCamSrv.service```<br>Replace all (4) occurrences of '\<user>' with the user ID, specified during [System Setup](./system_setup.md)<br>If necessary, raplace also the standard port 5000 with your port.<br>Remove the entry User=\<user> from the [System] section<br>In section [Install], change ```WantedBy=multi-user.target``` to ```WantedBy=default.target```
4. Create the directory for systemd user units<br>```mkdir -p ~/.config/systemd/user```
5. Stage the service configuration file to systemd for user units:<br>```cp ~/raspiCamSrv.service ~/.config/systemd/user```
6. Start the service:<br>```systemctl --user start raspiCamSrv.service```
7. Check that the Flask server has started as service:<br>```journalctl --user -ef```<br>If you get ```No journal files were found.```, try<br>```sudo journalctl -ef```
8. Enable the service so that it automatically starts with a session for the active user:<br>```systemctl --user enable raspiCamSrv.service```
9. Enable lingering in order to start the unit right after boot and keep it running independently from a user session<br>```loginctl enable-linger```
10. Reboot the system to test automatic server start:<br>```sudo reboot```


## Bullseye Systems

If your system is a bullseye system (```lsb_release -a```), which is currently still the case for Pi Zero, follow these steps:

1. Open a SSH session on the Raspberry Pi
2. Clone branch 0_3_12_next of Picamera2 repository<br>```cd ~/prg```<br>```git clone -b 0_3_12_next https://github.com/raspberrypi/picamera2```
3. Copy the service template *raspiCamSrv.service* which is provided with **raspiCamSrv** to your home directory<br>```cp ~/prg/raspi-cam-srv/config/raspiCamSrv.service ~``` 
4. Adjust the service configuration:<br>```nano ~/raspiCamSrv.service```<br>- Replace '\<user>' with the user ID, specified during [System Setup](./system_setup.md)<br>- If necessary, raplace also the standard port 5000 with your port.<br>- Add another Environment entry: ```Environment="PYTHONPATH=/home/<user>/prg/picamera2"```<br>- Remove the entry User=\<user> from the [System] section<br>- In section [Install], change ```WantedBy=multi-user.target``` to ```WantedBy=default.target```<br>For an example of the final .service file, see below
5. Create the directory for systemd user units<br>```mkdir -p ~/.config/systemd/user```
6. Stage the service configuration file to systemd for user units:<br>```cp ~/raspiCamSrv.service ~/.config/systemd/user```
7. Start the service:<br>```systemctl --user start raspiCamSrv.service```
8. Check that the Flask server has started as service:<br>```journalctl --user -e```
9. Enable the service so that it automatically starts with a session for the active user:<br>```systemctl --user enable raspiCamSrv.service```
10. Enable lingering in order to start the unit right after boot and keep it running independently from a user session<br>```loginctl enable-linger```
11. Reboot the system to test automatic server start:<br>```sudo reboot```

## Example Service Configuration

Below is an example .service specification for user "sn":
```
[Unit]
Description=raspiCamSrv
After=network.target

[Service]
ExecStart=/home/sn/prg/raspi-cam-srv/.venv/bin/flask --app raspiCamSrv run --port 5000 --host=0.0.0.0
Environment="PATH=/home/sn/prg/raspi-cam-srv/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/home/sn/prg/picamera2"
WorkingDirectory=/home/sn/prg/raspi-cam-srv
StandardOutput=inherit
StandardError=inherit
Restart=always

[Install]
WantedBy=default.target
```
