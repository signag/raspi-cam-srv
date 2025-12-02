import io
import time
import datetime
import threading
from _thread import get_ident, allocate_lock
from raspiCamSrv.camCfg import (
    CameraInfo,
    CameraCfg,
    SensorMode,
    CameraConfig,
    TuningConfig,
)
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
import math
import subprocess
from subprocess import CalledProcessError


# Try to import SensorConfiguration, which is missing in Bullseye Picamera2 distributions
try:
    from picamera2.configuration import SensorConfiguration

    useSensorConfiguration = True
except ImportError:
    useSensorConfiguration = False
# Try to import cv2
try:
    import cv2
    cv2Available = True
except ImportError:
    cv2Available = False

logger = logging.getLogger(__name__)

prgLogger = logging.getLogger("pc2_prg")


class CameraStopError(RuntimeError):
    pass

class UsbCameraOpenError(RuntimeError):
    """Exception raised when a USB camera is unexpectedly not open
    
       The reason why the USB camera is found to be not open after it had been opened
       are currently not yet clear.
    """
    # TODO: Clarify under which conditions this exception is raised
    pass

class UsbCameraNoFrameReceivedError(RuntimeError):
    """Exception raised when a USB camera does not deliver frames for 1 second after being opened
    
       The reason is currently not yet clear.
    """
    # TODO: Clarify under which conditions this exception is raised
    pass

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        # logger.debug("Thread %s: StreamingOutput.__init__", get_ident())
        self.frame = None
        self.lock = Lock()
        self.condition = Condition(self.lock)

    def write(self, buf):
        # logger.debug("Thread %s: StreamingOutput.write", get_ident())
        with self.condition:
            self.frame = buf
            # logger.debug("Thread %s: StreamingOutput.write - got buffer of length %s", get_ident(), len(buf))
            self.condition.notify_all()
            # logger.debug("Thread %s: StreamingOutput.write - notification done", get_ident())
        # logger.debug("Thread %s: StreamingOutput.write - write done", get_ident())


class CameraController:
    """The class controls status change actions for the camera"""

    def __init__(self, isUsb: bool = False, usbDev: str = None):
        logger.debug(
            "Thread %s: CameraController.__init__ isUsb: %s", get_ident(), isUsb
        )
        if not useSensorConfiguration:
            logger.info(
                "Could not import SensorConfiguration from picamera2.configuration. Bypassing sensor configuration"
            )
        self._activeCfg: CameraConfiguration = None
        self._requestedCfg: CameraConfiguration = CameraConfiguration()
        self._activeEncoders = {}
        self._isUsb = isUsb
        self._usbDev = usbDev
        logger.debug(
            "Thread %s: CameraController.__init__ isUsb: requestedCfg: %s",
            get_ident(),
            self._requestedCfg,
        )

    @property
    def configuration(self) -> CameraConfiguration:
        return self._requestedCfg

    @property
    def isUsb(self) -> bool:
        return self._isUsb

    @property
    def usbDev(self) -> str:
        return self._usbDev

    def requestCameraForConfig(
        self,
        cam: Picamera2,
        camNum,
        cfg: CameraConfig,
        cfgPhoto: CameraConfig = None,
        forLiveStream: bool = False,
        forActiveCamera=True,
        forceExclusive: bool = False,
    ):
        """Request camera start for a specific configuration

        Parameters:
        cam      Camera
        camNum   Camera number
        isUsb    Whether the camera is a USB camera
        cfg      Configuration for which camera is requested
                 If None, request start for the active configuration
        cfgPhoto Photo configuration. To be provided when cfg is a raw photo configuration
        forLiveStream:  The request is for the Live Stream -> don't deactivate Live Stream
        forActiveCamera: Whether the request is for the active camera
        forceExclusive: Whether the request is for an exclusive camera start

        Return:
        True  if start is exclusive for the requested configuration
        False if the active configuration is used
        """
        if cfg:
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig cfg:        %s",
                get_ident(),
                cfg.__dict__,
            )
        else:
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig cfg:        %s",
                get_ident(),
                cfg,
            )
        if cfgPhoto:
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig - cfgPhoto: %s",
                get_ident(),
                cfgPhoto.__dict__,
            )
        else:
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig - cfgPhoto: %s",
                get_ident(),
                cfgPhoto,
            )
        logger.debug(
            "Thread %s: CameraController.requestCameraForConfig - forLiveStream: %s",
            get_ident(),
            forLiveStream,
        )
        logger.debug(
            "Thread %s: CameraController.requestCameraForConfig - forActiveCamera: %s",
            get_ident(),
            forActiveCamera,
        )
        logger.debug(
            "Thread %s: CameraController.requestCameraForConfig - forceExclusive: %s",
            get_ident(),
            forceExclusive,
        )

        exclusive = False

        if cfg:
            self.requestConfig(cfg, cfgPhoto=cfgPhoto)
        if forceExclusive == False:
            cam, started = self.requestStart(
                cam, camNum, self.isUsb, self.usbDev, forActiveCamera
            )
        else:
            started = False
        if started:
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig - camera started",
                get_ident(),
            )
        else:
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig: Camara stop required",
                get_ident(),
            )
            if not forLiveStream:
                if forActiveCamera == True:
                    Camera.liveViewDeactivated = True
                else:
                    Camera.liveView2Deactivated = True
                logger.debug(
                    "Thread %s: CameraController.requestCameraForConfig - Live stream deactivated",
                    get_ident(),
                )
            if forActiveCamera == True:
                Camera.stopLiveStream()
            else:
                Camera.stopLiveStream2()
            logger.debug(
                "Thread %s: CameraController.requestCameraForConfig: Live stream stopped",
                get_ident(),
            )
            cam, stopped = self.requestStop(cam)
            if stopped:
                if forActiveCamera == True:
                    cam, started = Camera.ctrl.requestStart(
                        cam, camNum, self.isUsb, self.usbDev, forActiveCamera
                    )
                else:
                    cam, started = Camera.ctrl2.requestStart(
                        cam, camNum, self.isUsb, self.usbDev, forActiveCamera
                    )
                if started:
                    logger.debug(
                        "Thread %s: CameraController.requestCameraForConfig - camera started",
                        get_ident(),
                    )
                else:
                    logger.error(
                        "Thread %s: CameraController.requestCameraForConfig - camera could not be started",
                        get_ident(),
                    )
                    raise RuntimeError(
                        "CameraController.requestCameraForConfig - Camera could not be started"
                    )
            else:
                logger.error(
                    "Thread %s: CameraController.requestCameraForConfig - camera did not stop",
                    get_ident(),
                )
                raise RuntimeError(
                    "CameraController.requestCameraForConfig - Camera did not stop"
                )
            exclusive = True
        return cam, exclusive

    def restoreLivestream(self, cam, exclusive: bool):
        """Restart the live stream after exclusive camera use by other task"""
        logger.debug(
            "Thread %s: CameraController.restoreLivestream - exclusive: %s",
            get_ident(),
            exclusive,
        )
        if exclusive:
            logger.debug(
                "Thread %s: CameraController.restoreLivestream - Need to stop camera and restart live stream",
                get_ident(),
            )
            cam, stopped = self.requestStop(cam)
            if not stopped:
                logger.error(
                    "Thread %s: CameraController.restoreLivestream - camera did not stop",
                    get_ident(),
                )
                raise RuntimeError(
                    "CameraController.restoreLivestream - Camera did not stop"
                )
            Camera.liveViewDeactivated = False
            logger.debug(
                "Thread %s: CameraController.restoreLivestream - Live stream activated",
                get_ident(),
            )
            Camera.startLiveStream()
            logger.debug(
                "Thread %s: CameraController.restoreLivestream: Live stream started",
                get_ident(),
            )
        else:
            logger.debug(
                "Thread %s: CameraController.restoreLivestream - Restart live stream not required",
                get_ident(),
            )
        return cam

    def restoreLivestream2(self, cam, exclusive: bool):
        """Restart the live stream 2 after exclusive camera use by other task"""
        logger.debug(
            "Thread %s: CameraController.restoreLivestream2 - exclusive: %s",
            get_ident(),
            exclusive,
        )
        if exclusive:
            logger.debug(
                "Thread %s: CameraController.restoreLivestream2 - Need to stop camera and restart live stream",
                get_ident(),
            )
            cam, stopped = self.requestStop(cam)
            if not stopped:
                logger.error(
                    "Thread %s: CameraController.restoreLivestream2 - camera did not stop",
                    get_ident(),
                )
                raise RuntimeError(
                    "CameraController.restoreLivestream2 - Camera did not stop"
                )
            Camera.liveView2Deactivated = False
            logger.debug(
                "Thread %s: CameraController.restoreLivestream2 - Live stream activated",
                get_ident(),
            )
            Camera.startLiveStream2()
            logger.debug(
                "Thread %s: CameraController.restoreLivestream2: Live stream started",
                get_ident(),
            )
        else:
            logger.debug(
                "Thread %s: CameraController.restoreLivestream2 - Restart live stream not required",
                get_ident(),
            )
        return cam

    def requestStart(
        self, cam, camNum, isUsb=False, camUsbDev=None, forActiveCamera=True
    ):
        """Request to start the camera

        If the camera is not yet started, it is configured and started

        forActiveCamera: Whether the request is for the active camera
        Return:
        - True  if the camera was started
                or if the camera had been started before with the same configuration
        - False if the camera was already started or if an exception occurs during start
        """
        logger.debug(
            "Thread %s: CameraController.requestStart - camNum: %s isUsb: %s camUsbDev: %s",
            get_ident(),
            camNum,
            isUsb,
            camUsbDev,
        )
        res = False
        if isUsb == False:
            logger.debug(
                "Thread %s: CameraController.requestStart - cam.started: %s",
                get_ident(),
                cam.started,
            )
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
                            tuning = Picamera2.load_tuning_file(
                                tc.tuningFile, tc.tuningFolder
                            )
                            logger.debug(
                                "Thread %s: CameraController.requestStart - Tuning file loaded: File=%s Folder=%s",
                                get_ident(),
                                tc.tuningFile,
                                tc.tuningFolder,
                            )
                            cam = Picamera2(camNum, tuning=tuning)
                            logger.debug(
                                "Thread %s: CameraController.requestStart - Initialized camera %s with tuning",
                                get_ident(),
                                camNum,
                            )
                            prgLogger.debug(
                                "tuning = Picamera2.load_tuning_file(%s, %s)",
                                tc.tuningFile,
                                tc.tuningFolder,
                            )
                            prgLogger.debug(
                                "picam2 = Picamera2(%s, tuning=tuning)", camNum
                            )
                    self._activeCfg = self.copyConfig(self._requestedCfg)
                    logger.debug(
                        "Thread %s: CameraController.requestStart - activeCfg b: %s",
                        get_ident(),
                        self._activeCfg,
                    )
                    wrkCfg = self.copyConfig(self._activeCfg)
                    cam.configure(wrkCfg)
                    logger.debug(
                        "Thread %s: CameraController.requestStart - activeCfg a: %s",
                        get_ident(),
                        self._activeCfg,
                    )
                    if self.isUsb == False:
                        if prgLogger.level == logging.DEBUG:
                            self.codeGenConfig(self._activeCfg)
                            prgLogger.debug("picam2.configure(ccfg)")
                    logger.debug(
                        "Thread %s: CameraController.requestStart - Camera configured",
                        get_ident(),
                    )
                    cam.start(show_preview=False)
                    prgLogger.debug("picam2.start(show_preview=False)")
                    logger.debug(
                        "Thread %s: CameraController.requestStart - Camera started",
                        get_ident(),
                    )
                    res = True
                    # let camera warm up
                    time.sleep(1.5)
                    prgLogger.debug("time.sleep(1.5)")
                except Exception as e:
                    logger.error(
                        "Thread %s: CameraController.requestStart - Error starting camera: %s",
                        get_ident(),
                        e,
                    )
                    cfg = CameraCfg()
                    sc = cfg.serverConfig
                    if not sc.error:
                        sc.error = "Error while starting camera: " + str(e)
                        sc.errorSource = "CameraController.requestStart"

            else:
                isIdentical, dif = self.compareConfig(
                    self._requestedCfg, self._activeCfg
                )
                if isIdentical:
                    logger.debug(
                        "Thread %s: CameraController.requestStart - Camera was already started with same configuration.",
                        get_ident(),
                    )
                    res = True
                else:
                    logger.debug(
                        "Thread %s: CameraController.requestStart - Camera was already started, but with different configuration. Difference is: %s",
                        get_ident(),
                        dif,
                    )
        else:
            logger.debug(
                "Thread %s: CameraController.requestStart - cam.isOpened: %s",
                get_ident(),
                cam.isOpened(),
            )
            # For USB cameras, just open the camera if not already opened
            if cam.isOpened() == False:
                cam = cv2.VideoCapture(camUsbDev, cv2.CAP_V4L2)
                if not cam or not cam.isOpened():
                    logger.error(
                        "Thread %s: CameraController.requestStart - Error: USB camera not opened",
                        get_ident(),
                    )
                    sc = cfg.serverConfig
                    sc.error = "Error while initializing camera: USB camera not opened"
                    sc.errorSource = "CV2"
                else:
                    res = True
                    logger.debug(
                        "Thread %s: CameraController.requestStart - USB camera started",
                        get_ident(),
                    )
            else:
                logger.debug(
                    "Thread %s: CameraController.requestStart - USB Camera was already opened.",
                    get_ident(),
                )
                res = True
            if cam.isOpened() == True:
                # Apply configuration
                self._activeCfg = self.copyConfig(self._requestedCfg)
                wrkCfg = self.copyConfig(self._activeCfg)
                fmt = wrkCfg.main.format
                width = wrkCfg.main.size[0]
                height = wrkCfg.main.size[1]
                cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fmt))
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                logger.debug(
                    "Thread %s: CameraController.requestStart - USB Cam started with format: %s, size: %s x %s",
                    get_ident(),
                    fmt,
                    width,
                    height,
                )

        logger.debug("Thread %s: CameraController.requestStart: %s", get_ident(), res)
        return cam, res

    def requestStop(self, cam, close=False):
        """Request to stop the camera

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
        if self.isUsb == False:
            try:
                if cam.started == True:
                    # First stop encoders
                    logger.debug(
                        "Thread %s: CameraController.requestStop - Stopping %s encoders",
                        get_ident(),
                        len(self._activeEncoders),
                    )
                    while len(self._activeEncoders) > 0:
                        task, encoder = self._activeEncoders.popitem()
                        cam.stop_encoder(encoder)
                        encoder = None
                        prgLogger.debug("picam2.stop_encoder(encoder)")
                        logger.debug(
                            "Thread %s: CameraController.requestStop - Stopped Encoder for %s",
                            get_ident(),
                            task,
                        )
                    # Then stop the camera
                    logger.debug(
                        "Thread %s: CameraController.requestStop - Stopping camera",
                        get_ident(),
                    )
                    cam.stop()
                    prgLogger.debug("picam2.stop()")
                    cnt = 0
                    while cam.started == True:
                        time.sleep(0.01)
                        cnt += 1
                        if cnt > 200:
                            logger.error(
                                "Thread %s: CameraController.requestStop - Camera did not stop",
                                get_ident(),
                            )
                            raise TimeoutError(
                                "CameraController.requestStop: Camera did not stop within 2 sec"
                            )
                    if cnt < 200:
                        logger.debug(
                            "Thread %s: CameraController.requestStop - Camera stopped",
                            get_ident(),
                        )
                        res = True
                else:
                    res = True

            except TimeoutError:
                raise
            except Exception as e:
                logger.error(
                    "Thread %s: CameraController.requestStop - error: %s",
                    get_ident(),
                    e,
                )
                raise

            if close == True:
                try:
                    if cam.is_open == True:
                        logger.debug(
                            "Thread %s: CameraController.requestStop - About to close camera",
                            get_ident(),
                        )
                        prgLogger.debug("picam2.close()")
                        cam.close()
                        logger.debug(
                            "Thread %s: CameraController.requestStop - Camera closed",
                            get_ident(),
                        )
                except Exception as e:
                    logger.debug(
                        "Thread %s: CameraController.requestStop - Ignoring error while closing camera: %s",
                        get_ident(),
                        e,
                    )
                gc.collect()
                prgLogger.debug("gc.collect()")
                logger.debug(
                    "Thread %s: CameraController.requestStop - Garbage collection completed",
                    get_ident(),
                )
        else:
            # For USB cameras, just close the camera
            try:
                if cam.isOpened() == True:
                    logger.debug(
                        "Thread %s: CameraController.requestStop - About to close USB camera",
                        get_ident(),
                    )
                    cam.release()
                    logger.debug(
                        "Thread %s: CameraController.requestStop - USB Camera closed",
                        get_ident(),
                    )
                else:
                    logger.debug(
                        "Thread %s: CameraController.requestStop - USB Camera was not opened",
                        get_ident(),
                    )
                res = True
            except Exception as e:
                logger.debug(
                    "Thread %s: CameraController.requestStop - Ignoring error while closing USB camera: %s",
                    get_ident(),
                    e,
                )
            gc.collect()
            logger.debug(
                "Thread %s: CameraController.requestStop - Garbage collection completed",
                get_ident(),
            )
        logger.debug("Thread %s: CameraController.requestStop: %s", get_ident(), res)
        return cam, res

    def requestConfig(
        self, cfg: CameraConfig, test: bool = False, cfgPhoto: CameraConfig = None
    ):
        """Register a new configuration

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
        logger.debug(
            "Thread %s: CameraController.requestConfig - test: %s cfg     : %s",
            get_ident(),
            test,
            cfg.__dict__,
        )
        if cfgPhoto:
            logger.debug(
                "Thread %s: CameraController.requestConfig - test: %s cfgPhoto: %s",
                get_ident(),
                test,
                cfgPhoto.__dict__,
            )
        else:
            logger.debug(
                "Thread %s: CameraController.requestConfig - test: %s cfgPhoto: %s",
                get_ident(),
                test,
                cfgPhoto,
            )

        cfgRef = self._requestedCfg

        configChange = False
        configChangeReason = ""

        if not test:
            if cfgRef.use_case:
                if cfgRef.use_case.find(cfg.use_case) < 0:
                    cfgRef.use_case += "," + cfg.use_case
            else:
                cfgRef.use_case = cfg.use_case

        # Transform of new config must be identical to existing
        if cfgRef.transform:
            if (
                cfgRef.transform.hflip != cfg.transform_hflip
                or cfgRef.transform.vflip != cfg.transform_vflip
            ):
                configChange = True
                configChangeReason += "transform,"
        else:
            if not test:
                cfgRef.transform = Transform(
                    vflip=cfg.transform_vflip, hflip=cfg.transform_hflip
                )

        # For buffer_count, always choose the larger one
        if not test:
            if cfgRef.buffer_count:
                if cfg.buffer_count > cfgRef.buffer_count:
                    cfgRef.buffer_count = cfg.buffer_count
            else:
                cfgRef.buffer_count = cfg.buffer_count

        if self.isUsb == False:
            # Colour space must be identical
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

        # queue must be identical
        if cfgRef.queue:
            if cfgRef.queue != cfg.queue:
                configChange = True
                configChangeReason += "queue,"
        else:
            if not test:
                cfgRef.queue = cfg.queue

        # display must be identical
        if cfgRef.display:
            if cfgRef.display != cfg.display:
                configChange = True
                configChangeReason += "display,"
        else:
            if not test:
                cfgRef.display = cfg.display

        # encode is not used. Always set it to 'main'
        if not test:
            cfgRef.encode = "main"

        # Sensor is not explicitely set in the configuration
        # It will be selected and updated by picamera2 automaticallx
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
                # If cofig change is detected, replace entire configuration
                camCfg = CameraConfiguration()

                camCfg.use_case = cfg.use_case
                camCfg.transform = Transform(
                    vflip=cfg.transform_vflip, hflip=cfg.transform_hflip
                )
                camCfg.buffer_count = cfg.buffer_count
                cosp = cfg.colour_space
                if self.isUsb == False:
                    if cosp == "sYCC":
                        colourSpace = ColorSpace.Sycc()
                    elif cosp == "Smpte170m":
                        colourSpace = ColorSpace.Smpte170m()
                    elif cosp == "Rec709":
                        colourSpace = ColorSpace.Rec709()
                    else:
                        colourSpace = ColorSpace.Sycc()
                    camCfg.colour_space = colourSpace
                else:
                    camCfg.colour_space = cfgRef.colour_space
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
                    raise ValueError(
                        "controls in camera configuration must not be empty"
                    )
                else:
                    camCfg.controls = ctrls
                cfgRef = camCfg

            # Automatically align the stream size, if selected
            if cfg.stream_size_align and cfg.sensor_mode == "custom":
                cfgRef.align()
                if cfg.stream == "main":
                    cfg.stream_size = cfgRef.main.size
                if cfg.stream == "lores":
                    cfg.stream_size = cfgRef.lores.size

        self._requestedCfg = cfgRef
        logger.debug(
            "Thread %s: CameraController.requestConfig - configChange: %s",
            get_ident(),
            configChange,
        )
        logger.debug(
            "Thread %s: CameraController.requestConfig - configChangeReason: %s",
            get_ident(),
            configChangeReason,
        )
        logger.debug(
            "Thread %s: CameraController.requestConfig - cfg: %s",
            get_ident(),
            self._requestedCfg,
        )
        return configChange, configChangeReason

    def codeGenConfig(self, cfg: CameraConfiguration):
        """Generate code for the given configuration"""
        logger.debug(
            "Thread %s: CameraController.codeGenConfig cfg: %s",
            get_ident(),
            cfg.__dict__,
        )
        prgLogger.debug("ccfg = CameraConfiguration()")
        prgLogger.debug('ccfg.use_case = "%s"', cfg.use_case)
        if cfg.encode:
            prgLogger.debug('ccfg.encode = "%s"', cfg.encode)
        else:
            prgLogger.debug("ccfg.encode = None")
        if cfg.display:
            prgLogger.debug('ccfg.display = "%s"', cfg.display)
        else:
            prgLogger.debug("ccfg.display = None")
        prgLogger.debug("ccfg.buffer_count = %s", cfg.buffer_count)
        prgLogger.debug("ccfg.queue = %s", cfg.queue)

        if cfg.transform:
            prgLogger.debug(
                "ccfg.transform = Transform(vflip=%s, hflip=%s)",
                cfg.transform.vflip,
                cfg.transform.hflip,
            )
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
            prgLogger.debug('ccfg.main.format = "%s"', cfg.main.format)
            prgLogger.debug("ccfg.main.stride = %s", cfg.main.stride)
            prgLogger.debug("ccfg.main.framesize = %s", cfg.main.framesize)
        else:
            prgLogger.debug("ccfg.main = None")

        if cfg.lores:
            prgLogger.debug("ccfg.lores = StreamConfiguration()")
            prgLogger.debug("ccfg.lores.size = %s", cfg.lores.size)
            prgLogger.debug('ccfg.lores.format = "%s"', cfg.lores.format)
            prgLogger.debug("ccfg.lores.stride = %s", cfg.lores.stride)
            prgLogger.debug("ccfg.lores.framesize = %s", cfg.lores.framesize)
        else:
            prgLogger.debug("ccfg.lores = None")

        if cfg.raw:
            prgLogger.debug("ccfg.raw = StreamConfiguration()")
            prgLogger.debug("ccfg.raw.size = %s", cfg.raw.size)
            prgLogger.debug('ccfg.raw.format = "%s"', cfg.raw.format)
            prgLogger.debug("ccfg.raw.stride = %s", cfg.raw.stride)
            prgLogger.debug("ccfg.raw.framesize = %s", cfg.raw.framesize)
        else:
            prgLogger.debug("ccfg.raw = None")

    def copyConfig(self, cfg: CameraConfiguration) -> CameraConfiguration:
        """Return a copy of the given configuration"""
        logger.debug(
            "Thread %s: CameraController.copyConfig cfg(in) : %s",
            get_ident(),
            cfg.__dict__,
        )
        ccfg = CameraConfiguration()
        ccfg.use_case = cfg.use_case
        ccfg.encode = cfg.encode
        ccfg.display = cfg.display
        ccfg.buffer_count = cfg.buffer_count
        ccfg.queue = cfg.queue

        if cfg.transform:
            ccfg.transform = Transform(
                vflip=cfg.transform.vflip, hflip=cfg.transform.hflip
            )
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
        logger.debug(
            "Thread %s: CameraController.copyConfig cfg(out): %s",
            get_ident(),
            ccfg.__dict__,
        )
        return ccfg

    def compareConfig(
        self, cfg1: CameraConfiguration, cfg2: CameraConfiguration
    ) -> bool:
        """Check equality of configurations

        Return:
        result (bool):
            True  if configurations are identical
            False if configuration differ
        difference (str): List of differences
        """
        logger.debug(
            "Thread %s: CameraController.compareConfig cfg1: %s",
            get_ident(),
            cfg1.__dict__,
        )
        logger.debug(
            "Thread %s: CameraController.compareConfig cfg2: %s",
            get_ident(),
            cfg2.__dict__,
        )
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
                if (
                    cfg1.transform.hflip != cfg2.transform.hflip
                    or cfg1.transform.vflip != cfg2.transform.vflip
                ):
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
        logger.debug(
            "Thread %s: CameraController.compareConfig res: %s, dif: %s",
            get_ident(),
            res,
            dif,
        )
        return res, dif

    def clearConfig(self):
        """Clear the configuration"""
        logger.debug("Thread %s: CameraController.clearConfig", get_ident())
        self._requestedCfg = CameraConfiguration()

    def registerEncoder(self, task: str, encoder):
        """Register an encoder which needs to be stopped when stopping the camera"""
        logger.debug(
            "Thread %s: CameraController.registerEncoder: %s", get_ident(), encoder
        )
        self._activeEncoders[task] = encoder

    def stopEncoder(self, cam, task: str):
        """Stop an encoder for a specific task"""
        logger.debug("Thread %s: CameraController.stopEncoder: %s", get_ident(), task)
        if task in self._activeEncoders:
            encoder = self._activeEncoders[task]
            cam.stop_encoder(encoder)
            prgLogger.debug("picam2.stop_encoder(encoder)")
            del self._activeEncoders[task]
            logger.debug(
                "Thread %s: CameraController.stopEncoder - Encoder stopped", get_ident()
            )


class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """

    def __init__(self):
        # logger.debug("Thread %s: CameraEvent.__init__", get_ident())
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        # logger.debug("Thread %s: CameraEvent.wait", get_ident())
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
            # logger.debug("Thread %s: CameraEvent.wait - Event ident: %s added to events dict. time:%s", get_ident(), ident, self.events[ident][1])
        # for ident, event in self.events.items():
        # logger.debug("Thread %s: CameraEvent.wait - Event ident: %s Flag: %s Time: %s (Flag False -> blocking)", get_ident(), ident, self.events[ident][0].is_set(), event[1])

        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        # logger.debug("Thread %s: CameraEvent.set", get_ident())
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
                # logger.debug("Thread %s: CameraEvent.set  - Event ident: %s Flag: False -> True (unblock/notify)", get_ident(), ident)
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                # logger.debug("Thread %s: CameraEvent.set  - Event ident: %s Flag: True (Last image not processed).", get_ident(), ident)
                if now - event[1] > 5:
                    # logger.debug("Thread %s: CameraEvent.set  - Event ident: %s  too old; marked for removal.", get_ident(), ident)
                    remove = ident
        if remove:
            del self.events[remove]
            # logger.debug("Thread %s: CameraEvent.set  - Event ident: %s removed.", get_ident(), ident)

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        ident = get_ident()
        if ident in self.events:
            self.events[get_ident()][0].clear()
        # logger.debug("Thread %s: CameraEvent.clear - Flag set to False -> blocking.", get_ident())

    def toDict(self):
        """Convert the event to a dict representation."""
        return {
            "events": {
                ident: {
                    "flag": event[0].is_set(),
                    "time": event[1],
                    "timeHR": datetime.datetime.fromtimestamp(event[1]).strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    ),
                }
                for ident, event in self.events.items()
            }
        }


class Camera:
    logger.debug("Thread %s: Camera - setting class variables", get_ident())
    _instance = None
    ENCODER_LIVESTREAM = "LIVESTREAM"
    ENCODER_VIDEO = "VIDEO"
    ENCODER_PHOTOSERIES = "PHOTOSERIES"

    cam = None
    camIsUsb = False
    camUsbDev = ""
    camNum = -1
    cam2 = None
    cam2IsUsb = False
    cam2UsbDev = ""
    camNum2 = -1
    ctrl: CameraController = None
    ctrl2: CameraController = None
    videoOutput = None
    videoOutput2 = None
    prgVideoOutput = None
    prgVideoOutput2 = None
    photoSeries: Series = None

    thread = None  # background thread that reads frames from camera
    threadLock = allocate_lock()  # lock for stopping the camera thread
    thread2 = None  # background thread for second camera
    thread2Lock = allocate_lock()  # lock for stopping the second camera thread
    threadUsbVideo = None  # background thread that records video from USB camera
    threadUsbVideoLock = allocate_lock()  # lock for stopping the USB video thread
    logUsbFrameApplyControls = False
    logUsbFrame2ApplyControls = False
    liveViewDeactivated = False
    liveView2Deactivated = False
    videoThread = None
    videoThread2 = None
    photoSeriesThread = None
    frame = None  # current frame is stored here by background thread
    frame2 = None  # current frame for second camera
    frameRaw = None  # current raw frame is stored here by background thread
    frame2Raw = None  # current raw frame for second camera
    streamOutput = None  # output for MJPEG streaming for live stream
    stream2Output = None  # output for MJPEG streaming for second camera
    last_access = 0  # time of last client access to the camera
    last_access2 = 0  # time of last client access for second camera
    stopRequested = False  # Request to stop the background thread
    stopRequested2 = False  # Request to stop the background thread for second camera
    stopVideoRequested = False  # Request to stop the video thread
    stopVideoRequested2 = False  # Request to stop the video thread
    stopUsbVideoRequested = False  # Request to stop the video thread
    videoDuration = 0  # Planned duration of video recording in sec
    videoDuration2 = 0  # Planned duration of video recording in sec
    stopPhotoSeriesRequested = False  # Request to stop the photoseries thread
    resetScalerCropRequested = False
    event = CameraEvent()
    event2 = None

    # Callbacks
    when_photo_taken = None
    when_photo_2_taken = None
    when_series_photo_taken = None
    when_recording_starts = None
    when_recording_stops = None
    when_recording_2_starts = None
    when_recording_2_stops = None
    when_streaming_1_starts = None
    when_streaming_1_stops = None
    when_streaming_2_starts = None
    when_streaming_2_stops = None

    def __new__(cls):
        logger.debug("Thread %s: Camera.__new__", get_ident())
        if cls._instance is None:
            logger.debug(
                "Thread %s: Camera.__new__ - Instantiating Camera Class", get_ident()
            )
            cls._instance = super(Camera, cls).__new__(cls)
            cls.cam = None
            cls.camIsUsb = False
            cls.camUsbDev = ""
            cls.camNum = -1
            cls.cam2 = None
            cls.cam2IsUsb = False
            cls.cam2UsbDev = ""
            cls.camNum2 = -1
            cls.ctrl: CameraController = None
            cls.ctrl2: CameraController = None
            cls.videoOutput = None
            cls.videoOutput2 = None
            cls.prgVideoOutput = None
            cls.prgVideoOutput2 = None
            cls.photoSeries: Series = None
            cls.thread = None
            cls.threadLock = allocate_lock()
            cls.thread2 = None
            cls.thread2Lock = allocate_lock()
            cls.threadUsbVideo = None
            cls.threadUsbVideoLock = allocate_lock()
            cls.liveViewDeactivated = False
            cls.liveView2Deactivated = False
            cls.videoThread = None
            cls.videoThread2 = None
            cls.photoSeriesThread = None
            cls.frame = None
            cls.frame2 = None
            cls.frameRaw = None
            cls.frame2Raw = None
            cls.streamOutput = None
            cls.stream2Output = None
            cls.last_access = 0
            cls.last_access2 = 0
            cls.stopRequested = False
            cls.stopRequested2 = False
            cls.stopVideoRequested = False
            cls.stopVideoRequested2 = False
            cls.stopUsbVideoRequested = False
            cls.videoDuration = 0
            cls.videoDuration2 = 0
            cls.stopPhotoSeriesRequested = False
            cls.resetScalerCropRequested = False
            cls.event = CameraEvent()
            cls.event2 = None
            cls.when_photo_taken = None
            cls.when_photo_2_taken = None
            cls.when_series_photo_taken = None
            cls.when_recording_starts = None
            cls.when_recording_stops = None
            cls.when_recording_2_starts = None
            cls.when_recording_2_stops = None
            cls.when_streaming_1_starts = None
            cls.when_streaming_1_stops = None
            cls.when_streaming_2_starts = None
            cls.when_streaming_2_stops = None

            cls.initCamera()
        else:
            if CameraCfg().serverConfig.noCamera == False:
                if cls.cam is None:
                    cls.initCamera()
                else:
                    CameraCfg().serverConfig.error = None
        return cls._instance

    @classmethod
    def isCamera2Available(cls) -> bool:
        """Check if the second camera is available
        Returns True if the second camera is available, False otherwise
        """
        logger.debug("Thread %s: Camera.isCamera2Available", get_ident())
        if cls.cam2 is not None:
            return True
            logger.debug(
                "Thread %s: Camera.isCamera2Available - Second camera is available",
                get_ident(),
            )
        else:
            logger.debug(
                "Thread %s: Camera.isCamera2Available - Second camera not available",
                get_ident(),
            )
            return False

    @classmethod
    def initCamera(cls):
        """Instantiate the camera"""
        logger.debug(
            "Thread %s: Camera.initCamera - Instantiating Camera Class", get_ident()
        )

        prgLogger.debug(
            "from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls"
        )
        prgLogger.debug("from libcamera import Transform, Size, ColorSpace, controls")
        prgLogger.debug("from picamera2.encoders import JpegEncoder, MJPEGEncoder")
        if useSensorConfiguration:
            prgLogger.debug("from picamera2.configuration import SensorConfiguration")
        prgLogger.debug("from picamera2.outputs import FileOutput, FfmpegOutput")
        prgLogger.debug("from picamera2.encoders import H264Encoder")
        prgLogger.debug("import time")
        prgLogger.debug("import os")
        prgLogger.debug("import gc")
        prgLogger.debug("import logging")
        prgLogger.debug("Picamera2.set_logging(logging.ERROR)")
        prgLogger.debug('os.environ["LIBCAMERA_LOG_LEVELS"] = "*:3"')
        prgLogger.debug("videoDuration = 10")

        cfg = CameraCfg()
        sc = cfg.serverConfig
        sc.error = None
        # Before all, load the global camera info to get the installed cameras and the active cam
        activeCam, activeCamIsUsb, activeCamUsbDev = cls.getActiveCamera()
        if sc.noCamera == True:
            return

        if cls.cam is None:
            logger.debug(
                "Thread %s: Camera.initCamera: Active camera is None - Needing initialization",
                get_ident(),
            )
            if activeCamIsUsb == False:
                logger.debug(
                    "Thread %s: Camera.initCamera: Instantiating Pi camera %s",
                    get_ident(),
                    activeCam,
                )
                cls.camIsUsb = False
                cls.camUsbDev = activeCamUsbDev
                try:
                    tc = cfg.tuningConfig
                    if tc.loadTuningFile == False:
                        cls.cam = Picamera2(activeCam)
                        prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                    else:
                        tuning = Picamera2.load_tuning_file(
                            tc.tuningFile, tc.tuningFolder
                        )
                        cls.cam = Picamera2(activeCam, tuning=tuning)
                        logger.debug(
                            "Thread %s: Camera.initCamera - Initialized camera %s with tuning file %s",
                            get_ident(),
                            activeCam,
                            tc.tuningFilePath,
                        )
                        prgLogger.debug(
                            "tuning = Picamera2.load_tuning_file(%s, %s)",
                            tc.tuningFile,
                            tc.tuningFolder,
                        )
                        prgLogger.debug(
                            "picam2 = Picamera2(%s, tuning=tuning)", activeCam
                        )
                    cls.camNum = activeCam
                    cls.ctrl = CameraController(cls.camIsUsb, cls.camUsbDev)
                except RuntimeError as e:
                    logger.error(
                        "Thread %s: Camera.initCamera - Error %s", get_ident(), e
                    )
                    if not sc.error:
                        sc.error = "Error while initializing camera: " + str(e)
                        sc.error2 = "Probably another process is using the camera."
                        sc.errorSource = "Picamera2"
            else:
                logger.debug(
                    "Thread %s: Camera.initCamera: Instantiating USB camera %s",
                    get_ident(),
                    activeCam,
                )
                cls.camIsUsb = True
                cls.camUsbDev = activeCamUsbDev
                cls.cam = cv2.VideoCapture(cls.camUsbDev, cv2.CAP_V4L2)
                if not cls.cam or not cls.cam.isOpened():
                    logger.error(
                        "Thread %s: Camera.initCamera - Error: USB camera not opened",
                        get_ident(),
                    )
                    sc.error = "Error while initializing camera: USB camera not opened"
                    sc.errorSource = "CV2"
                else:
                    logger.debug(
                        "Thread %s: Camera.initCamera - Initialized USB camera %s",
                        get_ident(),
                        activeCam,
                    )
                    cls.camNum = activeCam
                    cls.ctrl = CameraController(cls.camIsUsb, cls.camUsbDev)
        else:
            logger.debug(
                "Thread %s: Camera.initCamera: Active camera is already set for %s. Checking if switch is needed",
                get_ident(),
                Camera.camNum,
            )
            if activeCam != Camera.camNum:
                try:
                    logger.debug(
                        "Thread %s: Camera.initCamera: About to switch camera from %s to %s",
                        get_ident(),
                        Camera.camNum,
                        activeCam,
                    )
                    cls.stopCameraSystem()
                    if activeCamIsUsb == False:
                        tc = cfg.tuningConfig
                        if tc.loadTuningFile == False:
                            cls.cam = Picamera2(activeCam)
                            prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                        else:
                            tuning = Picamera2.load_tuning_file(
                                tc.tuningFile, tc.tuningFolder
                            )
                            cls.cam = Picamera2(activeCam, tuning=tuning)
                            logger.debug(
                                "Thread %s: Camera.initCamera - Initialized camera %s with tuning file %s",
                                get_ident(),
                                activeCam,
                                tc.tuningFilePath,
                            )
                            prgLogger.debug(
                                "tuning = Picamera2.load_tuning_file(%s, %s)",
                                tc.tuningFile,
                                tc.tuningFolder,
                            )
                            prgLogger.debug(
                                "picam2 = Picamera2(%s, tuning=tuning)", activeCam
                            )
                        cls.camNum = activeCam
                        cls.camIsUsb = False
                        cls.camUsbDev = ""
                        cls.ctrl = CameraController(cls.camIsUsb, cls.camUsbDev)
                        logger.debug(
                            "Thread %s: Camera.initCamera: Switch camera to %s successful",
                            get_ident(),
                            activeCam,
                        )
                        # Force refresh of camera properties
                        cfg.cameraProperties.model = None
                        cfg.sensorModes = []
                        cfg.rawFormats = []
                        logger.debug(
                            "Thread %s: Camera.initCamera: Camera-specific configs were reset",
                            get_ident(),
                        )
                    else:
                        cls.cam = cv2.VideoCapture(activeCamUsbDev, cv2.CAP_V4L2)
                        if not cls.cam or not cls.cam.isOpened():
                            raise RuntimeError("USB camera not opened")
                        cls.camNum = activeCam
                        cls.camIsUsb = True
                        cls.camUsbDev = activeCamUsbDev
                        cls.ctrl = CameraController(cls.camIsUsb, cls.camUsbDev)
                        logger.debug(
                            "Thread %s: Camera.initCamera: Switch camera to %s successful",
                            get_ident(),
                            activeCam,
                        )
                        # Force refresh of camera properties
                        cfg.cameraProperties.model = None
                        cfg.sensorModes = []
                        cfg.rawFormats = []
                        logger.debug(
                            "Thread %s: Camera.initCamera: Camera-specific configs were reset",
                            get_ident(),
                        )
                except RuntimeError as e:
                    logger.error(
                        "Thread %s: Camera.initCamera - Error %s", get_ident(), e
                    )
                    if not sc.error:
                        if activeCamIsUsb == False:
                            sc.error = "Error while initializing camera: " + str(e)
                            sc.error2 = "Probably another process is using the camera."
                            sc.errorSource = "Picamera2"
                        else:
                            sc.error = (
                                "Error while initializing camera: USB camera not opened"
                            )
                            sc.errorSource = "CV2"
                except Exception as e:
                    logger.error(
                        "Thread %s: Camera.initCamera - Error %s", get_ident(), e
                    )
                    if not sc.error:
                        sc.error = "Error while initializing camera: " + str(e)
                        sc.errorSource = "Picamera2"
            else:
                logger.debug(
                    "Thread %s: Camera.initCamera: Camera was already instantiated",
                    get_ident(),
                )
        if not sc.error:
            if cls.camIsUsb == False:
                cls.loadCameraSpecifics()
            else:
                if cls.loadUsbCameraSpecifics() == False:
                    sc.error = "USB Camera not found. Apply Settings/Configuration/Reload Cameras"
                    sc.errorSource = "V4L2"
        if not sc.error:
            cls.setSecondCamera()

        if (
            sc.isPhotoSeriesRecording == False
            and sc.isVideoRecording == False
            and sc.isLiveStream == False
        ):
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        if sc.isLiveStream2 == False:
            if Camera.cam2:
                Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)

    @staticmethod
    def getActiveCamera() -> tuple:
        """Determine the active camera and return its number, whether it is USB, and USB device path

        First load the global camera info, if not already done,
        Which gives us the list of currently connected cameras.

        Then check the active camera and return it.
        If a stored configuration had an active camera, camera number (Num) and model are checked.

        Returns:
            tuple: (active camera number (int),
                    is USB (bool),
                    USB device path (str)
                    )
        """
        logger.debug("Thread %s: Camera.getActiveCamera", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        trc = cfg.triggerConfig
        if (len(cfg.cameras) == 0) and (sc.noCamera == False):
            cfgCams = []
            cams = Picamera2.global_camera_info()
            if len(cams) == 0:
                sc.noCamera = True
                logger.debug(
                    "Thread %s: Camera.getActiveCamera - no cameras found", get_ident()
                )
                return 0, False, ""
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
                        logger.debug(
                            "Thread %s: Camera.getActiveCamera - USB camera found:  %s",
                            get_ident(),
                            cfgCam.id,
                        )
                    else:
                        cfgCam.usbDev = ""
                # On Bullseye systems, "Num" is not in the dict
                if "Num" in camera:
                    cfgCam.num = camera["Num"]
                else:
                    cfgCam.num = camNum
                    camNum += 1
                cfgCam.setUsbDev()
                cfgCams.append(cfgCam)
            cfg.cameras = cfgCams
            logger.debug(
                "Thread %s: Camera.getActiveCamera - %s cameras found",
                get_ident(),
                len(cfg.cameras),
            )
            # Set the list of supported cameras
            cfg.setSupportedCameras()
            # Set the list of Pi cameras
            cfg.setPiCameras()

        # Check that active camera is within the list of cameras
        logger.debug(
            "Thread %s: Camera.getActiveCamera - Checking active camera %s (model: %s, isUsb: %s, usbDev: %s) against %s found cameras",
            get_ident(),
            sc.activeCamera,
            sc.activeCameraModel,
            sc.activeCameraIsUsb,
            sc.activeCameraUsbDev,
            len(cfg.cameras),
        )
        activeCamOK = False
        if sc.activeCameraModel != "":
            for cfgCam in sc.supportedCameras:
                if (
                    cfgCam.num == sc.activeCamera
                    and cfgCam.model == sc.activeCameraModel
                    and cfgCam.isUsb == sc.activeCameraIsUsb
                    and cfgCam.usbDev == sc.activeCameraUsbDev
                ):
                    activeCamOK = True
                    break
            logger.debug(
                "Thread %s: Camera.getActiveCamera - Active camera:%s - activeCamOK:%s",
                get_ident(),
                sc.activeCamera,
                activeCamOK,
            )
        # If config for active camera is not in the list,
        # set it to the first camera
        if activeCamOK == False:
            logger.debug(
                "Thread %s: Camera.getActiveCamera - Resetting active camera to first of %s supported cameras",
                get_ident(),
                len(sc.supportedCameras),
            )
            for cfgCam in sc.supportedCameras:
                sc.activeCamera = cfgCam.num
                sc.activeCameraInfo = (
                    "Camera " + str(cfgCam.num) + " (" + cfgCam.model + ")"
                )
                sc.activeCameraModel = cfgCam.model
                sc.activeCameraIsUsb = cfgCam.isUsb
                sc.activeCameraUsbDev = cfgCam.usbDev
                break
            logger.debug(
                "Thread %s: Camera.getActiveCamera - active camera reset to %s",
                get_ident(),
                sc.activeCamera,
            )
            # Reset the active camera configuration
            cfg.resetActiveCameraSettings()
            trc.setCameraSettingsToDefault()
            sc.unsavedChanges = True
            sc.addChangeLogEntry(
                f"Camera settings for {sc.activeCameraInfo} were reset due to camera model change"
            )

        # Make sure that folder for photos exists
        sc.cameraPhotoSubPath = "photos/" + "camera_" + str(sc.activeCamera)
        fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath
        if not os.path.exists(fp):
            os.makedirs(fp)
            logger.debug(
                "Thread %s: Camera.getActiveCamera - Photo directory created %s",
                get_ident(),
                fp,
            )

        logger.debug(
            "Thread %s: Camera.getActiveCamera - activeCamera: %s - isUsb: %s - usbDev: %s",
            get_ident(),
            sc.activeCamera,
            sc.activeCameraIsUsb,
            sc.activeCameraUsbDev,
        )
        return sc.activeCamera, sc.activeCameraIsUsb, sc.activeCameraUsbDev

    @classmethod
    def switchCamera(cls):
        """Switch the camera"""
        logger.debug("Thread %s: Camera.switchCamera", get_ident())

        logger.debug(
            "Thread %s: Camera.switchCamera - stopping Live Stream", get_ident()
        )
        cls.stopLiveStream()
        logger.debug(
            "Thread %s: Camera.switchCamera - Live Stream stopped", get_ident()
        )
        if cls.cam2:
            cls.stopLiveStream2()
            logger.debug(
                "Thread %s: Camera.switchCamera - Live Stream2 stopped", get_ident()
            )

        time.sleep(1)

        activeCam, activeCamIsUsb, activeCamUsbDev = Camera.getActiveCamera()
        cfg = CameraCfg()
        sc = cfg.serverConfig
        trc = cfg.triggerConfig
        if sc.noCamera == True:
            return

        if Camera.cam is None:
            if activeCamIsUsb == False:
                logger.debug(
                    "Thread %s: Camera.switchCamera: Instantiating Pi camera %s",
                    get_ident(),
                    activeCam,
                )
                cls.camIsUsb = False
                cls.camUsbDev = ""
                tc = cfg.tuningConfig
                if tc.loadTuningFile == False:
                    cls.cam = Picamera2(activeCam)
                    prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                else:
                    tuning = Picamera2.load_tuning_file(tc.tuningFile, tc.tuningFolder)
                    cls.cam = Picamera2(activeCam, tuning=tuning)
                    logger.debug(
                        "Thread %s: Camera.switchCamera - Initialized camera %s with tuning file %s",
                        get_ident(),
                        activeCam,
                        tc.tuningFilePath,
                    )
                    prgLogger.debug(
                        "tuning = Picamera2.load_tuning_file(%s, %s)",
                        tc.tuningFile,
                        tc.tuningFolder,
                    )
                    prgLogger.debug("picam2 = Picamera2(%s, tuning=tuning)", activeCam)
            else:
                logger.debug(
                    "Thread %s: Camera.switchCamera: Instantiating USB camera %s",
                    get_ident(),
                    activeCam,
                )
                cls.camIsUsb = True
                cls.camUsbDev = activeCamUsbDev
                cls.cam = cv2.VideoCapture(cls.camUsbDev, cv2.CAP_V4L2)
                if not cls.cam or not cls.cam.isOpened():
                    logger.error(
                        "Thread %s: Camera.initCamera - Error: USB camera not opened",
                        get_ident(),
                    )
            Camera.camNum = activeCam
            Camera.camIsUsb = activeCamIsUsb
            Camera.camUsbDev = activeCamUsbDev
            Camera.ctrl = CameraController(Camera.camIsUsb, Camera.camUsbDev)
        else:
            if activeCam != Camera.camNum:
                logger.debug(
                    "Thread %s: Camera.switchCamera: About to switch camera from %s to %s",
                    get_ident(),
                    Camera.camNum,
                    activeCam,
                )
                Camera.stopCameraSystem()
                if activeCamIsUsb == False:
                    tc = cfg.tuningConfig
                    logger.debug(
                        "Thread %s: Camera.switchCamera: tc.loadTuningFile=%s",
                        get_ident(),
                        tc.loadTuningFile,
                    )
                    if tc.loadTuningFile == False:
                        cls.cam = Picamera2(activeCam)
                        prgLogger.debug("picam2 = Picamera2(%s)", activeCam)
                    else:
                        tuning = Picamera2.load_tuning_file(
                            tc.tuningFile, tc.tuningFolder
                        )
                        cls.cam = Picamera2(activeCam, tuning=tuning)
                        logger.debug(
                            "Thread %s: Camera.switchCamera - Initialized camera %s with tuning file %s",
                            get_ident(),
                            activeCam,
                            tc.tuningFilePath,
                        )
                        prgLogger.debug(
                            "tuning = Picamera2.load_tuning_file(%s, %s)",
                            tc.tuningFile,
                            tc.tuningFolder,
                        )
                        prgLogger.debug(
                            "picam2 = Picamera2(%s, tuning=tuning)", activeCam
                        )
                    Camera.camNum = activeCam
                    Camera.camIsUsb = False
                    Camera.camUsbDev = ""
                    Camera.ctrl = CameraController(Camera.camIsUsb, Camera.camUsbDev)
                    logger.debug(
                        "Thread %s: Camera.switchCamera: Switch camera to %s successful",
                        get_ident(),
                        activeCam,
                    )
                    # Force refresh of camera properties
                    CameraCfg().cameraProperties.model = None
                    CameraCfg().sensorModes = []
                    CameraCfg().rawFormats = []
                    CameraCfg().resetActiveCameraSettings() 
                    trc.setCameraSettingsToDefault()
                    logger.debug(
                        "Thread %s: Camera.switchCamera: Camera-specific configs were reset",
                        get_ident(),
                    )
                else:
                    cls.cam = cv2.VideoCapture(activeCamUsbDev, cv2.CAP_V4L2)
                    if not cls.cam or not cls.cam.isOpened():
                        logger.error(
                            "Thread %s: Camera.switchCamera - Error: USB camera not opened",
                            get_ident(),
                        )
                    Camera.camNum = activeCam
                    Camera.camIsUsb = True
                    Camera.camUsbDev = activeCamUsbDev
                    Camera.ctrl = CameraController(Camera.camIsUsb, Camera.camUsbDev)
                    logger.debug(
                        "Thread %s: Camera.switchCamera: Switch camera to %s successful",
                        get_ident(),
                        activeCam,
                    )
                    # Force refresh of camera properties
                    CameraCfg().cameraProperties.model = None
                    CameraCfg().sensorModes = []
                    CameraCfg().rawFormats = []
                    CameraCfg().resetActiveCameraSettings() 
                    trc.setCameraSettingsToDefault()
                    logger.debug(
                        "Thread %s: Camera.switchCamera: Camera-specific configs were reset",
                        get_ident(),
                    )
            else:
                logger.debug(
                    "Thread %s: Camera.switchCamera: Camera was already instantiated",
                    get_ident(),
                )

        time.sleep(1)

        if cls.camIsUsb == False:
            cls.loadCameraSpecifics()
            cls.setSecondCamera()
        else:
            if cls.loadUsbCameraSpecifics() == False:
                sc.error = "USB Camera not found. Apply Settings/Configuration/Reload Cameras"
                sc.errorSource = "V4L2"
            else:
                cls.setSecondCamera()

        # Restore streaming config, if available
        cls.restoreConfigFromStreamingConfig()

        logger.debug(
            "Thread %s: Camera.switchCamera - starting Live Stream", get_ident()
        )
        cls.startLiveStream()
        logger.debug(
            "Thread %s: Camera.switchCamera - Live Stream started", get_ident()
        )

        logger.debug("Thread %s: Camera.switchCamera - second camera set", get_ident())
        if cls.cam2:
            cls.startLiveStream2()
            logger.debug(
                "Thread %s: Camera.switchCamera - Live Stream 2 started", get_ident()
            )

    @classmethod
    def startLiveStream(cls):
        """Start thread for live stream"""
        logger.debug("Thread %s: Camera.startLiveStream", get_ident())
        if (not CameraCfg().serverConfig.error) and (not CameraCfg().serverConfig.noCamera):
            if Camera.liveViewDeactivated:
                logger.debug(
                    "Thread %s: Not starting Live View thread. Live View deactivated",
                    get_ident(),
                )
                CameraCfg().serverConfig.isLiveStream = False
            else:
                with Camera.threadLock:
                    Camera.last_access = time.time()
                logger.debug(
                    "Thread %s: Camera.startLiveStream - last_access set", get_ident()
                )
                if Camera.thread is None:
                    logger.debug(
                        "Thread %s: Camera.startLiveStream: Starting new thread",
                        get_ident(),
                    )

                    # start background frame thread
                    Camera.thread = threading.Thread(target=cls._thread)
                    Camera.thread.start()
                    logger.debug(
                        "Thread %s: Camera.startLiveStream - Thread started",
                        get_ident(),
                    )

                    # wait until first frame is available
                    logger.debug(
                        "Thread %s: Camera.startLiveStream - waiting for frame",
                        get_ident(),
                    )
                    Camera.event.wait()
                    if not CameraCfg().serverConfig.error:
                        CameraCfg().serverConfig.isLiveStream = True
                else:
                    logger.debug(
                        "Thread %s: Camera.startLiveStream - Thread exists", get_ident()
                    )
                    if not Camera.thread.is_alive:
                        logger.debug(
                            "Thread %s: Camera.startLiveStream - Thread is not alive",
                            get_ident(),
                        )
                        Camera.thread = threading.Thread(target=cls._thread)
                        Camera.thread.start()
                        logger.debug(
                            "Thread %s: Camera.startLiveStream - Thread started",
                            get_ident(),
                        )

    @classmethod
    def startLiveStream2(cls):
        """Start thread for live stream"""
        logger.debug("Thread %s: Camera.startLiveStream2", get_ident())
        if not CameraCfg().serverConfig.errorc2:
            if cls.cam2:
                if Camera.liveView2Deactivated:
                    logger.debug(
                        "Thread %s: Not starting Live View 2 thread. Live View 2 deactivated",
                        get_ident(),
                    )
                    CameraCfg().serverConfig.isLiveStream2 = False
                else:
                    # logger.debug("Thread %s: Camera.startLiveStream2 - About to acquire Lock: thread2Lock=%s.", get_ident(), Camera.thread2Lock.locked())
                    with Camera.thread2Lock:
                        Camera.last_access2 = time.time()
                    # logger.debug("Thread %s: Camera.startLiveStream2 - last_access2 set", get_ident())
                    if Camera.thread2 is None:
                        logger.debug(
                            "Thread %s: Camera.startLiveStream2: Starting new thread",
                            get_ident(),
                        )

                        # start background frame thread
                        Camera.thread2 = threading.Thread(target=cls._thread2)
                        Camera.thread2.start()
                        logger.debug(
                            "Thread %s: Camera.startLiveStream2 - Thread started",
                            get_ident(),
                        )

                        # wait until first frame is available
                        logger.debug(
                            "Thread %s: Camera.startLiveStream2 - waiting for frame",
                            get_ident(),
                        )
                        Camera.event2.wait()
                        if not CameraCfg().serverConfig.errorc2:
                            CameraCfg().serverConfig.isLiveStream2 = True
                    else:
                        logger.debug(
                            "Thread %s: Camera.startLiveStream2 - Thread exists",
                            get_ident(),
                        )
                        if not Camera.thread2.is_alive:
                            logger.debug(
                                "Thread %s: Camera.startLiveStream2 - Thread is not alive",
                                get_ident(),
                            )
                            Camera.thread2 = threading.Thread(target=cls._thread2)
                            Camera.thread2.start()
                            logger.debug(
                                "Thread %s: Camera.startLiveStream2 - Thread started",
                                get_ident(),
                            )
            else:
                logger.debug(
                    "Thread %s: Camera.startLiveStream2 - Not starting Live View 2 thread. Second camera not available",
                    get_ident(),
                )
        else:
            logger.debug(
                "Thread %s: Camera.startLiveStream2 - Not starting Live View 2 thread. Error present: %s",
                get_ident(),
                CameraCfg().serverConfig.errorc2,
            )

    @classmethod
    def stopLiveStream(cls):
        """Stop thread for live stream"""
        logger.debug("Thread %s: Camera.stopLiveStream", get_ident())
        if not Camera.thread is None:
            logger.debug(
                "Thread %s: Camera.stopLiveStream - stopping live stream thread",
                get_ident(),
            )
            Camera.stopRequested = True
            cnt = 0
            while Camera.thread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    # Assume thread dead
                    Camera.thread = None
                    logger.debug(
                        "Thread %s: Camera.stopLiveStream: Thread assumed dead",
                        get_ident(),
                    )
                    break
                    # raise TimeoutError("Background thread did not stop within 2 sec")
            if cnt < 200:
                logger.debug(
                    "Thread %s: Camera.stopLiveStream: Thread has stopped", get_ident()
                )
            Camera.ctrl.stopEncoder(Camera.cam, Camera.ENCODER_LIVESTREAM)
            CameraCfg().serverConfig.isLiveStream = False
        else:
            logger.debug(
                "Thread %s: Camera.stopLiveStream: Thread was not started", get_ident()
            )
            CameraCfg().serverConfig.isLiveStream = False

    @classmethod
    def stopLiveStream2(cls):
        """Stop thread for live stream 2"""
        logger.debug("Thread %s: Camera.stopLiveStream2", get_ident())
        if Camera.cam2:
            if not Camera.thread2 is None:
                logger.debug(
                    "Thread %s: Camera.stopLiveStream2 - stopping live stream thread",
                    get_ident(),
                )
                Camera.stopRequested2 = True
                cnt = 0
                while Camera.thread2:
                    time.sleep(0.01)
                    cnt += 1
                    if cnt > 200:
                        # Assume thread dead
                        Camera.thread2 = None
                        logger.debug(
                            "Thread %s: Camera.stopLiveStream2: Thread assumed dead",
                            get_ident(),
                        )
                        break
                        # raise TimeoutError("Background thread did not stop within 2 sec")
                if cnt < 200:
                    logger.debug(
                        "Thread %s: Camera.stopLiveStream2: Thread has stopped",
                        get_ident(),
                    )
                Camera.ctrl2.stopEncoder(Camera.cam2, Camera.ENCODER_LIVESTREAM)
                CameraCfg().serverConfig.isLiveStream2 = False
            else:
                logger.debug(
                    "Thread %s: Camera.stopLiveStream2: Thread was not started",
                    get_ident(),
                )
                CameraCfg().serverConfig.isLiveStream2 = False

    @staticmethod
    def restartLiveStream():
        logger.debug("Thread %s: Camera.restartLiveStream", get_ident())
        Camera.liveViewDeactivated = True
        Camera.stopLiveStream()
        time.sleep(0.5)
        logger.debug(
            "Thread %s: Camera.restartLiveStream: Live stream stopped", get_ident()
        )
        Camera.cam, done = Camera.ctrl.requestStop(Camera.cam)
        logger.debug("Thread %s: Camera.restartLiveStream: Camera stopped", get_ident())
        time.sleep(0.5)
        Camera.ctrl.clearConfig()
        logger.debug("Thread %s: Camera.restartLiveStream: Config cleared", get_ident())
        Camera.liveViewDeactivated = False
        Camera.startLiveStream()
        logger.debug(
            "Thread %s: Camera.restartLiveStream: Live stream started", get_ident()
        )

    @staticmethod
    def restartLiveStream2():
        logger.debug("Thread %s: Camera.restartLiveStream2", get_ident())
        Camera.liveView2Deactivated = True
        Camera.stopLiveStream2()
        logger.debug(
            "Thread %s: Camera.restartLiveStream2: Live stream stopped", get_ident()
        )
        Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2)
        logger.debug(
            "Thread %s: Camera.restartLiveStream2: Camera stopped", get_ident()
        )
        Camera.ctrl2.clearConfig()
        logger.debug(
            "Thread %s: Camera.restartLiveStream2: Config cleared", get_ident()
        )
        Camera.liveView2Deactivated = False
        Camera.startLiveStream2()
        logger.debug(
            "Thread %s: Camera.restartLiveStream2: Live stream started", get_ident()
        )

    def getLiveViewImageForMotionDetection(self):
        """Capture and return a buffer"""
        cfg = CameraCfg()
        if Camera.camIsUsb == False:
            if cfg.triggerConfig.motionDetectAlgo == 0:
                buf = Camera.cam.capture_buffer(cfg.liveViewConfig.stream)
                (w, h) = cfg.liveViewConfig.stream_size
                buf = buf[: w * h].reshape(h, w)
                frameRaw = buf
            else:
                frameRaw = Camera.cam.capture_array(cfg.liveViewConfig.stream)
                if cfg.liveViewConfig.format == "YUV420":
                    if cv2Available == True:
                        frameRaw = cv2.cvtColor(frameRaw, cv2.COLOR_YUV2BGR_I420)
        else:
            frame, frameRaw = self.get_frame()
        return copy.copy(frameRaw)

    def getLeftImageForStereo(self):
        """Capture and return a buffer"""
        if Camera.camIsUsb == False:
            return Camera.cam.capture_array(CameraCfg().liveViewConfig.stream)
        else:
            frame, frameRaw = self.get_frame()
            return frameRaw

    def getRightImageForStereo(self):
        """Capture and return a buffer"""
        if Camera.camIsUsb == False:
            return Camera.cam2.capture_array(
                CameraCfg().streamingCfg[str(Camera.camNum2)]["liveconfig"].stream
            )
        else:
            frame, frameRaw = self.get_frame2()
            return frameRaw

    def get_frame(self):
        """Return the current camera frame."""
        # logger.debug("Thread %s: Camera.get_frame", get_ident())
        with Camera.threadLock:
            Camera.last_access = time.time()

        # wait for a signal from the camera thread
        # logger.debug("Thread %s: Camera.get_frame - waiting for frame", get_ident())
        Camera.event.wait()
        # logger.debug("Thread %s: Camera.get_frame - continue", get_ident())
        Camera.event.clear()

        # logger.debug("Thread %s: Returning frame", get_ident())
        return Camera.frame, Camera.frameRaw

    def get_frame2(self):
        """Return the current camera 2 frame."""
        # logger.debug("Thread %s: Camera.get_frame2", get_ident())
        if Camera.cam2:
            with Camera.thread2Lock:
                Camera.last_access2 = time.time()

            # wait for a signal from the camera thread
            # logger.debug("Thread %s: Camera.get_frame2 - waiting for frame", get_ident())
            Camera.event2.wait()
            # logger.debug("Thread %s: Camera.get_frame2 - continue", get_ident())
            Camera.event2.clear()

            # logger.debug("Thread %s: Returning frame2", get_ident())
            return Camera.frame2, Camera.frame2Raw
        else:
            return None, None

    def get_photoFrame(self):
        """Return the current camera frame."""
        logger.debug("Thread %s: Camera.get_photoFrame", get_ident())
        with Camera.threadLock:
            Camera.last_access = time.time()

        # wait for a signal from the camera thread
        logger.debug(
            "Thread %s: Camera.get_photoFrame - waiting for frame", get_ident()
        )
        Camera.event.wait()
        logger.debug("Thread %s: Camera.get_photoFrame - continue", get_ident())
        Camera.event.clear()

        logger.debug("Thread %s: Camera.get_photoFrame - Returning frame", get_ident())
        return Camera.frame

    def get_photoFrame2(self):
        """Return the current camera 2 frame."""
        logger.debug("Thread %s: Camera.get_photoFrame2", get_ident())
        if Camera.cam2:
            with Camera.thread2Lock:
                Camera.last_access2 = time.time()

            # wait for a signal from the camera thread
            logger.debug(
                "Thread %s: Camera.get_photoFrame2 - waiting for frame", get_ident()
            )
            Camera.event2.wait()
            logger.debug("Thread %s: Camera.get_photoFrame2 - continue", get_ident())
            Camera.event2.clear()

            logger.debug(
                "Thread %s: Camera.get_photoFrame2 - Returning frame", get_ident()
            )
            return Camera.frame2
        else:
            return None

    @staticmethod
    def loadCameraSpecifics():
        """Load camera specific parameters into configuration, if not already done"""
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
            cfgProps.colorFilterArrangement = camPprops["ColorFilterArrangement"]
            cfgProps.scalerCropMaximum = camPprops["ScalerCropMaximum"]
            cfgProps.systemDevices = camPprops["SystemDevices"]
            if "SensorSensitivity" in camPprops:
                cfgProps.sensorSensitivity = camPprops["SensorSensitivity"]

            cfgProps.hasFocus = "AfMode" in Camera.cam.camera_controls
            cfgProps.hasFlicker = "AeFlickerMode" in Camera.cam.camera_controls
            cfgProps.hasHdr = "HdrMode" in Camera.cam.camera_controls

            if cfgCtrls.include_scalerCrop == False:
                cfgCtrls.scalerCrop = (
                    0,
                    0,
                    camPprops["PixelArraySize"][0],
                    camPprops["PixelArraySize"][1],
                )
                # This must be updated after the camera has been started
                Camera.resetScalerCropRequested = True
            logger.debug(
                "Thread %s: Camera.loadCameraSpecifics loaded to config", get_ident()
            )

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
            logger.debug(
                "Thread %s: Camera.loadCameraSpecifics: %s sensor modes found",
                get_ident(),
                len(cfg.sensorModes),
            )
            logger.debug(
                "Thread %s: Camera.loadCameraSpecifics: %s raw formats found",
                get_ident(),
                len(cfg.rawFormats),
            )

            # Set some Sensor Mode specific parameters for standard configurations
            maxModei = len(cfg.sensorModes) - 1
            maxMode = str(maxModei)
            # For Live View
            # Initially set the stream size to (640, 480). Use Sensor Mode, if possible
            # If stream_size is set, keep the settings. They have been loeaded from stored config
            if cfg.liveViewConfig.stream_size is None:
                sizeWidth = 640
                sizeHeight = int(
                    sizeWidth * cfgProps.pixelArraySize[1] / cfgProps.pixelArraySize[0]
                )
                if (sizeHeight % 2) != 0:
                    sizeHeight += 1
                cfg.liveViewConfig.stream_size = (sizeWidth, sizeHeight)
                cfg.liveViewConfig.stream_size_align = False
                if (
                    cfgSensorModes[0].size[0] == sizeWidth
                    and cfgSensorModes[0].size[1] == sizeHeight
                ):
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
                if (
                    cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero")
                    or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 1")
                    or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 2")
                    or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 3")
                    or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4")
                ):
                    cfg.videoConfig.sensor_mode = 0
                    cfg.videoConfig.stream_size = cfgSensorModes[0].size
                    cfg.photoConfig.sensor_mode = 0
                    cfg.photoConfig.stream_size = cfgSensorModes[0].size
                else:
                    cfg.videoConfig.sensor_mode = maxMode
                    cfg.videoConfig.stream_size = cfgSensorModes[maxModei].size

            # Sync aspect ratio for CSI cameras
            cfg.serverConfig.syncAspectRatio = True

    @staticmethod
    def loadUsbCameraSpecifics() -> bool:
        """Load USB camera specific parameters into configuration, if not already done

        Returns:
            bool: True if USB camera specifics were loaded, False otherwise
        """
        logger.debug("Thread %s: Camera.loadUsbCameraSpecifics", get_ident())

        cfg = CameraCfg()

        # Load Camera Properties
        if cfg.cameraProperties.model is None:
            if cfg.setUsbCameraProperties() == False:
                return False

            if cfg.controls.include_scalerCrop == False:
                cfg.controls.scalerCrop = cfg.cameraProperties.scalerCropMaximum
                # This must be updated after the camera has been started
                Camera.resetScalerCropRequested = True
            logger.debug(
                "Thread %s: Camera.loadUsbCameraSpecifics loaded to config", get_ident()
            )

        # Load Sensor Modes
        if len(cfg.sensorModes) == 0:
            if cfg.setUsbSensorModes() == False:
                return False

            logger.debug(
                "Thread %s: Camera.loadUsbCameraSpecifics: %s sensor modes found",
                get_ident(),
                len(cfg.sensorModes),
            )
            logger.debug(
                "Thread %s: Camera.loadUsbCameraSpecifics: %s raw formats found",
                get_ident(),
                len(cfg.rawFormats),
            )

            # Set some Sensor Mode specific parameters for standard configurations
            maxModei = len(cfg.sensorModes) - 1
            maxMode = str(maxModei)
            # For Live View
            # Initially set the stream size to the size of the first Sensor Mode
            if cfg.liveViewConfig.stream_size is None:
                cfg.liveViewConfig.sensor_mode = "0"
                sizeWidth = cfg.sensorModes[0].size[0]
                sizeHeight = cfg.sensorModes[0].size[1]
                cfg.liveViewConfig.stream_size = (sizeWidth, sizeHeight)
            cfg.liveViewConfig.colour_space = cfg.cameraProperties.colorSpace
            cfg.liveViewConfig.buffer_count = 1
            cfg.liveViewConfig.queue = False
            cfg.liveViewConfig.stream = "main"
            cfg.liveViewConfig.stream_size_align = False
            cfg.liveViewConfig.format = cfg.sensorModes[0].format
            cfg.liveViewConfig.display = None
            cfg.liveViewConfig.encode = None
            # For photo
            if cfg.photoConfig.stream_size is None:
                cfg.photoConfig.sensor_mode = maxMode
                cfg.photoConfig.stream_size = cfg.sensorModes[maxModei].size
            cfg.photoConfig.colour_space = cfg.cameraProperties.colorSpace
            cfg.photoConfig.buffer_count = 1
            cfg.photoConfig.queue = False
            cfg.photoConfig.stream = "main"
            cfg.photoConfig.stream_size_align = False
            cfg.photoConfig.format = cfg.sensorModes[maxModei].format
            cfg.photoConfig.display = None
            cfg.photoConfig.encode = None
            # For raw photo
            if cfg.rawConfig.stream_size is None:
                cfg.rawConfig.sensor_mode = maxMode
                cfg.rawConfig.stream_size = cfg.sensorModes[maxModei].size
                cfg.rawConfig.format = "tiff"
            cfg.rawConfig.colour_space = cfg.cameraProperties.colorSpace
            cfg.rawConfig.buffer_count = 1
            cfg.rawConfig.queue = False
            cfg.rawConfig.stream = "main"
            cfg.rawConfig.stream_size_align = False
            # For Video
            if cfg.videoConfig.stream_size is None:
                cfg.videoConfig.sensor_mode = maxMode
                cfg.videoConfig.stream_size = cfg.sensorModes[maxModei].size
            cfg.videoConfig.colour_space = cfg.cameraProperties.colorSpace
            cfg.videoConfig.buffer_count = 1
            cfg.videoConfig.queue = False
            cfg.videoConfig.stream = "main"
            cfg.videoConfig.stream_size_align = False
            cfg.videoConfig.format = cfg.sensorModes[maxModei].format
            cfg.videoConfig.display = None
            cfg.videoConfig.encode = None

            # Do not sync aspect ratio for USB cameras
            cfg.serverConfig.syncAspectRatio = False

        # Load USB Camera Controls
        if len(cfg.controls.usbCamControls) == 0:
            cfg.setUsbCamControls()
            cfg.cameraProperties.hasFocus = "AfMode" in cfg.controls.usbCamControls

        return True

    @classmethod
    def setSecondCamera(cls):
        """Set the second camera"""
        logger.debug("Thread %s: Camera.setSecondCamera", get_ident())
        cls.camNum2 = None
        cls.cam2 = None
        cfg = CameraCfg()
        sc = cfg.serverConfig
        sc.errorc2 = None
        camNum2 = None
        secondCamIsUsb = False
        secondCamUsbDev = ""
        secondCamModel = ""

        # Check camera list for registered second camera
        if not sc.secondCamera is None:
            secondCam = None
            for cfgCam in cfg.cameras:
                if cfgCam.num == sc.secondCamera \
                and cfgCam.model == sc.secondCameraModel:
                    secondCam = cfgCam.num
                    camNum2 = cfgCam.num
                    secondCamIsUsb = cfgCam.isUsb
                    secondCamUsbDev = cfgCam.usbDev
                    secondCamModel = cfgCam.model
                    break
            if secondCam is None:
                logger.debug(
                    "Thread %s: Camera.setSecondCamera - Registered second camera %s not found",
                    get_ident(),
                    sc.secondCamera,
                )
                sc.unsavedChanges = True
                sc.addChangeLogEntry(
                    f"Second camera was reset Camera {sc.secondCamera}: {sc.secondCameraModel} - not found"
                )
                sc.secondCamera = None

        # If no registered second camera, take the first available which is not the active camera
        if sc.secondCamera is None:
            for cfgCam in cfg.cameras:
                if cfgCam.num != cls.camNum and camNum2 is None:
                    # Take the first camera which is not the active camera if USB is OK
                    if not cfgCam.isUsb or sc.supportsUsbCamera == True:
                        camNum2 = cfgCam.num
                        secondCamIsUsb = cfgCam.isUsb
                        secondCamUsbDev = cfgCam.usbDev
                        secondCamModel = cfgCam.model
                        break
        logger.debug(
            "Thread %s: Camera.setSecondCamera - found second camera: %s model: %s",
            get_ident(),
            camNum2,
            secondCamModel,
        )
        if not camNum2 is None:
            try:
                cls.camNum2 = camNum2
                cls.cam2IsUsb = secondCamIsUsb
                cls.cam2UsbDev = secondCamUsbDev
                sc.secondCamera = camNum2
                sc.secondCameraIsUsb = secondCamIsUsb
                sc.secondCameraUsbDev = secondCamUsbDev
                sc.secondCameraModel = secondCamModel
                sc.secondCameraInfo = (
                    "Camera " + str(camNum2) + " (" + secondCamModel + ")"
                )
                strc = cfg.streamingCfg
                camNum2Str = str(camNum2)
                if secondCamIsUsb == False:
                    if camNum2Str in strc:
                        scfg = strc[camNum2Str]
                        if "tuningconfig" in scfg:
                            tc = scfg["tuningconfig"]
                            if tc.loadTuningFile == False:
                                cls.cam2 = Picamera2(cls.camNum2)
                            else:
                                tuning = Picamera2.load_tuning_file(
                                    tc.tuningFile, tc.tuningFolder
                                )
                                cls.cam2 = Picamera2(cls.camNum2, tuning=tuning)
                                logger.debug(
                                    "Thread %s: Camera.setSecondCamera - Initialized camera %s with tuning file %s",
                                    get_ident(),
                                    cls.camNum2,
                                    tc.tuningFilePath,
                                )
                        else:
                            cls.cam2 = Picamera2(cls.camNum2)
                    else:
                        cls.cam2 = Picamera2(cls.camNum2)
                else:
                    cls.cam2 = cv2.VideoCapture(cls.cam2UsbDev, cv2.CAP_V4L2)
                    if not cls.cam2 or not cls.cam2.isOpened():
                        raise RuntimeError("USB camera not opened")
                cls.ctrl2 = CameraController(cls.cam2IsUsb, cls.cam2UsbDev)
                cls.event2 = CameraEvent()
                logger.debug(
                    "Thread %s: Camera.setSecondCamera - second camera initialized %s",
                    get_ident(),
                    cls.camNum2,
                )
                cfg.serverConfig.isLiveStream2 = False
            except RuntimeError as e:
                logger.error(
                    "Thread %s: Camera.setSecondCamera - Error %s", get_ident(), e
                )
                if not sc.errorc2:
                    sc.errorc2 = "Error while initializing camera: " + str(e)
                    sc.errorc22 = "Probably another process is using the camera."
                    if secondCamIsUsb == False:
                        sc.errorc2Source = "Picamera2"
                    else:
                        sc.errorc2Source = "CV2"
            except Exception as e:
                logger.error(
                    "Thread %s: Camera.setSecondCamera - Error %s", get_ident(), e
                )
                if not sc.errorc2:
                    sc.errorc2 = "Error while initializing camera: " + str(e)
                    if secondCamIsUsb == False:
                        sc.errorc2Source = "Picamera2"
                    else:
                        sc.errorc2Source = "CV2"

        cls.setStreamingConfigs()
        logger.debug(
            "Thread %s: Camera.setSecondCamera - second camera set to %s",
            get_ident(),
            cls.camNum2,
        )

        cameraPhotoSubPath = "photos/" + "camera_" + str(camNum2)
        fp = sc.photoRoot + "/" + cameraPhotoSubPath
        if not os.path.exists(fp):
            os.makedirs(fp)
            logger.debug(
                "Thread %s: Camera.setSecondCamera - Photo directory created %s",
                get_ident(),
                fp,
            )

    @classmethod
    def setStreamingConfigs(cls):
        """Set the configuration for streaming which will be used when cameras are switched"""
        logger.debug("Thread %s: Camera.setStreamingConfigs", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        trc = cfg.triggerConfig
        strc = cfg.streamingCfg
        logger.debug(
            "Thread %s: Camera.setStreamingConfigs - current streamingCfg: %s",
            get_ident(),
            strc,
        )

        # For active camera
        cn = str(sc.activeCamera)
        logger.debug(
            "Thread %s: Camera.setStreamingConfigs - for active camera %s",
            get_ident(),
            cn,
        )
        resetActive = False
        if cn in strc:
            scfg = strc[cn]
            logger.debug(
                "Thread %s: Camera.setStreamingConfigs - found in strc. scfg: %s",
                get_ident(),
                scfg,
            )
            if "camerainfo" in scfg:
                if scfg["camerainfo"] != sc.activeCameraInfo:
                    resetActive = True
                    logger.debug(
                        "Thread %s: Camera.setStreamingConfigs - Resetting active camera config for camera %s",
                        get_ident(),
                        cn,
                    )
                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(
                        f"Streaming configuration for {sc.activeCameraInfo} was reset due to camera model change"
                    )
                else:
                    # Check whether camera properties are available
                    if not "cameraproperties" in scfg:
                        logger.debug(
                            "Thread %s: Camera.setStreamingConfigs - StreamingConfig for active camera %s does not have camera properties",
                            get_ident(),
                            cn,
                        )
                        scfg["cameraproperties"] = copy.deepcopy(cfg.cameraProperties)
                        sc.unsavedChanges = True
                        sc.addChangeLogEntry(
                            f"Streaming configuration for {sc.activeCameraInfo} was extended with camera properties"
                        )
                # For USB cameras, check the status
                # The streaming config needs to be reset if it was initially created for the second camera
                # And has never been updated for the active camera
                if cls.camIsUsb == True:
                    if "is_ok" in scfg:
                        isOK = scfg["is_ok"]
                        if isOK == False:
                            resetActive = True
                            logger.debug(
                                "Thread %s: Camera.setStreamingConfigs - Resetting active camera config for camera %s due to is_OK=False",
                                get_ident(),
                                cn,
                            )
                            sc.unsavedChanges = True
                            sc.addChangeLogEntry(
                                f"Streaming configuration for {sc.activeCameraInfo} was reset due to camera status change"
                            )
                    else:
                        resetActive = True
                        logger.debug(
                            "Thread %s: Camera.setStreamingConfigs - Resetting active camera config for camera %s due to missing is_OK",
                            get_ident(),
                            cn,
                        )
                        sc.unsavedChanges = True
                        sc.addChangeLogEntry(
                            f"Streaming configuration for {sc.activeCameraInfo} was reset due to camera status change"
                        )
                if not "triggercamera" in scfg:
                    resetActive = True
                    logger.debug(
                        "Thread %s: Camera.setStreamingConfigs - StreamingConfig for active camera %s does not have triggercamera",
                        get_ident(),
                        cn,
                    )
                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(
                        f"Streaming configuration for {sc.activeCameraInfo} was extended with trigger camera settings"
                    )
            else:
                logger.debug(
                    "Thread %s: Camera.setStreamingConfigs - not found in strc.",
                    get_ident(),
                )
                resetActive = True
        else:
            resetActive = True
        if resetActive == True:
            logger.debug(
                "Thread %s: Camera.setStreamingConfigs - Active camera strc must be reset",
                get_ident(),
            )
            scfg = {}
            scfg["camnum"] = sc.activeCamera
            scfg["is_ok"] = True
            scfg["camerainfo"] = copy.copy(sc.activeCameraInfo)
            scfg["cameraproperties"] = copy.deepcopy(cfg.cameraProperties)
            scfg["hasfocus"] = cfg.cameraProperties.hasFocus
            if cls.camIsUsb == False:
                scfg["tuningconfig"] = copy.deepcopy(cfg.tuningConfig)
            scfg["liveconfig"] = copy.deepcopy(cfg.liveViewConfig)
            scfg["photoconfig"] = copy.deepcopy(cfg.photoConfig)
            scfg["rawconfig"] = copy.deepcopy(cfg.rawConfig)
            scfg["videoconfig"] = copy.deepcopy(cfg.videoConfig)
            scfg["controls"] = copy.deepcopy(cfg.controls)
            scfg["triggercamera"] = copy.deepcopy(trc.cameraSettings)
            strc[cn] = scfg
            logger.debug(
                "Thread %s: Camera.setStreamingConfigs - created  entry for active camera %s",
                get_ident(),
                cn,
            )
        else:
            if cn in strc:
                scfg = strc[cn]
                if not "camnum" in scfg:
                    scfg["camnum"] = sc.activeCamera
                    strc[cn] = scfg
        # Reset streaming config invalidation flag
        cfg.streamingCfgInvalid = False

        # For second camera
        if cls.cam2:
            cn = str(cls.camNum2)
            resetSecond = False
            if cn in strc:
                scfg = strc[cn]
                if "camerainfo" in scfg:
                    model = ""
                    for cfgCam in cfg.cameras:
                        if cfgCam.num == cls.camNum2:
                            model = cfgCam.model
                            break
                    newCamInfo = "Camera " + str(cls.camNum2) + " (" + model + ")"
                    if scfg["camerainfo"] != newCamInfo:
                        resetSecond = True
                        logger.debug(
                            "Thread %s: Camera.setStreamingConfigs - Resetting second camera config for camera %s",
                            get_ident(),
                            cn,
                        )
                        sc.unsavedChanges = True
                        sc.addChangeLogEntry(
                            f"Streaming configuration for {newCamInfo} was reset due to camera model change"
                        )
                else:
                    resetSecond = True
            else:
                resetSecond = True
            if resetSecond == True:
                scfg = {}
                model = ""
                for cfgCam in cfg.cameras:
                    if cfgCam.num == cls.camNum2:
                        model = cfgCam.model
                        break
                scfg["camnum"] = cls.camNum2
                scfg["camerainfo"] = "Camera " + cn + " (" + model + ")"

                if cls.cam2IsUsb == False:
                    scfg["is_ok"] = True
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
                        sizeHeight = int(
                            sizeWidth * pixelArraySize[1] / pixelArraySize[0]
                        )
                        if (sizeHeight % 2) != 0:
                            sizeHeight += 1
                        liveViewConfig.stream_size = (sizeWidth, sizeHeight)
                        liveViewConfig.stream_size_align = False
                        if (
                            sensorModes[0]["size"][0] == sizeWidth
                            and sensorModes[0]["size"][1] == sizeHeight
                        ):
                            liveViewConfig.sensor_mode = "0"
                        else:
                            liveViewConfig.sensor_mode = "custom"

                    videoConfig = CameraConfig()
                    videoConfig.id = "VIDO"
                    videoConfig.use_case = "Video"
                    videoConfig.buffer_count = 6
                    videoConfig.encode = "main"
                    videoConfig.controls["FrameDurationLimits"] = (33333, 33333)

                    if (
                        cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 1")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 2")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 3")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4")
                    ):
                        videoConfig.sensor_mode = 0
                        videoConfig.stream_size = sensorModes[0]["size"]
                        videoConfig.buffer_count = 2
                        liveViewConfig.buffer_count = 2
                    else:
                        videoConfig.sensor_mode = str(maxMode)
                        videoConfig.stream_size = sensorModes[maxMode]["size"]

                    photoConfig = CameraConfig()
                    photoConfig.id = "FOTO"
                    photoConfig.use_case = "Photo"
                    photoConfig.buffer_count = 1
                    photoConfig.encode = "main"
                    photoConfig.controls["FrameDurationLimits"] = (100, 1000000000)

                    if (
                        cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 1")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 2")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 3")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4")
                    ):
                        photoConfig.sensor_mode = 0
                        photoConfig.stream_size = sensorModes[0]["size"]
                    else:
                        photoConfig.sensor_mode = str(maxMode)
                        photoConfig.stream_size = sensorModes[maxMode]["size"]

                    rawConfig = CameraConfig()
                    rawConfig.id = "PRAW"
                    rawConfig.use_case = "Raw Photo"
                    rawConfig.buffer_count = 1
                    rawConfig.encode = "raw"
                    rawConfig.controls["FrameDurationLimits"] = (100, 1000000000)
                    rawConfig.sensor_mode = str(maxMode)
                    rawConfig.stream_size = sensorModes[maxMode]["size"]

                    scfg["hasfocus"] = hasFocus
                    scfg["tuningconfig"] = TuningConfig()
                    scfg["liveconfig"] = liveViewConfig
                    scfg["photoconfig"] = photoConfig
                    scfg["rawconfig"] = rawConfig
                    scfg["videoconfig"] = videoConfig
                    scfg["controls"] = copy.deepcopy(cfg.controls)
                else:
                    scfg["is_ok"] = False
                    hasFocus = False
                    pixelArraySize = None
                    sensorModes = []
                    maxMode = len(sensorModes) - 1

                    liveViewConfig = CameraConfig()
                    liveViewConfig.id = "LIVE"
                    liveViewConfig.use_case = "Live view"
                    liveViewConfig.stream = "main"
                    liveViewConfig.colour_space = "sRGB"
                    liveViewConfig.buffer_count = 1
                    liveViewConfig.queue = False
                    liveViewConfig.encode = "main"
                    liveViewConfig.controls["FrameDurationLimits"] = (33333, 33333)
                    sizeWidth = cfg.sensorModes[0].size[0]
                    sizeHeight = cfg.sensorModes[0].size[1]
                    liveViewConfig.stream_size = (sizeWidth, sizeHeight)
                    liveViewConfig.stream_size_align = False
                    liveViewConfig.sensor_mode = "0"
                    liveViewConfig.format = "YUYV"

                    videoConfig = CameraConfig()
                    videoConfig.id = "VIDO"
                    videoConfig.use_case = "Video"
                    videoConfig.colour_space = "sRGB"
                    videoConfig.buffer_count = 1
                    videoConfig.queue = False
                    videoConfig.encode = "main"
                    videoConfig.controls["FrameDurationLimits"] = (33333, 33333)
                    videoConfig.stream = "main"
                    videoConfig.sensor_mode = 0
                    videoConfig.stream_size = (640, 480)
                    videoConfig.stream_size_align = False
                    videoConfig.format = "YUYV"

                    photoConfig = CameraConfig()
                    photoConfig.id = "FOTO"
                    photoConfig.use_case = "Photo"
                    photoConfig.colour_space = "sRGB"
                    photoConfig.buffer_count = 1
                    photoConfig.queue = False
                    photoConfig.encode = "main"
                    photoConfig.controls["FrameDurationLimits"] = (100, 1000000000)
                    photoConfig.stream = "main"
                    photoConfig.sensor_mode = 0
                    photoConfig.stream_size = (640, 480)
                    photoConfig.stream_size_align = False
                    photoConfig.format = "YUYV"

                    rawConfig = CameraConfig()
                    rawConfig.id = "PRAW"
                    rawConfig.use_case = "Raw Photo"
                    rawConfig.colour_space = "sRGB"
                    rawConfig.buffer_count = 1
                    rawConfig.queue = False
                    rawConfig.encode = "raw"
                    rawConfig.controls["FrameDurationLimits"] = (100, 1000000000)
                    rawConfig.stream = "main"
                    rawConfig.sensor_mode = 0
                    rawConfig.stream_size = (640, 480)
                    rawConfig.stream_size_align = False
                    rawConfig.format = "tiff"

                    scfg["hasfocus"] = hasFocus
                    scfg["liveconfig"] = liveViewConfig
                    scfg["photoconfig"] = photoConfig
                    scfg["rawconfig"] = rawConfig
                    scfg["videoconfig"] = videoConfig
                    scfg["controls"] = copy.deepcopy(cfg.controls)

                strc[cn] = scfg
                logger.debug(
                    "Thread %s: Camera.setStreamingConfigs - created  entry for second camera %s",
                    get_ident(),
                    cn,
                )
            else:
                if cn in strc:
                    scfg = strc[cn]
                    if not "camnum" in scfg:
                        scfg["camnum"] = cls.camNum2
                        strc[cn] = scfg

    @classmethod
    def restoreConfigFromStreamingConfig(cls):
        """Restore active configuration and controls from a previously saved streaming config"""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        trc = cfg.triggerConfig
        strc = cfg.streamingCfg
        logger.debug("Thread %s: Camera.restoreConfigFromStreamingConfig for camera %s", get_ident(), sc.activeCamera)

        # For active camera
        cn = str(sc.activeCamera)
        if cn in strc:
            scfg = strc[cn]
            if sc.activeCameraIsUsb:
                if "is_ok" in scfg:
                    isOK = scfg["is_ok"]
                    if isOK == False:
                        logger.debug(
                            "Thread %s: Camera.restoreConfigFromStreamingConfig - Streaming config for active camera %s is not OK, skipping restore",
                            get_ident(),
                            cn,
                        )
                        return
            if "liveconfig" in scfg:
                cfg.liveViewConfig = copy.deepcopy(scfg["liveconfig"])
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - restored liveViewConfig from streaming config %s",
                    get_ident(),
                    cn,
                )
            if "photoconfig" in scfg:
                cfg.photoConfig = copy.deepcopy(scfg["photoconfig"])
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - restored photoconfig from streaming config %s",
                    get_ident(),
                    cn,
                )
            if "rawconfig" in scfg:
                cfg.rawConfig = copy.deepcopy(scfg["rawconfig"])
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - restored rawconfig from streaming config %s",
                    get_ident(),
                    cn,
                )
            if "videoconfig" in scfg:
                cfg.videoConfig = copy.deepcopy(scfg["videoconfig"])
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - restored videoconfig from streaming config %s",
                    get_ident(),
                    cn,
                )
            if "controls" in scfg:
                cfg.controls = copy.deepcopy(scfg["controls"])
                # Camera.resetScalerCropRequested = False
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - restored controls from streaming config %s",
                    get_ident(),
                    cn,
                )
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - cfgCtrls=%s",
                    get_ident(),
                    scfg["controls"].__dict__,
                )
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - cfg.controls=%s",
                    get_ident(),
                    cfg.controls.__dict__,
                )
            if "triggercamera" in scfg:
                trc.cameraSettings = copy.deepcopy(scfg["triggercamera"])
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - Trigger camera settings restored from streaming config for camera %s",
                    get_ident(),
                    cn,
                )
            else:
                trc.setCameraSettingsToDefault()
                logger.debug(
                    "Thread %s: Camera.restoreConfigFromStreamingConfig - Trigger camera settings set to defaults for camera %s",
                    get_ident(),
                    cn,
                )
            logger.debug(
                "Thread %s: Camera.restoreConfigFromStreamingConfig - restored config and controls from streaming config %s",
                get_ident(),
                cn,
            )
        else:
            trc.setCameraSettingsToDefault()
            logger.debug(
                "Thread %s: Camera.restoreConfigFromStreamingConfig - Trigger camera settings set to defaults for camera %s",
                get_ident(),
                cn,
            )

    @staticmethod
    def configure(cfg: CameraConfig, cfgPhoto: CameraConfig):
        """The function creates and configures a CameraConfiguration
        based on given configuration settings cfg.

        The fully configured configuration is returned
        """
        logger.debug("Thread %s: Camera.configure", get_ident())
        # We start configuration with a new blank CameraConfiguration object
        camCfg = CameraConfiguration()

        camCfg.use_case = cfg.use_case
        camCfg.transform = Transform(
            vflip=cfg.transform_vflip, hflip=cfg.transform_hflip
        )
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
        logger.debug(
            "Thread %s: Camera.configure: configuration completed", get_ident()
        )

        # Automatically align the stream size, if selected
        if cfg.stream_size_align and cfg.sensor_mode == "custom":
            logger.debug(
                "Thread %s: Camera.configure: Aligning camera configuration. Old size: %s",
                get_ident(),
                cfg.stream_size,
            )
            camCfg.align()
            logger.debug(
                "Thread %s: Camera.configure: Alignment successful. Adjusting stream size",
                get_ident(),
            )
            cfg.stream_size = camCfg.size
            logger.debug(
                "Thread %s: Camera.configure: Stream size adjusted to %s",
                get_ident(),
                cfg.stream_size,
            )

        return camCfg

    @staticmethod
    def requiresTimeForAutoAlgos() -> bool:
        """Check if the camera requires time for auto algorithms to settle
        Returns True, if the camera is a Pi 4 or Pi 5
        """
        logger.debug("Thread %s: Camera.requiresTimeForAutoAlgos", get_ident())
        cfgCtrls = CameraCfg().controls
        res = False
        if cfgCtrls.include_aeEnable and cfgCtrls.aeEnable == True:
            res = True
        if cfgCtrls.include_awbEnable and cfgCtrls.awbEnable == True:
            res = True
        if CameraCfg().cameraProperties.hasFocus == True:
            if cfgCtrls.include_afMode and cfgCtrls.afMode != 0:
                res = True
        return res

    @staticmethod
    def applyMappedControlToUsbCamera(
        ctrl: str,
        ctrls: dict,
        isBool: bool,
        usbCc: dict,
        camDev: str,
    ):
        """Apply a mapped control to a USB camera

        Values of the raspiCamSrv Control are mapped to USB camera control values.

        ctrl        : The control to be applied
        ctrls       : The controls to be applied
        isBool      : Indicates if the control value is boolean
        usbCc       : The USB camera controls mapping
        camDev      : The camera device identifier  
        """
        logger.debug(
            "Thread %s: Camera.applyMappedControlToUsbCamera - ctrl: %s", get_ident(), ctrl
        )
        if ctrl in ctrls and ctrls[ctrl] is not None:
            logger.debug("Thread %s: Camera.applyMappedControlToUsbCamera - applying: %s ", get_ident(), ctrl)
            if isBool == True:
                if ctrls[ctrl] == True:
                    cfgVal = "1"
                else:
                    cfgVal = "0"
            else:
                cfgVal = str(ctrls[ctrl])
            if "mapping" in usbCc[ctrl]:
                mapping = usbCc[ctrl]["mapping"]
                if cfgVal in mapping:
                    camVal = mapping[cfgVal]
                    ctrlName = usbCc[ctrl]["ctrlName"]
                    try:
                        subprocess.run(["v4l2-ctl", "-d", camDev, f"--set-ctrl={ctrlName}={camVal}"])
                        logger.debug(
                            "Thread %s: Camera.applyMappedControlToUsbCamera - camDev: %s set ctrl %s to %s",
                            get_ident(),
                            camDev,
                            ctrlName,
                            camVal,
                        )
                    except Exception as e:
                        logger.error(
                            "Camera.applyMappedControlToUsbCamera - camDev: %s Error setting %s to %s: %s",
                            camDev,
                            ctrlName,
                            camVal,
                            e,
                        )
        else:
            logger.debug(
                "Thread %s: Camera.applyMappedControlToUsbCamera - ctrl: %s not applied (not in ctrls)",
                get_ident(),
                ctrl,
            )

    @staticmethod
    def applyDirectControlToUsbCamera(
        ctrl: str,
        ctrls: dict,
        usbCc: dict,
        camDev: str,
    ):
        """Apply a control directly to a USB camera

        Values of the raspiCamSrv Control are scaled to USB camera control values.

        ctrl        : The control to be applied
        ctrls       : The controls to be applied
        usbCc       : The USB camera controls mapping
        camDev      : The camera device identifier  
        """
        logger.debug(
            "Thread %s: Camera.applyDirectControlToUsbCamera - ctrl: %s", get_ident(), ctrl
        )
        if ctrl in ctrls and ctrls[ctrl] is not None:
            logger.debug("Thread %s: Camera.applyDirectControlToUsbCamera - applying: %s ", get_ident(), ctrl)
            camVal = ctrls[ctrl]
            if ctrl == "LensPosition":
                camVal = 1.0 / camVal
            if usbCc[ctrl]["type"] == "int":
                camVal = int(camVal)
            ctrlName = usbCc[ctrl]["ctrlName"]
            try:
                subprocess.run(["v4l2-ctl", "-d", camDev, f"--set-ctrl={ctrlName}={camVal}"])
                logger.debug(
                    "Thread %s: Camera.applyScaledControlToUsbCamera - camDev: %s set ctrl %s to %s",
                    get_ident(),
                    camDev,
                    ctrlName,
                    camVal,
                )
            except Exception as e:
                logger.error(
                    "Camera.applyScaledControlToUsbCamera - camDev: %s Error setting %s to %s: %s",
                    camDev,
                    ctrlName,
                    camVal,
                    e,
                )
        else:
            logger.debug(
                "Thread %s: Camera.applyScaledControlToUsbCamera - ctrl: %s not applied (not in ctrls)",
                get_ident(),
                ctrl,
            )

    @staticmethod
    def applyControlsToUsbCamera(
        ctrls: dict,
        toCam2: bool = False
    ):
        """Apply controls to a USB camera

        This method is called before images are captured from a USB camera.
        It can be used to set camera properties, e.g. via v4l2-ctl commands.
        ctrls       : The controls to be applied
        toCam2      : If true, controls are set for the second camera
        """
        logger.debug(
            "Thread %s: Camera.applyControlsToUsbCamera - toCam2: %s ctrls: %s", get_ident(), toCam2, ctrls
        )
        cfg = CameraCfg()
        cc = cfg.controls
        usbCc = cc.usbCamControls
        if toCam2 == False:
            camNum = Camera.camNum
            camDev = Camera.camUsbDev
        else:
            camNum = Camera.camNum2
            camDev = Camera.cam2UsbDev
        logger.debug("Thread %s: Camera.applyControlsToUsbCamera - camNum: %s camDev: %s", get_ident(), camNum, camDev)

        # Auto White Balance
        Camera.applyMappedControlToUsbCamera("AwbEnable", ctrls, True, usbCc, camDev)

        # Auto White Balance Mode
        Camera.applyMappedControlToUsbCamera("AwbMode", ctrls, False, usbCc, camDev)

        # Sharpness
        Camera.applyDirectControlToUsbCamera("Sharpness", ctrls, usbCc, camDev)

        # Brightness
        Camera.applyDirectControlToUsbCamera("Brightness", ctrls, usbCc, camDev)

        # Contrast
        Camera.applyDirectControlToUsbCamera("Contrast", ctrls, usbCc, camDev)

        # Saturation
        Camera.applyDirectControlToUsbCamera("Saturation", ctrls, usbCc, camDev)

        # AfMode
        Camera.applyMappedControlToUsbCamera("AfMode", ctrls, False, usbCc, camDev)

        # LensPosition
        Camera.applyDirectControlToUsbCamera("LensPosition", ctrls, usbCc, camDev)

    @staticmethod
    def usbFrameApplyControls(
        frame,
        log = False,
        exceptCtrl=None, exceptValue=None, toCam2=None
    ):
        """Apply the currently selected camera controls to a frame captured from a USB camera

        frame       : Frame captured from the USB camera
        log         : If true, log debug information (to prevent logging for each frame in video mode)
        exceptCtrl  : Exception control. Optionally, one exceptional control can be specified
                      If specified, the exceptValue will replace the value fom CameraCfg().controls
                      Currently supported:
                      - ExposureTime
                      - AnalogueGain
                      - FocalDistance -> LensPosition = 1 / FocalDistance
        toCam2      : If true, controls are set for the second camera with control data from streamingCfg

        Returns     : The frame with applied controls
        """
        if toCam2 is None:
            toCam2 = False

        if log:
            logger.debug(
                "Thread %s: Camera.usbFrameApplyControls - toCam2: %s", get_ident(), toCam2
            )

        cfg = CameraCfg()
        if toCam2 is False:
            cfgCtrls = cfg.controls
        else:
            cfgCtrls = cfg.streamingCfg[str(Camera.camNum2)]["controls"]
        
        if log:
            logger.debug(
                "Thread %s: Camera.usbFrameApplyControls - cfgCtrls=%s",
                get_ident(),
                cfgCtrls.__dict__,
            )
        
        newFrame = frame

        ctrls = {}
        cnt = 0

        # Apply selected controls
        # Scaler crop
        if cfgCtrls.include_scalerCrop:
            ctrls["ScalerCrop"] = cfgCtrls.scalerCrop
            cnt += 1

            hFrame, wFrame = frame.shape[:2]
            if log:
                logger.debug(
                    "Thread %s: Camera.usbFrameApplyControls - Frame size: width=%s height=%s",
                    get_ident(),
                    wFrame,
                    hFrame,
                )
            X, Y, W, H = Camera.getUsbScalerCrop(wFrame, hFrame, log=log, forCam2=toCam2)
            x, y, w, h = cfgCtrls.scalerCrop
            if log:
                logger.debug("Thread %s: Camera.usbFrameApplyControls - ScalerCrop Frame is %s", get_ident(), (X, Y, W, H))
                logger.debug("Thread %s: Camera.usbFrameApplyControls - Cropping to %s", get_ident(), (x, y, w, h))
            xc = x + int(w/2)
            yc = y + int(h/2)
            if log:
                logger.debug("Thread %s: Camera.usbFrameApplyControls - Crop center is %s", get_ident(), (xc, yc))

            aspectRatioFrame = W / H
            aspectRatioCrop = w / h
            if aspectRatioFrame > aspectRatioCrop:
                # Frame is wider than crop aspect ratio -> increase width
                wNew = int(h * aspectRatioFrame)
                hNew = h
                if log:
                    logger.debug("Thread %s: Camera.usbFrameApplyControls - Frame is wider than crop aspect ratio. New size is %s", get_ident(), (wNew, hNew))
            else:
                # Frame is taller than crop aspect ratio -> increase height
                wNew = w
                hNew = int(w / aspectRatioFrame)
                if log:
                    logger.debug("Thread %s: Camera.usbFrameApplyControls - Frame is taller than crop aspect ratio. New size is %s", get_ident(), (wNew, hNew))
            if wNew > W:
                wNew = W
            if hNew > H:
                hNew = H

            scaleToFrame = W / wFrame
            wNew = int(wNew / scaleToFrame)
            hNew = int(hNew / scaleToFrame)
            xc = int((xc - X) / scaleToFrame)
            yc = int((yc - Y) / scaleToFrame)

            x1 = xc - int(wNew / 2)
            if x1 < 0:
                x1 = 0
            y1 = yc - int(hNew / 2)
            if y1 < 0:
                y1 = 0
            x2 = x1 + wNew
            if x2 > wFrame:
                x2 = wFrame
            y2 = y1 + hNew
            if y2 > hFrame:
                y2 = hFrame
            if log:
                logger.debug("Thread %s: Camera.usbFrameApplyControls - Cropping coordinates are x1=%s y1=%s x2=%s y2=%s", get_ident(), x1, y1, x2, y2)
            cropped = frame[y1:y2, x1:x2]
            newFrame = cv2.resize(cropped, (wFrame, hFrame), interpolation=cv2.INTER_LINEAR)
            if log:
                logger.debug("Thread %s: Camera.usbFrameApplyControls - Cropping and resizing done", get_ident())
        return newFrame

    @staticmethod
    def applyControls(
        camCfg: CameraConfig, exceptCtrl=None, exceptValue=None, toCam2=None
    ):
        """Apply the currently selected camera controls
        camCfg      : Configuration from which controls shall be taken with priority
        exceptCtrl  : Exception control. Optionally, one exceptional control can be specified
                      If specified, the exceptValue will replace the value fom CameraCfg().controls
                      Currently supported:
                      - ExposureTime
                      - AnalogueGain
                      - FocalDistance -> LensPosition = 1 / FocalDistance
        toCam2      : If true, controls are set for the second camera with control data from streamingCfg
        """
        logger.debug(
            "Thread %s: Camera.applyControls - toCam2: %s", get_ident(), toCam2
        )

        logger.debug(
            "Thread %s: Camera.applyControls - camCfg.controls=%s",
            get_ident(),
            camCfg.controls,
        )
        cfg = CameraCfg()
        if toCam2 is None:
            cfgCtrls = cfg.controls
        else:
            cfgCtrls = cfg.streamingCfg[str(Camera.camNum2)]["controls"]
        logger.debug(
            "Thread %s: Camera.applyControls - cfgCtrls=%s",
            get_ident(),
            cfgCtrls.__dict__,
        )

        # Initialize controls dict with controls included in configuration
        # ctrls = copy.deepcopy(camCfg.controls)
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
        if (
            cfgCtrls.include_aeConstraintMode
            and "AeConstraintMode" not in camCfg.controls
        ):
            ctrls["AeConstraintMode"] = cfgCtrls.aeConstraintMode
            cnt += 1
        if cfgCtrls.include_aeFlickerMode and "AeFlickerMode" not in camCfg.controls:
            ctrls["AeFlickerMode"] = cfgCtrls.aeFlickerMode
            cnt += 1
        if (
            cfgCtrls.include_aeFlickerPeriod
            and "AeFlickerPeriod" not in camCfg.controls
        ):
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
        if (
            cfgCtrls.include_frameDurationLimits
            and "FrameDurationLimits" not in camCfg.controls
        ):
            ctrls["FrameDurationLimits"] = (
                cfgCtrls.frameDurationLimitMax,
                cfgCtrls.frameDurationLimitMin,
            )
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
        if (
            cfgCtrls.include_noiseReductionMode
            and "NoiseReductionMode" not in camCfg.controls
        ):
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
        logger.debug(
            "Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s",
            get_ident(),
            cfg.liveViewConfig.controls,
        )
        logger.debug(
            "Thread %s: Camera.applyControls - include_scalerCrop=%s",
            get_ident(),
            cfgCtrls.include_scalerCrop,
        )
        if cfgCtrls.include_scalerCrop and "ScalerCrop" not in camCfg.controls:
            ctrls["ScalerCrop"] = cfgCtrls.scalerCrop
            cnt += 1
        logger.debug(
            "Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s",
            get_ident(),
            cfg.liveViewConfig.controls,
        )
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

        logger.debug(
            "Thread %s: Camera.applyControls - Applying %s controls", get_ident(), cnt
        )
        logger.debug("Thread %s: Camera.applyControls - ctrls=%s", get_ident(), ctrls)
        if toCam2 is None:
            if Camera.camIsUsb == False:
                camCtrls = Controls(Camera.cam)
                prgLogger.debug("camCtrls = Controls(picam2)")
                prgLogger.debug("ctrls = %s", ctrls)
                camCtrls.set_controls(ctrls)
                prgLogger.debug("camCtrls.set_controls(ctrls)")
                Camera.cam.controls = camCtrls
                # Camera.cam.controls.set_controls(ctrls)
                prgLogger.debug("picam2.controls = camCtrls")
                logger.debug(
                    "Thread %s: Camera.applyControls - id(Camera)=%s id(Camera.cam)=%s id(Camera.cam.controls)=%s",
                    get_ident(),
                    id(Camera),
                    id(Camera.cam),
                    id(Camera.cam.controls),
                )
                logger.debug(
                    "Thread %s: Camera.applyControls - Camera.cam.controls=%s",
                    get_ident(),
                    Camera.cam.controls,
                )
            else:
                camCtrls = ctrls
                Camera.applyControlsToUsbCamera(ctrls)
        else:
            if Camera.cam2IsUsb == False:
                camCtrls = Controls(Camera.cam2)
                camCtrls.set_controls(ctrls)
                Camera.cam2.controls = camCtrls
                logger.debug(
                    "Thread %s: Camera.applyControls - Camera.cam2.controls=%s",
                    get_ident(),
                    Camera.cam2.controls,
                )
            else:
                camCtrls = ctrls
                Camera.applyControlsToUsbCamera(ctrls, toCam2=True)
        return camCtrls

    @staticmethod
    def applyControlsForAfCycle(camCfg: CameraConfig):
        """Apply camera controls required for AF cycle"""
        logger.debug("Thread %s: Camera.applyControlsForAfCycle", get_ident())

        cfg = CameraCfg()
        cfgCtrls = cfg.controls

        # Initialize controls dict with controls included in configuration
        # ctrls = copy.deepcopy(camCfg.controls)
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

        logger.debug(
            "Thread %s: Camera.applyControlsForAfCycle - Applying %s controls",
            get_ident(),
            cnt,
        )
        camCtrls = Controls(Camera.cam)
        prgLogger.debug("camCtrls = Controls(picam2)")
        prgLogger.debug("ctrls = %s", ctrls)
        camCtrls.set_controls(ctrls)
        prgLogger.debug("camCtrls.set_controls(ctrls)")
        Camera.cam.controls = camCtrls
        prgLogger.debug("picam2.controls = camCtrls")
        logger.debug(
            "Thread %s: Camera.applyControlsForAfCycle - Camera.cam.controls=%s",
            get_ident(),
            Camera.cam.controls,
        )

    @staticmethod
    def applyControlsForLivestream(wait: float = None):
        """Apply active controls if livestream is active"""
        logger.debug("Thread %s: Camera.applyControlsForLivestream", get_ident())
        if Camera.thread:
            if wait:
                time.sleep(wait)
            Camera.applyControls(Camera.ctrl.configuration)
            if Camera.camIsUsb:
                Camera.logUsbFrameApplyControls = True
            logger.debug(
                "Thread %s: Camera.applyControlsForLivestream - Controlls applied",
                get_ident(),
            )

    @staticmethod
    def stopCameraSystem():
        logger.debug("Thread %s: Camera.stopCameraSystem", get_ident())
        logger.debug(
            "Thread %s: Camera.stopCameraSystem: Stopping Live view thread", get_ident()
        )
        Camera.stopRequested = True
        if Camera.thread:
            cnt = 0
            while Camera.thread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    break
            if Camera.thread:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Live view thread did not stop within 2 sec",
                    get_ident(),
                )
            else:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Live view thread successfully stopped",
                    get_ident(),
                )
        else:
            logger.debug(
                "Thread %s: Camera.stopCameraSystem: Live view thread was not active",
                get_ident(),
            )
        Camera.stopRequested = False

        logger.debug(
            "Thread %s: Camera.stopCameraSystem: Stopping Video thread", get_ident()
        )
        Camera.stopVideoRequested = True
        if Camera.videoThread:
            cnt = 0
            while Camera.videoThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    break
            if Camera.videoThread:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Video thread did not stop within 2 sec",
                    get_ident(),
                )
            else:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Video thread successfully stopped",
                    get_ident(),
                )
        else:
            logger.debug(
                "Thread %s: Camera.stopCameraSystem: Video thread was not active",
                get_ident(),
            )
        Camera.stopVideoRequested = False
        Camera.videoDuration = 0

        logger.debug(
            "Thread %s: Camera.stopCameraSystem: Stopping Photoseries thread",
            get_ident(),
        )
        Camera.stopPhotoSeriesRequested = True
        if Camera.photoSeriesThread:
            cnt = 0
            while Camera.photoSeriesThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 500:
                    break
            if Camera.photoSeriesThread:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Photoseries thread did not stop within 5 sec",
                    get_ident(),
                )
            else:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Photoseries thread successfully stopped",
                    get_ident(),
                )
        else:
            logger.debug(
                "Thread %s: Camera.stopCameraSystem: Photoseries thread was not active",
                get_ident(),
            )
        Camera.stopPhotoSeriesRequested = False

        if Camera.ctrl:
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
                    logger.debug(
                        "Thread %s: Camera.stopCameraSystem: Live view thread 2 did not stop within 2 sec",
                        get_ident(),
                    )
                else:
                    logger.debug(
                        "Thread %s: Camera.stopCameraSystem: Live view thread 2 successfully stopped",
                        get_ident(),
                    )
            else:
                logger.debug(
                    "Thread %s: Camera.stopCameraSystem: Live view thread 2 was not active",
                    get_ident(),
                )
            Camera.stopRequested2 = False
            if Camera.ctrl2:
                Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)

    @classmethod
    def _thread(cls):
        """Camera background thread."""
        logger.debug("Thread %s: Camera._thread", get_ident())
        frames_iterator = None

        if Camera().when_streaming_1_starts:
            Camera().when_streaming_1_starts()

        try:
            if Camera.camIsUsb == False:
                frames_iterator = cls.frames()
            else:
                frames_iterator = cls.framesUsb()
            logger.debug(
                "Thread %s: Camera._thread - frames_iterator instantiated", get_ident()
            )
            for frame, frameRaw in frames_iterator:
                Camera.frame = frame
                Camera.frameRaw = frameRaw
                # logger.debug("Thread %s: Camera._thread - received frame from camera -> notifying clients", get_ident())
                Camera.event.set()  # send signal to clients
                time.sleep(0)

                Camera.threadLock.acquire()

                stop = False
                # Check whether stop is requested
                if Camera.stopRequested:
                    frames_iterator.close()
                    Camera.stopRequested = False
                    stop = True
                    logger.debug(
                        "Thread %s: Camera._thread - Thread is requested to stop.",
                        get_ident(),
                    )
                    break

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - Camera.last_access > 10:
                    frames_iterator.close()
                    stop = True
                    logger.debug(
                        "Thread %s: Camera._thread - Stopping camera thread due to inactivity.",
                        get_ident(),
                    )
                    break

                # Release lock if not stopping
                if stop == False:
                    Camera.threadLock.release()
        except UsbCameraNoFrameReceivedError as fe:
            Camera.threadLock.acquire()
            if frames_iterator:
                frames_iterator.close()
            Camera.event.set()
            Camera.event.clear()
        except UsbCameraOpenError as ue:
            Camera.threadLock.acquire()
            if frames_iterator:
                frames_iterator.close()
            Camera.event.set()
            Camera.event.clear()
        except Exception as e:
            Camera.threadLock.acquire()
            logger.error("Thread %s: Camera._thread - Exception: %s", get_ident(), e)
            if frames_iterator:
                frames_iterator.close()
            Camera.event.set()
            Camera.event.clear()
            CameraCfg().serverConfig.error = "Error in live view: " + str(e)
            CameraCfg().serverConfig.error2 = (
                "Probably, a different camera configuration can solve the problem."
            )
            CameraCfg().serverConfig.errorSource = "Camera._thread"

        sc = CameraCfg().serverConfig

        closeCam = True
        if sc.isVideoRecording == True or cls.isVideoRecording() == True:
            closeCam = False
            logger.debug(
                "Thread %s: Camera._thread - isVideoRecording -> Camera not closing",
                get_ident(),
            )
        if sc.isPhotoSeriesRecording == True:
            ser = Camera.photoSeries
            if ser:
                if ser.isExposureSeries == True or ser.isFocusStackingSeries == True:
                    closeCam = False
                    logger.debug(
                        "Thread %s: Camera._thread - Exposure- or PhotoStack series -> Camera not closing",
                        get_ident(),
                    )
                else:
                    nextTime = ser.nextTime()
                    curTime = datetime.datetime.now()
                    timedif = nextTime - curTime
                    timedifSec = timedif.total_seconds()
                    if timedifSec < 60:
                        logger.debug(
                            "Thread %s: Camera._thread - Photo series next shot within 60 sec -> Camera not closing",
                            get_ident(),
                        )
                        closeCam = False
        if closeCam == True:
            logger.debug("Thread %s: Camera._thread - Closing camera", get_ident())
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        sc.isLiveStream = False

        if Camera().when_streaming_1_stops:
            Camera().when_streaming_1_stops()

        if Camera.threadLock.locked():
            Camera.threadLock.release()

        Camera.thread = None
        logger.debug("Thread %s: Camera._thread - Terminated", get_ident())

    @classmethod
    def _thread2(cls):
        """Camera background thread 2."""
        logger.debug("Thread %s: Camera._thread2", get_ident())
        frames_iterator = None

        if Camera().when_streaming_2_starts:
            Camera().when_streaming_2_starts()

        try:
            if Camera.cam2IsUsb == False:
                frames_iterator = cls.frames2()
            else:
                frames_iterator = cls.frames2Usb()
            logger.debug(
                "Thread %s: Camera._thread2 - frames_iterator instantiated", get_ident()
            )
            for frame, frameRaw in frames_iterator:
                Camera.frame2 = frame
                Camera.frame2Raw = frameRaw
                # logger.debug("Thread %s: Camera._thread2 - received frame from camera -> notifying clients", get_ident())
                Camera.event2.set()  # send signal to clients
                time.sleep(0)

                # Acquire lock to avoid clients accessing the stream while it is closing down
                # logger.debug("Thread %s: Camera._thread2 - About to acquire Lock: thread2Lock=%s.", get_ident(), Camera.thread2Lock.locked())
                Camera.thread2Lock.acquire()
                # logger.debug("Thread %s: Camera._thread2 - Lock acquired: thread2Lock=%s.", get_ident(), Camera.thread2Lock.locked())
                stop = False
                # Check whether stop is requested
                if Camera.stopRequested2:
                    frames_iterator.close()
                    Camera.stopRequested2 = False
                    stop = True
                    logger.debug(
                        "Thread %s: Camera._thread2 - Thread is requested to stop.",
                        get_ident(),
                    )
                    break

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - Camera.last_access2 > 10:
                    frames_iterator.close()
                    stop = True
                    logger.debug(
                        "Thread %s: Camera._thread2 - Stopping camera thread due to inactivity.",
                        get_ident(),
                    )
                    break

                # Release lock if not stopping
                if stop == False:
                    Camera.thread2Lock.release()
                    # logger.debug("Thread %s: Camera._thread2 - Lock released: thread2Lock=%s.", get_ident(), Camera.thread2Lock.locked())
        except Exception as e:
            Camera.thread2Lock.acquire()
            logger.error("Thread %s: Camera._thread2 - Exception: %s", get_ident(), e)
            if frames_iterator:
                frames_iterator.close()
            Camera.event2.set()
            Camera.event2.clear()
            CameraCfg().serverConfig.errorc2 = "Error in camera 2 stream: " + str(e)
            CameraCfg().serverConfig.errorc22 = (
                "Probably, a different camera configuration can solve the problem."
            )
            CameraCfg().serverConfig.errorc2Source = "Camera._thread2"

        Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)
        CameraCfg().serverConfig.isLiveStream2 = False

        if Camera().when_streaming_2_stops:
            Camera().when_streaming_2_stops()

        if Camera.thread2Lock.locked():
            Camera.thread2Lock.release()
            logger.debug(
                "Thread %s: Camera._thread2 - Lock released: thread2Lock=%s.",
                get_ident(),
                Camera.thread2Lock.locked(),
            )

        Camera.thread2 = None

        logger.debug("Thread %s: Camera._thread2 - Exit.", get_ident())

    @staticmethod
    def framesUsb():
        logger.debug("Thread %s: Camera.framesUsb", get_ident())
        srvCam = CameraCfg()

        try:
            cc, cr = Camera.ctrl.requestConfig(srvCam.photoConfig)
            if cc:
                # If the request for photoConfig caused a configuration change, restart with a new configuration
                Camera.ctrl.clearConfig()
                Camera.ctrl.requestConfig(srvCam.photoConfig)
            Camera.ctrl.requestConfig(srvCam.rawConfig, cfgPhoto=srvCam.photoConfig)
            Camera.ctrl.requestConfig(srvCam.liveViewConfig)
            Camera.cam, started = Camera.ctrl.requestStart(
                Camera.cam,
                Camera.camNum,
                Camera.camIsUsb,
                Camera.camUsbDev,
                forActiveCamera=True,
            )
            if not started:
                Camera.cam, excl = Camera.ctrl.requestCameraForConfig(
                    Camera.cam, Camera.camNum, cfg=None, forLiveStream=True
                )
            else:
                if Camera.cam.isOpened():
                    logger.debug(
                        "Thread %s: Camera.framesUsb - camera started", get_ident()
                    )
                else:
                    logger.error(
                        "Thread %s: Camera.framesUsb - camera not opened", get_ident()
                    )
                    raise RuntimeError("USB camera could not be opened")

            # Camera.applyControls(Camera.ctrl.configuration)
            # logger.debug("Thread %s: Camera.framesUsb - controls applied", get_ident())
            # time.sleep(0.5)
        except Exception as e:
            logger.error("Thread %s: Camera.framesUsb - Exception: %s", get_ident(), e)
            raise

        cfg = Camera.ctrl.configuration
        hflip = cfg.transform.hflip
        vflip = cfg.transform.vflip
        logger.debug(
            "Thread %s: Camera.framesUsb - hflip=%s vflip=%s",
            get_ident(),
            hflip,
            vflip,
        )
        gotScalerCropLiveView = False
        try:
            cnt = 0
            Camera.logUsbFrameApplyControls = True
            while True:
                if Camera.cam.isOpened() == False:
                    raise UsbCameraOpenError("USB camera not open during live view")
                success, frame = Camera.cam.read()
                if not success:
                    time.sleep(0.01)
                    cnt += 1
                    if cnt > 100:
                        raise UsbCameraNoFrameReceivedError("No frame received from USB camera for live view")
                else:
                    if gotScalerCropLiveView == False:
                        # Get the live view scaler crop
                        if Camera.resetScalerCropRequested == True:
                            Camera.resetScalerCropUsb()
                        metadata = Camera.getUsbCamMetadata(Camera.cam)
                        srvCam.scalerCropLiveView = metadata["ScalerCrop"]
                        gotScalerCropLiveView = True
                    # logger.debug("Thread %s: Camera.framesUsb - Received frame from camera", get_ident())
                    # Apply controls for each frame to allow dynamic changes
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, log=Camera.logUsbFrameApplyControls)
                    Camera.logUsbFrameApplyControls = False
                    # Encode frame as JPEG
                    ret, buffer = cv2.imencode(".jpg", frame)
                    frameEncoded = buffer.tobytes()
                    yield frameEncoded, frame
        except UsbCameraNoFrameReceivedError as ue:
            logger.debug(
                "Thread %s: Camera.framesUsb - No frame received after 1 sec",
                get_ident(),
            )
            raise
        except UsbCameraOpenError as ue:
            logger.debug(
                        "Thread %s: Camera.framesUsb - camera not opened during streaming",
                        get_ident(),
                    )
            raise
        except Exception as e:
            logger.error("Thread %s: Camera.framesUsb - Exception: %s", get_ident(), e)
            raise

    @staticmethod
    def frames():
        logger.debug("Thread %s: Camera.frames", get_ident())
        srvCam = CameraCfg()
        try:
            cc, cr = Camera.ctrl.requestConfig(srvCam.photoConfig)
            if cc:
                # If the request for photoConfig caused a configuration change, restart with a new configuration
                Camera.ctrl.clearConfig()
                Camera.ctrl.requestConfig(srvCam.photoConfig)
            Camera.ctrl.requestConfig(srvCam.rawConfig, cfgPhoto=srvCam.photoConfig)
            Camera.ctrl.requestConfig(srvCam.liveViewConfig)
            Camera.cam, started = Camera.ctrl.requestStart(
                Camera.cam,
                Camera.camNum,
                Camera.camIsUsb,
                Camera.camUsbDev,
                forActiveCamera=True,
            )
            if not started:
                Camera.cam, excl = Camera.ctrl.requestCameraForConfig(
                    Camera.cam, Camera.camNum, cfg=None, forLiveStream=True
                )
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
            Camera.streamOutput = StreamingOutput()
            prgLogger.debug("output = None")
            encoder = MJPEGEncoder()
            prgLogger.debug("encoder = MJPEGEncoder()")
            Camera.cam.start_encoder(
                encoder,
                FileOutput(Camera.streamOutput),
                name=srvCam.liveViewConfig.stream,
            )
            prgLogger.debug(
                'picam2.start_encoder(encoder, FileOutput(output), name="%s")',
                srvCam.liveViewConfig.stream,
            )
            prgLogger.debug("time.sleep(videoDuration)")
            Camera.ctrl.registerEncoder(Camera.ENCODER_LIVESTREAM, encoder)
            logger.debug("Thread %s: Camera.frames - encoder started", get_ident())

            # Get the live view scaler crop
            metadata = Camera.cam.capture_metadata()
            srvCam.serverConfig.scalerCropLiveView = metadata["ScalerCrop"]
            while True:
                # logger.debug("Thread %s: Camera.frames - Receiving camera stream", get_ident())
                with Camera.streamOutput.condition:
                    # logger.debug("Thread %s: Camera.frames - waiting", get_ident())
                    Camera.streamOutput.condition.wait()
                    # logger.debug("Thread %s: Camera.frames - waiting done", get_ident())
                    frame = Camera.streamOutput.frame
                    l = len(frame)
                # logger.debug("Thread %s: Camera.frames - got frame with length %s", get_ident(), l)
                yield frame, None
        except Exception as e:
            logger.error("Thread %s: Camera.frames - Exception: %s", get_ident(), e)
            raise

    @staticmethod
    def frames2Usb():
        logger.debug("Thread %s: Camera.frames2Usb", get_ident())
        srvCam = CameraCfg()

        Camera.ctrl2.requestConfig(
            srvCam.streamingCfg[str(Camera.camNum2)]["videoconfig"]
        )
        Camera.ctrl2.requestConfig(
            srvCam.streamingCfg[str(Camera.camNum2)]["liveconfig"]
        )
        Camera.cam2, started = Camera.ctrl2.requestStart(
            Camera.cam2,
            Camera.camNum2,
            Camera.cam2IsUsb,
            Camera.cam2UsbDev,
            forActiveCamera=False,
        )
        if not started:
            logger.error("Second camera did not start")
            raise RuntimeError("Second camera did not start")
        else:
            logger.debug("Thread %s: Camera.frames2Usb - camera started", get_ident())

        cfg = Camera.ctrl2.configuration
        hflip = cfg.transform.hflip
        vflip = cfg.transform.vflip
        Camera.logUsbFrame2ApplyControls = True
        try:
            while True:
                # logger.debug("Thread %s: Camera.frames2Usb - Receiving camera stream", get_ident())
                success, frame = Camera.cam2.read()
                if not success:
                    break
                else:
                    # Apply controls for each frame to allow dynamic changes
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, log=Camera.logUsbFrame2ApplyControls, toCam2=True)
                    Camera.logUsbFrame2ApplyControls = False
                    # Encode frame as JPEG
                    ret, buffer = cv2.imencode(".jpg", frame)
                    frameEncoded = buffer.tobytes()
                yield frameEncoded, frame
        except Exception as e:
            logger.error("Thread %s: Camera.frames2Usb - Exception: %s", get_ident(), e)
            raise

    @staticmethod
    def frames2():
        logger.debug("Thread %s: Camera.frames2", get_ident())
        srvCam = CameraCfg()

        Camera.ctrl2.requestConfig(
            srvCam.streamingCfg[str(Camera.camNum2)]["videoconfig"]
        )
        Camera.ctrl2.requestConfig(
            srvCam.streamingCfg[str(Camera.camNum2)]["liveconfig"]
        )

        Camera.cam2, started = Camera.ctrl2.requestStart(
            Camera.cam2,
            Camera.camNum2,
            Camera.cam2IsUsb,
            Camera.cam2UsbDev,
            forActiveCamera=False,
        )
        if not started:
            logger.error("Second camera did not start")
            raise RuntimeError("Second camera did not start")
        else:
            logger.debug("Thread %s: Camera.frames2 - camera started", get_ident())

        Camera.applyControls(Camera.ctrl2.configuration, toCam2=True)
        logger.debug("Thread %s: Camera.frames2 - controls applied", get_ident())
        time.sleep(0.5)

        try:
            Camera.stream2Output = StreamingOutput()
            encoder = MJPEGEncoder()
            Camera.cam2.start_encoder(
                encoder,
                FileOutput(Camera.stream2Output),
                name=srvCam.streamingCfg[str(Camera.camNum2)]["liveconfig"].stream,
            )
            Camera.ctrl2.registerEncoder(Camera.ENCODER_LIVESTREAM, encoder)
            logger.debug("Thread %s: Camera.frames2 - encoder started", get_ident())

            while True:
                # logger.debug("Thread %s: Camera.frames2 - Receiving camera stream", get_ident())
                with Camera.stream2Output.condition:
                    # logger.debug("Thread %s: Camera.frames2 - waiting", get_ident())
                    Camera.stream2Output.condition.wait()
                    # logger.debug("Thread %s: Camera.frames2 - waiting done", get_ident())
                    frame = Camera.stream2Output.frame
                    l = len(frame)
                # logger.debug("Thread %s: Camera.frames2 - got frame with length %s", get_ident(), l)
                yield frame, None
        except Exception as e:
            logger.error("Thread %s: Camera.frames2 - Exception: %s", get_ident(), e)
            raise

    @staticmethod
    def getUsbScalerCrop(width: int, height: int, log=True, forCam2=None) -> tuple:
        """Get ScalerCrop for a given size for USB camera
        
            Determine ScalerCrop assuming that the camera will first crop to the requested aspect ratio
            and then scale to the requested resolution
        """
        if forCam2 is None:
            forCam2 = False
        if log:
            logger.debug("Thread %s: Camera.getUsbScalerCrop - width: %d, height: %d forCam2: %s", get_ident(), width, height, forCam2)
        aspectRatio = width / height
        cfg = CameraCfg()
        if forCam2 == False:
            sensorWidth = cfg.cameraProperties.pixelArraySize[0]
            sensorHeight = cfg.cameraProperties.pixelArraySize[1]
        else:
            cam2Str = str(Camera.camNum2)
            strCfg = cfg.streamingCfg[cam2Str]
            if "cameraproperties" in strCfg:
                cam2Props = strCfg["cameraproperties"]
                sensorWidth = cam2Props.pixelArraySize[0]
                sensorHeight = cam2Props.pixelArraySize[1]
            else:
                sensorWidth = cfg.cameraProperties.pixelArraySize[0]
                sensorHeight = cfg.cameraProperties.pixelArraySize[1]
        if log:
            logger.debug("Thread %s: Camera.getUsbScalerCrop - sensorWidth: %d, sensorHeight: %d", get_ident(), sensorWidth, sensorHeight)
        sensorAspectRatio = sensorWidth / sensorHeight
        if aspectRatio > sensorAspectRatio:
            # Crop height
            cropHeight = sensorWidth / aspectRatio
            cropY = (sensorHeight - cropHeight) / 2
            scalerCrop = (
                0,
                int(cropY),
                sensorWidth,
                int(cropHeight),
            )
        else:
            # Crop width
            cropWidth = sensorHeight * aspectRatio
            cropX = (sensorWidth - cropWidth) / 2
            scalerCrop = (
                int(cropX),
                0,
                int(cropWidth),
                sensorHeight,
            )
        if log:
            logger.debug("Thread %s: Camera.getUsbScalerCrop - scalerCrop: %s", get_ident(), scalerCrop)
        return scalerCrop

    @staticmethod
    def getUsbCamMetadata(cam, log=True) -> dict:
        """Get metadata from USB camera using OpenCV"""
        logger.debug("Thread %s: Camera.getUsbCamMetadata", get_ident())

        width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cfg = CameraCfg()
        sc = cfg.serverConfig
        cc = cfg.controls
        if width > 0 and height > 0:
            if cc.include_scalerCrop == True:
                scalerCrop = cc.scalerCrop
                # Map scalerCrop for LiveView to current resolution
                if width != cfg.liveViewConfig.stream_size[0] or height != cfg.liveViewConfig.stream_size[1]:
                    aspectRatioLiveView = cfg.liveViewConfig.stream_size[0] / cfg.liveViewConfig.stream_size[1]
                    aspectRatioCurrent = width / height
                    if aspectRatioLiveView != aspectRatioCurrent:
                        x1, y1, w, h = scalerCrop
                        if aspectRatioCurrent > aspectRatioLiveView:
                            # Extend width
                            newW = h * aspectRatioCurrent
                            newX1 = x1 - (newW - w) / 2
                            scalerCrop = (
                                int(newX1),
                                y1,
                                int(newW),
                                h,
                            )
                        else:
                            # Extend height
                            newH = w / aspectRatioCurrent
                            newY1 = y1 - (newH - h) / 2
                            scalerCrop = (
                                x1,
                                int(newY1),
                                w,
                                int(newH),
                            )
            else:
                scalerCrop = Camera.getUsbScalerCrop(width, height)
        else:
            scalerCrop = sc.scalerCropMax

        metadata = {
            "Width": width,
            "Height": height,
            "ScalerCrop": scalerCrop,
            "FPS": cam.get(cv2.CAP_PROP_FPS),
            "Format (FOURCC)": int(cam.get(cv2.CAP_PROP_FOURCC)),
            "Format": "".join(
                [chr((int(cam.get(cv2.CAP_PROP_FOURCC)) >> 8 * i) & 0xFF) for i in range(4)]
            ),
            "Brightness": cam.get(cv2.CAP_PROP_BRIGHTNESS),
            "Contrast": cam.get(cv2.CAP_PROP_CONTRAST),
            "Saturation": cam.get(cv2.CAP_PROP_SATURATION),
            "Hue": cam.get(cv2.CAP_PROP_HUE),
            "Gain": cam.get(cv2.CAP_PROP_GAIN),
            "Exposure": cam.get(cv2.CAP_PROP_EXPOSURE),
            "Exposure": cam.get(cv2.CAP_PROP_EXPOSURE),
            "White Balance Temperature": cam.get(cv2.CAP_PROP_WB_TEMPERATURE),
            "White Balance Auto WB": cam.get(cv2.CAP_PROP_AUTO_WB),
            "Focus": cam.get(cv2.CAP_PROP_FOCUS),
            "Autofocus": cam.get(cv2.CAP_PROP_AUTOFOCUS),
            }
        return metadata

    @staticmethod
    def takeImage(
        filename: str,
        keepExclusive: bool = False,
        noEvents: bool = False,
        alternatePath: str = "",
    ) -> str:
        """Takes a photo with the specified file name and returns the path

        filename:       file name for the photo
        keepExclusive:  If True, keep the exclusive mode
                        This can be used for example if a jpg photo shall be taken
                        before a video is recorded
        noEvents:       If True, no events are triggered
        alternatePath:  If not empty, the file path of the photo,
                        otherwise the standard photo path is taken
                        and the display buffer is not updated

        """
        logger.debug(
            "Thread %s: Camera.takeImage - filename: %s keepExclusive: %s",
            get_ident(),
            filename,
            keepExclusive,
        )
        fp = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig

        if noEvents == False:
            logger.debug(
                "Thread %s: Camera.takeImage Checking for callback: when_photo_taken=%s",
                get_ident(),
                Camera().when_photo_taken,
            )
            if Camera().when_photo_taken:
                Camera().when_photo_taken()
        try:
            forceExclusive = False
            if Camera.camIsUsb == True:
                forceExclusive = True
            logger.debug(
                "Thread %s: Camera.takeImage Requesting camera for photoConfig",
                get_ident(),
            )
            Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(
                Camera.cam, Camera.camNum, cfg.photoConfig, forceExclusive=forceExclusive
            )
            logger.debug(
                "Thread %s: Camera.takeImage Got camera for photoConfig exclusive: %s",
                get_ident(),
                exclusive,
            )

            Camera.applyControls(Camera.ctrl.configuration)
            logger.debug("Thread %s: Camera.takeImage - controls applied", get_ident())

            if Camera.camIsUsb == False:
                logger.debug(
                    "Thread %s: Camera.takeImage - Camera.cam.controls=%s",
                    get_ident(),
                    Camera.cam.controls,
                )
                request = Camera.cam.capture_request()
                prgLogger.debug("request = picam2.capture_request()")
                logger.debug("Thread %s: Camera.takeImage: Request started", get_ident())
            path = sc.photoRoot + "/" + sc.cameraPhotoSubPath
            if alternatePath != "":
                path = alternatePath
            fp = path + "/" + filename
            if Camera.camIsUsb == False:
                request.save(cfg.photoConfig.stream, fp)
                prgLogger.debug(
                    'request.save("%s", "%s")',
                    cfg.photoConfig.stream,
                    sc.prgOutputPath + "/" + filename,
                )
            else:
                # For USB cameras, save the image using OpenCV
                if Camera.cam.isOpened() == False:
                    raise RuntimeError("USB camera is not opened")
                success, frame = Camera.cam.read()
                if success:
                    conf = Camera.ctrl.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, log=True)
                    cv2.imwrite(fp, frame)
                else:
                    raise RuntimeError("Failed to capture image from USB camera")
            logger.debug(
                "Thread %s: Camera.takeImage: Image saved as %s", get_ident(), fp
            )
            if alternatePath == "":
                sc.displayFile = filename
                sc.displayPhoto = sc.cameraPhotoSubPath + "/" + filename
                sc.isDisplayHidden = False
                if Camera.camIsUsb == False:
                    metadata = request.get_metadata()
                    prgLogger.debug("metadata = request.get_metadata()")
                else:
                    metadata = Camera.getUsbCamMetadata(Camera.cam)
                sc.displayMeta = {"Camera": sc.activeCameraInfo}
                sc.displayMeta.update(metadata)
                sc.displayMetaFirst = 0
                if len(metadata) < 11:
                    sc._displayMetaLast = 999
                else:
                    sc.displayMetaLast = 10
                sc.displayHistogram = None
            logger.debug(
                "Thread %s: Camera.takeImage: Image metedata captured", get_ident()
            )
            if Camera.camIsUsb == False:
                request.release()
                prgLogger.debug("request.release()")
                logger.debug("Thread %s: Camera.takeImage: Request released", get_ident())

            if not keepExclusive:
                Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
                if (
                    sc.isPhotoSeriesRecording == False
                    and sc.isVideoRecording == False
                    and sc.isLiveStream == False
                ):
                    Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        except Exception as e:
            logger.error("Thread %s: Camera.takeImage: Error %s", get_ident(), e)
            if not sc.error:
                sc.error = "Phototaking caused error: " + str(e)
                sc.errorSource = "Camera.takeImage"
        Camera.liveViewDeactivated = False
        return fp

    @staticmethod
    def takeImage2(
        filename: str,
        keepExclusive: bool = False,
        noEvents: bool = False,
        alternatePath: str = "",
    ) -> str:
        """Takes a photo with second camera with the specified file name and returns the path

        filename:       file name for the photo
        keepExclusive:  If True, keep the exclusive mode
                        This can be used for example if a jpg photo shall be taken
                        before a video is recorded
        noEvents:       If True, no events are triggered
        alternatePath:  If not empty, the file path of the photo,
                        otherwise the standard photo path is taken
                        and the display buffer is not updated

        """
        logger.debug(
            "Thread %s: Camera.takeImage2 - filename: %s keepExclusive: %s",
            get_ident(),
            filename,
            keepExclusive,
        )
        fp = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig

        if noEvents == False:
            logger.debug(
                "Thread %s: Camera.takeImage2 Checking for callback: when_photo_taken=%s",
                get_ident(),
                Camera().when_photo_taken,
            )
            if Camera().when_photo_2_taken:
                Camera().when_photo_2_taken()
        try:
            photoConfig = cfg.streamingCfg[str(Camera.camNum2)]["photoconfig"]
            forceExclusive = False
            if Camera.cam2IsUsb == True:
                forceExclusive = True
            logger.debug(
                "Thread %s: Camera.takeImage2 Requesting camera for photoConfig",
                get_ident(),
            )
            Camera.cam2, exclusive = Camera.ctrl2.requestCameraForConfig(
                Camera.cam2, Camera.camNum2, photoConfig, forActiveCamera=False, forceExclusive=forceExclusive
            )
            logger.debug(
                "Thread %s: Camera.takeImage2 Got camera for photoConfig exclusive: %s",
                get_ident(),
                exclusive,
            )

            Camera.applyControls(Camera.ctrl2.configuration, toCam2=True)
            logger.debug("Thread %s: Camera.takeImage2 - controls applied", get_ident())

            if Camera.cam2IsUsb == False:
                logger.debug(
                    "Thread %s: Camera.takeImage2 - Camera.cam2.controls=%s",
                    get_ident(),
                    Camera.cam2.controls,
                )
                request = Camera.cam2.capture_request()
                prgLogger.debug("request = picam2.capture_request()")
                logger.debug("Thread %s: Camera.takeImage2: Request started", get_ident())
            cameraPhotoSubPath = "photos/" + "camera_" + str(Camera.camNum2)
            path = sc.photoRoot + "/" + cameraPhotoSubPath
            if alternatePath != "":
                path = alternatePath
            fp = path + "/" + filename
            if Camera.cam2IsUsb == False:
                request.save(photoConfig.stream, fp)
                prgLogger.debug(
                    'request.save("%s", "%s")',
                    photoConfig.stream,
                    sc.prgOutputPath + "/" + filename,
                )
            else:
                # For USB cameras, save the image using OpenCV
                if Camera.cam2.isOpened() == False:
                    raise RuntimeError("USB camera 2 is not opened")
                success, frame = Camera.cam2.read()
                if success:
                    conf = Camera.ctrl2.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, log=True, toCam2=True)
                    cv2.imwrite(fp, frame)
                else:
                    raise RuntimeError("Failed to capture image from USB camera")
            logger.debug(
                "Thread %s: Camera.takeImage2: Image saved as %s", get_ident(), fp
            )
            if Camera.cam2IsUsb == False:
                request.release()
                prgLogger.debug("request.release()")
                logger.debug("Thread %s: Camera.takeImage2: Request released", get_ident())

            if not keepExclusive:
                Camera.cam2 = Camera.ctrl2.restoreLivestream2(Camera.cam2, exclusive)
                if sc.isVideoRecording2 == False and sc.isLiveStream2 == False:
                    Camera.cam2, done = Camera.ctrl2.requestStop(
                        Camera.cam2, close=True
                    )
        except Exception as e:
            logger.error("Thread %s: Camera.takeImage2: Error %s", get_ident(), e)
            if not sc.errorc2:
                sc.errorc2 = "Phototaking caused error: " + str(e)
                sc.errorc2Source = "Camera.takeImage2"
        Camera.liveView2Deactivated = False
        return fp

    @staticmethod
    def quickPhoto(fp: str, saveImage: bool = True) -> tuple:
        """Take a photo assuming that the camera is started
        
        Parameters:
            fp:         File path where the photo shall be saved
            saveImage:  True: save image to file
                        False: do not save image but return frame
        Returns:
            done:   True if photo was saved to file
            err:    Error message if any
            img:    Image frame if saveImage is False
        """
        logger.debug("Thread %s: Camera.quickPhoto - filename: %s", get_ident(), fp)
        done = False
        err = ""
        frameRaw = None
        cfg = CameraCfg()
        if Camera.camIsUsb == False:
            if Camera.cam.started:
                try:
                    if saveImage == True:
                        request = Camera.cam.capture_request()
                        request.save(cfg.photoConfig.stream, fp)
                        request.release()
                        done = True
                    else:
                        request = Camera.cam.capture_request()
                        frameRaw = Camera.cam.capture_array(cfg.liveViewConfig.stream)
                        if cfg.liveViewConfig.format == "YUV420":
                            if cv2Available == True:
                                frameRaw = cv2.cvtColor(frameRaw, cv2.COLOR_YUV2BGR_I420)
                        request.release()
                except Exception as e:
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            if Camera.cam.isOpened() == True:
                frame, frameRaw = Camera().get_frame()
                if saveImage == True:
                    cv2.imwrite(fp, frameRaw)
                    done = True
            else:
                err = "USB Camera not started"
        return (done, err, copy.copy(frameRaw))

    @staticmethod
    def quickUsbVideoThread(out):
        """Record a video from a USB camera"""
        logger.debug(
            "Thread %s: Camera.quickUsbVideoThread - starting recording", get_ident()
        )
        done = False
        if Camera.cam.isOpened() == False:
            logger.error(
                "Thread %s: Camera.quickUsbVideoThread - USB camera not opened", get_ident()
            )
            done = True
        if out.isOpened() == False:
            logger.error(
                "Thread %s: Camera.quickUsbVideoThread - VideoWriter not opened", get_ident()
            )
            done = True
        while not done:
            logger.debug("Thread %s: Camera.quickUsbVideoThread - acquiring lock - locked: %s", get_ident(), Camera.threadUsbVideoLock.locked())
            Camera.threadUsbVideoLock.acquire()
            logger.debug("Thread %s: Camera.quickUsbVideoThread - getting frame", get_ident())
            frame, frameRaw = Camera().get_frame()
            logger.debug("Thread %s: Camera.quickUsbVideoThread - got frame", get_ident())
            out.write(frameRaw)
            logger.debug("Thread %s: Camera.quickUsbVideoThread - wrote frame", get_ident())
            if Camera.stopUsbVideoRequested == True:
                done = True
            Camera.threadUsbVideoLock.release()
        logger.debug(
            "Thread %s: Camera.quickUsbVideoThread - stopping recording", get_ident()
        )

        if Camera.threadUsbVideoLock.locked():
            Camera.threadUsbVideoLock.release()
        Camera.threadUsbVideo = None

    @staticmethod
    def quickVideoStart(fp: str) -> tuple:
        """Record a video assuming that the camera is started"""
        logger.debug(
            "Thread %s: Camera.quickVideoStart - filename: %s", get_ident(), fp
        )
        encoder = None
        done = False
        err = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        if Camera.camIsUsb == False:
            if Camera.cam.started:
                try:
                    encoder = H264Encoder()
                    output = fp
                    if output.lower().endswith(".mp4"):
                        if sc.recordAudio == False:
                            encoder.output = FfmpegOutput(output, audio=False)
                        else:
                            encoder.output = FfmpegOutput(
                                output, audio=True, audio_sync=sc.audioSync
                            )
                    else:
                        encoder.output = FileOutput(output)

                    stream = cfg.videoConfig.stream
                    # For Pi Zero take video with liveView (lowres stream)
                    # The lower buffer size of these devices is too small for full size video
                    # and we do not want to switch mode
                    if (
                        cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi Zero")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 4")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 3")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 2")
                        or cfg.serverConfig.raspiModelFull.startswith("Raspberry Pi 1")
                    ):
                        stream = cfg.liveViewConfig.stream
                    Camera.cam.start_encoder(encoder, name=stream)
                    done = True
                except Exception as e:
                    logger.error(
                        "Thread %s: Camera.quickVideoStart - error when starting encoder: %s",
                        get_ident(),
                        e,
                    )
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            if Camera.cam.isOpened() == True:
                frameRate = 30
                Camera.cam.set(cv2.CAP_PROP_FPS, frameRate)
                fourcc = cv2.VideoWriter_fourcc(*"avc1")
                width = int(Camera.cam.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(Camera.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
                out = cv2.VideoWriter(fp, fourcc, frameRate, (width, height))
                logger.debug(
                    "Thread %s: Camera.quickVideoStart - starting quickUsbVideoThread", get_ident()
                )
                Camera.stopUsbVideoRequested = False
                Camera.threadUsbVideo = threading.Thread(
                    target=Camera.quickUsbVideoThread, args=(out,)
                )
                Camera.threadUsbVideo.start()
                encoder = out
                done = True
            else:
                err = "USB Camera not started"
        return (done, encoder, err)

    @staticmethod
    def quickVideoStop(encoder) -> tuple:
        """Stop a video recording that the camera is started"""
        logger.debug("Thread %s: Camera.quickVideoStop", get_ident())
        done = False
        err = ""
        if Camera.camIsUsb == False:
            if Camera.cam.started:
                try:
                    Camera.cam.stop_encoder(encoder)
                    done = True
                except Exception as e:
                    logger.error(
                        "Thread %s: Camera.quickVideoStop - error when stopping encoder: %s",
                        get_ident(),
                        e,
                    )
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            if Camera.threadUsbVideo:
                logger.debug(
                    "Thread %s: Camera.quickVideoStop - stopping quickUsbVideoThread", get_ident()
                )
                with Camera.threadUsbVideoLock:
                    Camera.stopUsbVideoRequested = True
                while Camera.threadUsbVideo:
                    time.sleep(0.1)
                encoder.release()
                logger.debug(
                    "Thread %s: Camera.quickVideoStop - quickUsbVideoThread stopped",
                    get_ident(),
                )
                Camera.stopUsbVideoRequested = False
                done = True
            else:
                err = "USB video thread not running"
        return (done, err)

    @staticmethod
    def startCircular(buffersizeSec=5) -> tuple:
        """Start encoder for circular output"""
        logger.debug("Thread %s: Camera.startCircular", get_ident())
        encoder = None
        circ = None
        done = False
        err = ""
        cfg = CameraCfg()
        if Camera.camIsUsb == False:
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
                    logger.error(
                        "Thread %s: Camera.startCircular - error when starting encoder: %s",
                        get_ident(),
                        e,
                    )
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            err = "USB camera does not support circular recording"
        return (done, circ, encoder, err)

    @staticmethod
    def stopCircular(encoder) -> tuple:
        """Stop encoder for circular output"""
        logger.debug("Thread %s: Camera.stopCircular", get_ident())
        done = False
        err = ""
        if Camera.camIsUsb == False:
            if Camera.cam.started:
                try:
                    Camera.cam.stop_encoder(encoder)
                    done = True
                except Exception as e:
                    logger.error(
                        "Thread %s: Camera.stopCircular - error when stopping encoder: %s",
                        get_ident(),
                        e,
                    )
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            err = "USB camera does not support circular recording"
        return (done, err)

    @staticmethod
    def recordCircular(circ: CircularOutput, fp: str) -> tuple:
        """Start recording circular output"""
        logger.debug("Thread %s: Camera.recordCircular - file: %s", get_ident(), fp)
        done = False
        err = ""
        if Camera.camIsUsb == False:
            if Camera.cam.started:
                try:
                    circ.fileoutput = fp
                    circ.start()
                    done = True
                except Exception as e:
                    logger.error(
                        "Thread %s: Camera.recordCircular - error when starting circular: %s",
                        get_ident(),
                        e,
                    )
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            err = "USB camera does not support circular recording"
        return (done, err)

    @staticmethod
    def stopRecordingCircular(circ: CircularOutput) -> tuple:
        """Start recording circular output"""
        logger.debug("Thread %s: Camera.stopRecordingCircular", get_ident())
        done = False
        err = ""
        if Camera.camIsUsb == False:
            if Camera.cam.started:
                try:
                    circ.stop()
                    done = True
                except Exception as e:
                    logger.error(
                        "Thread %s: Camera.stopRecordingCircular - error when stopping circular: %s",
                        get_ident(),
                        e,
                    )
                    err = str(e)
            else:
                err = "Camera not started"
        else:
            err = "USB camera does not support circular recording"
        return (done, err)

    @staticmethod
    def takeRawImage(
        filenameRaw: str, filename: str, noEvents: bool = False, alternatePath: str = ""
    ):
        """Takes a photo as well as a raw image with the specified file names
        and returns the path for the raw photo
        filenameRaw: file name for the raw image
        filename:    file name for the photo
        noEvents:       If True, no events are triggered
        alternatePath:  If not empty, the file path of the photo,
                        otherwise the standard photo path is taken
                        and the display buffer is not updated
        """
        logger.debug("Thread %s: Camera.takeRawImage", get_ident())
        fpr = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig

        if noEvents == False:
            logger.debug(
                "Thread %s: Camera.takeImage Checking for callback: when_photo_taken=%s",
                get_ident(),
                Camera().when_photo_taken,
            )
            if Camera().when_photo_taken:
                Camera().when_photo_taken()

        try:
            forceExclusive = False
            if Camera.camIsUsb == True:
                forceExclusive = True
            logger.debug(
                "Thread %s: Camera.takeRawImage Requesting camera for rawConfig",
                get_ident(),
            )
            Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(
                Camera.cam, Camera.camNum, cfg.rawConfig, cfg.photoConfig, forceExclusive=forceExclusive
            )
            logger.debug(
                "Thread %s: Camera.takeRawImage Got camera for rawConfig exclusive: %s",
                get_ident(),
                exclusive,
            )

            Camera.applyControls(Camera.ctrl.configuration)
            logger.debug(
                "Thread %s: Camera.takeRawImage: controls applied", get_ident()
            )

            if Camera.camIsUsb == False:
                request = Camera.cam.capture_request()
                prgLogger.debug("request = picam2.capture_request()")
                logger.debug("Thread %s: Camera.takeRawImage: Request started", get_ident())
            path = sc.photoRoot + "/" + sc.cameraPhotoSubPath
            if alternatePath != "":
                path = alternatePath
            fp = path + "/" + filename
            fpr = path + "/" + filenameRaw
            if Camera.camIsUsb == False:
                request.save("main", fp)
                prgLogger.debug(
                    'request.save("main", "%s")', sc.prgOutputPath + "/" + filename
                )
                request.save_dng(fpr)
                prgLogger.debug('request.save_dng("%s")', fpr)
            else:
                # For USB cameras, save the image using OpenCV
                if Camera.cam.isOpened() == False:
                    raise RuntimeError("USB camera is not opened")
                success, frame = Camera.cam.read()
                if success:
                    conf = Camera.ctrl.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, log=True)
                    cv2.imwrite(fp, frame)
                    cv2.imwrite(fpr, frame, [cv2.IMWRITE_TIFF_COMPRESSION, 1])
                else:
                    raise RuntimeError("Failed to capture image from USB camera")
            logger.debug(
                "Thread %s: Camera.takeRawImage: Raw Image saved as %s",
                get_ident(),
                fpr,
            )
            if alternatePath == "":
                sc.displayFile = filenameRaw
                sc.displayPhoto = sc.cameraPhotoSubPath + "/" + filename
                sc.isDisplayHidden = False
                if Camera.camIsUsb == False:
                    metadata = request.get_metadata()
                    prgLogger.debug("metadata = request.get_metadata()")
                else:
                    metadata = Camera.getUsbCamMetadata(Camera.cam)
                sc.displayMeta = {"Camera": sc.activeCameraInfo}
                sc.displayMeta.update(metadata)
                sc.displayMetaFirst = 0
                if len(metadata) < 11:
                    sc._displayMetaLast = 999
                else:
                    sc.displayMetaLast = 10
                sc.displayHistogram = None
                logger.debug(
                    "Thread %s: Camera.takeRawImage: Raw Image metedata captured",
                    get_ident(),
                )
            if Camera.camIsUsb == False:
                request.release()
                prgLogger.debug("request.release()")
            logger.debug(
                "Thread %s: Camera.takeRawImage: Request released", get_ident()
            )

            Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
            if (
                sc.isPhotoSeriesRecording == False
                and sc.isVideoRecording == False
                and sc.isLiveStream == False
            ):
                Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        except Exception as e:
            logger.error("Thread %s: Camera.takeRawImage: Error %s", get_ident(), e)
            if not sc.error:
                sc.error = "Taking raw photo caused error: " + str(e)
                sc.errorSource = "Camera.takeRawImage"
        Camera.liveViewDeactivated = False
        return fpr

    @staticmethod
    def takeRawImage2(
        filenameRaw: str, filename: str, noEvents: bool = False, alternatePath: str = ""
    ):
        """Takes a photo as well as a raw image with the specified file names
        and returns the path for the raw photo
        filenameRaw: file name for the raw image
        filename:    file name for the photo
        noEvents:       If True, no events are triggered
        alternatePath:  If not empty, the file path of the photo,
                        otherwise the standard photo path is taken
                        and the display buffer is not updated
        """
        logger.debug("Thread %s: Camera.takeRawImage2", get_ident())
        fpr = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig

        if noEvents == False:
            logger.debug(
                "Thread %s: Camera.takeRawImage2 Checking for callback: when_photo_2_taken=%s",
                get_ident(),
                Camera().when_photo_2_taken,
            )
            if Camera().when_photo_2_taken:
                Camera().when_photo_2_taken()

        try:
            forceExclusive = False
            if Camera.cam2IsUsb == True:
                forceExclusive = True
            rawConfig = cfg.streamingCfg[str(Camera.camNum2)]["rawconfig"]
            photoConfig = cfg.streamingCfg[str(Camera.camNum2)]["photoconfig"]
            logger.debug(
                "Thread %s: Camera.takeRawImage2 Requesting camera for rawConfig",
                get_ident(),
            )
            Camera.cam2, exclusive = Camera.ctrl2.requestCameraForConfig(
                Camera.cam2,
                Camera.camNum2,
                rawConfig,
                photoConfig,
                forActiveCamera=False,
                forceExclusive=forceExclusive,
            )
            logger.debug(
                "Thread %s: Camera.takeRawImage2 Got camera for rawConfig exclusive: %s",
                get_ident(),
                exclusive,
            )

            Camera.applyControls(Camera.ctrl2.configuration, toCam2=True)
            logger.debug(
                "Thread %s: Camera.takeRawImage2: controls applied", get_ident()
            )

            if Camera.cam2IsUsb == False:
                request = Camera.cam2.capture_request()
                prgLogger.debug("request = picam2.capture_request()")
                logger.debug(
                    "Thread %s: Camera.takeRawImage2: Request started", get_ident()
                )
            cameraPhotoSubPath = "photos/" + "camera_" + str(Camera.camNum2)
            path = sc.photoRoot + "/" + cameraPhotoSubPath
            if alternatePath != "":
                path = alternatePath
            fp = path + "/" + filename
            fpr = path + "/" + filenameRaw
            if Camera.cam2IsUsb == False:
                request.save(photoConfig.stream, fp)
                prgLogger.debug(
                    'request.save("%s", "%s")',
                    photoConfig.stream,
                    sc.prgOutputPath + "/" + filename,
                )
                request.save_dng(fpr)
                prgLogger.debug('request.save_dng("%s")', fpr)
            else:
                # For USB cameras, save the image using OpenCV
                if Camera.cam2.isOpened() == False:
                    raise RuntimeError("USB camera is not opened")
                success, frame = Camera.cam2.read()
                if success:
                    conf = Camera.ctrl2.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, log=True, toCam2=True)
                    cv2.imwrite(fp, frame)
                    cv2.imwrite(fpr, frame, [cv2.IMWRITE_TIFF_COMPRESSION, 1])
                else:
                    raise RuntimeError("Failed to capture image from USB camera")
            logger.debug(
                "Thread %s: Camera.takeRawImage2: Raw Image saved as %s",
                get_ident(),
                fpr,
            )
            if Camera.cam2IsUsb == False:
                request.release()
                prgLogger.debug("request.release()")
                logger.debug(
                    "Thread %s: Camera.takeRawImage2: Request released", get_ident()
                )

            Camera.cam2 = Camera.ctrl2.restoreLivestream2(Camera.cam2, exclusive)
            if sc.isVideoRecording2 == False and sc.isLiveStream2 == False:
                Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)
        except Exception as e:
            logger.error("Thread %s: Camera.takeRawImage2: Error %s", get_ident(), e)
            if not sc.errorc2:
                sc.errorc2 = "Taking raw photo caused error: " + str(e)
                sc.errorc2Source = "Camera.takeRawImage2"
        Camera.liveView2Deactivated = False
        return fpr

    @staticmethod
    def _videoThreadUsb():
        logger.debug("Thread %s: Camera._videoThreadUsb", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig

        logger.debug(
            "Thread %s: Camera._videoThreadUsb - Requesting camera for videoConfig",
            get_ident(),
        )
        Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(
            Camera.cam, Camera.camNum, cfg.videoConfig, forceExclusive=True
        )
        logger.debug(
            "Thread %s: Camera._videoThreadUsb - Got camera for videoConfig exclusive: %s",
            get_ident(),
            exclusive,
        )

        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera._videoThreadUsb - controls applied", get_ident())

        # frameRate = Camera.cam.get(cv2.CAP_PROP_FPS)
        frameRate = 14.5
        Camera.cam.set(cv2.CAP_PROP_FPS, frameRate)
        logger.debug("Thread %s: Camera._videoThreadUsb - frameRate is %s", get_ident(), frameRate)

        # Codec for MP4 (most compatible)
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        width = int(Camera.cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(Camera.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.debug("Thread %s: Camera._videoThreadUsb - width:%s, height:%s", get_ident(), width, height)
        logger.debug("Thread %s: Camera._videoThreadUsb - videoOutput:%s", get_ident(), Camera.videoOutput)

        out = cv2.VideoWriter(Camera.videoOutput, fourcc, frameRate, (width, height))
        logger.debug("Thread %s: Camera._videoThreadUsb - VideoWriter created", get_ident())

        try:
            videoStart = time.time()
            duration = float(Camera.videoDuration)
            logger.debug(
                "Thread %s: Camera._videoThreadUsb - video started at %s, duration is %s",
                get_ident(),
                videoStart,
                duration,
            )

            if duration > 0.0:
                elapsed = time.time() - videoStart
                while elapsed <= duration:
                    ret, frame = Camera.cam.read()
                    if not ret:
                        break
                    conf = Camera.ctrl.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame)
                    out.write(frame)
                    if Camera.stopVideoRequested == True:
                        logger.debug(
                            "Thread %s: Camera._videoThreadUsb - stop video requested", get_ident()
                        )
                        break
                    elapsed = time.time() - videoStart
                sc.isVideoRecording = False
                sc.isAudioRecording = False
            else:
                while Camera.stopVideoRequested == False:
                    ret, frame = Camera.cam.read()
                    if not ret:
                        break
                    conf = Camera.ctrl.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame)
                    out.write(frame)
                    if Camera.stopVideoRequested == True:
                        logger.debug(
                            "Thread %s: Camera._videoThreadUsb - stop video requested", get_ident()
                        )
                        break
            out.release()
            Camera.stopVideoRequested = False
            Camera.videoDuration = 0
        except Exception as e:
            logger.error(
                "Thread %s: Camera._videoThreadUsb - Exception: %s", get_ident(), e
            )
            Camera.liveViewDeactivated = False
            if not sc.error:
                sc.error = "Error in video recording: " + str(e)
                sc.errorSource = "Camera._videoThreadUsb"

        Camera.videoThread = None
        logger.debug(
            "Thread %s: Camera._videoThread - _videoThreadUsb terminated", get_ident()
        )

        Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
        logger.debug(
            "Thread %s: Camera._videoThreadUsb - sc.error: %s)", get_ident(), sc.error
        )

        if sc.isPhotoSeriesRecording == False and sc.isLiveStream == False:
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)

    @staticmethod
    def _videoThread():
        logger.debug("Thread %s: Camera._videoThread", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig

        logger.debug(
            "Thread %s: Camera._videoThread - Requesting camera for videoConfig",
            get_ident(),
        )
        Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(
            Camera.cam, Camera.camNum, cfg.videoConfig
        )
        logger.debug(
            "Thread %s: Camera._videoThread - Got camera for videoConfig exclusive: %s",
            get_ident(),
            exclusive,
        )

        Camera.applyControls(Camera.ctrl.configuration)
        logger.debug("Thread %s: Camera._videoThread - controls applied", get_ident())

        sc.checkMicrophone()

        encoder = H264Encoder()
        prgLogger.debug("encoder = H264Encoder()")
        output = Camera.videoOutput
        prgLogger.debug('output="%s"', Camera.prgVideoOutput)
        if output.lower().endswith(".mp4"):
            if sc.recordAudio == False:
                encoder.output = FfmpegOutput(output, audio=False)
                prgLogger.debug("encoder.output = FfmpegOutput(output, audio=False)")
            else:
                encoder.output = FfmpegOutput(
                    output, audio=True, audio_sync=sc.audioSync
                )
                prgLogger.debug(
                    "encoder.output = FfmpegOutput(output, audio=True, audio_sync=%s)",
                    sc.audioSync,
                )
            logger.debug(
                "Thread %s: Camera._videoThread - mp4 Video output to %s",
                get_ident(),
                output,
            )
        else:
            encoder.output = FileOutput(output)
            prgLogger.debug("encoder.output = FileOutput(output)")
            logger.debug(
                "Thread %s: Camera._videoThread - h264 Video output to %s",
                get_ident(),
                output,
            )
        try:
            videoStart = time.time()
            duration = float(Camera.videoDuration)
            logger.debug(
                "Thread %s: Camera._videoThread - video started at %s, duration is %s",
                get_ident(),
                videoStart,
                duration,
            )
            Camera.cam.start_encoder(encoder, name=cfg.videoConfig.stream)
            prgLogger.debug(
                'picam2.start_encoder(encoder, name="%s")', cfg.videoConfig.stream
            )
            prgLogger.debug("time.sleep(videoDuration)")
            Camera.ctrl.registerEncoder(Camera.ENCODER_VIDEO, encoder)
            logger.debug(
                "Thread %s: Camera._videoThread - Encoder started", get_ident()
            )
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
            logger.debug(
                "Thread %s: Camera._videoThread - stop video requested", get_ident()
            )
            Camera.ctrl.stopEncoder(Camera.cam, Camera.ENCODER_VIDEO)
            logger.debug(
                "Thread %s: Camera._videoThread - encoder stopped", get_ident()
            )
            Camera.stopVideoRequested = False
            Camera.videoDuration = 0
        except ProcessLookupError as e:
            logger.error("Thread %s: Camera._videoThread - Error: %s", get_ident(), e)
            Camera.liveViewDeactivated = False
            if not sc.error:
                sc.error = "Error in encoder: " + str(e)
                sc.error2 = "Probably, the requested resolution is too high."
                sc.errorSource = "Camera._videoThread"
        except RuntimeError as e:
            logger.error("Thread %s: Camera._videoThread - Error: %s)", get_ident(), e)
            Camera.liveViewDeactivated = False
            if not sc.error:
                sc.error = "Error in encoder: " + str(e)
                sc.error2 = "Probably, there is not sufficient memory for the requested resolution."
                sc.errorSource = "Camera._videoThread"
            logger.debug(
                "Thread %s: Camera._videoThread - sc.error: %s)", get_ident(), sc.error
            )
        except Exception as e:
            logger.error(
                "Thread %s: Camera._videoThread - Exception: %s", get_ident(), e
            )
            Camera.liveViewDeactivated = False
            if not sc.error:
                sc.error = "Error in video recording: " + str(e)
                sc.errorSource = "Camera._videoThread"

        Camera.videoThread = None
        logger.debug(
            "Thread %s: Camera._videoThread - videoThread terminated", get_ident()
        )

        Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
        logger.debug(
            "Thread %s: Camera._videoThread - sc.error: %s)", get_ident(), sc.error
        )

        if sc.isPhotoSeriesRecording == False and sc.isLiveStream == False:
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)

    @staticmethod
    def _videoThread2Usb():
        logger.debug("Thread %s: Camera._videoThread2Usb", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig

        logger.debug(
            "Thread %s: Camera._videoThread2Usb - Requesting camera for videoConfig",
            get_ident(),
        )
        videoConfig = cfg.streamingCfg[str(Camera.camNum2)]["videoconfig"]
        Camera.cam2, exclusive = Camera.ctrl2.requestCameraForConfig(
            Camera.cam2, Camera.camNum2, videoConfig, forActiveCamera=False, forceExclusive=True
        )
        logger.debug(
            "Thread %s: Camera._videoThread2Usb - Got camera for videoConfig exclusive: %s",
            get_ident(),
            exclusive,
        )

        Camera.applyControls(Camera.ctrl2.configuration, toCam2=True)
        logger.debug(
            "Thread %s: Camera._videoThread2Usb - controls applied", get_ident()
        )

        # frameRate = Camera.cam.get(cv2.CAP_PROP_FPS)
        frameRate = 14.5
        Camera.cam2.set(cv2.CAP_PROP_FPS, frameRate)
        logger.debug("Thread %s: Camera._videoThread2Usb - frameRate is %s", get_ident(), frameRate)

        # Codec for MP4 (most compatible)
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        width = int(Camera.cam2.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(Camera.cam2.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.debug("Thread %s: Camera._videoThread2Usb - width:%s, height:%s", get_ident(), width, height)
        logger.debug("Thread %s: Camera._videoThread2Usb - videoOutput2:%s", get_ident(), Camera.videoOutput2)

        out = cv2.VideoWriter(Camera.videoOutput2, fourcc, frameRate, (width, height))
        logger.debug(
            "Thread %s: Camera._videoThread2Usb - VideoWriter created", get_ident()
        )

        try:
            videoStart = time.time()
            duration = float(Camera.videoDuration2)
            logger.debug(
                "Thread %s: Camera._videoThread2Usb - video started at %s, duration is %s",
                get_ident(),
                videoStart,
                duration,
            )

            if duration > 0.0:
                elapsed = time.time() - videoStart
                while elapsed <= duration:
                    ret, frame = Camera.cam2.read()
                    if not ret:
                        break
                    conf = Camera.ctrl2.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, toCam2=True)
                    out.write(frame)
                    if Camera.stopVideoRequested2 == True:
                        logger.debug(
                            "Thread %s: Camera._videoThread2Usb - stop video requested",
                            get_ident(),
                        )
                        break
                    elapsed = time.time() - videoStart
                sc.isVideoRecording2 = False
                sc.isAudioRecording = False
            else:
                while Camera.stopVideoRequested2 == False:
                    ret, frame = Camera.cam2.read()
                    if not ret:
                        break
                    conf = Camera.ctrl2.configuration
                    hflip = conf.transform.hflip
                    vflip = conf.transform.vflip
                    if hflip == True:
                        frame = cv2.flip(frame, 1)
                    if vflip == True:
                        frame = cv2.flip(frame, 0)
                    # Apply controls
                    frame = Camera.usbFrameApplyControls(frame, toCam2=True)
                    out.write(frame)
                    if Camera.stopVideoRequested2 == True:
                        logger.debug(
                            "Thread %s: Camera._videoThread2Usb - stop video requested",
                            get_ident(),
                        )
                        break
            out.release()
            Camera.stopVideoRequested2 = False
            Camera.videoDuration2 = 0
        except Exception as e:
            logger.error(
                "Thread %s: Camera._videoThread2Usb - Exception: %s", get_ident(), e
            )
            Camera.liveView2Deactivated = False
            if not sc.errorc2:
                sc.errorc2 = "Error in video recording: " + str(e)
                sc.errorc2Source = "Camera._videoThread2Usb"

        Camera.videoThread2 = None
        logger.debug(
            "Thread %s: Camera._videoThread2Usb - _videoThread2Usb terminated",
            get_ident(),
        )

        Camera.cam2 = Camera.ctrl2.restoreLivestream2(Camera.cam2, exclusive)
        logger.debug(
            "Thread %s: Camera._videoThread2Usb - sc.errorc2: %s)", get_ident(), sc.errorc2
        )

        if sc.isLiveStream2 == False:
            Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)

    @staticmethod
    def _videoThread2():
        logger.debug("Thread %s: Camera._videoThread2", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig

        logger.debug(
            "Thread %s: Camera._videoThread2 - Requesting camera for videoConfig",
            get_ident(),
        )
        videoConfig = cfg.streamingCfg[str(Camera.camNum2)]["videoconfig"]
        Camera.cam2, exclusive = Camera.ctrl2.requestCameraForConfig(
            Camera.cam2, Camera.camNum2, videoConfig
        )
        logger.debug(
            "Thread %s: Camera._videoThread2 - Got camera for videoConfig exclusive: %s",
            get_ident(),
            exclusive,
        )

        Camera.applyControls(Camera.ctrl2.configuration, toCam2=True)
        logger.debug("Thread %s: Camera._videoThread2 - controls applied", get_ident())
        time.sleep(0.5)

        encoder = H264Encoder()
        prgLogger.debug("encoder = H264Encoder()")
        output = Camera.videoOutput2
        prgLogger.debug('output="%s"', Camera.prgVideoOutput)
        if output.lower().endswith(".mp4"):
            encoder.output = FfmpegOutput(output, audio=False)
            prgLogger.debug("encoder.output = FfmpegOutput(output, audio=False)")
            logger.debug(
                "Thread %s: Camera._videoThread2 - mp4 Video output to %s",
                get_ident(),
                output,
            )
        else:
            encoder.output = FileOutput(output)
            prgLogger.debug("encoder.output = FileOutput(output)")
            logger.debug(
                "Thread %s: Camera._videoThread2 - h264 Video output to %s",
                get_ident(),
                output,
            )
        try:
            videoStart = time.time()
            duration = float(Camera.videoDuration2)
            logger.debug(
                "Thread %s: Camera._videoThread2 - video started at %s, duration is %s",
                get_ident(),
                videoStart,
                duration,
            )
            Camera.cam2.start_encoder(encoder, name=videoConfig.stream)
            prgLogger.debug(
                'picam2.start_encoder(encoder, name="%s")', videoConfig.stream
            )
            prgLogger.debug("time.sleep(videoDuration)")
            Camera.ctrl2.registerEncoder(Camera.ENCODER_VIDEO, encoder)
            logger.debug(
                "Thread %s: Camera._videoThread2 - Encoder started", get_ident()
            )
            if duration > 0.0:
                elapsed = time.time() - videoStart
                while elapsed <= duration:
                    if Camera.stopVideoRequested2 == True:
                        break
                    time.sleep(0.1)
                    elapsed = time.time() - videoStart
                sc.isVideoRecording2 = False
            else:
                while Camera.stopVideoRequested2 == False:
                    time.sleep(0.1)
            logger.debug(
                "Thread %s: Camera._videoThread2 - stop video requested", get_ident()
            )
            Camera.ctrl2.stopEncoder(Camera.cam2, Camera.ENCODER_VIDEO)
            logger.debug(
                "Thread %s: Camera._videoThread2 - encoder stopped", get_ident()
            )
            Camera.stopVideoRequested2 = False
            Camera.videoDuration2 = 0
        except ProcessLookupError as e:
            logger.error("Thread %s: Camera._videoThread2 - Error: %s", get_ident(), e)
            Camera.liveView2Deactivated = False
            if not sc.errorc2:
                sc.errorc2 = "Error in encoder: " + str(e)
                sc.errorc22 = "Probably, the requested resolution is too high."
                sc.errorc2Source = "Camera._videoThread2"
        except RuntimeError as e:
            logger.error("Thread %s: Camera._videoThread2 - Error: %s)", get_ident(), e)
            Camera.liveView2Deactivated = False
            if not sc.errorc2:
                sc.errorc2 = "Error in encoder: " + str(e)
                sc.errorc22 = "Probably, there is not sufficient memory for the requested resolution."
                sc.errorc2Source = "Camera._videoThread2"
            logger.debug(
                "Thread %s: Camera._videoThread2 - sc.errorc2: %s)",
                get_ident(),
                sc.errorc2,
            )
        except Exception as e:
            logger.error(
                "Thread %s: Camera._videoThread2 - Exception: %s", get_ident(), e
            )
            Camera.liveView2Deactivated = False
            if not sc.errorc2:
                sc.errorc2 = "Error in video recording: " + str(e)
                sc.errorc2Source = "Camera._videoThread2"

        Camera.videoThread2 = None
        logger.debug(
            "Thread %s: Camera._videoThread2 - videoThread2 terminated", get_ident()
        )

        Camera.cam2 = Camera.ctrl2.restoreLivestream2(Camera.cam2, exclusive)
        logger.debug(
            "Thread %s: Camera._videoThread2 - sc.errorc2: %s)", get_ident(), sc.errorc2
        )

        if sc.isLiveStream2 == False:
            Camera.cam2, done = Camera.ctrl2.requestStop(Camera.cam2, close=True)

    @staticmethod
    def recordVideo(
        filenameVid: str,
        filename: str,
        duration: int = 0,
        noEvents: bool = False,
        alternatePath: str = "",
    ):
        """Start recrding video in an own thread

        Args:
            filenameVid (str): File name for video
            filename (str): filename for placeholder image
                            If empty, no placeholder image is created
            duration (int, optional): Video duration. Defaults to 0.
            noEvents (bool, optional): Dont fire events. Defaults to False.
            alternatePath (str, optional): Alternate path.
                        If set, display buffer will not be upfated
                        Defaults to "".
        """
        logger.debug(
            "Thread %s: Camera.recordVideo. filename=%s, duration=%s",
            get_ident(),
            filename,
            duration,
        )
        cfg = CameraCfg()
        sc = cfg.serverConfig
        # First take a normal photo as placeholder
        if filename != "":
            Camera.takeImage(
                filename, keepExclusive=True, noEvents=True, alternatePath=alternatePath
            )
            if alternatePath == "":
                sc.displayFile = filenameVid

        # Configure output for video file
        path = sc.photoRoot + "/" + sc.cameraPhotoSubPath
        if alternatePath != "":
            path = alternatePath
        output = path + "/" + filenameVid
        prgoutput = sc.prgOutputPath + "/" + filenameVid

        if Camera.videoThread is None:
            Camera.videoOutput = output
            Camera.prgVideoOutput = prgoutput
            Camera.videoDuration = duration
            logger.debug(
                "Thread %s: Camera.recordVideo - Starting new videoThread", get_ident()
            )
            if Camera.camIsUsb == False:
                Camera.videoThread = threading.Thread(
                    target=Camera._videoThread, daemon=True
                )
            else:
                Camera.videoThread = threading.Thread(
                    target=Camera._videoThreadUsb, daemon=True
                )
            Camera.videoThread.start()
            logger.debug(
                "Thread %s: Camera.recordVideo - videoThread started", get_ident()
            )

            if noEvents == False:
                if Camera().when_recording_starts:
                    Camera().when_recording_starts()
        return output

    @staticmethod
    def recordVideo2(
        filenameVid: str,
        filename: str,
        duration: int = 0,
        noEvents: bool = False,
        alternatePath: str = "",
    ):
        """Start recording video with second camera in an own thread

        Args:
            filenameVid (str): File name for video
            filename (str): filename for placeholder image
                            If empty, no placeholder image is created
            duration (int, optional): Video duration. Defaults to 0.
            noEvents (bool, optional): Dont fire events. Defaults to False.
            alternatePath (str, optional): Alternate path.
                        If set, display buffer will not be upfated
                        Defaults to "".
        """
        logger.debug(
            "Thread %s: Camera.recordVideo2. filename=%s, duration=%s",
            get_ident(),
            filename,
            duration,
        )
        cfg = CameraCfg()
        sc = cfg.serverConfig
        # First take a normal photo as placeholder
        if filename != "":
            Camera.takeImage2(
                filename, keepExclusive=True, noEvents=True, alternatePath=alternatePath
            )

        # Configure output for video file
        cameraPhotoSubPath = "photos/" + "camera_" + str(Camera.camNum2)
        path = sc.photoRoot + "/" + cameraPhotoSubPath
        if alternatePath != "":
            path = alternatePath
        output = path + "/" + filenameVid
        prgoutput = sc.prgOutputPath + "/" + filenameVid

        if Camera.videoThread2 is None:
            Camera.videoOutput2 = output
            Camera.prgVideoOutput2 = prgoutput
            Camera.videoDuration2 = duration
            logger.debug(
                "Thread %s: Camera.recordVideo2 - Starting new videoThread with output=%s",
                get_ident(),
                Camera.prgVideoOutput2,
            )
            if Camera.cam2IsUsb == False:
                Camera.videoThread2 = threading.Thread(
                    target=Camera._videoThread2, daemon=True
                )
            else:
                Camera.videoThread2 = threading.Thread(
                    target=Camera._videoThread2Usb, daemon=True
                )
            Camera.videoThread2.start()
            logger.debug(
                "Thread %s: Camera.recordVideo2 - videoThread2 started", get_ident()
            )

            if noEvents == False:
                if Camera().when_recording_2_starts:
                    Camera().when_recording_2_starts()
        return output

    @staticmethod
    def stopVideoRecording(noEvents: bool = False):
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
        logger.debug(
            "Thread %s: Camera.stopVideoRecording: Thread has stopped", get_ident()
        )

        if noEvents == False:
            if Camera().when_recording_stops:
                Camera().when_recording_stops()
        Camera.liveViewDeactivated = False
        time.sleep(0.1)
        Camera.startLiveStream()

    @staticmethod
    def stopVideoRecording2(noEvents: bool = False):
        """stops the video recording for second camera"""
        logger.debug("Thread %s: Camera.stopVideoRecording2", get_ident())
        Camera.stopVideoRequested2 = True
        Camera.videoDurations = 0
        cnt = 0
        while Camera.videoThread2:
            time.sleep(0.01)
            cnt += 1
            if cnt > 500:
                raise TimeoutError("Video thread 2 did not stop within 5 sec")
        logger.debug(
            "Thread %s: Camera.stopVideoRecording2: Thread has stopped", get_ident()
        )

        if noEvents == False:
            if Camera().when_recording_2_stops:
                Camera().when_recording_2_stops()
        Camera.liveView2Deactivated = False

    @staticmethod
    def isVideoRecording() -> bool:
        return Camera.videoThread is not None

    @staticmethod
    def isVideoRecording2() -> bool:
        return Camera.videoThread2 is not None

    @staticmethod
    def getLensPosition() -> float:
        metadata = Camera.cam.capture_metadata()
        if "LensPosition" in metadata:
            return metadata["LensPosition"]
        else:
            return 0.0

    @staticmethod
    def getMetaData() -> dict:
        logger.debug("Thread %s: Camera.getMetaData", get_ident())
        if Camera.camIsUsb == False:
            return Camera.cam.capture_metadata()
        else:
            return Camera.getUsbCamMetadata(Camera.cam)

    @staticmethod
    def _photoSeriesThread():
        logger.debug("Thread %s: Camera._photoSeriesThread", get_ident())
        ser = Camera.photoSeries
        cfg = CameraCfg()
        sc = cfg.serverConfig

        logger.debug(
            "Thread %s: Camera._photoSeriesThread Requesting camera for photo series of type %s",
            get_ident(),
            ser.type,
        )
        exclusive = False
        try:
            if Camera.camIsUsb == False:
                forceExclusive = False
            else:
                forceExclusive = True
            if ser.type == "jpg":
                Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(
                    Camera.cam, Camera.camNum, cfg.photoConfig, forceExclusive=forceExclusive
                )
            else:
                Camera.cam, exclusive = Camera.ctrl.requestCameraForConfig(
                    Camera.cam, Camera.camNum, cfg.rawConfig, cfg.photoConfig, forceExclusive=forceExclusive
                )
            logger.debug(
                "Thread %s: Camera._photoSeriesThread Got camera for photo series exclusive: %s",
                get_ident(),
                exclusive,
            )
        except Exception as e:
            logger.error(
                "Thread %s: Camera._photoSeriesThread error: %s", get_ident(), e
            )
            if not sc.error:
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
                        logger.debug(
                            "Thread %s: Camera._photoSeriesThread - Exposure Series for %s: Restart after %s shots",
                            get_ident(),
                            exceptCtrl,
                            ser.curShots,
                        )
                logger.debug(
                    "Thread %s: Camera._photoSeriesThread - Exposure Series for %s: %s Factor: %s",
                    get_ident(),
                    exceptCtrl,
                    exceptValue,
                    expFact,
                )

            # Special handling for focus series
            if ser.isFocusStackingSeries:
                exceptCtrl = "LensPosition"
                exceptValueRaw = ser.focalDistStart
                exceptValue = 1.0 / exceptValueRaw
                if ser.curShots:
                    if ser.curShots > 1:
                        exceptValueRaw = (
                            ser.focalDistStart + (ser.curShots - 1) * ser.focalDistStep
                        )
                        exceptValue = 1.0 / exceptValueRaw
                        logger.debug(
                            "Thread %s: Camera._photoSeriesThread - Focus Series: Restart after %s shots",
                            get_ident(),
                            ser.curShots,
                        )
                logger.debug(
                    "Thread %s: Camera._photoSeriesThread - Focus Series for %s: %s (focal dist: %s, interval: %s)",
                    get_ident(),
                    exceptCtrl,
                    exceptValue,
                    exceptValueRaw,
                    ser.focalDistStep,
                )

            photoseriesCtrls = Camera.applyControls(
                Camera.ctrl.configuration, exceptCtrl, exceptValue
            )
            logger.debug(
                "Thread %s: Camera._photoSeriesThread - selected controls applied",
                get_ident(),
            )

            lastTime = None
            stop = False
            while not stop:
                nextTime = ser.nextTime(lastTime)
                curShots, nextPhoto = ser.nextPhoto()
                logger.debug(
                    "Thread %s: Camera._photoSeriesThread - nextPhoto: %s nextTime %s",
                    get_ident(),
                    nextPhoto,
                    str(nextTime),
                )
                if nextPhoto == "" or nextTime is None or ser.status == "FINISHED":
                    logger.debug(
                        "Thread %s: Camera._photoSeriesThread - Series done: nextPhoto=%s, nextTime=%s, status=%s",
                        get_ident(),
                        nextPhoto,
                        str(nextTime),
                        ser.status,
                    )
                    stop = True
                else:
                    curTime = datetime.datetime.now()
                    timedif = nextTime - curTime
                    timedifSec = timedif.total_seconds()
                    logger.debug(
                        "Thread %s: Camera._photoSeriesThread - Seconds to wait: %s",
                        get_ident(),
                        timedifSec,
                    )

                    camClosed = False
                    if (
                        ser.isFocusStackingSeries == False
                        and ser.isExposureSeries == False
                    ):
                        if sc.isVideoRecording == False and sc.isLiveStream == False:
                            if timedifSec > 60:
                                Camera.cam, camClosed = Camera.ctrl.requestStop(
                                    Camera.cam, close=True
                                )

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
                    logger.debug(
                        "Thread %s: Camera._photoSeriesThread - Stop requested",
                        get_ident(),
                    )
                    stop = True
                if not stop:
                    try:
                        logger.debug(
                            "Thread %s: Camera._photoSeriesThread - Starting next shot",
                            get_ident(),
                        )
                        if Camera.cam is None:
                            camClosed = True
                        else:
                            if Camera.camIsUsb == False:
                                if Camera.cam.started == False:
                                    camClosed = True
                            else:
                                camClosed = Camera.cam.isOpened() == False
                        if camClosed:
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - Preparing closed camera",
                                get_ident(),
                            )
                            if ser.type == "jpg":
                                Camera.cam, exclusive = (
                                    Camera.ctrl.requestCameraForConfig(
                                        Camera.cam, Camera.camNum, cfg.photoConfig, forceExclusive=forceExclusive
                                    )
                                )
                            else:
                                Camera.cam, exclusive = (
                                    Camera.ctrl.requestCameraForConfig(
                                        Camera.cam,
                                        Camera.camNum,
                                        cfg.rawConfig,
                                        cfg.photoConfig,
                                        forceExclusive=forceExclusive
                                    )
                                )
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread Got camera for photo series exclusive: %s",
                                get_ident(),
                                exclusive,
                            )
                            photoseriesCtrls = Camera.applyControls(
                                Camera.ctrl.configuration, exceptCtrl, exceptValue
                            )
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - selected controls applied",
                                get_ident(),
                            )
                            time.sleep(1.5)
                            curTime = datetime.datetime.now()
                            timedif = nextTime - curTime
                            timedifSec = timedif.total_seconds()
                            if timedifSec > 0:
                                time.sleep(timedifSec)

                        lastTime = datetime.datetime.now()
                        if Camera.camIsUsb == False:
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - Preparing request",
                                get_ident(),
                            )
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - id(Camera)=%s id(Camera.cam)=%s id(Camera.cam.controls)=%s",
                                get_ident(),
                                id(Camera),
                                id(Camera.cam),
                                id(Camera.cam.controls),
                            )
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - Camera.cam.controls=%s",
                                get_ident(),
                                Camera.cam.controls,
                            )
                            request = Camera.cam.capture_request()
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - capture_request completed",
                                get_ident(),
                            )
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - id(Camera)=%s id(Camera.cam)=%s id(Camera.cam.controls)=%s",
                                get_ident(),
                                id(Camera),
                                id(Camera.cam),
                                id(Camera.cam.controls),
                            )
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - Camera.cam.controls=%s",
                                get_ident(),
                                Camera.cam.controls,
                            )
                            prgLogger.debug("request = picam2.capture_request()")
                            fpjpg = ser.path + "/" + nextPhoto + ".jpg"
                            fpraw = ser.path + "/" + nextPhoto + ".dng"
                            request.save("main", fpjpg)
                            prgLogger.debug(
                                'request.save("main", "%s")',
                                sc.prgOutputPath + "/" + nextPhoto + ".jpg",
                            )
                            if ser.type == "raw+jpg":
                                request.save_dng(fpraw)
                                prgLogger.debug(
                                    'request.save_dng("%s")',
                                    sc.prgOutputPath + "/" + nextPhoto + ".dng",
                                )
                            metadata = request.get_metadata()
                            prgLogger.debug("metadata = request.get_metadata()")
                            request.release()
                            prgLogger.debug("request.release()")
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - Request released",
                                get_ident(),
                            )
                        else:
                            # For USB cameras, save the image using OpenCV
                            fpjpg = ser.path + "/" + nextPhoto + ".jpg"
                            fpraw = ser.path + "/" + nextPhoto + ".tiff"
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - USB camera capture image %s",
                                get_ident(),
                                fpjpg,
                            )
                            if Camera.cam.isOpened() == False:
                                raise RuntimeError("USB camera is not opened")
                            success, frame = Camera.cam.read()
                            if success:
                                metadata = Camera.getUsbCamMetadata(Camera.cam)
                                conf = Camera.ctrl.configuration
                                hflip = conf.transform.hflip
                                vflip = conf.transform.vflip
                                if hflip == True:
                                    frame = cv2.flip(frame, 1)
                                if vflip == True:
                                    frame = cv2.flip(frame, 0)
                                # Apply controls
                                frame = Camera.usbFrameApplyControls(frame)
                                cv2.imwrite(fpjpg, frame)
                                if ser.type == "raw+jpg":
                                    cv2.imwrite(fpraw, frame, [cv2.IMWRITE_TIFF_COMPRESSION, 1])
                                logger.debug(
                                    "Thread %s: Camera._photoSeriesThread - USB camera capture done",
                                    get_ident()
                                )
                            else:
                                raise RuntimeError("Failed to capture image from USB camera")
                        ser.curShots = curShots
                        ser.logPhoto(nextPhoto, lastTime, metadata)
                        if (
                            ser.isFocusStackingSeries == False
                            and ser.isExposureSeries == False
                        ):
                            if Camera().when_series_photo_taken:
                                Camera().when_series_photo_taken()
                    except Exception as e:
                        ser.nextStatus("pause")
                        stop = True
                        logger.error(
                            "Thread %s: Camera._photoSeriesThread - Error: %s",
                            get_ident(),
                            e,
                        )
                        ser.error = "Error in photoseries: " + str(e)
                        ser.errorSource = "Camera._photoSeriesThread"

                    if not sc.error and not ser.error:
                        # Draw histogram
                        if ser.isExposureSeries and sc.useHistograms:
                            dest = ser.histogramPath + "/" + nextPhoto + ".jpg"
                            plt.figure()
                            img = cv2.imread(fpjpg)
                            color = ("b", "g", "r")
                            for i, col in enumerate(color):
                                histr = cv2.calcHist([img], [i], None, [256], [0, 256])
                                plt.plot(histr, color=col)
                                plt.xlim([0, 256])
                            plt.savefig(dest)
                            logger.debug(
                                "Thread %s: Camera._photoSeriesThread - histogram created: %s",
                                get_ident(),
                                dest,
                            )

                        # For exposure series apply controls
                        if ser.isExposureSeries:
                            ser.logCamCfgCtrl(
                                nextPhoto,
                                Camera.ctrl.configuration.make_dict(),
                                photoseriesCtrls.make_dict(),
                            )
                            if not stop:
                                exceptValue = expFact * exceptValue
                                logger.debug(
                                    "Thread %s: Camera._photoSeriesThread - Exposure Series for %s: %s",
                                    get_ident(),
                                    exceptCtrl,
                                    exceptValue,
                                )
                                photoseriesCtrls = Camera.applyControls(
                                    Camera.ctrl.configuration, exceptCtrl, exceptValue
                                )
                                logger.debug(
                                    "Thread %s: Camera._photoSeriesThread - selected controls applied",
                                    get_ident(),
                                )

                        # For focus series apply controls
                        if ser.isFocusStackingSeries:
                            ser.logCamCfgCtrl(
                                nextPhoto,
                                Camera.ctrl.configuration.make_dict(),
                                photoseriesCtrls.make_dict(),
                            )
                            if not stop:
                                exceptValueRaw = exceptValueRaw + ser.focalDistStep
                                exceptValue = 1.0 / exceptValueRaw
                                logger.debug(
                                    "Thread %s: Camera._photoSeriesThread - Focus Series for %s: %s (focal dist: %s)",
                                    get_ident(),
                                    exceptCtrl,
                                    exceptValue,
                                    exceptValueRaw,
                                )
                                photoseriesCtrls = Camera.applyControls(
                                    Camera.ctrl.configuration, exceptCtrl, exceptValue
                                )
                                logger.debug(
                                    "Thread %s: Camera._photoSeriesThread - selected controls applied",
                                    get_ident(),
                                )

        Camera.photoSeriesThread = None
        Camera.stopPhotoSeriesRequested = False
        sc.isPhotoSeriesRecording = False
        Camera.cam = Camera.ctrl.restoreLivestream(Camera.cam, exclusive)
        if sc.isVideoRecording == False and sc.isLiveStream == False:
            Camera.cam, done = Camera.ctrl.requestStop(Camera.cam, close=True)
        logger.debug(
            "Thread %s: Camera._photoSeriesThread - photoSeriesThread terminated",
            get_ident(),
        )

    @staticmethod
    def startPhotoSeries(ser: Series):
        """Run photoseries in an own thread"""
        logger.debug("Thread %s: startPhotoSeries - series=%s", get_ident(), ser.name)

        if Camera.photoSeriesThread is None:
            logger.debug(
                "Thread %s: startPhotoSeries - Starting new photoSeriesThread",
                get_ident(),
            )
            Camera.photoSeries = ser
            Camera.photoSeriesThread = threading.Thread(
                target=Camera._photoSeriesThread, daemon=True
            )
            Camera.photoSeriesThread.start()
            logger.debug(
                "Thread %s: startPhotoSeries - photoSeriesThread started", get_ident()
            )

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
                # raise TimeoutError("Photoseries thread did not stop within 5 sec")
                logger.debug(
                    "Thread %s: stopPhotoSeries: Thread seams to be dead", get_ident()
                )
                break
        logger.debug("Thread %s: stopPhotoSeries: Thread has stopped", get_ident())
        Camera.stopPhotoSeriesRequested = False

    @classmethod
    def cameraStatus(cls, camNum) -> str:
        status = ""
        sc = CameraCfg().serverConfig
        if camNum == cls.camNum:
            if cls.camIsUsb == False:
                if cls.cam.is_open == True:
                    status = "open"
                    if cls.cam.started == True:
                        status = status + " - started"
                        mode = "unknown"
                        if useSensorConfiguration:
                            sc = cls.cam.camera_config["sensor"]
                            for sm in CameraCfg().sensorModes:
                                if (
                                    sc["output_size"] == sm.size
                                    and sc["bit_depth"] == sm.bit_depth
                                ):
                                    mode = str(sm.id)
                        status = status + " - current Sensor Mode: " + mode
                    else:
                        status = status + " - stopped"
                else:
                    status = "closed"
            else:
                if cls.cam.isOpened() == True:
                    status = "open"
                else:
                    status = "closed"
        elif camNum == cls.camNum2:
            if cls.cam2IsUsb == False:
                if cls.cam2.is_open == True:
                    status = "open"
                    if cls.cam2.started == True:
                        status = status + " - started"
                    else:
                        status = status + " - stopped"
                else:
                    status = "closed"
            else:
                if cls.cam2.isOpened() == True:
                    status = "open"
                else:
                    status = "closed"
        else:
            if sc.supportsUsbCamera == True:
                if sc.useUsbCameras == True:
                    status = "inactive"
                else:
                    status = "excluded"
            else:
                status = "not supported (OpenCV missing)"
        return status

    @classmethod
    def resetScalerCrop(cls):
        logger.debug("Thread %s: Camera.resetScalerCrop", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        cc = cfg.controls
        cp = cfg.cameraProperties
        scInf = cls.cam.camera_controls["ScalerCrop"]
        sc.scalerCropMin = scInf[0]
        sc.scalerCropMax = scInf[1]
        sc.scalerCropDef = scInf[2]
        sc.zoomFactor = 100
        sc.scalerCropLiveView = sc.scalerCropDef
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
            sc.zoomFactor = sc.zoomFactorStep * math.floor(
                (100 * cc.scalerCrop[2] / cp.pixelArraySize[0]) / sc.zoomFactorStep)
        else:
            cc.include_scalerCrop = False
        cls.resetScalerCropRequested = False

    @classmethod
    def resetScalerCropUsb(cls):
        logger.debug("Thread %s: Camera.resetScalerCropUsb", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        cc = cfg.controls
        cp = cfg.cameraProperties
        ref = cfg.liveViewConfig.stream_size
        sc.scalerCropMax = Camera.getUsbScalerCrop(ref[0], ref[1])
        sc.scalerCropMin = (0, 0, sc.scalerCropMax[2] / 100, sc.scalerCropMax[3] / 100)
        sc.scalerCropDef = sc.scalerCropMax
        sc.zoomFactor = 100
        sc.scalerCropLiveView = sc.scalerCropDef
        if cc.scalerCrop == cfg.cameraProperties.scalerCropMaximum:
            cc.scalerCrop = sc.scalerCropDef
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
            sc.zoomFactor = sc.zoomFactorStep * math.floor(
                (100 * cc.scalerCrop[2] / cp.pixelArraySize[0]) / sc.zoomFactorStep)
        else:
            cc.include_scalerCrop = False
        cls.resetScalerCropRequested = False
