import io
import time
from raspiCamSrv.camera_base import BaseCamera, CameraEvent
from raspiCamSrv.camCfg import CameraCfg, SensorMode
from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls
from libcamera import Transform, Size, ColorSpace
from picamera2.encoders import JpegEncoder, MJPEGEncoder
from picamera2.outputs import FileOutput
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

    def __init__(self):
        logger.info("Camera.__init__")
        if Camera.cam is None:
            logger.debug("Camera.__init__: Camera instantiated")
            Camera.cam = Picamera2()
        else:
            logger.debug("Camera.__init__: Camera was already instantiated")
            if not Camera.cam.is_open:
                logger.debug("Camera.__init__: Camera was not open")
                Camera.cam = None
                logger.debug("Camera.__init__: Camera destroyed")
                Camera.cam = Picamera2()
                logger.debug("Camera.__init__: Camera instantiated")
        self.loadCameraSpecifics()
        super().__init__()
        
    @staticmethod
    def loadCameraSpecifics():
        """ Load camera specific parameters into configuration, if not already done
        """
        logger.info("Camera.loadCameraSpecifics")
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
            logger.info("Camera.loadCameraSpecifics loaded to config")

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
            logger.info("%s sensor modes found", len(cfg.sensorModes))
            logger.info("%s raw formats found", len(cfg.rawFormats))
            
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
            cfg.videoConfig.sensor_mode = maxMode
            cfg.videoConfig.stream_size = cfgSensorModes[maxModei].size
            logger.info("Photo and video sensor modes set to %s", maxMode)
    
    @staticmethod
    def configure(cfg, cfgPhoto):
        """ The function creates and configures a CameraConfiguration
            based on given configuration settings cfg.
            
            The fully configured configuration is returned
        """
        logger.info("Camera.configure")
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
        logger.info("Camera.configure: configuration completed")
        
        #Automatically align the stream size, if selected
        if cfg.stream_size_align and cfg.sensor_mode == "custom" :
            logger.info("Camera.configure: Aligning camera configuration. Old size: %s", cfg.stream_size)
            camCfg.align()
            logger.info("Camera.configure: Alignment successful. Adjusting stream size")
            cfg.stream_size = camCfg.size
            logger.info("Camera.configure: Stream size adjusted to %s", cfg.stream_size)

        return camCfg

    @staticmethod
    def stopCameraSystem():
        logger.info("Camera.stopCameraSystem")
        logger.info("Camera.stopCameraSystem: Stopping thread")
        BaseCamera.stopRequested = True
        cnt = 0
        while BaseCamera.thread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                break
        logger.info("Camera.stopCameraSystem: Thread has eventually stopped")
        Camera.cam.stop_recording()
        logger.info("Camera.stopCameraSystem: Recording stopped")
        Camera().cam = None
        logger.info("Camera.stopCameraSystem: Camara deinitialized")

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
            cfgSensorModes = srvCam.sensorModes
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
