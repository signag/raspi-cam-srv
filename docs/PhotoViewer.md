raspiCamSrv Photo Viewer

All photos, raw photos or videos taken wit **raspiCamSrv** are stored in a camera-specific folder on the server.

Currently, the folder is located within the folder where Flask expects static content.   
The full path of the folder for the active camera is shown in the [Settings](./Settings.md) screen.

The current implementation of **raspiCamSrv** includes a very simple viewer which allows to inspect the available files:

![Photos](img/Photos.jpg)

[![Up](img/goup.gif)](./UserGuide.md)

On the left side, a chunk of photos (placeholders for raw and video) are shown in reverse order with the newest one on top.

The file name in the photo (or placeholder) shows the correct filename of the resource represented by the picture.

Below the list, there is a pagination infrastructure allowing to select specific pages or go forward or backward.

The page size (chunk size) can be specified in the [Settings](./Settings.md) screen.

A large view of the photo or a video player is presented when a specific picture has been clicked on.