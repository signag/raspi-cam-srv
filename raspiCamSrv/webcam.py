from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.version import version
from _thread import get_ident

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("webcam", __name__)

logger = logging.getLogger(__name__)

@bp.route("/webcam")
@login_required
def webcam():
    logger.debug("In photo_feed")
    Camera().startLiveStream()
    cam = Camera().cam
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    sc.curMenu = "webcam"
    return render_template("webcam/webcam.html", sm=sm, sc=sc, cp=cp, cs=cs, cfg=cfg)

def genPhoto(camera):
    """photo taking function."""
    logger.debug("Thread %s: In genPhoto", get_ident())
    yield b'--frame\r\n'
    frame = camera.get_photoFrame()
    l = len(frame)
    logger.debug("Thread %s: genPhoto - Got frame of length %s", get_ident(), l)
    yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/photo_feed")
# @login_required
def photo_feed():
    logger.debug("Thread %s: In photo_feed", get_ident())
    return Response(genPhoto(Camera()), mimetype='multipart/x-mixed-replace; boundary=frame')
