from flask import current_app, g
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
        logging.info("Initializing camera")
        self.cam = Picamera2()
        self.streamingConfig = self.cam.create_video_configuration(main={"size": (640, 480)})
        self.cam.configure(self.streamingConfig)
        self.isStreaming = False
        self.output = None
        
    def __del__(self):
        self.stopStreaming()
        del self.cam
        
    def startStreaming(self):
        logging.info("starting stream, if required")
        if not self.isStreaming:
            logging.info("starting stream")
            self.output = StreamingOutput()
            self.cam.start_recording(JpegEncoder(),FileOutput(self.output))
            self.isStreaming = True
            
    def stopStreaming(self):
        logging.info("starting stream, if required")
        if self.isStreaming:
            logging.info("stopping stream")
            self.cam.stop_recording()
            self.isStreaming = False
            
    def getStream(self):
        logging.info("getting stream")
        self.startStreaming()
        while True:
            with self.output.condition:
                self.output.condition.wait()
                frame = self.output.frame
                l = len(frame)
            logging.info("got frame with length %s", l)
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def get_camera():
    logging.info("getting camera")
    if "camera" not in g:
        logging.info("adding camera to g")
        g.camera = Camera()
    return g.camera


def remove_camera(e=None):
    logging.info("Removing camera")
    camera = g.pop("camera", None)
    if camera:
        del camera


def init_app(app):
    logging.info("init camera app")
    app.teardown_appcontext(remove_camera)
