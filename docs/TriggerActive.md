# Triggered Capture of Videos and Photos

[![Up](img/goup.gif)](./Trigger.md)

# Active Motion Capturing

The *Start* button on the *Control* page starts the trigger capturing process.

![ActiveCapture](./img/Trigger_Active.jpg)

An active capture process is indicated with red [Process Status Indicator](./UserGuide.md#process-status-indicators)

The *Start* button has changed to *Stop*, which allows stopping the process.

If motion capturing is currently active but operation paused because of schedule settings, this is indicated by a yellow process status indicator:

![Capturepaused](./img/ProcessIndicator8.jpg)

## Event Data

Event data are stored in directory ```./prg/raspi-cam-srv/raspiCamSrv/static/events```:

![Eventstorage](./img/Trigger_Storage.jpg)

Storage includes a log file as well as video and photo files.

## Parallel Activities

While motion capturing is active, the live stream process will be kept active because this is used for motion detection.

While motion capturing is active, you may continue working with **raspiCamSrv**.   
You may even take photos, videos or photo series.

However, you should avoyd changing camera controls or configuration because this would restart the camera

## Log File

While events are registered and videos and photos are taken, the system maintains a log file with antries for all events and the times when photos are captured or videos are started and stopped:

![EventLog](./img/Trigger_Logfile.jpg)

The log file of the above screenshot shows examples with and without delayed actions as well as with configurations with just one or with 4 photos in the *Photo Burst*.    
There is also a situation represented where no more motion was detected after the configured delay pariod of 2 seconds. In this case, the event has been registered but no video or photo has been captured.

## Database

Events and event actions are also stored in the SQLite3 database stored at   
```./prg/raspi-cam-srv/instance/raspiCamSrv.sqlite```.

The primary purpose of the database is providing fast access to event data over a longer period for the [Event Viewer](./TriggerEventViewer.md)

![TriggerDB](./img/Trigger_DB.jpg)

Table *events* holds all individual events:

![DBEvents](./img/Trigger_DB_Events.jpg)

Table *eventactions* holds the actions taken for each event:

![DBEventactions](./img/Trigger_DB_Eventactions.jpg)