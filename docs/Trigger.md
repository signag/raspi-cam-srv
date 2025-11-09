# Event Handling and Triggered Capture of Videos and Photos

[![Up](img/goup.gif)](./UserGuide.md)

**raspiCamSrv** can capture events from camera and GPIO input devices and let these process actions by the camera and GPIO output devices.

##### Supported Triggers
- [Triggers](./TriggerTriggers.md) from GPIO-connected sensors


##### Additional Triggers when a Camera is available
- [Triggers](./TriggerTriggers.md) from camera events such as start and stop of video recording or streaming or [detection of motion](./TriggerMotion.md).
- [Motion Capturing](./TriggerMotion.md) through image analysis
- [Active Motion Capture](./TriggerActive.md)

##### Supported Actions
- [Actions](./TriggerActions.md) with GPIO-connected devices, such as LEDs, motors, servos or sound devices.
- SMTP [actions](./TriggerActions.md) for sending an eMail to the [configured recipient](./TriggerNotification.md).
- [Trigger-Actions](./TriggerTriggerActions.md) define which trigger will execute which action(s).
- Under [Notification](./TriggerNotification.md), you configure the general mail recipient as well as specifics for notification on [motion detection through the camera](./TriggerMotion.md). 

##### Additional Actions when a Camera is available
- Camera [actions](./TriggerActions.md), such as taking photos, starting or stopping video recording or recording a video with a given length.
- [Camera Actions](./TriggerCameraActions.md) specify the camera actions in case of [motion detection through the camera](./TriggerMotion.md).
- Under [Notification](./TriggerNotification.md), you configure whether mail notification shall include photos or videos from [motion detection through the camera](./TriggerMotion.md). 

##### Event Dashboard

- [Event Viewer](./TriggerEventViewer.md#events)
- [Calendar](./TriggerEventViewer.md)


## Event Handling Infrastructure

**raspiCamSrv** comes with two different types of event handling:

### 1. Motion Capturing

Originally supported was [Motion Capturing](./TriggerMotion.md) with photo-taking and video recording actions as well as notification by mail.    
The relevant dialogs for configuration are [Motion](./TriggerMotion.md), [Camera](./TriggerCameraActions.md) and [Notification](./TriggerNotification.md).

### 2. General Event Handling

Since version V3.3.0, **raspiCamSrv** supports a more general approach to event handling which includes not only the camera but also various kinds of input and output devices which can be connected to the Raspberry Pi's GPIO pins.

If you have no devices connected to your Raspberry Pi, you just stay with [Motion Capturing](./TriggerMotion.md).

If you have input devices, such as sensors or buttons and/or output devices, such as LEDs, buzzers, relais or motors connected to your Pi, in addition to a camera, you can benefit from the fully integrated powerful event handling of **raspiCamSrv**.

- You start with configuring the connected devices in the [Settings/Devices](./SettingsDevices.md) screen.    
- Then, for the configured input devices, you configure [Triggers](./TriggerTriggers.md) which can also be based on camera events, such as start or stop of video recording, streaming or motion capturing.
- As next, you configure any type of [actions](./TriggerActions.md) which you want to see, such as LEDs being switched on, a stepper motor executing a certain number of steps or photos and/or videos being taken with the camera.<br>In addition, you can also configure an SMTP action for being informed about an event by mail.
- Once this is done, you need to specify for each of the triggers, which actions shall be processed once an event has been triggered. This is done in dialog [Trigger Actions](./TriggerTriggerActions.md).
- In the [Triggers](./TriggerTriggers.md) and [Actions](./TriggerActions.md) dialogs, you also have the possibility to deactivate or activate triggers and actions, respectively.

### Integration

The two types of event handling exist independently from each other and can be used separately or simultaneously.    
Events from [Triggers](./TriggerTriggers.md) defined as part of the [General Event Handling](#2-general-event-handling) can also be [logged](./TriggerActive.md#log-file) and visualized in the [Event Viewer](./TriggerEventViewer.md) if their *event_log* control parameter is set to "True".

SMTP actions for mailing use the [Notification](./TriggerNotification.md) settings. Whether photos and/or videos, created during action processing, shall be included in a mail, can be configured independently for each SMTP [action](./TriggerActions.md).

In order to receive a mail on an event, you just activate one of your configured SMTP actions for the intended trigger.   
While all actions are started simultanously in individual threads, the thread for the SMTP action will wait for completion of all other actions of the same trigger and include any information and rosources from the other action threads.

### Where do Photos and Videos go?

Photos and videos taken in case of [motion detection](./TriggerMotion.md) will always be stored in the [event folder](./TriggerActive.md#event-data) while events are logged in the [log file](./TriggerActive.md#log-file) and the [database](./TriggerActive.md#database).    
Old data can be removed with the [Cleanup](./TriggerEventViewer.md#cleanup) function.

The same applies to triggers and actions of [General Event Handling](#2-general-event-handling) if the control parameter *event_log* for the trigger is set to "True*.

If this parameter is "False", photos and videos will be stored at the same location as if they were taken on the [Live](./LiveScreen.md) screen and they can be inspected in the [Photo Viewer](./PhotoViewer.md).

### Restrictions

You can use [motion capturing through the camera](./TriggerMotion.md) as trigger.   
Whereas you can associate any kind of GPIO actions with such a trigger, you can not associate any camera or SMTP action.    
This is because camrea- and SMTP actions are handled already in the [Motion Capturing](#1-motion-capturing) infrastructure, which must be activated in order to capture motion detection events.

## Control

![Triggercontrol](./img/Trigger_Control.jpg)

In the *Control* section, you may specify basic aspects of triggered actions:

Where not otherwise stated, this applies to 'legacy' [motion capturing](#1-motion-capturing) as well as to [General Event Handling](#2-general-event-handling).

- Under *Triggers*, you select the triggers to be used.   
You can activate Motion detection and/or the other *Configured Triggers*
- Under *Actions* you specify the actions to be taken in case of [motion detection through the camera](./TriggerMotion.md).   
You may select among video recording and photo taking.   
In case *Record Video* is selected, also at least one photo must be taken. This photo will serve as placeholder for the video in the [Event Viewer](./TriggerEventViewer.md).    
With *Notification* you specify whether or not you want to be informed by e-Mail about an event. The details need to be specified on the [Notification](./TriggerNotification.md) tab.    
**ATTENTION**: If you have chosen to only activate *Configured Triggers* without *Motion Detection*, the listed Actions will be deactivated because they are only supported with *Motion Detection*.<br>From the *Configured Triggers*, the configured [Trigger-Actions](./TriggerTriggerActions.md) will be executed, which may also include camera actions.
- With *Operation Weekdays*, you specify the weekdays when triggering shall be active.
- *Operation Start* specifies the daytime when triggering is activated on each active weekday.
- *Operation End* specifies the daytime when triggering is paused.
- *Automatic Start with Server*   
When activated, the trigger capturing process can be automatically started with the server.   
When you change this parameter, you need to go to [Settings](./Settings.md) and store the current [Server Configuration](./SettingsConfiguration.md)   
If you want automatic start, you also need to select *Start Server with stored Configuration*.    
**Note** In case you start the Flask server manually, do not use the ```--debug``` option. This will cause an exception (see [Flask Issue #5437](https://github.com/pallets/flask/discussions/5437)).
- *Detection Delay* allows specifying a delay in seconds. When an event is triggered, the configured action (video and/or photo, Notification) will be delayed by the specified number of seconds. Normally, this will be 0.<br>This applies to motion-captured events only.    
- *Detection Pause* specifies a 'dead time' after an event has been registerd. Within this time no new event will be registered although the system will not stop detecting motion.    
This setting prevents from being flooded with registered events, for example if motion persists for a longer time.    
Detection pause (and alse *Detection Delay*), configured here, does not apply to the configured [Triggers](./TriggerTriggers.md). For these, it is possible to specify *bouncing-time* individually for every trigger.
- *Retention Period* specifies the number of days  for which event data will be retained when a [cleanup](./TriggerEventViewer.md#cleanup) is done.<br>This does not apply for photos or videos which have been taken on triggers for which *event_log* was set to "False"

Data changes will not be persisted unless the **Submit** button has been pressed.

## Starting Trigger capturing

Trigger- and event handling is activated using the *Start* button.

Depending on the selected Triggers, *Motion Detection* and/or *Configured Triggers* are started.

Which process is currently active is indicated by the [status indicators](./UserGuide.md#process-status-indicators):

- Motion detection only:    
![Proc13](./img/ProcessIndicator14.jpg)
- Configured Triggers only:    
![Proc13](./img/ProcessIndicator15.jpg)
- Both    
![Proc13](./img/ProcessIndicator13.jpg)

Note that, whenever Motion Detection is active, also the live stream will be kept active because this is used to detect motion.

For active of motion capturing, see [Active Motion Capturing](./TriggerActive.md) 

