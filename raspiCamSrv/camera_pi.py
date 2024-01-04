import io
import time
import datetime
import threading
from _thread import get_ident
from raspiCamSrv.camera_base import BaseCamera, CameraEvent
from raspiCamSrv.camCfg import CameraCfg, SensorMode
from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls
from libcamera import Transform, Size, ColorSpace
from picamera2.encoders import JpegEncoder, MJPEGEncoder
from picamera2.outputs import FileOutput, FfmpegOutput
from picamera2.encoders import H264Encoder
from threading import Condition, Lock
import logging

logger = logging.getLogger(__name__)


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        logger.debug("StreamingOutput.__init__")
        self.frame = None
        self.lock = Lock()
        self.condition = Condition(self.lock)

    def write(self, buf):
        logger.debug("StreamingOutput.write")
        with self.condition:
            self.frame = buf
            logger.debug("got buffer of length %s", len(buf))
            self.condition.notify_all()
            logger.debug("notification done")
        logger.debug("write done")


class Camera(BaseCamera):
    cam = None
    videoOutput = None

    def __init__(self):
        logger.info("Thread %s: Camera.__init__", get_ident())
        if Camera.cam is None:
            logger.info("Thread %s: Camera.__init__: Camera instantiated", get_ident())
            Camera.cam = Picamera2()
        else:
            logger.info("Thread %s: Camera.__init__: Camera was already instantiated", get_ident())
            if not Camera.cam.is_open:
                logger.info("Thread %s: Camera.__init__: Camera was not open", get_ident())
                Camera.cam = None
                logger.info("Thread %s: Camera.__init__: Camera destroyed", get_ident())
                Camera.cam = Picamera2()
                logger.info("Thread %s: Camera.__init__: Camera instantiated", get_ident())
        self.loadCameraSpecifics()
        super().__init__()
        
    @staticmethod
    def loadCameraSpecifics():
        """ Load camera specific parameters into configuration, if not already done
        """
        logger.info("Thread %s: Camera.loadCameraSpecifics", get_ident())
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
            logger.info("Thread %s: Camera.loadCameraSpecifics loaded to config", get_ident())

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
            logger.info("Thread %s: %s sensor modes found", get_ident(), len(cfg.sensorModes))
            logger.info("Thread %s: %s raw formats found", get_ident(), len(cfg.rawFormats))
            
            # Set some Sensor Mode specific parameters for standard configurations
            maxModei = len(cfg.sensorModes) - 1
            maxMode = str(maxModei)
            # For Live View
            # Initially set the stream size to (640, 4800). Use Sensor Mode, if possible
            cfg.liveViewConfig.stream_size = (640, 480)
            cfg.liveViewConfig.stream_size_align = False
            if cfgSensorModes[0].size[0] == 640 \
            and cfgSensorModes[0].size[1] == 480:
                cfg.liveViewConfig.sensor_mode = "0"
            else:
                cfg.liveViewConfig.sensor_mode = "custom"
            # For photo
            cfg.photoConfig.sensor_mode = maxMode
            cfg.photoConfig.stream_size = cfgSensorModes[maxModei].size
            # For raw photo
            cfg.rawConfig.sensor_mode = maxMode
            cfg.rawConfig.stream_size = cfgSensorModes[maxModei].size
            cfg.rawConfig.format = str(cfgSensorModes[maxModei].format)
            # For Video
            cfg.videoConfig.sensor_mode = "0"
            cfg.videoConfig.stream_size = cfgSensorModes[0].size
    
    @staticmethod
    def configure(cfg, cfgPhoto):
        """ The function creates and configures a CameraConfiguration
            based on given configuration settings cfg.
            
            The fully configured configuration is returned
        """
        logger.info("Thread %s: Camera.configure", get_ident())
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
        logger.info("Thread %s: Camera.configure: configuration completed", get_ident())
        
        #Automatically align the stream size, if selected
        if cfg.stream_size_align and cfg.sensor_mode == "custom" :
            logger.info("Thread %s: Camera.configure: Aligning camera configuration. Old size: %s", get_ident(), cfg.stream_size)
            camCfg.align()
            logger.info("Thread %s: Camera.configure: Alignment successful. Adjusting stream size", get_ident())
            cfg.stream_size = camCfg.size
            logger.info("Thread %s: Camera.configure: Stream size adjusted to %s", get_ident(), cfg.stream_size)

        return camCfg

    @staticmethod
    def stopCameraSystem():
        logger.info("Thread %s: Camera.stopCameraSystem", get_ident())
        logger.info("Thread %s: Camera.stopCameraSystem: Stopping Live view thread", get_ident())
        BaseCamera.stopRequested = True
        if BaseCamera.thread:
            cnt = 0
            while BaseCamera.thread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    break
            if BaseCamera.thread:
                logger.info("Thread %s: Camera.stopCameraSystem: Live view thread did not stop within 2 sec", get_ident())
            else:
                logger.info("Thread %s: Camera.stopCameraSystem: Live view thread successfully stopped", get_ident())
        else:
            logger.info("Thread %s: Camera.stopCameraSystem: Live view thread was not active", get_ident())
        BaseCamera.stopRequested = False
        
        logger.info("Thread %s: Camera.stopCameraSystem: Stopping Video thread", get_ident())
        BaseCamera.stopVideoRequested = True        
        if BaseCamera.videoThread:
            cnt = 0
            while BaseCamera.videoThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 200:
                    break
            if BaseCamera.videoThread:
                logger.info("Thread %s: Camera.stopCameraSystem: Video thread did not stop within 2 sec", get_ident())
            else:
                logger.info("Thread %s: Camera.stopCameraSystem: Video thread successfully stopped", get_ident())
        else:
            logger.info("Thread %s: Camera.stopCameraSystem: Video thread was not active", get_ident())
        BaseCamera.stopVideoRequested = False        
            
        Camera.cam.stop_recording()
        logger.info("Thread %s: Camera.stopCameraSystem: Recording stopped", get_ident())
        Camera.cam.stop()
        logger.info("Thread %s: Camera.stopCameraSystem: Camara stopped", get_ident())
        Camera.cam.close()
        logger.info("Thread %s: Camera.stopCameraSystem: Camara closed", get_ident())
        

    @staticmethod
    def restartLiveView():
        logger.info("Camera.restartLiveView")
        logger.info("Camera.restartLiveView: Stopping thread")
        BaseCamera.stopRequested = True
        cnt = 0
        while BaseCamera.thread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Background thread did not stop within 2 sec")
        logger.info("Camera.restartLiveView: Thread has stopped")
        Camera.cam.stop_recording()
        logger.info("Camera.restartLiveView: Recording stopped")

    @staticmethod
    def takeImage(path: str, filename: str):
        logger.info("Camera.takeImage")
        cfg = CameraCfg()
        sc = cfg.serverConfig
        logger.info("Camera.takeImage: Stopping thread")
        BaseCamera.stopRequested = True
        cnt = 0
        while BaseCamera.thread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Background thread did not stop within 2 sec")
        logger.info("Camera.takeImage: Thread has stopped")
        Camera.cam.stop_recording()
        logger.info("Camera.takeImage: Recording stopped")
        Camera.cam = Picamera2()
        logger.info("Camera.takeImage: Camera reinitialized")
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfg = srvCam.photoConfig
            photoConfig = Camera.configure(cfg, srvCam.photoConfig)
            cam.configure(photoConfig)
            logger.info("Camera.takeImage: Camera configured for still")
            cam.start(show_preview=False)
            logger.info("Camera.takeImage: Camera started")
            request = cam.capture_request()
            logger.info("Camera.takeImage: Request started")
            fp = path + "/" + filename
            request.save("main", fp)
            sc.displayFile = filename
            sc.displayPhoto = "photos/" + filename
            sc.isDisplayHidden = False
            logger.info("Camera.takeImage: Image saved as %s", fp)
            metadata = request.get_metadata()
            sc.displayMeta = metadata
            sc.displayMetaFirst = 0
            if len(metadata) < 11:
                sc._displayMetaLast = 999
            else:
                sc.displayMetaLast = 10
            logger.info("Camera.takeImage: Image metedata captured")
            request.release()
            logger.info("Camera.takeImage: Request released")

    @staticmethod
    def takeRawImage(path: str, filenameRaw: str, filename: str):
        logger.info("Camera.takeRawImage")
        cfg = CameraCfg()
        sc = cfg.serverConfig
        BaseCamera.stopRequested = True
        cnt = 0
        while BaseCamera.thread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Background thread did not stop within 2 sec")
        Camera.cam.stop_recording()
        Camera.cam = Picamera2()
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfg = srvCam.rawConfig
            rawConfig = Camera.configure(cfg, srvCam.photoConfig)
            logger.info("rawConfig:%s", rawConfig)
            cam.configure(rawConfig)
            logger.info("Camera.takeImage: Camera configured for raw")
            cam.start(show_preview=False)
            logger.info("Camera.takeImage: Camera started")
            request = cam.capture_request()
            logger.info("Camera.takeImage: Request started")
            fp = path + "/" + filename
            request.save("main", fp)
            fpr = path + "/" + filenameRaw
            request.save_dng(fpr)
            sc.displayFile = filenameRaw
            sc.displayPhoto = "photos/" + filename
            sc.isDisplayHidden = False
            logger.info("Camera.takeImage: Raw Image saved as %s", fpr)
            metadata = request.get_metadata()
            sc.displayMeta = metadata
            sc.displayMetaFirst = 0
            if len(metadata) < 11:
                sc._displayMetaLast = 999
            else:
                sc.displayMetaLast = 10
            logger.info("Camera.takeRawImage: Raw Image metedata captured")
            request.release()
            logger.info("Camera.takeRawImage: Request released")
    
    @staticmethod
    def frames():
        logger.debug("Camera.frames")
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfg = srvCam.liveViewConfig
            streamingConfig = Camera.configure(cfg, srvCam.photoConfig)
            cam.configure(streamingConfig)
            logger.debug("starting recording")
            output = StreamingOutput()
            cam.start_recording(MJPEGEncoder(), FileOutput(output))
            logger.debug("recording started")
            # let camera warm up
            time.sleep(2)
            while True:
                logger.debug("Receiving camera stream")
                with output.condition:
                    logger.debug("waiting")
                    output.condition.wait()
                    logger.debug("waiting done")
                    frame = output.frame
                    l = len(frame)
                logger.debug("got frame with length %s", l)
                yield frame
    
    @staticmethod
    def _videoThread():
        logger.info("Thread %s: _videoThread", get_ident())
        # First, stop the camera system
        Camera.stopCameraSystem()
        # Deactivate Live View to avoid the Live View thread to start
        
        Camera.cam = Picamera2()
        logger.info("Thread %s: _videoThread - Camera reassigned", get_ident())
        logger.info("Thread %s: _videoThread - Camera isOpen=%s started=%s", get_ident(), Camera.cam.is_open, Camera.cam.started)
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfg = srvCam.videoConfig
            videoConfig = Camera.configure(cfg, srvCam.photoConfig)
            cam.configure(videoConfig)
            logger.info("Thread %s: _videoThread - Video configuration done", get_ident())
            encoder = H264Encoder(10000000)
            output = Camera.videoOutput
            if output.lower().endswith(".mp4"):
                encoder.output = FfmpegOutput(output, audio=False)
                logger.info("Thread %s: _videoThread - mp4 Video output to %s", get_ident(), output)
            else:
                encoder.output = FileOutput(output)
                logger.info("Thread %s: _videoThread - h264 Video output to %s", get_ident(), output)
            try:
                cam.start()
                logger.info("Thread %s: _videoThread - Camera started", get_ident())
                cam.start_encoder(encoder)
                logger.info("Thread %s: _videoThread - Encoder started", get_ident())
                while Camera.stopVideoRequested == False:
                    time.sleep(0.1)
                logger.info("Thread %s: _videoThread - stop video requested", get_ident())
                cam.stop_encoder()
                logger.info("Thread %s: _videoThread - encoder stopped", get_ident())
                cam.stop()
                logger.info("Thread %s: _videoThread - camera stopped", get_ident())
            except ProcessLookupError:
                logger.info("Thread %s: _videoThread - Encoder could not be started (requested resolution too high)", get_ident())
                BaseCamera.liveViewDeactivated = False
            except RuntimeError:
                logger.info("Thread %s: _videoThread - Encoder could not be started (not enough memory for requested resolution)", get_ident())
                BaseCamera.liveViewDeactivated = False
            
        BaseCamera.videoThread = None
        logger.info("Thread %s: _videoThread - videoThread terminated", get_ident())

    @staticmethod
    def recordVideo(output: str):
        """Record a video in an own thread"""
        logger.info("Thread %s: recordVideo. output=%s", get_ident(), output)
        BaseCamera.liveViewDeactivated = True
        logger.info("Thread %s: recordVideo - Live view deactivated", get_ident())
        
        if BaseCamera.videoThread is None:
            Camera.videoOutput = output
            logger.info("Thread %s: recordVideo - Starting new videoThread", get_ident())
            BaseCamera.videoThread = threading.Thread(target=Camera._videoThread, daemon=True)
            BaseCamera.videoThread.start()
            logger.info("Thread %s: recordVideo - videoThread started", get_ident())

    @staticmethod
    def stopVideoRecording():
        """stops the video recording"""
        logger.info("Thread %s: stopVideoRecording", get_ident())
        BaseCamera.stopVideoRequested = True
        cnt = 0
        while BaseCamera.videoThread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Video thread did not stop within 2 sec")
        logger.info("Thread %s: stopVideoRecording: Thread has stopped", get_ident())
        Camera.cam = Picamera2()
        BaseCamera.liveViewDeactivated = False
        
    @staticmethod
    def isVideoRecording() -> bool:
        return BaseCamera.videoThread is not None
        