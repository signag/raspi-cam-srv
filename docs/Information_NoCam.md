# raspiCamSrv Information (No Camera)

[![Up](img/goup.gif)](./UserGuide_NoCam.md)

This is a variant of the general [Information](./Information.md) screen which shows up when no camera is available.

## Info

![Cameras](img/Info-No-Cameras.jpg)

### Raspberry Pi

This section shows information on the server hardware with *Model* and *Board Revision*

For the operating system, the kernel version (result of ```uname -r```), the Debian version (result of *Description* from ```lsb_release -a``` and ```cat /etc/debian_version```) and the system architecture (32-/64-bit) (result from ```dpkg-architecture --query DEB_HOST_ARCH```) are shown.

*Process Info* shows current process information for the raspiCamSrv server process (result of Linux ```ps -eLf``` command)
- *PID*: Process ID of Flask process (PID)
- *Start*: Process start time (STIME): either start time (HH:MM) at current day or day (MonDD) when process was started.
- *#Threads*: Number of threads (NLWP)
- *CPU Process*: CPU time of process (TIME for LWP == PID) in HH:MM:SS
- *CPU Threads*: Sum of CPU time for threads ((TIME for LWP != PID)) in %H:MM:SS

*FFmpeg Info* shows information on an ffmpeg process if encoding of .mp4 videos is currently active.   
Recording of .mp4 videos may have been [started manually](./Phototaking.md) or as an action within [motion capturing](./Trigger.md)

*raspiCamSrv Start* shows the time when the raspiCamSrv server has been started.   
At server start, raspiCamSrv checks whether or not the Raspberry Pi system time is synchronized with the time server.   
When the device is booted and raspiCamSrv is automatically started, the time syncronization will occasionally be done after the Flask server has already been started.    
In this case, in order to avoid timing issues, raspiCamSrv will wait at startup until time syncronization is completed.   
The time shown here is the system time at the moment when the check for time synchrinization was successful.   
raspiCamSrv analyzes the output of command ```timedatectl``` to check the system clock synchronization status.    
If this check fails or times out (60 sec), raspiCamSrv will start nevertheless. In this case, the information "System time not synced at raspiCamSrv start" will be shown here.

### Camera x

The tab lists all cameras currently connected to the system.    
In the situation where currently no camera is available, the list will only include USB cameras because CSI cameras, if connected, will always be activated.

Each camera has an identifying number (0, 1, ...) shown in the title above each parameter list.

The information "(Not in use)" indicates that the camera has been detected by **raspiCamSrv** but it is not in use because USB cameras have been deactivated in the [Settings](./Settings_NoCam.md).

For USB cameras, the device through which the camera is accessible is also shown.

#### Camera connected but not in the list?

If you have a USB camera connected which does not show up in the list, you may have plugged in the camera while **raspiCamSrv** was running.   
In this case, you can use function [Reload Cameras](./SettingsConfiguration_NoCam.md) to identify hot-plugged cameras.

## Detection of Cameras

See [Detection of Cameras](./Information.md#detection-of-cameras)