from libcamera import controls, Transform
import logging

logger = logging.getLogger(__name__)

class CameraInfo():
    def __init__(self):
        self._model = ""
        self._location = 0
        self._rotation = 0
        self._id = ""
        self._num = 0

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

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
        self._afWindows = ()
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
        self._stream_size_align = True
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
    def controls(self) -> str:
        return self._controls

    @controls.setter
    def controls(self, value: str):
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
        self._activeCamera = 0
        self._activeCameraInfo = ""
        self._photoRoot = "."
        self._cameraPhotoSubPath = "."
        self._photoType = "jpg"
        self._rawPhotoType = "dng"
        self._videoType = "mp4"
        self._zoomFactor = 100
        self._zoomFactorStep = 10
        self._scalerCropLiveView = (0, 0, 4608, 2592)
        self._curMenu = "live"
        self._lastLiveTab = "focus"
        self._lastConfigTab = "cfglive"
        self._lastInfoTab = "camprops"
        self._isVideoRecording = False
        self._isDisplayHidden = True
        self._displayPhoto = None
        self._displayFile = None
        self._displayMeta = None
        self._displayMetaFirst = 0
        self._displayMetaLast = 999
        self._displayBuffer = {}

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
    def isDisplayHidden(self) -> bool:
        return self._isDisplayHidden

    @isDisplayHidden.setter
    def isDisplayHidden(self, value: bool):
        self._isDisplayHidden = value

    @property
    def isVideoRecording(self) -> bool:
        return self._isVideoRecording

    @isVideoRecording.setter
    def isVideoRecording(self, value: bool):
        self._isVideoRecording = value

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
                                self.displayMetaFirst = value["displayMetaFirst"]
                                self.displayMetaLast = value["displayMetaLast"]
                                break
                else:
                    # Active element is not in buffer: Just clear active element
                    self.displayFile = None
                    self.displayPhoto = None
                    self.displayMeta = None
                    self.displayMetaFirst = 0
                    self.displayMetaLast = 999
        else:
            # Buffer is empty: Just clear active element
            self.displayFile = None
            self.displayPhoto = None
            self.displayMeta = None
            self.displayMetaFirst = 0
            self.displayMetaLast = 999
        
    def displayBufferClear(self):
        """ Clears the display buffer as well as the current display
        """
        self._displayBuffer.clear()
        self.displayFile = None
        self.displayPhoto = None
        self.displayMeta = None
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
            self.displayMetaFirst = prevEl["displayMetaFirst"]
            self.displayMetaLast = prevEl["displayMetaLast"]
    
class CameraCfg():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraCfg, cls).__new__(cls)
            cls._cameras = []
            cls._controls = CameraControls()
            cls._cameraProperties = CameraProperties()
            cls._sensorModes = []
            cls._rawFormats = []
            cls._liveViewConfig = CameraConfig()
            cls._liveViewConfig.id = "LIVE"
            cls._liveViewConfig.use_case = "Live view"
            cls._liveViewConfig.buffer_count = 4
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
            cls._serverConfig = ServerConfig()
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
    
    @property
    def cameraProperties(self) -> CameraProperties:
        return self._cameraProperties
    
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
    
    @property
    def photoConfig(self) -> CameraConfig:
        return self._photoConfig
    
    @property
    def rawConfig(self) -> CameraConfig:
        return self._rawConfig
    
    @property
    def videoConfig(self) -> CameraConfig:
        return self._videoConfig
    
    @property
    def cameraConfigs(self) -> list:
        return self._cameraConfigs
    
    @property
    def serverConfig(self) -> ServerConfig:
        return self._serverConfig
