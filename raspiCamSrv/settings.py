from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera, BaseCamera

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("settings", __name__)

logger = logging.getLogger(__name__)

@bp.route("/settings")
@login_required
def main():
    g.hostname = request.host
    cfg = CameraCfg()
    sc = cfg.serverConfig
    sc.curMenu = "settings"
    return render_template("settings/main.html", sc=sc)

@bp.route("/serverconfig", methods=("GET", "POST"))
@login_required
def serverconfig():
    logger.info("serverconfig")
    g.hostname = request.host
    cfg = CameraCfg()
    sc = cfg.serverConfig
    sc.curMenu = "settings"
    if request.method == "POST":
        photoType = request.form["phototype"]
        sc.photoType = photoType
        rawPhotoType = request.form["rawphototype"]
        sc.rawPhotoType = rawPhotoType
        videoType = request.form["videotype"]
        sc.videoType = videoType
    
    return render_template("settings/main.html", sc=sc)

@bp.route("/resetServer", methods=("GET", "POST"))
@login_required
def resetServer():
    logger.info("resetServer")
    g.hostname = request.host
    cfg = CameraCfg()
    sc = cfg.serverConfig
    sc.curMenu = "settings"
    if request.method == "POST":
        logger.info("Stopping camera system")
        Camera().stopCameraSystem()
        BaseCamera.liveViewDeactivated = False
        BaseCamera.thread = None
        BaseCamera.videoThread = None
        logger.info("Resetting server configuration")
        del cfg
        cfg = CameraCfg()
        sc = cfg.serverConfig
        sc.isVideoRecording = False
        sc.curMenu = "settings"
    
    return render_template("settings/main.html", sc=sc)
