from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.version import version
from _thread import get_ident
import copy

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("webcam", __name__)

logger = logging.getLogger(__name__)

@bp.route("/webcam")
@login_required
def webcam():
    logger.debug("In webcam")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    sc.error = None
    sc.errorc2 = None
    Camera().startLiveStream()
    Camera().startLiveStream2()
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    if sc.error:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        flash(msg)
        if sc.error2:
            flash(sc.error2)
    if sc.errorc2:
        msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
        flash(msg)
        if sc.errorc22:
            flash(sc.errorc22)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

@bp.route("/store_streaming_config", methods=("GET", "POST"))
@login_required
def store_streaming_config():
    logger.debug("In store_streaming_config")
    Camera().startLiveStream()
    Camera().startLiveStream2()
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    if request.method == "POST":
        scfg = cfg.streamingCfg[str(sc.activeCamera)]
        scfg["liveconfig"] = copy.deepcopy(cfg.liveViewConfig)
        scfg["videoconfig"] = copy.deepcopy(cfg.videoConfig)
        scfg["controls"] = copy.deepcopy(cfg.controls)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

@bp.route("/switch_cameras", methods=("GET", "POST"))
@login_required
def switch_cameras():
    logger.debug("In switch_cameras")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    if request.method == "POST":
        cs = cfg.cameras
        activeCam = sc.activeCamera
        newCam = activeCam
        for cm in cs:
            if cm.isUsb == False:
                if activeCam != cm.num:
                    newCam = cm.num
                    newCamInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
                    break
        if newCam != sc.activeCamera:
            sc.activeCameraInfo = newCamInfo
            cfg.liveViewConfig.stream_size = None
            cfg.photoConfig.stream_size = None
            cfg.rawConfig.stream_size = None
            cfg.videoConfig.stream_size = None
            sc.activeCamera = newCam
            Camera.switchCamera()
            if sc.isLiveStream2:
                str2 = cfg.streamingCfg[str(Camera().camNum2)]
            logger.debug("switch_cameras - active camera set to %s", sc.activeCamera)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

def genPhoto(camera):
    """photo taking function."""
    logger.debug("Thread %s: In genPhoto", get_ident())
    yield b'--frame\r\n'
    frame = camera.get_photoFrame()
    if frame:
        logger.debug("Thread %s: genPhoto - Got frame of length %s", get_ident(), len(frame))
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

def genPhoto2(camera):
    """photo taking function."""
    logger.debug("Thread %s: In genPhoto", get_ident())
    yield b'--frame\r\n'
    frame = camera.get_photoFrame2()
    if frame:
        logger.debug("Thread %s: genPhoto - Got frame of length %s", get_ident(), len(frame))
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/photo_feed")
# @login_required
def photo_feed():
    logger.debug("Thread %s: In photo_feed", get_ident())
    Camera().startLiveStream()
    return Response(genPhoto(Camera()), mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/photo_feed2")
# @login_required
def photo_feed2():
    logger.debug("Thread %s: In photo_feed2", get_ident())
    Camera().startLiveStream2()
    return Response(genPhoto2(Camera()), mimetype='multipart/x-mixed-replace; boundary=frame')
