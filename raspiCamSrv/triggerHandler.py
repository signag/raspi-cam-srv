from gpiozero import Button, LineSensor, MotionSensor, LightSensor, DistanceSensor, RotaryEncoder, DigitalInputDevice
from gpiozero import LED, PWMLED, RGBLED, Buzzer,TonalBuzzer, Motor,PhaseEnableMotor, Servo, AngularServo, DigitalOutputDevice, OutputDevice
from raspiCamSrv.gpioDevices import StepperMotor
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.motionDetector import MotionDetector
from raspiCamSrv.camCfg import CameraCfg, TriggerConfig, ServerConfig, GPIODevice, Trigger, Action
from _thread import get_ident
from datetime import datetime, timedelta
from raspiCamSrv.dbx import get_dbx
from sqlite3 import Connection
from uuid import uuid4, UUID
import smtplib
import json
from email.message import EmailMessage
import mimetypes
import time
import threading
import logging

logger = logging.getLogger(__name__)

class TriggerHandler():
    """ Class for trigger and event handling
    
    """
    logger.debug("Thread %s: TriggerHandler - setting class variables", get_ident())
    _instance = None
    _registry = {}
    _registry_lock = threading.Lock()
    _sub_threads = []
    _list_lock = threading.Lock()
    _event_contexts = []
    _context_lock = threading.Lock()
    _livestream_lock = threading.Lock()
    triggerThread = None
    triggerThreadStop = False

    def __new__(cls):
        logger.debug("Thread %s: TriggerHandler.__new__", get_ident())
        if cls._instance is None:
            logger.debug("Thread %s: TriggerHandler.__new__ - Instantiating Class", get_ident())
            cls._instance = super(TriggerHandler, cls).__new__(cls)
        return cls._instance
                    
    @staticmethod
    def _isActive() -> bool:
        """ Check whether trigger is supposed to be active

        This is controlled by operation times specified in CameraCfg().triggerConfig

        Returns:
            bool: true when triggering is active
        """
        active = True
        cfg = CameraCfg()
        tc = cfg.triggerConfig
        
        now = datetime.now()
        wd = str(now.isoweekday())
        if tc.operationWeekdays[wd] == True:
            h = now.hour
            m = now.minute
            dm = 60 * h + m
            if dm >= tc.operationStartMinute \
            and dm <= tc.operationEndMinute:
                active = True
            else:
                active = False
        else:
            active = False
        if active:
            cfg.serverConfig.isEventsWaiting = False
        else:
            cfg.serverConfig.isEventsWaiting = True
        return active
    
    @classmethod
    def _findDeviceInRegistry(cls, source: str, deviceId: str, sc:ServerConfig, busy:bool) -> tuple[bool, dict]:
        """ Find the registry entry for the specified device class
        
        A specific device can be used in multiple triggers or actions.
        Every device must be instantiated only once. 
        For GPIO devices, a second try would result in a "Device in use" error.
        Therefore instantiated devices are stored in the registry for later access
        Camera and MotionDetector devices are singletons, 
        but their class is stored in the registry for unregistration.
        
        The registry structure is:
        - source ("GPIO")
            +- deviceId
                 +- "deviceClass" : device type (class name)
                 +- "deviceObject": reference to instantiated device object
                 +- "busy"        : true if the device is currently busy  
                 +- "lastAccess   : Time of last access to a device
                 +- "methods"     : Methods to which callbacks are assigned
                 +- ...
        - source ("Camera" or "MotionDetector")
            +- deviceId
                 +- "deviceClass" : device type (class name)
                 +- "deviceObject": reference to instantiated device object
                 +- "methods"     : Methods to which callbacks are assigned

        Args:
            source (str)      : source of device, e.g. "GPIO"
            deviceId (str)    : ID of the device (key element)
            sc (ServerConfig) : Server Configuration object which holds device information
            busy (bool)       : Busy state to be set

        Raises:

        Returns:
            bool: True if device was not busy and busy state was set
                  or if the device was not busy and busy state was not requested
            dict: Dictionary entry for the device - level deviceId.
                  If an entry for the device does not yet exist, it will be created
        """
        logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - source=%s deviceId=%s", get_ident(), source, deviceId)

        res = {}
        busyAcquired = False
        with cls._registry_lock:
            if not source in cls._registry:
                cls._registry[source] = {}

            if not deviceId in cls._registry[source]:
                cls._registry[source][deviceId] = {}
                
            if not "deviceClass" in cls._registry[source][deviceId]:
                if source == "GPIO":
                    device = sc.getDevice(deviceId)
                    deviceClass = device.type
                    deviceArgs = device.params
                    cls._registry[source][deviceId]["deviceClass"] = deviceClass

                    # Instantiate device object
                    deviceObj = globals()[deviceClass](**deviceArgs)
                    device.setState(deviceObj)
                    logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - instantiated: %s(%s)", get_ident(), deviceClass, deviceArgs)
                    cls._registry[source][deviceId]["deviceObject"] = deviceObj
                elif source == "Camera":
                    device = deviceId
                    deviceClass = "Camera"
                    deviceArgs = {}
                    cls._registry[source][deviceId]["deviceClass"] = deviceClass

                    # Nothing to instantiate for Camera
                    deviceObj = Camera()
                    logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - instantiated: %s(%s)", get_ident(), deviceClass, deviceArgs)
                    cls._registry[source][deviceId]["deviceObject"] = deviceObj
                elif source == "MotionDetector":
                    device = deviceId
                    deviceClass = "MotionDetector"
                    deviceArgs = {}
                    cls._registry[source][deviceId]["deviceClass"] = deviceClass

                    # Nothing to instantiate for Camera
                    deviceObj = MotionDetector()
                    logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - instantiated: %s(%s)", get_ident(), deviceClass, deviceArgs)
                    cls._registry[source][deviceId]["deviceObject"] = deviceObj
                
            if not "methods" in cls._registry[source][deviceId]:
                cls._registry[source][deviceId]["methods"] = []

            if source == "GPIO":
                if not "busy" in cls._registry[source][deviceId]:
                    cls._registry[source][deviceId]["busy"] = busy
                    if busy == True:
                        busyAcquired = True
                else:
                    if busy == True:
                        if cls._registry[source][deviceId]["busy"] == True:
                            busyAcquired = False
                        else:
                            cls._registry[source][deviceId]["busy"] = True
                            busyAcquired = True
                    else:
                        if cls._registry[source][deviceId]["busy"] == True:
                            cls._registry[source][deviceId]["busy"] = False
                            busyAcquired = False
                        else:
                            busyAcquired = True
            if source == "GPIO":
                if busyAcquired == True:
                    cls._registry[source][deviceId]["last_access"] = datetime.now()

            res = cls._registry[source][deviceId]
            logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - Returning:busyAcquired=%s res=%s", get_ident(), busyAcquired, res)
        return busyAcquired, res
    
    @classmethod
    def _bouncing(cls, trg:Trigger, sc:ServerConfig) -> bool:
        """ Check for bouncing

        If the time difference between the current time and the time of last device access
        is larger than the bouncing time for the trigger (if defined), bouncing is assumed.
        
        Returns:
            bool: True if bouncing
        """
        logger.debug("Thread %s: TriggerHandler._bouncing - trigger.id=%s", get_ident(), trg.id)
        res = False
        
        with cls._registry_lock:
            control = trg.control
            if "bounce_time" in control:
                bounce_time = control["bounce_time"]
                logger.debug("Thread %s: TriggerHandler._bouncing - bounce time=%s", get_ident(), bounce_time)
                if bounce_time > 0.0:
                    source = trg.source
                    device = sc.getDevice(trg.device)
                    deviceId = device.id
                    logger.debug("Thread %s: TriggerHandler._bouncing - Checking reg for: source:%s, deviceId:%s", get_ident(), source, deviceId)
                    if source in cls._registry:
                        if deviceId in cls._registry[source]:
                            reg = cls._registry[source][deviceId]
                            logger.debug("Thread %s: TriggerHandler._bouncing - found reg: %s", get_ident(), reg)
                            if "last_access" in reg:
                                lastAccess = reg["last_access"]
                                logger.debug("Thread %s: TriggerHandler._bouncing - last_access: %s", get_ident(), lastAccess)
                                now = datetime.now()
                                diff = now - lastAccess
                                secs = diff.total_seconds()
                                if secs < bounce_time:
                                    res = True
                                    logger.debug("Thread %s: TriggerHandler._bouncing - bouncing - timediff: %s s", get_ident(), secs)
                                else:
                                    logger.debug("Thread %s: TriggerHandler._bouncing - Nobouncing - timediff: %s s", get_ident(), secs)
                                    reg["last_access"] = datetime.now()
                            else:
                                reg["last_access"] = datetime.now()
            logger.debug("Thread %s: TriggerHandler._bouncing - Result: %s", get_ident(), res)
        return res

    @classmethod    
    def _doGpioAction(cls, action:Action, trigger:Trigger=None, eventId:UUID=None, last:bool=False, threadRegistered:bool=True, wait:bool=True) -> bool:
        """ Execute an action with a GPIO device

        Args:
            action (Action): The action to execute
            trigger (Trigger): Trigger on behalf of which the action is executed
            eventId (UUID): Unique ID of the event in the context of which the action is executed
            threadRegistered (bool): if True, the thread is registered in the sub_threads list and must be unregistered
                                    after completion
        """
        if trigger:
            triggerDisp = trigger.id
        else:
            triggerDisp = "No Trigger"
        logger.debug("Thread %s: TriggerHandler._doGpioAction - action=%s trigger.id=%s - starting - wait=%s last=%s", get_ident(), action.id, triggerDisp, wait, last)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        
        isEvent = False
        if trigger:
            triggerCtrl = trigger.control
            if "event_log" in triggerCtrl:
                event_log = triggerCtrl["event_log"]
                if event_log == True:
                    isEvent = True
                    db = get_dbx()

        deviceId = action.device
        
        done = False
        
        acquired, reg = cls._findDeviceInRegistry("GPIO", deviceId, sc, busy=True)
        if wait == True:
            while acquired == False:
                time.sleep(0.1)
                acquired, reg = cls._findDeviceInRegistry("GPIO", deviceId, sc, busy=True)

        if acquired:
            if isEvent == True:
                db = get_dbx()
            deviceClass = reg["deviceClass"]
            deviceObj = reg["deviceObject"]
            method = action.method
            methodParams = action.params
            actionCtrl = action.control
            logger.debug("Thread %s: TriggerHandler._doGpioAction - deviceClass=%s method=%s params=%s", get_ident(), deviceClass, method, methodParams)

            # Update action context
            eCtx = cls._getEventContext(eventId)
            ctx = cls._getActionContext(eventId, action.id)
            ctx["action_start"] = datetime.now()

            try:
                # Apply action method
                if hasattr(deviceObj, method):
                    logger.debug("Thread %s: TriggerHandler._doGpioAction - class: %s has method: %s", get_ident(), deviceClass, method)
                    attr = getattr(deviceObj, method)
                    if callable(attr) == True:
                        logger.debug("Thread %s: TriggerHandler._doGpioAction - method: %s - is callable", get_ident(), method)
                        if len(methodParams) > 0:
                            call = f"{deviceClass}.{method}({methodParams})"
                            logger.debug("Thread %s: TriggerHandler._doGpioAction - calling: %s", get_ident(), call)
                            result = attr(**methodParams)
                            logger.debug("Thread %s: TriggerHandler._doGpioAction Action:%s - %s=%s", get_ident(),  action.id, call, result)
                        else:
                            call = f"{deviceClass}.{method}()"
                            logger.debug("Thread %s: TriggerHandler._doGpioAction - calling: %s", get_ident(), call)
                            result = attr()
                            logger.debug("Thread %s: TriggerHandler._doGpioAction Action:%s - %s=%s", get_ident(),  action.id, call, result)
                    else:
                        logger.debug("Thread %s: TriggerHandler._doGpioAction - method: %s - is not callable", get_ident(), method)
                        if len(methodParams) > 0:
                            for key, value in methodParams.items():
                                if value != "":
                                    assignment = f"{deviceClass}.{method}={value}"
                                    setattr(deviceObj, method, value)
                                    logger.debug("Thread %s: TriggerHandler._doGpioAction Action: %s - %s", get_ident(),  action.id, assignment)
                                else:
                                    call = f"{deviceClass}.{method}"
                                    result = attr
                                    logger.debug("Thread %s: TriggerHandler._doGpioAction Action: %s - %s", get_ident(),  action.id, call)
                                break
                        else:
                            call = f"{deviceClass}.{method}"
                            result = attr
                            logger.debug("Thread %s: TriggerHandler._doGpioAction Action: %s - %s", get_ident(),  action.id, call)
                else:
                    logger.debug("TriggerHandler._doGpioAction - Action %s - Method %s not found in %s", action.id, method, deviceClass)

                # Log
                if isEvent == True:
                    cls._logEvent(db, "gpio_action", tc, eCtx, ctx)
            except Exception as e:
                logger.error("TriggerHandler._doGpioAction - Error %s: %s", type(e), e)
                err = f"Error {type(e)} while executing action: {e}"
                if isEvent == True:
                    cls._logEvent(db, "gpio_action_error", tc, eCtx, ctx, err=err)
                tc.error = f"Error {type(e)} while executing action {action.id}: {e}"
                
            # Wait for the specified duration
            if "duration" in actionCtrl:
                duration = actionCtrl["duration"]
                if duration > 0.0:
                    time.sleep(duration)
                    # Then try off() or stop()
                    method = ""
                    if hasattr(deviceObj, "off"):
                        method = "off"
                    else:
                        if hasattr(deviceObj, "stop"):
                            method = "stop"
                    if method != "":
                        attr = getattr(deviceObj, method)
                        logger.debug("Thread %s: TriggerHandler._doGpioAction - Trying to stop device with method %s", get_ident(), method)
                        try:
                            attr()
                        except Exception as e:
                            logger.error("TriggerHandler._doGpioAction - Error while stopping %s with %s: %s: %s", deviceId, method, type(e), e)
            # Track state
            device = sc.getDevice(deviceId)
            device.trackState(deviceObj)

            # Release busy state
            cls._findDeviceInRegistry("GPIO", deviceId, sc, busy=False)
            ctx["action_stop"] = datetime.now()
            # Log stop
            if isEvent == True:
                cls._logEvent(db, "gpio_action_finished", tc, eCtx, ctx)
            done = True
        else:
            logger.debug("Thread %s: TriggerHandler._doGpioAction - action=%s trigger.id=%s - Not executing. Device busy", get_ident(), action.id, triggerDisp)

        if last == True:
            # Finalize event
            cls._finalizeEvent(eventId)
            
        # Remove sub_thread from the list of threads
        if threadRegistered == True:
            thread = threading.current_thread()
            with cls._list_lock:
                if thread in cls._sub_threads:
                    cls._sub_threads.remove(thread)

        logger.debug("Thread %s: TriggerHandler._doGpioAction - action=%s trigger.id=%s terminated", get_ident(), action.id, triggerDisp)
        return done
    
    @classmethod
    def _videoTimer(cls, action:Action, isEvent:bool, sc:ServerConfig, tc:TriggerConfig, eventId:UUID):
        """ Record video with duration according to action control. Then stop

        Args:
            action (Action): Action
            sc (ServerConfig): Server configuration

        """
        logger.debug("Thread %s: TriggerHandler._videoTimer", get_ident())

        actionCtrl = action.control
        if "duration" in actionCtrl:
            duration = actionCtrl["duration"]
            time.sleep(duration)
        
        if isEvent:
            db = get_dbx()
        else:
            db = None
        
        cls._doStopVideo(action, isEvent, sc, tc, eventId, db)

        thread = threading.current_thread()
        with cls._list_lock:
            if thread in cls._sub_threads:
                cls._sub_threads.remove(thread)

        logger.debug("Thread %s: TriggerHandler._videoTimer - action=%s terminated", get_ident(), action.id)

    
    @classmethod
    def _doRecordVideo(cls, action:Action, isEvent:bool, sc:ServerConfig, tc:TriggerConfig, eventId:UUID, db:Connection) -> tuple[bool, str]:
        """ Record video according to action details

        Args:
            action (Action): Action
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            eventId (UUID): Unique ID of the event in the context of which the action is executed

        Returns:
            tuple[bool, str]:
                bool: True when recording was started
                str:  Error message in case of errors
        """
        logger.debug("Thread %s: TriggerHandler._doRecordVideo", get_ident())
        
        done = False
        
        done, msg = cls._doStartVideo(action, isEvent, sc, tc, eventId, db)
        
        recordingThread = threading.Thread(target=cls._videoTimer, args=(action, isEvent, sc, tc, eventId))
        ctx = cls._getActionContext(eventId, action.id)
        ctx["thread"] = recordingThread
        recordingThread.start()
        cls._sub_threads.append(recordingThread)
            
        return done,msg
    
    @classmethod
    def _doStartVideo(cls, action:Action, isEvent:bool, sc:ServerConfig, tc:TriggerConfig, eventId:UUID, db:Connection) -> tuple[bool, str]:
        """ Start video recording according to action details

        Args:
            action (Action): Action
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            eventId (UUID): Unique ID of the event in the context of which the action is executed

        Returns:
            tuple[bool, str]:
                bool: True when recording was started
                str:  Error message in case of errors
        """
        logger.debug("Thread %s: TriggerHandler._doStartVideo", get_ident())
        # Update action context
        eCtx = cls._getEventContext(eventId)
        ctx = cls._getActionContext(eventId, action.id)
        ctx["action_start"] = datetime.now()
        
        msg = ""
        done = False
        methodParams = action.params

        typ = sc.videoType
        if "type" in methodParams:
            typ = methodParams["type"]
            if typ == "mp4" \
            or typ == "h264":
                pass
            else:
                logger.error("TriggerHandler._doStartVideo - Action %s - Invalid 'type': %s", action.id, typ)
                msg = f"Action {action.id} - 'type': {typ} invalid. "
                typ = sc.videoType

        timeImg = datetime.now()
        if isEvent == True:
            path = tc.actionPath
            filenameVid = timeImg.strftime("%Y-%m-%dT%H-%M-%S") + "." + typ
            filename = ""
        else:
            path = ""
            filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + typ
            filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType

        if not "video" in ctx:
            ctx["video"] = {}
        video = ctx["video"]
        video["video_start"] = timeImg
        video["video_file"] = filenameVid
        logger.debug("Thread %s: TriggerHandler._doStartVideo - Recording a video %s", get_ident(), filenameVid)
        try:
            fp = Camera().recordVideo(filenameVid, filename, alternatePath=path, noEvents=True)
            video["video_path"] = fp
            time.sleep(2)
            if not sc.error:
                if Camera.isVideoRecording():
                    logger.debug("Thread %s: TriggerHandler._doStartVideo - Video recording started", get_ident())
                    sc.isVideoRecording = True
                    if sc.recordAudio:
                        sc.isAudioRecording = True
                    msg = f"Video recording started {fp}"

                    if isEvent == True:
                        cls._logEvent(db, "video_start",tc, eCtx, ctx)
                    done = True
                else:
                    logger.debug("Thread %s: TriggerHandler._doStartVideo - Video recording did not start", get_ident())
                    sc.isVideoRecording = False
                    sc.isAudioRecording = False
                    msg = "Start of video recording failed. Probably the requested resolution too high"
            else:
                msg = "Error in " + sc.errorSource + ": " + sc.error
        except Exception as e:
            logger.error("TriggerHandler._doStartVideo - Error %s: %s", type(e), e)
            sc.isVideoRecording = False
            sc.isAudioRecording = False
            msg = f"Error {type(e)} while starting video recording: {e}"
            tc.error = f"Error {type(e)} while starting video recording: {e}"

        if done == False:
            if isEvent == True:
                cls._logEvent(db, "video_start_err", tc, eCtx, ctx, err=msg)
            
        return done, msg
        
    @classmethod
    def _doStopVideo(cls, action:Action, isEvent:bool, sc:ServerConfig, tc:TriggerConfig, eventId:UUID, db:Connection) -> tuple[bool, str]:
        """ Stop video recording according to action details

        Args:
            action (Action): Action
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            eventId (UUID): Unique ID of the event in the context of which the action is executed

        Returns:
            tuple[bool, str]:
                bool: True when photo(s) were taken
                str:  Error message in case of errors
        """
        logger.debug("Thread %s: TriggerHandler._doStopVideo", get_ident())
        msg = ""
        done = False

        # Get action context
        eCtx = cls._getEventContext(eventId)
        ctx = cls._getActionContext(eventId, action.id)
        if not "video" in ctx:
            ctx["video"] = {}
        video = ctx["video"]
        try:
            Camera().stopVideoRecording(noEvents=True)
            video["video_stop"] = datetime.now()
            time.sleep(2)
            if Camera.isVideoRecording() == False:
                sc.isVideoRecording = False
                sc.isAudioRecording = False
                if isEvent == True:
                    cls._logEvent(db, "video_stop", tc, eCtx, ctx)
                done = True
                logger.debug("Thread %s: TriggerHandler._doStopVideo - Video recording stopped", get_ident())
                msg="Video recording stopped"
            else:
                logger.debug("Thread %s: TriggerHandler._doStopVideo - Video recording did not stop", get_ident())
                msg="Video recording did not stop"
        except Exception as e:
            logger.error("TriggerHandler._doStopVideo - Error %s: %s", type(e), e)
            msg = f"Error {type(e)} while stopping video recording: {e}"
            tc.error = f"Error {type(e)} while stopping video recording: {e}"
            
        if done == False:
            if isEvent == True:
                cls._logEvent(db, "video_stop_err", tc, eCtx, ctx, err=msg)

        ctx["action_stop"] = datetime.now()

        return done, msg
    
    @classmethod
    def _doTakePhoto(cls, action:Action, isEvent:bool, sc:ServerConfig, tc:TriggerConfig, eventId:UUID, db:Connection) -> tuple[bool, str]:
        """ Take photo(s) according to action details

        Args:
            action (Action): Action
            isEvent (bool): True if the action is handled as event
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            eventId (UUID): Unique ID of the event in the context of which the action is executed

        Returns:
            tuple[bool, str]:
                bool: True when photo(s) were taken
                str:  Error message in case of errors
        """
        logger.debug("Thread %s: TriggerHandler._doTakePhoto - entry", get_ident())
        
        msg = ""
        done = False
        methodParams = action.params
        actionCtrl = action.control
        # Get action context
        eCtx = cls._getEventContext(eventId)
        ctx = cls._getActionContext(eventId, action.id)
        ctx["action_start"] = datetime.now()

        typ = sc.photoType
        if "type" in methodParams:
            typ = methodParams["type"]
            if typ == "jpg" \
            or typ == "jpeg" \
            or typ == "bmp" \
            or typ == "png" \
            or typ == "gif" \
            or typ == "dng":
                pass
            else:
                logger.error("TriggerHandler._doTakePhoto - Action %s - Invalid 'type': %s", action.id, typ)
                msg = f"Action {action.id} - 'type': {typ} invalid. "
                typ = sc.photoType
        burstCount = 1
        burstIntvl = 0
        photoCtx = {}
        if "burst_count" in actionCtrl:
            burstCount = actionCtrl["burst_count"]
        if "burst_intvl" in actionCtrl:
            burstIntvl = actionCtrl["burst_intvl"]
        try:
            ctx["photos"] = []
            for count in range(0, burstCount):
                timeImg = datetime.now()
                if isEvent == True:
                    path = tc.actionPath
                    file = timeImg.strftime("%Y-%m-%dT%H-%M-%S")
                else:
                    path = ""
                    file = timeImg.strftime("%Y%m%d_%H%M%S")
                if typ == "dng":
                    filename = file + "." + sc.photoType
                    filenameRaw = file + "." + typ
                    fp = Camera().takeRawImage(filenameRaw, filename, alternatePath=path, noEvents=True)
                else:
                    filename = file + "." + typ
                    fp = Camera().takeImage(filename, alternatePath=path, noEvents=True)
                    
                photoCtx = {}
                photoCtx["photo_time"] = timeImg
                photoCtx["photo_file"] = filename
                photoCtx["photo_path"] = fp
                ctx["photos"].append(photoCtx)
                logger.debug("Thread %s: TriggerHandler._doTakePhoto - Image saved as %s", get_ident(), fp)
                time.sleep(burstIntvl)
                if burstCount == 1:
                    msg = f"{msg}Photo taken: {fp}"
                else:
                    if count == 0:
                        msg = f"{msg}{burstCount} photos taken: {fp} ..."
                # log
                if isEvent == True:
                    cls._logEvent(db, "photo_taken", tc, eCtx, ctx, photoCtx)                     
                done = True
        except Exception as e:
            logger.error("TriggerHandler._doTakePhoto - error %s: %s", type(e), e)
            msg = f"Error {type(e)} while taking a photo: {e}"
            tc.error = f"Error {type(e)} while taking a photo: {e}"
        
        if done == False:
            if isEvent == True:
                cls._logEvent(db, "photo_error", tc, eCtx, ctx, photoCtx, err=msg)

        ctx["action_stop"] = datetime.now()

        logger.debug("Thread %s: TriggerHandler._doTakePhoto - exit - done=%s msg=%s", get_ident(), done, msg)
        return done, msg
    
    @classmethod
    def _doCameraAction(cls, action:Action, trigger:Trigger=None, eventId:UUID=None, last:bool=False, threadRegistered:bool=True, wait:bool=True) -> tuple[bool, str]:
        """ Execution of a camera action

        Args:
            action (Action): Action to be executed
            trigger (Trigger, optional): Trigger on behalf of which the action is executed
            eventId (UUID): Unique ID of the event in the context of which the action is executed
            threadRegistered (bool, optional): If true (default), the active thread must be unregistered
            wait (bool, optional): If true (default), the thread needs to wait for the resource

        Raises:

        Returns:
            bool: True if action was executed
        """
        if trigger:
            triggerDisp = trigger.id
        else:
            triggerDisp = "No Trigger"
        logger.debug("Thread %s: TriggerHandler._doCameraAction - action=%s trigger.id=%s - starting - wait=%s last=%s", get_ident(), action.id, triggerDisp, wait, last)

        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        
        done = False
        msg = ""

        db = None
        isEvent = False
        if trigger:
            triggerCtrl = trigger.control
            if "event_log" in triggerCtrl:
                event_log = triggerCtrl["event_log"]
                if event_log == True:
                    isEvent = True
                    db = get_dbx()
        logger.debug("Thread %s: TriggerHandler._doCameraAction - isEvent=%s", get_ident(), isEvent)

        acquired = True
        
        if action.device == "CAM-1":
            if sc.isVideoRecording == True:
                if action.method == "stop_video":
                    acquired = True
                else:
                    acquired = False
            else:
                if action.method == "stop_video":
                    acquired = False
                    msg = f"Video recording not active. Stopping not required"
        logger.debug("Thread %s: TriggerHandler._doCameraAction - acquired=%s", get_ident(), acquired)
        
        # Start the live stream to avoid issues with concurrent camera access
        streamActive = sc.isLiveStream
        logger.debug("Thread %s: TriggerHandler._doCameraAction - Initially: sc.isLivestream=%s", get_ident(), streamActive)
        with cls._livestream_lock:
            Camera().startLiveStream()
            while sc.isLiveStream == False:
                time.sleep(0.1)
            logger.debug("Thread %s: TriggerHandler._doCameraAction - Finally: sc.isLivestream=%s", get_ident(), sc.isLiveStream)
            if streamActive == False and sc.isLiveStream == True:
                # If camera has been started give time to collect data for AE and AWB
                if Camera().requiresTimeForAutoAlgos() == True:
                    logger.debug("Thread %s: TriggerHandler._doCameraAction - Camera requires time for auto algorithms", get_ident())
                    time.sleep(2)
            
        if acquired:
            if action.device == "CAM-1":
                method = action.method
                if method == "take_photo":
                    done, msg = cls._doTakePhoto(action, isEvent, sc, tc, eventId, db)
                elif action.method == "record_video":
                    done, msg = cls._doRecordVideo(action, isEvent, sc, tc, eventId, db)
                elif action.method == "start_video":
                    done, msg = cls._doStartVideo(action, isEvent, sc, tc, eventId, db)
                elif action.method == "stop_video":
                    done, msg = cls._doStopVideo(action, isEvent, sc, tc, eventId, db)
                else:
                    logger.error("TriggerHandler._doCameraAction - Method %s not supported for device %s/%s", action.method, action.source, action.device)
                    msg = f"Method {action.method} not supported for device {action.source}/{action.device}"
            else:
                logger.error("TriggerHandler._doCameraAction - Device %s not supported for source %s", action.device, action.source)
                msg = f"Device {action.device} not supported for source {action.source}"
        else:
            logger.debug("Thread %s: TriggerHandler._doCameraAction - action=%s trigger.id=%s - Not executing. Device busy", get_ident(), action.id, triggerDisp)
            if msg == "":
                msg = f"Dev:ice {action.device} busy. Please try later."


        if last == True:
            # Finalize event
            cls._finalizeEvent(eventId)
            
        # Remove sub_thread from the list of threads
        if threadRegistered == True:
            thread = threading.current_thread()
            with cls._list_lock:
                if thread in cls._sub_threads:
                    cls._sub_threads.remove(thread)

        logger.debug("Thread %s: TriggerHandler._doCameraAction - action=%s trigger.id=%s terminated", get_ident(), action.id, triggerDisp)
        return done, msg
    
    @classmethod            
    def _initNotificationMessage(cls, eventId:UUID) -> EmailMessage:
        """ Set up an eMail Message for notification
        """
        logger.debug("Thread %s: TriggerHandler._initNotificationMessage", get_ident())
        tc = CameraCfg().triggerConfig
        ctx = cls._getEventContext(eventId)
        if "event_id" in ctx:
            logTS = ctx["event_TS"]
        else:
            logTS = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if "trigger" in ctx:
            triggerId = ctx["trigger"]
            trg = tc.getTrigger(triggerId)
            triggerType = f"{trg.source}/{trg.device}"
            triggerParams =f"{trg.params}"
        else:
            triggerId = "Unknown"
        

        msg = EmailMessage()
        msg["From"] = tc.notifyFrom
        msg["To"] = tc.notifyTo
        msg["Subject"] = tc.notifySubject
        trgContent = [
            ("Time:", logTS),
            ("Trigger:", triggerId),
            ("Type:", triggerType),
            ("Parameter:", str(triggerParams))
        ]
    
        actContent = []
        actLen = 0
        attContent = []
        attLen = 0
        if "actions" in ctx:
            actions = ctx["actions"]
            for actionCtx in actions:
                actLine = []
                actLine.append(f"- {actionCtx['action']}")
                if len(actionCtx["action"]) > actLen:
                    actLen = len(actionCtx["action"])
                if "action_start" in actionCtx:
                    actLine.append(actionCtx["action_start"].strftime("%Y-%m-%dT%H:%M:%S"))
                else:
                    actLine.append("")
                if "action_stop" in actionCtx:
                    actLine.append("-")
                    actLine.append(actionCtx["action_stop"].strftime("%Y-%m-%dT%H:%M:%S"))
                else:
                    actLine.append("")
                    actLine.append("")
                actContent.append(tuple(actLine))
                if "photos" in actionCtx:
                    photos = actionCtx["photos"]
                    for photo in photos:
                        attLine = []
                        if "photo_file" in photo:
                            attLine.append(photo["photo_file"])
                            if len(photo["photo_file"]) > attLen:
                                attLen = len(photo["photo_file"])
                            if "photo_time" in photo:
                                attLine.append(photo["photo_time"].strftime("%Y-%m-%dT%H:%M:%S"))
                            else:
                                attLine.append("")
                            attLine.append("")
                            attLine.append("")
                            attContent.append(tuple(attLine))
                if "video" in actionCtx:
                    video = actionCtx["video"]
                    if "video_file" in video:
                        attLine = []
                        filename = video["video_file"]
                        if len(filename) > attLen:
                            attLen = len(filename)
                        attLine.append(filename)
                        if "video_start" in video:
                            attLine.append(video["video_start"].strftime("%Y-%m-%dT%H:%M:%S"))
                        else:
                            attLine.append("")
                        if "video_stop" in video:
                            attLine.append("-")
                            attLine.append(video["video_stop"].strftime("%Y-%m-%dT%H:%M:%S"))
                        else:
                            attLine.append("")
                            attLine.append("")
                        attContent.append(tuple(attLine))
                        
        # Assemble content
        leftLen = max(actLen + 3, attLen)
        content = "Notification on an event\n\n"
        for left, right in trgContent:
            content += f"{left:<12} {right}\n"
        content += "\nActions:\n"
        for action, start, dash, stop in actContent:
            content += f"{action:<{leftLen}} {start:<20} {dash:<2} {stop}\n"
        content += "\nAttachments:\n"
        for filename, start, dash, stop in attContent:
            content += f"{filename:<{leftLen}} {start:<20} {dash:<2} {stop}\n"
        
        # Plain text for fallback
        msg.set_content(content)
        
        # HTML content
        html = "<html><body><div style='font-family: monospace; white-space: pre;'>"
        html += content.replace("\n", "<br>")
        html += "</div></body></html>"
        msg.add_alternative(html, subtype="html")
        
        logger.debug("Thread %s: MotionDetector._initNotificationMessage - done", get_ident())
        return msg
        
    @classmethod
    def _attachMedia(cls, mail:EmailMessage, eventId:UUID) -> bool:
        """ Attach media to the mail message
        
        This method is called when the action is executed in the context of a trigger.
        The media is attached from the event context.

        Args:
            mail (EmailMessage): Email message to which the media should be attached
            eventId (UUID): Unique ID of the event in the context of which the action is executed

        Returns:
            bool: True if media was attached
        """
        logger.debug("Thread %s: TriggerHandler._attachMedia", get_ident())
        done = False
        ctx = cls._getEventContext(eventId)
        if "actions" in ctx:
            actions = ctx["actions"]
            for actionCtx in actions:
                if "photos" in actionCtx:
                    photos = actionCtx["photos"]
                    for photo in photos:
                        if "photo_file" in photo:
                            filename = photo["photo_file"]
                            filepath = photo["photo_path"]
                            logger.debug("Thread %s: TriggerHandler._attachMedia - Adding attachment %s", get_ident(), filename)
                            with open(filepath, "rb") as f:
                                filetype, _ = mimetypes.guess_type(filename)
                                mail.add_attachment(f.read(), maintype=filetype, subtype=filetype.split("/")[1], filename=filename)
                if "video" in actionCtx:
                    video = actionCtx["video"]
                    if "video_file" in video:
                        filename = video["video_file"]
                        filepath = video["video_path"]
                        logger.debug("Thread %s: TriggerHandler._attachMedia - Adding attachment %s", get_ident(), filename)
                        # Wait a second for the file to be closed
                        time.sleep(1)
                        with open(filepath, "rb") as f:
                            filetype, _ = mimetypes.guess_type(filename)
                            mail.add_attachment(f.read(), maintype=filetype, subtype=filetype.split("/")[1], filename=filename)
            done = True
        return done

    @classmethod
    def _doSMTPaAction(cls, action:Action, trigger:Trigger=None, eventId:UUID=None, last:bool=False, threadRegistered:bool=True, wait:bool=True) -> tuple[bool, str]:
        """ Send a mail

        Args:
            action (Action): Action to be executed
            trigger (Trigger, optional): Trigger on behalf of which the action is executed
            eventId (UUID): Unique ID of the event in the context of which the action is executed
            threadRegistered (bool, optional): If true (default), the active thread must be unregistered
            wait (bool, optional): If true (default), the thread needs to wait for the resource

        Raises:

        Returns:
            bool: True if action was executed
        """
        if trigger:
            triggerDisp = trigger.id
        else:
            triggerDisp = "No Trigger"
        logger.debug("Thread %s: TriggerHandler._doSMTPaAction - action=%s trigger.id=%s - starting - wait=%s last=%s", get_ident(), action.id, triggerDisp, wait, last)
        cfg = CameraCfg()
        
        done = False
        msg = ""
        ok = True
    
        if last == True:
            # Wait for other actions to complete
            cls._waitForCompletion(eventId)
        
        ctx = cls._getActionContext(eventId, action.id)
        ctx["action_start"] = datetime.now()
        
        try:
            # Prepare email
            mail = cls._initNotificationMessage(eventId)

            #Attach media
            cls._attachMedia(mail, eventId)
            
            # Send email
            tc = cfg.triggerConfig
            scr =CameraCfg().secrets
            if tc.notifyUseSSL == True:
                server = smtplib.SMTP_SSL(host=tc.notifyHost, port=tc.notifyPort)
            else:
                server = smtplib.SMTP(host=tc.notifyHost, port=tc.notifyPort)
            server.connect(tc.notifyHost)
            
            if tc.notifyAuthenticate == True:
                logger.debug("Thread %s: TriggerHandler._doSMTPaAction - Authentication with user/pwd", get_ident())
                server.login(scr.notifyUser, scr.notifyPwd)
            else:
                logger.debug("Thread %s: TriggerHandler._doSMTPaAction - Authentication skipped", get_ident())
            server.ehlo()
            server.send_message(mail)
            server.quit()
            logger.debug("Thread %s: TriggerHandler._doSMTPaAction - Mail sent", get_ident())
        except Exception as e:
            logger.error("TriggerHandler._doSMTPaAction - Error %s: %s", type(e), e)
            tc.error = f"Error {type(e)} while sending email: {e}"

        if last == True:
            # Finalize event
            cls._finalizeEvent(eventId)
            
        # Remove sub_thread from the list of threads
        if threadRegistered == True:
            thread = threading.current_thread()
            with cls._list_lock:
                if thread in cls._sub_threads:
                    cls._sub_threads.remove(thread)

        ctx["action_stop"] = datetime.now()

        logger.debug("Thread %s: TriggerHandler._doSMTPaAction - action=%s trigger.id=%s terminated", get_ident(), action.id, triggerDisp)
        return done, msg
                

    @classmethod
    def doAction(cls, actionId: str) ->str:
        """ Execute an action outside the triggering context
        
        This method is designed to be executed outside the triggering context.
        It is assumed that it is not run within the trigger handling thread, for example through an action button.

        The function will wait for completion of the action.
                
        Action execution initiated through this method will share registered devices.
        Therefore, 'manual' execution of actions can be done while the trigger handling thread is active.

        Args:
            actionId (str): ID of the action to be executed

        Returns:
            (str) : Information / Error message
        """
        msg = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig

        action = tc.getAction(actionId)
        if action is None:
            msg = f"There is no action with ID {actionId}"
        else:
            if action.isActive:
                if action.source == "GPIO":
                    done = cls._doGpioAction(action, threadRegistered=False, wait=False)
                    if not done:
                        msg = "Device busy. Please repeat the action later."
                    else:
                        msg = "Action completed"
                elif action.source == "Camera":
                    done, msg = cls._doCameraAction(action, threadRegistered=False, wait=False)
                    if not done:
                        if msg == "":
                            msg = "Device busy. Please repeat the action later."
                    else:
                        if msg == "":
                            msg = "Action completed"
                else:
                    msg = f"Actions from source {action.source} are not (yet) supported."
            else:
                msg = f"Action {actionId} is not activated."
        return msg
    
    @classmethod
    def _getEventContext(cls, eventId:UUID) -> dict:
        """ Return the event context for a given event ID
        
        Args:
            eventId (UUID): event ID to be searched

        Returns:
            dict: event context
        """
        ctx = {}
        for eventCtx in cls._event_contexts:
            if eventCtx["event_id"] == eventId:
                ctx = eventCtx
                break
        return ctx
    
    @classmethod
    def _getActionContext(cls, eventId:UUID, actionId:str) -> dict:
        """ Find the action context in the event context

        Args:
            eventId (UUID): Unique ID of the ecent
            actionId (str): Action ID

        Returns:
            dict: dictionary for action context
        """
        ctx = {}
        if eventId is not None:
            eventCtx = cls._getEventContext(eventId)
            if "actions" in eventCtx:
                actions = eventCtx["actions"]
                for action in actions:
                    if action["action"] == actionId:
                        ctx = action
                        break
        return ctx
    
    @classmethod
    def _finalizeEvent(cls, eventId:UUID):
        """ Finalize an event

            - Handle event log
            - Remove event from event contexts
        Args:
            eventId (UUID): ID of invent to be finalized
        """
        logger.debug("Thread %s: TriggerHandler.finalizeEvent - eventId=%s", get_ident(), eventId)
        
        # Wait for event completion
        cls._waitForCompletion(eventId)
        
        ctx = cls._getEventContext(eventId)
        if ctx in cls._event_contexts:
            with cls._context_lock:
                cls._event_contexts.remove(ctx)
                logger.debug("Thread %s: TriggerHandler.finalizeEvent - context removed", get_ident())

    @classmethod
    def _waitForCompletion(cls, eventId:UUID):
        """ wait for compeltion of tasks for an event
        
            Iterate through the action contexts for an event.
            As long as an action is found, which is not marked as last action,
            for which the thread is still in the thread table, wait

        Args:
            eventId (UUID): Unique ID of event
        """
        time.sleep(1.0)
        logger.debug("Thread %s: TriggerHandler._waitForCompletion - entry", get_ident())
        ctxActions = None
        if eventId:
            ctx = cls._getEventContext(eventId)
            if ctx in cls._event_contexts:
                logger.debug("Thread %s: TriggerHandler._waitForCompletion - context=%s", get_ident(), ctx)
                if "actions" in ctx:
                    ctxActions = ctx["actions"]
        if ctxActions is not None:
            if len(ctxActions) > 0:
                wait = True
                while wait == True:
                    wait = False
                    for actionCtx in ctxActions:
                        if "is_last" in actionCtx:
                            isLast = actionCtx["is_last"]
                            if isLast == False:
                                if "thread" in actionCtx:
                                    thread = actionCtx["thread"]
                                    if thread in cls._sub_threads:
                                        wait = True
                    if wait == True:
                        time.sleep(0.1)
        if eventId:
            ctx = cls._getEventContext(eventId)
            logger.debug("Thread %s: TriggerHandler._waitForCompletion - context=%s", get_ident(), ctx)
        logger.debug("Thread %s: TriggerHandler._waitForCompletion - exit", get_ident())
        
    @classmethod
    def _logEvent(cls, db:Connection, logType:str, tc:TriggerConfig, eventCtx:dict, actionCtx:dict=None, photoCtx:dict=None, err:str=""):
        logger.debug("Thread %s: TriggerHandler._logEvent - entry", get_ident())
        
        triggerId = eventCtx["trigger"]
        trigger = tc.getTrigger(triggerId)
        eventTS = eventCtx["event_TS"]
        
        if logType == "start":
            # Event start
            logTS = eventTS
            key = eventTS
            with open(tc.logFilePath, "a") as f:
                f.write(eventCtx["event_TS"] + " Event  detected       Trigger: " + trigger.id + " - '" + trigger.source + "' " + str(trigger.params) + "\n")
            db.execute(
                "INSERT INTO events (timestamp, date, minute, time, type, trigger, triggertype, triggerparam) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (key, key[:10], key[11:16], key[11:19], "Motion", trigger.id, trigger.source, str(trigger.params))
            )
            db.commit()
            
        elif logType == "gpio_action":
            # GPIO action
            if "action" in actionCtx:
                actionId = actionCtx["action"]
                action = tc.getAction(actionId)
                hasDuration = False
                duration = 0
                if "duration" in action.control:
                    duration = action.control["duration"]
                    if duration > 0:
                        hasDuration = True
                logTS = actionCtx["action_start"].strftime("%Y-%m-%dT%H:%M:%S")
                with open(tc.logFilePath, "a") as f:
                    if hasDuration == True:
                        f.write(logTS + "  GPIO: " + actionId + " started\n")
                    else:
                        f.write(logTS + "  GPIO: " + actionId + "\n")
                db.execute(
                    "INSERT INTO eventactions (event, timestamp, date, time, actiontype, actionduration, filename, fullpath) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (eventTS, logTS, logTS[:10], logTS[11:19], actionId, duration, "", "")
                )
                db.commit()
            
        elif logType == "gpio_action_finished":
            # GPIO action finished
            if "action" in actionCtx:
                actionId = actionCtx["action"]
                action = tc.getAction(actionId)
                actionTS = actionCtx["action_start"].strftime("%Y-%m-%dT%H:%M:%S")
                logTS = actionCtx["action_stop"].strftime("%Y-%m-%dT%H:%M:%S")
                duration = actionCtx["action_stop"] - actionCtx["action_start"]
                actionDuration = duration.total_seconds()
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + "  GPIO: " + actionId + " stopped\n")
                db.execute(
                    "UPDATE eventactions set actionduration = ? WHERE event = ? AND timestamp = ? AND actiontype = ?",
                    (actionDuration, eventTS, actionTS, actionId)
                )
                db.commit()
        
        elif logType == "gpio_action_error":
            # GPIO Error
            if "action" in actionCtx:
                actionId = actionCtx["action"]
                logTS = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + "  GPIO: " + actionId + " Error:  " + err + "\n")
            
        elif logType == "photo_taken":
            # Photo taken
            if "photo_file" in photoCtx:
                fnPhoto = photoCtx["photo_file"]
                fpPhoto = photoCtx["photo_path"]
                logTS = photoCtx["photo_time"].strftime("%Y-%m-%dT%H:%M:%S")
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Photo: " + fnPhoto + "\n")
                db.execute(
                    "INSERT INTO eventactions (event, timestamp, date, time, actiontype, actionduration, filename, fullpath) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (eventTS, logTS, logTS[:10], logTS[11:19], "Photo", 0, fnPhoto, fpPhoto)
                )
                db.commit()
        
        elif logType == "photo_error":
            # Photo Error
            if "photo_file" in photoCtx:
                fnPhoto = photoCtx["photo_file"]
                logTS = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Photo: " + fnPhoto + " Error:  " + err + "\n")

        elif logType == "video_start":
            # Video Start
            if "video" in actionCtx:
                fnVideo = actionCtx["video"]["video_file"]
                fpVideo = actionCtx["video"]["video_path"]
                logTS = actionCtx["video"]["video_start"].strftime("%Y-%m-%dT%H:%M:%S")
                actionId = actionCtx["action"]
                action = tc.getAction(actionId)
                if "duration" in action.control:
                    actionDuration = action.control["duration"]
                else:
                    actionDuration = 0
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Video: " + fnVideo + " started" + "\n")
                db.execute(
                    "INSERT INTO eventactions (event, timestamp, date, time, actiontype, actionduration, filename, fullpath) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (eventTS, logTS, logTS[:10], logTS[11:19], "Video", actionDuration, fnVideo, fpVideo)
                )
                db.commit()
        
        elif logType == "video_start_err":
            # Video Start error
            if "video" in actionCtx:
                fnVideo = actionCtx["video"]["video_file"]
                logTS = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Video: " + fnVideo + " Start   Error: " + err + "\n")
            
        elif logType == "video_stop":
            # Video stopped
            if "video" in actionCtx:
                fnVideo = actionCtx["video"]["video_file"]
                fpVideo = actionCtx["video"]["video_path"]
                videoKey = actionCtx["video"]["video_start"].strftime("%Y-%m-%dT%H:%M:%S")
                logTS = actionCtx["video"]["video_stop"].strftime("%Y-%m-%dT%H:%M:%S")
                actionId = actionCtx["action"]
                action = tc.getAction(actionId)
                if "duration" in action.control:
                    actionDuration = action.control["duration"]
                else:
                    actionDuration = 0
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Video: " + fnVideo + " stopped" + "\n")
                logger.debug("Thread %s: MotionDetector._stopAction - UPDATE eventactions", get_ident())
                db.execute(
                    "UPDATE eventactions set actionduration = ? WHERE event = ? AND timestamp = ? AND actiontype = ?",
                    (round(actionDuration,0), eventTS, videoKey, "Video")
                )
                db.commit()
        
        elif logType == "video_stop_err":
            # Video stop error
            if "video" in actionCtx:
                fnVideo = actionCtx["video"]["video_file"]
                logTS = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Video: " + fnVideo + " Stop     Error" + err + "\n")
        else:
            logger.error("TriggerHandler._logEvent - Unknown logType %s", logType)
        

    @classmethod    
    def _actionDispatcher(cls, gpioDevice, trigger:Trigger):
        """ Dispatch actions configured for the given trigger
        
            Every active action associated with the given trigger, which initiated the event,
            will be started in an own sub-thread.
            All sub_threads are listed in the cls._sub_threads list.
            When a thread terminates, its last action will be to remove itself from the list.
            
            A context is maintained for the event fired by the given trigger:

            eventCtx = {
                "event_id": eventId,
                "trigger": trigger,
                "event_time": eventTime,
                "event_TS": eventTimestamp,
                "actions]:[
                    {
                        "action": action,
                        "is_last": is_last,
                        "thread": thread,
                        "action_start": actionStart,
                        "action_stop": actionStop,
                        "video": [
                            {
                                "video_start": videoStart,
                                "video_file": filename,
                                "video_path": filepath
                            }
                        ],
                        "photos": [
                            {
                                "photo_time": photoTime,
                                "photo_file": filename,
                                "photo_path": filepath
                            },
                            ...
                        ]
                    }
                ]
            }
            
        Args:
            gpioDevice (_type_): gpiozero device opject which activated the function
            trigger (Trigger): Trigger on behalf of which the function was activated
        """
        logger.debug("Thread %s: TriggerHandler._actionDispatcher - gpioDevice=%s trigger.id=%s", get_ident(), gpioDevice, trigger.id)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig

        isEvent = False
        if trigger:
            triggerCtrl = trigger.control
            if "event_log" in triggerCtrl:
                event_log = triggerCtrl["event_log"]
                if event_log == True:
                    isEvent = True
        
        if cls._isActive() == True:
            trg = tc.getTrigger(trigger.id)
            if cls._bouncing(trg, sc) == False:
                # Initialize the trigger context
                eventId = uuid4()
                eventCtx = {}
                eventCtx["event_id"] = eventId
                eventCtx["trigger"] = trigger.id
                now = datetime.now()
                eventCtx["event_time"] = now
                eventCtx["event_TS"] = now.strftime("%Y-%m-%dT%H:%M:%S")
                eventCtx["actions"] = []
                with cls._context_lock:
                    cls._event_contexts.append(eventCtx)

                # log event start
                if isEvent == True:
                    db = get_dbx()
                    cls._logEvent(db, "start", tc, eventCtx)
                
                # Search SMTP action in order to set it as last one
                setAsLast = True
                for act, status in trg.actions.items():
                    if status == True:
                        action = tc.getAction(act)
                        if action.isActive:
                            if action.source == "SMTP":
                                action = tc.getAction(act)
                                actionCtx = {}
                                actionCtx["action"] = action.id
                                actionCtx["is_last"] = setAsLast
                                # For SMTP action, do not wait.
                                # Mails can always be sent
                                smtpActionThread = threading.Thread(target=cls._doSMTPaAction, args=(action, trigger, eventId, setAsLast, True, False))
                                actionCtx["thread"] = smtpActionThread
                                smtpActionThread.start()
                                cls._sub_threads.append(smtpActionThread)
                                setAsLast = False
                
                # Iterate actions
                for act, status in trg.actions.items():
                    if status == True:
                        action = tc.getAction(act)
                        if action.isActive:
                            if action.source != "SMTP":
                                actionCtx = {}
                                actionCtx["action"] = action.id
                                actionCtx["is_last"] = setAsLast
                                eventCtx["actions"]. append(actionCtx)
                                if action.source == "GPIO":
                                    gpioActionThread = threading.Thread(target=cls._doGpioAction, args=(action, trigger, eventId, setAsLast))
                                    actionCtx["thread"] = gpioActionThread
                                    gpioActionThread.start()
                                    cls._sub_threads.append(gpioActionThread)
                                if action.source == "Camera":
                                    # For camera action, do not wait for the camera.
                                    # Waits would mainly occur with video recording. There, it does no make sense
                                    # to wait until current recording is finished and start new recording afterwards.
                                    camActionThread = threading.Thread(target=cls._doCameraAction, args=(action, trigger, eventId, setAsLast, True, False))
                                    actionCtx["thread"] = camActionThread
                                    camActionThread.start()
                                    cls._sub_threads.append(camActionThread)
                                setAsLast = False
                logger.debug("Thread %s: TriggerHandler._actionDispatcher - cls._event_contexts: %s", get_ident(), cls._event_contexts)

    @classmethod
    def _registerGpioTrigger(cls, sc:ServerConfig, tc:TriggerConfig, trg:Trigger):
        """ Register callback function for gpiozero device

        Args:
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            trg (Trigger): Trigger which specifies device and method to be registered
        """
        logger.debug("Thread %s: TriggerHandler._registerGpioTrigger", get_ident())
        
        triggerId = trg.id
        deviceId = trg.device
        _, reg = cls._findDeviceInRegistry("GPIO", deviceId, sc, False)
        deviceClass = reg["deviceClass"]
        deviceObj = reg["deviceObject"]

        try:
            # Apply event settings
            params = trg.params
            if len(params) > 0:
                for param, value in params.items():
                    if hasattr(deviceObj, param):
                        attr = getattr(deviceObj, param)
                        if callable(attr) == True:
                            call = f"{deviceClass}.{param}()"
                            logger.debug("Thread %s: TriggerHandler._registerGpioTrigger Trigger: %s - %s=%s", get_ident(),  triggerId, call, result)
                            result = attr()
                        else:
                            if value != "":
                                assignment = f"{deviceClass}.{param}={value}"
                                logger.debug("Thread %s: TriggerHandler._registerGpioTrigger Trigger: %s - %s", get_ident(),  triggerId, assignment)
                                setattr(deviceObj, param, value)
                            else:
                                call = f"{deviceClass}.{param}"
                                logger.debug("Thread %s: TriggerHandler._registerGpioTrigger - Trigger: %s - %s=%s", get_ident(),  triggerId, call, result)
                                result = attr
    
            # register event handler
            event = trg.event
            if hasattr(deviceObj, event):
                attr = getattr(deviceObj, event)
                assignment = f"{deviceClass}.{event}"
                if callable(attr) == False:
                    setattr(deviceObj, event, lambda deviceObj=deviceObj, trg=trg: cls._actionDispatcher(deviceObj, trigger=trg))
                    logger.debug("Thread %s: TriggerHandler._registerGpioTrigger - Trigger: %s - callback assigned to %s", get_ident(),  triggerId, assignment)
                    with cls._registry_lock:
                        reg["methods"].append(event)
                else:
                    raise ValueError(f"{assignment} is callable and not suitable for assignment of callback")
            else:
                raise ValueError(f"Class {deviceClass} has no element {event}")
        except Exception as e:
            logger.error("TriggerHandler._registerGpioTrigger - Trigger: %s - Error %s : %s",  triggerId, type(e), e)
            tc.error = f"Trigger: {triggerId} - Error: {type(e)} - {e}"

    @classmethod
    def _registerCameraTrigger(cls, sc:ServerConfig, tc:TriggerConfig, trg:Trigger):
        """ Register callback function for Camera

        Args:
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            trg (Trigger): Trigger which specifies device and method to be registered
        """
        logger.debug("Thread %s: TriggerHandler._registerCameraTrigger", get_ident())

        triggerId = trg.id
        deviceId = trg.device
        _, reg = cls._findDeviceInRegistry("Camera", deviceId, sc, False)
        deviceClass = reg["deviceClass"]
        deviceObj = reg["deviceObject"]

        try:
            # Get Camera instance
            deviceObj = Camera()
    
            # register event handler
            event = trg.event
            if hasattr(deviceObj, event):
                attr = getattr(deviceObj, event)
                assignment = f"{deviceClass}.{event}"
                setattr(deviceObj, event, lambda deviceObj=deviceObj, trg=trg: cls._actionDispatcher(deviceObj, trigger=trg))
                logger.debug("Thread %s: TriggerHandler._registerGpioTrigger - Trigger: %s - callback assigned to %s", get_ident(),  triggerId, assignment)
                with cls._registry_lock:
                    reg["methods"].append(event)
            else:
                raise ValueError(f"Class {deviceClass} has no element {event}")
        except Exception as e:
            logger.error("TriggerHandler._registerCameraTrigger - Trigger: %s - Error %s : %s",  triggerId, type(e), e)
            tc.error = f"Trigger: {triggerId} - Error: {type(e)} - {e}"

    @classmethod
    def _registerMotionDetectorTrigger(cls, sc:ServerConfig, tc:TriggerConfig, trg:Trigger):
        """ Register callback function for MotionDetector

        Args:
            sc (ServerConfig): Server configuration
            tc (TriggerConfig): Trigger configuration
            trg (Trigger): Trigger which specifies device and method to be registered
        """
        logger.debug("Thread %s: TriggerHandler._registerMotionDetectorTrigger", get_ident())
        
        # Register trigger only if motion detection is enabled
        if tc.triggeredByMotion == True:
            triggerId = trg.id
            deviceId = trg.device
            _, reg = cls._findDeviceInRegistry("MotionDetector", deviceId, sc, False)
            deviceClass = reg["deviceClass"]
            deviceObj = reg["deviceObject"]

            try:
                # Get MotionDetector instance
                deviceObj = MotionDetector()
        
                # register event handler
                event = trg.event
                if hasattr(deviceObj, event):
                    attr = getattr(deviceObj, event)
                    assignment = f"{deviceClass}.{event}"
                    setattr(deviceObj, event, lambda deviceObj=deviceObj, trg=trg: cls._actionDispatcher(deviceObj, trigger=trg))
                    logger.debug("Thread %s: TriggerHandler._registerMotionDetectorTrigger - Trigger: %s - callback assigned to %s", get_ident(),  triggerId, assignment)
                    with cls._registry_lock:
                        reg["methods"].append(event)
                else:
                    raise ValueError(f"Class {deviceClass} has no element {event}")
            except Exception as e:
                logger.error("TriggerHandler._registerMotionDetectorTrigger - Trigger: %s - Error %s : %s",  triggerId, type(e), e)
                tc.error = f"Trigger: {triggerId} - Error: {type(e)} - {e}"
        
    @classmethod        
    def _registerTriggers(cls):
        """ Register callback functions for methods specified for the configured triggers

        """
        logger.debug("Thread %s: TriggerHandler._registerTriggers", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        
        try:
            for trg in tc.triggers:
                if trg.isActive == True:
                    if trg.source == "GPIO":
                        cls._registerGpioTrigger(sc, tc, trg)
                    elif trg.source == "Camera":
                        cls._registerCameraTrigger(sc, tc, trg)
                    elif trg.source == "MotionDetector":
                        cls._registerMotionDetectorTrigger(sc, tc, trg)
            
        except Exception as e:
            logger.error("TriggerHandler._registerTriggers - Error %s : %s", type(e), e)
            tc.error = f"registerTriggers - Error: {type(e)} - {e}"

    @classmethod
    def _unregisterGpioTrigger(cls, sc:ServerConfig, tc:TriggerConfig, trg:Trigger):
        """ Unregister callback function for gpiozero device

        Args:
            trg (Trigger): Trigger which specifies device and method to be registered
        """
        logger.debug("Thread %s: TriggerHandler._unregisterGpioTrigger", get_ident())

        triggerId = trg.id
        deviceId = trg.device
        device = sc.getDevice(deviceId)
        deviceClass = device.type
        method = trg.event
        
        unregister = False
        if "GPIO" in cls._registry:
            regGPIO = cls._registry["GPIO"]
            if deviceId in regGPIO:
                regGpioDevice = regGPIO[deviceId]
                if "deviceObject" in regGpioDevice:
                    deviceObj = regGpioDevice["deviceObject"]
                    if "methods" in regGpioDevice:
                        regGpioMethods = regGpioDevice["methods"]
                        if method in regGpioMethods:
                            unregister = True
        if unregister:
            assignment = f"{deviceClass}.{method}=None"
            setattr(deviceObj, method, None)
            logger.debug("Thread %s: TriggerHandler._unregisterGpioTrigger - assignment: %s", get_ident(), assignment)
            regGpioMethods.remove(method)

    @classmethod
    def _unregisterCameraTrigger(cls, sc:ServerConfig, tc:TriggerConfig, trg:Trigger):
        """ Unregister callback function for Camera device

        Args:
            trg (Trigger): Trigger which specifies device and method to be registered
        """
        logger.debug("Thread %s: TriggerHandler._unregisterCameraTrigger", get_ident())

        triggerId = trg.id
        deviceId = trg.device
        deviceClass = "Camera"
        method = trg.event
        
        unregister = False
        if "Camera" in cls._registry:
            regCamera = cls._registry["Camera"]
            if deviceId in regCamera:
                regCameraDevice = regCamera[deviceId]
                if "deviceObject" in regCameraDevice:
                    deviceObj = regCameraDevice["deviceObject"]
                    if "methods" in regCameraDevice:
                        regCameraMethods = regCameraDevice["methods"]
                        if method in regCameraMethods:
                            unregister = True
        if unregister:
            assignment = f"{deviceClass}.{method}=None"
            setattr(deviceObj, method, None)
            logger.debug("Thread %s: TriggerHandler._unregisterCameraTrigger - assignment: %s", get_ident(), assignment)
            regCameraMethods.remove(method)

    @classmethod
    def _unregisterMotionDetectorTrigger(cls, sc:ServerConfig, tc:TriggerConfig, trg:Trigger):
        """ Unregister callback function for MotionDetector device

        Args:
            trg (Trigger): Trigger which specifies device and method to be registered
        """
        logger.debug("Thread %s: TriggerHandler._unregisterMotionDetectorTrigger", get_ident())

        triggerId = trg.id
        deviceId = trg.device
        deviceClass = "MotionDetector"
        method = trg.event
        
        unregister = False
        if "MotionDetector" in cls._registry:
            regMotionDetector = cls._registry["MotionDetector"]
            if deviceId in regMotionDetector:
                regMotionDetectorDevice = regMotionDetector[deviceId]
                if "deviceObject" in regMotionDetectorDevice:
                    deviceObj = regMotionDetectorDevice["deviceObject"]
                    if "methods" in regMotionDetectorDevice:
                        regMotionDetectorMethods = regMotionDetectorDevice["methods"]
                        if method in regMotionDetectorMethods:
                            unregister = True
        if unregister:
            assignment = f"{deviceClass}.{method}=None"
            setattr(deviceObj, method, None)
            logger.debug("Thread %s: TriggerHandler._unregisterMotionDetectorTrigger - assignment: %s", get_ident(), assignment)
            regMotionDetectorMethods.remove(method)
        
    @classmethod
    def _unregisterTriggers(cls):
        """ Unregister callback functions for methods specified for the configured triggers

        """
        logger.debug("Thread %s: TriggerHandler._unregisterTriggers", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        
        try:
            for trg in tc.triggers:
                if trg.isActive == True:
                    if trg.source == "GPIO":
                        cls._unregisterGpioTrigger(sc, tc, trg)
                    if trg.source == "Camera":
                        cls._unregisterCameraTrigger(sc, tc, trg)
                    if trg.source == "MotionDetector":
                        cls._unregisterMotionDetectorTrigger(sc, tc, trg)
            
        except Exception as e:
            logger.error("TriggerHandler._unregisterTriggers - Error %s : %s", type(e), e)
        
    @classmethod
    def _closeGpioDevices(cls):
        """ Close devices found in the registry

        """
        logger.debug("Thread %s: TriggerHandler._closeGpioDevices", get_ident())

        close = False
        closed = []
        if "GPIO" in cls._registry:
            regGPIO = cls._registry["GPIO"]
            for deviceClass in regGPIO:
                regGpioDevice = regGPIO[deviceClass]
                if "deviceObject" in regGpioDevice:
                    deviceObj = regGpioDevice["deviceObject"]
                    if deviceObj:
                        if hasattr(deviceObj, "close"):
                            try:
                                attr = getattr(deviceObj, "close")
                                if callable(attr) == True:
                                    attr()
                                    logger.debug("Thread %s: TriggerHandler._closeDevices - %s.close()", get_ident(), deviceClass)
                                    closed.append(deviceClass)
                            except Exception as e:
                                logger.error("TriggerHandler._closeDevices - Error while closing %s: %s - %s", deviceClass, type(e), e)                        
        for dev in closed:
            cls._registry["GPIO"].pop(dev)
        if "GPIO" in cls._registry:
            if len(cls._registry["GPIO"]) > 0:
                logger.error("TriggerHandler._closeDevices - Rgegistry not empty, not all devices closed. Resetting aniway")                        
        cls._registry["GPIO"] = {}            

    @classmethod
    def _triggerThread(cls):
        """ Thread for lifecycle of trigger registration

        """
        logger.debug("Thread %s: TriggerHandler._triggerThread", get_ident())
        
        # Set active status
        cls._isActive()
        
        stop = False
        cls._registerTriggers()
        while not stop:
            time.sleep(0.5)
            if cls.triggerThreadStop == True:
                logger.debug("Thread %s: TriggerHandler._triggerThread - stop requested", get_ident())
                stop = True

        logger.debug("Thread %s: TriggerHandler._triggerThread - stopped", get_ident())
        
        # Wait for sub_threds to terminate
        logger.debug("Thread %s: TriggerHandler._triggerThread - There are %s subthreads to wait for termination", get_ident(), len(cls._sub_threads))
        cnt = 0
        while cls._sub_threads:
            time.sleep(0.1)
            cnt += 1
            if cnt > 200:
                logger.warning("TriggerHandler._triggerThread - %s sub_threads not yet terminated. Stopping anyway")
                break
        cls._sub_threads = []
        cls._event_contexts = []
        cls._unregisterTriggers()
        cls.triggerThread = None

    @classmethod
    def start(cls) -> bool:
        """ Start trigger operation

        Returns:
            bool: true if operation was successfully started
        """
        logger.debug("Thread %s: TriggerHandler.start", get_ident())
        sc = CameraCfg().serverConfig
        tc = CameraCfg().triggerConfig
        
        tc.error = None
        tc.error2 = None

        if cls.triggerThread is None:
            sc.error = None
            tc.error = None
            if not sc.error:
                logger.debug("Thread %s: TriggerHandler.start - starting new thread", get_ident())
                cls.triggerThread = threading.Thread(target=cls._triggerThread, daemon=True)
                cls.triggerThread.start()
                logger.debug("Thread %s: TriggerHandler.start - thread started", get_ident())
            else:
                logger.debug("Thread %s: TriggerHandler.start - not started", get_ident())

    @classmethod
    def stop(cls) -> bool:
        """ Stop trigger operation

        Returns:
            bool: true if operation was successfully stopped
        """
        logger.debug("Thread %s: TriggerHandler.stop", get_ident())

        if cls.triggerThread is None:
            logger.debug("Thread %s: TriggerHandler.stop - thread was not active", get_ident())
        else:
            logger.debug("Thread %s: TriggerHandler.stop - stopping thread", get_ident())
            cls.triggerThreadStop = True
            cnt = 0
            while cls.triggerThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 500:
                    logger.error("Trigger thread did not stop within 5 sec")
                    if cls.triggerThread.is_alive():
                        cnt = 0
                    else:
                        cls.triggerThread = None
            cls._closeGpioDevices()
            cls.triggerThreadStop = False
        logger.debug("Thread %s: TriggerHandler.stop: Thread has stopped", get_ident())
        