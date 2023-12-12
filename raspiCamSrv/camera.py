from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import io
from threading import Condition

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
            
class Camera():
    def __init__(self):
        logging.debug("Initializing camera")
        self.cam = Picamera2()
        self.streamingConfig = self.cam.create_video_configuration(main={"size": (640, 480)})
        self.cam.configure(self.streamingConfig)
        self.isStreaming = False
        self.output = None
        
    def __del__(self):
        self.stopStreaming()
        del self.cam
        
    def stopCamera(self):
        logging.debug("stopping the camera")
        self.stopStreaming()
        if self.cam.started:
            logging.debug("Camera was started and will be stopped")
            self.cam.stop()        
            
    def startStreaming(self):
        logging.debug("starting stream, if required")
        if not self.isStreaming:
            logging.debug("starting stream")
            self.output = StreamingOutput()
            self.cam.start_recording(JpegEncoder(),FileOutput(self.output))
            self.isStreaming = True
            
    def stopStreaming(self):
        logging.debug("starting stream, if required")
        if self.isStreaming:
            logging.debug("stopping stream")
            self.cam.stop_recording()
            self.isStreaming = False
            
    def getStream(self):
        logging.debug("getting stream")
        self.startStreaming()
        while True:
            with self.output.condition:
                self.output.condition.wait()
                frame = self.output.frame
                l = len(frame)
            logging.debug("got frame with length %s", l)
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
