# Setup of Raspberry Pi Zero as Standalone System

[![Up](img/goup.gif)](./getting_started_overview.md)

This section describes how to set up a Raspberry Pi **Zero W** or **Zero 2 W** as standalone system.

This will allow you placing the Raspi camera anywhere, independently from an accessible Wi-Fi.

It will act as hotspot to which you can connect from a mobile client to gain access to **raspiCamSrv**.

The subsequent descriptions can, in principle, also be applied for other Raspberry Pi models.

## Headless Setup

During the setup of such a system, the Raspberry Pi requires a cabled network connection because the Wi-Fi adapter will be configured as hotspot and is, therefore, not available for access by the configuration client.

Connections to a display, keyboard and mouse are not required.

![Standalone Setup](./img/bp_PiZero_Connect.jpg)

Required [cables and adapters](https://www.raspberrypi.com/products/#power-supplies-and-cables):

- USB A to Ethernet adapter
- Micro USB/Male to USB A/Female cable
- Power supply with Micro USB plug

## 1. Install OS on microSD Card

Follow the instructions for [Install using Imager](https://www.raspberrypi.com/documentation/computers/getting-started.html#raspberry-pi-imager).

- **Model**<br>
Make sure to select the correct model
- **Bullseye, Bookworm or Trixie?**<br>
raspiCamSrv can be used with all of these systems.<br>
Unless other reasons force taking one of the older OS, it is recommended to use the officially recommended, which is currently Trixie.
- **Full or lite system?**<br>
It is recommended to install the full system although the desktop environment will not be required.
- **OS Customisation**<br>
Make sure to *Configure wireless LAN*, although the Wi-Fi Adapter will later not be run in client mode,<br>
however this will assure that the *Wireless LAN Country* will be set.

## 2. Power Up

1. If camera applications are intended, connect the camera (the small CSI-2 port of Pi Zero and Pi 5 require a special cable)
2. Insert the microSD card into the card slot
3. If available, encapsulate the Pi into a case
4. Connect the network USB cable through an ethernet adapter to a switch of your local network
5. Connect the power supply

## 3. Connect and upgrade

The system may take some time until it is visible within the network.

From a client device connect via SSH<br>

```
ssh <user>@<hostname>

...

sudo apt update
sudo apt full-upgrade
```

## 4. Configure Hotspot

The process of configuration is slightly different, depending on the cosen OS:

- [Hotspot Configuration for 'Trixie' OS](./bp_Hotspot_Trixie.md)
- [Hotspot Configuration for 'Bookworm' OS](./bp_Hotspot_Bookworm.md)
- [Hotspot Configuration for 'Bullseye' OS](./bp_Hotspot_Bullseye.md)

## 5. Install raspiCamSrv

For installation, you will need to connect through ethernet.

Then, follow the [raspiCamSrv Installation Procedure](./installation.md), which will also do the Service configuration.

## 6. Test

After rebooting, first test using the client connected with ethernet cable.

If this is successfull, you can shutdown and unplug the ethernet cable.

After restart, connect from a mobile client to the hotspot and connect to raspiCamSrv from a browser window.    
**NOTE**, that for the [Trixie setup](./bp_Hotspot_Trixie.md), you need to use ```<hostname>.local``` instead of ```hostname```.


## Updating a Stanalone RaspiCamSrv System

Since the standalone system has no internet connection, you will not be notified on new **raspiCamSrv** versions (see [Update notification through coloured version number](./UserGuide.md#title-bar)).

When you are aware of an update, you need to connect the standalone Raspberry Pi to a network with internet access using an ethernet cable.

Then, you can use the [Update function](./SettingsUpdate.md) to check for updates and for updating **raspiCamSrv**.