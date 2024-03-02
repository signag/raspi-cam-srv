import io
import time
import datetime
import threading
from _thread import get_ident
from raspiCamSrv.camCfg import CameraInfo, CameraCfg, SensorMode, CameraConfig
from raspiCamSrv.photoseriesCfg import Series
from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls
from libcamera import Transform, Size, ColorSpace, controls
from picamera2.encoders import JpegEncoder, MJPEGEncoder
from picamera2.configuration import SensorConfiguration
from picamera2.outputs import FileOutput, FfmpegOutput
from picamera2.encoders import H264Encoder
from threading import Condition, Lock
import copy
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

prgLogger = logging.getLogger("pc2_prg")
prgLogger.debug("from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls")
prgLogger.debug("from libcamera import Transform, Size, ColorSpace, controls")
prgLogger.debug("from picamera2.encoders import JpegEncoder, MJPEGEncoder")
prgLogger.debug("from picamera2.configuration import SensorConfiguration")
prgLogger.debug("from picamera2.outputs import FileOutput, FfmpegOutput")
prgLogger.debug("from picamera2.encoders import H264Encoder")
prgLogger.debug("import time")
prgLogger.debug("Picamera2.set_logging(Picamera2.DEBUG)")
prgLogger.debug("videoDuration = 10")

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        #logger.debug("Thread %s: StreamingOutput.__init__", get_ident())
        self.frame = None
        self.lock = Lock()
        self.condition = Condition(self.lock)

    def write(self, buf):
        #logger.debug("Thread %s: StreamingOutput.write", get_ident())
        with self.condition:
            self.frame = buf
            #logger.debug("Thread %s: StreamingOutput.write - got buffer of length %s", get_ident(), len(buf))
            self.condition.notify_all()
            #logger.debug("Thread %s: StreamingOutput.write - notification done", get_ident())
        #logger.debug("Thread %s: StreamingOutput.write - write done", get_ident())
        
class CameraController():
    """ The class controls status change actions for the camera
    """
    def __init__(self, cam: Picamera2):
        logger.debug("Thread %s: CameraController.__init__", get_ident())
        self._cam = cam
        self._activeCfg:CameraConfiguration = None
        self._requestedCfg:CameraConfiguration = CameraConfiguration()
        self._activeEncoders = {}
        logger.debug("Thread %s: cfg: %s", get_ident(), self._requestedCfg)

    @property
    def configuration(self) -> CameraConfiguration:
        return self._requestedCfg

    def requestCameraForConfig(self, cfg:CameraConfig, cfgPhoto:CameraConfig=None, forLiveStream:bool=False) -> bool:
        """ Request camera start for a specific configuration
        
            Parameters:
            cfg      Configuration for which camera is requested
                     If None, request start for the active configuration
            cfgPhoto Photo configuration. To be provided when cfg is a raw photo configuration
            forLiveStream:  The request is for the Live Stream -> don't deactivete Live Stream
        
            Return:
            True  if start is exclusive for the requested configuration
            False if the active configuration is used
        """
        if cfg:
            logger.debug("Thread %s: CameraController.requestCameraForConfig cfg:        %s", get_ident(), cfg.__dict__)
        else:
            logger.debug("Thread %s: CameraController.requestCameraForConfig cfg:        %s", get_ident(), cfg)
        if cfgPhoto:
            logger.debug("Thread %s: CameraController.requestCameraForConfig - cfgPhoto: %s", get_ident(), cfgPhoto.__dict__)
        else:
            logger.debug("Thread %s: CameraController.requestCameraForConfig - cfgPhoto: %s", get_ident(), cfgPhoto)
        logger.debug("Thread %s: CameraController.requestCameraForConfig - forLiveStream: %s", get_ident(), forLiveStream)
                    
        exclusive = False

        if cfg:
            self.requestConfig(cfg, cfgPhoto=cfgPhoto)
        started = self.requestStart()
        if started:
            logger.debug("Thread %s: CameraController.requestCameraForConfig - camera started", get_ident())
        else:
            logger.debug("Thread %s: CameraController.requestCameraForConfig: Camara stop required", get_ident())
            if not forLiveStream:
                Camera.liveViewDeactivated = True
                logger.debug("Thread %s: CameraController.requestCameraForConfig - Live stream deactivated", get_ident())
            Camera.stopLiveStream()
            logger.debug("Thread %s: CameraController.requestCameraForConfig: Live stream stopped", get_ident())
            stopped = self.requestStop()
            if stopped:
                started = Camera.ctrl.requestStart()
                if started:
                    logger.debug("Thread %s: CameraController.requestCameraForConfig - camera started", get_ident())
                else:
                    logger.error("Thread %s: CameraController.requestCameraForConfig - camera could not be started", get_ident())
                    raise RuntimeError("CameraController.requestCameraForConfig - Camera could not be started")
            else:
                logger.error("Thread %s: CameraController.requestCameraForConfig - camera did not stop", get_ident())
                raise RuntimeError("CameraController.requestCameraForConfig - Camera did not stop")
            exclusive = True
        return exclusive
    
    def restoreLivestream(self, exclusive: bool):
        """ Restart the live stream after exclusive camera use by other task
        """
        logger.debug("Thread %s: CameraController.restoreLivestream - exclusive: %s", get_ident(), exclusive)
        if exclusive:
            logger.debug("Thread %s: CameraController.restoreLivestream - Need to stop camera and restart live stream", get_ident())
            stopped = self.requestStop()
            if not stopped:
                logger.error("Thread %s: CameraController.restoreLivestream - camera did not stop", get_ident())
                raise RuntimeError("CameraController.restoreLivestream - Camera did not stop")
            Camera.liveViewDeactivated = False
            logger.debug("Thread %s: CameraController.restoreLivestream - Live stream activated", get_ident())
            Camera.startLiveStream()
            logger.debug("Thread %s: CameraController.restoreLivestream: Live stream started", get_ident())
        else:
            logger.debug("Thread %s: CameraController.restoreLivestream - Restart live stream not required", get_ident())
    
    def requestStart(self) -> bool:
        """ Request to start the camera
        
            If the camera is not yet started, it is configured and started
            Return:
            - True  if the camera was started
                    or if the camera had been started before with the same configuration
            - False if the camera was already started or if an exception occurs during start
        """
        logger.debug("Thread %s: CameraController.requestStart - _cam.started: %s", get_ident(), self._cam.started)
        res = False
        if self._cam.started == False:
            try:
                self._activeCfg = self.copyConfig(self._requestedCfg)
                self._cam.configure(self._activeCfg)
                if prgLogger.level == logging.DEBUG:
                    self.codeGenConfig(self._activeCfg)
                    prgLogger.debug("picam2.configure(ccfg)")
                logger.debug("Thread %s:  CameraController.requestStart - Camera configured", get_ident())
                self._cam.start(show_preview=False)
                prgLogger.debug("picam2.start(show_preview=False)")
                logger.debug("Thread %s:  CameraController.requestStart - Camera started", get_ident())
                res = True
                # let camera warm up
                time.sleep(1.5)
                prgLogger.debug("time.sleep(1.5)")
            except RuntimeError as e:
                logger.error("Thread %s:  CameraController.requestStart - Error starting camera: %s", get_ident(), e)
        else:
            isIdentical, dif = self.compareConfig(self._requestedCfg, self._activeCfg)
            if isIdentical:
                logger.debug("Thread %s: Camera was already started with same configuration.", get_ident())
                res = True
            else:
                logger.debug("Thread %s: Camera was already started, but with different configuration. Difference is: %s", get_ident(), dif)
            
        logger.debug("Thread %s: CameraController.requestStart: %s", get_ident(), res)
        return res
    
    def requestStop(self) -> bool:
        """ Request to stop the camera
        
            If the camera is started,
            - stop the active encoders, if any
            - stop the camera
            Return:
            - True  if the camera was stopped
                    or if the camera was not started
            - False if the camera could not be stopped
        """
        logger.debug("Thread %s: CameraController.requestStop", get_ident())
        res = False
        if self._cam.started == True:
            try:
                #First stop encoders
                while len(self._activeEncoders) > 0:
                    task, encoder = self._activeEncoders.popitem()
                    self._cam.stop_encoder(encoder)
                    prgLogger.debug("picam2.stop_encoder(encoder)")
                    logger.debug("Thread %s: CameraController.requestStop - Stopped Encoder for %s", get_ident(), task)
                #Then stop the camera
                self._cam.stop()
                prgLogger.debug("picam2.stop()")
                cnt = 0
                while self._cam.started == True:
                    time.sleep(0.01)
                    cnt += 1
                    if cnt > 200:
                        logger.error("Thread %s: CameraController.requestStop - Camera did not stop", get_ident())
                        raise TimeoutError("CameraController.requestStop: Camera did not stop within 2 sec")
                if cnt < 200:
                    logger.debug("Thread %s: CameraController.requestStop - Camera stopped", get_ident())
                    res = True
            except TimeoutError:
                raise()
            except Exception as e:
                logger.error("Thread %s: CameraController.requestStop - error: %s", get_ident(), e)
                raise()
        else:
            res = True
        logger.debug("Thread %s: CameraController.requestStop: %s", get_ident(), res)
        return res

    def requestConfig(self, cfg:CameraConfig, test:bool=False, cfgPhoto:CameraConfig=None):
        """ Register a new configuration
        
            Parameters:
            cfg:     configuration to register
            test:    Run in test mode without modifying self._requestedCfg
            cfgPhoto Configuration for Photo.
                     Required only if cfg is a Raw Photo configuration.
                     In this case, cfgPhoto is used to configure the main stream for placeholder jpg photos
                     
            Return:
            configChange:       True/False if the requested configuration caused a change in configuration
            configChangeReason: Reason for configuration change: list of discrepancies
            
            If there are no configuration conflicts,
            the requested configuration is merged into the active configuration.
            Otherwise, the active configuration is replaced by the requested configuration
            and configChange is set to True and configChangeReason is filled with detected conflicts
        """
        logger.debug("Thread %s: CameraController.requestConfig - test: %s cfg     : %s", get_ident(), test, cfg.__dict__)
        if cfgPhoto:
            logger.debug("Thread %s: CameraController.requestConfig - test: %s cfgPhoto: %s", get_ident(), test, cfgPhoto.__dict__)
        else:
            logger.debug("Thread %s: CameraController.requestConfig - test: %s cfgPhoto: %s", get_ident(), test, cfgPhoto)

        cfgRef = self._requestedCfg

        configChange = False
        configChangeReason = ""

        if not test:
            if cfgRef.use_case:
                if cfgRef.use_case.find(cfg.use_case) < 0:
                    cfgRef.use_case += "," + cfg.use_case
            else:
                cfgRef.use_case = cfg.use_case

        #Transform of new config must be identical to existing
        if cfgRef.transform:
            if cfgRef.transform.hflip != cfg.transform_hflip \
            or cfgRef.transform.vflip != cfg.transform_vflip:
                configChange = True
                configChangeReason += "transform,"
        else:
            if not test:
                cfgRef.transform = Transform(vflip = cfg.transform_vflip, hflip = cfg.transform_hflip)

        #For buffer_count, always choose the larger one
        if not test:
            if cfgRef.buffer_count:
                if cfg.buffer_count > cfgRef.buffer_count:
                    cfgRef.buffer_count = cfg.buffer_count
            else:
                cfgRef.buffer_count = cfg.buffer_count

        #Colour space must be identical
        cosp = cfg.colour_space
        if cosp == "sYCC":
            colourSpace = ColorSpace.Sycc()
        elif cosp == "Smpte170m":
            colourSpace = ColorSpace.Smpte170m()
        elif cosp == "Rec709":
            colourSpace = ColorSpace.Rec709()
        else:
            colourSpace = ColorSpace.Sycc()
        
        if cfgRef.colour_space:
            if cfgRef.colour_space != colourSpace:
                configChange = True
                configChangeReason += "colourSpace,"
        else:
            if not test:
                cfgRef.colour_space = colourSpace
                                    
        #queue must be identical
        if cfgRef.queue:
            if cfgRef.queue != cfg.queue:
                configChange = True
                configChangeReason += "queue,"
        else:
            if not test:
                cfgRef.queue = cfg.queue
            
        #display must be identical
        if cfgRef.display:
            if cfgRef.display != cfg.display:
                configChange = True
                configChangeReason += "display,"
        else:
            if not test:
                cfgRef.display = cfg.display
        
        #encode is not used. Always set it to 'main'
        if not test:
            cfgRef.encode = 'main'

        #Sensor is not explicitely set in the configuration
        #It will be selected and updated by picamera2 automaticallx
        if not cfgRef.sensor:
            if not test:
                sensor = SensorConfiguration()
                sensor.output_size = None
                sensor.bit_depth = None
                cfgRef.sensor = sensor

        #'main' stream must be identical
        if cfg.stream == "main":
            if cfgRef.main:
                if cfgRef.main.size != cfg.stream_size:
                    configChange = True
                    configChangeReason += "main.size,"
                if cfgRef.main.format != cfg.format:
                    configChange = True
                    configChangeReason += "main.format,"
            else:
                if not test:
                    mstream = StreamConfiguration()
                    mstream.size = cfg.stream_size
                    mstream.format = cfg.format
                    mstream.stride = None
                    mstream.framesize = None
                    cfgRef.main = mstream

        #'lores' stream must be identical
        if cfg.stream == "lores":
            if cfgRef.lores:
                if cfgRef.lores.size != cfg.stream_size:
                    configChange = True
                    configChangeReason += "lores.size,"
                if cfgRef.lores.format != cfg.format:
                    configChange = True
                    configChangeReason += "lores.format,"
            else:
                if not test:
                    lstream = StreamConfiguration()
                    lstream.size = cfg.stream_size
                    lstream.format = cfg.format
                    lstream.stride = None
                    lstream.framesize = None
                    cfgRef.lores = lstream

        #'raw' stream must be identical
        if cfg.stream == "raw":
            if cfgRef.raw:
                if cfgRef.raw.size:
                    if cfgRef.raw.size != cfg.stream_size:
                        configChange = True
                        configChangeReason += "raw.size,"
                else:
                    if not test:
                        cfgRef.raw.size = cfg.stream_size
                if cfgRef.raw.format:
                    if cfgRef.raw.format != cfg.format:
                        configChange = True
                        configChangeReason += "raw.format,"
                else:
                    if not test:
                        cfgRef.raw.format = cfg.format
            else:
                if not test:
                    rstream = StreamConfiguration()
                    rstream.size = cfg.stream_size
                    rstream.format = cfg.format
                    rstream.stride = None
                    rstream.framesize = None
                    cfgRef.raw = rstream
        if not test:
            if cfgRef.controls:
                for key, value in cfg.controls.items():
                    if not key in cfgRef.controls:
                        cfgRef.controls[key] = value
            else:
                ctrls = copy.deepcopy(cfg.controls)
                cfgRef.controls = ctrls
        if not test:
            if configChange:
                #If cofig change is detected, replace entire configuration
                camCfg = CameraConfiguration()

                camCfg.use_case = cfg.use_case
                camCfg.transform = Transform(vflip=cfg.transform_vflip, hflip=cfg.transform_hflip)
                camCfg.buffer_count = cfg.buffer_count
                cosp = cfg.colour_space
                if cosp == "sYCC":
                    colourSpace = ColorSpace.Sycc()
                elif cosp == "Smpte170m":
                    colourSpace = ColorSpace.Smpte170m()
                elif cosp == "Rec709":
                    colourSpace = ColorSpace.Rec709()
                else:
                    colourSpace = ColorSpace.Sycc()
                camCfg.colour_space = colourSpace
                camCfg.queue = cfg.queue
                camCfg.display = cfg.display
                camCfg.encode = cfg.encode

                stream = StreamConfiguration()
                stream.size = cfg.stream_size
                stream.format = cfg.format
                if cfg.stream == "main":
                    camCfg.main = stream
                    camCfg.lores = None
                    camCfg.raw = None
                if cfg.stream == "lores":
                    camCfg.main = stream
                    camCfg.lores = stream
                    camCfg.raw = None
                if cfg.stream == "raw":
                    if cfgPhoto:
                        mstream = StreamConfiguration()
                        mstream.size = cfgPhoto.stream_size
                        mstream.format = cfgPhoto.format
                        camCfg.main = mstream
                    else:
                        camCfg.main = stream
                    camCfg.lores = None
                    camCfg.raw = stream
                ctrls = copy.deepcopy(cfg.controls)
                if len(ctrls) == 0:
                    raise ValueError("controls in camera configuration must not be empty")
                else:
                    camCfg.controls = ctrls
                cfgRef = camCfg
            
            #Automatically align the stream size, if selected
            if cfg.stream_size_align and cfg.sensor_mode == "custom" :
                cfgRef.align()
                if cfg.stream == "main":
                    cfg.stream_size = cfgRef.main.size
                if cfg.stream == "lores":
                    cfg.stream_size = cfgRef.lores.size
                    
        self._requestedCfg = cfgRef
        logger.debug("Thread %s: CameraController.requestConfig - configChange: %s", get_ident(), configChange)
        logger.debug("Thread %s: CameraController.requestConfig - configChangeReason: %s", get_ident(), configChangeReason)
        logger.debug("Thread %s: CameraController.requestConfig - cfg: %s", get_ident(), self._requestedCfg)
        return configChange, configChangeReason

    def codeGenConfig(self, cfg:CameraConfiguration):
        """ Generate code for the given configuration
        """
        logger.debug("Thread %s: CameraController.codeGenConfig cfg: %s", get_ident(), cfg.__dict__)
        prgLogger.debug("ccfg = CameraConfiguration()")
        prgLogger.debug("ccfg.use_case = \"%s\"", cfg.use_case)
        if cfg.encode:
            prgLogger.debug("ccfg.encode = \"%s\"", cfg.encode)
        else:
            prgLogger.debug("ccfg.encode = None")
        if cfg.display:
            prgLogger.debug("ccfg.display = \"%s\"", cfg.display)
        else:
            prgLogger.debug("ccfg.display = None")
        prgLogger.debug("ccfg.buffer_count = %s", cfg.buffer_count)
        prgLogger.debug("ccfg.queue = %s", cfg.queue)
        
        if cfg.transform:
            prgLogger.debug("ccfg.transform = Transform(vflip=%s, hflip=%s)", cfg.transform.vflip, cfg.transform.hflip)
        else:
            prgLogger.debug("ccfg.transform = None")
        
        if cfg.colour_space.__str__().find("sYCC") >= 0:
            prgLogger.debug("ccfg.colour_space = ColorSpace.Sycc()")
        if cfg.colour_space.__str__().find("SMPTE170M") >= 0:
            prgLogger.debug("ccfg.colour_space = ColorSpace.Smpte170m()")
        if cfg.colour_space.__str__().find("Rec709") >= 0:
            prgLogger.debug("ccfg.colour_space = ColorSpace.Rec709()")
        
        if cfg.controls:
            prgLogger.debug("ccfg.controls = %s", cfg.controls)
        else:
            prgLogger.debug("ccfg.controls = None")
            
        if cfg.sensor:
            prgLogger.debug("ccfg.sensor = SensorConfiguration()")
            prgLogger.debug("ccfg.sensor.output_size = %s", cfg.sensor.output_size)
            prgLogger.debug("ccfg.sensor.bit_depth = %s", cfg.sensor.bit_depth)
        else:
            prgLogger.debug("ccfg.sensor = None")

        if cfg.main:
            prgLogger.debug("ccfg.main = StreamConfiguration()")
            prgLogger.debug("ccfg.main.size = %s", cfg.main.size)
            prgLogger.debug("ccfg.main.format = \"%s\"", cfg.main.format)
            prgLogger.debug("ccfg.main.stride = %s", cfg.main.stride)
            prgLogger.debug("ccfg.main.framesize = %s", cfg.main.framesize)
        else:
            prgLogger.debug("ccfg.main = None")

        if cfg.lores:
            prgLogger.debug("ccfg.lores = StreamConfiguration()")
            prgLogger.debug("ccfg.lores.size = %s", cfg.lores.size)
            prgLogger.debug("ccfg.lores.format = \"%s\"", cfg.lores.format)
            prgLogger.debug("ccfg.lores.stride = %s", cfg.lores.stride)
            prgLogger.debug("ccfg.lores.framesize = %s", cfg.lores.framesize)
        else:
            prgLogger.debug("ccfg.lores = None")

        if cfg.raw:
            prgLogger.debug("ccfg.raw = StreamConfiguration()")
            prgLogger.debug("ccfg.raw.size = %s", cfg.raw.size)
            prgLogger.debug("ccfg.raw.format = \"%s\"", cfg.raw.format)
            prgLogger.debug("ccfg.raw.stride = %s", cfg.raw.stride)
            prgLogger.debug("ccfg.raw.framesize = %s", cfg.raw.framesize)
        else:
            prgLogger.debug("ccfg.raw = None")

    def copyConfig(self, cfg:CameraConfiguration) -> CameraConfiguration:
        """ Return a copy of the given configuration
        """
        logger.debug("Thread %s: CameraController.copyConfig cfg: %s", get_ident(), cfg.__dict__)
        ccfg = CameraConfiguration()
        ccfg.use_case = cfg.use_case
        ccfg.encode = cfg.encode
        ccfg.display = cfg.display
        ccfg.buffer_count = cfg.buffer_count
        ccfg.queue = cfg.queue
        
        if cfg.transform:
            ccfg.transform = Transform(vflip=cfg.transform.vflip, hflip=cfg.transform.hflip)
        else:
            ccfg.transform = None
            
        ccfg.colour_space = cfg.colour_space
        
        if cfg.controls:
            ccfg.controls = copy.copy(cfg.controls)
        else:
            ccfg.controls = None
            
        if cfg.sensor:
            ccfg.sensor = SensorConfiguration()
            ccfg.sensor.output_size = copy.copy(cfg.sensor.output_size)
            ccfg.sensor.bit_depth = cfg.sensor.bit_depth
        else:
            ccfg.sensor = None

        if cfg.main:
            ccfg.main = StreamConfiguration()
            ccfg.main.size = cfg.main.size
            ccfg.main.format = cfg.main.format
            ccfg.main.stride = cfg.main.stride
            ccfg.main.framesize = cfg.main.framesize
        else:
            ccfg.main = None

        if cfg.lores:
            ccfg.lores = StreamConfiguration()
            ccfg.lores.size = cfg.lores.size
            ccfg.lores.format = cfg.lores.format
            ccfg.lores.stride = cfg.lores.stride
            ccfg.lores.framesize = cfg.lores.framesize
        else:
            ccfg.lores = None

        if cfg.raw:
            ccfg.raw = StreamConfiguration()
            ccfg.raw.size = cfg.raw.size
            ccfg.raw.format = cfg.raw.format
            ccfg.raw.stride = cfg.raw.stride
            ccfg.raw.framesize = cfg.raw.framesize
        else:
            ccfg.raw = None
        return ccfg

    def compareConfig(self, cfg1:CameraConfiguration, cfg2:CameraConfiguration) -> bool:
        """ Check equality of configurations

            Return:
            result (bool):
                True  if configurations are identical
                False if configuration differ
            difference (str): List of differences
        """
        logger.debug("Thread %s: CameraController.compareConfig cfg1: %s", get_ident(), cfg1.__dict__)
        logger.debug("Thread %s: CameraController.compareConfig cfg2: %s", get_ident(), cfg2.__dict__)
        res = True
        dif = ""
        if cfg1.encode:
            if cfg2.encode:
                if cfg1.encode != cfg2.encode:
                    res = False
                    dif += "encode,"
            else:
                res = False
                dif += "encode,"
        else:
            if cfg2.encode:
                res = False
                dif += "encode,"

        if cfg1.display:
            if cfg2.display:
                if cfg1.display != cfg2.display:
                    res = False
                    dif += "display,"
            else:
                res = False
                dif += "display,"
        else:
            if cfg2.display:
                res = False
                dif += "display,"

        if cfg1.buffer_count:
            if cfg2.buffer_count:
                if cfg1.buffer_count != cfg2.buffer_count:
                    res = False
                    dif += "buffer_count,"
            else:
                res = False
                dif += "buffer_count,"
        else:
            if cfg2.buffer_count:
                res = False
                dif += "buffer_count,"

        if cfg1.transform:
            if cfg2.transform:
                if cfg1.transform.hflip != cfg2.transform.hflip \
                or cfg1.transform.vflip != cfg2.transform.vflip:
                    res = False
                    dif += "transform,"
            else:
                res = False
                dif += "transform,"
        else:
            if cfg2.transform:
                res = False
                dif += "transform,"

        if cfg1.colour_space:
            if cfg2.colour_space:
                if cfg1.colour_space != cfg2.colour_space:
                    res = False
                    dif += "colour_space,"
            else:
                res = False
                dif += "colour_space,"
        else:
            if cfg2.colour_space:
                res = False
                dif += "colour_space,"

        if cfg1.queue:
            if cfg2.queue:
                if cfg1.queue != cfg2.queue:
                    res = False
                    dif += "queue,"
            else:
                res = False
                dif += "queue,"
        else:
            if cfg2.queue:
                res = False
                dif += "queue,"

        if cfg1.sensor:
            if cfg2.sensor:
                if cfg1.sensor.bit_depth != cfg2.sensor.bit_depth:
                    res = False
                    dif += "sensor.bit_depth,"
                if cfg1.sensor.output_size != cfg2.sensor.output_size:
                    res = False
                    dif += "sensor.output_size,"
            else:
                res = False
                dif += "sensor,"
        else:
            if cfg2.sensor:
                res = False
                dif += "sensor,"

        if cfg1.main:
            if cfg2.main:
                if cfg1.main.size != cfg2.main.size:
                    res = False
                    dif += "main.size,"
                if cfg1.main.format != cfg2.main.format:
                    res = False
                    dif += "main.format,"
            else:
                res = False
                dif += "main,"
        else:
            if cfg2.main:
                res = False
                dif += "main,"

        if cfg1.lores:
            if cfg2.lores:
                if cfg1.lores.size != cfg2.lores.size:
                    res = False
                    dif += "lores.size,"
                if cfg1.lores.format != cfg2.lores.format:
                    res = False
                    dif += "lores.format,"
            else:
                res = False
                dif += "lores,"
        else:
            if cfg2.lores:
                res = False
                dif += "lores,"

        if cfg1.raw:
            if cfg2.raw:
                if cfg1.raw.size != cfg2.raw.size:
                    res = False
                    dif += "raw.size,"
                if cfg1.raw.format != cfg2.raw.format:
                    res = False
                    dif += "raw.format,"
            else:
                res = False
                dif += "raw,"
        else:
            if cfg2.raw:
                res = False
                dif += "raw,"

        if cfg1.controls:
            resCtrls = True
            if cfg2.controls:
                for key, value in cfg1.controls.items():
                    if key in cfg2.controls:
                        if value != cfg2.controls[key]:
                            resCtrls = False
                if len(cfg1.controls) != len(cfg2.controls):
                    resCtrls = False
            else:
                res = False
                dif += "controls,"
        else:
            if cfg2.controls:
                res = False
                dif += "controls,"
        if not resCtrls:
            res = False
            dif += "controls,"
        logger.debug("Thread %s: CameraController.compareConfig res: %s, dif: %s", get_ident(), res, dif)
        return res, dif
        
    def clearConfig(self):
        """ Clear the configuration
        """
        logger.debug("Thread %s: CameraController.clearConfig: %s", get_ident())
        self._requestedCfg = CameraConfiguration()
        
    def registerEncoder(self, task:str, encoder):
        """ Register an encoder which needs to be stopped when stopping the camera
        """
        logger.debug("Thread %s: CameraController.registerEncoder: %s", get_ident(), encoder)
        self._activeEncoders[task] = encoder
        
    def stopEncoder(self, task:str):
        """ Stop an encoder for a specific task
        """
        logger.debug("Thread %s: CameraController.stopEncoder: %s", get_ident(), task)
        if task in self._activeEncoders:
            encoder = self._activeEncoders[task]
            self._cam.stop_encoder(encoder)
            prgLogger.debug("picam2.stop_encoder(encoder)")
            del self._activeEncoders[task]
            logger.debug("Thread %s: CameraController.stopEncoder - Encoder stopped", get_ident())

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        #logger.debug("Thread %s: CameraEvent.__init__", get_ident())
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        #logger.debug("Thread %s: CameraEvent.wait", get_ident())
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
            #logger.debug("Thread %s: CameraEvent.wait - Event ident: %s added to events dict. time:%s", get_ident(), ident, self.events[ident][1])
        #for ident, event in self.events.items():
            #logger.debug("Thread %s: CameraEvent.wait - Event ident: %s Flag: %s Time: %s (Flag False -> blocking)", get_ident(), ident, self.events[ident][0].is_set(), event[1])
            
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        #logger.debug("Thread %s: CameraEvent.set", get_ident())
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
                #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s Flag: False -> True (unblock/notify)", get_ident(), ident)
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s Flag: True (Last image not processed).", get_ident(), ident)
                if now - event[1] > 5:
                    #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s  too old; marked for removal.", get_ident(), ident)
                    remove = ident
        if remove:
            del self.events[remove]
            #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s removed.", get_ident(), ident)

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        self.events[get_ident()][0].clear()
        #logger.debug("Thread %s: CameraEvent.clear - Flag set to False -> blocking.", get_ident())

class Camera():
    logger.debug("Thread %s: Camera - setting class variables", get_ident())
    _instance = None
    ENCODER_LIVESTREAM = "LIVESTREAM"
    ENCODER_VIDEO = "VIDEO"
    ENCODER_PHOTOSERIES = "PHOTOSERIES"
    
    cam: Picamera2 = None
    camNum = -1
    ctrl:CameraController = None
    videoOutput = None
    prgVideoOutput = None
    photoSeries:Series = None
    
    thread = None               # background thread that reads frames from camera
    liveViewDeactivated = False
    videoThread = None
    photoSeriesThread = None
    frame = None                    # current frame is stored here by background thread
    last_access = 0                 # time of last client access to the camera
    stopRequested = False           # Request to stop the background thread
    stopVideoRequested = False      # Request to stop the video thread
    stopPhotoSeriesRequested = False  # Request to stop the photoseries thread
    event = CameraEvent()
    

    def __new__(cls):
        logger.debug("Thread %s: Camera.__new__", get_ident())
        if cls._instance is None:
            logger.debug("Thread %s: Camera.__new__ - Instantiating Camera Class", get_ident())
            cls._instance = super(Camera, cls).__new__(cls)

            # Before all, load the global camera info to get the installed cameras and the active cam
            activeCam = Camera.getActiveCamera()
            
            if Camera.cam is None:
                logger.debug("Thread %s: Camera.__new__: Camera instantiated: %s", get_ident(), activeCam)
                Camera.cam = Picamera2(activeCam)
                prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                Camera.camNum = activeCam
                Camera.ctrl = CameraController(Camera.cam)
            else:
                if activeCam != Camera.camNum:
                    logger.debug("Thread %s: Camera.__new__: About to switch camera from %s to %s", get_ident(), Camera.camNum, activeCam)
                    Camera.stopCameraSystem()
                    Camera.cam = Picamera2(activeCam)
                    prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                    Camera.camNum = activeCam
                    Camera.ctrl = CameraController(Camera.cam)
                    logger.debug("Thread %s: Camera.__new__: Switch camera to %s successful", get_ident(), activeCam)
                    # Force refresh of camera properties
                    CameraCfg().cameraProperties.model=None
                    CameraCfg().sensorModes = []
                    CameraCfg().rawFormats = []
                    logger.debug("Thread %s: Camera.__new__: Camera-specific configs were reset", get_ident())
                else:
                    logger.debug("Thread %s: Camera.__new__: Camera was already instantiated", get_ident())
            cls.loadCameraSpecifics()
            
        return cls._instance

    @classmethod
    def switchCamera(cls):
        """ Switch the camera
        """
        logger.debug("Thread %s: Camera.switchCamera", get_ident())
        
        logger.debug("Thread %s: Camera.switchCamera - stopping Live Stream", get_ident())
        cls.stopLiveStream()
        logger.debug("Thread %s: Camera.switchCamera - Live Stream stopped", get_ident())

        activeCam = Camera.getActiveCamera()
        if Camera.cam is None:
            logger.debug("Thread %s: Camera.switchCamera: Camera instantiated: %s", get_ident(), activeCam)
            Camera.cam = Picamera2(activeCam)
            prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
            Camera.camNum = activeCam
            Camera.ctrl = CameraController(Camera.cam)
        else:
            if activeCam != Camera.camNum:
                logger.debug("Thread %s: Camera.switchCamera: About to switch camera from %s to %s", get_ident(), Camera.camNum, activeCam)
                Camera.stopCameraSystem()
                Camera.cam = Picamera2(activeCam)
                prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                Camera.camNum = activeCam
                Camera.ctrl = CameraController(Camera.cam)
                logger.debug("Thread %s: Camera.switchCamera: Switch camera to %s successful", get_ident(), activeCam)
                # Force refresh of camera properties
                CameraCfg().cameraProperties.model=None
                CameraCfg().sensorModes = []
                CameraCfg().rawFormats = []
                logger.debug("Thread %s: Camera.switchCamera: Camera-specific configs were reset", get_ident())
            else:
                logger.debug("Thread %s: Camera.switchCamera: Camera was already instantiated", get_ident())
        cls.loadCameraSpecifics()

        logger.debug("Thread %s: Camera.switchCamera - starting Live Stream", get_ident())
        cls.startLiveStream()
        logger.debug("Thread %s: Camera.switchCamera - Live Stream started", get_ident())

    @classmethod
    def startLiveStream(cls):
        """ Start thread for live stream
        """
        logger.debug("Thread %s: Camera.startLiveStream", get_ident())
        if Camera.liveViewDeactivated:
            logger.debug("Thread %s: Not starting Live View thread. Live View deactivated")
            CameraCfg().serverConfig.isLiveStream = False
        else:
            if Camera.thread is None:
                logger.debug("Thread %s: Camera.startLiveStream: Starting new thread", get_ident())
                Camera.last_access = time.time()

                # start background frame thread
                Camera.thread = threading.Thread(target=cls._thread)
                Camera.thread.start()
                logger.debug("Thread %s: Camera.startLiveStream - Thread started", get_ident())

                # wait until first frame is available
                logger.debug("Thread %s: Camera.startLiveStream - waiting for frame", get_ident())
                Camera.event.wait()
                CameraCfg().serverConfig.isLiveStream = True
            else:
                logger.debug("Thread %s: Camera.startLiveStream - Thread exists", get_ident())
                if not Camera.thread.is_alive:
                    logger.debug("Thread %s: Camera.startLiveStream - Thread is not alive", get_ident())
                    Camera.thread = threading.Thread(target=cls._thread)
                    Camera.thread.start()
                    logger.debug("Thread %s: Camera.startLiveStream - Thread started", get_ident())

    @classmethod
    def stopLiveStream(cls):
        """ Stop thread for live stream
        """
        logger.debug("Thread %s: Camera.stopLiveStream", get_ident())
        if not Camera.thread is None:
            logger.debug("Thread %s: Camera.stopLiveStream - stopping live stream thread", get_ident())
            Camera.stopRequested = True
            cnt = 0
            while Camera.thread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    # Assume thread dead
                    Camera.thread = None
                    logger.debug("Thread %s: Camera.stopLiveStream: Thread assumed dead", get_ident())
                    break
                    #raise TimeoutError("Background thread did not stop within 2 sec")
            if cnt < 200:
                logger.debug("Thread %s: Camera.stopLiveStream: Thread has stopped", get_ident())
            Camera.ctrl.stopEncoder(Camera.ENCODER_LIVESTREAM)
            CameraCfg().serverConfig.isLiveStream = False
        else:
            logger.debug("Thread %s: Camera.stopLiveStream: Thread was not started", get_ident())
            CameraCfg().serverConfig.isLiveStream = False
    
    @staticmethod
    def restartLiveStream():
        logger.debug("Thread %s: Camera.restartLiveStream", get_ident())
        Camera.stopLiveStream()
        logger.debug("Thread %s: Camera.restartLiveStream: Live stream stopped", get_ident())
        Camera.ctrl.requestStop()
        logger.debug("Thread %s: Camera.restartLiveStream: Camera stopped", get_ident())
        Camera.ctrl.clearConfig()
        logger.debug("Thread %s: Camera.restartLiveStream: Config cleared", get_ident())
        Camera.startLiveStream()
        logger.debug("Thread %s: Camera.restartLiveStream: Live stream started", get_ident())

    def get_frame(self):
        """Return the current camera frame."""
        #logger.debug("Thread %s: Camera.get_frame", get_ident())
        Camera.last_access = time.time()

        # wait for a signal from the camera thread
        #logger.debug("Thread %s: Camera.get_frame - waiting for frame", get_ident())
        Camera.event.wait()
        #logger.debug("Thread %s: Camera.get_frame - continue", get_ident())
        Camera.event.clear()

        #logger.debug("Thread %s: Returning frame", get_ident())
        return Camera.frame
        
    @staticmethod
    def getActiveCamera() -> int:
        """ Load the global camera info, if not already done,
            Which gives us the list of currently connected cameras.
            
            Then check the active camera and return it
        """
        logger.debug("Thread %s: Camera.getActiveCamera", get_ident())
        cfg = CameraCfg()
        if len(cfg.cameras) == 0:
            cfgCams = []
            cams = Picamera2.global_camera_info()
            if len(cams) == 0:
                raise SystemError("No cameras were found on the server's device")
            camNum = 0
            for camera in cams:
                cfgCam = CameraInfo()
                if "Model" in camera:
                    cfgCam.model = camera["Model"]
                if "Location" in camera:
                    cfgCam.location = camera["Location"]
                if "Rotation" in camera:
                    cfgCam.rotation = camera["Rotation"]
                if "Id" in camera:
                    cfgCam.id = camera["Id"]
                    # Check for USB camera
                    if cfgCam.id.find("/usb@") > 0:
                        cfgCam.isUsb = True
                        logger.debug("Thread %s: Camera.getActiveCamera - USB camera found:  %s", get_ident(), cfgCam.id)
                # On Bullseye systems, "Num" is not in the dict
                if "Num" in camera:
                    cfgCam.num = camera["Num"]
                else:
                    cfgCam.num = camNum
                    camNum += 1
                cfgCams.append(cfgCam)
            cfg.cameras = cfgCams
            logger.debug("Thread %s: Camera.getActiveCamera - %s cameras found", get_ident(), len(cfg.cameras))
        
        # Check that active camera is within the list of cameras
        sc = cfg.serverConfig
        activeCamOK = False
        activeCam = sc.activeCamera
        for cfgCam in cfg.cameras:
            if cfgCam.num == activeCam:
                # Accept the active camera only if it is not a USB camera
                if cfgCam.isUsb == False:
                    activeCamOK = True
                    sc.activeCameraInfo = "Camera " + str(cfgCam.num) + " (" + cfgCam.model + ")"
                break
        logger.debug("Thread %s: Camera.getActiveCamera - Active camera:%s - activeCamOK:%s", get_ident(), activeCam, activeCamOK)
        # If config for active camera is not in the list, or if it is a USB cam, 
        # set it to the first non-USB camera
        if activeCamOK == False:
            for cfgCam in cfg.cameras:
                if cfgCam.isUsb == False:
                    sc.activeCamera = cfgCam.num
                    sc.activeCameraInfo = "Camera " + str(cfgCam.num) + " (" + cfgCam.model + ")"
                    break
            logger.debug("Thread %s: Camera.getActiveCamera - active camera reset to %s", get_ident(), sc.activeCamera)
        # Make sure that folder for photos exists
        sc.cameraPhotoSubPath = "photos/" + "camera_" + str(sc.activeCamera)
        fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath
        if not os.path.exists(fp):
            os.makedirs(fp)
            logger.debug("Thread %s: Camera.getActiveCamera - Photo directory created %s", get_ident(), fp)
        
        return cfg.serverConfig.activeCamera
        
    @staticmethod
    def loadCameraSpecifics():
        """ Load camera specific parameters into configuration, if not already done
        """
        logger.debug("Thread %s: Camera.loadCameraSpecifics", get_ident())
        cfg = CameraCfg()
        cfgProps = cfg.cameraProperties
        cfgCtrls = cfg.controls
        cfgSensorModes = cfg.sensorModes
        cfgRawFormats = cfg.rawFormats
        
        # Load Camera Properties
        if cfgProps.model is None:
            camPprops = Camera.cam.camera_properties
            cfgProps.model = camPprops["Model"]
            cfgProps.unitCellSize = camPprops["UnitCellSize"]
            cfgProps.location = camPprops["Location"]
            cfgProps.rotation = camPprops["Rotation"]
            cfgProps.pixelArraySize = camPprops["PixelArraySize"]
            cfgProps.pixelArrayActiveAreas = camPprops["PixelArrayActiveAreas"]
            cfgProps.colorFilterArrangement= camPprops["ColorFilterArrangement"]
            cfgProps.scalerCropMaximum = camPprops["ScalerCropMaximum"]
            cfgProps.systemDevices = camPprops["SystemDevices"]
            
            cfgProps.hasFocus = "AfMode" in Camera.cam.camera_controls
            cfgProps.hasFlicker = "AeFlickerMode" in Camera.cam.camera_controls
            cfgProps.hasHdr = "HdrMode" in Camera.cam.camera_controls
            
            cfgCtrls.scalerCrop = (0, 0, camPprops["PixelArraySize"][0], camPprops["PixelArraySize"][1])
            logger.debug("Thread %s: Camera.loadCameraSpecifics loaded to config", get_ident())

        # Load Sensor Modes
        if len(cfgSensorModes) == 0:
            sensorModes = Camera.cam.sensor_modes
            ind = 0
            for mode in sensorModes:
                fmt = str(mode["format"])
                if not fmt in cfgRawFormats:
                    cfgRawFormats.append(fmt)
                fmt = str(mode["unpacked"])
                if not fmt in cfgRawFormats:
                    cfgRawFormats.append(fmt)
                cfgMode = SensorMode()
                cfgMode.id = str(ind)
                cfgMode.format = mode["format"]
                cfgMode.unpacked = mode["unpacked"]
                cfgMode.bit_depth = mode["bit_depth"]
                cfgMode.size = mode["size"]
                cfgMode.fps = mode["fps"]
                cfgMode.crop_limits = mode["crop_limits"]
                cfgMode.exposure_limits = mode["exposure_limits"]
                cfgSensorModes.append(cfgMode)
                ind = ind + 1
            logger.debug("Thread %s: %s sensor modes found", get_ident(), len(cfg.sensorModes))
            logger.debug("Thread %s: %s raw formats found", get_ident(), len(cfg.rawFormats))
            
            # Set some Sensor Mode specific parameters for standard configurations
            maxModei = len(cfg.sensorModes) - 1
            maxMode = str(maxModei)
            # For Live View
            # Initially set the stream size to (640, 480). Use Sensor Mode, if possible
            # If stream_size is set, keep the settings. They have been loeaded from stored config
            if cfg.liveViewConfig.stream_size is None:
                sizeWidth = 640
                sizeHeight =  int(sizeWidth * cfgProps.pixelArraySize[1] / cfgProps.pixelArraySize[0])
                if (sizeHeight % 2) != 0:
                    sizeHeight += 1
                cfg.liveViewConfig.stream_size = (sizeWidth, sizeHeight)
                cfg.liveViewConfig.stream_size_align = False
                if cfgSensorModes[0].size[0] == sizeWidth \
                and cfgSensorModes[0].size[1] == sizeHeight:
                    cfg.liveViewConfig.sensor_mode = "0"
                else:
                    cfg.liveViewConfig.sensor_mode = "custom"
            # For photo
            if cfg.photoConfig.stream_size is None:
                cfg.photoConfig.sensor_mode = maxMode
                cfg.photoConfig.stream_size = cfgSensorModes[maxModei].size
            # For raw photo
            if cfg.rawConfig.stream_size is None:
                cfg.rawConfig.sensor_mode = maxMode
                cfg.rawConfig.stream_size = cfgSensorModes[maxModei].size
                cfg.rawConfig.format = str(cfgSensorModes[maxModei].format)
            # For Video
            if cfg.videoConfig.stream_size is None:
                cfg.videoConfig.sensor_mode = maxMode
                cfg.videoConfig.stream_size = cfgSensorModes[maxModei].size
    
    @staticmethod
    def configure(cfg: CameraConfig, cfgPhoto: CameraConfig):
        """ The function creates and configures a CameraConfiguration
            based on given configuration settings cfg.
            
            The fully configured configuration is returned
        """
        logger.debug("Thread %s: Camera.configure", get_ident())
        # We start configuration with a new blank CameraConfiguration object
        camCfg = CameraConfiguration()

        camCfg.use_case = cfg.use_case
        camCfg.transform = Transform(vflip=cfg.transform_vflip, hflip=cfg.transform_hflip)
        camCfg.buffer_count = cfg.buffer_count
        cosp = cfg.colour_space
        if cosp == "sYCC":
            colourSpace = ColorSpace.Sycc()
        elif cosp == "Smpte170m":
            colourSpace = ColorSpace.Smpte170m()
        elif cosp == "Rec709":
            colourSpace = ColorSpace.Rec709()
        else:
            colourSpace = ColorSpace.Sycc()
        camCfg.colour_space = colourSpace
        camCfg.queue = cfg.queue
        camCfg.display = cfg.display
        camCfg.encode = cfg.encode
        # The mainStream is configured here from the photo configuration (e.g. jpg)
        # to allow for a jpeg in addition to a dng from the raw stream
        mainStream = StreamConfiguration()
        mainStream.format = cfgPhoto.format
        # However the size shall be that of the target configuration
        # so that the formats of both, jpg and dng are the same
        mainStream.size = cfg.stream_size
        stream = StreamConfiguration()
        stream.size = cfg.stream_size
        stream.format = cfg.format
        if cfg.stream == "main":
            camCfg.main = stream
            camCfg.lores = None
            camCfg.raw = None
        if cfg.stream == "lores":
            camCfg.main = mainStream
            camCfg.lores = stream
            camCfg.raw = None
        if cfg.stream == "raw":
            camCfg.main = mainStream
            camCfg.lores = None
            camCfg.raw = stream
        ctrls = cfg.controls
        if len(ctrls) == 0:
            raise ValueError("controls in camera configuration must not be empty")
        else:
            camCfg.controls = ctrls
        logger.debug("Thread %s: Camera.configure: configuration completed", get_ident())
        
        #Automatically align the stream size, if selected
        if cfg.stream_size_align and cfg.sensor_mode == "custom" :
            logger.debug("Thread %s: Camera.configure: Aligning camera configuration. Old size: %s", get_ident(), cfg.stream_size)
            camCfg.align()
            logger.debug("Thread %s: Camera.configure: Alignment successful. Adjusting stream size", get_ident())
            cfg.stream_size = camCfg.size
            logger.debug("Thread %s: Camera.configure: Stream size adjusted to %s", get_ident(), cfg.stream_size)

        return camCfg

    @staticmethod
    def applyControls(camCfg: CameraConfig, exceptCtrl=None, exceptValue = None):
        """ Apply the currently selected camera controls
            camCfg      : Configuration from which controls shall be taken with priority
            exceptCtrl  : Exception control. Optionally, one exceptional control can be specified
                          If specified, the exceptValue will replace the value fom CameraCfg().controls
                          Currently supported:
                          - ExposureTime
                          - AnalogueGain
                          - FocalDistance -> LensPosition = 1 / FocalDistance
        """
        logger.debug("Thread %s: Camera.applyControls", get_ident())

        cfg = CameraCfg()
        cfgCtrls = cfg.controls
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)

        # Initialize controls dict with controls included in configuration
        #ctrls = copy.deepcopy(camCfg.controls)
        ctrls = {}
        logger.debug("Thread %s: Camera.applyControls - camCfg.controls=%s", get_ident(), ctrls)
        cnt = 0
        
        # Apply selected controls with precedence of controls from configuration
        # Auto exposure controls
        if cfgCtrls.include_aeEnable and "AeEnable" not in camCfg.controls:
            ctrls["AeEnable"] = cfgCtrls.aeEnable
            cnt += 1
        if cfgCtrls.include_aeMeteringMode and "AeMeteringMode" not in camCfg.controls:
            ctrls["AeMeteringMode"] = cfgCtrls.aeMeteringMode
            cnt += 1
        if cfgCtrls.include_aeExposureMode and "AeExposureMode" not in camCfg.controls:
            ctrls["AeExposureMode"] = cfgCtrls.aeExposureMode
            cnt += 1
        if cfgCtrls.include_aeConstraintMode and "AeConstraintMode" not in camCfg.controls:
            ctrls["AeConstraintMode"] = cfgCtrls.aeConstraintMode
            cnt += 1
        if cfgCtrls.include_aeFlickerMode and "AeFlickerMode" not in camCfg.controls:
            ctrls["AeFlickerMode"] = cfgCtrls.aeFlickerMode
            cnt += 1
        if cfgCtrls.include_aeFlickerPeriod and "AeFlickerPeriod" not in camCfg.controls:
            ctrls["AeFlickerPeriod"] = cfgCtrls.aeFlickerPeriod
            cnt += 1
        # Exposure controls
        if cfgCtrls.include_exposureTime and "ExposureTime" not in camCfg.controls:
            ctrls["ExposureTime"] = cfgCtrls.exposureTime
            cnt += 1
        if cfgCtrls.include_exposureValue and "ExposureValue" not in camCfg.controls:
            ctrls["ExposureValue"] = cfgCtrls.exposureValue
            cnt += 1
        if cfgCtrls.include_analogueGain and "AnalogueGain" not in camCfg.controls:
            ctrls["AnalogueGain"] = cfgCtrls.analogueGain
            cnt += 1
        if cfgCtrls.include_colourGains and "ColourGains" not in camCfg.controls:
            ctrls["ColourGains"] = (cfgCtrls.colourGainRed, cfgCtrls.colourGainBlue)
            cnt += 1
        if cfgCtrls.include_frameDurationLimits and "FrameDurationLimits" not in camCfg.controls:
            ctrls["FrameDurationLimits"] = (cfgCtrls.frameDurationLimitMax, cfgCtrls.frameDurationLimitMin)
            cnt += 1
        if cfgCtrls.include_hdrMode and "HdrMode" not in camCfg.controls:
            ctrls["HdrMode"] = cfgCtrls.hdrMode
            cnt += 1
        # Image controls
        if cfgCtrls.include_awbEnable and "AwbEnable" not in camCfg.controls:
            ctrls["AwbEnable"] = cfgCtrls.awbEnable
            cnt += 1
        if cfgCtrls.include_awbMode and "AwbMode" not in camCfg.controls:
            ctrls["AwbMode"] = cfgCtrls.awbMode
            cnt += 1
        if cfgCtrls.include_noiseReductionMode and "NoiseReductionMode" not in camCfg.controls:
            ctrls["NoiseReductionMode"] = cfgCtrls.noiseReductionMode
            cnt += 1
        if cfgCtrls.include_sharpness and "Sharpness" not in camCfg.controls:
            ctrls["Sharpness"] = cfgCtrls.sharpness
            cnt += 1
        if cfgCtrls.include_contrast and "Contrast" not in camCfg.controls:
            ctrls["Contrast"] = cfgCtrls.contrast
            cnt += 1
        if cfgCtrls.include_saturation and "Saturation" not in camCfg.controls:
            ctrls["Saturation"] = cfgCtrls.saturation
            cnt += 1
        if cfgCtrls.include_brightness and "Brightness" not in camCfg.controls:
            ctrls["Brightness"] = cfgCtrls.brightness
            cnt += 1
        # Scaler crop
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)
        logger.debug("Thread %s: Camera.applyControls - include_scalerCrop=%s", get_ident(), cfgCtrls.include_scalerCrop)
        if cfgCtrls.include_scalerCrop and "ScalerCrop" not in camCfg.controls:
            ctrls["ScalerCrop"] = cfgCtrls.scalerCrop
            cnt += 1
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)
        # Focus
        if cfg.cameraProperties.hasFocus:
            if cfgCtrls.include_afMode and "AfMode" not in camCfg.controls:
                ctrls["AfMode"] = cfgCtrls.afMode
                cnt += 1
            if cfgCtrls.include_lensPosition and "LensPosition" not in camCfg.controls:
                ctrls["LensPosition"] = cfgCtrls.lensPosition
                cnt += 1
            if cfgCtrls.include_afMetering and "AfMetering" not in camCfg.controls:
                ctrls["AfMetering"] = cfgCtrls.afMetering
                cnt += 1
            if cfgCtrls.include_afPause and "AfPause" not in camCfg.controls:
                ctrls["AfPause"] = cfgCtrls.afPause
                cnt += 1
            if cfgCtrls.include_afRange and "AfRange" not in camCfg.controls:
                ctrls["AfRange"] = cfgCtrls.afRange
                cnt += 1
            if cfgCtrls.include_afSpeed and "AfSpeed" not in camCfg.controls:
                ctrls["AfSpeed"] = cfgCtrls.afSpeed
                cnt += 1
            if cfgCtrls.include_afTrigger and "AfTrigger" not in camCfg.controls:
                ctrls["AfTrigger"] = cfgCtrls.afTrigger
                cnt += 1
            if cfgCtrls.include_afWindows and "AfWindows" not in camCfg.controls:
                ctrls["AfWindows"] = cfgCtrls.afWindows
                cnt += 1
            # Consider exception control
            if exceptCtrl:
                if exceptCtrl == "FocalDistance":
                    if not "LensPosition" in camCfg.controls:
                        cnt += 1
                    ctrls["LensPosition"] = 1.0 / exceptValue
        
        # Consider exception control
        if exceptCtrl:
            if exceptCtrl != "FocalDistance":
                if not exceptCtrl in camCfg.controls:
                    cnt += 1
                if exceptCtrl == "ExposureTime":
                    ctrls[exceptCtrl] = int(exceptValue)
                else:
                    ctrls[exceptCtrl] = exceptValue
            
        logger.debug("Thread %s: Camera.applyControls - Applying %s controls", get_ident(), cnt)
        camCtrls = Controls(Camera.cam)
        prgLogger.debug("camCtrls = Controls(picam2)")
        prgLogger.debug("ctrls = %s", ctrls)
        camCtrls.set_controls(ctrls)
        prgLogger.debug("camCtrls.set_controls(ctrls)")
        Camera.cam.controls = camCtrls
        prgLogger.debug("picam2.controls = camCtrls")
        logger.debug("Thread %s: Camera.applyControls - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)
        return camCtrls

    @staticmethod
    def applyControlsForAfCycle(camCfg: CameraConfig):
        """Apply camera controls required for AF cycle"""
        logger.debug("Thread %s: Camera.applyControlsForAfCycle", get_ident())

        cfg = CameraCfg()
        cfgCtrls = cfg.controls

        # Initialize controls dict with controls included in configuration
        #ctrls = copy.deepcopy(camCfg.controls)
        ctrls = {}
        cnt = 0
        # Focus
        if cfg.cameraProperties.hasFocus:
            if cfgCtrls.include_afMode and "AfMode" not in camCfg.controls:
                ctrls["AfMode"] = cfgCtrls.afMode
                cnt += 1
            if cfgCtrls.include_afMetering and "AfMetering" not in camCfg.controls:
                ctrls["AfMetering"] = cfgCtrls.afMetering
                cnt += 1
            if cfgCtrls.include_afPause and "AfPause" not in camCfg.controls:
                ctrls["AfPause"] = cfgCtrls.afPause
                cnt += 1
            if cfgCtrls.include_afRange and "AfRange" not in camCfg.controls:
                ctrls["AfRange"] = cfgCtrls.afRange
                cnt += 1
            if cfgCtrls.include_afSpeed and "AfSpeed" not in camCfg.controls:
                ctrls["AfSpeed"] = cfgCtrls.afSpeed
                cnt += 1
            if cfgCtrls.include_afWindows and "AfWindows" not in camCfg.controls:
                ctrls["AfWindows"] = cfgCtrls.afWindows
                cnt += 1
            
        logger.debug("Thread %s: Camera.applyControlsForAfCycle - Applying %s controls", get_ident(), cnt)
        camCtrls = Controls(Camera.cam)
        prgLogger.debug("camCtrls = Controls(picam2)")
        prgLogger.debug("ctrls = %s", ctrls)
        camCtrls.set_controls(ctrls)
        prgLogger.debug("camCtrls.set_controls(ctrls)")
        Camera.cam.controls = camCtrls
        prgLogger.debug("picam2.controls = camCtrls")
        logger.debug("Thread %s: Camera.applyControlsForAfCycle - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)

    @staticmethod
    def applyControlsForLivestream(wait:float=None):
        """ Apply active controls if livestream is active
        """
        logger.debug("Thread %s: Camera.applyControlsForLivestream", get_ident())
        if Camera.thread:
            if wait:
                time.sleep(wait)
            Camera.applyControls(Camera.ctrl.configuration)
            logger.debug("Thread %s: Camera.applyControlsForLivestream - Controlls applied", get_ident())
             
    @staticmethod
    def stopCameraSystem():
        logger.debug("Thread %s: Camera.stopCameraSystem", get_ident())
        logger.debug("Thread %s: Camera.stopCameraSystem: Stopping Live view thread", get_ident())
        Camera.stopRequested = True
        if Camera.thread:
            cnt = 0
            while Camera.thread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    break
            if Camera.thread:
                logger.debug("Thread %s: Camera.stopCameraSystem: Live view thread did not stop within 2 sec", get_ident())
            else:
                logger.debug("Thread %s: Camera.stopCameraSystem: Live view thread successfully stopped", get_ident())
        else:
            logger.debug("Thread %s: Camera.stopCameraSystem: Live view thread was not active", get_ident())
        Camera.stopRequested = False
        
        logger.debug("Thread %s: Camera.stopCameraSystem: Stopping Video thread", get_ident())
        Camera.stopVideoRequested = True        
        if Camera.videoThread:
            cnt = 0
            while Camera.videoThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    break
            if Camera.videoThread:
                logger.debug("Thread %s: Camera.stopCameraSystem: Video thread did not stop within 2 sec", get_ident())
            else:
                logger.debug("Thread %s: Camera.stopCameraSystem: Video thread successfully stopped", get_ident())
        else:
            logger.debug("Thread %s: Camera.stopCameraSystem: Video thread was not active", get_ident())
        Camera.stopVideoRequested = False        
        
        logger.debug("Thread %s: Camera.stopCameraSystem: Stopping Photoseries thread", get_ident())
        Camera.stopPhotoSeriesRequested = True        
        if Camera.photoSeriesThread:
            cnt = 0
            while Camera.photoSeriesThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 500:
                    break
            if Camera.photoSeriesThread:
                logger.debug("Thread %s: Camera.stopCameraSystem: Photoseries thread did not stop within 5 sec", get_ident())
            else:
                logger.debug("Thread %s: Camera.stopCameraSystem: Photoseries thread successfully stopped", get_ident())
        else:
            logger.debug("Thread %s: Camera.stopCameraSystem: Photoseries thread was not active", get_ident())
        Camera.stopPhotoSeriesRequested = False        
        
        Camera.ctrl.requestStop()
        logger.debug("Thread %s: Camera.stopCameraSystem: Camara stopped", get_ident())
        Camera.cam.close()
        prgLogger.debug("picam2.close()")
        logger.debug("Thread %s: Camera.stopCameraSystem: Camara closed", get_ident())

    @classmethod
    def _thread(cls):
        """Camera background thread."""
        logger.debug("Thread %s: Camera._thread", get_ident())
        try:
            frames_iterator = cls.frames()
            logger.debug("Thread %s: Camera._thread - frames_iterator instantiated", get_ident())
            for frame in frames_iterator:
                Camera.frame = frame
                #logger.debug("Thread %s: Camera._thread - received frame from camera -> notifying clients", get_ident())
                Camera.event.set()  # send signal to clients
                time.sleep(0)
                
                # Check whether stop is requested
                if Camera.stopRequested:
                    frames_iterator.close()
                    Camera.stopRequested = False
                    logger.debug("Thread %s: Camera._thread - Thread is requested to stop.", get_ident())
                    break

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - Camera.last_access > 10:
                    frames_iterator.close()
                    logger.debug("Thread %s: Camera._thread - Stopping camera thread due to inactivity.", get_ident())
                    break
        except Exception:
            logger.error("Thread %s: Camera._thread - Exception.", get_ident())
            if frames_iterator:
                frames_iterator.close()
            Camera.event.clear()
                
        Camera.thread = None
        CameraCfg().serverConfig.isLiveStream = False

    @staticmethod
    def frames():
        logger.debug("Thread %s: Camera.frames", get_ident())
        srvCam = CameraCfg()
        cc, cr = Camera.ctrl.requestConfig(srvCam.photoConfig)
        if cc:
            #If the request for photoConfig caused a configuration change, restart with a new configuration
            Camera.ctrl.clearConfig()
            Camera.ctrl.requestConfig(srvCam.photoConfig)
        Camera.ctrl.requestConfig(srvCam.rawConfig, cfgPhoto=srvCam.photoConfig)
        Camera.ctrl.requestConfig(srvCam.liveViewConfig)
        started = Camera.ctrl.requestStart()
        if not started:
            Camera.ctrl.requestCameraForConfig(cfg=None, forLiveStream=True)
        else:
            logger.debug("Thread %s: Camera.frames - camera started", get_ident())

        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera.frames - controls applied", get_ident())
        time.sleep(0.5)

        try:
            output = StreamingOutput()
            prgLogger.debug("output = None")
            encoder = MJPEGEncoder()
            prgLogger.debug("encoder = MJPEGEncoder()")
            Camera.cam.start_encoder(encoder, FileOutput(output), name=srvCam.liveViewConfig.stream)
            prgLogger.debug("picam2.start_encoder(encoder, FileOutput(output), name=\"%s\")", srvCam.liveViewConfig.stream)
            prgLogger.debug("time.sleep(videoDuration)")
            Camera.ctrl.registerEncoder(Camera.ENCODER_LIVESTREAM, encoder)
            logger.debug("Thread %s: Camera.frames - encoder started", get_ident())

            # Get the live view scaler crop
            metadata = Camera.cam.capture_metadata()
            srvCam.serverConfig.scalerCropLiveView = metadata["ScalerCrop"]
            while True:
                #logger.debug("Thread %s: Camera.frames - Receiving camera stream", get_ident())
                with output.condition:
                    #logger.debug("Thread %s: Camera.frames - waiting", get_ident())
                    output.condition.wait()
                    #logger.debug("Thread %s: Camera.frames - waiting done", get_ident())
                    frame = output.frame
                    l = len(frame)
                #logger.debug("Thread %s: Camera.frames - got frame with length %s", get_ident(), l)
                yield frame
        except Exception as e:
            logger.error("Thread %s: Camera.frames - Exception: %s", get_ident(), e)
            raise()

    @staticmethod
    def takeImage(filename: str, keepExclusive:bool=False):
        """ Takes a photo with the specified file name and returns the path

            filename:       file name for the photo
            keepExclusive:  If True, keep the exclusive mode
                            This can be used for example if a jpg photo shall be taken
                            before a video is recorded
        """
        logger.debug("Thread %s: Camera.takeImage - filename: %s keepExclusive: %s", get_ident(), filename, keepExclusive)
        fp = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        
        logger.debug("Thread %s: Camera.takeImage Requesting camera for photoConfig", get_ident())
        exclusive = Camera.ctrl.requestCameraForConfig(cfg.photoConfig)
        logger.debug("Thread %s: Camera.takeImage Got camera for photoConfig exclusive: %s", get_ident(), exclusive)

        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera.takeImage - controls applied", get_ident())
        
        request = Camera.cam.capture_request()
        prgLogger.debug("request = picam2.capture_request()")
        logger.debug("Thread %s: Camera.takeImage: Request started", get_ident())
        fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filename
        request.save(cfg.photoConfig.stream, fp)
        prgLogger.debug("request.save(\"%s\", \"%s\")", cfg.photoConfig.stream, sc.prgOutputPath + "/" + filename)
        sc.displayFile = filename
        sc.displayPhoto = sc.cameraPhotoSubPath + "/" + filename
        sc.isDisplayHidden = False
        logger.debug("Thread %s: Camera.takeImage: Image saved as %s", get_ident(), fp)
        metadata = request.get_metadata()
        prgLogger.debug("metadata = request.get_metadata()")
        sc.displayMeta = {"Camera": sc.activeCameraInfo}
        sc.displayMeta.update(metadata)
        sc.displayMetaFirst = 0
        if len(metadata) < 11:
            sc._displayMetaLast = 999
        else:
            sc.displayMetaLast = 10
        sc.displayHistogram = None
        logger.debug("Thread %s: Camera.takeImage: Image metedata captured", get_ident())
        request.release()
        prgLogger.debug("request.release()")
        logger.debug("Thread %s: Camera.takeImage: Request released", get_ident())
        
        if not keepExclusive:
            Camera.ctrl.restoreLivestream(exclusive)
        return fp

    @staticmethod
    def takeRawImage(filenameRaw: str, filename: str):
        """ Takes a photo as well as a raw image with the specified file names 
            and returns the path for the raw photo
            filenameRaw: file name for the raw image
            filename:    file name for the photo   
        """
        logger.debug("Thread %s: Camera.takeRawImage", get_ident())
        fpr = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        
        logger.debug("Thread %s: Camera.takeRawImage Requesting camera for rawConfig", get_ident())
        exclusive = Camera.ctrl.requestCameraForConfig(cfg.rawConfig, cfg.photoConfig)
        logger.debug("Thread %s: Camera.takeRawImage Got camera for rawConfig exclusive: %s", get_ident(), exclusive)
        
        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera.takeRawImage: controls applied", get_ident())

        request = Camera.cam.capture_request()
        prgLogger.debug("request = picam2.capture_request()")
        logger.debug("Thread %s: Camera.takeRawImage: Request started", get_ident())
        fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filename
        request.save("main", fp)
        prgLogger.debug("request.save(\"main\", \"%s\")", sc.prgOutputPath + "/" + filename)
        fpr = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filenameRaw
        request.save_dng(fpr)
        prgLogger.debug("request.save_dng(\"%s\")", fpr)
        sc.displayFile = filenameRaw
        sc.displayPhoto = sc.cameraPhotoSubPath + "/" + filename
        sc.isDisplayHidden = False
        logger.debug("Thread %s: Camera.takeRawImage: Raw Image saved as %s", get_ident(), fpr)
        metadata = request.get_metadata()
        prgLogger.debug("metadata = request.get_metadata()")
        sc.displayMeta = {"Camera": sc.activeCameraInfo}
        sc.displayMeta.update(metadata)
        sc.displayMetaFirst = 0
        if len(metadata) < 11:
            sc._displayMetaLast = 999
        else:
            sc.displayMetaLast = 10
        sc.displayHistogram = None
        logger.debug("Thread %s: Camera.takeRawImage: Raw Image metedata captured", get_ident())
        request.release()
        prgLogger.debug("request.release()")
        logger.debug("Thread %s: Camera.takeRawImage: Request released", get_ident())

        Camera.ctrl.restoreLivestream(exclusive)
        return fpr
    
    @staticmethod
    def _videoThread():
        logger.debug("Thread %s: Camera._videoThread", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        
        logger.debug("Thread %s: Camera._videoThread - Requesting camera for videoConfig", get_ident())
        exclusive = Camera.ctrl.requestCameraForConfig(cfg.videoConfig)
        logger.debug("Thread %s: Camera._videoThread - Got camera for videoConfig exclusive: %s", get_ident(), exclusive)
        
        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera._videoThread - controls applied", get_ident())

        sc.checkMicrophone()

        encoder = H264Encoder(10000000)
        prgLogger.debug("encoder = H264Encoder(10000000)")
        output = Camera.videoOutput
        prgLogger.debug("output=\"%s\"", Camera.prgVideoOutput)
        if output.lower().endswith(".mp4"):
            if sc.recordAudio == False:
                encoder.output = FfmpegOutput(output, audio=False)
                prgLogger.debug("encoder.output = FfmpegOutput(output, audio=False)")
            else:
                encoder.output = FfmpegOutput(output, audio=True, audio_sync=sc.audioSync)
                prgLogger.debug("encoder.output = FfmpegOutput(output, audio=True, audio_sync=%s)", sc.audioSync)
            logger.debug("Thread %s: Camera._videoThread - mp4 Video output to %s", get_ident(), output)
        else:
            encoder.output = FileOutput(output)
            prgLogger.debug("encoder.output = FileOutput(output)")
            logger.debug("Thread %s: Camera._videoThread - h264 Video output to %s", get_ident(), output)
        try:
            Camera.cam.start_encoder(encoder, name=cfg.videoConfig.stream)
            prgLogger.debug("picam2.start_encoder(encoder, name=\"%s\")", cfg.videoConfig.stream)
            prgLogger.debug("time.sleep(videoDuration)")
            Camera.ctrl.registerEncoder(Camera.ENCODER_VIDEO, encoder)
            logger.debug("Thread %s: Camera._videoThread - Encoder started", get_ident())
            while Camera.stopVideoRequested == False:
                time.sleep(0.1)
            logger.debug("Thread %s: Camera._videoThread - stop video requested", get_ident())
            Camera.ctrl.stopEncoder(Camera.ENCODER_VIDEO)
            logger.debug("Thread %s: Camera._videoThread - encoder stopped", get_ident())
            Camera.stopVideoRequested = False
        except ProcessLookupError:
            logger.debug("Thread %s: Camera._videoThread - Encoder could not be started (requested resolution too high)", get_ident())
            Camera.liveViewDeactivated = False
        except RuntimeError:
            logger.debug("Thread %s: Camera._videoThread - Encoder could not be started (not enough memory for requested resolution)", get_ident())
            Camera.liveViewDeactivated = False
            
        Camera.videoThread = None
        logger.debug("Thread %s: Camera._videoThread - videoThread terminated", get_ident())

        Camera.ctrl.restoreLivestream(exclusive)

    @staticmethod
    def recordVideo(filenameVid: str, filename: str):
        """Record a video in an own thread"""
        logger.debug("Thread %s: Camera.recordVideo. filename=%s", get_ident(), filename)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        # First take a normal photo as placeholder
        Camera.takeImage(filename, keepExclusive=True)
        sc.displayFile = filenameVid
        
        # Configure output for video file
        output = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filenameVid
        prgoutput = sc.prgOutputPath + "/" + filenameVid
        
        if Camera.videoThread is None:
            Camera.videoOutput = output
            Camera.prgVideoOutput = prgoutput
            logger.debug("Thread %s: Camera.recordVideo - Starting new videoThread", get_ident())
            Camera.videoThread = threading.Thread(target=Camera._videoThread, daemon=True)
            Camera.videoThread.start()
            logger.debug("Thread %s: Camera.recordVideo - videoThread started", get_ident())
        return output

    @staticmethod
    def stopVideoRecording():
        """stops the video recording"""
        logger.debug("Thread %s: Camera.stopVideoRecording", get_ident())
        Camera.stopVideoRequested = True
        cnt = 0
        while Camera.videoThread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 500:
                raise TimeoutError("Video thread did not stop within 5 sec")
        logger.debug("Thread %s: Camera.stopVideoRecording: Thread has stopped", get_ident())
        
    @staticmethod
    def isVideoRecording() -> bool:
        return Camera.videoThread is not None

    @staticmethod
    def getLensPosition() -> float:
        metadata = Camera.cam.capture_metadata()
        if "LensPosition" in metadata:
            return metadata["LensPosition"]
        else:
            return 0.0

    @staticmethod
    def getMetaData() -> dict:
        return Camera.cam.capture_metadata()
    
    @staticmethod
    def _photoSeriesThread():
        logger.debug("Thread %s: Camera._photoSeriesThread", get_ident())
        ser = Camera.photoSeries
        cfg = CameraCfg()
        sc = cfg.serverConfig
        
        logger.debug("Thread %s: Camera._photoSeriesThread Requesting camera for photo series of type %s", get_ident(), ser.type)
        if ser.type == "jpg":
            exclusive = Camera.ctrl.requestCameraForConfig(cfg.photoConfig)
        else:
            exclusive = Camera.ctrl.requestCameraForConfig(cfg.rawConfig, cfg.photoConfig)
        logger.debug("Thread %s: Camera._photoSeriesThread Got camera for photo series exclusive: %s", get_ident(), exclusive)

        sc.isPhotoSeriesRecording = True

        exceptCtrl = None
        exceptValue = None
        exceptValueRaw = None
        # Special handling for exposure series
        if ser.isExposureSeries:
            if sc.useHistograms:
                import cv2
                import numpy as np
                from matplotlib import pyplot as plt
            if ser.isExpGainFix:
                exceptCtrl = "ExposureTime"
                exceptValue = ser.expTimeStart
                if ser.expTimeStep == 0:
                    expFact = 2
                elif ser.expTimeStep == 1:
                    expFact = 2 ** (1.0 / 3)
                elif ser.expTimeStep == 2:
                    expFact = 4
                else:
                    expFact = 2
            else:
                exceptCtrl = "AnalogueGain"
                exceptValue = ser.expGainStart
                if ser.expGainStep == 0:
                    expFact = 2
                elif ser.expGainStep == 1:
                    expFact = 2 ** (1.0 / 3)
                elif ser.expGainStep == 2:
                    expFact = 4
                else:
                    expFact = 2
            if ser.curShots:
                if ser.curShots > 1:
                    n = 0
                    while n < ser.curShots:
                        n += 1
                        exceptValue = exceptValue * expFact
                    logger.debug("Thread %s: Camera._photoSeriesThread - Exposure Series for %s: Restart after %s shots", get_ident(), exceptCtrl, ser.curShots)                    
            logger.debug("Thread %s: Camera._photoSeriesThread - Exposure Series for %s: %s Factor: %s", get_ident(), exceptCtrl, exceptValue, expFact)

        # Special handling for focus series
        if ser.isFocusStackingSeries:
            exceptCtrl = "LensPosition"
            exceptValueRaw = ser.focalDistStart
            exceptValue = 1.0 / exceptValueRaw
            if ser.curShots:
                if ser.curShots > 1:
                    exceptValueRaw = ser.focalDistStart + (ser.curShots - 1) * ser.focalDistStep
                    exceptValue = 1.0 / exceptValueRaw
                    logger.debug("Thread %s: Camera._photoSeriesThread - Focus Series: Restart after %s shots", get_ident(), ser.curShots)                    
            logger.debug("Thread %s: Camera._photoSeriesThread - Focus Series for %s: %s (focal dist: %s, interval: %s)", get_ident(), exceptCtrl, exceptValue, exceptValueRaw, ser.focalDistStep)
        
        photoseriesCtrls = Camera.applyControls(Camera.ctrl.configuration, exceptCtrl, exceptValue)
        logger.debug("Thread %s: Camera._photoSeriesThread - selected controls applied", get_ident())

        lastTime = None
        stop = False
        while not stop:
            nextTime = ser.nextTime(lastTime)
            nextPhoto = ser.nextPhoto
            logger.debug("Thread %s: Camera._photoSeriesThread - nextPhoto: %s nextTime %s", get_ident(), nextPhoto, str(nextTime))
            if nextPhoto == "" or nextTime is None:
                stop = True
            else:
                curTime = datetime.datetime.now()
                timedif = nextTime - curTime
                timedifSec = timedif.total_seconds()
                logger.debug("Thread %s: Camera._photoSeriesThread - Seconds to wait: %s", get_ident(), timedifSec)
                while timedifSec > 2.0:
                    time.sleep(2.0)
                    curTime = datetime.datetime.now()
                    timedif = nextTime - curTime
                    timedifSec = timedif.total_seconds()
                    if Camera.stopPhotoSeriesRequested:
                        stop = True
                        break
                if stop == False and timedifSec > 0.0:
                    time.sleep(timedifSec)
            if Camera.stopPhotoSeriesRequested:
                logger.debug("Thread %s: Camera._photoSeriesThread - Stop requested", get_ident())
                stop = True
            if not stop:
                logger.debug("Thread %s: Camera._photoSeriesThread - Preparing request", get_ident())
                request = Camera.cam.capture_request()
                prgLogger.debug("request = picam2.capture_request()")
                fpjpg = ser.path + "/" + nextPhoto + ".jpg"
                fpraw = ser.path + "/" + nextPhoto + ".dng"
                lastTime = datetime.datetime.now()
                request.save("main", fpjpg)
                prgLogger.debug("request.save(\"main\", \"%s\")", sc.prgOutputPath + "/" + nextPhoto + ".jpg")
                if ser.type == "raw+jpg":
                    request.save_dng(fpraw)
                    prgLogger.debug("request.save_dng(\"%s\")", sc.prgOutputPath + "/" + nextPhoto + ".dng")
                metadata = request.get_metadata()
                prgLogger.debug("request.get_metadata()")
                request.release()
                prgLogger.debug("request.release()")
                logger.debug("Thread %s: Camera._photoSeriesThread - Request released", get_ident())
                ser.logPhoto(nextPhoto, lastTime, metadata)
                
                # Draw histogram
                if ser.isExposureSeries \
                and sc.useHistograms:
                    dest = ser.histogramPath + "/" + nextPhoto + ".jpg"
                    plt.figure()    
                    img = cv2.imread(fpjpg)
                    color = ('b','g','r')
                    for i,col in enumerate(color):
                        histr = cv2.calcHist([img],[i],None,[256],[0,256])
                        plt.plot(histr,color = col)
                        plt.xlim([0,256])
                    plt.savefig(dest)
                    logger.debug("Thread %s: Camera._photoSeriesThread - histogram created: %s", get_ident(), dest)

                # For exposure series apply controls
                if ser.isExposureSeries:
                    ser.logCamCfgCtrl(nextPhoto, Camera.ctrl.configuration.make_dict(), photoseriesCtrls.make_dict())
                    if not stop:
                        exceptValue = expFact * exceptValue
                        logger.debug("Thread %s: Camera._photoSeriesThread - Exposure Series for %s: %s", get_ident(), exceptCtrl, exceptValue)
                        photoseriesCtrls = Camera.applyControls(Camera.ctrl.configuration, exceptCtrl, exceptValue)
                        logger.debug("Thread %s: Camera._photoSeriesThread - selected controls applied", get_ident())

                # For focus series apply controls
                if ser.isFocusStackingSeries:
                    ser.logCamCfgCtrl(nextPhoto, Camera.ctrl.configuration.make_dict(), photoseriesCtrls.make_dict())
                    if not stop:
                        exceptValueRaw = exceptValueRaw + ser.focalDistStep
                        exceptValue = 1.0 / exceptValueRaw
                        logger.debug("Thread %s: Camera._photoSeriesThread - Focus Series for %s: %s (focal dist: %s)", get_ident(), exceptCtrl, exceptValue, exceptValueRaw)
                        photoseriesCtrls = Camera.applyControls(Camera.ctrl.configuration, exceptCtrl, exceptValue)
                        logger.debug("Thread %s: Camera._photoSeriesThread - selected controls applied", get_ident())
            
        Camera.photoSeriesThread = None
        Camera.stopPhotoSeriesRequested = False
        sc.isPhotoSeriesRecording = False
        Camera.ctrl.restoreLivestream(exclusive)
        logger.debug("Thread %s: Camera._photoSeriesThread - photoSeriesThread terminated", get_ident())

    @staticmethod
    def startPhotoSeries(ser: Series):
        """Run photoseries in an own thread"""
        logger.debug("Thread %s: startPhotoSeries - series=%s", get_ident(), ser.name)
        
        if Camera.photoSeriesThread is None:
            logger.debug("Thread %s: startPhotoSeries - Starting new photoSeriesThread", get_ident())
            Camera.photoSeries = ser
            Camera.photoSeriesThread = threading.Thread(target=Camera._photoSeriesThread, daemon=True)
            Camera.photoSeriesThread.start()
            logger.debug("Thread %s: startPhotoSeries - photoSeriesThread started", get_ident())

    @staticmethod
    def stopPhotoSeries():
        """stops the photo series"""
        logger.debug("Thread %s: stopPhotoSeries", get_ident())
        Camera.stopPhotoSeriesRequested = True
        cnt = 0
        while Camera.photoSeriesThread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 500:
                raise TimeoutError("Photoseries thread did not stop within 5 sec")
        logger.debug("Thread %s: stopPhotoSeries: Thread has stopped", get_ident())
