import subprocess
import importlib
from subprocess import CalledProcessError
import json
import logging
import os
from ast import literal_eval
from pathlib import Path
from datetime import datetime
from datetime import date
from datetime import time
from datetime import timedelta
import raspiCamSrv.dbx as dbx
from raspiCamSrv.gpioDeviceTypes import gpioDeviceTypes
import smtplib
from pathlib import Path
import zoneinfo
from secrets import token_urlsafe
import threading
from time import sleep

logger = logging.getLogger(__name__)

class GPIODevice():
    def __init__(self):
        self._id = ""
        self._usage = ""
        self._type = ""
        self._params = {}
        self._usedPins = ""
        self._isOk = False
        self._docUrl = ""
        self._needsCalibration = False
        self._isCalibrating = False
        self._deviceStatePath = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        self._deviceStatePath = sc.cfgPath + "/device_state"
        os.makedirs(self._deviceStatePath, exist_ok=True)
        self._deviceStateFile = ""

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value
        self._deviceStateFile = self._deviceStatePath + "/" + self._id + ".json"

    @property
    def usage(self) -> str:
        return self._usage

    @usage.setter
    def usage(self, value: str):
        self._usage = value

    @property
    def type(self) -> str:
        return self._type

    @type.setter
    def type(self, value: str):
        self._type = value

    @property
    def params(self) -> dict:
        return self._params

    @params.setter
    def params(self, value: dict):
        self._params = value

    @property
    def usedPins(self) -> str:
        return self._usedPins

    @usedPins.setter
    def usedPins(self, value: str):
        self._usedPins = value

    @property
    def isOk(self) -> bool:
        return self._isOk

    @isOk.setter
    def isOk(self, value: bool):
        self._isOk = value

    @property
    def docUrl(self) -> str:
        return self._docUrl

    @docUrl.setter
    def docUrl(self, value: str):
        self._docUrl = value

    @property
    def isCalibrating(self) -> bool:
        return self._isCalibrating

    @isCalibrating.setter
    def isCalibrating(self, value: bool):
        self._isCalibrating = value

    @property
    def needsCalibration(self) -> bool:
        return self._needsCalibration

    @needsCalibration.setter
    def needsCalibration(self, value: bool):
        self._needsCalibration = value
        
    def trackState(self, devObject:object) ->bool:
        """ Track the state of a GPIO device for which calibration is required

            The device object is expected to have the following attributes:
            - value
            The state is persisted in file

        Args:
            devObject (object): device object to track
        Returns:
            bool: True if the state is tracked successfully, False otherwise
        """
        logger.debug("GPIODevice.trackState - entry")
        res = False
        state = {}
        if self._needsCalibration:
            if hasattr(devObject, "value"):
                try:
                    value = getattr(devObject, "value")
                    state["value"] = value
                    logger.debug("GPIODevice.trackState - tracking value %s in file %s", value, self._deviceStateFile)
                    with open(self._deviceStateFile, "w") as f:
                        json.dump(state, f)
                    res = True
                except Exception as e:
                    logger.error("GPIODevice.trackState: Error %s tracking device state: %s", type(e), e)
        return res
        
    def setState(self, devObject:object) ->bool:
        """ Set the state of a GPIO device for which calibration is required

            The device object is expected to have the following attributes:
            - value
            The state is read from file

        Args:
            devObject (object): device object to track
        Returns:
            bool: True if the state is trasetcked successfully, False otherwise
        """
        logger.debug("GPIODevice.setState - entry")
        res = False
        state = {}
        if self._needsCalibration:
            try:
                with open(self._deviceStateFile, "r") as f:
                    state = json.load(f)
                    logger.debug("GPIODevice.trackState - read from file %s : %s",self._deviceStateFile, state)
                    if "value" in state:
                        setattr(devObject, "value", state["value"])
                        res = True
            except FileNotFoundError:
                # If state has not yet been persisted, keep default state
                pass
            except Exception as e:
                logger.error("GPIODevice.setState: Error %s setting device state: %s", type(e), e)  
        return res

    @classmethod                
    def initFromDict(cls, dict:dict):
        dev = GPIODevice()
        for key, value in dict.items():
            if value is None:
                setattr(dev, key, value)
            else:
                if key == "_params":
                    newval = {}
                    for pkey, pvalue in value.items():
                        if type(pvalue) is list:
                            newval[pkey] = tuple(pvalue)
                        else:
                            newval[pkey] = pvalue
                    value = newval
                setattr(dev, key, value)
        return dev

class Trigger():
    def __init__(self):
        self._id = ""
        self._source = ""
        self._device = ""
        self._event = ""
        self._params = {}
        self._control = {}
        self._isActive = False
        self._actions = {}

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, value: str):
        self._source = value

    @property
    def device(self) -> str:
        return self._device

    @device.setter
    def device(self, value: str):
        self._device = value

    @property
    def event(self) -> str:
        return self._event

    @event.setter
    def event(self, value: str):
        self._event = value

    @property
    def params(self) -> dict:
        return self._params

    @params.setter
    def params(self, value: dict):
        self._params = value

    @property
    def control(self) -> dict:
        return self._control

    @control.setter
    def control(self, value: dict):
        self._control = value

    @property
    def isActive(self) -> bool:
        return self._isActive

    @isActive.setter
    def isActive(self, value: bool):
        self._isActive = value

    @property
    def actions(self) -> dict:
        return self._actions

    @actions.setter
    def actions(self, value: dict):
        self._actions = value

    @classmethod                
    def initFromDict(cls, dict:dict):
        trg = Trigger()
        for key, value in dict.items():
            if value is None:
                setattr(trg, key, value)
            else:
                if key == "_device":
                    val = value
                    if value == "Active Camera":
                        val = "CAM-1"
                    if value == "Second Camera":
                        val = "CAM-2"
                    value = val
                if key == "_params":
                    newval = {}
                    for pkey, pvalue in value.items():
                        if type(pvalue) is list:
                            newval[pkey] = tuple(pvalue)
                        else:
                            newval[pkey] = pvalue
                    value = newval
                if key == "_control":
                    newval = {}
                    for pkey, pvalue in value.items():
                        if type(pvalue) is list:
                            newval[pkey] = tuple(pvalue)
                        else:
                            newval[pkey] = pvalue
                    value = newval
                elif key == "_actions":
                    newval = {}
                    for pkey, pvalue in value.items():
                        if type(pvalue) is list:
                            newval[pkey] = tuple(pvalue)
                        else:
                            newval[pkey] = pvalue
                    value = newval
                setattr(trg, key, value)
        return trg

class Action():
    def __init__(self):
        self._id = ""
        self._isActive = False
        self._source = ""
        self._device = ""
        self._method = ""
        self._params = {}
        self._control = {}

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def isActive(self) -> bool:
        return self._isActive

    @isActive.setter
    def isActive(self, value: bool):
        self._isActive = value

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, value: str):
        self._source = value

    @property
    def device(self) -> str:
        return self._device

    @device.setter
    def device(self, value: str):
        self._device = value

    @property
    def method(self) -> str:
        return self._method

    @method.setter
    def method(self, value: str):
        self._method = value

    @property
    def params(self) -> dict:
        return self._params

    @params.setter
    def params(self, value: dict):
        self._params = value

    @property
    def control(self) -> dict:
        return self._control

    @control.setter
    def control(self, value: dict):
        self._control = value

    @classmethod                
    def initFromDict(cls, dict:dict):
        act = Action()
        for key, value in dict.items():
            if value is None:
                setattr(act, key, value)
            else:
                if key == "_params":
                    newval = {}
                    for pkey, pvalue in value.items():
                        if type(pvalue) is list:
                            newval[pkey] = tuple(pvalue)
                        else:
                            newval[pkey] = pvalue
                    value = newval
                elif key == "_control":
                    newval = {}
                    for pkey, pvalue in value.items():
                        if type(pvalue) is list:
                            newval[pkey] = tuple(pvalue)
                        else:
                            newval[pkey] = pvalue
                    value = newval
                setattr(act, key, value)
        return act

class TriggerConfig():
    motionDetectAlgos = ["Mean Square Diff", "Frame Differencing", "Optical Flow", "Background Subtraction"]
    videoRecorders = ["Normal", "Circular"]
    backgroundSubtractionModels = ["MOG2", "KNN"]
    def __init__(self):
        self._triggeredByMotion = True
        self._triggeredBySound = False
        self._triggeredByEvents = False
        self._actionVideo = True
        self._actionPhoto = True
        self._actionNotify = False
        self._operationStartMinute: int = 0
        self._operationEndMinute: int = 1439
        self._operationWeekdays = {"1":True, "2":True, "3":True, "4":True, "5":True, "6":True, "7":True}
        self._operationAutoStart = False
        self._detectionDelaySec = 0
        self._detectionPauseSec = 20
        self._motionDetectAlgo = 1
        self._motionRefTit = ""
        self._motionRefURL = ""
        self._msdThreshold = 10
        self._bboxThreshold = 400
        self._nmsThreshold = 0.001
        self._motionThreshold = 1
        self._backSubModel = "MOG2"
        self._videoBboxes = True
        self._motionTestFrame1Title = ""
        self._motionTestFrame2Title = ""
        self._motionTestFrame3Title = ""
        self._motionTestFrame4Title = ""
        self._motionTestFramerate = 0
        self._actionVR = 1
        self._actionCircSize = 5
        self._actionPath = ""
        self._actionVideoDuration = 10
        self._actionPhotoBurst = 1
        self._actionPhotoBurstDelaySec = 2
        self._notifyHost = ""
        self._notifyPort = 0
        self._notifyUseSSL = False
        self._notifyAuthenticate = True
        self._notifyConOK = False
        self._notifyPause = 0
        self._notifyIncludeVideo = False
        self._notifyIncludePhoto = False
        self._notifySavePwd = False
        self._notifyPwdPath = ""
        self._notifyFrom = ""
        self._notifyTo = ""
        self._notifySubject = ""
        self._retentionPeriod = 3
        self._evStart = None
        self._evIncludePhoto = False
        self._evIncludeVideo = True
        self._evAutoRefresh = False
        self._calStart = None
        self._error = None
        self._error2 = None
        self._errorSource = None
        self._triggers = []
        self._actions = []
        
    @property
    def logFileName(self) -> str:
        return "_events.log"
        
    @property
    def logFilePath(self) -> str:
        return self._actionPath + "/" + self.logFileName

    @property
    def operationStartMinute(self) -> int:
        return self._operationStartMinute

    @operationStartMinute.setter
    def operationStartMinute(self, value: int):
        self._operationStartMinute = value

    @property
    def operationStartStr(self) -> str:
        h = self._operationStartMinute // 60
        m = self._operationStartMinute % 60
        return str(h).zfill(2) + ":" + str(m).zfill(2)

    @operationStartStr.setter
    def operationStartStr(self, value: str):
        h = 0
        m = 0
        if value:
            if len(value) == 5:
                h = int(value[:2])
                m = int(value[3:])
        self._operationStartMinute = 60 * h + m

    @property
    def operationEndMinute(self) -> int:
        return self._operationEndMinute

    @operationEndMinute.setter
    def operationEndMinute(self, value: int):
        self._operationEndMinute = value

    @property
    def operationEndStr(self) -> str:
        h = self._operationEndMinute // 60
        m = self._operationEndMinute % 60
        return str(h).zfill(2) + ":" + str(m).zfill(2)

    @operationEndStr.setter
    def operationEndStr(self, value: str):
        h = 0
        m = 0
        if value:
            if len(value) == 5:
                h = int(value[:2])
                m = int(value[3:])
        self._operationEndMinute = 60 * h + m

    @property
    def operationWeekdays(self) -> dict:
        return self._operationWeekdays

    @operationWeekdays.setter
    def operationWeekdays(self, value: dict):
        self._operationWeekdays = value

    @property
    def operationAutoStart(self) -> bool:
        return self._operationAutoStart

    @operationAutoStart.setter
    def operationAutoStart(self, value: bool):
        self._operationAutoStart = value

    @property
    def detectionDelaySec(self) -> int:
        return self._detectionDelaySec

    @detectionDelaySec.setter
    def detectionDelaySec(self, value: int):
        self._detectionDelaySec = value

    @property
    def detectionPauseSec(self) -> int:
        return self._detectionPauseSec

    @detectionPauseSec.setter
    def detectionPauseSec(self, value: int):
        self._detectionPauseSec = value

    @property
    def triggeredByMotion(self) -> bool:
        return self._triggeredByMotion

    @triggeredByMotion.setter
    def triggeredByMotion(self, value: bool):
        self._triggeredByMotion = value

    @property
    def triggeredBySound(self) -> bool:
        return self._triggeredBySound

    @triggeredBySound.setter
    def triggeredBySound(self, value: bool):
        self._triggeredBySound = value

    @property
    def triggeredByEvents(self) -> bool:
        return self._triggeredByEvents

    @triggeredByEvents.setter
    def triggeredByEvents(self, value: bool):
        self._triggeredByEvents = value

    @property
    def motionDetectAlgo(self) -> int:
        return self._motionDetectAlgo

    @motionDetectAlgo.setter
    def motionDetectAlgo(self, value: int):
        self._motionDetectAlgo = value

    @property
    def motionRefTit(self) -> str:
        return self._motionRefTit

    @motionRefTit.setter
    def motionRefTit(self, value: str):
        self._motionRefTit = value

    @property
    def motionRefURL(self) -> str:
        return self._motionRefURL

    @motionRefURL.setter
    def motionRefURL(self, value: str):
        self._motionRefURL = value

    @property
    def actionVideo(self) -> bool:
        return self._actionVideo

    @actionVideo.setter
    def actionVideo(self, value: bool):
        self._actionVideo = value

    @property
    def actionPhoto(self) -> bool:
        return self._actionPhoto

    @actionPhoto.setter
    def actionPhoto(self, value: bool):
        self._actionPhoto = value

    @property
    def actionNotify(self) -> bool:
        return self._actionNotify

    @actionNotify.setter
    def actionNotify(self, value: bool):
        self._actionNotify = value

    @property
    def msdThreshold(self) -> int:
        return self._msdThreshold

    @msdThreshold.setter
    def msdThreshold(self, value: int):
        self._msdThreshold = value

    @property
    def bboxThreshold(self) -> int:
        return self._bboxThreshold

    @bboxThreshold.setter
    def bboxThreshold(self, value: int):
        self._bboxThreshold = value

    # TODO: int->float
    @property
    def nmsThreshold(self) -> int:
        return self._nmsThreshold

    @nmsThreshold.setter
    def nmsThreshold(self, value: int):
        self._nmsThreshold = value

    @property
    def motionThreshold(self) -> int:
        return self._motionThreshold

    @motionThreshold.setter
    def motionThreshold(self, value: int):
        self._motionThreshold = value

    @property
    def backSubModel(self) -> str:
        return self._backSubModel

    @backSubModel.setter
    def backSubModel(self, value: str):
        self._backSubModel = value

    @property
    def videoBboxes(self) -> bool:
        return self._videoBboxes

    @videoBboxes.setter
    def videoBboxes(self, value: bool):
        self._videoBboxes = value

    @property
    def motionTestFrame1Title(self) -> str:
        return self._motionTestFrame1Title

    @motionTestFrame1Title.setter
    def motionTestFrame1Title(self, value: str):
        self._motionTestFrame1Title = value

    @property
    def motionTestFrame2Title(self) -> str:
        return self._motionTestFrame2Title

    @motionTestFrame2Title.setter
    def motionTestFrame2Title(self, value: str):
        self._motionTestFrame2Title = value

    @property
    def motionTestFrame3Title(self) -> str:
        return self._motionTestFrame3Title

    @motionTestFrame3Title.setter
    def motionTestFrame3Title(self, value: str):
        self._motionTestFrame3Title = value

    @property
    def motionTestFrame4Title(self) -> str:
        return self._motionTestFrame4Title

    @motionTestFrame4Title.setter
    def motionTestFrame4Title(self, value: str):
        self._motionTestFrame4Title = value

    @property
    def motionTestFramerate(self) -> float:
        return self._motionTestFramerate

    @motionTestFramerate.setter
    def motionTestFramerate(self, value: str):
        self._motionTestFramerate = value
        
    @property
    def actionVR(self) -> int:
        return self._actionVR

    @actionVR.setter
    def actionVR(self, value: int):
        self._actionVR = value

    @property
    def actionCircSize(self) -> int:
        return self._actionCircSize

    @actionCircSize.setter
    def actionCircSize(self, value: int):
        self._actionCircSize = value

    @property
    def actionPath(self) -> str:
        return self._actionPath

    @actionPath.setter
    def actionPath(self, value: str):
        self._actionPath = value

    @property
    def actionVideoDuration(self) -> int:
        return self._actionVideoDuration

    @actionVideoDuration.setter
    def actionVideoDuration(self, value: int):
        self._actionVideoDuration = value

    @property
    def actionPhotoBurst(self) -> int:
        return self._actionPhotoBurst

    @actionPhotoBurst.setter
    def actionPhotoBurst(self, value: int):
        self._actionPhotoBurst = value

    @property
    def actionPhotoBurstDelaySec(self) -> int:
        return self._actionPhotoBurstDelaySec

    @actionPhotoBurstDelaySec.setter
    def actionPhotoBurstDelaySec(self, value: int):
        self._actionPhotoBurstDelaySec = value

    @property
    def notifyHost(self) -> str:
        return self._notifyHost

    @notifyHost.setter
    def notifyHost(self, value: str):
        self._notifyHost = value

    @property
    def notifyPort(self) -> int:
        return self._notifyPort

    @notifyPort.setter
    def notifyPort(self, value: int):
        self._notifyPort = value

    @property
    def notifyUseSSL(self) -> bool:
        return self._notifyUseSSL

    @notifyUseSSL.setter
    def notifyUseSSL(self, value: bool):
        self._notifyUseSSL = value

    @property
    def notifyAuthenticate(self) -> bool:
        return self._notifyAuthenticate

    @notifyAuthenticate.setter
    def notifyAuthenticate(self, value: bool):
        self._notifyAuthenticate = value

    @property
    def notifyConOK(self) -> bool:
        return self._notifyConOK

    @notifyConOK.setter
    def notifyConOK(self, value: bool):
        self._notifyConOK = value

    @property
    def notifyPause(self) -> int:
        return self._notifyPause

    @notifyPause.setter
    def notifyPause(self, value: int):
        self._notifyPause = value

    @property
    def notifyIncludeVideo(self) -> bool:
        return self._notifyIncludeVideo

    @notifyIncludeVideo.setter
    def notifyIncludeVideo(self, value: bool):
        self._notifyIncludeVideo = value

    @property
    def notifyIncludePhoto(self) -> bool:
        return self._notifyIncludePhoto

    @notifyIncludePhoto.setter
    def notifyIncludePhoto(self, value: bool):
        self._notifyIncludePhoto = value

    @property
    def notifySavePwd(self) -> bool:
        return self._notifySavePwd

    @notifySavePwd.setter
    def notifySavePwd(self, value: bool):
        self._notifySavePwd = value

    @property
    def notifyPwdPath(self) -> str:
        return self._notifyPwdPath

    @notifyPwdPath.setter
    def notifyPwdPath(self, value: str):
        self._notifyPwdPath = value

    @property
    def notifyFrom(self) -> str:
        return self._notifyFrom

    @notifyFrom.setter
    def notifyFrom(self, value: str):
        self._notifyFrom = value

    @property
    def notifyTo(self) -> str:
        return self._notifyTo

    @notifyTo.setter
    def notifyTo(self, value: str):
        self._notifyTo = value

    @property
    def notifySubject(self) -> str:
        return self._notifySubject

    @notifySubject.setter
    def notifySubject(self, value: str):
        self._notifySubject = value

    @property
    def retentionPeriod(self) -> int:
        return self._retentionPeriod

    @retentionPeriod.setter
    def retentionPeriod(self, value: int):
        self._retentionPeriod = value

    @property
    def retentionPeriodStr(self) -> str:
        return str(self._retentionPeriod)

    @property
    def evStart(self) -> datetime:
        return self._evStart

    @evStart.setter
    def evStart(self, value: datetime):
        if value is None:
            val = None
        else:
            val = datetime(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute)
        self._evStart = val

    @property
    def evStartDateStr(self) -> str:
        return self._evStart.isoformat()[:10]

    @evStartDateStr.setter
    def evStartDateStr(self, value: str):
        try:
            d = date.fromisoformat(value)
        except ValueError:
            d = datetime.now()
        v = datetime(year=d.year, month=d.month, day=d.day, hour=self._evStart.hour, minute=self._evStart.minute)        
        self._evStart = v

    @property
    def evStartTimeStr(self) -> str:
        return self._evStart.isoformat()[11:16]

    @evStartTimeStr.setter
    def evStartTimeStr(self, value: str):
        try:
            d = time.fromisoformat(value)
        except ValueError:
            d = datetime.now()
        v = datetime(year=self._evStart.year, month=self._evStart.month, day=self._evStart.day, hour=d.hour, minute=d.minute)        
        self._evStart = v
    
    @property
    def evStartIso(self) -> str:
        return self._evStart.isoformat()
    
    def evStartMidnight(self):
        self._evStart = datetime(year=self._evStart.year, month=self._evStart.month, day=self._evStart.day, hour=0, minute=0)

    @property
    def evIncludePhoto(self) -> bool:
        return self._evIncludePhoto

    @evIncludePhoto.setter
    def evIncludePhoto(self, value: bool):
        self._evIncludePhoto = value

    @property
    def evIncludeVideo(self) -> bool:
        return self._evIncludeVideo

    @evIncludeVideo.setter
    def evIncludeVideo(self, value: bool):
        self._evIncludeVideo = value

    @property
    def evAutoRefresh(self) -> bool:
        return self._evAutoRefresh

    @evAutoRefresh.setter
    def evAutoRefresh(self, value: bool):
        self._evAutoRefresh = value

    @property
    def calStart(self) -> datetime:
        return self._calStart

    @calStart.setter
    def calStart(self, value: datetime):
        if value == None:
            val = None
        else:
            val = datetime(year=value.year, month=value.month, day=1, hour=0, minute=0, second=0)
        self._calStart = val

    @property
    def calStartDateStr(self) -> str:
        return self._calStart.isoformat()[:10]

    @calStartDateStr.setter
    def calStartDateStr(self, value: str):
        try:
            d = date.fromisoformat(value)
        except ValueError:
            d = datetime.now()
        v = datetime(year=d.year, month=d.month, day=1, hour=0, minute=0)        
        self._evStart = v

    @property
    def error(self) -> str:
        return self._error

    @error.setter
    def error(self, value: str):
        self._error = value
        if value is None:
            self._errorSource = None
            self._error2 = None

    @property
    def error2(self) -> str:
        return self._error2

    @error2.setter
    def error2(self, value: str):
        self._error2 = value

    @property
    def errorSource(self) -> str:
        return self._errorSource

    @errorSource.setter
    def errorSource(self, value: str):
        self._errorSource = value

    @property
    def triggers(self) -> list[Trigger]:
        return self._triggers

    @triggers.setter
    def triggers(self, value: list[Trigger]):
        self._triggers = value

    @property
    def actions(self) -> list:
        return self._actions

    @actions.setter
    def actions(self, value: list):
        self._actions = value
        
    @property
    def eventList(self) -> list:
        return self.getEventList()
        
    def getEventList(self) -> list:
        db = dbx.get_dbx()
        events = []
        seldate = self.evStartDateStr
        seltime = self.evStartTimeStr
        eventsdb = db.execute("SELECT * FROM events WHERE date = ? AND minute >= ?",
                              (seldate, seltime)
        ).fetchall()
        
        for eventdb in eventsdb:
            eventContainer = {}
            event = {}
            event["timestamp"] = eventdb["timestamp"]
            event["date"] = eventdb["date"]
            event["time"] = eventdb["time"]
            event["type"] = eventdb["type"]
            event["trigger"] = eventdb["trigger"]
            event["triggertype"] = eventdb["triggertype"]
            tps = eventdb["triggerparam"]
            # Handle DB entries from previous releases where params were just strings and no dict
            handleAsStr = True
            tpd = {}
            try:
                tpdt = literal_eval(tps)
                if isinstance(tpdt, dict):
                    tpd = tpdt
                    handleAsStr = False                   
            except Exception:
                pass
            if handleAsStr == True:
                if tps[:5] == "msd: ":
                    tpd["msd"] = tps[5:]
                else:
                    tpd["par"] = tps
            event["triggerparam"] = tpd
            eventContainer["event"] = event
            events.append(eventContainer)
            
        if self.evIncludeVideo:
            for ev in events:
                event = ev["event"]
                ts = event["timestamp"]
                eventactions = db.execute("SELECT * FROM eventactions WHERE event = ? AND actiontype = ?",
                                    (ts, "Video")
                ).fetchone()
                if eventactions is None:
                    eventVideo = {}
                else:
                    eventVideo = {}
                    eventVideo["timestamp"] = eventactions["timestamp"]
                    eventVideo["date"] = eventactions["date"]
                    eventVideo["time"] = eventactions["time"]
                    eventVideo["duration"] = round(eventactions["actionduration"], 0)
                    eventVideo["filename"] = eventactions["filename"]
                    videophoto = db.execute("SELECT * FROM eventactions WHERE event = ? AND actiontype = ? AND timestamp = ?",
                                        (ts, "Photo", eventactions["timestamp"])
                    ).fetchone()
                    if videophoto is None:
                        eventVideo["photo"] = None
                    else:
                        eventVideo["photo"] = videophoto["filename"]
                ev["video"] = eventVideo

        if self.evIncludePhoto:
            for ev in events:
                event = ev["event"]
                ts = event["timestamp"]
                eventactions = None
                #if self.evIncludeVideo:
                #    if len(ev["video"]) > 0:
                #        eventVideo = ev["video"]
                #        if not eventVideo["photo"] is None:
                #            videoTs = eventVideo["timestamp"]
                #            eventactions = db.execute("SELECT * FROM eventactions WHERE event = ? AND actiontype = ? AND timestamp != ? ORDER BY timestamp ASC",
                #                                (ts, "Photo", videoTs)
                #            ).fetchall()
                if eventactions is None:
                    eventactions = db.execute("SELECT * FROM eventactions WHERE event = ? AND actiontype = ? ORDER BY timestamp ASC",
                                        (ts, "Photo")
                    ).fetchall()
                if eventactions is None:
                    eventPhotos = []
                else:
                    eventPhotos = []
                    for eventactiondb in eventactions:
                        eventPhoto = {}
                        eventPhoto["timestamp"] = eventactiondb["timestamp"]
                        eventPhoto["date"] = eventactiondb["date"]
                        eventPhoto["time"] = eventactiondb["time"]
                        eventPhoto["duration"] = round(eventactiondb["actionduration"], 0)
                        eventPhoto["filename"] = eventactiondb["filename"]
                        eventPhotos.append(eventPhoto)
                ev["photos"] = eventPhotos
        return events

    @property 
    def calendar(self) -> list:
        return self.getCalendar()

    @property 
    def calendarMonthStr(self) -> str:
        return self.calStart.strftime("%B") + " " + str(self.calStart.year)

    def getCalendar(self)-> list:
        """ Setup calendar for the selected month with information on events
        """
        db = dbx.get_dbx()
        wd = self.calStart.isocalendar().weekday
        month = self.calStart.month
        wnrStart = self.calStart.isocalendar().week
        dayStart = self.calStart - timedelta(hours = (wd - 1) * 24)
        
        calendar = []
        dayIter = dayStart
        for week in range(wnrStart, wnrStart + 6):
            calWeek = {}
            calWeek["week"] = week
            weekdays = []
            for weekday in range(1, 8):
                day = {}
                day["day"] = dayIter.day
                day["weekday"] = dayIter.isocalendar().weekday
                day["week"] = dayIter.isocalendar().week
                dayIso = dayIter.isoformat()[:10]
                day["date"] = dayIso
                data = {}
                nrEvents = db.execute("SELECT count(*) FROM events WHERE date = ?",
                                    (dayIso,)
                ).fetchone()[0]
                data["nrevents"] = nrEvents
                day["data"] = data
                weekdays.append(day)
                dayIter = dayIter + timedelta(hours=24)
            calWeek["weekdays"] = weekdays
            calendar.append(calWeek)
            if dayIter.month > month:
                break
        return calendar
    
    def cleanupEvents(self):
        """ Remove all events older than retention period
        """
        logger.debug("TriggerConfig.cleanupEvents")
        db = dbx.get_dbx()
        dr = datetime.now() - timedelta(days=self.retentionPeriod)
        #dr = dr - timedelta(hours=23)
        dateRem = str(dr.isoformat()[:10])
        logger.debug("TriggerConfig.cleanupEvents - Removing %s and earlier", dateRem)
        
        # Cleanup events log
        fpLog = self.logFilePath
        fpLogOld = os.path.dirname(fpLog) + "/_backup.log"
        if os.path.exists(fpLog):
            if os.path.exists(fpLogOld):
                os.remove(fpLogOld)
            os.rename(fpLog, fpLogOld)
        with open(fpLogOld, "r") as src:
            oldLines = src.readlines()
        with open(fpLog, "w") as tgt:
            for line in oldLines:
                if line[:10] > dateRem:
                    tgt.write(line)
        os.remove(fpLogOld)
        logger.debug("Cleaned up %s", fpLog)
        
        # Remove files
        cnt = 0
        evadb = db.execute("SELECT * FROM eventactions WHERE date <= ?", (dateRem,)).fetchall()
        if not evadb is None:
            for eva in evadb:
                fp = eva["fullpath"]
                if os.path.exists(fp):
                    os.remove(fp)
                    cnt += 1
        logger.debug("Removed %s files", cnt)

        # Delete eventactions
        db.execute("DELETE FROM eventactions WHERE date <= ?", (dateRem,)).fetchall()
        db.commit()
        logger.debug("Removed old eventaction")

        # Delete events
        db.execute("DELETE FROM events WHERE date <= ?", (dateRem,)).fetchall()
        db.commit()
        logger.debug("Removed old events")
        
    def checkNotificationRecipient(self, user=None, pwd=None) -> tuple:
        """ Check login to mail server using available credentials

            Return (user, password, error message)
        """
        logger.debug("TriggerConfig.checkNotificationRecipient")
        logger.debug("user: %s, password: %s", user, pwd)
        err = ""
        secHost = ""
        secPort = -1
        secUseSSL = None
        secAuthenticate = None
        secUser = ""
        secPwd = ""
        secretsOK = False
        # Try to get credentials from the file
        if os.path.exists(self.notifyPwdPath):
            with open(self.notifyPwdPath) as f:
                try:
                    secrets = json.load(f)
                    notifySecrets = secrets["eventnotification"]
                    secHost = notifySecrets["host"]
                    secPort = notifySecrets["port"]
                    secUseSSL = notifySecrets["useSSL"]
                    if "authentication" in notifySecrets:
                        secAuthenticate = notifySecrets["authentication"]
                    secUser = notifySecrets["user"]
                    secPwd = notifySecrets["password"]
                    secretsOK = True
                    logger.debug("TriggerConfig.checkNotificationRecipient - read credentials from file")
                except Exception as e:
                    pass
        if secHost == "":
            secHost = self.notifyHost
        else:
            if secHost != self.notifyHost:
                secHost = self.notifyHost
                secretsOK = False
        if secPort == -1:
            secPort = self.notifyPort
        else:
            if secPort != self.notifyPort:
                secPort = self.notifyPort
                secretsOK = False
        if secUseSSL is None:
            secUseSSL = self.notifyUseSSL
        else:
            if secUseSSL != self.notifyUseSSL:
                secUseSSL = self.notifyUseSSL
                secretsOK = False
        if secAuthenticate is None:
            secAuthenticate = self.notifyAuthenticate
        else:
            if secAuthenticate != self.notifyAuthenticate:
                secAuthenticate = self.notifyAuthenticate
                secretsOK = False
        if secUser == "":
            if not user is None:
                secUser = user
        else:
            if not user is None:
                if user != "":
                    secUser = user
                    secretsOK = False
        if secPwd == "":
            if not pwd is None:
                secPwd = pwd
        else:
            if not pwd is None:
                if pwd != "":
                    secPwd = pwd
                    secretsOK = False
                    
        # Test SSL
     # TODO: Investigate why this test no longer works
       #try:
        #    with smtplib.SMTP_SSL(host=secHost, port=secPort) as smtp_ssl:
        #        smtp_ssl.ehlo()
        #        if secUseSSL == False:
        #            err = "Server requires SSL"
        #except (smtplib.SMTPConnectError, ConnectionRefusedError):
        #    if secUseSSL == True:
        #        err = "Server does not require SSL"
        
        # Test connection
        if err == "":
            try:
                if secUseSSL == True:
                    server = smtplib.SMTP_SSL(host=secHost, port=secPort)
                else:
                    server = smtplib.SMTP(host=secHost, port=secPort)
                server.connect(secHost)
                server.ehlo()
                if secAuthenticate == True:
                    logger.debug("Authentication with user/pwd")
                    server.login(secUser, secPwd)
                else:
                    if "auth" in server.esmtp_features:
                        err = "The server requires authentication. Please provide 'User' and 'Password'"
                    logger.debug("Authentication skipped")
                server.quit()
                logger.debug("TriggerConfig.checkNotificationRecipient - connection test successful")
            except Exception as e:
                logger.debug("TriggerConfig.checkNotificationRecipient - connection test failed")
                err = "Connection error: " + str(e)
            
        if err == "":
            self.notifyConOK = True
            if secretsOK == False:
                if self.notifySavePwd == True:
                    # Store credentials
                    if self.notifyPwdPath == "":
                        err = "Please enter the file path for storage of credentials!"
                    else:
                        if not os.path.exists(self.notifyPwdPath):
                            fp = Path(self.notifyPwdPath)
                            dir = fp.parent.absolute()
                            fn = fp.name
                            if not os.path.exists(dir):
                                os.makedirs(dir, exist_ok=True)
                            self.notifyPwdPath = str(dir) + "/" + fn
                            Path(self.notifyPwdPath).touch(exist_ok=True)
                        else:
                            if os.path.isdir(self.notifyPwdPath):
                                err = "The 'Password File Path' must be a file and not a directory!"
                        secrets = {}
                        if err == "":
                            if os.stat(self.notifyPwdPath).st_size > 0:
                                with open(self.notifyPwdPath, "r") as f:
                                    try:
                                        secrets = json.load(f)
                                    except Exception as e:
                                        err = "The file specified as 'Password File Path' has content which is not in JSON format"
                        if err == "":
                            if "eventnotification" in secrets:
                                notifySecrets = secrets["eventnotification"]
                            else:
                                notifySecrets = {}
                                secrets["eventnotification"] = notifySecrets
                            notifySecrets["host"] = self.notifyHost
                            notifySecrets["port"] = self.notifyPort
                            notifySecrets["useSSL"] = self.notifyUseSSL
                            notifySecrets["authentication"] = self.notifyAuthenticate
                            notifySecrets["user"] = secUser
                            notifySecrets["password"] = secPwd
                            with open(self.notifyPwdPath, "w") as f:
                                try:
                                    json.dump(secrets,fp=f, indent=4)
                                    logger.debug("TriggerConfig.checkNotificationRecipient - saved credentials to file %s", self.notifyPwdPath)
                                except Exception as e:
                                    logger.err("TriggerConfig.checkNotificationRecipient - error while saving credentials to file %s: %s", self.notifyPwdPath, e)
                                    err = "Error writing to " + self.notifyPwdPath + ": " + str(e)
        else:
            self.notifyConOK = False
        return (secUser, secPwd, err)
    
    def triggerSources(self) -> list[str]:
        """ Return a list of trigger sources

            Trigger sources are:
            - 'Camera'          : Camera-based triggers
            - 'GPIO'            : for GPIO input devices
            - 'MotionDetector'  : for motion detection using a camera
        Returns:
            list[str] : List of trigger sources
        """
        triggerSources = ["Camera", "GPIO", "MotionDetector"]
        
        return triggerSources
        
    def actionSources(self) -> list[str]:
        """ Return a list of action sources

            Action sources are:
            - 'Camera'  : for photo taking and video recording
            - 'GPIO'    : for GPIO output devices

        Returns:
            list[str]: List of action sources
        """
        actionSources = ["Camera", "GPIO", "SMTP"]
        
        return actionSources
    
    def triggerDevices(self, source:str) -> list[str]:
        """ Return a list of trigger devices for the given source

            for source 'Camera':
                - "CAM-1"
                - "CAM-2"
            for source 'GPIO':
                - list of IDs of Input devices
            for source 'MotionDetector':
                - "CAM-1"
        Args:
            source (str): trigger source ('Camera' or 'GPIO')

        Returns:
            list[str]: list of devices
        """
        logger.debug("TriggerConfig.triggerDevices")
        deviceList = []
        if source == "Camera":
            deviceList = ["CAM-1",]
            if len(CameraCfg().cameras) > 1:
                deviceList.append("CAM-2")
        elif source == "MotionDetector":
            deviceList = ["CAM-1",]
        elif source == "GPIO":
            devices = CameraCfg().serverConfig.gpioDevices
            for device in devices:
                if device.usage == "Input" \
                and device.isOk == True:
                    id = device.id
                    deviceList.append(id)
        return deviceList
    
    def actionDevices(self, source:str) -> list[str]:
        """ Return a list of action devices for the given source

            for source 'Camera':
                - "CAM-1"
            for source 'GPIO':
                - list of IDs of Output devices
            for source 'SMTP':
                - The configured SMTP srver, if any
        Args:
            source (str): trigger source ('Camera' or 'GPIO')

        Returns:
            list[str]: list of devices
        """
        deviceList = []
        if source == "Camera":
            deviceList = ["CAM-1",]
        if source == "SMTP":
            deviceList = [self._notifyHost,]
        elif source == "GPIO":
            devices = CameraCfg().serverConfig.gpioDevices
            for device in devices:
                if device.usage == "Output":
                    id = device.id
                    deviceList.append(id)
        return deviceList
    
    def triggerEvents(self, source:str, device:str) -> tuple[list[str], dict, dict]:
        """ Return lists of events and event settings for the given device
        
            The returned events are methods which allow assignment of callback routines
        Args:
            source (str): Source ('Camera' or 'GPIO')
            device (str): Device

        Returns:
            tuple[list[str], dict]: 
                - list of events
                - dict of event settings
                - dict of control data
        """
        events = []
        eventSettings = {}
        control = {}
        if source == "Camera":
            if device == "CAM-1":
                events = [
                    "when_photo_taken", 
                    "when_series_photo_taken", 
                    "when_recording_starts",
                    "when_recording_stops",
                    "when_streaming_1_starts",
                    "when_streaming_1_stops",
                    "when_motion_detected",
                ]
                control = {
                    "event_log": False
                }
            elif device == "CAM-2":
                events = [
                    "when_streaming_2_starts",
                    "when_streaming_2_stops",
                ]
                control = {
                    "event_log": False
                }
        elif source == "MotionDetector":
            if device == "CAM-1":
                events = [
                    "when_motion_detected", 
                ]
                control = {}
        elif source == "GPIO":
            gpioDev = CameraCfg().serverConfig.getDevice(device)
            if gpioDev is not None:
                devType = gpioDev.type
                for typ in gpioDeviceTypes:
                    if typ["type"] == devType:
                        if "events" in typ:
                            events = typ["events"]
                        if "eventSettings" in typ:
                            eventSettings = typ["eventSettings"]
                        if "control" in typ:
                            control = typ["control"]
                        break
        return events, eventSettings, control
    
    def actionTargets(self, source:str, device:str) -> list[str]:
        """ Return lists of action targets for the given device
        
            The returned actions are methods or properties for the device type
        Args:
            source (str): Source ('Camera' or 'GPIO')
            device (str): Device

        Returns:
            list[str]: list of action targets
        """
        actionTargets = []
        if source == "Camera":
            actionTargets = []
            actionTargets = [
                {
                    "method": "take_photo",
                    "params": {
                        "type": "jpg"
                        },
                    "control": {
                        "burst_count": 1,
                        "burst_intvl": 1.0
                    }
                },
                {
                    "method": "record_video",
                    "params": {
                        "type": "mp4"
                    },
                    "control": {
                        "duration": 1
                    }
                },
                {
                    "method": "start_video",
                    "params": {
                        "type": "mp4"
                    },
                    "control": {
                    }
                },
                {
                    "method": "stop_video",
                    "params": {},
                    "control": {}
                }
            ]
        elif source == "SMTP":
            actionTargets = [
                {
                    "method": "send_mail",
                    "params": {},
                    "control": {
                        "attach_photo": False,
                        "attach_video": False
                    }
                }
            ]
        elif source == "GPIO":
            gpioDev = CameraCfg().serverConfig.getDevice(device)
            if gpioDev is not None:
                devType = gpioDev.type
                for typ in gpioDeviceTypes:
                    if typ["type"] == devType:
                        if "actionTargets" in typ:
                            actionTargets = typ["actionTargets"]
                        break
        return actionTargets
    
    def getTrigger(self, id:str) -> Trigger:
        """ Return a trigger with a specific ID

        Args:
            id (str): ID of trigger to be returned

        Returns:
            Trigger: Trigger with the given ID or None
        """
        trigger = None
        for trg in self.triggers:
            if trg.id == id:
                trigger = trg
                break
        return trigger
    
    def getAction(self, id:str) -> Action:
        """ Return an action with a specific ID

        Args:
            id (str): ID of action to be returned

        Returns:
            Action: Action with the given ID or None
        """
        action = None
        for act in self.actions:
            if act.id == id:
                action = act
                break
        return action

    @classmethod                
    def initFromDict(cls, dict:dict):
        cc = TriggerConfig()
        for key, value in dict.items():
            if value is None:
                setattr(cc, key, value)
            elif key == "_triggers":
                if value is None:
                    setattr(cc, key, value)
                else:
                    triggers = []
                    for trg in value:
                        trigger = Trigger.initFromDict(trg)
                        triggers.append(trigger)
                    setattr(cc, key, triggers)
            elif key == "_actions":
                if value is None:
                    setattr(cc, key, value)
                else:
                    actions = []
                    for act in value:
                        action = Action.initFromDict(act)
                        actions.append(action)
                    setattr(cc, key, actions)
            else:
                setattr(cc, key, value)
        #Reset some default values for which imported values shall be ignored
        cc.evStart = None
        cc.calStart = None
        cc.notifyConOK = False
        #Reset error
        cc._error = None
        cc._error2 = None
        cc._errorSource = None
        return cc

class CameraInfo():
    def __init__(self):
        self._model = ""
        self._isUsb = False
        self._location = 0
        self._rotation = 0
        self._id = ""
        self._num = 0
        self._status = ""

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    @property
    def isUsb(self) -> bool:
        return self._isUsb

    @isUsb.setter
    def isUsb(self, value: bool):
        self._isUsb = value
        
    @property
    def location(self) -> int:
        return self._location

    @location.setter
    def location(self, value: int):
        self._location = value

    @property
    def rotation(self) -> int:
        return self._rotation

    @rotation.setter
    def rotation(self, value: int):
        self._rotation = value

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def num(self) -> int:
        return self._num

    @num.setter
    def num(self, value: int):
        self._num = value

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        self._status = value

class CameraControls():
    def __init__(self):
        self._aeConstraintMode = 0
        self.include_aeConstraintMode = False
        self._aeEnable = True
        self.include_aeEnable = False
        self._aeExposureMode = 0
        self.include_aeExposureMode = False
        self._aeFlickerMode = 0
        self.include_aeFlickerMode = False
        self._aeFlickerPeriod = 10000
        self.include_aeFlickerPeriod = False
        self._aeMeteringMode = 0
        self.include_aeMeteringMode = False
        self._afMode = 0
        self.include_afMode = False
        self._lensPosition = 1.0
        self.include_lensPosition = False
        self._afMetering = 0
        self.include_afMetering = False
        self._afPause = 0
        self.include_afPause = False
        self._afRange = 0
        self.include_afRange = False
        self._afSpeed = 0
        self.include_afSpeed = False
        self._afTrigger = 0
        self.include_afTrigger = False
        self._afWindows = ()
        self.include_afWindows = False
        self._analogueGain = 1.0
        self.include_analogueGain = False
        self._awbEnable = True
        self.include_awbEnable = False
        self._awbMode = 0
        self.include_awbMode = False
        self._brightness = 0.0
        self.include_brightness = False
        self._colourGains = (0, 0)
        self.include_colourGains = False
        self._contrast = 1.0
        self.include_contrast = False
        self._exposureTime = 0
        self.include_exposureTime = False
        self._exposureValue = 0.0
        self.include_exposureValue = False
        self._frameDurationLimits = (0, 0)
        self.include_frameDurationLimits = False
        self._hdrMode = 0
        self.include_hdrMode = False
        self._noiseReductionMode = 0
        self.include_noiseReductionMode = False
        self._saturation = 1.0
        self.include_saturation = False
        self._scalerCrop = (0, 0, 4608, 2592)
        self.include_scalerCrop = False
        self._sharpness = 1.0
        self.include_sharpness = False

    def dict(self) -> dict:
        dict={}
        dict["AeConstraintMode"] = [self.include_aeConstraintMode, self._aeConstraintMode]
        dict["AeEnable"] = [self.include_aeEnable, self._aeEnable ]
        dict["AeExposureMode"] = [self.include_aeExposureMode, self._aeExposureMode]
        dict["AeFlickerMode"] = [self.include_aeFlickerMode, self._aeFlickerMode]
        dict["AeFlickerPeriod"] = [self.include_aeFlickerPeriod, self._aeFlickerPeriod]
        dict["AeMeteringMode"] = [self.include_aeMeteringMode, self._aeMeteringMode]
        dict["AfMode"] = [self.include_afMode, self._afMode]
        dict["LensPosition"] = [self.include_lensPosition, self._lensPosition]
        dict["AfMetering"] = [self.include_afMetering, self._afMetering]
        dict["AfPause"] = [self.include_afPause, self._afPause]
        dict["AfRange"] = [self.include_afRange, self._afRange]
        dict["AfSpeed"] = [self.include_afSpeed, self._afSpeed]
        dict["AfTrigger"] = [self.include_afTrigger, self._afTrigger]
        dict["AfWindows"] = [self.include_afWindows, self._afWindows]
        dict["AnalogueGain"] = [self.include_analogueGain, self._analogueGain]
        dict["AwbEnable"] = [self.include_awbEnable, self._awbEnable]
        dict["AwbMode"] = [self.include_awbMode, self._awbMode]
        dict["Brightness"] = [self.include_brightness, self._brightness]
        dict["ColourGains"] = [self.include_colourGains, self._colourGains]
        dict["Contrast"] = [self.include_contrast, self._contrast]
        dict["ExposureTime"] = [self.include_exposureTime, self._exposureTime]
        dict["ExposureValue"] = [self.include_exposureValue, self._exposureValue]
        dict["FrameDurationLimits"] = [self.include_frameDurationLimits, self._frameDurationLimits]
        dict["HdrMode"] = [self.include_hdrMode, self._hdrMode]
        dict["NoiseReductionMode"] = [self.include_noiseReductionMode, self._noiseReductionMode]
        dict["Saturation"] = [self.include_saturation, self._saturation]
        dict["ScalerCrop"] = [self.include_scalerCrop, self._scalerCrop]
        dict["Sharpness"] = [self.include_sharpness, self._sharpness]
        return dict
        
    @property
    def aeConstraintMode(self) -> int:
        return self._aeConstraintMode

    @aeConstraintMode.setter
    def aeConstraintMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2 \
        or value == 3:
            self._aeConstraintMode = value
        else:
            raise ValueError("Invalid value for aeConstraintMode")

    @aeConstraintMode.deleter
    def aeConstraintMode(self):
        del self._aeConstraintMode

    @property
    def aeEnable(self) -> bool:
        return self._aeEnable

    @aeEnable.setter
    def aeEnable(self, value: bool):
        self._aeEnable = value

    @aeEnable.deleter
    def aeEnable(self):
        del self._aeEnable
        
    @property
    def aeExposureMode(self) -> int:
        return self._aeExposureMode

    @aeExposureMode.setter
    def aeExposureMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2 \
        or value == 3:
            self._aeExposureMode = value
        else:
            raise ValueError("Invalid value for aeExposureMode")

    @aeExposureMode.deleter
    def aeExposureMode(self):
        del self._aeExposureMode
        
    @property
    def aeFlickerMode(self) -> int:
        return self._aeFlickerMode

    @aeFlickerMode.setter
    def aeFlickerMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._aeFlickerMode = value
        else:
            raise ValueError("Invalid value for aeFlickerMode")

    @aeFlickerMode.deleter
    def aeFlickerMode(self):
        del self._aeFlickerMode
        
    @property
    def aeFlickerPeriod(self) -> int:
        return self._aeFlickerPeriod

    @aeFlickerPeriod.setter
    def aeFlickerPeriod(self, value: int):
        if value > 0:
            self._aeFlickerPeriod = value
        else:
            raise ValueError("Invalid value for aeFlickerPeriod")

    @aeFlickerPeriod.deleter
    def aeFlickerPeriod(self):
        del self._aeFlickerPeriod
        
    @property
    def aeMeteringMode(self) -> int:
        return self._aeMeteringMode

    @aeMeteringMode.setter
    def aeMeteringMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2 \
        or value == 3:
            self._aeMeteringMode = value
        else:
            raise ValueError("Invalid value for aeMeteringMode")

    @aeMeteringMode.deleter
    def aeMeteringMode(self):
        del self._aeMeteringMode

    @property
    def afMode(self) -> int:
        return self._afMode

    @afMode.setter
    def afMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._afMode = value
        else:
            raise ValueError("Invalid value for afMode")

    @afMode.deleter
    def afMode(self):
        del self._afMode
        
    @property
    def lensPosition(self) -> float:
        return self._lensPosition
    
    @lensPosition.setter
    def lensPosition(self, value: float):
        if value >= 0.0 \
        and value <= 32.0:
            self._lensPosition = value
        else:
            raise ValueError("Invalid value for lens position. Allowed range is (0,32)")
    @lensPosition.deleter
    def lensPosition(self):
        del self._lensPosition
        
    @property
    def focalDistance(self) -> float:
        if self._lensPosition == 0:
            return 9999.9
        else:
            fd = 1.0 / self._lensPosition
            fd = int(1000 * fd)/1000
            return fd
    @focalDistance.setter
    def focalDistance(self, value: float):
        if value > 0:
            if value > 9999.9:
                self._lensPosition = 0
            else:
                self._lensPosition = 1.0 / value
        else:
            raise ValueError("focalDistance must be > 0")
        
    @property
    def afMetering(self) -> int:
        return self._afMetering

    @afMetering.setter
    def afMetering(self, value: int):
        if value == 0 \
        or value == 1:
            self._afMetering = value
        else:
            raise ValueError("Invalid value for afMetering")

    @afMetering.deleter
    def afMetering(self):
        del self._afMetering
        
    @property
    def afPause(self) -> int:
        return self._afPause

    @afPause.setter
    def afPause(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._afPause = value
        else:
            raise ValueError("Invalid value for afPause")

    @afPause.deleter
    def afPause(self):
        del self._afPause
        
    @property
    def afRange(self) -> int:
        return self._afRange

    @afRange.setter
    def afRange(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._afRange = value
        else:
            raise ValueError("Invalid value for afRange")

    @afRange.deleter
    def afRange(self):
        del self._afRange
        
    @property
    def afSpeed(self) -> int:
        return self._afSpeed

    @afSpeed.setter
    def afSpeed(self, value: int):
        if value == 0 \
        or value == 1:
            self._afSpeed = value
        else:
            raise ValueError("Invalid value for afSpeed")

    @afSpeed.deleter
    def afSpeed(self):
        del self._afSpeed
        
    @property
    def scalerCrop(self) -> tuple:
        return self._scalerCrop

    @scalerCrop.setter
    def scalerCrop(self, value: tuple):
        self._scalerCrop = value

    @scalerCrop.deleter
    def scalerCrop(self):
        del self._scalerCrop
        
    @property
    def scalerCropStr(self) -> str:
        return "(" + str(self._scalerCrop[0]) + "," + str(self._scalerCrop[1]) + "," + str(self._scalerCrop[2]) + "," + str(self._scalerCrop[3]) + ")"

    @scalerCropStr.setter
    def scalerCropStr(self, value: str):
        self._scalerCrop = CameraControls._parseRectTuple(value)

    @property
    def afTrigger(self) -> int:
        return self._afTrigger

    @afTrigger.setter
    def afTrigger(self, value: int):
        if value == 0 \
        or value == 1:
            self._afTrigger = value
        else:
            raise ValueError("Invalid value for afTrigger")

    @afTrigger.deleter
    def afTrigger(self):
        del self._afTrigger

    @property
    def afWindows(self) -> tuple:
        return self._afWindows

    @afWindows.setter
    def afWindows(self, value: tuple):
        self._afWindows = value

    @afWindows.deleter
    def afWindows(self):
        del self._afWindows
        
    @property
    def afWindowsStr(self) -> str:
        res = "("
        for win in self.afWindows:
            if len(res) > 1:
                res = res + ","
            res = res + "(" + str(win[0]) + "," + str(win[1]) + "," + str(win[2]) + "," + str(win[3]) + ")"
        res = res + ")"
        return res

    @afWindowsStr.setter
    def afWindowsStr(self, value: str):
        """Parse the string representation for afWindows
        """
        self._afWindows = ()
        # Get the list of windows
        winlist = CameraControls._parseWindows(value)
        for win in winlist:
            awin = CameraControls._parseRectTuple(win)
            # Add window from list to _afWindows tuple
            awin = (awin,)
            self._afWindows += awin

    @property
    def analogueGain(self) -> float:
        return self._analogueGain

    @analogueGain.setter
    def analogueGain(self, value: float):
        if value >= 1:
            self._analogueGain = value
        else:
            raise ValueError("Invalid value for _analogueGain. Must be >= 1.")

    @analogueGain.deleter
    def analogueGain(self):
        del self._analogueGain

    @property
    def awbEnable(self) -> bool:
        return self._awbEnable

    @awbEnable.setter
    def awbEnable(self, value: bool):
        self._awbEnable = value

    @awbEnable.deleter
    def awbEnable(self):
        del self._awbEnable

    @property
    def awbMode(self) -> int:
        return self._awbMode

    @awbMode.setter
    def awbMode(self, value: int):
        if value == 0 \
        or value == 2 \
        or value == 3 \
        or value == 4 \
        or value == 5 \
        or value == 6 \
        or value == 7:
            self._awbMode = value
        else:
            raise ValueError("Invalid value for awbMode")

    @awbMode.deleter
    def awbMode(self):
        del self._awbMode

    @property
    def brightness(self) -> float:
        return self._brightness

    @brightness.setter
    def brightness(self, value: float):
        if value >= -1.0 \
        and value <= 1.0:
            self._brightness = value
        else:
            raise ValueError("Invalid value for brightness. Allowed range is [-1;1]")

    @brightness.deleter
    def brightness(self):
        del self._brightness

    @property
    def colourGains(self) -> tuple:
        return self._colourGains

    @colourGains.setter
    def colourGains(self, value: tuple):
        if len(value) == 2:
            if value[0] >= 0.0 \
            and value[1] >= 0.0 \
            and value[0] <= 32.0 \
            and value[1] <= 32.0:
                self._colourGains = value
            else:
                raise ValueError("Invalid value for colourGains. Values must be in range [0.0;32.0]")
        else:
            raise ValueError("Invalid value for colourGains. Must be tuple of 2")

    @colourGains.deleter
    def colourGains(self):
        del self._colourGains

    @property
    def colourGainRed(self) -> float:
        return self._colourGains[0]

    @property
    def colourGainBlue(self) -> float:
        return self._colourGains[1]

    @property
    def contrast(self) -> float:
        return self._contrast

    @contrast.setter
    def contrast(self, value: float):
        if value >= 0.0 \
        and value <= 32.0:
            self._contrast = value
        else:
            raise ValueError("Invalid value for contrast. Must be in range [0.0, 32.0]")

    @contrast.deleter
    def contrast(self):
        del self._contrast

    @property
    def exposureTime(self) -> int:
        return self._exposureTime

    @exposureTime.setter
    def exposureTime(self, value: int):
        if value >= 0:
            self._exposureTime = value
        else:
            raise ValueError("Invalid value for exposureTime. Must be > 0")

    @exposureTime.deleter
    def exposureTime(self):
        del self._exposureTime

    @property
    def exposureTimeSec(self) -> float:
        return float(self._exposureTime / 1000000)

    @exposureTimeSec.setter
    def exposureTimeSec(self, value: float):
        if value >= 0:
            self._exposureTime = int(value * 1000000)
        else:
            raise ValueError("Invalid value for exposureTime. Must be > 0")

    @property
    def exposureValue(self) -> float:
        return self._exposureValue

    @exposureValue.setter
    def exposureValue(self, value: float):
        if value >= -8.0 \
        and value <= 8.0:
            self._exposureValue = value
        else:
            raise ValueError("Invalid value for exposureValue. Must be in range [-8.0;8.0]")

    @exposureValue.deleter
    def exposureValue(self):
        del self._exposureValue

    @property
    def frameDurationLimits(self) -> tuple:
        return self._frameDurationLimits

    @frameDurationLimits.setter
    def frameDurationLimits(self, value: tuple):
        if value[0] >= 0 \
        and value[1] >= 0:
            self._frameDurationLimits = value
        else:
            raise ValueError("Invalid value for frameDurationLimits")

    @frameDurationLimits.deleter
    def frameDurationLimits(self):
        del self._frameDurationLimits

    @property
    def frameDurationLimitMax(self) -> int:
        return self._frameDurationLimits[0]

    @property
    def frameDurationLimitMin(self) -> int:
        return self._frameDurationLimits[1]

    @property
    def hdrMode(self) -> int:
        return self._hdrMode

    @hdrMode.setter
    def hdrMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2 \
        or value == 3 \
        or value == 4:
            self._hdrMode = value
        else:
            raise ValueError("Invalid value for hdrMode")

    @hdrMode.deleter
    def hdrMode(self):
        del self._hdrMode

    @property
    def noiseReductionMode(self) -> int:
        return self._noiseReductionMode

    @noiseReductionMode.setter
    def noiseReductionMode(self, value: int):
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._noiseReductionMode = value
        else:
            raise ValueError("Invalid value for noiseReductionMode")

    @noiseReductionMode.deleter
    def noiseReductionMode(self):
        del self._noiseReductionMode

    @property
    def saturation(self) -> float:
        return self._saturation

    @saturation.setter
    def saturation(self, value: float):
        if value >= 0.0 \
        and value <= 32.0:
            self._saturation = value
        else:
            raise ValueError("Invalid value for saturation. Must be in range [0.0;32.0]")

    @saturation.deleter
    def saturation(self):
        del self._saturation

    @property
    def sharpness(self) -> float:
        return self._sharpness

    @sharpness.setter
    def sharpness(self, value: float):
        if value >= 0.0 \
        and value <= 16.0:
            self._sharpness = value
        else:
            raise ValueError("Invalid value for sharpness. Must be in range [0.0;16.0]")

    @sharpness.deleter
    def sharpness(self):
        del self._sharpness
    
    @staticmethod    
    def _parseWindows(wins: str) -> list:
        """  Parses the tuple-string of one or multiple rectangles
            "((x,x,x,x),(x,x,x,x))"
            and returns an array of rectangles as strings
        """
        resa = []
        if wins.startswith("("):
            wns = wins[1:]
            if wns.endswith(")"):
                wns = wns[0: len(wns) - 1]
                while len(wns) > 0:
                    i = wns.find(")")
                    if i > 0:
                        wn = wns[0: i + 1]
                        resa.append(wn)
                        if i < len(wns):
                            wns = wns[i + 2:].strip()
                        else:
                            wns = ""
                    else:
                        wns = ""
        return resa

    @staticmethod    
    def _parseRectTuple(stuple: str) -> tuple:
        """  Parse a Python tuple string for libcamera.Rectangle
             "(xOffset, yOffset, width, height)"
        """
        rest = (0, 0, 0, 0)
        if stuple.startswith("("):
            tpl = stuple[1:]
            if tpl.endswith(")"):
                tpl = tpl[0: len(tpl) - 1]
                res = tpl.rsplit(",")
                if len(res) == 4:
                    rest = (int(res[0]), int(res[1]), int(res[2]), int(res[3]))
        return rest

    @classmethod                
    def initFromDict(cls, dict:dict):
        cc = CameraControls()
        for key, value in dict.items():
            if value is None:
                setattr(cc, key, value)
            else:
                if key == "_scalerCrop":
                    setattr(cc, key, tuple(value))
                elif key == "_frameDurationLimits":
                    setattr(cc, key, tuple(value))
                elif key == "_colourGains":
                    setattr(cc, key, tuple(value))
                elif key == "_afWindows":
                    afws = ()
                    for el in value:
                        afw = (tuple(el),)
                        afws += afw
                    setattr(cc, key, afws)
                else:
                    setattr(cc, key, value)
        return cc

class SensorMode():
    """ The class represents a specific sensor mode of the camera
    """
    def __init__(self):
        self._id = None
        self._format = None
        self._unpacked = None
        self._bit_depth = None
        self._size = None
        self._fps = None
        self._crop_limits = None
        self._exposure_limits = None

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value

    @property
    def format(self) -> str:
        return self._format

    @format.setter
    def format(self, value: str):
        self._format = value

    @property
    def unpacked(self) -> str:
        return self._unpacked

    @unpacked.setter
    def unpacked(self, value: str):
        self._unpacked = value

    @property
    def bit_depth(self) -> int:
        return self._bit_depth

    @bit_depth.setter
    def bit_depth(self, value: int):
        self._bit_depth = value

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @size.setter
    def size(self, value: tuple[int, int]):
        self._size = value

    @property
    def fps(self) -> float:
        return self._fps

    @fps.setter
    def fps(self, value: float):
        self._fps = value

    @property
    def crop_limits(self) -> tuple:
        return self._crop_limits

    @crop_limits.setter
    def crop_limits(self, value: tuple):
        self._crop_limits = value

    @property
    def exposure_limits(self) -> tuple:
        return self._exposure_limits

    @exposure_limits.setter
    def exposure_limits(self, value: tuple):
        self._exposure_limits = value

    @property
    def tabId(self) -> str:
        return "sensormode" + str(self.id)

    @property
    def tabButtonId(self) -> str:
        return "sensormodetab" + str(self.id)

    @property
    def tabTitle(self) -> str:
        return "Sensor Mode " + str(self.id)

class TuningConfig():
    def __init__(self):
        self._loadTuningFile = False
        self._tuningFolderDef = None
        self._tuningFolder = None
        self._tuningFile = ""

    @property
    def loadTuningFile(self) -> bool:
        return self._loadTuningFile

    @loadTuningFile.setter
    def loadTuningFile(self, value: bool):
        self._loadTuningFile = value

    @property
    def tuningFolderDef(self) -> str:
        return self._tuningFolderDef

    @property
    def tuningFolder(self) -> str:
        return self._tuningFolder

    @tuningFolder.setter
    def tuningFolder(self, value: str):
        self._tuningFolder = value

    @property
    def tuningFile(self) -> str:
        return self._tuningFile

    @tuningFile.setter
    def tuningFile(self, value: str):
        self._tuningFile = value

    @property
    def tuningFilePath(self) -> str:
        if self.tuningFolder is None:
            return self._tuningFile
        else:
            return self.tuningFolder + "/" + self._tuningFile

    @property
    def isDefaultFolder(self) -> bool:
        return self.tuningFolder == self.tuningFolderDef

    @classmethod                
    def initFromDict(cls, dict:dict):
        cc = TuningConfig()
        for key, value in dict.items():
            if value is None:
                setattr(cc, key, value)
            else:
                setattr(cc, key, value)
        return cc

class CameraConfig():
    def __init__(self):
        self._id = ""
        self._use_case = ""
        self._transform_hflip = False
        self._transform_vflip = False
        self._colour_space = "sYCC"
        self._buffer_count = 1
        self._queue = False
        self._display = None
        self._encode = None
        self._sensor_mode = "0"
        self._stream = "main"
        self._stream_size = None
        self._stream_size_align = False
        self._format = "RGB888"
        self._controls = {}

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def use_case(self) -> str:
        return self._use_case

    @use_case.setter
    def use_case(self, value: str):
        self._use_case = value

    @property
    def transform_hflip(self) -> bool:
        return self._transform_hflip

    @transform_hflip.setter
    def transform_hflip(self, value: bool):
        self._transform_hflip = value

    @property
    def transform_vflip(self) -> bool:
        return self._transform_vflip

    @transform_vflip.setter
    def transform_vflip(self, value: bool):
        self._transform_vflip = value

    @property
    def colour_space(self) -> str:
        return self._colour_space

    @colour_space.setter
    def colour_space(self, value: str):
        if value == "sYCC" \
        or value == "Smpte170m" \
        or value == "Rec709":
            self._colour_space = value
        else:
            raise ValueError("Invalid value for colour_space: %s", value)
        
    @property
    def buffer_count(self) -> int:
        return self._buffer_count

    @buffer_count.setter
    def buffer_count(self, value: int):
        self._buffer_count = value

    @property
    def queue(self) -> bool:
        return self._queue

    @queue.setter
    def queue(self, value: bool):
        self._queue = value

    @property
    def display(self) -> str:
        return self._display

    @display.setter
    def display(self, value: str):
        self._display = value

    @property
    def encode(self) -> str:
        return self._encode

    @encode.setter
    def encode(self, value: str):
        if value is None:
            self._encode = value
        else:
            if value == "main" \
            or value == "lores" \
            or value == "raw":
                self._encode = value
            else:
                raise ValueError("Invalid value for encode: %s", value)

    @property
    def sensor_mode(self) -> str:
        return self._sensor_mode

    @sensor_mode.setter
    def sensor_mode(self, value: str):
        self._sensor_mode = value

    @property
    def stream(self) -> str:
        return self._stream

    @stream.setter
    def stream(self, value: str):
        if value == "main" \
        or value == "lores" \
        or value == "raw":
            self._stream = value
        else:
            raise ValueError("Invalid value for stream: %s. Must be 'main', 'lores' or 'raw'", value)

    @property
    def stream_size(self) -> tuple[int, int]:
        return self._stream_size

    @stream_size.setter
    def stream_size(self, value: tuple[int, int]):
        self._stream_size = value

    @property
    def stream_size_align(self) -> bool:
        return self._stream_size_align

    @stream_size_align.setter
    def stream_size_align(self, value: bool):
        self._stream_size_align = value

    @property
    def format(self) -> str:
        return self._format

    @format.setter
    def format(self, value: str):
        self._format = value

    @property
    def controls(self) -> dict:
        return self._controls

    @controls.setter
    def controls(self, value: dict):
        self._controls = value

    @property
    def tabId(self) -> str:
        return "cfg" + self.id

    @property
    def tabButtonId(self) -> str:
        return "cfg" + self.id + "btn"

    @property
    def tabTitle(self) -> str:
        return "Config " + self.id

    @classmethod                
    def initFromDict(cls, dict:dict):
        cc = CameraConfig()
        for key, value in dict.items():
            if value is None:
                setattr(cc, key, value)
            else:
                if key == "_stream_size":
                    setattr(cc, key, tuple(value))
                elif key == "_controls":
                    ctrlt = {}
                    for ckey, cvalue in value.items():
                        vt = cvalue
                        if ckey == "ScalerCrop":
                            vt = tuple(cvalue)
                        elif ckey == "FrameDurationLimits":
                            vt = tuple(cvalue)
                        elif ckey == "ColourGains":
                            vt = tuple(cvalue)
                        elif ckey == "AfWindows":
                            afws = ()
                            for el in cvalue:
                                afw = (tuple(el),)
                                afws += afw
                            vt = afws
                        else:
                            vt = cvalue
                        ctrlt[ckey] = vt
                    setattr(cc, key, ctrlt)
                else:
                    setattr(cc, key, value)
        return cc
        
class CameraProperties():
    def __init__(self):
        self._hasFocus = True
        self._hasFlicker = True
        self._hasHdr = True
        self._model = None
        self._unitCellSize = None
        self._location = None
        self._rotation = None
        self._pixelArraySize = None
        self._pixelArrayActiveAreas = None
        self._colorFilterArrangement = None
        self._scalerCropMaximum = None
        self.systemDevices = None

    @property
    def hasFocus(self) -> bool:
        return self._hasFocus

    @hasFocus.setter
    def hasFocus(self, value: bool):
        self._hasFocus = value

    @hasFocus.deleter
    def hasFocus(self):
        del self._hasFocus

    @property
    def hasFlicker(self) -> bool:
        return self._hasFlicker

    @hasFlicker.setter
    def hasFlicker(self, value: bool):
        self._hasFlicker = value

    @hasFlicker.deleter
    def hasFlicker(self):
        del self._hasFlicker

    @property
    def hasHdr(self) -> bool:
        return self._hasHdr

    @hasHdr.setter
    def hasHdr(self, value: bool):
        self._hasHdr = value

    @hasHdr.deleter
    def hasHdr(self):
        del self._hasHdr

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    @model.deleter
    def model(self):
        del self._model

    @property
    def unitCellSize(self):
        return self._unitCellSize

    @unitCellSize.setter
    def unitCellSize(self, value: str):
        self._unitCellSize = value

    @unitCellSize.deleter
    def unitCellSize(self):
        del self._unitCellSize

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value: str):
        self._location = value

    @location.deleter
    def location(self):
        del self._location

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value: str):
        self._rotation = value

    @rotation.deleter
    def rotation(self):
        del self._rotation

    @property
    def pixelArraySize(self):
        return self._pixelArraySize

    @pixelArraySize.setter
    def pixelArraySize(self, value: str):
        self._pixelArraySize = value

    @pixelArraySize.deleter
    def pixelArraySize(self):
        del self._pixelArraySize

    @property
    def pixelArrayActiveAreas(self):
        return self._pixelArrayActiveAreas

    @pixelArrayActiveAreas.setter
    def pixelArrayActiveAreas(self, value: str):
        self._pixelArrayActiveAreas = value

    @pixelArrayActiveAreas.deleter
    def pixelArrayActiveAreas(self):
        del self._pixelArrayActiveAreas

    @property
    def colorFilterArrangement(self):
        return self._colorFilterArrangement

    @colorFilterArrangement.setter
    def colorFilterArrangement(self, value: str):
        self._colorFilterArrangement = value

    @colorFilterArrangement.deleter
    def colorFilterArrangement(self):
        del self._colorFilterArrangement

    @property
    def scalerCropMaximum(self):
        return self._scalerCropMaximum

    @scalerCropMaximum.setter
    def scalerCropMaximum(self, value: str):
        self._scalerCropMaximum = value

    @scalerCropMaximum.deleter
    def scalerCropMaximum(self):
        del self._scalerCropMaximum

    @property
    def systemDevices(self):
        return self._systemDevices

    @systemDevices.setter
    def systemDevices(self, value: str):
        self._systemDevices = value

    @systemDevices.deleter
    def systemDevices(self):
        del self._systemDevices

class vButton():
    """ Versatile button

    """
    def __init__(self) -> None:
        self._row = 0
        self._col = 0
        self._isVisible = False
        self._needsConfirm = False
        self._buttonColor = None
        self._buttonShape = None
        self._buttonText = ""
        self._buttonExec = ""

    @property
    def row(self) -> int:
        return self._row

    @row.setter
    def row(self, value: int):
        self._row = value

    @property
    def col(self) -> int:
        return self._col

    @col.setter
    def col(self, value: int):
        self._col = value

    @property
    def isVisible(self) -> bool:
        return self._isVisible

    @isVisible.setter
    def isVisible(self, value: bool):
        self._isVisible = value

    @property
    def needsConfirm(self) -> bool:
        return self._needsConfirm

    @needsConfirm.setter
    def needsConfirm(self, value: bool):
        self._needsConfirm = value
        
    @property
    def buttonColor(self) -> str:
        return self._buttonColor

    @buttonColor.setter
    def buttonColor(self, value: str):
        self._buttonColor = value
        
    @property
    def buttonShape(self) -> str:
        return self._buttonShape

    @buttonShape.setter
    def buttonShape(self, value: str):
        self._buttonShape = value

    @property
    def buttonText(self) -> str:
        return self._buttonText

    @buttonText.setter
    def buttonText(self, value: str):
        self._buttonText = value

    @property
    def buttonExec(self) -> str:
        return self._buttonExec

    @buttonExec.setter
    def buttonExec(self, value: str):
        self._buttonExec = value

    @classmethod                
    def initFromDict(cls, dict:dict):
        vb = vButton()
        for key, value in dict.items():
            if value is None:
                setattr(vb, key, value)
            else:
                setattr(vb, key, value)
        return vb

class ActionButton():
    """ Action button

    """
    def __init__(self) -> None:
        self._row = 0
        self._col = 0
        self._isVisible = False
        self._needsConfirm = False
        self._buttonColor = None
        self._buttonShape = None
        self._buttonText = ""
        self._buttonAction = ""

    @property
    def row(self) -> int:
        return self._row

    @row.setter
    def row(self, value: int):
        self._row = value

    @property
    def col(self) -> int:
        return self._col

    @col.setter
    def col(self, value: int):
        self._col = value

    @property
    def isVisible(self) -> bool:
        return self._isVisible

    @isVisible.setter
    def isVisible(self, value: bool):
        self._isVisible = value

    @property
    def needsConfirm(self) -> bool:
        return self._needsConfirm

    @needsConfirm.setter
    def needsConfirm(self, value: bool):
        self._needsConfirm = value
        
    @property
    def buttonColor(self) -> str:
        return self._buttonColor

    @buttonColor.setter
    def buttonColor(self, value: str):
        self._buttonColor = value
        
    @property
    def buttonShape(self) -> str:
        return self._buttonShape

    @buttonShape.setter
    def buttonShape(self, value: str):
        self._buttonShape = value

    @property
    def buttonText(self) -> str:
        return self._buttonText

    @buttonText.setter
    def buttonText(self, value: str):
        self._buttonText = value

    @property
    def buttonAction(self) -> str:
        return self._buttonAction

    @buttonAction.setter
    def buttonAction(self, value: str):
        self._buttonAction = value

    @classmethod                
    def initFromDict(cls, dict:dict):
        ab = ActionButton()
        for key, value in dict.items():
            if value is None:
                setattr(ab, key, value)
            else:
                setattr(ab, key, value)
        return ab

class ServerConfig():
    def __init__(self):
        self._serverStartTime = None
        self._unsavedChanges = False
        self._error = None
        self._error2 = None
        self._errorSource = None
        self._errorc2 = None
        self._errorc22 = None
        self._errorc2Source = None
        self._database = None
        self._raspiModelFull = ""
        self._raspiModelLower5 = False
        self._boardRevision = ""
        self._kernelVersion = ""
        self._debianVersion = ""
        self._activeCamera = 0
        self._activeCameraInfo = ""
        self._activeCameraModel = ""
        self._hasMicrophone = False
        self._defaultMic = ""
        self._isMicMuted = False
        self._recordAudio = False
        self._audioSync = 0.3
        self._photoRoot = "."
        self._cameraPhotoSubPath = "."
        self._prgOutputPath = "."
        self._photoType = "jpg"
        self._rawPhotoType = "dng"
        self._videoType = "mp4"
        self._isZoomModeDraw = False
        self._zoomFactor = 100
        self._zoomFactorStep = 10
        self._scalerCropLiveView = (0, 0, 4608, 2592)
        self._scalerCropMin = (0, 0, 4608, 2592)
        self._scalerCropMax = (0, 0, 4608, 2592)
        self._scalerCropDef = (0, 0, 4608, 2592)
        self._syncAspectRatio = True
        self._curMenu = "live"
        self._lastLiveTab = "focus"
        self._lastConfigTab = "cfglive"
        self._lastInfoTab = "camprops"
        self._lastPhotoSeriesTab = "series"
        self._lastTriggerTab = "trgcontrol"
        self._lastConsoleTab = "versbuttons"
        self._lastSettingsTab = "settingsparams"
        self._isLiveStream = False
        self._isLiveStream2 = None
        self._isVideoRecording = False
        self._isAudioRecording = False
        self._isPhotoSeriesRecording = False
        self._isTriggerRecording = False
        self._isTriggerWaiting = False
        self._isTriggerTesting = False
        self._isEventhandling = False
        self._isEventsWaiting = False
        self._isDisplayHidden = True
        self._displayPhoto = None
        self._displayFile = None
        self._displayMeta = None
        self._displayMetaFirst = 0
        self._displayMetaLast = 999
        self._displayHistogram = None
        self._displayContent = "meta"
        self._displayBuffer = {}
        self._cv2Available = False
        self._numpyAvailable = False
        self._matplotlibAvailable = False
        self._flaskJwtLibAvailable = False
        self._useHistograms = False
        self._requireAuthForStreaming = False
        self._locLongitude = 0.0
        self._locLatitude = 0.0
        self._locElevation = 0.0
        self._locTzKey = "localtime"
        self._pvCamera = None
        self._pvFrom = None
        self._pvTo = None
        self._pvList = []
        self._useAPI = False
        self._API_active = False
        self._jwtAuthenticationActive = False
        self._jwtKeyStore = ""
        self._jwtAccessTokenExpirationMin = 60
        self._jwtRefreshTokenExpirationDays = 0
        self._streamingClients = []
        self._vButtonsRows = 0
        self._vButtonsCols = 0
        self._vButtons = []
        self._vButtonCommand = None
        self._vButtonArgs = None
        self._vButtonReturncode = None
        self._vButtonStdout = None
        self._vButtonStderr = None
        self._vButtonHasCommandLine = False
        self._aButtonsRows = 0
        self._aButtonsCols = 0
        self._aButtons = []
        self._aButtonAction = None
        self._curDeviceId = ""
        self._curDevice = None
        self._curDeviceType = None
        self._gpioDevices = []
        self._cfgPath = None
        
        # Check access of microphone
        self.checkMicrophone()
        
        # Get Raspi Info
        model = self.getPiModel()
        self._raspiModelFull = model
        if model.startswith("Raspberry Pi 5"):
            self._raspiModelLower5 = False
        elif model.startswith("Raspberry Pi 4"):
            self._raspiModelLower5 = True
        elif model.startswith("Raspberry Pi 3"):
            self._raspiModelLower5 = True
        elif model.startswith("Raspberry Pi 2"):
            self._raspiModelLower5 = True
        elif model.startswith("Raspberry Pi 1"):
            self._raspiModelLower5 = True
        elif model.startswith("Raspberry Pi Zero W"):
            self._raspiModelLower5 = True
        elif model.startswith("Raspberry Pi Zero 2 W"):
            self._raspiModelLower5 = True
        else:
            self._raspiModelLower5 = False

        boardRev = self.getBoardRevision()
        self._boardRevision = boardRev

        debianVers = self.getDebianVersion()
        self._debianVersion = debianVers

        kernelVers = self.getKernelVersion()
        self._kernelVersion = kernelVers

    @property
    def serverStartTime(self) -> datetime:
        return self._serverStartTime

    @serverStartTime.setter
    def serverStartTime(self, value: datetime):
        self._serverStartTime = value

    @property
    def serverStartTimeStr(self) -> str:
        if self._serverStartTime is None:
            return "System time not synced at raspiCamSrv start"
        else:
            return self._serverStartTime.isoformat()

    @property
    def unsavedChanges(self) -> bool:
        return self._unsavedChanges

    @unsavedChanges.setter
    def unsavedChanges(self, value: bool):
        self._unsavedChanges = value

    @property
    def error(self) -> str:
        return self._error

    @error.setter
    def error(self, value: str):
        self._error = value
        if value is None:
            self._errorSource = None
            self._error2 = None

    @property
    def error2(self) -> str:
        return self._error2

    @error2.setter
    def error2(self, value: str):
        self._error2 = value

    @property
    def errorSource(self) -> str:
        return self._errorSource

    @errorSource.setter
    def errorSource(self, value: str):
        self._errorSource = value

    @property
    def errorc2(self) -> str:
        return self._errorc2

    @errorc2.setter
    def errorc2(self, value: str):
        self._errorc2 = value
        if value is None:
            self._errorc2Source = None
            self._errorc22 = None

    @property
    def errorc22(self) -> str:
        return self._errorc22

    @errorc22.setter
    def errorc22(self, value: str):
        self._errorc22 = value

    @property
    def errorc2Source(self) -> str:
        return self._errorc2Source

    @errorc2Source.setter
    def errorc2Source(self, value: str):
        self._errorc2Source = value

    @property
    def database(self) -> str:
        return self._database

    @database.setter
    def database(self, value: str):
        self._database = value

    @property
    def raspiModelFull(self) -> str:
        return self._raspiModelFull

    @raspiModelFull.setter
    def raspiModelFull(self, value: str):
        self._raspiModelFull = value

    @property
    def raspiModelLower5(self) -> bool:
        return self._raspiModelLower5

    @raspiModelLower5.setter
    def raspiModelLower5(self, value: bool):
        self._raspiModelLower5 = value

    @property
    def boardRevision(self) -> str:
        return self._boardRevision

    @boardRevision.setter
    def boardRevision(self, value: str):
        self._boardRevision = value

    @property
    def kernelVersion(self) -> str:
        return self._kernelVersion

    @kernelVersion.setter
    def kernelVersion(self, value: str):
        self._kernelVersion = value

    @property
    def debianVersion(self) -> str:
        return self._debianVersion

    @debianVersion.setter
    def debianVersion(self, value: str):
        self._debianVersion = value

    @property
    def activeCamera(self) -> int:
        return self._activeCamera

    @activeCamera.setter
    def activeCamera(self, value: int):
        self._activeCamera = value

    @property
    def activeCameraInfo(self) -> str:
        return self._activeCameraInfo

    @activeCameraInfo.setter
    def activeCameraInfo(self, value: str):
        self._activeCameraInfo = value

    @property
    def activeCameraModel(self) -> str:
        return self._activeCameraModel

    @activeCameraModel.setter
    def activeCameraModel(self, value: str):
        self._activeCameraModel = value

    @property
    def hasMicrophone(self) -> bool:
        return self._hasMicrophone

    @hasMicrophone.setter
    def hasMicrophone(self, value: bool):
        self._hasMicrophone = value

    @property
    def defaultMic(self) -> str:
        return self._defaultMic

    @defaultMic.setter
    def defaultMic(self, value: str):
        self._defaultMic = value

    @property
    def isMicMuted(self) -> bool:
        return self._isMicMuted

    @isMicMuted.setter
    def isMicMuted(self, value: bool):
        self._isMicMuted = value

    @property
    def recordAudio(self) -> bool:
        return self._recordAudio

    @recordAudio.setter
    def recordAudio(self, value: bool):
        self._recordAudio = value

    @property
    def audioSync(self) -> float:
        return self._audioSync

    @audioSync.setter
    def audioSync(self, value: float):
        self._audioSync = value

    @property
    def photoRoot(self):
        return self._photoRoot

    @photoRoot.setter
    def photoRoot(self, value: str):
        self._photoRoot = value

    @property
    def cameraPhotoSubPath(self):
        return self._cameraPhotoSubPath

    @cameraPhotoSubPath.setter
    def cameraPhotoSubPath(self, value: str):
        self._cameraPhotoSubPath = value

    @property
    def prgOutputPath(self):
        return self._prgOutputPath

    @prgOutputPath.setter
    def prgOutputPath(self, value: str):
        self._prgOutputPath = value

    @property
    def cameraHistogramSubPath(self):
        return self._cameraPhotoSubPath + "/hist"

    @property
    def photoType(self) -> str:
        return self._photoType

    @photoType.setter
    def photoType(self, value: str):
        if value.lower() == "jpg" \
        or value.lower() == "jpeg" \
        or value.lower() == "png" \
        or value.lower() == "gif" \
        or value.lower() == "bmp":
            self._photoType = value
        else:
            raise ValueError("Invalid photo format")

    @property
    def rawPhotoType(self) -> str:
        return self._rawPhotoType

    @rawPhotoType.setter
    def rawPhotoType(self, value: str):
        if value.lower() == "dng":
            self._rawPhotoType = value
        else:
            raise ValueError("Invalid raw photo format")

    @property
    def videoType(self) -> str:
        return self._videoType

    @videoType.setter
    def videoType(self, value: str):
        if value.lower() == "h264" \
        or value.lower() == "mp4":
            self._videoType = value
        else:
            raise ValueError("Invalid video format")

    @property
    def isZoomModeDraw(self) -> bool:
        return self._isZoomModeDraw

    @isZoomModeDraw.setter
    def isZoomModeDraw(self, value: bool):
        self._isZoomModeDraw = value
        
    @property
    def zoomFactor(self):
        return self._zoomFactor

    @zoomFactor.setter
    def zoomFactor(self, value: int):
        if value > 100:
            value = 100
        if value < self.zoomFactorStep:
            value = self.zoomFactorStep
        self._zoomFactor = value

    @property
    def zoomFactorStep(self):
        return self._zoomFactorStep

    @zoomFactorStep.setter
    def zoomFactorStep(self, value: int):
        if value > 20:
            value = 20
        if value < 2:
            value = 2
        self._zoomFactorStep = value

    @property
    def scalerCropLiveView(self) -> tuple:
        return self._scalerCropLiveView

    @scalerCropLiveView.setter
    def scalerCropLiveView(self, value: tuple):
        self._scalerCropLiveView = value
        
    @property
    def scalerCropLiveViewStr(self) -> str:
        return "(" + str(self._scalerCropLiveView[0]) + "," + str(self._scalerCropLiveView[1]) + "," + str(self._scalerCropLiveView[2]) + "," + str(self._scalerCropLiveView[3]) + ")"

    @scalerCropLiveViewStr.setter
    def scalerCropLiveViewStr(self, value: str):
        self._scalerCropLiveView = CameraControls._parseRectTuple(value)

    @property
    def scalerCropMin(self) -> tuple:
        return self._scalerCropMin

    @scalerCropMin.setter
    def scalerCropMin(self, value: tuple):
        self._scalerCropMin = value

    @property
    def scalerCropMax(self) -> tuple:
        return self._scalerCropMax

    @scalerCropMax.setter
    def scalerCropMax(self, value: tuple):
        self._scalerCropMax = value

    @property
    def scalerCropDef(self) -> tuple:
        return self._scalerCropDef

    @scalerCropDef.setter
    def scalerCropDef(self, value: tuple):
        self._scalerCropDef = value

    @property
    def syncAspectRatio(self) -> bool:
        return self._syncAspectRatio

    @syncAspectRatio.setter
    def syncAspectRatio(self, value: bool):
        self._syncAspectRatio = value

    @property
    def curMenu(self) -> str:
        return self._curMenu

    @curMenu.setter
    def curMenu(self, value: str):
        self._curMenu = value

    @property
    def lastLiveTab(self):
        return self._lastLiveTab

    @lastLiveTab.setter
    def lastLiveTab(self, value: str):
        self._lastLiveTab = value

    @property
    def lastConfigTab(self):
        return self._lastConfigTab

    @lastConfigTab.setter
    def lastConfigTab(self, value: str):
        self._lastConfigTab = value

    @property
    def lastInfoTab(self):
        return self._lastInfoTab

    @lastInfoTab.setter
    def lastInfoTab(self, value: str):
        self._lastInfoTab = value

    @property
    def lastPhotoSeriesTab(self):
        return self._lastPhotoSeriesTab

    @lastPhotoSeriesTab.setter
    def lastPhotoSeriesTab(self, value: str):
        self._lastPhotoSeriesTab = value

    @property
    def lastTriggerTab(self):
        return self._lastTriggerTab

    @lastTriggerTab.setter
    def lastTriggerTab(self, value: str):
        self._lastTriggerTab = value

    @property
    def lastConsoleTab(self):
        return self._lastConsoleTab

    @lastConsoleTab.setter
    def lastConsoleTab(self, value: str):
        self._lastConsoleTab = value

    @property
    def lastSettingsTab(self):
        return self._lastSettingsTab

    @lastSettingsTab.setter
    def lastSettingsTab(self, value: str):
        self._lastSettingsTab = value

    @property
    def isDisplayHidden(self) -> bool:
        return self._isDisplayHidden

    @isDisplayHidden.setter
    def isDisplayHidden(self, value: bool):
        self._isDisplayHidden = value

    @property
    def isLiveStream(self) -> bool:
        return self._isLiveStream

    @isLiveStream.setter
    def isLiveStream(self, value: bool):
        self._isLiveStream = value

    @property
    def isLiveStream2(self) -> bool:
        return self._isLiveStream2

    @isLiveStream2.setter
    def isLiveStream2(self, value: bool):
        self._isLiveStream2 = value

    @property
    def isVideoRecording(self) -> bool:
        return self._isVideoRecording

    @isVideoRecording.setter
    def isVideoRecording(self, value: bool):
        self._isVideoRecording = value

    @property
    def isAudioRecording(self) -> bool:
        return self._isAudioRecording

    @isAudioRecording.setter
    def isAudioRecording(self, value: bool):
        self._isAudioRecording = value

    @property
    def isPhotoSeriesRecording(self) -> bool:
        return self._isPhotoSeriesRecording

    @isPhotoSeriesRecording.setter
    def isPhotoSeriesRecording(self, value: bool):
        self._isPhotoSeriesRecording = value

    @property
    def isTriggerRecording(self) -> bool:
        return self._isTriggerRecording

    @isTriggerRecording.setter
    def isTriggerRecording(self, value: bool):
        self._isTriggerRecording = value

    @property
    def isTriggerWaiting(self) -> bool:
        return self._isTriggerWaiting

    @isTriggerWaiting.setter
    def isTriggerWaiting(self, value: bool):
        self._isTriggerWaiting = value

    @property
    def isTriggerTesting(self) -> bool:
        return self._isTriggerTesting

    @isTriggerTesting.setter
    def isTriggerTesting(self, value: bool):
        self._isTriggerTesting = value

    @property
    def isEventhandling(self) -> bool:
        return self._isEventhandling

    @isEventhandling.setter
    def isEventhandling(self, value: bool):
        self._isEventhandling = value

    @property
    def isEventsWaiting(self) -> bool:
        return self._isEventsWaiting

    @isEventsWaiting.setter
    def isEventsWaiting(self, value: bool):
        self._isEventsWaiting = value

    @property
    def buttonClear(self) -> str:
        return "Clr(" + str(self.displayBufferCount) + ")"

    @property
    def displayPhoto(self):
        return self._displayPhoto

    @displayPhoto.setter
    def displayPhoto(self, value: str):
        self._displayPhoto = value

    @property
    def displayFile(self):
        return self._displayFile

    @displayFile.setter
    def displayFile(self, value: str):
        self._displayFile = value

    @property
    def displayMeta(self):
        return self._displayMeta

    @displayMeta.setter
    def displayMeta(self, value: str):
        self._displayMeta = value

    @property
    def displayMetaFirst(self):
        return self._displayMetaFirst

    @displayMetaFirst.setter
    def displayMetaFirst(self, value: int):
        self._displayMetaFirst = value

    @property
    def displayMetaLast(self):
        return self._displayMetaLast

    @displayMetaLast.setter
    def displayMetaLast(self, value: int):
        self._displayMetaLast = value

    @property
    def displayHistogram(self) -> str:
        return self._displayHistogram

    @displayHistogram.setter
    def displayHistogram(self, value: str):
        self._displayHistogram = value

    @property
    def displayContent(self) -> str:
        return self._displayContent

    @displayContent.setter
    def displayContent(self, value: str):
        if value == "meta" \
        or value == "hist":
            self._displayContent = value
        else:
            self._displayContent = "meta"

    @property
    def cv2Available(self) -> bool:
        return self._cv2Available

    @cv2Available.setter
    def cv2Available(self, value: bool):
        self._cv2Available = value

    @property
    def numpyAvailable(self) -> bool:
        return self._numpyAvailable

    @numpyAvailable.setter
    def numpyAvailable(self, value: bool):
        self._numpyAvailable = value

    @property
    def matplotlibAvailable(self) -> bool:
        return self._matplotlibAvailable

    @matplotlibAvailable.setter
    def matplotlibAvailable(self, value: bool):
        self._matplotlibAvailable = value

    @property
    def flaskJwtLibAvailable(self) -> bool:
        return self._flaskJwtLibAvailable

    @flaskJwtLibAvailable.setter
    def flaskJwtLibAvailable(self, value: bool):
        self._flaskJwtLibAvailable = value

    @property
    def useHistograms(self) -> bool:
        return self._useHistograms

    @useHistograms.setter
    def useHistograms(self, value: bool):
        self._useHistograms = value

    @property
    def supportsExtMotionDetection(self) -> bool:
        sup = self.cv2Available \
          and self.matplotlibAvailable \
          and self.numpyAvailable
        return sup

    @property
    def supportsHistograms(self) -> bool:
        sup = self.cv2Available \
          and self.matplotlibAvailable \
          and self.numpyAvailable
        return sup

    @property
    def supportsAPI(self) -> bool:
        sup = self.flaskJwtLibAvailable == True
        return sup

    @property
    def whyNotSupportsHistograms(self) -> str:
        why = ""
        if not self.supportsHistograms:
            why = "Histograms are not supported because"
            if not self.cv2Available:
                why = why + "<br>module cv2 is not available"
            if not self.matplotlibAvailable:
                why = why + "<br>module matplotlib is not available"
            if not self.numpyAvailable:
                why = why + "<br>module numpy is not available"
        return why

    @property
    def whyNotsupportsExtMotionDetection(self) -> str:
        why = ""
        if not self.supportsExtMotionDetection:
            why = "Extended motion detection is not supported because"
            if not self.cv2Available:
                why = why + "<br>module cv2 is not available"
            if not self.matplotlibAvailable:
                why = why + "<br>module matplotlib is not available"
            if not self.numpyAvailable:
                why = why + "<br>module numpy is not available"
        return why

    @property
    def whyNotSupportsAPI(self) -> str:
        why = ""
        if not self.supportsAPI:
            why = "The raspiCamSrv API is not supported because"
            if not self.flaskJwtLibAvailable:
                why = why + "<br>module flask_jwt_extended is not available"
        return why

    @property
    def requireAuthForStreaming(self) -> bool:
        return self._requireAuthForStreaming

    @requireAuthForStreaming.setter
    def requireAuthForStreaming(self, value: bool):
        self._requireAuthForStreaming = value

    @property
    def locLongitude(self) -> float:
        return self._locLongitude

    @locLongitude.setter
    def locLongitude(self, value: float):
        self._locLongitude = value

    @property
    def locLatitude(self) -> float:
        return self._locLatitude

    @locLatitude.setter
    def locLatitude(self, value: float):
        self._locLatitude = value

    @property
    def locElevation(self) -> float:
        return self._locElevation

    @locElevation.setter
    def locElevation(self, value: float):
        self._locElevation = value

    @property
    def locTzKey(self) -> str:
        return self._locTzKey

    @locTzKey.setter
    def locTzKey(self, value: str):
        self._locTzKey = value
        
    def timeZoneKeys(self) -> list:
        tzl = []
        tzs = zoneinfo.available_timezones()
        for tz in tzs:
            tzl.append(tz)
        tzl.sort()
        return tzl

    @property
    def pvCamera(self) -> int:
        return self._pvCamera

    @pvCamera.setter
    def pvCamera(self, value: int):
        self._pvCamera = value
 
    @property
    def pvFrom(self) -> date:
        return self._pvFrom

    @pvFrom.setter
    def pvFrom(self, value: date):
        self._pvFrom = value

    @property
    def pvFromStr(self) -> str:
        return self._pvFrom.isoformat()[:10]

    @pvFromStr.setter
    def pvFromStr(self, value: str):
        try:
            d = date.fromisoformat(value)
        except ValueError:
            d = datetime.now()
        v = datetime(year=d.year, month=d.month, day=d.day, hour=0, minute=0)     
        self._pvFrom = v
 
    @property
    def pvTo(self) -> date:
        return self._pvTo

    @pvTo.setter
    def pvTo(self, value: date):
        self._pvTo = value

    @property
    def pvToStr(self) -> str:
        return self._pvTo.isoformat()[:10]

    @pvToStr.setter
    def pvToStr(self, value: str):
        try:
            d = date.fromisoformat(value)
        except ValueError:
            d = datetime.now()
        v = datetime(year=d.year, month=d.month, day=d.day, hour=23, minute=59, second=59)        
        self._pvTo = v
 
    @property
    def pvList(self) -> list:
        return self._pvList

    @pvList.setter
    def pvList(self, value: list):
        self._pvList = value
 
    @property
    def jwtAuthenticationActive(self) -> bool:
        return self._jwtAuthenticationActive

    @jwtAuthenticationActive.setter
    def jwtAuthenticationActive(self, value: bool):
        self._jwtAuthenticationActive = value

    @property
    def jwtKeyStore(self) -> str:
        return self._jwtKeyStore

    @jwtKeyStore.setter
    def jwtKeyStore(self, value: str):
        self._jwtKeyStore = value
        
    @property
    def jwtAccessTokenExpirationMin(self) -> int:
        return self._jwtAccessTokenExpirationMin

    @jwtAccessTokenExpirationMin.setter
    def jwtAccessTokenExpirationMin(self, value: int):
        self._jwtAccessTokenExpirationMin = value
 
    @property
    def jwtRefreshTokenExpirationDays(self) -> int:
        return self._jwtRefreshTokenExpirationDays

    @jwtRefreshTokenExpirationDays.setter
    def jwtRefreshTokenExpirationDays(self, value: int):
        self._jwtRefreshTokenExpirationDays = value
 
    @property
    def streamingClients(self) -> list:
        return self._streamingClients

    @streamingClients.setter
    def streamingClients(self, value: list):
        self._streamingClients = value

    def registerStreamingClient(self, ipaddr: str, stream: str, thread: int):
        cl = None
        for scl in self.streamingClients:
            if scl["ipaddr"] == ipaddr:
                cl = scl
                break
        if cl is None:
            cl = {}
            cl["ipaddr"] = ipaddr
            streams = []
            s = {}
            s["stream"] = stream
            s["thread"] = thread
            streams.append(s)
            cl["streams"] = streams
            self.streamingClients.append(cl)
        else:
            streams = cl["streams"]
            append = True
            if len(streams) > 0:
                for s in streams:
                    if s["thread"] == thread and s["stream"] == stream:
                        append = False
                        break
            if append == True:
                s = {}
                s["stream"] = stream
                s["thread"] = thread
                streams.append(s)

    def unregisterStreamingClient(self, ipaddr: str, stream: str, thread: int):
        remcl = -1
        idxcl = 0
        for scl in self.streamingClients:
            if scl["ipaddr"] == ipaddr:
                streams = scl["streams"]
                rems = -1
                idxs = 0
                for s in streams:
                    if s["thread"] == thread and s["stream"] == stream:
                        rems = idxs
                    idxs += 1
                if rems >= 0:
                    streams.pop(rems)
                if len(streams) == 0:
                    remcl = idxcl
            idxcl += 1
        if remcl >= 0:
            self.streamingClients.pop(remcl)

    def streamingClientStreams(self, ipaddr: str) -> str:
        res = ""
        for scl in self.streamingClients:
            if scl["ipaddr"] == ipaddr:
                streams = scl["streams"]
                for s in streams:
                    stream = s["stream"]
                    if len(res) == 0:
                        res = stream
                    else:
                        res = res + ", " + stream
        return res
    
    def updateStreamingClients(self):
        for cl in self.streamingClients:
            ip = cl["ipaddr"]
            streams = cl["streams"]
            for s in streams:
                thread = s["thread"]
                is_alive = any([th for th in threading.enumerate() if th.ident == thread])
                if is_alive == False:
                    self.unregisterStreamingClient(ip,s["stream"], thread)

    @property
    def vButtonsRows(self) -> int:
        return self._vButtonsRows

    @vButtonsRows.setter
    def vButtonsRows(self, value: int):
        self._vButtonsRows = value
        
    @property
    def vButtonsCols(self) -> int:
        return self._vButtonsCols

    @vButtonsCols.setter
    def vButtonsCols(self, value: int):
        self._vButtonsCols = value
        
    @property
    def vButtons(self) -> list[list[vButton]]:
        return self._vButtons

    @vButtons.setter
    def vButtons(self, value: list):
        self._vButtons = value
        
    @property
    def vButtonCommand(self) -> str:
        return self._vButtonCommand

    @vButtonCommand.setter
    def vButtonCommand(self, value: str):
        self._vButtonCommand = value
        
    @property
    def vButtonArgs(self) -> list:
        return self._vButtonArgs

    @vButtonArgs.setter
    def vButtonArgs(self, value: list):
        self._vButtonArgs = value
        
    @property
    def vButtonReturncode(self) -> int:
        return self._vButtonReturncode

    @vButtonReturncode.setter
    def vButtonReturncode(self, value: int):
        self._vButtonReturncode = value
        
    @property
    def vButtonStdout(self) -> str:
        return self._vButtonStdout

    @vButtonStdout.setter
    def vButtonStdout(self, value: str):
        self._vButtonStdout = value
        
    @property
    def vButtonStderr(self) -> str:
        return self._vButtonStderr

    @vButtonStderr.setter
    def vButtonStderr(self, value: str):
        self._vButtonStderr = value

    @property
    def vButtonHasCommandLine(self) -> bool:
        return self._vButtonHasCommandLine

    @vButtonHasCommandLine.setter
    def vButtonHasCommandLine(self, value: bool):
        self._vButtonHasCommandLine = value

    @property
    def aButtonsRows(self) -> int:
        return self._aButtonsRows

    @aButtonsRows.setter
    def aButtonsRows(self, value: int):
        self._aButtonsRows = value
        
    @property
    def aButtonsCols(self) -> int:
        return self._aButtonsCols

    @aButtonsCols.setter
    def aButtonsCols(self, value: int):
        self._aButtonsCols = value
        
    @property
    def aButtons(self) -> list[list[ActionButton]]:
        return self._aButtons

    @aButtons.setter
    def aButtons(self, value: list):
        self._aButtons = value
        
    @property
    def aButtonAction(self) -> str:
        return self._aButtonAction

    @aButtonAction.setter
    def aButtonAction(self, value: str):
        self.aButtonAction = value

    @property
    def curDeviceId(self) -> str:
        return self._curDeviceId

    @curDeviceId.setter
    def curDeviceId(self, value: str):
        self._curDeviceId = value

    @property
    def curDevice(self) -> GPIODevice:
        return self._curDevice

    @curDevice.setter
    def curDevice(self, value: GPIODevice):
        self._curDevice = value

    @property
    def curDeviceType(self) -> dict:
        return self._curDeviceType

    @curDeviceType.setter
    def curDeviceType(self, value: dict):
        self._curDeviceType = value
    
    @property
    def gpioDevices(self) ->list[GPIODevice]:
        return self._gpioDevices

    @gpioDevices.setter
    def gpioDevices(self, value: list[GPIODevice]):
        self._gpioDevices = value

    @property
    def cfgPath(self) -> str:
        return self._cfgPath

    @cfgPath.setter
    def cfgPath(self, value: str):
        self._cfgPath = value

    @property
    def API_active(self) -> bool:
        return self._API_active

    @API_active.setter
    def API_active(self, value: bool):
        self._API_active = value
 
    @property
    def useAPI(self) -> bool:
        return self._useAPI

    @useAPI.setter
    def useAPI(self, value: bool):
        self._useAPI = value

    @property
    def processInfo(self) -> str:
        pi = self._countThreads("raspiCamSrv")
        # This subprocess runs in an own thread,
        # So we need to reduce prcNlwp to get the real number of threads
        threadCount = pi[2] - 1
        return f"PID:{pi[0]} Start:{pi[1]} #Threads:{threadCount} CPU Process:{pi[3]} Threads:{pi[4]}"
    
    @property
    def ffmpegProcessInfo(self) -> str:
        pi = self._countThreads("ffmpeg")
        if pi[2] == 0:
            return f"No ffmpeg process active"
        else:
            return f"PID:{pi[0]} Start:{pi[1]} #Threads:{pi[2]} CPU Process:{pi[3]} Threads:{pi[4]}"
    
    @property
    def deviceTypes(self) -> list:
        return gpioDeviceTypes
    
    def getDevice(self, id: str) -> GPIODevice:
        device = None
        for dev in self.gpioDevices:
            if dev.id == id:
                device = dev
                break
        return device
    
    def getDeviceType(self, id: str) -> dict:
        deviceType = None
        for typ in self.deviceTypes:
            if typ["type"] == id:
                deviceType = typ
                break
        return deviceType
    
    @property
    def freeGpioPins(self) -> list[int]:
        """ Return a list with the numbers of free GPIO pins

        Returns:
            list[int]: the free GPIO pins
        """
        pins = []
        for pin in range(0, 28):
            pins.append(pin)
        logger.debug("freeGpioPins")
        for device in self.gpioDevices:
            typ = device.type
            deviceParams = device.params
            devType = self.getDeviceType(typ)
            for param, value in devType["params"].items():
                if "isPin" in value:
                    if value["isPin"] == True:
                        pin = deviceParams[param]
                        if type(pin) is int:
                            if pin in pins:
                                pins.remove(pin)
        return pins
    
    def _checkModule(self, moduleName: str):
        module = None
        try:
            module = importlib.import_module(moduleName)
        except ModuleNotFoundError:
            module = None
        except ImportError:
            module = None
        except Exception:
            module = None
        except:
            module = None
        return module

    def checkEnvironment(self):
        """ Check the availability of specific modules 
            which might be required for specific tasks.
            - cv2
            - numpy
            - matplotlib
        """
        self.cv2Available = self._checkModule("cv2") is not None
        self.numpyAvailable = self._checkModule("numpy") is not None
        self.matplotlibAvailable = self._checkModule("matplotlib") is not None
        self.flaskJwtLibAvailable = self._checkModule("flask_jwt_extended") is not None
        if self.supportsHistograms:
            self.useHistograms = True
        else:
            self.useHistograms = False
        if self.supportsAPI:
            self.useAPI = True
        else:
            self.useAPI = False
        logger.debug("cv2Available: %s numpyAvailable: %s matplotlibAvailable: %s flaskJwtLibAvailable: %s", self. cv2Available, self.numpyAvailable, self.matplotlibAvailable, self.flaskJwtLibAvailable)

    def is_time_synchronized(self) -> tuple[bool, bool]:
        """ Check if the system time is synchronized with NTP server
        
        """
        err = False
        sync = False
        try:
            output = subprocess.check_output(["timedatectl"], text=True)
            for line in output.splitlines():
                if "System clock synchronized:" in line:
                    sync = "yes" in line.split(":")[1].strip().lower()
                    return (err, sync)
        except Exception as e:
            logger.error(f"Error checking time sync: {e}")
            err = True
        return (err, sync)

    def wait_for_time_sync(self, timeout:int=60, interval:int=2) -> bool:
        """ Wait for time synchronization with NTP server

        Args:
            timeout (int, optional): Timeout in seconds. Defaults to 60.
            interval (int, optional): test cycle interval in seconds. Defaults to 2.

        Returns:
            bool: True if time is synchronized, False otherwise
        """
        logger.debug("ServerConfig.wait_for_time_sync")
        for _ in range(int(timeout / interval)):
            (err, sync) = self.is_time_synchronized()
            if err == True:
                break
            if sync == True:
                logger.debug("System time is synchronized")
                self.serverStartTime = datetime.now()
                return True
            else:
                logger.debug("Still waiting for time synchronization...")
            sleep(interval)
        logger.debug("Timeout while waiting for system time synchronization")
        return False    
    
    @property
    def displayBufferCount(self) -> int:
        """ Returns the number of elements in the display buffer
        """
        return len(self._displayBuffer)
    
    @property
    def displayBufferIndex(self) -> str:
        """ Returns the index of the active element in the form (x/y)
        """
        res = ""
        if self.isDisplayBufferIn():
            for i, (key, value) in enumerate(self._displayBuffer.items()):
                if key == self.displayFile:
                    res = "(" + str(i + 1) + "/" + str(self.displayBufferCount) + ")"
                    break
            
        return res

    def isDisplayBufferIn(self) -> bool:
        """Determine whether the current display is in the buffer"""
        res = False
        if len(self._displayBuffer) > 0:
            if self._displayFile in self._displayBuffer:
                res = True
        return res
        
    def displayBufferAdd(self):
        """ Adds the current display photo to the buffer
            if it is not yet included
        """
        if self.isDisplayBufferIn() == False:
            el = {}
            el["displayPhoto"] = self._displayPhoto
            el["displayFile"]  = self._displayFile
            el["displayMeta"]  = self._displayMeta
            el["displayHisto"]  = self._displayHistogram
            el["displayMetaFirst"]  = self._displayMetaFirst
            el["displayMetaLast"]  = self._displayMetaLast
            self._displayBuffer[self._displayFile] = el
        
    def displayBufferRemove(self):
        """ Removes the current display photo from the buffer
            and set active display to next element
        """
        if self.displayBufferCount > 0:
            if self.displayBufferCount == 1:
                # If the buffer contains just one element: clear it
                self.displayBufferClear()
            else:
                # Buffer contains more than one element
                if self.isDisplayBufferIn():
                    # Active element is in buffer
                    idel = -1
                    if self.isDisplayBufferIn() == True:
                        # If active element in buffer: find and delete it
                        for i, (key, value) in enumerate(self._displayBuffer.items()):
                            if key == self.displayFile:
                                idel = i
                                # idel is now the index of the element to activate (show)
                                del self._displayBuffer[key]
                                break
                    if idel >= 0:
                        # If the previouslay active element has been deleted,
                        # activate another element
                        # This will normally the next in buffer ...
                        if idel >= self.displayBufferCount:
                            # ... except when the last element has been deleted.
                            # then activate the previous element
                            idel = idel - 1
                        for i, (key, value) in enumerate(self._displayBuffer.items()):
                            if i == idel:
                                self.displayFile = key
                                self.displayPhoto = value["displayPhoto"]
                                self.displayMeta = value["displayMeta"]
                                self.displayHistogram = value["displayHisto"]
                                self.displayMetaFirst = value["displayMetaFirst"]
                                self.displayMetaLast = value["displayMetaLast"]
                                break
                else:
                    # Active element is not in buffer: Just clear active element
                    self.displayFile = None
                    self.displayPhoto = None
                    self.displayMeta = None
                    self.displayHistogram = None
                    self.displayMetaFirst = 0
                    self.displayMetaLast = 999
        else:
            # Buffer is empty: Just clear active element
            self.displayFile = None
            self.displayPhoto = None
            self.displayMeta = None
            self.displayHistogram = None
            self.displayMetaFirst = 0
            self.displayMetaLast = 999
        
    def displayBufferClear(self):
        """ Clears the display buffer as well as the current display
        """
        self._displayBuffer.clear()
        self.displayFile = None
        self.displayPhoto = None
        self.displayMeta = None
        self.displayHistogram = None
        self.displayMetaFirst = 0
        self.displayMetaLast = 999

    def isDisplayBufferFirst(self) -> bool:
        """Determine whether the current display is the first element in the buffer"""
        res = False
        if self.isDisplayBufferIn():
            for i, (key, value) in enumerate(self._displayBuffer.items()):
                if i == 0:
                    if key == self.displayFile:
                        res = True
                else:
                    break
        return res

    def isDisplayBufferLast(self) -> bool:
        """Determine whether the current display is the last element in the buffer"""
        res = False
        l = len(self._displayBuffer) - 1
        if self.isDisplayBufferIn():
            for i, (key, value) in enumerate(self._displayBuffer.items()):
                if i == l:
                    if key == self.displayFile:
                        res = True
        return res

    def displayBufferFirst(self):
        """Change the current display element to the first in buffer"""
        firstKey = None
        firstEl = None
        if self.displayBufferCount > 0:
            for i, (key, value) in enumerate(self._displayBuffer.items()):
                if i == 0:
                    firstKey = key
                    firstEl = value
                    break
        if firstKey:
            self.displayFile = firstKey
            self.displayPhoto = firstEl["displayPhoto"]
            self.displayMeta = firstEl["displayMeta"]
            self.displayHistogram = firstEl["displayHisto"]
            self.displayMetaFirst = firstEl["displayMetaFirst"]
            self.displayMetaLast = firstEl["displayMetaLast"]

    def displayBufferNext(self):
        """Change the current display element to the next in buffer"""
        nextKey = None
        nextEl = None
        if self.isDisplayBufferIn():
            if not self.isDisplayBufferLast():
                found = False
                for i, (key, value) in enumerate(self._displayBuffer.items()):
                    if key == self.displayFile:
                        found = True
                    else:
                        if found:
                            nextKey = key
                            nextEl = value
                            break
        else:
            self.displayBufferFirst()
        if nextKey:
            self.displayFile = nextKey
            self.displayPhoto = nextEl["displayPhoto"]
            self.displayMeta = nextEl["displayMeta"]
            self.displayHistogram = nextEl["displayHisto"]
            self.displayMetaFirst = nextEl["displayMetaFirst"]
            self.displayMetaLast = nextEl["displayMetaLast"]

    def displayBufferPrev(self):
        """Change the current display element to the previous in buffer"""
        prevKey = None
        prevEl = None
        if self.isDisplayBufferIn():
            if not self.isDisplayBufferFirst():
                for i, (key, value) in enumerate(self._displayBuffer.items()):
                    if key == self.displayFile:
                        break
                    prevKey = key
                    prevEl = value
        if prevKey:
            self.displayFile = prevKey
            self.displayPhoto = prevEl["displayPhoto"]
            self.displayMeta = prevEl["displayMeta"]
            self.displayHistogram = prevEl["displayHisto"]
            self.displayMetaFirst = prevEl["displayMetaFirst"]
            self.displayMetaLast = prevEl["displayMetaLast"]

    def _lineGen(self, s):
        """Generator to yield lines of a text
        """
        while len(s) > 0:
            p = s.find("\n")
            if p >= 0:
                if p == 0:
                    line = ""
                else:
                    line = s[:p]
                s = s[p+1:]
            else:
                line = s
                s = ""
            yield line

    def _checkMicrophoneNoJson(self):
        """Check connection of microphone for older PulseAudio versions where pactl has no -fjson option
        """
        logger.debug("ServerConfig._checkMicrophoneNoJson")
        hasMic = False
        defMic = ""
        isMute = False
        try:
            result = subprocess.run(["pactl", "list", "sources"], capture_output=True, text=True, check=True).stdout
            logger.debug("ServerConfig._checkMicrophoneNoJson - got result from 'pactl list sources: \n%s'", result)
            
            sourceId = ""
            desc = ""
            getPorts = False
            for line in self._lineGen(result):
                if line.startswith("Source"):
                    # Start of a new source
                    if sourceId == "":
                        # First source
                        sourceId = line[8:]
                        desc = ""
                        getPorts = False
                    else:
                        # Terminate last source (actually nothing specific)
                        sourceId = line[8:]
                        desc = ""
                        getPorts = False
                else:
                    if line.startswith("\t"):
                        line = line[1:]
                        if line.startswith("Description:"):
                            desc = line[13:]
                        if getPorts:
                            if line.find("type: Mic") > 0:
                                # We stop if the first microphone has been found
                                # This version of pactl does not allow to get the default mic.
                                hasMic = True
                                defMic = desc
                                break
                            getPorts = False
                        else:
                            if line.startswith("Ports:"):
                                getPorts = True
        
        except CalledProcessError as e:
            # In case pactl cannot be run, ignore the exception
            # And assume that no microphone is connected
            pass
        except Exception as e:
            pass
        
        logger.debug("ServerConfig._checkMicrophoneNoJson - hasMic=%s, defMic=%s'", hasMic, defMic)
        return hasMic, defMic, isMute
            
    def checkMicrophone(self):
        """Check whether a microphone is connected.
           Update configuration with description of default configuration.
           
           This infomation is obtained by querying the PulseAudio server through pactl
        """
        logger.debug("ServerConfig._checkMicrophone")
        hasMic = False
        defMic = ""
        isMute = True
        try:
            result = subprocess.run(["pactl", "-fjson", "list", "sources"], capture_output=True, text=True, check=True).stdout
            logger.debug("ServerConfig._checkMicrophone - got result from 'pactl -fjson list sources'")

            sources=json.loads(result)

            if len(sources) > 0:
                definput  = subprocess.run(["pactl", "get-default-source"], capture_output=True, text=True, check=True).stdout
                if definput.endswith("\n"):
                    definput = definput[:len(definput) - 1]
                for source in sources:
                    if "name" in source:
                        srcName = source["name"]
                        if srcName == definput:
                            if "ports" in source:
                                ports = source["ports"]
                                for port in ports:
                                    if "type" in port:
                                        type = port["type"]
                                        if type.casefold() == "mic":
                                            hasMic = True
                                            break
                            if hasMic == True:
                                if "description" in source:
                                    defMic = source["description"]
                                if "mute" in source:
                                    isMute = source["mute"]
                                else:
                                    isMute = False
        except CalledProcessError as e:
            # In case pactl cannot be run successfully, assume an older PulseAudio version
            # and try without -fjson option
            hasMic, defMic, isMute = self._checkMicrophoneNoJson()
        except Exception as e:
            pass
        
        if hasMic == True:
            self.hasMicrophone = True
            if len(defMic) > 0:
                self.defaultMic = defMic
            else:
                self._defaultMic = "Unknown description"
            self.isMicMuted = isMute
        else:
            self.hasMicrophone = False
            self.defaultMic = "No Microphone found"
            self.recordAudio = False
            self.isMicMuted = False
        logger.debug("ServerConfig._checkMicrophone - hasMicrophone=%s, defaultMic=%s", self.hasMicrophone, self.defaultMic)

    @staticmethod
    def getPiModel() -> str:
        """ Get the Raspberry Pi model
        
        """
        logger.debug("CameraCfg.getPiModel")
        model = ""
        try:
            with open('/proc/device-tree/model') as f:
                model = f.read()
                if model.endswith("\x00"):
                    model = model[:len(model)-1]
            logger.debug("CameraCfg.getPiModel - model: %s", model)
        except Exception as e:
            pass
        return model

    @staticmethod
    def getBoardRevision():
        """ Get the revision of the Raspberry Pi board
        
        """
        logger.debug("CameraCfg.getBoardRevision")
        boardRev = "0000"
        try:
            with open('/proc/cpuinfo','r') as f:
                for line in f:
                    if line[0:8]=='Revision':
                        length=len(line)
                        boardRev = line[11:length-1]
        except Exception as e:
            logger.error("Error opening /proc/cpuinfo : %s", e)
            boardRev = "0000"
        
        logger.debug("CameraCfg.getBoardRevision - boardRev = %s", boardRev)
        return boardRev

    def getDebianVersion(self):
        """ Get the Debian Version of the installed OS
        
        """
        logger.debug("CameraCfg.getDebianVersion")
        debianVers = ""
        try:
            with open('/etc/debian_version','r') as f:
                for line in f:
                    debianVers += line
        except Exception as e:
            logger.error("Error opening /etc/debian_version : %s", e)
            debianVers = ""
        
        debianVers = self.getOsName() + " - Version " + debianVers
        logger.debug("CameraCfg.getDebianVersion - debianVers = %s", debianVers)
        return debianVers

    def getKernelVersion(self):
        """ Get the Kernel Version of the installed OS
        
        """
        logger.debug("CameraCfg.getKernelVersion")
        kernelVers = ""
        try:
            result = subprocess.run(["uname", "-r"], capture_output=True, text=True, check=True).stdout
            for line in self._lineGen(result):
                kernelVers += line.strip()
        except Exception as e:
            logger.error("Error opening /etc/debian_version : %s", e)
            kernelVers = ""
        
        logger.debug("CameraCfg.getKernelVersion - kernelVers = %s", kernelVers)
        return kernelVers

    def getOsName(self):
        """ Get the name of the installed OS
        
        """
        logger.debug("CameraCfg.getOsName")
        osName = ""

        logger.debug("CameraCfg.getOsName - trying lsb_release")
        try:
            result = subprocess.run(["lsb_release", "-a"], capture_output=True, text=True, check=True).stdout
            for line in self._lineGen(result):
                logger.debug("CameraCfg.getOsName - line:%s", line)
                if line[0:12] == "Description:":
                    osName = line[13:].strip()
                    break
        except Exception as e:
            osName = ""
            
        if osName == "":
            logger.debug("CameraCfg.getOsName - trying cat /etc/os-release")
            try:
                result = subprocess.run(["cat", "/etc/os-release"], capture_output=True, text=True, check=True).stdout
                for line in self._lineGen(result):
                    logger.debug("CameraCfg.getOsName - line:%s", line)
                    if line[0:12] == "PRETTY_NAME=":
                        osName = line[13:].strip()
                        osName = osName.strip('"')
                        break
            except Exception as e:
                osName = ""
        
        logger.debug("CameraCfg.getOsName - osName = %s", osName)
        return osName
            
    def checkJwtSettings(self) -> tuple:
        """ Get secret key for JSON Wob Tokens JWT

            The secret key is expected in the JWT secrets file
            If a secret key is found, JWT authentication for the API is enabled
        """
        logger.debug("ServerConfig.checkJwtSettings")
        self.jwtAuthenticationActive = False
        # Try to get secret key from the file
        err = None
        msg = ""
        jwtSecretKey = None
        if self.jwtKeyStore != "":
            logger.debug("ServerConfig.checkJwtSettings - jwtKeyStore = %s", self.jwtKeyStore)
            if not os.path.exists(self.jwtKeyStore):
                fp = Path(self.jwtKeyStore)
                dir = fp.parent.absolute()
                fn = fp.name
                if not os.path.exists(dir):
                    os.makedirs(dir, exist_ok=True)
                    logger.debug("ServerConfig.checkJwtSettings - dir created: %s", dir)
                self.jwtKeyStore = str(dir) + "/" + fn
                Path(self.jwtKeyStore).touch(exist_ok=True)
                logger.debug("ServerConfig.checkJwtSettings - file created: %s", self.jwtKeyStore)
            else:
                logger.debug("ServerConfig.checkJwtSettings - path exists: %s", self.jwtKeyStore)
                if os.path.isdir(self.jwtKeyStore):
                    err = "The 'Password File Path' must be a file and not a directory!"
            secrets = {}
            if err is None:
                if os.stat(self.jwtKeyStore).st_size > 0:
                    with open(self.jwtKeyStore, "r") as f:
                        try:
                            secrets = json.load(f)
                        except Exception as e:
                            err = "The file specified as 'JWT Secret Key File Path' has content which is not in JSON format"
            if err is None:
                jwtSecretKey = ""
                if "jwtSecrets" in secrets:
                    jwtSecrets = secrets["jwtSecrets"]
                    if "jwtSecretKey" in jwtSecrets:
                        jwtSecretKey = jwtSecrets["jwtSecretKey"]
                        logger.debug("ServerConfig.checkJwtSettings - JWT secret key read from file")
                        msg = "JWT secret key read from Secret Key Store"
                else:
                    jwtSecrets = {}
                if jwtSecretKey == "":
                    jwtSecretKey = token_urlsafe()
                    logger.debug("ServerConfig.checkJwtSettings - jwtSecretKey generated: %s", jwtSecretKey)
                    msg = "New JWT secret key generated"
                    secrets["jwtSecrets"] = jwtSecrets
                    jwtSecrets["jwtSecretKey"] = jwtSecretKey
                    with open(self.jwtKeyStore, "w") as f:
                        try:
                            json.dump(secrets,fp=f, indent=4)
                            logger.debug("ServerConfig.checkJwtSettings -  - saved secrets to file %s", self.jwtKeyStore)
                        except Exception as e:
                            logger.err("ServerConfig.checkJwtSettings -  - error while saving secrets to file %s: %s", self.jwtKeyStore, e)
                            err = "Error writing to " + self.jwtKeyStore + ": " + str(e)
        else:
            logger.debug("ServerConfig.checkJwtSettings - jwtKeyStore not set")
            msg = "API inactive - No JWT Secret Key Store specified"

        if jwtSecretKey is None:
            self.jwtAuthenticationActive = False
        else:
            self.jwtAuthenticationActive = True
        logger.debug("ServerConfig.checkJwtSettings - jwtAuthenticationActive = %s", self.jwtAuthenticationActive)
        return (jwtSecretKey, err, msg)

    @staticmethod
    def _lineGen(s):
        """Generator to yield lines of a text
        """
        while len(s) > 0:
            p = s.find("\n")
            if p >= 0:
                if p == 0:
                    line = ""
                else:
                    line = s[:p]
                s = s[p+1:]
            else:
                line = s
                s = ""
            yield line

    def _countThreads(self, process: str=None):
        """Count number of threads for a given process
        
        """
        cntAll = -1
        cntReq = 0
        prcPid = 0
        prcStime = ""
        prcNlwp = 0
        prcTime = ""
        thrTime = ""
        thrTimed = timedelta(0)
        
        try:
            result = subprocess.run(["ps", "-e", "-L", "-f"], capture_output=True, text=True, check=True).stdout
            for line in self._lineGen(result):
                cntAll += 1
                if cntAll > 0:
                    uid = line[sUID:eUID].strip()
                    pid = int(line[sPID:ePID].strip())
                    ppid = int(line[sPPID:ePPID].strip())
                    lwp = int(line[sLWP:eLWP].strip())
                    c = int(line[sC:eC].strip())
                    nlwp = int(line[sNLWP:eNLWP].strip())
                    stime = line[sSTIME:eSTIME].strip()
                    tty = line[sTTY:eTTY].strip()
                    time = line[sTIME:eTIME].strip()
                    cmd = line[sCMD:].strip()
                    if not process is None:
                        if cmd.find(process) >= 0:
                            if pid == lwp:
                                cntReq += 1
                                prcPid = pid
                                prcStime = stime
                                prcNlwp = nlwp
                                prcTime = time
                            else:
                                if pid == prcPid:
                                    cntReq += 1
                                    t = datetime.strptime(time, "%H:%M:%S")
                                    td = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                                    thrTimed += td
                            if cntReq >= prcNlwp:
                                break
                else:
                    p = 0
                    p = line.find("UID", p)
                    sUID = p
                    p = line.find("PID", p + 3)
                    ePID = p + 3
                    sPID = ePID - 6
                    eUID = sPID
                    p = line.find("PPID", p + 3)
                    ePPID = p + 4
                    sPPID = ePID
                    p = line.find("LWP", p + 4)
                    eLWP = p + 3
                    sLWP = ePPID
                    p = line.find("C", p + 3)
                    eC = p + 1
                    sC = eLWP
                    p = line.find("NLWP", p + 1)
                    eNLWP = p + 4
                    sNLWP = eC
                    p = line.find("STIME", p + 4)
                    eSTIME = p + 5
                    sSTIME = eNLWP
                    p = line.find("TTY", p + 5)
                    sTTY = p - 1
                    p = line.find("TIME", p + 3)
                    eTTY = p - 5
                    eTIME = p + 4
                    sTIME = eTTY
                    p = line.find("CMD", p + 4)
                    sCMD = p
                    
        except CalledProcessError as e:
            pass
        except Exception as e:
            pass
        
        if process is None:
            return (cntAll,)
        else:
            thrTime = str(thrTimed)
            return (prcPid, prcStime, prcNlwp, prcTime, thrTime)
    
    @classmethod                
    def initFromDict(cls, dict:dict):
        sc = ServerConfig()
        for key, value in dict.items():
            #logger.debug("serverConfig.initFromDict - processing key %s", key)
            if key == "_scalerCropLiveView":
                setattr(sc, key, tuple(value))
            elif key == "_scalerCropMin":
                setattr(sc, key, tuple(value))
            elif key == "_scalerCropMax":
                setattr(sc, key, tuple(value))
            elif key == "_scalerCropDef":
                setattr(sc, key, tuple(value))
            elif key == "_displayMeta":
                if value is None:
                    setattr(sc, key, value)
                else:
                    metat = {}
                    for ckey, cvalue in value.items():
                        vt = cvalue
                        if ckey == "ScalerCrop":
                            vt = tuple(cvalue)
                        elif ckey == "FrameDurationLimits":
                            vt = tuple(cvalue)
                        elif ckey == "ColourGains":
                            vt = tuple(cvalue)
                        elif ckey == "ColourCorrectionMatrix":
                            vt = tuple(cvalue)
                        elif ckey == "SensorBlackLevels":
                            vt = tuple(cvalue)
                        elif ckey == "AfWindows":
                            afws = ()
                            for el in cvalue:
                                afw = (tuple(el),)
                                afws += afw
                            vt = afws
                        else:
                            vt = cvalue
                        metat[ckey] = vt
                    setattr(sc, key, metat)
            elif key == "_displayBuffer":
                if value is None:
                    setattr(sc, key, value)
                else:
                    dbt = {}
                    for bkey, bvalue in value.items():
                        belt = {}
                        for belmetakey, belmetavalue in bvalue.items():
                            if belmetakey == "displayMeta":
                                metat = {}
                                for ckey, cvalue in belmetavalue.items():
                                    vt = cvalue
                                    if ckey == "ScalerCrop":
                                        vt = tuple(cvalue)
                                    elif ckey == "FrameDurationLimits":
                                        vt = tuple(cvalue)
                                    elif ckey == "ColourGains":
                                        vt = tuple(cvalue)
                                    elif ckey == "ColourCorrectionMatrix":
                                        vt = tuple(cvalue)
                                    elif ckey == "SensorBlackLevels":
                                        vt = tuple(cvalue)
                                    elif ckey == "AfWindows":
                                        afws = ()
                                        for el in cvalue:
                                            afw = (tuple(el),)
                                            afws += afw
                                        vt = afws
                                    else:
                                        vt = cvalue
                                    metat[ckey] = vt
                                belt[belmetakey] = metat
                            else:
                                belt[belmetakey] = belmetavalue
                        dbt[bkey] = belt
                    setattr(sc, key, dbt)
            elif key == "_pvList":
                # Photo viewer list shall not be imported
                # It will be filled on demand
                setattr(sc, key, [])
            elif key == "_streamingClients":
                # Streaming clients shall not be imported
                # They will be populated during server runtime when clients start/stop streaming
                setattr(sc, key, [])
            elif key == "_pvCamera":
                setattr(sc, key, None)
            elif key == "_pvFrom":
                setattr(sc, key, None)
            elif key == "_pvTo":
                setattr(sc, key, None)
            elif key == "_vButtons":
                if value is None:
                    setattr(sc, key, value)
                else:
                    vButtons = []
                    for row in value:
                        vButtonRow = []
                        for btn in row:
                            button = vButton.initFromDict(btn)
                            vButtonRow.append(button)
                        vButtons.append(vButtonRow)
                    setattr(sc, key, vButtons)
            #Initialize last vButton execution result
            elif key == "_vButtonCommand":
                setattr(sc, key, None)
            elif key == "_vButtonArgs":
                setattr(sc, key, None)
            elif key == "_vButtonReturncode":
                setattr(sc, key, None)
            elif key == "_vButtonStdout":
                setattr(sc, key, None)
            elif key == "_vButtonStderr":
                setattr(sc, key, None)
            elif key == "_aButtons":
                if value is None:
                    setattr(sc, key, value)
                else:
                    aButtons = []
                    for row in value:
                        aButtonRow = []
                        for btn in row:
                            button = ActionButton.initFromDict(btn)
                            aButtonRow.append(button)
                        aButtons.append(aButtonRow)
                    setattr(sc, key, aButtons)
            elif key == "_gpioDevices":
                if value is None:
                    setattr(sc, key, value)
                else:
                    gpioDevices = []
                    for device in value:
                        gpioDevice = GPIODevice.initFromDict(device)
                        gpioDevices.append(gpioDevice)
                    setattr(sc, key, gpioDevices)
            elif key == "_curDevice":
                if value is None:
                    setattr(sc, key, value)
                else:
                    curDevice = GPIODevice.initFromDict(value)
                    setattr(sc, key, curDevice)
            elif key == "_curDeviceType":
                # Take the current device type from a fresh declaration rather than from stored data
                # This will allow later modifications of gpioDeviceTypes being immediately effective
                if value is None:
                    setattr(sc, key, value)
                else:
                    type = value["type"]
                    for typ in gpioDeviceTypes:
                        if typ["type"] == type:
                            setattr(sc, key, typ)
                            break
            elif key == "_unsavedChanges":
                setattr(sc, key, False)
            elif key == "_serverStartTime":
                # Do not overwrite the server start time
                # It has been set when the ServerConfig singleton has been instantiated
                pass
            else:
                setattr(sc, key, value)
        # Reset process status variables
        sc.isLiveStream = False
        sc.isAudioRecording = False
        sc.isPhotoSeriesRecording = False
        sc.isTriggerRecording = False
        sc.isVideoRecording = False

        #Set the sc.curDevice attribute to the corresponding object from sc.gpioDevices
        # After import fom the JSON file sc.curDevice is an own object and not the one
        # from the sc.gpioDevices list.
        for device in sc.gpioDevices:
            if device.id == sc.curDeviceId:
                sc.curDevice = device
                break
        
        return sc
    
class Secrets():
    """ Class for secrets which are never persisted
    """
    def __init__(self) -> None:
        self._notifyUser = ""
        self._notifyPwd = ""
        self._jwtSecretKey = ""

    @property
    def notifyUser(self) -> str:
        return self._notifyUser

    @notifyUser.setter
    def notifyUser(self, value: str):
        self._notifyUser = value

    @property
    def notifyPwd(self) -> str:
        return self._notifyPwd

    @notifyPwd.setter
    def notifyPwd(self, value: str):
        self._notifyPwd = value

    @property
    def jwtSecretKey(self) -> str:
        return self._jwtSecretKey

    @jwtSecretKey.setter
    def jwtSecretKey(self, value: str):
        self._jwtSecretKey = value
    
class CameraCfg():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraCfg, cls).__new__(cls)
            cls._cameras = []
            cls._sensorModes = []
            cls._rawFormats = []
            cls._tuningConfig = TuningConfig()
            cls._controls = CameraControls()
            cls._controlsBackup: CameraControls = None
            cls._cameraProperties = CameraProperties()
            cls._liveViewConfig = CameraConfig()
            cls._liveViewConfig.id = "LIVE"
            cls._liveViewConfig.use_case = "Live view"
            cls._liveViewConfig.stream = "lores"
            cls._liveViewConfig.buffer_count = 6
            cls._liveViewConfig.encode = "main"
            cls._liveViewConfig.controls["FrameDurationLimits"] = (33333, 33333)
            cls._photoConfig = CameraConfig()
            cls._photoConfig.id = "FOTO"
            cls._photoConfig.use_case = "Photo"
            cls._photoConfig.buffer_count = 1
            cls._photoConfig.controls["FrameDurationLimits"] = (100, 1000000000)
            cls._rawConfig = CameraConfig()
            cls._rawConfig.id = "PRAW"
            cls._rawConfig.use_case = "Raw Photo"
            cls._rawConfig.buffer_count = 1
            cls._rawConfig.stream = "raw"
            cls._rawConfig.controls["FrameDurationLimits"] = (100, 1000000000)
            cls._videoConfig = CameraConfig()
            cls._videoConfig.buffer_count = 6
            cls._videoConfig.id = "VIDO"
            cls._videoConfig.use_case = "Video"
            cls._videoConfig.buffer_count = 6
            cls._videoConfig.encode = "main"
            cls._videoConfig.controls["FrameDurationLimits"] = (33333, 33333)
            cls._cameraConfigs = []
            cls._triggerConfig = TriggerConfig()
            cls._serverConfig = ServerConfig()
            # For Raspi models < 5 the lowres format must be YUV
            # See Picamera2 manual ch. 4.2, p. 16
            if cls._serverConfig.raspiModelLower5:
                cls._liveViewConfig.format = "YUV420"
            if cls._serverConfig.raspiModelFull.startswith("Raspberry Pi Zero") \
            or cls._serverConfig.raspiModelFull.startswith("Raspberry Pi 4") \
            or cls._serverConfig.raspiModelFull.startswith("Raspberry Pi 3") \
            or cls._serverConfig.raspiModelFull.startswith("Raspberry Pi 2") \
            or cls._serverConfig.raspiModelFull.startswith("Raspberry Pi 1"):
                # For Pi Zero and 4 reduce buffer_count defaults for live view and video
                cls._liveViewConfig.buffer_count = 2
                cls._videoConfig.buffer_count = 2
            cls._streamingCfg = {}
            cls._secrets = Secrets()
        return cls._instance
    
    @property
    def cameras(self) -> list:
        return self._cameras

    @cameras.setter
    def cameras(self, value: list):
        self._cameras = value
    
    @property
    def controls(self) -> CameraControls:
        return self._controls

    @controls.setter
    def controls(self, value: CameraControls):
        self._controls = value
    
    @property
    def tuningConfig(self) -> TuningConfig:
        return self._tuningConfig

    @tuningConfig.setter
    def tuningConfig(self, value: TuningConfig):
        self._tuningConfig = value
    
    @property
    def controlsBackup(self) -> CameraControls:
        return self._controlsBackup

    @controlsBackup.setter
    def controlsBackup(self, value: CameraControls):
        self._controlsBackup = value
    
    @property
    def cameraProperties(self) -> CameraProperties:
        return self._cameraProperties

    @cameraProperties.setter
    def cameraProperties(self, value: CameraProperties):
        self._cameraProperties = value

    @property
    def sensorModes(self) -> list:
        return self._sensorModes

    @sensorModes.setter
    def sensorModes(self, value: list):
        self._sensorModes = value
    
    @property
    def rawFormats(self) -> list:
        return self._rawFormats

    @rawFormats.setter
    def rawFormats(self, value: list):
        self._rawFormats = value

    @property
    def nrSensorModes(self) -> int:
        return len(self._sensorModes)
    
    @property
    def liveViewConfig(self) -> CameraConfig:
        return self._liveViewConfig

    @liveViewConfig.setter
    def liveViewConfig(self, value: CameraConfig):
        self._liveViewConfig = value
    
    @property
    def photoConfig(self) -> CameraConfig:
        return self._photoConfig

    @photoConfig.setter
    def photoConfig(self, value: CameraConfig):
        self._photoConfig = value
    
    @property
    def rawConfig(self) -> CameraConfig:
        return self._rawConfig

    @rawConfig.setter
    def rawConfig(self, value: CameraConfig):
        self._rawConfig = value
    
    @property
    def videoConfig(self) -> CameraConfig:
        return self._videoConfig

    @videoConfig.setter
    def videoConfig(self, value: CameraConfig):
        self._videoConfig = value
    
    @property
    def cameraConfigs(self) -> list:
        return self._cameraConfigs

    @cameraConfigs.setter
    def cameraConfigs(self, value: list):
        self._cameraConfigs = value
    
    @property
    def triggerConfig(self) -> TriggerConfig:
        return self._triggerConfig

    @triggerConfig.setter
    def triggerConfig(self, value: TriggerConfig):
        self._triggerConfig = value
    
    @property
    def serverConfig(self) -> ServerConfig:
        return self._serverConfig

    @serverConfig.setter
    def serverConfig(self, value: ServerConfig):
        self._serverConfig = value
    
    @property
    def streamingCfg(self) -> dict:
        return self._streamingCfg

    @streamingCfg.setter
    def streamingCfg(self, value: dict):
        self._streamingCfg = value
    
    @property
    def secrets(self) -> Secrets:
        return self._secrets

    @secrets.setter
    def secrets(self, value: Secrets):
        self._secrets = value
    
    def _persistCl(self, cl, fn: str, cfgPath: str):
        """ Store class dictionary for class cl in the config file fn
        """
        fp = cfgPath + "/" + fn
        Path(fp).touch()
        f = open(fp, "w")
        cj = self._toJson(cl)
        f.write(str(cj))
        f.close()
    
    def persist(self, cfgPath: str):
        """ Store class dictionary in the config file
        """
        if cfgPath:
            if not os.path.exists(cfgPath):
                os.makedirs(cfgPath, exist_ok=True)
            self._persistCl(self.cameras, "cameras.json", cfgPath)
            self._persistCl(self.tuningConfig, "tuningConfig.json", cfgPath)
            self._persistCl(self.sensorModes, "sensorModes.json", cfgPath)
            self._persistCl(self.rawFormats, "rawFormats.json", cfgPath)
            self._persistCl(self.cameraProperties, "cameraProperties.json", cfgPath)
            self._persistCl(self.cameraConfigs, "cameraConfigs.json", cfgPath)
            self._persistCl(self.liveViewConfig, "liveViewConfig.json", cfgPath)
            self._persistCl(self.photoConfig, "photoConfig.json", cfgPath)
            self._persistCl(self.rawConfig, "rawConfig.json", cfgPath)
            self._persistCl(self.videoConfig, "videoConfig.json", cfgPath)
            self._persistCl(self.controls, "controls.json", cfgPath)
            self._persistCl(self.serverConfig, "serverConfig.json", cfgPath)
            self._persistCl(self.triggerConfig, "triggerConfig.json", cfgPath)
            self._persistCl(self.streamingCfg, "streamingCfg.json", cfgPath)
            
    def _toJson(self, cl):
        return json.dumps(cl, default=lambda o: getattr(o, '__dict__', str(o)), indent=4)
        
    def _loadConfigCl(self, cl, fn: str, cfgPath: str):
        """ Load configuration from files, except camera-specific configs
        """
        fp = cfgPath + "/" + fn
        obj = cl()
        if os.path.exists(fp):
            with open(fp) as f:
                try:
                    cldict = json.load(f)
                    obj = cl.initFromDict(cldict)
                except Exception as e:
                    logger.error("Error loading from %s: %s", fp, e)
                    obj = cl()
        return obj
    
    def _initStreamingConfigFromDisc(self, fn: str, cfgPath: str) -> dict:
        """ Load streaming configuration
        """
        sc = {}
        scdict = {}
        fp = cfgPath + "/" + fn
        if os.path.exists(fp):
            with open(fp) as f:
                try:
                    scdict = json.load(f)
                except Exception as e:
                    logger.error("Error loading StreamingConfig from %s: %s", fp, e)
                    scdict = {}
        if len(scdict) > 0:
            for camKey, camValue in scdict.items():
                scfg = {}
                for key, value in camValue.items():
                    if key == "liveconfig":
                        scfg["liveconfig"] = CameraConfig.initFromDict(value)
                    elif key == "videoconfig":
                        scfg["videoconfig"] = CameraConfig.initFromDict(value)
                    elif key == "controls":
                        scfg["controls"] = CameraControls.initFromDict(value)
                    elif key == "tuningconfig":
                        scfg["tuningconfig"] = TuningConfig.initFromDict(value)
                    else:
                        scfg[key] = value
                sc[camKey] = scfg
        return sc
    
    def _initGpioDevicesFromDisc(self, fn: str, cfgPath: str) -> list:
        """ Load GPIO devices
        """
        devs = []
        fdevs = {}
        fp = cfgPath + "/" + fn
        if os.path.exists(fp):
            with open(fp) as f:
                try:
                    fdevs = json.load(f)
                except Exception as e:
                    logger.error("Error loading GPIO devices from %s: %s", fp, e)
                    fdevs = []
        if len(fdevs) > 0:
            for dev in fdevs.items():
                devo = GPIODevice.initFromDict(dev)
                devs.append(devo)
        return devs
    
    def loadConfig(self, cfgPath):
        """ Load configuration from files, except camera-specific configs
        """
        if cfgPath:
            if os.path.exists(cfgPath):
                self.tuningConfig = self._loadConfigCl(TuningConfig, "tuningConfig.json", cfgPath)
                self.serverConfig = self._loadConfigCl(ServerConfig, "serverConfig.json", cfgPath)
                self.liveViewConfig = self._loadConfigCl(CameraConfig, "liveViewConfig.json", cfgPath)
                self.photoConfig = self._loadConfigCl(CameraConfig, "photoConfig.json", cfgPath)
                self.rawConfig = self._loadConfigCl(CameraConfig, "rawConfig.json", cfgPath)
                self.videoConfig = self._loadConfigCl(CameraConfig, "videoConfig.json", cfgPath)
                self.controls = self._loadConfigCl(CameraControls, "controls.json", cfgPath)
                self.triggerConfig = self._loadConfigCl(TriggerConfig, "triggerConfig.json", cfgPath)
                self.streamingCfg = self._initStreamingConfigFromDisc("streamingCfg.json", cfgPath)
                self.gpioDevices = self._initGpioDevicesFromDisc("gpioDevices.json", cfgPath)
                sc = self.secrets
                tc = self.triggerConfig
                (usr, pwd, err) = tc.checkNotificationRecipient()
                if tc.notifyConOK == True:
                    sc.notifyUser = usr
                    sc.notifyPwd = pwd
                srv = self.serverConfig
                if srv.useAPI == True:
                    (secretKey, err, msg) = srv.checkJwtSettings()
                    if err is None:
                        sc.jwtSecretKey = secretKey
