# raspiCamSrv Information on Camera System

[![Up](img/goup.gif)](./UserGuide.md)

This screen contains several tabs with information on the camera system:

## Cameras

![Cameras](img/Info-Cameras.jpg)

### Raspberry Pi

This section shows information on the server hardware with *Model* and *Board Revision*

### Camera x

The tab lists all cameras currently connected to the system.

Each camera has an identifying number (0, 1, ...) shown in the title above each parameter list.

**raspiCamSrv** detects also USB cameras, however, these are not supported, which is indicated in the title.

When the server starts up, the first camera, which is not a USB camera, is selected.

You may later switch to another non-USB camera on the [Settings](./Settings.md) screen

The active camera is indicated in the list.

The active camera will also be shown in the title bar of the application after log-in,

## Camera Properties

![Camera Properties](img/Info-CamProps.jpg)

These are the properties of the camera which is currently active.

## Sensor Modes

The camera system advertises the supported Sensor Modes with their characteristics.

These are referred to within the [Camera Configuration](./Configuration.md).

The characteristics vor every Sensor Mode are shown on an individual tab:

![Sensor Mode](img/Info_SensorMode.jpg)