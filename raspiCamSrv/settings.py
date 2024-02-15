from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera, BaseCamera
from raspiCamSrv.db import get_db

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
        useHist = not request.form.get("showhistograms") is None
        if not useHist:
            sc.displayContent = "meta"
        sc.useHistograms = useHist
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

@bp.route("/remove_users", methods=("GET", "POST"))
@login_required
def remove_users():
    logger.debug("In remove_users")
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
        cnt = 0
        msg = None
        for user in g.users:
            if request.form.get("sel_" + str(user["id"])) is not None:
                if user["id"] == g.user["id"]:
                    msg = "The active user cannot be removed"
                    break
                else:
                    cnt += 1
        if not msg:
            logger.debug("Request to remove %s users", cnt)
            if cnt > 0:
                db = get_db()
                if cnt < len(g.users):
                    while cnt > 0:
                        logger.debug("cnt: %s", cnt)
                        userDel = None
                        for user in g.users:
                            logger.debug("Trying user %s %s", user["id"], user["username"])
                            if request.form.get("sel_" + str(user["id"])) is not None:
                                userDel =user["id"]
                                logger.debug("User selected")
                                break
                            else:
                                logger.debug("User not selected")
                        if userDel:
                            logger.debug("Removing user with id %s", userDel)
                            db.execute("DELETE FROM user WHERE id = ?", (userDel,)).fetchone
                            db.commit()
                            g.nrUsers = db.execute("SELECT count(*) FROM user").fetchone()[0]
                            logger.debug("Found %s users", g.nrUsers)
                            g.users = db.execute("SELECT * FROM user").fetchall()
                            for user in g.users:
                                logger.debug("Found user: ID: %s, UserName: %s", user["id"], user["username"])
                            cnt -= 1
                else:
                    msg="At least one user must remain"
                    flash(msg)
            else:
                msg="No users were selected"
                flash(msg)
        else:
            flash(msg)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/register_user", methods=("GET", "POST"))
@login_required
def register_user():
    logger.debug("In register_user")
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
        return render_template("auth/register.html", sc=sc, cp=cp)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs)
