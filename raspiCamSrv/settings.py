from flask import Blueprint, Response, flash, g, render_template, request, current_app
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg, CameraControls, CameraProperties, CameraConfig, ServerConfig
from raspiCamSrv.camera_pi import Camera, BaseCamera
from raspiCamSrv.version import version
from raspiCamSrv.db import get_db
import os
from pathlib import Path

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("settings", __name__)

logger = logging.getLogger(__name__)

@bp.route("/settings")
@login_required
def main():
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

@bp.route("/serverconfig", methods=("GET", "POST"))
@login_required
def serverconfig():
    logger.debug("serverconfig")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    if request.method == "POST":
        photoType = request.form["phototype"]
        sc.photoType = photoType
        rawPhotoType = request.form["rawphototype"]
        sc.rawPhotoType = rawPhotoType
        videoType = request.form["videotype"]
        sc.videoType = videoType
        activeCam = int(request.form["activecamera"])
        # If active camera has changed reset stream size to force adaptation of sensor mode
        if activeCam != sc.activeCamera:
            cfg.liveViewConfig.stream_size = None
            cfg.photoConfig.stream_size = None
            cfg.rawConfig.stream_size = None
            cfg.videoConfig.stream_size = None
        sc.activeCamera = activeCam
        for cm in cs:
            if activeCam == cm.num:
                sc.activeCameraInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
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
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

@bp.route("/resetServer", methods=("GET", "POST"))
@login_required
def resetServer():
    logger.debug("resetServer")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    if request.method == "POST":
        logger.debug("Stopping camera system")
        Camera().stopCameraSystem()
        BaseCamera.liveViewDeactivated = False
        BaseCamera.thread = None
        BaseCamera.videoThread = None
        BaseCamera.timelapseThread = None
        logger.debug("Resetting server configuration")
        photoRoot = sc.photoRoot
        cfg = CameraCfg()
        cfg.cameras = []
        cfg.sensorModes = []
        cfg.rawFormats = []
        cfg.controls = CameraControls()
        cfg.cameraProperties = CameraProperties()
        cfg._liveViewConfig = CameraConfig()
        cfg._liveViewConfig.id = "LIVE"
        cfg._liveViewConfig.use_case = "Live view"
        cfg._liveViewConfig.buffer_count = 4
        cfg._liveViewConfig.encode = "main"
        cfg._liveViewConfig.controls["FrameDurationLimits"] = (33333, 33333)
        cfg._photoConfig = CameraConfig()
        cfg._photoConfig.id = "FOTO"
        cfg._photoConfig.use_case = "Photo"
        cfg._photoConfig.buffer_count = 1
        cfg._photoConfig.controls["FrameDurationLimits"] = (100, 1000000000)
        cfg._rawConfig = CameraConfig()
        cfg._rawConfig.id = "PRAW"
        cfg._rawConfig.use_case = "Raw Photo"
        cfg._rawConfig.buffer_count = 1
        cfg._rawConfig.stream = "raw"
        cfg._rawConfig.controls["FrameDurationLimits"] = (100, 1000000000)
        cfg._videoConfig = CameraConfig()
        cfg._videoConfig.buffer_count = 6
        cfg._videoConfig.id = "VIDO"
        cfg._videoConfig.use_case = "Video"
        cfg._videoConfig.buffer_count = 6
        cfg._videoConfig.encode = "main"
        cfg._videoConfig.controls["FrameDurationLimits"] = (33333, 33333)
        cfg._cameraConfigs = []
        cfg._serverConfig = ServerConfig()
        sc = cfg.serverConfig
        sc.photoRoot = photoRoot
        sc.isVideoRecording = False
        sc.curMenu = "settings"
        sc.checkMicrophone()
        sc.checkEnvironment()
        
        msg = "Server configuration has been reset to default values"
        flash(msg)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

@bp.route("/remove_users", methods=("GET", "POST"))
@login_required
def remove_users():
    logger.debug("In remove_users")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
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
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

@bp.route("/register_user", methods=("GET", "POST"))
@login_required
def register_user():
    logger.debug("In register_user")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    if request.method == "POST":
        return render_template("auth/register.html", sc=sc, cp=cp)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

@bp.route("/store_config", methods=("GET", "POST"))
@login_required
def store_config():
    logger.debug("In store_config")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    if request.method == "POST":
        cfgPath = current_app.static_folder + "/config"
        cfg.persist(cfgPath)
        msg = "Configuration stored under " + cfgPath
        flash(msg)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

@bp.route("/load_config", methods=("GET", "POST"))
@login_required
def load_config():
    logger.debug("In load_config")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    if request.method == "POST":
        cfg.loadConfig(cfgPath)
        msg = "Configuration loaded from " + cfgPath
        flash(msg)
        Camera().restartLiveView()
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)

def getLoadConfigOnStart(cfgPath: str) -> bool:
    logger.debug("getLoadConfigOnStart")
    res = False
    if cfgPath:
        if os.path.exists(cfgPath):
            fp = cfgPath + "/_loadConfigOnStart.txt"
            if os.path.exists(fp):
                res = True
    logger.debug("getLoadConfigOnStart: %s", res)
    return res

def setLoadConfigOnStart(cfgPath: str, value: bool):
    logger.debug("setLoadConfigOnStart - value: %s", value)
    if cfgPath:
        if not os.path.exists(cfgPath):
            os.makedirs(cfgPath, exist_ok=True)
    fp = cfgPath + "/_loadConfigOnStart.txt"
    if value == True:
        Path(fp).touch()
    else:
        if os.path.exists(fp):
            os.remove(fp)

@bp.route("/loadConfigOnStart", methods=("GET", "POST"))
@login_required
def loadConfigOnStart():
    logger.debug("In loadConfigOnStart")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    if request.method == "POST":
        cb = not request.form.get("loadconfigonstartcb") is None
        setLoadConfigOnStart(cfgPath, cb)
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, cp=cp, cs=cs, los=los)
