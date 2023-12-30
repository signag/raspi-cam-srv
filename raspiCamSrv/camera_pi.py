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

        if len(cfgSensorModes) == 0:
            sensorModes = Camera.cam.sensor_modes
            ind = 0
            for mode in sensorModes:
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
            maxModei = len(cfg.sensorModes) - 1
            maxMode = str(maxModei)
            cfg.liveViewConfig.stream_size = cfgSensorModes[0].size
            cfg.photoConfig.sensor_mode = maxMode
            cfg.photoConfig.stream_size = cfgSensorModes[maxModei].size
            cfg.rawConfig.sensor_mode = maxMode
            cfg.rawConfig.stream_size = cfgSensorModes[maxModei].size
            cfg.videoConfig.sensor_mode = maxMode
            cfg.videoConfig.stream_size = cfgSensorModes[maxModei].size
            logger.info("Photo and video sensor modes set to %s", maxMode)
    
    @staticmethod
    def configure(cfg):
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
        stream = StreamConfiguration()
        stream.size = cfg.stream_size
        stream.format = cfg.format
        if cfg.stream == "main":
            camCfg.main = stream
            camCfg.lores = None
            camCfg.raw = None
        if cfg.stream == "lores":
            camCfg.main = None
            camCfg.lores = stream
            camCfg.raw = None
        if cfg.stream == "raw":
            camCfg.main = None
            camCfg.lores = None
            camCfg.raw = stream
        ctrls = cfg.controls
        if len(ctrls) == 0:
            raise ValueError("controls in camera configuration must not be empty")
        else:
            camCfg.controls = ctrls
        logger.info("Camera.configure: configuration completed")
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
            stillConfig = cam.create_still_configuration()
            logger.info("Camera.takeImage: Still config created: %s", stillConfig)
            srvCam = CameraCfg()
            cfgSensorModes = srvCam.sensorModes
            cfg = srvCam.photoConfig
            photoConfig = Camera.configure(cfg)
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
    def frames():
        logger.debug("Camera.frames")
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfgSensorModes = srvCam.sensorModes
            cfg = srvCam.liveViewConfig
            streamingConfig = Camera.configure(cfg)
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
