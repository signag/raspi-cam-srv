import io
import time
import datetime
import threading
from _thread import get_ident
from raspiCamSrv.camera_base import BaseCamera, CameraEvent
from raspiCamSrv.camCfg import CameraInfo, CameraCfg, SensorMode, CameraConfig
from picamera2 import Picamera2, CameraConfiguration, StreamConfiguration, Controls
from libcamera import Transform, Size, ColorSpace, controls
from picamera2.encoders import JpegEncoder, MJPEGEncoder
from picamera2.outputs import FileOutput, FfmpegOutput
from picamera2.encoders import H264Encoder
from threading import Condition, Lock
import copy
import os
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
    camNum = -1
    videoOutput = None

    def __init__(self):
        logger.info("Thread %s: Camera.__init__", get_ident())
        # Before all, load the global camera info to get the installed cameras and the active cam
        activeCam = Camera.getActiveCamera()
        
        if Camera.cam is None:
            logger.info("Thread %s: Camera.__init__: Camera instantiated: %s", get_ident(), activeCam)
            Camera.cam = Picamera2(activeCam)
            Camera.camNum = activeCam
        else:
            if activeCam != Camera.camNum:
                logger.info("Thread %s: Camera.__init__: About to switch camera from %s to %s", get_ident(), Camera.camNum, activeCam)
                Camera.stopCameraSystem()
                Camera.cam = Picamera2(activeCam)
                Camera.camNum = activeCam
                logger.info("Thread %s: Camera.__init__: Switch camera to %s successful", get_ident(), activeCam)
                # Force refresh of camera properties
                CameraCfg().cameraProperties.model=None
                CameraCfg().sensorModes = []
                CameraCfg().rawFormats = []
                logger.info("Thread %s: Camera.__init__: Camera-specific configs were reset", get_ident())
            else:
                logger.debug("Thread %s: Camera.__init__: Camera was already instantiated", get_ident())
                if not Camera.cam.is_open:
                    logger.debug("Thread %s: Camera.__init__: Camera was not open", get_ident())
                    Camera.cam = None
                    logger.debug("Thread %s: Camera.__init__: Camera destroyed", get_ident())
                    Camera.cam = Picamera2(activeCam)
                    logger.debug("Thread %s: Camera.__init__: Camera instantiated", get_ident())
        self.loadCameraSpecifics()
        super().__init__()
        
    @staticmethod
    def getActiveCamera() -> int:
        """ Load the global camera info, if not already done,
            Which gives us the list of currently connected cameras.
            
            Then check the active camera and return it
        """
        logger.info("Thread %s: Camera.loadGlobalCameraInfo", get_ident())
        cfg = CameraCfg()
        if len(cfg.cameras) == 0:
            cfgCams = []
            cams = Picamera2.global_camera_info()
            if len(cams) == 0:
                raise SystemError("No cameras were found on the server's device")
            for camera in cams:
                cfgCam = CameraInfo()
                cfgCam.model = camera["Model"]
                cfgCam.location = camera["Location"]
                cfgCam.rotation = camera["Rotation"]
                cfgCam.id = camera["Id"]
                # On devices with a single camera, "Num" is not in the dict
                if "Num" in camera:
                    cfgCam.num = camera["Num"]
                else:
                    cfgCam.num = 0
                cfgCams.append(cfgCam)
            cfg.cameras = cfgCams
            logger.info("Thread %s: Camera.loadGlobalCameraInfo - %s cameras found", get_ident(), len(cfg.cameras))
        
        # Check that active camera is within the list of cameras
        sc = cfg.serverConfig
        activeCamOK = False
        activeCam = sc.activeCamera
        for cfgCam in cfg.cameras:
            if cfgCam.num == activeCam:
                activeCamOK = True
                sc.activeCameraInfo = "Camera " + str(cfgCam.num) + " (" + cfgCam.model + ")"
                break
        # If config for active camera is not in the list, set it to the first camera
        if activeCamOK == False:
            sc.activeCamera = cfg.cameras[0].num
            sc.activeCameraInfo = "Camera " + str(cfg.cameras[0].num) + " (" + cfg.cameras[0].model + ")"
            logger.info("Thread %s: Camera.loadGlobalCameraInfo - active camera reset to %s", get_ident(), sc.activeCamera)
        # Make sure that folder for photos exists
        sc.cameraPhotoSubPath = "photos/" + "camera_" + str(sc.activeCamera)
        fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath
        if not os.path.exists(fp):
            os.makedirs(fp)
            logger.info("Thread %s: Camera.loadGlobalCameraInfo - Photo directory created %s", get_ident(), fp)
        
        return cfg.serverConfig.activeCamera
        
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
    def applyControls(camCfg: CameraConfig):
        """Apply the currently selected camera controls"""
        logger.debug("Thread %s: Camera.applyControls", get_ident())

        cfg = CameraCfg()
        cfgCtrls = cfg.controls
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)

        # Initialize controls dict with controls included in configuration
        ctrls = copy.deepcopy(camCfg.controls)
        logger.debug("Thread %s: Camera.applyControls - camCfg.controls=%s", get_ident(), ctrls)
        cnt = 0
        
        # Apply selected controls with precedence of controls from configuration
        # Auto exposure controls
        if cfgCtrls.include_aeEnable and "AeEnable" not in ctrls:
            ctrls["AeEnable"] = cfgCtrls.aeEnable
            cnt += 1
        if cfgCtrls.include_aeMeteringMode and "AeMeteringMode" not in ctrls:
            ctrls["AeMeteringMode"] = cfgCtrls.aeMeteringMode
            cnt += 1
        if cfgCtrls.include_aeExposureMode and "AeExposureMode" not in ctrls:
            ctrls["AeExposureMode"] = cfgCtrls.aeExposureMode
            cnt += 1
        if cfgCtrls.include_aeConstraintMode and "AeConstraintMode" not in ctrls:
            ctrls["AeConstraintMode"] = cfgCtrls.aeConstraintMode
            cnt += 1
        if cfgCtrls.include_aeFlickerMode and "AeFlickerMode" not in ctrls:
            ctrls["AeFlickerMode"] = cfgCtrls.aeFlickerMode
            cnt += 1
        if cfgCtrls.include_aeFlickerPeriod and "AeFlickerPeriod" not in ctrls:
            ctrls["AeFlickerPeriod"] = cfgCtrls.aeFlickerPeriod
            cnt += 1
        # Exposure controls
        if cfgCtrls.include_exposureTime and "ExposureTime" not in ctrls:
            ctrls["ExposureTime"] = cfgCtrls.exposureTime
            cnt += 1
        if cfgCtrls.include_exposureValue and "ExposureValue" not in ctrls:
            ctrls["ExposureValue"] = cfgCtrls.exposureValue
            cnt += 1
        if cfgCtrls.include_analogueGain and "AnalogueGain" not in ctrls:
            ctrls["AnalogueGain"] = cfgCtrls.analogueGain
            cnt += 1
        if cfgCtrls.include_colourGains and "ColourGains" not in ctrls:
            ctrls["ColourGains"] = (cfgCtrls.colourGainRed, cfgCtrls.colourGainBlue)
            cnt += 1
        if cfgCtrls.include_frameDurationLimits and "FrameDurationLimits" not in ctrls:
            ctrls["FrameDurationLimits"] = (cfgCtrls.frameDurationLimitMax, cfgCtrls.frameDurationLimitMin)
            cnt += 1
        if cfgCtrls.include_hdrMode and "HdrMode" not in ctrls:
            ctrls["HdrMode"] = cfgCtrls.hdrMode
            cnt += 1
        # Image controls
        if cfgCtrls.include_awbEnable and "AwbEnable" not in ctrls:
            ctrls["AwbEnable"] = cfgCtrls.awbEnable
            cnt += 1
        if cfgCtrls.include_awbMode and "AwbMode" not in ctrls:
            ctrls["AwbMode"] = cfgCtrls.awbMode
            cnt += 1
        if cfgCtrls.include_noiseReductionMode and "NoiseReductionMode" not in ctrls:
            ctrls["NoiseReductionMode"] = cfgCtrls.noiseReductionMode
            cnt += 1
        if cfgCtrls.include_sharpness and "Sharpness" not in ctrls:
            ctrls["Sharpness"] = cfgCtrls.sharpness
            cnt += 1
        if cfgCtrls.include_contrast and "Contrast" not in ctrls:
            ctrls["Contrast"] = cfgCtrls.contrast
            cnt += 1
        if cfgCtrls.include_saturation and "Saturation" not in ctrls:
            ctrls["Saturation"] = cfgCtrls.saturation
            cnt += 1
        if cfgCtrls.include_brightness and "Brightness" not in ctrls:
            ctrls["Brightness"] = cfgCtrls.brightness
            cnt += 1
        # Scaler crop
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)
        logger.debug("Thread %s: Camera.applyControls - include_scalerCrop=%s", get_ident(), cfgCtrls.include_scalerCrop)
        if cfgCtrls.include_scalerCrop and "ScalerCrop" not in ctrls:
            ctrls["ScalerCrop"] = cfgCtrls.scalerCrop
            cnt += 1
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)
        # Focus
        if cfg.cameraProperties.hasFocus:
            if cfgCtrls.include_afMode and "AfMode" not in ctrls:
                ctrls["AfMode"] = cfgCtrls.afMode
                cnt += 1
            if cfgCtrls.include_lensPosition and "LensPosition" not in ctrls:
                ctrls["LensPosition"] = cfgCtrls.lensPosition
                cnt += 1
            if cfgCtrls.include_afMetering and "AfMetering" not in ctrls:
                ctrls["AfMetering"] = cfgCtrls.afMetering
                cnt += 1
            if cfgCtrls.include_afPause and "AfPause" not in ctrls:
                ctrls["AfPause"] = cfgCtrls.afPause
                cnt += 1
            if cfgCtrls.include_afRange and "AfRange" not in ctrls:
                ctrls["AfRange"] = cfgCtrls.afRange
                cnt += 1
            if cfgCtrls.include_afSpeed and "AfSpeed" not in ctrls:
                ctrls["AfSpeed"] = cfgCtrls.afSpeed
                cnt += 1
            if cfgCtrls.include_afTrigger and "AfTrigger" not in ctrls:
                ctrls["AfTrigger"] = cfgCtrls.afTrigger
                cnt += 1
            if cfgCtrls.include_afWindows and "AfWindows" not in ctrls:
                ctrls["AfWindows"] = cfgCtrls.afWindows
                cnt += 1
            
        logger.debug("Thread %s: Camera.applyControls - Applying %s controls", get_ident(), cnt)
        camCtrls = Controls(Camera.cam)
        camCtrls.set_controls(ctrls)
        Camera.cam.controls = camCtrls
        logger.debug("Thread %s: Camera.applyControls - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)
        logger.debug("Thread %s: Camera.applyControls - cfg.liveViewConfig.controls=%s", get_ident(), cfg.liveViewConfig.controls)

    @staticmethod
    def applyControlsForAfCycle(camCfg: CameraConfig):
        """Apply camera controls required for AF cycle"""
        logger.debug("Thread %s: Camera.applyControlsForAfCycle", get_ident())

        cfg = CameraCfg()
        cfgCtrls = cfg.controls

        # Initialize controls dict with controls included in configuration
        ctrls = copy.deepcopy(camCfg.controls)
        cnt = 0
        # Focus
        if cfg.cameraProperties.hasFocus:
            if cfgCtrls.include_afMode and "AfMode" not in ctrls:
                ctrls["AfMode"] = cfgCtrls.afMode
                cnt += 1
            if cfgCtrls.include_afMetering and "AfMetering" not in ctrls:
                ctrls["AfMetering"] = cfgCtrls.afMetering
                cnt += 1
            if cfgCtrls.include_afPause and "AfPause" not in ctrls:
                ctrls["AfPause"] = cfgCtrls.afPause
                cnt += 1
            if cfgCtrls.include_afRange and "AfRange" not in ctrls:
                ctrls["AfRange"] = cfgCtrls.afRange
                cnt += 1
            if cfgCtrls.include_afSpeed and "AfSpeed" not in ctrls:
                ctrls["AfSpeed"] = cfgCtrls.afSpeed
                cnt += 1
            if cfgCtrls.include_afWindows and "AfWindows" not in ctrls:
                ctrls["AfWindows"] = cfgCtrls.afWindows
                cnt += 1
            
        logger.debug("Thread %s: Camera.applyControlsForAfCycle - Applying %s controls", get_ident(), cnt)
        camCtrls = Controls(Camera.cam)
        camCtrls.set_controls(ctrls)
        Camera.cam.controls = camCtrls
        logger.debug("Thread %s: Camera.applyControlsForAfCycle - Camera.cam.controls=%s", get_ident(), Camera.cam.controls)

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
        
        logger.debug("Thread %s: Camera.stopCameraSystem: Stopping Video thread", get_ident())
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
        logger.debug("Camera.restartLiveView")
        logger.debug("Camera.restartLiveView: Stopping thread")
        BaseCamera.stopRequested = True
        cnt = 0
        while BaseCamera.thread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Background thread did not stop within 2 sec")
        logger.debug("Camera.restartLiveView: Thread has stopped")
        Camera.cam.stop_recording()
        logger.debug("Camera.restartLiveView: Recording stopped")

    @staticmethod
    def takeImage(filename: str):
        """ Takes a photo with the specified file name and returns the path
            filename: file name for the photo
        """
        logger.debug("Camera.takeImage")
        fp = ""
        cfg = CameraCfg()
        sc = cfg.serverConfig
        logger.debug("Camera.takeImage: Stopping thread")
        BaseCamera.stopRequested = True
        cnt = 0
        while BaseCamera.thread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Background thread did not stop within 2 sec")
        logger.debug("Camera.takeImage: Thread has stopped")
        Camera.cam.stop_recording()
        logger.debug("Camera.takeImage: Recording stopped")
        Camera.cam = Picamera2(sc.activeCamera)
        logger.debug("Camera.takeImage: Camera reinitialized")
        logger.debug("Camera.takeImage: Camera controls: %s", Camera.cam.controls)
        with Camera.cam as cam:
            photoConfig = Camera.configure(cfg.photoConfig, cfg.photoConfig)
            cam.configure(photoConfig)
            logger.debug("Camera.takeImage: Camera configured for photo")
            logger.debug("Camera.takeImage: Camera controls: %s", Camera.cam.controls)
            Camera.applyControls(cfg.photoConfig)
            logger.debug("Camera.takeImage: Selected controls applied")
            logger.debug("Camera.takeImage: Camera controls: %s", Camera.cam.controls)
            cam.start(show_preview=False)
            logger.debug("Camera.takeImage: Camera started")
            request = cam.capture_request()
            logger.debug("Camera.takeImage: Request started")
            fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filename
            request.save("main", fp)
            sc.displayFile = filename
            sc.displayPhoto = sc.cameraPhotoSubPath + "/" + filename
            sc.isDisplayHidden = False
            logger.debug("Camera.takeImage: Image saved as %s", fp)
            metadata = request.get_metadata()
            sc.displayMeta = {"Camera": sc.activeCameraInfo}
            sc.displayMeta.update(metadata)
            sc.displayMetaFirst = 0
            if len(metadata) < 11:
                sc._displayMetaLast = 999
            else:
                sc.displayMetaLast = 10
            logger.debug("Camera.takeImage: Image metedata captured")
            request.release()
            logger.debug("Camera.takeImage: Request released")
        return fp

    @staticmethod
    def takeRawImage(filenameRaw: str, filename: str):
        """ Takes a photo as well as a raw image with the specified file names 
            and returns the path for the raw photo
            filenameRaw: file name for the raw image
            filename:    file name for the photo   
        """
        logger.debug("Camera.takeRawImage")
        fpr = ""
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
        Camera.cam = Picamera2(sc.activeCamera)
        with Camera.cam as cam:
            rawConfig = Camera.configure(cfg.rawConfig, cfg.photoConfig)
            cam.configure(rawConfig)
            logger.debug("Camera.takeRawImage: Camera configured for raw")
            Camera.applyControls(cfg.rawConfig)
            logger.debug("Camera.takeRawImage: Selected controls applied")
            cam.start(show_preview=False)
            logger.debug("Camera.takeRawImage: Camera started")
            request = cam.capture_request()
            logger.debug("Camera.takeRawImage: Request started")
            fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filename
            request.save("main", fp)
            fpr = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filenameRaw
            request.save_dng(fpr)
            sc.displayFile = filenameRaw
            sc.displayPhoto = sc.cameraPhotoSubPath + "/" + filename
            sc.isDisplayHidden = False
            logger.debug("Camera.takeRawImage: Raw Image saved as %s", fpr)
            metadata = request.get_metadata()
            sc.displayMeta = {"Camera": sc.activeCameraInfo}
            sc.displayMeta.update(metadata)
            sc.displayMetaFirst = 0
            if len(metadata) < 11:
                sc._displayMetaLast = 999
            else:
                sc.displayMetaLast = 10
            logger.debug("Camera.takeRawImage: Raw Image metedata captured")
            request.release()
            logger.debug("Camera.takeRawImage: Request released")
        return fpr

    @staticmethod
    def frames():
        logger.debug("Thread %s: Camera.frames", get_ident())
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfg = srvCam.liveViewConfig
            streamingConfig = Camera.configure(cfg, srvCam.photoConfig)
            cam.configure(streamingConfig)
            logger.debug("Thread %s: Camera.frames - starting recording", get_ident())
            output = StreamingOutput()
            cam.start_recording(MJPEGEncoder(), FileOutput(output))
            logger.debug("Thread %s: Camera.frames - recording started", get_ident())
            # let camera warm up
            time.sleep(1.5)
            Camera.applyControls(cfg)
            logger.debug("Thread %s: Camera.frames - controls applied", get_ident())
            # Get the live view scaler crop
            time.sleep(0.5)
            metadata = Camera.cam.capture_metadata()
            srvCam.serverConfig.scalerCropLiveView = metadata["ScalerCrop"]
            while True:
                logger.debug("Thread %s: Camera.frames - Receiving camera stream", get_ident())
                with output.condition:
                    logger.debug("Thread %s: Camera.frames - waiting", get_ident())
                    output.condition.wait()
                    logger.debug("Thread %s: Camera.frames - waiting done", get_ident())
                    frame = output.frame
                    l = len(frame)
                logger.debug("Thread %s: Camera.frames - got frame with length %s", get_ident(), l)
                yield frame
    
    @staticmethod
    def _videoThread():
        logger.debug("Thread %s: _videoThread", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        # First, stop the camera system
        Camera.stopCameraSystem()
        # Deactivate Live View to avoid the Live View thread to start
        
        Camera.cam = Picamera2(sc.activeCamera)
        logger.debug("Thread %s: _videoThread - Camera reassigned", get_ident())
        logger.debug("Thread %s: _videoThread - Camera isOpen=%s started=%s", get_ident(), Camera.cam.is_open, Camera.cam.started)
        with Camera.cam as cam:
            srvCam = CameraCfg()
            cfg = srvCam.videoConfig
            videoConfig = Camera.configure(cfg, srvCam.photoConfig)
            cam.configure(videoConfig)
            logger.debug("Thread %s: _videoThread - Video configuration done", get_ident())
            Camera.applyControls(cfg)
            logger.debug("Thread %s: _videoThread - selected controls applied", get_ident())
            encoder = H264Encoder(10000000)
            output = Camera.videoOutput
            if output.lower().endswith(".mp4"):
                encoder.output = FfmpegOutput(output, audio=False)
                logger.debug("Thread %s: _videoThread - mp4 Video output to %s", get_ident(), output)
            else:
                encoder.output = FileOutput(output)
                logger.debug("Thread %s: _videoThread - h264 Video output to %s", get_ident(), output)
            try:
                cam.start()
                logger.debug("Thread %s: _videoThread - Camera started", get_ident())
                cam.start_encoder(encoder)
                logger.debug("Thread %s: _videoThread - Encoder started", get_ident())
                while Camera.stopVideoRequested == False:
                    time.sleep(0.1)
                logger.debug("Thread %s: _videoThread - stop video requested", get_ident())
                cam.stop_encoder()
                logger.debug("Thread %s: _videoThread - encoder stopped", get_ident())
                cam.stop()
                logger.debug("Thread %s: _videoThread - camera stopped", get_ident())
            except ProcessLookupError:
                logger.debug("Thread %s: _videoThread - Encoder could not be started (requested resolution too high)", get_ident())
                BaseCamera.liveViewDeactivated = False
            except RuntimeError:
                logger.debug("Thread %s: _videoThread - Encoder could not be started (not enough memory for requested resolution)", get_ident())
                BaseCamera.liveViewDeactivated = False
            
        BaseCamera.videoThread = None
        logger.debug("Thread %s: _videoThread - videoThread terminated", get_ident())

    @staticmethod
    def recordVideo(filename: str):
        """Record a video in an own thread"""
        logger.debug("Thread %s: recordVideo. filename=%s", get_ident(), filename)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        output = sc.photoRoot + "/" + sc.cameraPhotoSubPath + "/" + filename

        BaseCamera.liveViewDeactivated = True
        logger.debug("Thread %s: recordVideo - Live view deactivated", get_ident())
        
        if BaseCamera.videoThread is None:
            Camera.videoOutput = output
            logger.debug("Thread %s: recordVideo - Starting new videoThread", get_ident())
            BaseCamera.videoThread = threading.Thread(target=Camera._videoThread, daemon=True)
            BaseCamera.videoThread.start()
            logger.debug("Thread %s: recordVideo - videoThread started", get_ident())
        return output

    @staticmethod
    def stopVideoRecording():
        """stops the video recording"""
        logger.debug("Thread %s: stopVideoRecording", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        BaseCamera.stopVideoRequested = True
        cnt = 0
        while BaseCamera.videoThread:
            time.sleep(0.01)
            cnt += 1
            if cnt > 200:
                raise TimeoutError("Video thread did not stop within 2 sec")
        logger.debug("Thread %s: stopVideoRecording: Thread has stopped", get_ident())
        Camera.cam = Picamera2(sc.activeCamera)
        BaseCamera.liveViewDeactivated = False
        
    @staticmethod
    def isVideoRecording() -> bool:
        return BaseCamera.videoThread is not None

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
