# System Setup for raspiCamSrv

[![Up](img/goup.gif)](./getting_started_overview.md)

Follow the instructions of the [Raspberry Pi Getting Started Documentation](https://www.raspberrypi.com/documentation/computers/os.html#get-raspberry-pi-os) for OS installation using [Imager](https://www.raspberrypi.com/documentation/computers/getting-started.html#raspberry-pi-imager).   

**NOTE**: It is recommended to install the Debian distribution proposed by [Imager](https://www.raspberrypi.com/documentation/computers/getting-started.html#raspberry-pi-imager) for your Raspberry Pi device. This is usually the full 64-bit version including desktop.   
The latest distribution is currently Trixie.

RaspiCamSrv can also be installed on Bullseye or Bookworm systems, updated to the latest version.

Lite variants of these systems, without desktop, can be used for RPI Zero models which are usually only operated in headless mode. For these, the [Automated Installer](./installation.md) will install all required features which are not included in this distribution.

Make sure that SSH is enabled on the Services tab.

Once the SD card is written, insert it into the Raspberry Pi and power it up.   
Initially, it will take several minutes until it is visible in the network.
