# Trigger / Events

[![Up](img/goup.gif)](./TriggerOverview.md)

Event Details are shown in the Event Viewer for a specific day:

![Event Viewer](./img/Trigger_Events.gif)

In the top area, you may 

- change the active day using the date control or the arrow buttons.   
Single arrows shift by day, double arrows by week.   
In each case the starting hour is set to 00:00h.
- change the start time from which on events will be shown.   
Here, single arrows shift by a quarter of an hour, double arrows by an hour.
- You can select whether you want to see videos, photos, both or none.   
In case of videos, the first photo is always shown instead of the video on the left side, however clicking on the photo will open the video viewer.
- whether a video or a photo is represented by the small picture can be distinguished by information on the video length.

Selecting a video or photo shows it in the detail area on the right side.

## Event Card

The Event Card for each event     
![EventCard](./img/Trigger_EventCard.jpg)    
shows, from top to bottom:

- Event Type
- Event date
- Event time
- Event trigger
- Event trigger algorithm (for Motion Detection)  
[Mean Square Diff](./TriggerMotion.md)    
[Frame Diff.](./TriggerMotion.md#test-for-frame-differencing-algorithm)    
[Optical Flow](./TriggerMotion.md#test-for-optical-flow-algorithm)    
[BG Subtraction](./TriggerMotion.md#test-for-background-subtraction-algorithm)
- Trigger parameter (see [Motion](./TriggerMotion.md) tab)   
cam : Camera Num by which motion was detected    
roi : Index of the [Region of Interest](./TriggerMotion.md#regions-of-interest-and-regions-of-no-interest) in which motion was detected   
**NOTE**: Motion detection analysis is stopped whenever motion has been detected in one of the RoIs. The index of this ROI is reported here.    
msd : *Mean Square Threshold*    
BBox_thr : *Bounding Box Threshold*    
IOU_thr : *IOU Threshold*     
Motion_thr : *Motion Threshold*    
Model : *Background Subtraction Model* (1=MOG2, 2=KNN)

You may use the information to fine tune the algorithm parameters on the [Motion](./TriggerMotion.md) tab.

## Photos/Videos with ROI/RoNI

When [Photos/Videos with RoI/RoNI](./TriggerMotion.md) has been activated, borders of RoIs/RoNIs are shown on photos and videos (for "Mean Square Diff" not no videos):

- Red borders represent *Regions of Interest* where motion was detected first.
- Green borders represent the other specified *Regions of Interest.
- Blue borders represent *Regions of NO Interest.

In case that photos have been taken together with videos, this is represented as shown below.   
Videos show the video length in the footer.

![EventsVideoPhoto](./img/Trigger_Events_Photo.jpg)

## Events from configured Triggers

Events originating from configured [Triggers](./TriggerTriggers.md) (GPIO input devices, Camera action events or camera-based motion detection) are also shown on this page.

![GPIO_Events](./img/Trigger_Events_GPIO.jpg)

If the [Actions](./TriggerActions.md) associated with such a Trigger include one of the available camera actions (*take_photo*, *record_video*, *start_video*, *stop_video*), videos and photos taken will be accessible here.

If the [Trigger-Actions](./TriggerTriggerActions.md) include video actions but no action to take a photo, the system will stage a placeholder photo through which the video taken will be accessible.

If an action starts video recording (*start_video*), the video will be accessible but cannot be played while the camera is recording. The lengt of the video will be shown as "0 sec"    
If later another event fires which has an action to stop recording (*stop_video*), the system will calculate the video length as the time difference between start and stop actions.

If video recording is currently active, while an [Action](./TriggerActions.md) executes, which tries to start recording, this will not be done and the [log file](./TriggerActive.md#log-file) will show an error message

**NOTE**: Camera actions started through an [Action Button](./ConsoleActionButtons.md), the resulting video or photo will not be visible here but in the [Photo Viewer](./PhotoViewer.md). If, however, the camera action fires a trigger, this will be visible here, in case that the background process has been started.
