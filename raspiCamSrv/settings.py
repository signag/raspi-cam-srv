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
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/serverconfig", methods=("GET", "POST"))
@login_required
def serverconfig():
    logger.debug("serverconfig")
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    if request.method == "POST":
        photoType = request.form["phototype"]
        sc.photoType = photoType
        rawPhotoType = request.form["rawphototype"]
        sc.rawPhotoType = rawPhotoType
        videoType = request.form["videotype"]
        sc.videoType = videoType
        activeCam = int(request.form["activecamera"])
        sc.activeCamera = activeCam
        for cam in cs:
            if activeCam == cam.num:
                sc.activeCameraInfo = "Camera " + str(cam.num) + " (" + cam.model + ")"
                break
        logger.debug("serverconfig - active camera set to %s", sc.activeCamera)
        chnk = int(request.form["chunkSizePhoto"])
        sc.chunkSizePhoto = chnk
        recordAudio = not request.form.get("recordaudio") is None
        sc.recordAudio = recordAudio        
        audioSync = request.form["audiosync"]
        sc.audioSync = audioSync
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/resetServer", methods=("GET", "POST"))
@login_required
def resetServer():
    logger.debug("resetServer")
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    if request.method == "POST":
        logger.debug("Stopping camera system")
        Camera().stopCameraSystem()
        BaseCamera.liveViewDeactivated = False
        BaseCamera.thread = None
        BaseCamera.videoThread = None
        logger.debug("Resetting server configuration")
        cfg = CameraCfg()
        cfg.cameras = []
        cfg.sensorModes = []
        cfg.rawFormats = []
        sc = cfg.serverConfig
        sc.isVideoRecording = False
        sc.curMenu = "settings"
        sc.checkMicrophone()
    
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs)
