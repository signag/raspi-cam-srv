from datetime import datetime
from datetime import timedelta
from raspiCamSrv.camCfg import CameraCfg, CameraConfig, CameraControls
import raspiCamSrv.camera_pi
import os
import csv
import copy
import shutil
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class Series():
    PHOTODIGITS = 6     # Number of digits for photo number in filename
    HISTOGRAMFOLDER = "hist"
    def __init__(self):
        self._name = ""
        self._status = "NE"
        self._path = ""
        self._start = None
        self._started = None
        self._end = None
        self._ended = None
        self._interval = None
        self._nrShots = None
        self._curShots = None
        self._type = "jpg"
        self._continueOnServerStart = False
        self._showPreview = True
        self._logFile = None
        self._cfgFile = None
        self._camFile = None
        self._cameraConfig = None
        self._cameraControls = None
        self._logHeadlineReq = True
        self._firstCamEntry = True
        self._isExposureSeries = False
        self._isExpExpTimeFix = False
        self._isExpGainFix = True
        self._expTimeStart = 125
        self._expTimeStop = 1024000
        self._expTimeStep = 0
        self._expGainStart = 1
        self._expGainStop = 16
        self._expGainStep = 0
        self._isFocusStackingSeries = False
        self._focalDistStart = 0
        self._focalDistStop = 0
        self._focalDistStep = 0
        self._error = None
        self._error2 = None
        self._errorSource = None
    
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value
    
    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        self._status = value
    
    @property
    def nextActions(self) -> list:
        """Return the allowed lifecycle actions depending on current status
        """
        if self._status == "NE":
            return ["create",]
        elif self._status == "NEW":
            return ["configure", "remove"]
        elif self._status == "READY":
            return ["start", "remove"]
        elif self._status == "ACTIVE":
            return ["pause", "finish"]
        elif self.status == "PAUSED":
            return ["continue", "finish"]
        elif self.status == "FINISHED":
            return ["remove",]
        else:
            return []
    
    def nextStatus(self, action: str) -> str:
        """Update and return the lifecycle status depending on action
        """
        if action == "create":
            self._status = "NEW"
        elif action == "configure":
            self._status = "READY"
        elif action == "start":
            self._status = "ACTIVE"
        elif action == "pause":
            self._status = "PAUSED"
        elif action == "finish":
            self._status = "FINISHED"
            self.logCamCfgCtrlClose()
        elif action == "continue":
            self._status = "ACTIVE"
        else:
            self._status = "NONE"
        return self._status
    
    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str):
        self._path = value
    
    @property
    def histogramPath(self) -> str:
        return self._path + "/" + Series.HISTOGRAMFOLDER
    
    @property
    def start(self) -> datetime:
        return self._start

    @start.setter
    def start(self, value: datetime):
        if value is None:
            self._start = None
        else:
            dt = datetime(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute)
            self._start = dt
    
    @property
    def startIso(self) -> str:
        return self._start.isoformat()
    
    @property
    def started(self) -> datetime:
        return self._started

    @started.setter
    def started(self, value: datetime):
        if value is None:
            self._started = None
        else:
            dt = datetime(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute)
            self._started = dt
    
    @property
    def startedIso(self) -> str:
        if self._started is None:
            return None
        else:
            return self._started.isoformat()
    
    @property
    def end(self) -> datetime:
        return self._end

    @end.setter
    def end(self, value: datetime):
        if value is None:
            self._end = None
        else:
            dt = datetime(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute)
            self._end = dt
    
    @property
    def endIso(self) -> str:
        return self._end.isoformat()
    
    @property
    def ended(self) -> datetime:
        return self._ended

    @ended.setter
    def ended(self, value: datetime):
        if value is None:
            self._ended = None
        else:
            dt = datetime(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute)
            self._ended = dt
    
    @property
    def endedIso(self) -> str:
        if self.ended is None:
            return None
        else:
            return self._ended.isoformat()
    
    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float):
        self._interval = value
    
    @property
    def nrShots(self) -> int:
        return self._nrShots

    @nrShots.setter
    def nrShots(self, value: int):
        self._nrShots = value
    
    @property
    def curShots(self) -> int:
        return self._curShots

    @curShots.setter
    def curShots(self, value: int):
        self._curShots = value
    
    @property
    def type(self) -> str:
        return self._type

    @type.setter
    def type(self, value: str):
        self._type = value
    
    @property
    def continueOnServerStart(self) -> bool:
        return self._continueOnServerStart

    @continueOnServerStart.setter
    def continueOnServerStart(self, value: bool):
        self._continueOnServerStart = value
    
    @property
    def showPreview(self) -> bool:
        return self._showPreview

    @showPreview.setter
    def showPreview(self, value: bool):
        self._showPreview = value
    
    @property
    def logFileName(self) -> str:
        return self.name + "_log.csv"
    
    @property
    def logFileRelPath(self) -> str:
        return "photoseries/" + self.name + "/" + self.logFileName
    
    @property
    def logFile(self) -> str:
        return self._logFile

    @logFile.setter
    def logFile(self, value: str):
        self._logFile = value
    
    @property
    def cfgFileName(self) -> str:
        return self.name + "_cfg.json"
    
    @property
    def cfgFileRelPath(self) -> str:
        return  "photoseries/" + self.name + "/" + self.cfgFileName
    
    @property
    def cfgFile(self) -> str:
        return self._cfgFile

    @cfgFile.setter
    def cfgFile(self, value: str):
        self._cfgFile = value
    
    @property
    def camFileName(self) -> str:
        return self.name + "_cam.json"
    
    @property
    def camFileRelPath(self) -> str:
        return  "photoseries/" + self.name + "/" + self.camFileName
    
    @property
    def camFile(self) -> str:
        return self._camFile

    @camFile.setter
    def camFile(self, value: str):
        self._camFile = value
    
    @property
    def isExposureSeries(self) -> bool:
        return self._isExposureSeries

    @isExposureSeries.setter
    def isExposureSeries(self, value: bool):
        self._isExposureSeries = value
    
    @property
    def isExpExpTimeFix(self) -> bool:
        return self._isExpExpTimeFix

    @isExpExpTimeFix.setter
    def isExpExpTimeFix(self, value: bool):
        self._isExpExpTimeFix = value
    
    @property
    def isExpGainFix(self) -> bool:
        return self._isExpGainFix

    @isExpGainFix.setter
    def isExpGainFix(self, value: bool):
        self._isExpGainFix = value
    
    @property
    def expTimeStart(self) -> int:
        return self._expTimeStart

    @expTimeStart.setter
    def expTimeStart(self, value: int):
        self._expTimeStart = value
    
    @property
    def expTimeStop(self) -> int:
        return self._expTimeStop

    @expTimeStop.setter
    def expTimeStop(self, value: int):
        self._expTimeStop = value
    
    @property
    def expTimeStep(self) -> int:
        return self._expTimeStep

    @expTimeStep.setter
    def expTimeStep(self, value: int):
        """ Step for exposure time:
            0: 1 EV
            1: 1/3 EV
            2: 2 EV
        """
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._expTimeStep = value
        else:
            self._expTimeStep = 0

    @property
    def expGainStart(self) -> float:
        return self._expGainStart

    @expGainStart.setter
    def expGainStart(self, value: float):
        self._expGainStart = value
    
    @property
    def expGainStop(self) -> float:
        return self._expGainStop

    @expGainStop.setter
    def expGainStop(self, value: float):
        self._expGainStop = value
    
    @property
    def expGainStep(self) -> int:
        return self._expGainStep

    @expGainStep.setter
    def expGainStep(self, value: int):
        """ Step for analogue gain:
            0: 1 EV
            1: 1/3 EV
            2: 2 EV
        """
        if value == 0 \
        or value == 1 \
        or value == 2:
            self._expGainStep = value
        else:
            self._expGainStep = 0
    
    @property
    def isFocusStackingSeries(self) -> bool:
        return self._isFocusStackingSeries

    @isFocusStackingSeries.setter
    def isFocusStackingSeries(self, value: bool):
        self._isFocusStackingSeries = value
    
    @property
    def focalDistStart(self) -> float:
        return self._focalDistStart

    @focalDistStart.setter
    def focalDistStart(self, value: float):
        self._focalDistStart = value
    
    @property
    def focalDistStop(self) -> float:
        return self._focalDistStop

    @focalDistStop.setter
    def focalDistStop(self, value: float):
        self._focalDistStop = value
    
    @property
    def focalDistStep(self) -> float:
        return self._focalDistStep

    @focalDistStep.setter
    def focalDistStep(self, value: float):
        self._focalDistStep = value

    @property
    def cameraConfig(self) -> CameraConfig:
        return self._cameraConfig

    @cameraConfig.setter
    def cameraConfig(self, value: CameraConfig):
        self._cameraConfig = value
    
    @property
    def cameraControls(self) -> CameraControls:
        return self._cameraControls

    @cameraControls.setter
    def cameraControls(self, value: CameraControls):
        self._cameraControls = value

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
    def nextPhoto(self) -> str:
        logger.debug("Series.nextPhoto")
        name = ""
        if self.curShots is None:
            self.curShots = 0
        if self.curShots < self.nrShots:
            self.curShots += 1
            name = self.name + "_" + str(self.curShots).zfill(Series.PHOTODIGITS)
        else:
            if self.ended is None:
                logger.debug("Series.nextPhoto - Finishing series")
                dt = datetime.now()
                dt = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
                self.ended = dt
                self.nextStatus("finish")
                self.persist()
                #Restore camera controls
                if CameraCfg().controlsBackup:
                    CameraCfg().controls = copy.deepcopy(CameraCfg().controlsBackup)
                    CameraCfg().controlsBackup = None
                    logger.debug("Series.nextPhoto - Restored controls backup: %s", CameraCfg().controls.__dict__)
                    wait = None
                    if self.isExposureSeries:
                        #For an exposure series wait for the longest exposure time
                        if self.isExpGainFix:
                            wait = 0.2 + self.expTimeStop / 1000000
                    raspiCamSrv.camera_pi.Camera().applyControlsForLivestream(wait)
        logger.debug("Series.nextPhoto - returning: %s", name)
        return name
    
    def nextTimeOnlyAsStr(self) -> str: 
        """ Returns just the time for the next shot
        """
        t = str(self.nextTime())
        return t[11:]
    
    def nextTimeIso(self) -> str: 
        """ Returns the time for the next shot in ISO format
        """
        t = self.nextTime()
        return t.isoformat()
    
    def nextTime(self, lastTime=None) -> datetime:
        """ Calculate and return the time when the next photo must be taken
            lastTime: time when the last photo has been taken
        """
        logger.debug("Series.nextTime - lastTime: %s", lastTime)
        next = None
        curTime = datetime.now()
        if curTime <= self.end:
            if curTime < self.start:
                next = self.start
            else:
                timedif = curTime - self.start
                timedifSec = timedif.total_seconds()
                nrint = int(timedifSec / self._interval)
                next = self.start + timedelta(seconds = (nrint + 1)*self.interval)
        else:
            if self.ended is None:
                logger.debug("Series.nextTime - Finishing series")
                dt = datetime.now()
                dt = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
                self.ended = dt
                self.nextStatus("finish")
                self.persist()
                #Restore camera controls
                if CameraCfg().controlsBackup:
                    CameraCfg().controls = copy.deepcopy(CameraCfg().controlsBackup)
                    CameraCfg().controlsBackup = None
                    logger.debug("Series.nextTime - Restored controls backup: %s", CameraCfg().controls.__dict__)
                    wait = None
                    if self.isExposureSeries:
                        #For an exposure series wait for the longest exposure time
                        if self.isExpGainFix:
                            wait = 0.2 + self.expTimeStop / 1000000
                    raspiCamSrv.camera_pi.Camera().applyControlsForLivestream(wait)
        if not next:
            next = datetime.now()
        logger.debug("Series.nextTime - returning: %s", next.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
        return next
    
    def getPreviewList(self):
        """ return a list with the last n photos of the series
        """
        list = []
        if self.curShots:
            n = self.curShots + 1
            cnt = 0
            
            while (cnt < 20 and n >= 0):
                name = self.name + "_" + str(n).zfill(Series.PHOTODIGITS) + ".jpg"
                path = self.path + "/" + name
                if os.path.exists(path):
                    relPath = "photoseries/" + self.name + "/" + name
                    set = {}
                    set["name"] = name
                    set["relPath"] = relPath
                    list.append(set)
                    cnt += 1
                n = n - 1
        return list

    def _readLog(self, file: str) -> dict:
        """ Read the log file and return as dict
        """
        ret = {}
        with open(file, newline="") as csvFile:
            reader = csv.DictReader(csvFile, delimiter = ";", quotechar = "'")
            for row in reader:
                ret[row["Name"]] = row
        return ret

    def _getParamsFromLog(self, log: dict, name: str) -> dict:
        """ Get parameters for a specific name with float limited to n digits
        """
        ret = {}
        if name in log:
            ret = log[name]
        # Limit number of digits
        if "AnalogueGain" in ret:
            ret["AnalogueGain"] = round(float(ret["AnalogueGain"]),4)
        if "DigitalGain" in ret:
            ret["DigitalGain"] = round(float(ret["DigitalGain"]),4)
        if "Lux" in ret:
            ret["Lux"] = round(float(ret["Lux"]),4)
        if "LensPosition" in ret:
            lp = ret["LensPosition"]
            if len(lp) > 0:
                if float(ret["LensPosition"]) > 0:
                    ret["FocalDistance"] = round(1.0/float(ret["LensPosition"]), 4)
                else:
                    ret["FocalDistance"] = 999.999
                ret["LensPosition"] = round(float(ret["LensPosition"]),4)
            else:
                ret["FocalDistance"] = "0"
                ret["LensPosition"] = "0"
                
        if "ExposureTime" in ret:
            ret["ExposureTime"] = round(float(ret["ExposureTime"]) / 1000000,4)
        return ret
    
    def getPreviewListHistDetail(self):
        """ return a list with the last n photos of the series
            including histogram and details
        """
        log = self._readLog(self.logFile)
        list = []
        if self.curShots:
            n = self.curShots + 1
            cnt = 0
            
            while (cnt < 20 and n >= 0):
                pureName = self.name + "_" + str(n).zfill(Series.PHOTODIGITS)
                name = pureName + ".jpg"
                nameRaw = pureName + ".dng"
                photoPath = self.path + "/" + name
                histoPath = self.histogramPath + "/" + name
                include = False
                if os.path.exists(photoPath):
                    relPhotoPath = "photoseries/" + self.name + "/" + name
                    include = True
                else:
                    relPhotoPath = None
                if os.path.exists(histoPath):
                    relHisroPath = "photoseries/" + self.name + "/" + Series.HISTOGRAMFOLDER + "/" + name
                    include = True
                else:
                    relHisroPath = None
                if include:
                    set = {}
                    if self.type == "raw+jpg":
                        set["name"] = nameRaw
                    else:
                        set["name"] = name
                    set["relPhotoPath"] = relPhotoPath
                    set["relHistoPath"] = relHisroPath
                    set["params"] = self._getParamsFromLog(log, pureName)
                    list.append(set)
                    cnt += 1
                n = n - 1
        return list

    def logCamCfgCtrlClose(self):
        """Append camera _cam.json file with closing ]
        """
        if self.camFile:
            with open(self.camFile, mode='a', encoding='utf-8') as f:
                f.write("\n]")

    def logCamCfgCtrl(self, name: str, cfg: dict, ctrl: dict):
        """Append camera config & controls  used for a photo to the _cam.json file
           name: Name of the photo
           cfg : camera configuration
           ctrl: camera controls
        """
        if self.camFile:
            if not os.path.exists(self.camFile):
                os.makedirs(self.path, exist_ok=True)
                Path(self.camFile).touch()
            new = {}
            new["name"] = name
            new["config"] = cfg
            new["controls"] = ctrl
            logger.debug("logCamCfgCtrl new: %s", new)
            newJson = json.dumps(new, default=lambda o: getattr(o, '__dict__', str(o)), indent=4)
            if self._firstCamEntry:
                newJson = "[\n" + newJson
                self._firstCamEntry = False
            else:
                newJson = ",\n" + newJson
            with open(self.camFile, mode='a', encoding='utf-8') as f:
                f.write(newJson)
    
    def logPhoto(self, name: str, ptime: datetime, metadata: dict):
        """Append a log entry for the photo
        """
        if self.started is None:
            self.started = ptime
            
        if self._logHeadlineReq:
            log = "Name" + ";"
            log = log + "Time" + ";"
            log = log + "SensorTimestamp" + ";"
            log = log + "ExposureTime" + ";"
            log = log + "AnalogueGain" + ";"
            log = log + "DigitalGain" + ";"
            log = log + "Lux" + ";"
            log = log + "LensPosition" + ";"
            log = log + "FocusFoM" + ";"
            log = log + "FrameDuration" + ";"
            log = log + "SensorTemperature" + ";"
            log = log + "ColourTemperature" + ";"
            log = log + "AeLocked" + ";"
            f = open(self.logFile, "a")
            f.write(log + "\n")
            f.close()
            self._logHeadlineReq = False
        
        log = name + ";"
        log = log + ptime.isoformat() + ";"
        if "SensorTimestamp" in metadata:
            log = log + str(metadata["SensorTimestamp"]) + ";"
        else:
            log = log + ";"
        if "ExposureTime" in metadata:
            log = log + str(metadata["ExposureTime"]) + ";"
        else:
            log = log + ";"
        if "AnalogueGain" in metadata:
            log = log + str(metadata["AnalogueGain"]) + ";"
        else:
            log = log + ";"
        if "DigitalGain" in metadata:
            log = log + str(metadata["DigitalGain"]) + ";"
        else:
            log = log + ";"
        if "Lux" in metadata:
            log = log + str(metadata["Lux"]) + ";"
        else:
            log = log + ";"
        if "LensPosition" in metadata:
            log = log + str(metadata["LensPosition"]) + ";"
        else:
            log = log + ";"
        if "FocusFoM" in metadata:
            log = log + str(metadata["FocusFoM"]) + ";"
        else:
            log = log + ";"
        if "FrameDuration" in metadata:
            log = log + str(metadata["FrameDuration"]) + ";"
        else:
            log = log + ";"
        if "SensorTemperature" in metadata:
            log = log + str(metadata["SensorTemperature"]) + ";"
        else:
            log = log + ";"
        if "ColourTemperature" in metadata:
            log = log + str(metadata["ColourTemperature"]) + ";"
        else:
            log = log + ";"
        if "AeLocked" in metadata:
            log = log + str(metadata["AeLocked"]) + ";"
        else:
            log = log + ";"
        f = open(self.logFile, "a")
        f.write(log + "\n")
        f.close()
    
    def persist(self):
        """ Store class dictionary in the config file
        """
        if self.cfgFile:
            if not os.path.exists(self.cfgFile):
                os.makedirs(self.path, exist_ok=True)
                Path(self.cfgFile).touch()
            f = open(self.cfgFile, "w")
            #cj = json.loads(json.dumps(self.toJson(), indent=4))
            cj = self.toJson()
            f.write(str(cj))
            f.close()
            
    def toJson(self):
        #return json.dumps(self, default=lambda o: o.__dict__)
        return json.dumps(self, default=lambda o: getattr(o, '__dict__', str(o)), indent=4)
    
    @classmethod
    def checkPhotos(cls, path: str, name: str):
        """ Analyze photos <name>nnnnnn
            Return nrPhotos, maxNumber
        """
        nrPhotos = 0
        maxNumber = 0
        fs = []
        try:
            fs = os.listdir(path)
        except FileNotFoundError:
            fs = []
        fs.sort()
        l = len(name) + 1
        nl = l + Series.PHOTODIGITS
        for f in fs:
            if f.endswith(".jpg"):
                fn = f[:len(f) - 4]
                if len(fn) == nl:
                    nums = fn[l:]
                    if nums.isnumeric:
                        nrPhotos += 1
                        num = int(nums)
                        if num > maxNumber:
                            maxNumber = num
        return nrPhotos, maxNumber
            

    @classmethod                
    def initFromDict(cls, dict:dict):
        ser = Series()
        for key, value in dict.items():
            if key == "_start" \
            or key == "_started" \
            or key == "_end" \
            or key == "_ended":
                if value is None:
                    setattr(ser, key, value)
                else:
                    setattr(ser, key, datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))
            elif key == "_cameraConfig":
                if value is None:
                    setattr(ser, key, value)
                else:
                    ccfg = CameraConfig.initFromDict(value)
                    ser.cameraConfig = ccfg
            elif key == "_cameraControls":
                if value is None:
                    setattr(ser, key, value)
                else:
                    cctr = CameraControls.initFromDict(value)
                    ser.cameraControls = cctr
            else:
                setattr(ser, key, value)
                
        nrPhotos, maxNumber = Series.checkPhotos(ser.path, ser.name)
        ser.curShots = maxNumber
        return ser

class PhotoSeriesCfg():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PhotoSeriesCfg, cls).__new__(cls)
            cls._rootPath = None
            cls._tlSeries = []
            cls._curSeries: Series = None
        return cls._instance
    
    @property
    def rootPath(self) -> str:
        return self._rootPath

    @rootPath.setter
    def rootPath(self, value: str):
        self._rootPath = value
    
    @property
    def tlSeries(self) -> list:
        return self._tlSeries

    @tlSeries.setter
    def tlSeries(self, value: list):
        self._tlSeries = value
    
    @property
    def seriesNames(self) -> list:
        nl = []
        for s in self._tlSeries:
            nl.append(s.name)
        return nl
    
    @property
    def curSeries(self) -> Series:
        return self._curSeries

    @curSeries.setter
    def curSeries(self, value: Series):
        self._curSeries = value
    
    @property
    def hasCurSeries(self) -> bool:
        return self._curSeries is not None
        
    def appendSeries(self, s:Series):
        self._tlSeries.append(s)

    def nameExists(self, name: str) -> bool:
        ne = False
        for s in self._tlSeries:
            if s.name == name:
                ne = True
                break
        return ne
    
    def _initSeriesFromCfg(self, spath: str, name: str) -> Series:
        """ Initialize a photoseries series from folder information
            Returns True/False if series is OK/NOK
        """
        logger.debug("_initSeriesFromFolder - path: %s name: %s", spath, name)
        ser = None
        cfgFile = spath + "/" + name + "_cfg.json"
        if os.path.exists(cfgFile):
            with open(cfgFile) as f:
                try:
                    sdict = json.load(f)
                    ser = Series.initFromDict(sdict)
                except Exception:
                    ser = Series()
                    ser.name = name
                    ser.path = spath
                    ser.cfgFile = cfgFile
                    ser.logFile = spath + "/" + ser.logFileName
                    ser.camFile = spath + "/" + ser.camFileName
        return ser
    
    def initFromTlFolder(self):
        """ Initialize photoseries from file system information
        """
        try:
            tls = os.listdir(self.rootPath)
        except FileNotFoundError:
            tls = []
        tls.sort()
        logger.debug("initFromTlFolder - Found TL series: %s", tls)
        curSer = None
        lastSer = None
        for tl in tls:
            spath = self.rootPath + "/" + tl
            if os.path.isdir(spath):
                ser = self._initSeriesFromCfg(spath, tl)
                if ser:
                    self.tlSeries.append(ser)
                    lastSer = ser
                    if ser.status == "ACTIVE":
                        curSer = ser
        if curSer:
            self.curSeries = curSer
        else:
            self.curSeries = lastSer
        logger.debug("initFromTlFolder - # series: %s", len(self.tlSeries))
        
    def removeCurrentSeries(self):
        """ Remove the current series and set current series to last one in list
        """
        sp = self.curSeries.path
        try:
            if os.path.exists(sp):
                if os.path.isdir(sp):
                    shutil.rmtree(sp)
        except Exception as e:
            logger.error("Failed to delete folder %s. Reason: %s", sp, e)
            
        self.tlSeries.remove(self.curSeries)
        if len(self.tlSeries) > 0:
            self.curSeries = self.tlSeries[0]
        else:
            self.curSeries = None