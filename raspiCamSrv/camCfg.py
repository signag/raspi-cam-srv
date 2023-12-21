from libcamera import controls, Transform

class CameraControls():
    def __init__(self):
        self._aeConstraintMode = 0
        self._aeEnable = None
        self._aeExposureMode = 0
        self._aeMeteringMode = 0
        self._afMetering = 0
        self._afMode = controls.AfModeEnum.Manual
        self._afPause = 0
        self._afRange = 0
        self._afSpeed = 0
        self._afTrigger = 0
        self._afWindows = (0, 0, 0, 0)
        self._analogueGain = None
        self._awbEnable = None
        self._awbMode = 0
        self._brightness = 0.0
        self._colourGains = None
        self._contrast = 1.0
        self._exposureTime = None
        self._exposureValue = 0.0
        self._frameDurationLimits = None
        self._lensPosition = 1.0
        self._noiseReductionMode = 0
        self._saturation = 1.0
        self._scalerCrop = (0, 0, 4608, 2592)
        self._sharpness = 1.0
        
    @property
    def afMode(self):
        return self._afMode

    @afMode.setter
    def afMode(self, value: int):
        if value == controls.AfModeEnum.Manual \
        or value == controls.AfModeEnum.Auto \
        or value == controls.AfModeEnum.Continuous:
            self._afMode = value
        else:
            raise ValueError("Invalid value for afMode")

    @afMode.deleter
    def afMode(self):
        del self._afMode
        
    @property
    def lensePosition(self):
        return self._lensPosition
    
    @lensePosition.setter
    def lensePosition(self, value: float):
        if value >= 0.0 \
        and value <= 32.0:
            self._lensPosition = value
        else:
            raise ValueError("Invalid value for lense position. Allowed range is (0,32)")
    @lensePosition.deleter
    def lensePosition(self):
        del self._lensPosition
        
    @property
    def focalDistance(self):
        if self._lensPosition == 0:
            return 9999.9
        else:
            return 1.0 / self._lensPosition
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
    def afMetering(self):
        return self._afPause

    @afMetering.setter
    def afMetering(self, value: int):
        if value == controls.AfMeteringEnum.Auto \
        or value == controls.AfMeteringEnum.Windows:
            self._afMetering = value
        else:
            raise ValueError("Invalid value for afMetering")

    @afMetering.deleter
    def afMetering(self):
        del self._afMetering
        
    @property
    def afPause(self):
        return self._afPause

    @afPause.setter
    def afPause(self, value: int):
        if value == controls.AfPauseEnum.Immediate \
        or value == controls.AfPauseEnum.Deferred \
        or value == controls.AfPauseEnum.Resume:
            self._afPause = value
        else:
            raise ValueError("Invalid value for afPause")

    @afPause.deleter
    def afPause(self):
        del self._afPause
        
    @property
    def afRange(self):
        return self._afRange

    @afRange.setter
    def afRange(self, value: int):
        if value == controls.AfRangeEnum.Normal \
        or value == controls.AfRangeEnum.Macro \
        or value == controls.AfRangeEnum.Full:
            self._afRange = value
        else:
            raise ValueError("Invalid value for afRange")

    @afRange.deleter
    def afRange(self):
        del self._afRange
        
    @property
    def afSpeed(self):
        return self._afSpeed

    @afSpeed.setter
    def afSpeed(self, value: int):
        if value == controls.AfSpeedEnum.Normal \
        or value == controls.AfSpeedEnum.Fast:
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

class cameraConfig():
    def __init__(self):
        self._transform = 0
        self._colour_space = 0
        self._buffer_count = 0
        self._display = "main"
        self._encode = "main"
        self._sensor = None
        self._format = None
        self._size = None

class CameraProperties():
    def __init__(self):
        self._hasFocus = True
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
    def hasFocus(self):
        return self._hasFocus

    @hasFocus.setter
    def hasFocus(self, value: str):
        self._hasFocus = value

    @hasFocus.deleter
    def hasFocus(self):
        del self._hasFocus

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

class ServerConfig():
    def __init__(self):
        self._zoomFactor = 100
        self._zoomFactorStep = 10
        self._lastLiveTab = "focus"
        
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

    @zoomFactor.deleter
    def zoomFactor(self):
        del self._zoomFactor

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

    @zoomFactorStep.deleter
    def zoomFactorStep(self):
        del self._zoomFactorStep

    @property
    def lastLiveTab(self):
        return self._lastLiveTab

    @lastLiveTab.setter
    def lastLiveTab(self, value: str):
        self._lastLiveTab = value

    @lastLiveTab.deleter
    def lastLiveTab(self):
        del self._lastLiveTab
        
    
class CameraCfg():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraCfg, cls).__new__(cls)
            cls._controls = CameraControls()
            cls._cameraProperties = CameraProperties()
            cls._serverConfig = ServerConfig()
        return cls._instance
    
    @property
    def controls(self):
        return self._controls
    
    @property
    def cameraProperties(self):
        return self._cameraProperties
    
    @property
    def serverConfig(self):
        return self._serverConfig
