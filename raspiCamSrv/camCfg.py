from libcamera import controls
from raspiCamSrv.camera_pi import Camera

class cameraControls():
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
        self._scalerCrop = (576, 0, 3456, 2592)
        self._sharpness = 1.0

    @property
    def hasFocus(self):
        if "AfMode" in Camera().cam.camera_controls:
            return True
        else:
            return False
        
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
        if value == controls.AfMteringEnum.Auto \
        or value == controls.AfMetringEnum.Windows:
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
    
class CameraCfg():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraCfg, cls).__new__(cls)
            cls._controls = cameraControls()
        return cls._instance
    
    @property
    def controls(self):
        return self._controls
