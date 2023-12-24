from libcamera import controls, Transform

class CameraControls():
    def __init__(self):
        self._aeConstraintMode = controls.AeConstraintModeEnum.Normal
        self.include_aeConstraintMode = False
        self._aeEnable = True
        self.include_aeEnable = False
        self._aeExposureMode = controls.AeExposureModeEnum.Normal
        self.include_aeExposureMode = False
        self._aeFlickerMode = 0
        self.include_aeFlickerMode = False
        self._aeFlickerPeriod = 10000
        self.include_aeFlickerPeriod = False
        self._aeMeteringMode = controls.AeMeteringModeEnum.CentreWeighted
        self.include_aeMeteringMode = False
        self._afMode = controls.AfModeEnum.Manual
        self.include_afMode = False
        self._lensPosition = 1.0
        self.include_lensPosition = False
        self._afMetering = controls.AfMeteringEnum.Auto
        self.include_afMetering = False
        self._afPause = controls.AfPauseEnum.Immediate
        self.include_afPause = False
        self._afRange = controls.AfRangeEnum.Normal
        self.include_afRange = False
        self._afSpeed = controls.AfSpeedEnum.Normal
        self.include_afSpeed = False
        self._afTrigger = controls.AfTriggerEnum.Start
        self.include_afTrigger = False
        self._afWindows = (0, 0, 0, 0)
        self.include_afWindows = False
        self._analogueGain = 1.0
        self.include_analogueGain = False
        self._awbEnable = True
        self.include_awbEnable = False
        self._awbMode = controls.AwbModeEnum.Auto
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
        
    @property
    def aeConstraintMode(self) -> int:
        return self._aeConstraintMode

    @aeConstraintMode.setter
    def aeConstraintMode(self, value: int):
        if value == controls.AeConstraintModeEnum.Normal \
        or value == controls.AeConstraintModeEnum.Highlight \
        or value == controls.AeConstraintModeEnum.Shadows \
        or value == controls.AeConstraintModeEnum.Custom:
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
        if value == controls.AeExposureModeEnum.Normal \
        or value == controls.AeExposureModeEnum.Short \
        or value == controls.AeExposureModeEnum.Long \
        or value == controls.AeExposureModeEnum.Custom:
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
        if value == controls.AeFlickerModeEnum.Off \
        or value == controls.AeFlickerModeEnum.Manual \
        or value == controls.AeFlickerModeEnum.Auto:
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
        if value == controls.AeMeteringModeEnum.CentreWeighted \
        or value == controls.AeMeteringModeEnum.Spot \
        or value == controls.AeMeteringModeEnum.Matrix \
        or value == controls.AeMeteringModeEnum.Custom:
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
    def afMetering(self) -> int:
        return self._afMetering

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
    def afPause(self) -> int:
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
    def afRange(self) -> int:
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
    def afSpeed(self) -> int:
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

    @property
    def afTrigger(self) -> int:
        return self._afTrigger

    @afTrigger.setter
    def afTrigger(self, value: int):
        if value == controls.AfTriggerEnum.Start \
        or value == controls.AfTriggerEnum.Cancel:
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
        if value == controls.AwbModeEnum.Auto \
        or value == controls.AwbModeEnum.Tungsten \
        or value == controls.AwbModeEnum.Fluorescent \
        or value == controls.AwbModeEnum.Indoor \
        or value == controls.AwbModeEnum.Daylight \
        or value == controls.AwbModeEnum.Cloudy \
        or value == controls.AwbModeEnum.Custom:
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
        if value == controls.HdrModeEnum.Off \
        or value == controls.HdrModeEnum.MultiExposureUnmerged \
        or value == controls.HdrModeEnum.MultiExposure \
        or value == controls.HdrModeEnum.SingleExposure \
        or value == controls.HdrModeEnum.Night:
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
