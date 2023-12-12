from flask import g

from raspiCamSrv.camera import Camera
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def get_camera():
    logging.debug("getting camera")
    if "camera" not in g:
        logging.debug("adding camera to g")
        g.camera = Camera()
    return g.camera


def remove_camera(e=None):
    logging.debug("Removing camera")
    
    camera = g.pop("camera", None)
    if camera is not None:
        logging.debug("camera found in application context")
        if camera.isStreaming:
            logging.debug("stop streaming")
            camera.stopStreaming
        camera.stopCamera()
        del camera
    else:
        logging.debug("camera not in application context")


def init_app(app):
    logging.debug("init camera app")
    #app.teardown_appcontext(remove_camera)
    #logging.debug("Added 'remove_camera' to 'teardown_appcontext'")
