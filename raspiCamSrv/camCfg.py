from libcamera import controls

class cameraControls():
    def __init___(self):
        self._aeConstraintMode = 0
        self._aeEnable = None
        self._aeExposureMode = 0
        self._aeMeteringMode = 0
        self._afMetering = 0
        self._afMode = controls.AfModeEnum.AfModeManual
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
    
class CameraCfg():
    def __init__():
        pass
