from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required
from raspiCamSrv.camera_pi import Camera
import logging

bp = Blueprint("home", __name__)

logger = logging.getLogger(__name__)

@bp.route("/")
@login_required
def index():
    return render_template("home/index.html")

def gen(camera):
    """Video streaming generator function."""
    logger.debug("In gen")
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()
        l = len(frame)
        logger.debug("Got frame of length %s", l)
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/video_feed")
@login_required
def video_feed():
    logger.debug("In video_feed")
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')