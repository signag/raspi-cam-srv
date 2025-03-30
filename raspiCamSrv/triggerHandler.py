from gpiozero import Button, LineSensor, MotionSensor, LightSensor, DistanceSensor, RotaryEncoder
from gpiozero import LED, PWMLED, RGBLED, Buzzer,TonalBuzzer, Motor,PhaseEnableMotor, Servo, AngularServo
from raspiCamSrv.gpioDevices import StepperMotor
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, TriggerConfig, ServerConfig, GPIODevice, Trigger, Action
from _thread import get_ident
from datetime import datetime, timedelta
from raspiCamSrv.dbx import get_dbx
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
    db = None
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
        A second try would result in a "Device in use" error.
        Therefore instantiated devices are stored in the registry for later access
        
        The registry structure is:
        - source ("GPIO")
            +- deviceId
                 +- "deviceClass" : device type (class name)
                 +- "deviceObject": reference to instantiated device object
                 +- "busy"        : true if the device is currently busy  
                 +- "lastAccess   : Time of last access to a device
                 +- "methods"     : Methods to which callbacks are assigned
                 +- ...

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
                device = sc.getDevice(deviceId)
                deviceClass = device.type
                deviceArgs = device.params
                cls._registry[source][deviceId]["deviceClass"] = deviceClass

                # Instantiate device object
                deviceObj = globals()[deviceClass](**deviceArgs)
                logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - instantiated: %s(%s)", get_ident(), deviceClass, deviceArgs)
                cls._registry[source][deviceId]["deviceObject"] = deviceObj
                
            if not "methods" in cls._registry[source][deviceId]:
                cls._registry[source][deviceId]["methods"] = []

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
            if busyAcquired == True:
                cls._registry[source][deviceId]["last_access"] = datetime.now()
                    

            res = cls._registry[source][deviceId]
            logger.debug("Thread %s: TriggerHandler._findDeviceInRegistry - Returning: %s", get_ident(), res)
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
    def _doGpioAction(cls, action:Action, trigger:Trigger=None, threadRegistered:bool=True, wait:bool=True) -> bool:
        """ Execute an action with a GPIO device

        Args:
            action (Action): The action to execute
            trigger (Trigger): Trigger on behalf of which the action is executed
            threadRegistered (bool): if True, the thread is registered in the sub_threads list and must be unregistered
                                    after completion
        """
        if trigger:
            triggerDisp = trigger.id
        else:
            triggerDisp = "No Trigger"
        logger.debug("Thread %s: TriggerHandler._doGpioAction - action=%s trigger.id=%s - starting - wait=%s", get_ident(), action.id, triggerDisp, wait)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig

        deviceId = action.device
        
        done = False
        
        acquired, reg = cls._findDeviceInRegistry("GPIO", deviceId, sc, busy=True)
        if wait == True:
            while acquired == False:
                time.sleep(0.1)
                acquired, reg = cls._findDeviceInRegistry("GPIO", deviceId, sc, busy=True)

        if acquired:
            deviceClass = reg["deviceClass"]
            deviceObj = reg["deviceObject"]
            method = action.method
            methodParams = action.params
            actionCtrl = action.control

            try:

                # Apply action method
                if hasattr(deviceObj, method):
                    attr = getattr(deviceObj, method)
                    if callable(attr) == True:
                        if len(methodParams) > 0:
                            call = f"{deviceClass}.{method}({methodParams})"
                            result = attr(**methodParams)
                        else:
                            call = f"{deviceClass}.{method}()"
                            result = attr()
                        logger.debug("Thread %s: TriggerHandler._doGpioAction Action:%s - %s=%s", get_ident(),  action.id, call, result)
                    else:
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
            except Exception as e:
                logger.error("TriggerHandler._doGpioAction - Error %s: %s", type(e), e)
                
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

            # Release busy state
            cls._findDeviceInRegistry("GPIO", deviceId, sc, busy=False)
            done = True
        else:
            logger.debug("Thread %s: TriggerHandler._doGpioAction - action=%s trigger.id=%s - Not executing. Device busy", get_ident(), action.id, triggerDisp)
            
        # Remove sub_thread from the list of threads
        if threadRegistered == True:
            thread = threading.current_thread()
            with cls._list_lock:
                if thread in cls._sub_threads:
                    cls._sub_threads.remove(thread)

        logger.debug("Thread %s: TriggerHandler._doGpioAction - action=%s trigger.id=%s terminated", get_ident(), action.id, triggerDisp)
        return done

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
                    done = cls._doGpioAction(action, None,False, False)
                    if not done:
                        msg = "Device busy. Please repeat the action later."
                    else:
                        msg = "Action completed"
                else:
                    msg = f"Actions from source {action.source} are notb yet supported."
            else:
                msg = f"Action {actionId} is not activated."
        return msg

    @classmethod    
    def _actionDispatcher(cls, gpioDevice, trigger:Trigger):
        """ Dispatch actions configured for the given trigger

        Args:
            gpioDevice (_type_): gpiozero device opject which activated the function
            trigger (Trigger): Trigger on behalf of which the function was activated
        """
        logger.debug("Thread %s: TriggerHandler._actionDispatcher - gpioDevice=%s trigger.id=%s", get_ident(), gpioDevice, trigger.id)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        
        if cls._isActive() == True:
            trg = tc.getTrigger(trigger.id)
            if cls._bouncing(trg, sc) == False:
                for act, status in trg.actions.items():
                    if status == True:
                        action = tc.getAction(act)
                        if action.isActive:
                            if action.source == "GPIO":
                                gpioActionThread = threading.Thread(target=cls._doGpioAction, args=(action, trigger))
                                gpioActionThread.start()
                                cls._sub_threads.append(gpioActionThread)

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
        deviceClass = "Camera"

        try:
            # Get Camera instance
            deviceObj = Camera()
    
            # register event handler
            event = trg.event
            if hasattr(deviceObj, event):
                attr = getattr(deviceObj, event)
                assignment = f"{deviceClass}.{event}"
                if callable(attr) == False:
                    setattr(deviceObj, event, lambda deviceObj=deviceObj, trg=trg: cls._actionDispatcher(deviceObj, trigger=trg))
                    logger.debug("Thread %s: TriggerHandler._registerGpioTrigger - Trigger: %s - callback assigned to %s", get_ident(),  triggerId, assignment)
                else:
                    raise ValueError(f"{assignment} is callable and not suitable for assignment of callback")
            else:
                raise ValueError(f"Class {deviceClass} has no element {event}")
        except Exception as e:
            logger.error("TriggerHandler._registerCameraTrigger - Trigger: %s - Error %s : %s",  triggerId, type(e), e)
        
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
            
        except Exception as e:
            logger.error("TriggerHandler._registerTriggers - Error %s : %s", type(e), e)

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
        