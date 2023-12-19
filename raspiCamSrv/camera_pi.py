import io
import time
from raspiCamSrv.camera_base import BaseCamera, CameraEvent
import threading
from threading import Condition
from picamera2 import Picamera2
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
            logger.info("Camera.__init__: Camera instantiated")
            Camera.cam = Picamera2()
        else:
            logger.info("Camera.__init__: Camera was already instantiated")
            if not Camera.cam.is_open:
                logger.info("Camera.__init__: Camera was not open")
                Camera.cam = None
                logger.info("Camera.__init__: Camera destroyed")
                Camera.cam = Picamera2()
                logger.info("Camera.__init__: Camera instantiated")
                
        super().__init__()

    @staticmethod
    def takeImage(fp):
        logger.info("Camera.takeImage")
        with Camera.cam as cam:
            stillConfig = cam.create_still_configuration()
            logger.info("Camera.takeImage: Still config created")
            logger.info("Camera.takeImage: Stopping thread")
            cam.stop_recording()
            cam.switch_mode_and_capture_file(stillConfig, fp)
            logger.info("Camera.takeImage: Image taken %s", fp)

    @staticmethod
    def frames():
        logger.debug("Camera.frames")
        with Camera.cam as cam:
            #            streamingConfig = cam.create_video_configuration(main={"size": (640, 480)})
            streamingConfig = cam.create_video_configuration(
                lores={"size": (640, 480), "format": "YUV420"},
                raw=None,
                display=None,
                encode="lores",
            )
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
