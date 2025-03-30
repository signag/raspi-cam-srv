from flask import Blueprint, Response, flash, g, render_template, request, current_app
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg, CameraControls, CameraProperties, CameraConfig, ServerConfig, TriggerConfig, TuningConfig, vButton, ActionButton
from raspiCamSrv.camCfg import GPIODevice
from raspiCamSrv.camera_pi import Camera, CameraEvent
from raspiCamSrv.version import version
from raspiCamSrv.db import get_db
from gpiozero import Button, RotaryEncoder, MotionSensor, DistanceSensor, LightSensor, LineSensor
from gpiozero import LED, PWMLED, RGBLED, Buzzer, TonalBuzzer, Servo, AngularServo, Motor
from raspiCamSrv.gpioDevices import StepperMotor
import os
import ast
import time
from pathlib import Path
import json
from raspiCamSrv.auth import login_required
import logging

# Try to import flask_jwt_extended to avoid errors when upgrading to V2.11 from earlier versions
try:
    from flask_jwt_extended import create_access_token
except ImportError:
    pass


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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    sc.lastSettingsTab = "settingsparams"
    if request.method == "POST":
        msg = None
        if sc.isTriggerRecording:
            msg = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not msg:
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
                        sc.activeCameraModel = cm.model
                        break
                strCfg = cfg.streamingCfg
                newCamStr = str(activeCam)
                if newCamStr in strCfg:
                    ncfg = strCfg[newCamStr]
                    if "tuningconfig" in ncfg:
                        cfg.tuningConfig = ncfg["tuningconfig"]
                    else:
                        cfg.tuningConfig = TuningConfig
                else:
                    cfg.tuningConfig = TuningConfig
                Camera.switchCamera()
                msg = "Camera switched to " + sc.activeCameraInfo
                logger.debug("serverconfig - active camera set to %s", sc.activeCamera)
            recordAudio = not request.form.get("recordaudio") is None
            sc.recordAudio = recordAudio        
            audioSync = request.form["audiosync"]
            sc.audioSync = audioSync
            useHist = not request.form.get("showhistograms") is None
            if not useHist:
                sc.displayContent = "meta"
            sc.useHistograms = useHist
            sc.requireAuthForStreaming = not request.form.get("requireAuthForStreaming") is None
            useAPI = not request.form.get("useapi") is None
            sc.useAPI = useAPI
            sc.locLatitude = float(request.form["loclatitude"])
            sc.locLongitude = float(request.form["loclongitude"])
            sc.locElevation = float(request.form["locelevation"])
            sc.locTzKey = request.form["loctzkey"]
        if msg:
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        logger.debug("Stopping camera system")
        Camera().stopCameraSystem()
        Camera.liveViewDeactivated = False
        Camera.thread = None
        Camera.thread2 = None
        Camera.videoThread = None
        Camera.photoSeriesThread = None
        logger.debug("Resetting server configuration")
        photoRoot = sc.photoRoot
        cfg = CameraCfg()
        cfg.cameras = []
        cfg.sensorModes = []
        cfg.rawFormats = []
        cfg.tuningConfig = TuningConfig()
        cfg.controls = CameraControls()
        cfg.controlsBackup = None
        cfg.cameraProperties = CameraProperties()
        cfg.liveViewConfig = CameraConfig()
        cfg.liveViewConfig.id = "LIVE"
        cfg.liveViewConfig.use_case = "Live view"
        cfg.liveViewConfig.stream = "lores"
        cfg.liveViewConfig.buffer_count = 6
        cfg.liveViewConfig.encode = "main"
        cfg.liveViewConfig.controls["FrameDurationLimits"] = (33333, 33333)
        cfg.photoConfig = CameraConfig()
        cfg.photoConfig.id = "FOTO"
        cfg.photoConfig.use_case = "Photo"
        cfg.photoConfig.buffer_count = 1
        cfg.photoConfig.controls["FrameDurationLimits"] = (100, 1000000000)
        cfg.rawConfig = CameraConfig()
        cfg.rawConfig.id = "PRAW"
        cfg.rawConfig.use_case = "Raw Photo"
        cfg.rawConfig.buffer_count = 1
        cfg.rawConfig.stream = "raw"
        cfg.rawConfig.controls["FrameDurationLimits"] = (100, 1000000000)
        cfg.videoConfig = CameraConfig()
        cfg.videoConfig.buffer_count = 6
        cfg.videoConfig.id = "VIDO"
        cfg.videoConfig.use_case = "Video"
        cfg.videoConfig.buffer_count = 6
        cfg.videoConfig.encode = "main"
        cfg.videoConfig.controls["FrameDurationLimits"] = (33333, 33333)
        cfg._cameraConfigs = []
        cfg.triggerConfig = TriggerConfig()
        cfg.serverConfig = ServerConfig()
        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        sc.photoRoot = photoRoot
        if sc.raspiModelLower5:
            cfg.liveViewConfig.format = "YUV420"
        if sc.raspiModelFull.startswith("Raspberry Pi Zero") \
        or sc.raspiModelFull.startswith("Raspberry Pi 4") \
        or sc.raspiModelFull.startswith("Raspberry Pi 3") \
        or sc.raspiModelFull.startswith("Raspberry Pi 2") \
        or sc.raspiModelFull.startswith("Raspberry Pi 1"):
            # For Pi Zero and 4 reduce buffer_count defaults for live view and video
            cfg.liveViewConfig.buffer_count = 2
            cfg.videoConfig.buffer_count = 2
        cfg.streamingCfg = {}
        
        sc.isVideoRecording = False
        sc.isAudioRecording = False
        sc.isTriggerRecording = False
        sc.isPhotoSeriesRecording = False
        sc.isLiveStream = False
        sc.isLiveStream2 = False
        sc.checkMicrophone()
        sc.checkEnvironment()
        sc.curMenu = "settings"
        
        Camera.cam = None
        Camera.cam2 = None
        Camera.camNum = -1
        Camera.camNum2 = -1
        Camera.ctrl = None
        Camera.ctrl2 = None
        Camera.videoOutput = None
        Camera.prgVideoOutput = None
        Camera.photoSeries = None
        Camera.thread = None
        Camera.thread2 = None
        Camera.liveViewDeactivated = False
        Camera.videoThread = None
        Camera.photoSeriesThread = None
        Camera.frame = None
        Camera.frame2 = None
        Camera.last_access = 0
        Camera.last_access2 = 0
        Camera.stopRequested = False
        Camera.stopRequested2 = False
        Camera.stopVideoRequested = False
        Camera.videoDuration = 0
        Camera.stopPhotoSeriesRequested = False
        Camera.event = CameraEvent()
        Camera.event2 = None
        Camera._instance = None
        
        msg = "Server configuration has been reset to default values"
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsusers"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    if request.method == "POST":
        cnt = 0
        msg = None
        if not msg:
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
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsusers"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    if request.method == "POST":
        return render_template("auth/register.html", sc=sc, cp=cp)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        cfgPath = current_app.static_folder + "/config"
        # Initialize the Photo viewer list
        sc = cfg.serverConfig
        sc.pvList = []
        sc.updateStreamingClients()
        cfg.persist(cfgPath)
        msg = "Configuration stored under " + cfgPath
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        cfg.loadConfig(cfgPath)
        msg = "Configuration loaded from " + cfgPath
        flash(msg)
        Camera().restartLiveStream()
        if Camera().cam2:
            Camera().restartLiveStream2()
        cam = Camera()
        cfg = CameraCfg()
        cs = cfg.cameras
        sc = cfg.serverConfig
        sc.checkMicrophone()
        cp = cfg.cameraProperties
        sc.curMenu = "settings"
        cfgPath = current_app.static_folder + "/config"
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

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
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        cb = not request.form.get("loadconfigonstartcb") is None
        setLoadConfigOnStart(cfgPath, cb)
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
    
@bp.route('/shutdown', methods=("GET", "POST"))
@login_required
def shutdown():
    logger.debug("In shutdown")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        shutdown = request.environ.get('werkzeug.server.shutdown')
        if shutdown is None:
            msg = "raspiCamSrv is not running with Werkzeug Server. Shut down manually."
        else:
            shutdown()
            msg = "Server shutting down ..."
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

@bp.route("/api_config", methods=("GET", "POST"))
@login_required
def api_config():
    logger.debug("In api_config")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    sc.lastSettingsTab = "settingsapi"
    if request.method == "POST":
        msg = ""
        sc = cfg.serverConfig
        jwtAccessTokenExpirationMin = sc.jwtAccessTokenExpirationMin
        jwtRefreshTokenExpirationDays = sc.jwtRefreshTokenExpirationDays
        jwtKeyStore = request.form["jwtkeystore"]
        logger.debug("api_config - jwtKeyStore=%s", jwtKeyStore)
        if jwtKeyStore != "":
            if os.path.exists(jwtKeyStore):
                if os.path.isfile(jwtKeyStore):
                    with open(jwtKeyStore) as f:
                        try:
                            secrets = json.load(f)
                            sc.jwtKeyStore = jwtKeyStore
                            logger.debug("api_config - jwtKeyStore successfully accessed")
                        except Exception as e:
                            msg = f"Error when accessing JWT Secret Key File: {e}"
                else:
                    sc.jwtKeyStore = jwtKeyStore
            else:
                sc.jwtKeyStore = jwtKeyStore
        else:
            sc.jwtKeyStore = ""
        sc.jwtAccessTokenExpirationMin = int(request.form["jwtaccesstokenexpirationmin"])
        sc.jwtRefreshTokenExpirationDays = int(request.form["jwtrefreshtokenexpirationdays"])
        if msg == "":
            (secretKey, err, msg) = sc.checkJwtSettings()
            logger.debug("api_config - secrKey = %s, err = %s, msg = %s", secretKey, err, msg)
            if not err is None:
                msg = "ERROR: " + err
        if msg != "":
            flash(msg)
        if sc.API_active == True:
            if sc.jwtAuthenticationActive == True:
                if jwtAccessTokenExpirationMin != sc.jwtAccessTokenExpirationMin \
                or jwtRefreshTokenExpirationDays != sc.jwtRefreshTokenExpirationDays:
                    sc.jwtAuthenticationActive = False
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

@bp.route("/generate_token", methods=("GET", "POST"))
@login_required
def generate_token():
    logger.debug("In generate_token")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    sc.lastSettingsTab = "settingsapi"
    if request.method == "POST":
        access_token = create_access_token(identity=g.user['username'])
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, access_token=access_token)
    
@bp.route('/vbutton_dimensions', methods=("GET", "POST"))
@login_required
def vbutton_dimensions():
    logger.debug("In vbutton_dimensions")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsvbuttons"
    if request.method == "POST":
        msg = ""
        if request.form["vbuttonsrows"]:
            vButtonsRows = int(request.form["vbuttonsrows"])
        else:
            msg = "Please enter a valid number of rows"
        if request.form["vbuttonscols"]:
            vButtonsCols = int(request.form["vbuttonscols"])
        else:
            msg = "Please enter a valid number of columns"
        if msg == "":
            if vButtonsRows == 0 \
            or vButtonsCols == 0:
                sc.vButtonsCols = vButtonsCols
                sc.vButtonsRows = vButtonsRows
                sc.vButtons = []
            else:
                vButtons = []
                for r in range(0, vButtonsRows):
                    row = []
                    for c in range(0, vButtonsCols):
                        if r < sc.vButtonsRows and c < sc.vButtonsCols:
                            btn = sc.vButtons[r][c]
                        else:
                            btn = vButton()
                        btn.row = r
                        btn.col = c
                        row.append(btn)
                    vButtons.append(row)
                sc.vButtonsCols = vButtonsCols
                sc.vButtonsRows = vButtonsRows
                sc.vButtons = vButtons
                sc.vButtonHasCommandLine = not request.form.get("vbuttonhascommandline") is None
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
    
@bp.route('/vbutton_settings', methods=("GET", "POST"))
@login_required
def vbutton_settings():
    logger.debug("In vbutton_settings")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsvbuttons"
    if request.method == "POST":
        msg = ""
        for r in range(0, sc.vButtonsRows):
            for c in range(0, sc.vButtonsCols):
                btn = sc.vButtons[r][c]
                visibleId = f"vbtn_{btn.row}{ btn.col }_visible"
                btn.isVisible = not request.form.get(visibleId) is None
                buttonTextKey = f"vbtn_{btn.row}{btn.col}_buttontext"
                btn.buttonText = request.form[buttonTextKey]
                buttonExecKey = f"vbtn_{btn.row}{btn.col}_buttonexec"
                btn.buttonExec = request.form[buttonExecKey]
                buttonShapeKey = f"vbtn_{btn.row}{btn.col}_shape"
                btn.buttonShape = request.form[buttonShapeKey]
                buttonColorKey = f"vbtn_{btn.row}{btn.col}_color"
                btn.buttonColor = request.form[buttonColorKey]
                confirmId = f"vbtn_{btn.row}{ btn.col }_confirm"
                btn.needsConfirm = not request.form.get(confirmId) is None
                sc.vButtons[r][c] = btn
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
    
@bp.route('/abutton_dimensions', methods=("GET", "POST"))
@login_required
def abutton_dimensions():
    logger.debug("In vbutton_dimensions")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsabuttons"
    if request.method == "POST":
        msg = ""
        if request.form["abuttonsrows"]:
            aButtonsRows = int(request.form["abuttonsrows"])
        else:
            msg = "Please enter a valid number of rows"
        if request.form["abuttonscols"]:
            aButtonsCols = int(request.form["abuttonscols"])
        else:
            msg = "Please enter a valid number of columns"
        if msg == "":
            if aButtonsRows == 0 \
            or aButtonsCols == 0:
                sc.aButtonsCols = aButtonsCols
                sc.aButtonsRows = aButtonsRows
                sc.aButtons = []
            else:
                aButtons = []
                for r in range(0, aButtonsRows):
                    row = []
                    for c in range(0, aButtonsCols):
                        if r < sc.aButtonsRows and c < sc.aButtonsCols:
                            btn = sc.aButtons[r][c]
                        else:
                            btn = ActionButton()
                        btn.row = r
                        btn.col = c
                        row.append(btn)
                    aButtons.append(row)
                sc.aButtonsCols = aButtonsCols
                sc.aButtonsRows = aButtonsRows
                sc.aButtons = aButtons
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
    
@bp.route('/abutton_settings', methods=("GET", "POST"))
@login_required
def abutton_settings():
    logger.debug("In abutton_settings")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsabuttons"
    if request.method == "POST":
        msg = ""
        for r in range(0, sc.aButtonsRows):
            for c in range(0, sc.aButtonsCols):
                btn = sc.aButtons[r][c]
                visibleId = f"abtn_{btn.row}{ btn.col }_visible"
                btn.isVisible = not request.form.get(visibleId) is None
                buttonTextKey = f"abtn_{btn.row}{btn.col}_buttontext"
                btn.buttonText = request.form[buttonTextKey]
                buttonAction = f"abtn_{btn.row}{btn.col}_action"
                btn.buttonAction = request.form[buttonAction]
                buttonShapeKey = f"abtn_{btn.row}{btn.col}_shape"
                btn.buttonShape = request.form[buttonShapeKey]
                buttonColorKey = f"abtn_{btn.row}{btn.col}_color"
                btn.buttonColor = request.form[buttonColorKey]
                confirmId = f"abtn_{btn.row}{ btn.col }_confirm"
                btn.needsConfirm = not request.form.get(confirmId) is None
                sc.aButtons[r][c] = btn
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
    
@bp.route('/new_device', methods=("GET", "POST"))
@login_required
def new_device():
    logger.debug("In new_device")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = ""
        deviceId = request.form["newdeviceid"]
        deviceTypeId = request.form["newdevicetype"]
        for dev in sc.gpioDevices:
            if dev.id == deviceId:
                msg = "Device IDs must be unique! A device with this ID exists already."
                break
        if msg == "":
            device = GPIODevice()
            device.id = deviceId
            device.type = deviceTypeId
            for dt in sc.deviceTypes:
                if dt["type"] == deviceTypeId:
                    sc.curDeviceType = dt
                    device.usage = dt["usage"]
                    device.docUrl = dt["docUrl"]
                    device.isOk = False
                    params = {}
                    for key, value in dt["params"].items():
                        params[key] = value["value"]
                    device.params = params
            sc.gpioDevices.append(device)
            sc.curDeviceId = deviceId
            sc.curDevice = device
        
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
    
@bp.route('/select_device', methods=("GET", "POST"))
@login_required
def select_device():
    logger.debug("In select_device")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = ""
        deviceId = request.form["selectdevice"]
        for device in sc.gpioDevices:
            if device.id == deviceId:
                sc.curDeviceId = deviceId
                sc.curDevice = device
                type = device.type
                for dt in sc.deviceTypes:
                    if dt["type"] == type:
                        sc.curDeviceType = dt
                        break
                break
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

def checkDeviceDeletion(deviceId: str, tc:TriggerConfig) -> str:
    """ Check whether a device can be deleted
    
    The device must not be used in either triggers or actions.

    Args:
        deviceId (str): Device ID to be deleted

    Returns:
        str: Empty stringif device can be deleted
             Or message where device occurs
    """
    msg = ""
    inTrg = []
    for trigger in tc.triggers:
        if trigger.device == deviceId:
            inTrg.append(trigger.id)
    
    inAction = []
    for action in tc.actions:
        if action.device == deviceId:
            inAction.append(action.id)

    if len(inTrg) > 0 or len(inAction) > 0:
        msg = f"Device {deviceId} cannot be deleted because it is used in"
        if len(inTrg) > 0:
            msg = msg + " Triggers " + str(inTrg)
        if len(inAction) > 0:
            msg = msg + " Actions " + str(inAction)
    return msg        
            
    
@bp.route('/delete_device', methods=("GET", "POST"))
@login_required
def delete_device():
    logger.debug("In delete_device")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = checkDeviceDeletion(sc.curDeviceId, tc)
        if msg == "":
            idxDel = -1
            idx = 0
            for device in sc.gpioDevices:
                if device.id == sc.curDeviceId:
                    idxDel = idx
                    break
                idx += 1
            if idxDel >= 0:
                pass
                del sc.gpioDevices[idxDel]
            
            if len(sc.gpioDevices) > 0:
                sc.curDevice = sc.gpioDevices[0]
                sc.curDeviceId = sc.curDevice.id
                for deviceType in sc.deviceTypes:
                    if deviceType["type"] == sc.curDevice.type:
                        sc.curDeviceType = deviceType
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

def parseTuple(stuple: str) -> tuple[str, tuple]:
    """ Parse a string which is assumed to be a tuple

    Args:
        stuple (str): string to be tuplelized

    Returns:
        tuple[str, tuple]: 
            - error
            - tuplelized string    
    """
    rest = stuple
    err = ""
    try:
        tpl = ast.literal_eval(str(stuple))
        if type(tpl) is tuple:
            rest = tpl
        else:
            err = f"{stuple} could not be cast to type of tuple!"
    except Exception as e:
        err = f"Error parsing {stuple} to tuple: {type(e):{e}}"
    return err, rest

def castType(val:str, tpl:object) ->tuple[str, object]:
    """ Cast the given value to the type of the given template

    Args:
        val (str)   : Value to be casted
        tpl (object): template

    Returns:
        tuple[str, object]: 
            - Error message
            - type-converted value
    """
    err = ""
    res = val
    if type(val) is str:
        try:
            if type(tpl) is str:
                pass
            elif type(tpl) is int:
                res = int(val)
            elif type(tpl) is float:
                res = float(val)
            elif type(tpl) is bool:
                if val == "0":
                    res = False
                elif val == "1":
                    res = True
                elif val.casefold() == "false":
                    res = False
                elif val.casefold == "true":
                    res = True
                else:
                    err = "String does not represent boolean."            
            elif type(tpl) is tuple:
                l = len(tpl)
                err, valt = parseTuple(val)
                if err == "":
                    ll = len(valt)
                    if ll != l:
                        err = f"{val} should be a tuple of length {l}"
                    else:
                        for n in range(0, l):
                            if type(valt[n]) != type(tpl[n]):
                                err = f"{val} : elements of tuple do not have the expected type"
                                break
                        if err == "":
                            res = valt
        except TypeError as e:
            err = f"Type error for {val}: {e}"
        except Exception as e:
            err = f"{type(e)} error for {val}: {e}"
    else:
        err = f"{val} should be a string rather than {type(val)}"
    return err, res

def parseColorTuple(stuple: str) -> tuple:
    rest = (0, 0, 0)
    err = ""
    if stuple.startswith("("):
        tpl = stuple[1:]
        if tpl.endswith(")"):
            tpl = tpl[0: len(tpl) - 1]
            res = tpl.rsplit(",")
            if len(res) == 3:
                for n in range(0, 3):
                    c = res[n]
                    c = c.strip()
                    cnum = c.replace('.','',1).replace(',','',1)
                    if cnum.isdigit() == False:
                        err = "Tuple color values must be numeric."
                if err == "":
                    rest = (float(res[0]), float(res[1]), float(res[2]))
            else:
                err = "Tuple for color must include 3 numeric color values."
        else:
            err="Tuple does not end with ')'."
    else:
        err="Tuple does not start with '('."
    return err, rest

    
@bp.route('/device_properties', methods=("GET", "POST"))
@login_required
def device_properties():
    logger.debug("In device_properties")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = ""
        newParams={}
        usedPins = ""
        ok = True
        try:
            for key, value in sc.curDeviceType["params"].items():
                paramId = f"param_{key}"
                if value["type"] == "str":
                    val = request.form[paramId]
                elif value["type"] == "int":
                    vals = request.form[paramId]
                    if vals != "":
                        val = int(vals)
                    else:
                        val = vals
                elif value["type"] == "float":
                    val = float(request.form[paramId])
                elif value["type"] == "floatOrNone":
                    vals = request.form[paramId]
                    if vals == "None":
                        val = None
                    else:
                        vals = vals.strip()
                        if vals.replace('.','',1).replace(',','',1).isdigit() == True:
                            vals = vals.replace(',', '.', 1)
                            val = float(vals)
                        else:
                            msg = f"{key} must be None or float"
                elif value["type"] == "bool":
                    val = not request.form.get(paramId) is None
                elif value["type"] == "boolOrNone":
                    vals = request.form[paramId]
                    if vals == "None":
                        val = None
                    else:
                        if vals == "True":
                            val = True
                        elif vals == "False":
                            val = False
                        else:
                            msg = f"{key} must be bool or None"
                elif value["type"] == "tuple(float)":
                    vals = request.form[paramId]
                    msg, val = parseColorTuple(vals)
                elif value["type"] == "tuple(int)":
                    vals = request.form[paramId]
                    msg, val = parseTuple(vals)
                else:
                    val = request.form[paramId]
                newParams[key] = val
                if "isPin" in value:
                    if value["isPin"] == True:
                        if usedPins == "":
                            usedPins = f"{val}"
                        else:
                            usedPins += f", {val}"

                if val == "":
                    ok = False
                    
        except Exception as e:
            msg = f"{type(e)}: {e}"
            
        if msg == "":
            sc.curDevice.params = newParams
            sc.curDevice.usedPins = usedPins
            sc.curDevice.isOk = ok
        else:
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)

def storeResult(result:dict, test:str, testResult:str) -> dict:
    """ Store a test result in the results dict
    
    Since dict keys must be unique, test, which is used as key must be made unique,
    in order to avoid that duplicate tests are not registered.

    Args:
        result (dict)   : Results dict
        test (str)      : Test to be registered
        testResult (str): Test result

    Returns:
        dict: Results dict with the test result included
    """
    testu = test
    n = 1
    while testu in result:
        testu = test + " - " + str(n)
        n+= 1
    result[testu] = testResult
    return result
    
@bp.route('/test_device', methods=("GET", "POST"))
@login_required
def test_device():
    logger.debug("In test_device")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    cfgPath = current_app.static_folder + "/config"
    los = getLoadConfigOnStart(cfgPath)
    result = {}
    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = ""
        dev = sc.curDevice
        devType = sc.curDeviceType
        devClass = f"{dev.type}"
        devArgs = dev.params
        logger.debug("settings.test_device - devClass=%s", devClass)
        logger.debug("settings.test_device - devArgs=%s", devArgs)
        if "testMethods" in devType:
            devTests = devType["testMethods"]
            logger.debug("settings.test_device - devTests=%s", devTests)
            try:
                logger.debug("settings.test_device -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
            except Exception as e:
                logger.debug("settings.test_device - Error while instantiating %s:%s, %s", devClass, type(e), e)
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
                try:
                    if devObj:
                        devObj.close()
                except Exception as e:
                    logger.debug("settings.test_device - Error closing %s:%s", devClass, e)
            if msg == "":
                for test in devTests:
                    testMethod = test
                    rawTest = test
                    assignValue = None
                    if type(test) == dict:
                        for key,val in test.items():
                            testMethod = key
                            assignValue = val
                            break
                    elif test.find("=") >= 0:
                        testmethod, assign = test.split("=")
                        if assign[0] == "(":
                            err, assignValue = parseColorTuple(assign)
                        else:
                            assignValue = assign
                        assignValue = castType()
                        
                    logger.debug("settings.test_device - Starting test %s", test)
                    if hasattr(devObj, testMethod):
                        try:
                            attr = getattr(devObj, testMethod)
                            if callable(attr) == True:
                                if assignValue is None:
                                    dispTest = f"{devClass}.{testMethod}()"
                                    logger.debug("settings.test_device - %s", dispTest)
                                    res = attr()
                                    result = storeResult(result, dispTest, res)
                                else:
                                    dispTest = f"{devClass}.{testMethod}({assignValue})"
                                    logger.debug("settings.test_device - %s", dispTest)
                                    res = attr(assignValue)
                                    result = storeResult(result, dispTest, res)
                            else:
                                if assignValue:
                                    dispTest = f"{devClass}.{testMethod}={assignValue}"
                                    logger.debug("settings.test_device - %s.%s=%s",devClass, testMethod, assignValue)
                                    setattr(devObj, testMethod, assignValue)
                                    result = storeResult(result, dispTest, "OK")
                                else:
                                    dispTest = f"{devClass}.{testMethod}"
                                    result = storeResult(result, dispTest, attr)
                                logger.debug("settings.test_device - %s.%s=%s",devClass, testMethod, result[dispTest])
                        except Exception as e:
                            result = storeResult(result, testMethod, f"{type(e)} : {e}")
                            logger.debug("settings.test_device - Exception %s, %s", type(e), e)
                    else:
                        result = storeResult(result, testMethod, f"Class {devClass} has no method {testMethod}")
                    if "testStepDuration" in devType:
                        dur = devType["testStepDuration"]
                        time.sleep(dur)
                if "testDuration" in devType:
                    dur = devType["testDuration"]
                    time.sleep(dur)
                try:
                    if devObj:
                        devObj.close()
                        msg = f"Test completed, {devClass} closed."
                except Exception as e:
                    logger.debug("settings.test_device - Error closing %s:%s", devClass, e)
        else:
            msg = f"No test methods specified for device type {dev.type}"
        if msg != "":
            flash(msg)
    logger.debug("settings.test_device - result %s", result)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result)
