import io
import time
from raspiCamSrv.camera_base import BaseCamera
from threading import Condition
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from threading import Condition
import logging

logger = logging.getLogger(__name__)

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        logger.debug("StreamingOutput.__init__")
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        #logger.debug("StreamingOutput.write")
        with self.condition:
            self.frame = buf
            #logger.debug("got buffer of length %s", len(buf))
            self.condition.notify_all()
            #logger.debug("notification done")
        #logger.debug("write done")

class Camera(BaseCamera):
    def __init__(self):
        logger.debug("Camera.__init__")
        self.isStreaming = False
        self.output = None
        super().__init__()
            
    def startStreaming(self):
        logger.debug("Camera.startStreaming")
        with Picamera2() as cam:
            streamingConfig = cam.create_video_configuration(main={"size": (640, 480)})
            cam.configure(streamingConfig)
            logger.debug("starting stream")
            self.output = StreamingOutput()
            cam.start_recording(JpegEncoder(),FileOutput(self.output))
            self.isStreaming = True
            
    def stopStreaming(self):
        logger.debug("starting stream, if required")
        if self.isStreaming:
            with Picamera2() as cam:
                logger.debug("stopping stream")
                cam.stop_recording()
                self.isStreaming = False
            
    @staticmethod
    def frames():
        logger.debug("Camera.frames")
        with Picamera2() as cam:
            streamingConfig = cam.create_video_configuration(main={"size": (640, 480)})
            cam.configure(streamingConfig)
            logger.debug("starting recording")
            output = StreamingOutput()
            cam.start_recording(JpegEncoder(),FileOutput(output))
            # let camera warm up
            logger.debug("recording started")
            time.sleep(2)
            while True:
                #logger.debug("Receiving camera stream")
                with output.condition:
                    #logger.debug("waiting")
#                    output.condition.wait()
                    #logger.debug("waiting done")
                    frame = output.frame
                    #l = len(frame)
                #logger.debug("got frame with length %s", l)
                yield frame
