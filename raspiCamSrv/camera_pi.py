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
        logger.debug("Camera.__init__")
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
                
        super().__init__()

    @staticmethod
    def takeImage(fp):
        logger.debug("Camera.takeImage")
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
        Camera.cam = Picamera2()
        logger.debug("Camera.takeImage: Camera reinitialized")
        with Camera.cam as cam:
            stillConfig = cam.create_still_configuration()
            logger.debug("Camera.takeImage: Still config created: %s", stillConfig)
            cam.configure(stillConfig)
            logger.debug("Camera.takeImage: Camera configured for still")
            cam.start(show_preview=False)
            logger.debug("Camera.takeImage: Camera started")
            logger.debug("Camera.takeImage: Image file %s", fp)
            cam.capture_file(fp)
            logger.debug("Camera.takeImage: Image taken %s", fp)

    @staticmethod
    def frames():
        logger.debug("Camera.frames")
        with Camera.cam as cam:
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
