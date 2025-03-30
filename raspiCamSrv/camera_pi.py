import io
import time
import datetime
import threading
from _thread import get_ident
from raspiCamSrv.camCfg import CameraInfo, CameraCfg, SensorMode, CameraConfig, TuningConfig
from raspiCamSrv.photoseriesCfg import Series
from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls
from libcamera import Transform, Size, ColorSpace, controls
from picamera2.encoders import JpegEncoder, MJPEGEncoder
from picamera2.outputs import FileOutput, FfmpegOutput, CircularOutput
from picamera2.encoders import H264Encoder
from threading import Condition, Lock
import copy
import os
from pathlib import Path
import logging
import gc
# Try to import SensorConfiguration, which is missing in Bullseye Picamera2 distributions
try:
    from picamera2.configuration import SensorConfiguration
    useSensorConfiguration = True
except ImportError:
    useSensorConfiguration = False

logger = logging.getLogger(__name__)

prgLogger = logging.getLogger("pc2_prg")

class CameraStopError(RuntimeError):
    pass

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
    def __init__(self):
        logger.debug("Thread %s: CameraController.__init__", get_ident())
        if not useSensorConfiguration:
            logger.info("Could not import SensorConfiguration from picamera2.configuration. Bypassing sensor configuration")
        self._activeCfg:CameraConfiguration = None
        self._requestedCfg:CameraConfiguration = CameraConfiguration()
        self._activeEncoders = {}
        logger.debug("Thread %s: cfg: %s", get_ident(), self._requestedCfg)

    @property
    def configuration(self) -> CameraConfiguration:
        return self._requestedCfg

    def requestCameraForConfig(self, cam:Picamera2, camNum, cfg:CameraConfig, cfgPhoto:CameraConfig=None, forLiveStream:bool=False, forActiveCamera=True):
        """ Request camera start for a specific configuration
        
            Parameters:
            cam      Camera
            camNum   Camera number
            cfg      Configuration for which camera is requested
                     If None, request start for the active configuration
            cfgPhoto Photo configuration. To be provided when cfg is a raw photo configuration
            forLiveStream:  The request is for the Live Stream -> don't deactivete Live Stream
            forActiveCamera: Whether the request is for the active camera
        
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
        cam, started = self.requestStart(cam, camNum, forActiveCamera)
        if started:
            logger.debug("Thread %s: CameraController.requestCameraForConfig - camera started", get_ident())
        else:
            logger.debug("Thread %s: CameraController.requestCameraForConfig: Camara stop required", get_ident())
            if not forLiveStream:
                Camera.liveViewDeactivated = True
                logger.debug("Thread %s: CameraController.requestCameraForConfig - Live stream deactivated", get_ident())
            Camera.stopLiveStream()
            logger.debug("Thread %s: CameraController.requestCameraForConfig: Live stream stopped", get_ident())
            cam, stopped = self.requestStop(cam)
            if stopped:
                cam, started = Camera.ctrl.requestStart(cam, camNum, forActiveCamera)
                if started:
                    logger.debug("Thread %s: CameraController.requestCameraForConfig - camera started", get_ident())
                else:
                    logger.error("Thread %s: CameraController.requestCameraForConfig - camera could not be started", get_ident())
                    raise RuntimeError("CameraController.requestCameraForConfig - Camera could not be started")
            else:
                logger.error("Thread %s: CameraController.requestCameraForConfig - camera did not stop", get_ident())
                raise RuntimeError("CameraController.requestCameraForConfig - Camera did not stop")
            exclusive = True
        return cam, exclusive
    
    def restoreLivestream(self, cam, exclusive: bool):
        """ Restart the live stream after exclusive camera use by other task
        """
        logger.debug("Thread %s: CameraController.restoreLivestream - exclusive: %s", get_ident(), exclusive)
        if exclusive:
            logger.debug("Thread %s: CameraController.restoreLivestream - Need to stop camera and restart live stream", get_ident())
            cam, stopped = self.requestStop(cam)
            if not stopped:
                logger.error("Thread %s: CameraController.restoreLivestream - camera did not stop", get_ident())
                raise RuntimeError("CameraController.restoreLivestream - Camera did not stop")
            Camera.liveViewDeactivated = False
            logger.debug("Thread %s: CameraController.restoreLivestream - Live stream activated", get_ident())
            Camera.startLiveStream()
            logger.debug("Thread %s: CameraController.restoreLivestream: Live stream started", get_ident())
        else:
            logger.debug("Thread %s: CameraController.restoreLivestream - Restart live stream not required", get_ident())
        return cam
    
    def requestStart(self, cam, camNum, forActiveCamera=True):
        """ Request to start the camera
        
            If the camera is not yet started, it is configured and started
            
            forActiveCamera: Whether the request is for the active camera
            Return:
            - True  if the camera was started
                    or if the camera had been started before with the same configuration
            - False if the camera was already started or if an exception occurs during start
        """
        logger.debug("Thread %s: CameraController.requestStart - _cam.started: %s", get_ident(), cam.started)
        res = False
        if cam.started == False:
            try:
                if cam.is_open == False:
                    cfg = CameraCfg()
                    if forActiveCamera == True:
                        tc = cfg.tuningConfig
                    else:
                        strc = cfg.streamingCfg
                        camNumStr = str(camNum)
                        if camNumStr in strc:
                            scfg = strc[camNumStr]
                            if "tuningconfig" in scfg:
                                tc = scfg["tuningconfig"]
                            else:
                                tc = TuningConfig()
                        else:
                            tc = TuningConfig()
                    if tc.loadTuningFile == False:
                        cam = Picamera2(camNum)
                        prgLogger.debug("picam2 = Picamera2(%s)", camNum)
                    else:
                        tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                        logger.debug("Thread %s: CameraController.requestStart - Tuning file loaded: File=%s Folder=%s", get_ident(), tc.tuningFile, tc.tuningFolder)
                        cam = Picamera2(camNum, tuning=tuning)
                        logger.debug("Thread %s: CameraController.requestStart - Initialized camera %s with tuning", get_ident(), camNum)
                        prgLogger.debug("tuning = Picamera2.load_tuning_file(%s, %s)", tc.tuningFile, tc.tuningFolder)
                        prgLogger.debug("picam2 = Picamera2(%s, tuning=tuning)", camNum)
                self._activeCfg = self.copyConfig(self._requestedCfg)
                logger.debug("Thread %s: CameraController.requestStart - activeCfg b: %s", get_ident(), self._activeCfg)
                wrkCfg = self.copyConfig(self._activeCfg)
                cam.configure(wrkCfg)
                logger.debug("Thread %s: CameraController.requestStart - activeCfg a: %s", get_ident(), self._activeCfg)
                if prgLogger.level == logging.DEBUG:
                    self.codeGenConfig(self._activeCfg)
                    prgLogger.debug("picam2.configure(ccfg)")
                logger.debug("Thread %s: CameraController.requestStart - Camera configured", get_ident())
                cam.start(show_preview=False)
                prgLogger.debug("picam2.start(show_preview=False)")
                logger.debug("Thread %s: CameraController.requestStart - Camera started", get_ident())
                res = True
                # let camera warm up
                time.sleep(1.5)
                prgLogger.debug("time.sleep(1.5)")
            except RuntimeError as e:
                logger.error("Thread %s: CameraController.requestStart - Error starting camera: %s", get_ident(), e)
        else:
            isIdentical, dif = self.compareConfig(self._requestedCfg, self._activeCfg)
            if isIdentical:
                logger.debug("Thread %s: Camera was already started with same configuration.", get_ident())
                res = True
            else:
                logger.debug("Thread %s: Camera was already started, but with different configuration. Difference is: %s", get_ident(), dif)
            
        logger.debug("Thread %s: CameraController.requestStart: %s", get_ident(), res)
        return cam, res
    
    def requestStop(self, cam, close=False):
        """ Request to stop the camera
        
            If the camera is started,
            - stop the active encoders, if any
            - stop the camera
            - if close: close the camera
            Return:
            - True  if the camera was stopped / closed
                    or if the camera was not started
            - False if the camera could not be stopped
        """
        logger.debug("Thread %s: CameraController.requestStop", get_ident())
        res = False
        try:
            if cam.started == True:
                #First stop encoders
                logger.debug("Thread %s: CameraController.requestStop - Stopping %s encoders", get_ident(), len(self._activeEncoders))
                while len(self._activeEncoders) > 0:
                    task, encoder = self._activeEncoders.popitem()
                    cam.stop_encoder(encoder)
                    encoder = None
                    prgLogger.debug("picam2.stop_encoder(encoder)")
                    logger.debug("Thread %s: CameraController.requestStop - Stopped Encoder for %s", get_ident(), task)
                #Then stop the camera
                logger.debug("Thread %s: CameraController.requestStop - Stopping camera", get_ident())
                cam.stop()
                prgLogger.debug("picam2.stop()")
                cnt = 0
                while cam.started == True:
                    time.sleep(0.01)
                    cnt += 1
                    if cnt > 200:
                        logger.error("Thread %s: CameraController.requestStop - Camera did not stop", get_ident())
                        raise TimeoutError("CameraController.requestStop: Camera did not stop within 2 sec")
                if cnt < 200:
                    logger.debug("Thread %s: CameraController.requestStop - Camera stopped", get_ident())
                    res = True
            else:
                res = True
            
        except TimeoutError:
            raise
        except Exception as e:
            logger.error("Thread %s: CameraController.requestStop - error: %s", get_ident(), e)
            raise

        if close == True:
            try:
                if cam.is_open == True:
                    logger.debug("Thread %s: CameraController.requestStop - About to close camera", get_ident())
                    prgLogger.debug("picam2.close()")
                    cam.close()
                    logger.debug("Thread %s: CameraController.requestStop - Camera closed", get_ident())
            except Exception as e:
                logger.debug("Thread %s: CameraController.requestStop - Ignoring error while closing camera: %s", get_ident(), e)
            gc.collect()
            prgLogger.debug("gc.collect()")
            logger.debug("Thread %s: CameraController.requestStop - Garbage collection completed", get_ident())

        logger.debug("Thread %s: CameraController.requestStop: %s", get_ident(), res)
        return cam, res

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
        if useSensorConfiguration:
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
            if cfgPhoto:
                if cfgRef.main:
                    if cfgRef.main.size != cfgPhoto.stream_size:
                        configChange = True
                        configChangeReason += "main.size,"
                    if cfgRef.main.format != cfgPhoto.format:
                        configChange = True
                        configChangeReason += "main.format,"
                else:
                    if not test:
                        mstream = StreamConfiguration()
                        mstream.size = cfgPhoto.stream_size
                        mstream.format = cfgPhoto.format
                        mstream.stride = None
                        mstream.framesize = None
                        cfgRef.main = mstream

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
            
        if useSensorConfiguration:
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
        logger.debug("Thread %s: CameraController.copyConfig cfg(in) : %s", get_ident(), cfg.__dict__)
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
            
        if useSensorConfiguration:
            if cfg.sensor:
                ccfg.sensor = SensorConfiguration()
                ccfg.sensor.output_size = copy.copy(cfg.sensor.output_size)
                ccfg.sensor.bit_depth = cfg.sensor.bit_depth
            else:
                ccfg.sensor = None

        if cfg.main:
            ccfg.main = StreamConfiguration()
            ccfg.main.size = copy.copy(cfg.main.size)
            ccfg.main.format = cfg.main.format
            ccfg.main.stride = cfg.main.stride
            ccfg.main.framesize = cfg.main.framesize
        else:
            ccfg.main = None

        if cfg.lores:
            ccfg.lores = StreamConfiguration()
            ccfg.lores.size = copy.copy(cfg.lores.size)
            ccfg.lores.format = cfg.lores.format
            ccfg.lores.stride = cfg.lores.stride
            ccfg.lores.framesize = cfg.lores.framesize
        else:
            ccfg.lores = None

        if cfg.raw:
            ccfg.raw = StreamConfiguration()
            ccfg.raw.size = copy.copy(cfg.raw.size)
            ccfg.raw.format = cfg.raw.format
            ccfg.raw.stride = cfg.raw.stride
            ccfg.raw.framesize = cfg.raw.framesize
        else:
            ccfg.raw = None
        logger.debug("Thread %s: CameraController.copyConfig cfg(out): %s", get_ident(), ccfg.__dict__)
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

        if useSensorConfiguration:
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
        logger.debug("Thread %s: CameraController.clearConfig", get_ident())
        self._requestedCfg = CameraConfiguration()
        
    def registerEncoder(self, task:str, encoder):
        """ Register an encoder which needs to be stopped when stopping the camera
        """
        logger.debug("Thread %s: CameraController.registerEncoder: %s", get_ident(), encoder)
        self._activeEncoders[task] = encoder
        
    def stopEncoder(self, cam, task:str):
        """ Stop an encoder for a specific task
        """
        logger.debug("Thread %s: CameraController.stopEncoder: %s", get_ident(), task)
        if task in self._activeEncoders:
            encoder = self._activeEncoders[task]
            cam.stop_encoder(encoder)
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
        ident = get_ident()
        if ident in self.events:
            self.events[get_ident()][0].clear()
        #logger.debug("Thread %s: CameraEvent.clear - Flag set to False -> blocking.", get_ident())

class Camera():
    logger.debug("Thread %s: Camera - setting class variables", get_ident())
    _instance = None
    ENCODER_LIVESTREAM = "LIVESTREAM"
    ENCODER_VIDEO = "VIDEO"
    ENCODER_PHOTOSERIES = "PHOTOSERIES"
    
    cam: Picamera2 = None
    cam2: Picamera2 = None
    camNum = -1
    camNum2 = -1
    ctrl:CameraController = None
    ctrl2:CameraController = None
    videoOutput = None
    prgVideoOutput = None
    photoSeries:Series = None
    
    thread = None               # background thread that reads frames from camera
    thread2 = None              # background thread for second camera
    liveViewDeactivated = False
    videoThread = None
    photoSeriesThread = None
    frame = None                    # current frame is stored here by background thread
    frame2 = None                   # current frame for second camera
    last_access = 0                 # time of last client access to the camera
    last_access2 = 0                # time of last client access for second camera
    stopRequested = False           # Request to stop the background thread
    stopRequested2 = False          # Request to stop the background thread for second camera
    stopVideoRequested = False      # Request to stop the video thread
    videoDuration = 0               # Planned duration of video recording in sec
    stopPhotoSeriesRequested = False  # Request to stop the photoseries thread
    resetScalerCropRequested = False
    event = CameraEvent()
    event2 = None
    
    #Callbacks
    when_photo_taken = None
    when_recording_starts = None
    when_recording_stops = None
    when_streaming_1_starts = None
    when_streaming_1_stops = None
    when_streaming_2_starts = None
    when_streaming_2_stops = None
    

    def __new__(cls):
        logger.debug("Thread %s: Camera.__new__", get_ident())
        if cls._instance is None:
            logger.debug("Thread %s: Camera.__new__ - Instantiating Camera Class", get_ident())
            cls._instance = super(Camera, cls).__new__(cls)
            cls.initCamera()
        else:
            if cls.cam is None:
                cls.initCamera()
            else:
                CameraCfg().serverConfig.error = None
        return cls._instance
    
    @classmethod
    def initCamera(cls):
        """ Instantiate the camera
        """
        logger.debug("Thread %s: Camera.initCamera - Instantiating Camera Class", get_ident())
        
        prgLogger.debug("from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls")
        prgLogger.debug("from libcamera import Transform, Size, ColorSpace, controls")
        prgLogger.debug("from picamera2.encoders import JpegEncoder, MJPEGEncoder")
        if useSensorConfiguration:
            prgLogger.debug("from picamera2.configuration import SensorConfiguration")
        prgLogger.debug("from picamera2.outputs import FileOutput, FfmpegOutput")
        prgLogger.debug("from picamera2.encoders import H264Encoder")
        prgLogger.debug("import time")
        prgLogger.debug("import os")
        prgLogger.debug("import gc")
        prgLogger.debug("Picamera2.set_logging(Picamera2.ERROR)")
        prgLogger.debug('os.environ["LIBCAMERA_LOG_LEVELS"] = "*:3"')
        prgLogger.debug("videoDuration = 10")
        
        cfg = CameraCfg()
        sc = cfg.serverConfig
        sc.error = None
        # Before all, load the global camera info to get the installed cameras and the active cam
        activeCam = cls.getActiveCamera()
        
        if cls.cam is None:
            logger.debug("Thread %s: Camera.initCamera: Instantiating camera %s", get_ident(), activeCam)
            try:
                tc = cfg.tuningConfig
                if tc.loadTuningFile == False:
                    cls.cam = Picamera2(activeCam)
                    prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                else:
                    tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                    cls.cam = Picamera2(activeCam, tuning=tuning)
                    logger.debug("Thread %s: Camera.initCamera - Initialized camera %s with tuning file %s", get_ident(), activeCam, tc.tuningFilePath)
                    prgLogger.debug("tuning = Picamera2.load_tuning_file(%s, %s)", tc.tuningFile, tc.tuningFolder)
                    prgLogger.debug("picam2 = Picamera2(%s, tuning=tuning)", activeCam)
                cls.camNum = activeCam
                cls.ctrl = CameraController()
            except RuntimeError as e:
                logger.error("Thread %s: Camera.initCamera - Error %s", get_ident(), e)
                sc.error = "Error while initializing camera: " + str(e)
                sc.error2 = "Probably another process is using the camera."
                sc.errorSource = "Picamera2"
        else:
            if activeCam != Camera.camNum:
                try:
                    logger.debug("Thread %s: Camera.initCamera: About to switch camera from %s to %s", get_ident(), Camera.camNum, activeCam)
                    cls.stopCameraSystem()
                    tc = cfg.tuningConfig
                    if tc.loadTuningFile == False:
                        cls.cam = Picamera2(activeCam)
                        prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                    else:
                        tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                        cls.cam = Picamera2(activeCam, tuning=tuning)
                        logger.debug("Thread %s: Camera.initCamera - Initialized camera %s with tuning file %s", get_ident(), activeCam, tc.tuningFilePath)
                        prgLogger.debug("tuning = Picamera2.load_tuning_file(%s, %s)", tc.tuningFile, tc.tuningFolder)
                        prgLogger.debug("picam2 = Picamera2(%s, tuning=tuning)", activeCam)
                    cls.camNum = activeCam
                    cls.ctrl = CameraController()
                    logger.debug("Thread %s: Camera.initCamera: Switch camera to %s successful", get_ident(), activeCam)
                    # Force refresh of camera properties
                    cfg.cameraProperties.model=None
                    cfg.sensorModes = []
                    cfg.rawFormats = []
                    logger.debug("Thread %s: Camera.initCamera: Camera-specific configs were reset", get_ident())
                except RuntimeError as e:
                    logger.error("Thread %s: Camera.initCamera - Error %s", get_ident(), e)
                    sc.error = "Error while initializing camera: " + str(e)
                    sc.error2 = "Probably another process is using the camera."
                    sc.errorSource = "Picamera2"
                except Exception as e:
                    logger.error("Thread %s: Camera.initCamera - Error %s", get_ident(), e)
                    sc.error = "Error while initializing camera: " + str(e)
                    sc.errorSource = "Picamera2"
            else:
                logger.debug("Thread %s: Camera.initCamera: Camera was already instantiated", get_ident())
        if not sc.error:
            cls.loadCameraSpecifics()
            cls.setSecondCamera()

        if sc.isPhotoSeriesRecording == False \
        and sc.isVideoRecording == False \
        and sc.isLiveStream == False:
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        if sc.isLiveStream2 == False:
            if Camera.cam2:
                Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)

    @classmethod
    def switchCamera(cls):
        """ Switch the camera
        """
        logger.debug("Thread %s: Camera.switchCamera", get_ident())
        
        logger.debug("Thread %s: Camera.switchCamera - stopping Live Stream", get_ident())
        cls.stopLiveStream()
        logger.debug("Thread %s: Camera.switchCamera - Live Stream stopped", get_ident())
        if cls.cam2:
            cls.stopLiveStream2()
            logger.debug("Thread %s: Camera.switchCamera - Live Stream2 stopped", get_ident())
            
        time.sleep(1)

        activeCam = Camera.getActiveCamera()
        if Camera.cam is None:
            logger.debug("Thread %s: Camera.switchCamera: Camera instantiated: %s", get_ident(), activeCam)
            cfg = CameraCfg()
            tc = cfg.tuningConfig
            if tc.loadTuningFile == False:
                cls.cam = Picamera2(activeCam)
                prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
            else:
                tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                cls.cam = Picamera2(activeCam, tuning=tuning)
                logger.debug("Thread %s: Camera.switchCamera - Initialized camera %s with tuning file %s", get_ident(), activeCam, tc.tuningFilePath)
                prgLogger.debug("tuning = Picamera2.load_tuning_file(%s, %s)", tc.tuningFile, tc.tuningFolder)
                prgLogger.debug("picam2 = Picamera2(%s, tuning=tuning)", activeCam)
            Camera.camNum = activeCam
            Camera.ctrl = CameraController()
        else:
            if activeCam != Camera.camNum:
                logger.debug("Thread %s: Camera.switchCamera: About to switch camera from %s to %s", get_ident(), Camera.camNum, activeCam)
                Camera.stopCameraSystem()
                cfg = CameraCfg()
                tc = cfg.tuningConfig
                if tc.loadTuningFile == False:
                    cls.cam = Picamera2(activeCam)
                    prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                else:
                    tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                    cls.cam = Picamera2(activeCam, tuning=tuning)
                    logger.debug("Thread %s: Camera.switchCamera - Initialized camera %s with tuning file %s", get_ident(), activeCam, tc.tuningFilePath)
                    prgLogger.debug("tuning = Picamera2.load_tuning_file(%s, %s)", tc.tuningFile, tc.tuningFolder)
                    prgLogger.debug("picam2 = Picamera2(%s, tuning=tuning)", activeCam)
                Camera.camNum = activeCam
                Camera.ctrl = CameraController()
                logger.debug("Thread %s: Camera.switchCamera: Switch camera to %s successful", get_ident(), activeCam)
                # Force refresh of camera properties
                CameraCfg().cameraProperties.model=None
                CameraCfg().sensorModes = []
                CameraCfg().rawFormats = []
                logger.debug("Thread %s: Camera.switchCamera: Camera-specific configs were reset", get_ident())
            else:
                logger.debug("Thread %s: Camera.switchCamera: Camera was already instantiated", get_ident())

        time.sleep(1)

        cls.loadCameraSpecifics()
        cls.setSecondCamera()
        
        # Restore streaming config, if available
        if cls.cam2:
            cls.restoreLiveViewFromStreamingConfig() 

        logger.debug("Thread %s: Camera.switchCamera - starting Live Stream", get_ident())
        cls.startLiveStream()
        logger.debug("Thread %s: Camera.switchCamera - Live Stream started", get_ident())
        
        logger.debug("Thread %s: Camera.switchCamera - second camera set", get_ident())
        if cls.cam2:
            cls.startLiveStream2()
            logger.debug("Thread %s: Camera.switchCamera - Live Stream 2 started", get_ident())

    @classmethod
    def startLiveStream(cls):
        """ Start thread for live stream
        """
        logger.debug("Thread %s: Camera.startLiveStream", get_ident())
        if not CameraCfg().serverConfig.error:
            if Camera.liveViewDeactivated:
                logger.debug("Thread %s: Not starting Live View thread. Live View deactivated", get_ident())
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
                    if not CameraCfg().serverConfig.error:
                        CameraCfg().serverConfig.isLiveStream = True
                else:
                    logger.debug("Thread %s: Camera.startLiveStream - Thread exists", get_ident())
                    if not Camera.thread.is_alive:
                        logger.debug("Thread %s: Camera.startLiveStream - Thread is not alive", get_ident())
                        Camera.thread = threading.Thread(target=cls._thread)
                        Camera.thread.start()
                        logger.debug("Thread %s: Camera.startLiveStream - Thread started", get_ident())

    @classmethod
    def startLiveStream2(cls):
        """ Start thread for live stream
        """
        logger.debug("Thread %s: Camera.startLiveStream2", get_ident())
        if not CameraCfg().serverConfig.errorc2:
            if cls.cam2:
                if Camera.thread2 is None:
                    logger.debug("Thread %s: Camera.startLiveStream2: Starting new thread", get_ident())
                    Camera.last_access2 = time.time()

                    # start background frame thread
                    Camera.thread2 = threading.Thread(target=cls._thread2)
                    Camera.thread2.start()
                    logger.debug("Thread %s: Camera.startLiveStream2 - Thread started", get_ident())

                    # wait until first frame is available
                    logger.debug("Thread %s: Camera.startLiveStream2 - waiting for frame", get_ident())
                    Camera.event2.wait()
                    if not CameraCfg().serverConfig.errorc2:
                        CameraCfg().serverConfig.isLiveStream2 = True
                else:
                    logger.debug("Thread %s: Camera.startLiveStream2 - Thread exists", get_ident())
                    if not Camera.thread2.is_alive:
                        logger.debug("Thread %s: Camera.startLiveStream2 - Thread is not alive", get_ident())
                        Camera.thread2 = threading.Thread(target=cls._thread2)
                        Camera.thread2.start()
                        logger.debug("Thread %s: Camera.startLiveStream2 - Thread started", get_ident())

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
            Camera.ctrl.stopEncoder(Camera.cam, Camera.ENCODER_LIVESTREAM)
            CameraCfg().serverConfig.isLiveStream = False
        else:
            logger.debug("Thread %s: Camera.stopLiveStream: Thread was not started", get_ident())
            CameraCfg().serverConfig.isLiveStream = False

    @classmethod
    def stopLiveStream2(cls):
        """ Stop thread for live stream 2
        """
        logger.debug("Thread %s: Camera.stopLiveStream2", get_ident())
        if Camera.cam2:
            if not Camera.thread2 is None:
                logger.debug("Thread %s: Camera.stopLiveStream2 - stopping live stream thread", get_ident())
                Camera.stopRequested2 = True
                cnt = 0
                while Camera.thread2:
                    time.sleep(0.01)
                    cnt += 1
                    if cnt > 200:
                        # Assume thread dead
                        Camera.thread2 = None
                        logger.debug("Thread %s: Camera.stopLiveStream2: Thread assumed dead", get_ident())
                        break
                        #raise TimeoutError("Background thread did not stop within 2 sec")
                if cnt < 200:
                    logger.debug("Thread %s: Camera.stopLiveStream2: Thread has stopped", get_ident())
                Camera.ctrl2.stopEncoder(Camera.cam2, Camera.ENCODER_LIVESTREAM)
                CameraCfg().serverConfig.isLiveStream2 = False
            else:
                logger.debug("Thread %s: Camera.stopLiveStream2: Thread was not started", get_ident())
                CameraCfg().serverConfig.isLiveStream2 = False
    
    @staticmethod
    def restartLiveStream():
        logger.debug("Thread %s: Camera.restartLiveStream", get_ident())
        Camera.stopLiveStream()
        time.sleep(0.5)
        logger.debug("Thread %s: Camera.restartLiveStream: Live stream stopped", get_ident())
        Camera.cam, done = Camera.ctrl.requestStop(Camera.cam)
        logger.debug("Thread %s: Camera.restartLiveStream: Camera stopped", get_ident())
        time.sleep(0.5)
        Camera.ctrl.clearConfig()
        logger.debug("Thread %s: Camera.restartLiveStream: Config cleared", get_ident())
        Camera.startLiveStream()
        logger.debug("Thread %s: Camera.restartLiveStream: Live stream started", get_ident())
    
    @staticmethod
    def restartLiveStream2():
        logger.debug("Thread %s: Camera.restartLiveStream2", get_ident())
        Camera.stopLiveStream2()
        logger.debug("Thread %s: Camera.restartLiveStream2: Live stream stopped", get_ident())
        Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2)
        logger.debug("Thread %s: Camera.restartLiveStream2: Camera stopped", get_ident())
        Camera.ctrl2.clearConfig()
        logger.debug("Thread %s: Camera.restartLiveStream2: Config cleared", get_ident())
        Camera.startLiveStream2()
        logger.debug("Thread %s: Camera.restartLiveStream2: Live stream started", get_ident())

    def getLiveViewImageForMotionDetection(self):
        """ Capture and return a buffer
        """
        cfg = CameraCfg()
        if cfg.triggerConfig.motionDetectAlgo == 1:
            buf = Camera.cam.capture_buffer(cfg.liveViewConfig.stream)
            (w, h) = cfg.liveViewConfig.stream_size
            buf = buf[:w * h].reshape(h, w)
            return buf
        else:
            return Camera.cam.capture_array(cfg.liveViewConfig.stream)

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

    def get_frame2(self):
        """Return the current camera 2 frame."""
        #logger.debug("Thread %s: Camera.get_frame2", get_ident())
        if Camera.cam2:
            Camera.last_access2 = time.time()

            # wait for a signal from the camera thread
            #logger.debug("Thread %s: Camera.get_frame2 - waiting for frame", get_ident())
            Camera.event2.wait()
            #logger.debug("Thread %s: Camera.get_frame2 - continue", get_ident())
            Camera.event2.clear()

            #logger.debug("Thread %s: Returning frame2", get_ident())
            return Camera.frame2
        else:
            return None

    def get_photoFrame(self):
        """Return the current camera frame."""
        logger.debug("Thread %s: Camera.get_photoFrame", get_ident())
        Camera.last_access = time.time()

        # wait for a signal from the camera thread
        logger.debug("Thread %s: Camera.get_photoFrame - waiting for frame", get_ident())
        Camera.event.wait()
        logger.debug("Thread %s: Camera.get_photoFrame - continue", get_ident())
        Camera.event.clear()

        logger.debug("Thread %s: Camera.get_photoFrame - Returning frame", get_ident())
        return Camera.frame

    def get_photoFrame2(self):
        """Return the current camera 2 frame."""
        logger.debug("Thread %s: Camera.get_photoFrame2", get_ident())
        if Camera.cam2:
            Camera.last_access2 = time.time()

            # wait for a signal from the camera thread
            logger.debug("Thread %s: Camera.get_photoFrame2 - waiting for frame", get_ident())
            Camera.event2.wait()
            logger.debug("Thread %s: Camera.get_photoFrame - continue", get_ident())
            Camera.event2.clear()

            logger.debug("Thread %s: Camera.get_photoFrame - Returning frame", get_ident())
            return Camera.frame2
        else:
            return None
        
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
                    sc.activeCameraModel = cfgCam.model
                break
        logger.debug("Thread %s: Camera.getActiveCamera - Active camera:%s - activeCamOK:%s", get_ident(), activeCam, activeCamOK)
        # If config for active camera is not in the list, or if it is a USB cam, 
        # set it to the first non-USB camera
        if activeCamOK == False:
            for cfgCam in cfg.cameras:
                if cfgCam.isUsb == False:
                    sc.activeCamera = cfgCam.num
                    sc.activeCameraInfo = "Camera " + str(cfgCam.num) + " (" + cfgCam.model + ")"
                    sc.activeCameraModel = cfgCam.model
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
            if "UnitCellSize" in camPprops:
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
            
            if cfgCtrls.include_scalerCrop == False:
                cfgCtrls.scalerCrop = (0, 0, camPprops["PixelArraySize"][0], camPprops["PixelArraySize"][1])
                # This must be updated after the camera has been started
                Camera.resetScalerCropRequested = True
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
            logger.debug("Thread %s: Camera.loadCameraSpecifics: %s sensor modes found", get_ident(), len(cfg.sensorModes))
            logger.debug("Thread %s: Camera.loadCameraSpecifics: %s raw formats found", get_ident(), len(cfg.rawFormats))
            
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
                # For Pi < 5 set video and photo resolution to lowest value
                if cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 1") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 2") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 3") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4"):
                    cfg.videoConfig.sensor_mode = 0
                    cfg.videoConfig.stream_size = cfgSensorModes[0].size
                    cfg.photoConfig.sensor_mode = 0
                    cfg.photoConfig.stream_size = cfgSensorModes[0].size
                else:
                    cfg.videoConfig.sensor_mode = maxMode
                    cfg.videoConfig.stream_size = cfgSensorModes[maxModei].size
    
    @classmethod
    def setSecondCamera(cls):
        """Set the second camera
        """
        logger.debug("Thread %s: Camera.setSecondCamera", get_ident())
        cls.camNum2 = None
        cls.cam2 = None
        cfg = CameraCfg()
        sc = cfg.serverConfig
        sc.errorc2 = None
        camNum2 = None
        for cfgCam in cfg.cameras:
            if cfgCam.isUsb == False:
                if cfgCam.num != cls.camNum:
                    camNum2 = cfgCam.num
                    break
        logger.debug("Thread %s: Camera.setSecondCamera - found second camera: %s", get_ident(), camNum2)
        if not camNum2 is None:
            try:
                cls.camNum2 = camNum2
                cfg = CameraCfg()
                strc = cfg.streamingCfg
                camNum2Str = str(camNum2)
                if camNum2Str in strc:
                    scfg = strc[camNum2Str]
                    if "tuningconfig" in scfg:
                        tc = scfg["tuningconfig"]
                        if tc.loadTuningFile == False:
                            cls.cam2 = Picamera2(cls.camNum2)
                        else:
                            tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                            cls.cam2 = Picamera2(cls.camNum2, tuning=tuning)
                            logger.debug("Thread %s: Camera.setSecondCamera - Initialized camera %s with tuning file %s", get_ident(), cls.camNum2, tc.tuningFilePath)
                    else:
                        cls.cam2 = Picamera2(cls.camNum2)
                else:
                    cls.cam2 = Picamera2(cls.camNum2)
                cls.ctrl2 = CameraController()
                cls.event2 = CameraEvent()
                logger.debug("Thread %s: Camera.setSecondCamera - second camera initialized %s", get_ident(), cls.camNum2)
                cfg.serverConfig.isLiveStream2 = False
            except RuntimeError as e:
                logger.error("Thread %s: Camera.setSecondCamera - Error %s", get_ident(), e)
                sc.errorc2 = "Error while initializing camera: " + str(e)
                sc.errorc22 = "Probably another process is using the camera."
                sc.errorc2Source = "Picamera2"
            except Exception as e:
                logger.error("Thread %s: Camera.setSecondCamera - Error %s", get_ident(), e)
                sc.errorc2 = "Error while initializing camera: " + str(e)
                sc.errorc2Source = "Picamera2"
            
        cls.setStreamingConfigs()
        logger.debug("Thread %s: Camera.setSecondCamera - second camera set to %s", get_ident(), cls.camNum2)
    
    @classmethod
    def setStreamingConfigs(cls):
        """Set the configuration for streaming which will be used for the second camera
        """
        logger.debug("Thread %s: Camera.setStreamingConfigs", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        strc = cfg.streamingCfg
        logger.debug("Thread %s: Camera.setStreamingConfigs - current streamingCfg: %s", get_ident(), strc)

        # For active camera
        cn = str(sc.activeCamera)
        if not cn in strc:
            scfg = {}
            scfg["camerainfo"] = copy.copy(sc.activeCameraInfo)
            scfg["hasfocus"] = cfg.cameraProperties.hasFocus
            scfg["tuningconfig"] = copy.deepcopy(cfg.tuningConfig)
            scfg["liveconfig"] = copy.deepcopy(cfg.liveViewConfig)
            scfg["videoconfig"] = copy.deepcopy(cfg.videoConfig)
            scfg["controls"] = copy.deepcopy(cfg.controls)
            strc[cn] = scfg
            logger.debug("Thread %s: Camera.setStreamingConfigs - created  entry for active camera %s", get_ident(), cn)
        # For second camera
        if cls.cam2:
            cn = str(cls.camNum2)
            if not cn in strc:
                camPprops = cls.cam2.camera_properties
                hasFocus = "AfMode" in cls.cam2.camera_controls
                pixelArraySize = copy.copy(camPprops["PixelArraySize"])
                sensorModes = copy.copy(cls.cam2.sensor_modes)
                maxMode = len(sensorModes) - 1
                liveViewConfig = CameraConfig()
                liveViewConfig.id = "LIVE"
                liveViewConfig.use_case = "Live view"
                liveViewConfig.stream = "lores"
                liveViewConfig.buffer_count = 6
                liveViewConfig.encode = "main"
                liveViewConfig.controls["FrameDurationLimits"] = (33333, 33333)
                if liveViewConfig.stream_size is None:
                    sizeWidth = 640
                    sizeHeight =  int(sizeWidth * pixelArraySize[1] / pixelArraySize[0])
                    if (sizeHeight % 2) != 0:
                        sizeHeight += 1
                    liveViewConfig.stream_size = (sizeWidth, sizeHeight)
                    liveViewConfig.stream_size_align = False
                    if sensorModes[0]["size"][0] == sizeWidth \
                    and sensorModes[0]["size"][1] == sizeHeight:
                        liveViewConfig.sensor_mode = "0"
                    else:
                        liveViewConfig.sensor_mode = "custom"

                videoConfig = CameraConfig()
                videoConfig.id = "VIDO"
                videoConfig.use_case = "Video"
                videoConfig.buffer_count = 6
                videoConfig.encode = "main"
                videoConfig.controls["FrameDurationLimits"] = (33333, 33333)

                if cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 1") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 2") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 3") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4"):
                    videoConfig.sensor_mode = 0
                    videoConfig.stream_size = sensorModes[0]["size"]
                    videoConfig.buffer_count = 2
                    liveViewConfig.buffer_count = 2
                else:
                    videoConfig.sensor_mode = str(maxMode)
                    videoConfig.stream_size = sensorModes[maxMode]["size"]

                scfg = {}
                model = ""
                for cfgCam in cfg.cameras:
                    if cfgCam.num == cls.camNum2:
                        model = cfgCam.model
                        break
                scfg["camerainfo"] = "Camera " + cn + " (" + model + ")"
                scfg["hasfocus"] = hasFocus
                scfg["tuningconfig"] = TuningConfig()
                scfg["liveconfig"] = liveViewConfig
                scfg["videoconfig"] = videoConfig
                scfg["controls"] = copy.deepcopy(cfg.controls)
                strc[cn] = scfg
                logger.debug("Thread %s: Camera.setStreamingConfigs - created  entry for second camera %s", get_ident(), cn)
    
    @classmethod
    def restoreLiveViewFromStreamingConfig(cls):
        """Restore live view configuration and controls from a previously saved streaming config
        """
        logger.debug("Thread %s: Camera.restoreLiveViewFromStreamingConfig", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        strc = cfg.streamingCfg

        # For active camera
        cn = str(sc.activeCamera)
        if cn in strc:
            scfg = strc[cn]
            cfg.liveViewConfig = copy.deepcopy(scfg["liveconfig"])
            cfg.controls = copy.deepcopy(scfg["controls"])
            logger.debug("Thread %s: Camera.restoreLiveViewFromStreamingConfig - restored live view config and controls from streaming config %s", get_ident(), cn)
    
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
    def applyControls(camCfg: CameraConfig, exceptCtrl=None, exceptValue = None, toCam2 = None):
        """ Apply the currently selected camera controls
            camCfg      : Configuration from which controls shall be taken with priority
            exceptCtrl  : Exception control. Optionally, one exceptional control can be specified
                          If specified, the exceptValue will replace the value fom CameraCfg().controls
                          Currently supported:
                          - ExposureTime
                          - AnalogueGain
                          - FocalDistance -> LensPosition = 1 / FocalDistance
            toCam2      : If true, controls are set for the second camera with control data from streamingCfg
        """
        logger.debug("Thread %s: Camera.applyControls - toCam2: %s", get_ident(), toCam2)

        logger.debug("Thread %s: Camera.applyControls - camCfg.controls=%s", get_ident(), camCfg.controls)
        cfg = CameraCfg()
        if toCam2 is None:
            cfgCtrls = cfg.controls
        else:
            cfgCtrls = cfg.streamingCfg[str(Camera.camNum2)]["controls"]
        logger.debug("Thread %s: Camera.applyControls - cfgCtrls=%s", get_ident(), cfgCtrls.__dict__)

        # Initialize controls dict with controls included in configuration
        #ctrls = copy.deepcopy(camCfg.controls)
        ctrls = {}
        logger.debug("Thread %s: Camera.applyControls - ctrls=%s", get_ident(), ctrls)
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
        if toCam2 is None:
            hasFocus = cfg.cameraProperties.hasFocus
        else:
            hasFocus = cfg.streamingCfg[str(Camera.camNum2)]["hasfocus"]
        if hasFocus:
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
        logger.debug("Thread %s: Camera.applyControls - ctrls=%s", get_ident(), ctrls)
        if toCam2 is None:
            camCtrls = Controls(Camera.cam)
            prgLogger.debug("camCtrls = Controls(picam2)")
            prgLogger.debug("ctrls = %s", ctrls)
            camCtrls.set_controls(ctrls)
            prgLogger.debug("camCtrls.set_controls(ctrls)")
            Camera.cam.controls = camCtrls
            #Camera.cam.controls.set_controls(ctrls)
            prgLogger.debug("picam2.controls = camCtrls")
            logger.debug("Thread %s: Camera.applyControls - id(Camera)=%s id(Camera.cam)=%s id(Camera.cam.controls)=%s", get_ident(), id(Camera), id(Camera.cam), id(Camera.cam.controls))
            logger.debug("Thread %s: Camera.applyControls - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)
        else:
            camCtrls = Controls(Camera.cam2)
            camCtrls.set_controls(ctrls)
            Camera.cam2.controls = camCtrls
            logger.debug("Thread %s: Camera.applyControls - Camera.cam2.controls=%s", get_ident(), Camera.cam2.controls)
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
        Camera.videoDuration = 0
        
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
        
        Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        
        if Camera.cam2:
            Camera.stopRequested2 = True
            if Camera.thread2:
                cnt = 0
                while Camera.thread2:
                    time.sleep(0.01)
                    cnt += 1
                    if cnt > 200:
                        break
                if Camera.thread2:
                    logger.debug("Thread %s: Camera.stopCameraSystem: Live view thread 2 did not stop within 2 sec", get_ident())
                else:
                    logger.debug("Thread %s: Camera.stopCameraSystem: Live view thread 2 successfully stopped", get_ident())
            else:
                logger.debug("Thread %s: Camera.stopCameraSystem: Live view thread 2 was not active", get_ident())
            Camera.stopRequested2 = False
            Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)

    @classmethod
    def _thread(cls):
        """Camera background thread."""
        logger.debug("Thread %s: Camera._thread", get_ident())
        frames_iterator = None

        if Camera().when_streaming_1_starts:
            Camera().when_streaming_1_starts()

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
        except Exception as e:
            logger.error("Thread %s: Camera._thread - Exception: %s", get_ident(), e)
            if frames_iterator:
                frames_iterator.close()
            Camera.event.set()
            Camera.event.clear()
            CameraCfg().serverConfig.error = "Error in live view: " + str(e)
            CameraCfg().serverConfig.error2 = "Probably, a different camera configuration can solve the problem."
            CameraCfg().serverConfig.errorSource = "Camera._thread"
                
        Camera.thread = None
        sc = CameraCfg().serverConfig
        
        closeCam = True
        if sc.isVideoRecording == True \
        or cls.isVideoRecording() == True:
            closeCam = False
            logger.debug("Thread %s: Camera._thread - isVideoRecording -> Camera not closing", get_ident())
        if sc.isPhotoSeriesRecording == True:
            ser = Camera.photoSeries
            if ser:
                if ser.isExposureSeries == True \
                or ser.isFocusStackingSeries == True:
                    closeCam = False
                    logger.debug("Thread %s: Camera._thread - Exposure- or PhotoStack series -> Camera not closing", get_ident())
                else:
                    nextTime = ser.nextTime()
                    curTime = datetime.datetime.now()
                    timedif = nextTime - curTime
                    timedifSec = timedif.total_seconds()
                    if timedifSec < 60:
                        logger.debug("Thread %s: Camera._thread - Photo series next shot within 60 sec -> Camera not closing", get_ident())
                        closeCam = False
        if closeCam == True:
            logger.debug("Thread %s: Camera._thread - Closing camera", get_ident())
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        sc.isLiveStream = False

        if Camera().when_streaming_1_stops:
            Camera().when_streaming_1_stops()

    @classmethod
    def _thread2(cls):
        """Camera background thread 2."""
        logger.debug("Thread %s: Camera._thread2", get_ident())
        frames_iterator = None

        if Camera().when_streaming_2_starts:
            Camera().when_streaming_2_starts()

        try:
            frames_iterator = cls.frames2()
            logger.debug("Thread %s: Camera._thread2 - frames_iterator instantiated", get_ident())
            for frame in frames_iterator:
                Camera.frame2 = frame
                #logger.debug("Thread %s: Camera._thread2 - received frame from camera -> notifying clients", get_ident())
                Camera.event2.set()  # send signal to clients
                time.sleep(0)
                
                # Check whether stop is requested
                if Camera.stopRequested2:
                    frames_iterator.close()
                    Camera.stopRequested2 = False
                    logger.debug("Thread %s: Camera._thread2 - Thread is requested to stop.", get_ident())
                    break

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - Camera.last_access2 > 10:
                    frames_iterator.close()
                    logger.debug("Thread %s: Camera._thread2 - Stopping camera thread due to inactivity.", get_ident())
                    break
        except Exception as e:
            logger.error("Thread %s: Camera._thread2 - Exception: %s", get_ident(), e)
            if frames_iterator:
                frames_iterator.close()
            Camera.event2.set()
            Camera.event2.clear()
            CameraCfg().serverConfig.errorc2 = "Error in camera 2 stream: " + str(e)
            CameraCfg().serverConfig.errorc22 = "Probably, a different camera configuration can solve the problem."
            CameraCfg().serverConfig.errorc2Source = "Camera._thread2"
                
        Camera.thread2 = None
        Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)
        CameraCfg().serverConfig.isLiveStream2 = False

        if Camera().when_streaming_2_stops:
            Camera().when_streaming_2_stops()

    @staticmethod
    def frames():
        logger.debug("Thread %s: Camera.frames", get_ident())
        srvCam = CameraCfg()
        try:
            cc, cr = Camera.ctrl.requestConfig(srvCam.photoConfig)
            if cc:
                #If the request for photoConfig caused a configuration change, restart with a new configuration
                Camera.ctrl.clearConfig()
                Camera.ctrl.requestConfig(srvCam.photoConfig)
            Camera.ctrl.requestConfig(srvCam.rawConfig, cfgPhoto=srvCam.photoConfig)
            Camera.ctrl.requestConfig(srvCam.liveViewConfig)
            Camera.cam, started = Camera.ctrl.requestStart(Camera.cam, Camera.camNum, forActiveCamera=True)
            if not started:
                Camera.cam, excl = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg=None, forLiveStream=True)
            else:
                logger.debug("Thread %s: Camera.frames - camera started", get_ident())

            if Camera.resetScalerCropRequested == True:
                Camera.resetScalerCrop()

            Camera.applyControls(Camera.ctrl.configuration)
            logger.debug("Thread %s: Camera.frames - controls applied", get_ident())
            time.sleep(0.5)
        except Exception as e:
            logger.error("Thread %s: Camera.frames - Exception: %s", get_ident(), e)
            raise

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
            raise

    @staticmethod
    def frames2():
        logger.debug("Thread %s: Camera.frames2", get_ident())
        srvCam = CameraCfg()

        Camera.ctrl2.requestConfig(srvCam.streamingCfg[str(Camera.camNum2)]["videoconfig"])
        Camera.ctrl2.requestConfig(srvCam.streamingCfg[str(Camera.camNum2)]["liveconfig"])

        Camera.cam2, started = Camera.ctrl2.requestStart(Camera.cam2, Camera.camNum2, forActiveCamera=False)
        if not started:
            logger.error("Second camera did not start")
            raise RuntimeError("Second camera did not start")
        else:
            logger.debug("Thread %s: Camera.frames2 - camera started", get_ident())

        Camera.applyControls(Camera.ctrl2.configuration, toCam2=True)
        logger.debug("Thread %s: Camera.frames2 - controls applied", get_ident())
        time.sleep(0.5)

        try:
            output = StreamingOutput()
            encoder = MJPEGEncoder()
            Camera.cam2.start_encoder(encoder, FileOutput(output), name=srvCam.streamingCfg[str(Camera.camNum2)]["liveconfig"].stream)
            Camera.ctrl2.registerEncoder(Camera.ENCODER_LIVESTREAM, encoder)
            logger.debug("Thread %s: Camera.frames2 - encoder started", get_ident())

            # Get the live view scaler crop
            while True:
                #logger.debug("Thread %s: Camera.frames2 - Receiving camera stream", get_ident())
                with output.condition:
                    #logger.debug("Thread %s: Camera.frames2 - waiting", get_ident())
                    output.condition.wait()
                    #logger.debug("Thread %s: Camera.frames2 - waiting done", get_ident())
                    frame = output.frame
                    l = len(frame)
                #logger.debug("Thread %s: Camera.frames2 - got frame with length %s", get_ident(), l)
                yield frame
        except Exception as e:
            logger.error("Thread %s: Camera.frames2 - Exception: %s", get_ident(), e)
            raise

    @staticmethod
    def takeImage(filename: str, keepExclusive:bool=False, noEvents:bool=False):
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

        if noEvents == False:
            logger.debug("Thread %s: Camera.takeImage Checking for callback: when_photo_taken=%s", get_ident(), Camera().when_photo_taken)
            if Camera().when_photo_taken:
                Camera().when_photo_taken()
        try:
            logger.debug("Thread %s: Camera.takeImage Requesting camera for photoConfig", get_ident())
            Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.photoConfig)
            logger.debug("Thread %s: Camera.takeImage Got camera for photoConfig exclusive: %s", get_ident(), exclusive)

            Camera.applyControls(Camera.ctrl.configuration)
            logger.debug("Thread %s: Camera.takeImage - controls applied", get_ident())
            
            logger.debug("Thread %s: Camera.takeImage - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)
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
                Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
                if sc.isPhotoSeriesRecording == False \
                and sc.isVideoRecording == False \
                and sc.isLiveStream == False:
                    Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        except Exception as e:
            logger.error("Thread %s: Camera.takeImage: Error %s", get_ident(), e)
            sc.error = "Phototaking caused error: " + str(e)
            sc.errorSource = "Camera.takeImage"
        return fp
    
    @staticmethod
    def quickPhoto(fp: str) -> tuple:
        """ Take a photo assuming that the camera is started
        """
        logger.debug("Thread %s: Camera.quickPhoto - filename: %s", get_ident(), fp)
        done = False
        err = ""
        cfg = CameraCfg()
        if Camera.cam.started:
            try:
                request = Camera.cam.capture_request()
                request.save(cfg.photoConfig.stream, fp)
                request.release()
                done = True
            except Exception as e:
                err = str(e)
        else:
            err = "Camera not started"
        return (done, err)

    @staticmethod
    def quickVideoStart(fp: str) -> tuple:
        """ Record a video assuming that the camera is started
        """
        logger.debug("Thread %s: Camera.quickVideoStart - filename: %s", get_ident(), fp)
        encoder = None
        done = False
        err = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        if Camera.cam.started:
            try:
                encoder = H264Encoder()
                output = fp
                if output.lower().endswith(".mp4"):
                    if sc.recordAudio == False:
                        encoder.output = FfmpegOutput(output, audio=False)
                    else:
                        encoder.output = FfmpegOutput(output, audio=True, audio_sync=sc.audioSync)
                else:
                    encoder.output = FileOutput(output)
                    
                stream = cfg.videoConfig.stream
                # For Pi Zero take video with liveView (lowres stream)
                # The lower buffer size of lowres is too small for video and we do not want to switch mode
                if cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero") \
                or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4"):
                    stream = cfg.liveViewConfig.stream
                Camera.cam.start_encoder(encoder, name=stream)
                done = True
            except Exception as e:
                logger.error("Thread %s: Camera.quickVideoStart - error when starting encoder: %s", get_ident(), e)
                err = str(e)
        else:
            err = "Camera not started"
        return (done, encoder, err)
    
    @staticmethod
    def quickVideoStop(encoder) -> tuple:
        """ Stop a video recording that the camera is started
        """
        logger.debug("Thread %s: Camera.quickVideoStop", get_ident())
        done = False
        err = ""
        if Camera.cam.started:
            try:
                Camera.cam.stop_encoder(encoder)
                done = True
            except Exception as e:
                logger.error("Thread %s: Camera.quickVideoStop - error when stopping encoder: %s", get_ident(), e)
                err = str(e)
        else:
            err = "Camera not started"
        return (done, err)

    @staticmethod
    def startCircular(buffersizeSec = 5) -> tuple:
        """ Start encoder for circular output
        """
        logger.debug("Thread %s: Camera.startCircular", get_ident())
        encoder = None
        circ = None
        done = False
        err = ""
        cfg = CameraCfg()
        if Camera.cam.started:
            try:
                encoder = H264Encoder()
                sm = cfg.videoConfig.sensor_mode
                if sm == "custom":
                    buffersize = 150
                else:
                    buffersize = cfg.sensorModes[sm].fps * buffersizeSec
                circ = CircularOutput(buffersize=buffersize)
                encoder.output = [circ]
                Camera.cam.encoders = encoder
                Camera.cam.start_encoder(encoder, name=cfg.videoConfig.stream)
                done = True
            except Exception as e:
                logger.error("Thread %s: Camera.startCircular - error when starting encoder: %s", get_ident(), e)
                err = str(e)
        else:
            err = "Camera not started"
        return (done, circ, encoder, err)
    
    @staticmethod
    def stopCircular(encoder) -> tuple:
        """ Stop encoder for circular output
        """
        logger.debug("Thread %s: Camera.stopCircular", get_ident())
        done = False
        err = ""
        if Camera.cam.started:
            try:
                Camera.cam.stop_encoder(encoder)
                done = True
            except Exception as e:
                logger.error("Thread %s: Camera.stopCircular - error when stopping encoder: %s", get_ident(), e)
                err = str(e)
        else:
            err = "Camera not started"
        return (done, err)
    
    @staticmethod
    def recordCircular(circ:CircularOutput, fp: str) -> tuple:
        """ Start recording circular output
        """
        logger.debug("Thread %s: Camera.recordCircular - file: %s", get_ident(), fp)
        done = False
        err = ""
        if Camera.cam.started:
            try:
                circ.fileoutput = fp
                circ.start()
                done = True
            except Exception as e:
                logger.error("Thread %s: Camera.recordCircular - error when starting circular: %s", get_ident(), e)
                err = str(e)
        else:
            err = "Camera not started"
        return (done, err)
    
    @staticmethod
    def stopRecordingCircular(circ:CircularOutput) -> tuple:
        """ Start recording circular output
        """
        logger.debug("Thread %s: Camera.stopRecordingCircular", get_ident())
        done = False
        err = ""
        if Camera.cam.started:
            try:
                circ.stop()
                done = True
            except Exception as e:
                logger.error("Thread %s: Camera.stopRecordingCircular - error when stopping circular: %s", get_ident(), e)
                err = str(e)
        else:
            err = "Camera not started"
        return (done, err)

    @staticmethod
    def takeRawImage(filenameRaw: str, filename: str, noEvents:bool=False):
        """ Takes a photo as well as a raw image with the specified file names 
            and returns the path for the raw photo
            filenameRaw: file name for the raw image
            filename:    file name for the photo   
        """
        logger.debug("Thread %s: Camera.takeRawImage", get_ident())
        fpr = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig

        if noEvents == False:
            logger.debug("Thread %s: Camera.takeImage Checking for callback: when_photo_taken=%s", get_ident(), Camera().when_photo_taken)
            if Camera().when_photo_taken:
                Camera().when_photo_taken()
        
        try:
            logger.debug("Thread %s: Camera.takeRawImage Requesting camera for rawConfig", get_ident())
            Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.rawConfig, cfg.photoConfig)
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

            Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
            if sc.isPhotoSeriesRecording == False \
            and sc.isVideoRecording == False \
            and sc.isLiveStream == False:
                Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        except Exception as e:
            logger.error("Thread %s: Camera.takeRawImage: Error %s", get_ident(), e)
            sc.error = "Taking raw photo caused error: " + str(e)
            sc.errorSource = "Camera.takeRawImage"
        return fpr
    
    @staticmethod
    def _videoThread():
        logger.debug("Thread %s: Camera._videoThread", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        
        logger.debug("Thread %s: Camera._videoThread - Requesting camera for videoConfig", get_ident())
        Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.videoConfig)
        logger.debug("Thread %s: Camera._videoThread - Got camera for videoConfig exclusive: %s", get_ident(), exclusive)
        
        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera._videoThread - controls applied", get_ident())

        sc.checkMicrophone()

        encoder = H264Encoder()
        prgLogger.debug("encoder = H264Encoder()")
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
            videoStart = time.time()
            duration = float(Camera.videoDuration)
            logger.debug("Thread %s: Camera._videoThread - video started at %s, duration is %s", get_ident(), videoStart, duration)
            Camera.cam.start_encoder(encoder, name=cfg.videoConfig.stream)
            prgLogger.debug("picam2.start_encoder(encoder, name=\"%s\")", cfg.videoConfig.stream)
            prgLogger.debug("time.sleep(videoDuration)")
            Camera.ctrl.registerEncoder(Camera.ENCODER_VIDEO, encoder)
            logger.debug("Thread %s: Camera._videoThread - Encoder started", get_ident())
            if duration > 0.0:
                elapsed = time.time() - videoStart
                while elapsed <= duration:
                    if Camera.stopVideoRequested == True:
                        break
                    time.sleep(0.1)
                    elapsed = time.time() - videoStart
                sc.isVideoRecording = False
                sc.isAudioRecording = False
            else:
                while Camera.stopVideoRequested == False:
                    time.sleep(0.1)
            logger.debug("Thread %s: Camera._videoThread - stop video requested", get_ident())
            Camera.ctrl.stopEncoder(Camera.cam, Camera.ENCODER_VIDEO)
            logger.debug("Thread %s: Camera._videoThread - encoder stopped", get_ident())
            Camera.stopVideoRequested = False
            Camera.videoDuration = 0
        except ProcessLookupError as e:
            logger.error("Thread %s: Camera._videoThread - Error: %s", get_ident(), e)
            Camera.liveViewDeactivated = False
            sc.error = "Error in encoder: " + str(e)
            sc.error2 = "Probably, the requested resolution is too high."
            sc.errorSource = "Camera._videoThread"
        except RuntimeError as e:
            logger.error("Thread %s: Camera._videoThread - Error: %s)", get_ident(), e)
            Camera.liveViewDeactivated = False
            sc.error = "Error in encoder: " + str(e)
            sc.error2 = "Probably, there is not sufficient memory for the requested resolution."
            sc.errorSource = "Camera._videoThread"
            logger.debug("Thread %s: Camera._videoThread - sc.error: %s)", get_ident(), sc.error)
        except Exception as e:
            logger.error("Thread %s: Camera._videoThread - Exception: %s", get_ident(), e)
            Camera.liveViewDeactivated = False
            sc.error = "Error in video recording: " + str(e)
            sc.errorSource = "Camera._videoThread"
            
        Camera.videoThread = None
        logger.debug("Thread %s: Camera._videoThread - videoThread terminated", get_ident())

        Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
        logger.debug("Thread %s: Camera._videoThread - sc.error: %s)", get_ident(), sc.error)

        if sc.isPhotoSeriesRecording == False \
        and sc.isLiveStream == False:
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)

    @staticmethod
    def recordVideo(filenameVid: str, filename: str, duration: int = 0, noEvents:bool=False):
        """Record a video in an own thread"""
        logger.debug("Thread %s: Camera.recordVideo. filename=%s, duration=%s", get_ident(), filename, duration)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        # First take a normal photo as placeholder
        Camera.takeImage(filename, keepExclusive=True,noEvents=True)
        sc.displayFile = filenameVid
        
        # Configure output for video file
        output = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filenameVid
        prgoutput = sc.prgOutputPath + "/" + filenameVid
        
        if Camera.videoThread is None:
            Camera.videoOutput = output
            Camera.prgVideoOutput = prgoutput
            Camera.videoDuration = duration
            logger.debug("Thread %s: Camera.recordVideo - Starting new videoThread", get_ident())
            Camera.videoThread = threading.Thread(target=Camera._videoThread, daemon=True)
            Camera.videoThread.start()
            logger.debug("Thread %s: Camera.recordVideo - videoThread started", get_ident())

            if noEvents == False:
                if Camera().when_recording_starts:
                    Camera().when_recording_starts()
        return output

    @staticmethod
    def stopVideoRecording(noEvents:bool=False):
        """stops the video recording"""
        logger.debug("Thread %s: Camera.stopVideoRecording", get_ident())
        Camera.stopVideoRequested = True
        Camera.videoDuration = 0
        cnt = 0
        while Camera.videoThread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 500:
                raise TimeoutError("Video thread did not stop within 5 sec")
        logger.debug("Thread %s: Camera.stopVideoRecording: Thread has stopped", get_ident())

        if noEvents == False:
            if Camera().when_recording_stops:
                Camera().when_recording_stops()
        
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
        exclusive = False
        try:
            if ser.type == "jpg":
                Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.photoConfig)
            else:
                Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.rawConfig, cfg.photoConfig)
            logger.debug("Thread %s: Camera._photoSeriesThread Got camera for photo series exclusive: %s", get_ident(), exclusive)
        except Exception as e:
            logger.error("Thread %s: Camera._photoSeriesThread error: %s", get_ident(), e)
            sc.error = "Error while requesting camera: " + str(e)
            sc.errorSource = "Camera._photoSeriesThread"

        if not sc.error:
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
                curShots, nextPhoto = ser.nextPhoto()
                logger.debug("Thread %s: Camera._photoSeriesThread - nextPhoto: %s nextTime %s", get_ident(), nextPhoto, str(nextTime))
                if nextPhoto == "" or nextTime is None or ser.status == "FINISHED":
                    logger.debug("Thread %s: Camera._photoSeriesThread - Series done: nextPhoto=%s, nextTime=%s, status=%s", get_ident(), nextPhoto, str(nextTime), ser.status)
                    stop = True
                else:
                    curTime = datetime.datetime.now()
                    timedif = nextTime - curTime
                    timedifSec = timedif.total_seconds()
                    logger.debug("Thread %s: Camera._photoSeriesThread - Seconds to wait: %s", get_ident(), timedifSec)

                    camClosed = False
                    if ser.isFocusStackingSeries == False \
                    and ser.isExposureSeries == False:
                        if sc.isVideoRecording == False \
                        and sc.isLiveStream == False:
                            if timedifSec > 60:
                                Camera.cam, camClosed = Camera.ctrl.requestStop(Camera.cam, close=True)

                    while timedifSec > 2.0:
                        time.sleep(2.0)
                        curTime = datetime.datetime.now()
                        timedif = nextTime - curTime
                        timedifSec = timedif.total_seconds()
                        if camClosed:
                            timedifSec -= 2.0
                            
                        if Camera.stopPhotoSeriesRequested:
                            stop = True
                            break
                    if stop == False and timedifSec > 0.0:
                        time.sleep(timedifSec)
                if Camera.stopPhotoSeriesRequested:
                    logger.debug("Thread %s: Camera._photoSeriesThread - Stop requested", get_ident())
                    stop = True
                if not stop:
                    try:
                        if Camera.cam is None:
                            camClosed = True
                        else:
                            if Camera.cam.started == False:
                                camClosed = True
                        if camClosed:
                            logger.debug("Thread %s: Camera._photoSeriesThread - Preparing closed camera", get_ident())
                            if ser.type == "jpg":
                                Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.photoConfig)
                            else:
                                Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(Camera.cam, Camera.camNum, cfg.rawConfig, cfg.photoConfig)
                            logger.debug("Thread %s: Camera._photoSeriesThread Got camera for photo series exclusive: %s", get_ident(), exclusive)
                            photoseriesCtrls = Camera.applyControls(Camera.ctrl.configuration, exceptCtrl, exceptValue)
                            logger.debug("Thread %s: Camera._photoSeriesThread - selected controls applied", get_ident())
                            time.sleep(1)
                            curTime = datetime.datetime.now()
                            timedif = nextTime - curTime
                            timedifSec = timedif.total_seconds()
                            if timedifSec > 0:
                                time.sleep(timedifSec)
                            
                        logger.debug("Thread %s: Camera._photoSeriesThread - Preparing request", get_ident())
                        logger.debug("Thread %s: Camera._photoSeriesThread - id(Camera)=%s id(Camera.cam)=%s id(Camera.cam.controls)=%s", get_ident(), id(Camera), id(Camera.cam), id(Camera.cam.controls))
                        logger.debug("Thread %s: Camera._photoSeriesThread - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)
                        lastTime = datetime.datetime.now()
                        request = Camera.cam.capture_request()
                        logger.debug("Thread %s: Camera._photoSeriesThread - capture_request completed", get_ident())
                        logger.debug("Thread %s: Camera._photoSeriesThread - id(Camera)=%s id(Camera.cam)=%s id(Camera.cam.controls)=%s", get_ident(), id(Camera), id(Camera.cam), id(Camera.cam.controls))
                        logger.debug("Thread %s: Camera._photoSeriesThread - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)
                        prgLogger.debug("request = picam2.capture_request()")
                        fpjpg = ser.path + "/" + nextPhoto + ".jpg"
                        fpraw = ser.path + "/" + nextPhoto + ".dng"
                        request.save("main", fpjpg)
                        prgLogger.debug("request.save(\"main\", \"%s\")", sc.prgOutputPath + "/" + nextPhoto + ".jpg")
                        if ser.type == "raw+jpg":
                            request.save_dng(fpraw)
                            prgLogger.debug("request.save_dng(\"%s\")", sc.prgOutputPath + "/" + nextPhoto + ".dng")
                        metadata = request.get_metadata()
                        prgLogger.debug("metadata = request.get_metadata()")
                        request.release()
                        prgLogger.debug("request.release()")
                        logger.debug("Thread %s: Camera._photoSeriesThread - Request released", get_ident())
                        ser.curShots = curShots
                        ser.logPhoto(nextPhoto, lastTime, metadata)
                    except Exception as e:
                        ser.nextStatus("pause")
                        stop = True
                        logger.error("Thread %s: Camera._photoSeriesThread - Error: %s", get_ident(), e)
                        ser.error = "Error in photoseries: " + str(e)
                        ser.errorSource = "Camera._photoSeriesThread"

                    if not sc.error and not ser.error:
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
        Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
        if sc.isVideoRecording == False \
        and sc.isLiveStream == False:
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
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
                Camera.photoSeriesThread = None
                CameraCfg().serverConfig.isPhotoSeriesRecording = False
                #raise TimeoutError("Photoseries thread did not stop within 5 sec")
                logger.debug("Thread %s: stopPhotoSeries: Thread seams to be dead", get_ident())
            else:
                logger.debug("Thread %s: stopPhotoSeries: Thread has stopped", get_ident())
        Camera.stopPhotoSeriesRequested = False

    @classmethod
    def cameraStatus(cls, camNum) -> str:
        status = ""
        if camNum == cls.camNum:
            if cls.cam.is_open == True:
                status = "open"
                if cls.cam.started == True:
                    status = status + " - started"
                    mode = "unknown"
                    if useSensorConfiguration:
                        sc = cls.cam.camera_config["sensor"]
                        for sm in CameraCfg().sensorModes:
                            if sc["output_size"] == sm.size \
                            and sc["bit_depth"] == sm.bit_depth:
                                mode = str(sm.id)
                    status = status + " - current Sensor Mode: " + mode
                else:
                    status = status + " - stopped"
            else:
                status = "closed"
        if camNum == cls.camNum2:
            if cls.cam2.is_open == True:
                status = "open"
                if cls.cam2.started == True:
                    status = status + " - started"
                else:
                    status = status + " - stopped"
            else:
                status = "closed"
        return status
    
    @classmethod
    def resetScalerCrop(cls):
        logger.debug("Thread %s: Camera.resetScalerCrop", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        cc = cfg.controls
        scInf = cls.cam.camera_controls["ScalerCrop"]
        sc.scalerCropMin = scInf[0]
        sc.scalerCropMax = scInf[1]
        sc.scalerCropDef = scInf[2]
        sc.zoomFactor = 100
        sc.scalerCropLiveView = sc.scalerCropDef
        cc.scalerCrop = sc.scalerCropDef
        cc.include_scalerCrop = False
        cls.resetScalerCropRequested = False
        
