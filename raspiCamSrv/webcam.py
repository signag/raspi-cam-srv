from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, TuningConfig
from raspiCamSrv.version import version
from _thread import get_ident
import copy

from raspiCamSrv.auth import login_required, login_for_streaming
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
        scfg["tuningconfig"] = copy.deepcopy(cfg.tuningConfig)
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
        msg = None
        cs = cfg.cameras
        activeCam = sc.activeCamera
        newCam = activeCam
        for cm in cs:
            if cm.isUsb == False:
                if activeCam != cm.num:
                    newCam = cm.num
                    newCamInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
                    newCamModel = cm.model
                    break
        if newCam != sc.activeCamera:
            if sc.isTriggerRecording:
                msg = "Please go to 'Trigger' and stop the active process before changing the configuration"
            if sc.isVideoRecording == True:
                msg = "Please stop video recording before changing the tuning configuration"
            if sc.isPhotoSeriesRecording:
                msg = "Please go to 'Photo Series' and stop the active process before changing the tuning configuration"
            if not msg:
                sc.activeCameraInfo = newCamInfo
                sc.activeCameraModel = newCamModel
                cfg.liveViewConfig.stream_size = None
                cfg.photoConfig.stream_size = None
                cfg.rawConfig.stream_size = None
                cfg.videoConfig.stream_size = None
                sc.activeCamera = newCam
                strCfg = cfg.streamingCfg
                newCamStr = str(newCam)
                if newCamStr in strCfg:
                    ncfg = strCfg[newCamStr]
                    if "tuningconfig" in ncfg:
                        cfg.tuningConfig = ncfg["tuningconfig"]
                    else:
                        cfg.tuningConfig = TuningConfig
                else:
                    cfg.tuningConfig = TuningConfig
                Camera.switchCamera()
                if sc.isLiveStream2:
                    str2 = cfg.streamingCfg[str(Camera().camNum2)]
                logger.debug("switch_cameras - active camera set to %s", sc.activeCamera)
        if msg:
            flash(msg)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

@bp.route("/photo_feed")
@login_for_streaming
def photo_feed():
    logger.debug("Thread %s: In photo_feed", get_ident())
    Camera().startLiveStream()
    return Response(Camera().get_photoFrame(), mimetype='image/jpeg')

@bp.route("/photo_feed2")
@login_for_streaming
def photo_feed2():
    logger.debug("Thread %s: In photo_feed2", get_ident())
    Camera().startLiveStream2()
    return Response(Camera().get_photoFrame2(), mimetype='image/jpeg')
