from flask import Blueprint, Response, flash, g, render_template, request, current_app
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg, CameraControls, CameraProperties, CameraConfig, ServerConfig, TriggerConfig, TuningConfig, vButton, ActionButton
from raspiCamSrv.camCfg import GPIODevice
from raspiCamSrv.camera_pi import Camera, CameraEvent
from raspiCamSrv.photoseriesCfg import PhotoSeriesCfg
from raspiCamSrv.motionDetector import MotionDetector
from raspiCamSrv.triggerHandler import TriggerHandler
from raspiCamSrv.version import version
from raspiCamSrv.db import get_db
from gpiozero import Button, RotaryEncoder, MotionSensor, DistanceSensor, LightSensor, LineSensor, DigitalInputDevice
from gpiozero import LED, PWMLED, RGBLED, Buzzer, TonalBuzzer, Servo, AngularServo, Motor, DigitalOutputDevice, OutputDevice
from raspiCamSrv.gpioDevices import StepperMotor
import os
import shutil
import ast
import time
from pathlib import Path
import psutil
import subprocess
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
    backups = getBackupsList()

    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsparams"
    if request.method == "POST":
        msg = None
        activeCam = int(request.form["activecamera"])
        if sc.isTriggerRecording:
            msg = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if sc.isVideoRecording == True:
            msg = "Please stop video recording before changing the tuning configuration"
        if sc.isPhotoSeriesRecording:
            msg = "Please go to 'Photo Series' and stop the active process before changing the tuning configuration"
        if not sc.secondCamera is None:
            if activeCam == sc.secondCamera:
                msg = "Active camera must be different from second camera. Use 'Switch Cameras in Cam/Multi-Cam' to swap the cameras."
        if not msg:
            if sc.noCamera == False:
                photoType = request.form["phototype"]
                sc.photoType = photoType
                rawPhotoType = request.form["rawphototype"]
                sc.rawPhotoType = rawPhotoType
                videoType = request.form["videotype"]
                sc.videoType = videoType
                recordAudio = not request.form.get("recordaudio") is None
                sc.recordAudio = recordAudio        
                audioSync = request.form["audiosync"]
                sc.audioSync = audioSync
                useStereo = not request.form.get("usestereo") is None
                sc.useStereo = useStereo
                useHist = not request.form.get("showhistograms") is None
                if not useHist:
                    sc.displayContent = "meta"
                sc.useHistograms = useHist
                sc.requireAuthForStreaming = not request.form.get("requireAuthForStreaming") is None
                # If active camera has changed reset stream size to force adaptation of sensor mode
                if activeCam != sc.activeCamera:
                    sc.activeCamera = activeCam
                    cfg.liveViewConfig.stream_size = None
                    cfg.photoConfig.stream_size = None
                    cfg.rawConfig.stream_size = None
                    cfg.videoConfig.stream_size = None
                    for cm in cs:
                        if activeCam == cm.num:
                            sc.activeCameraInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
                            sc.activeCameraModel = cm.model
                            sc.activeCameraIsUsb = cm.isUsb
                            sc.activeCameraUsbDev = cm.usbDev
                            break
                    strCfg = cfg.streamingCfg
                    newCamStr = str(activeCam)
                    if newCamStr in strCfg:
                        ncfg = strCfg[newCamStr]
                        if "tuningconfig" in ncfg:
                            cfg.tuningConfig = ncfg["tuningconfig"]
                        else:
                            cfg.tuningConfig = TuningConfig()
                    else:
                        cfg.tuningConfig = TuningConfig()
                    Camera.switchCamera()
                    msg = "Camera switched to " + sc.activeCameraInfo
                    logger.debug("serverconfig - active camera set to %s", sc.activeCamera)
            useUsbCameras = not request.form.get("useusbcameras") is None

            reloadCamInfoNeeded = False
            if useUsbCameras != sc.useUsbCameras:
                logger.debug("serverconfig - useUsbCameras changed to %s", useUsbCameras)
                if len(sc.piCameras) == 0 and sc.useUsbCameras == True:
                    if sc.isLiveStream == True \
                    or sc.isLiveStream2 == True \
                    or sc.isVideoRecording == True \
                    or sc.isPhotoSeriesRecording == True \
                    or sc.isTriggerRecording == True \
                    or sc.isEventhandling == True:
                        msg = "Please stop all active camera processes before changing the USB camera configuration"
                if not msg:
                    if len(sc.piCameras) == 0:
                        reloadCamInfoNeeded = True
                    else:
                        if sc.activeCameraIsUsb == True:
                            reloadCamInfoNeeded = True
                        if not sc.secondCamera is None:
                            if sc.secondCameraIsUsb == True:
                                reloadCamInfoNeeded = True
                    sc.useUsbCameras = useUsbCameras
                    cfg.setSupportedCameras()

            useAPI = not request.form.get("useapi") is None
            sc.useAPI = useAPI
            sc.locLatitude = float(request.form["loclatitude"])
            sc.locLongitude = float(request.form["loclongitude"])
            sc.locElevation = float(request.form["locelevation"])
            sc.locTzKey = request.form["loctzkey"]
            sc.unsavedChanges = True
            sc.addChangeLogEntry(f"Settings/General Parameters changed")
            if reloadCamInfoNeeded:
                reloadCameraSystem()
        if msg:
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

def reloadCameraSystem():
    """Reload the camera system in case of hot plug-in/-out
    """
    logger.debug("reloadCameraSystem")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    Camera._instance = None
    cfg.cameras = []
    cfg.sensorModes = []
    cfg.rawFormats = []
    cfg.cameraProperties = CameraProperties()
    sc.noCamera = False
    sc.supportedCameras = []
    sc.usbCamAvailable = False
    sc.piCameras = []
    sc.hasMicrophone = False
    sc.defaultMic = ""
    sc.isMicMuted = False
    sc.recordAudio = False

    cam = Camera()
    cfg.setSupportedCameras()
    cfg.setPiCameras()
    logger.debug("reloadCameraSystem - done")

@bp.route("/reloadCameras", methods=("GET", "POST"))
@login_required
def reloadCameras():
    logger.debug("reloadCameras")
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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        if sc.isVideoRecording:
            Camera().stopVideoRecording()
        if sc.isPhotoSeriesRecording == True:
            tl = PhotoSeriesCfg()
            sr = tl.curSeries
            sr.nextStatus("pause")
            sr.persist()
            Camera().stopPhotoSeries()
            logger.debug("In resetServer - photo series stopped")
        if sc.isTriggerRecording == True:
            MotionDetector().stopMotionDetection()
            sc.isTriggerRecording = False
            logger.debug("In resetServer - Motion detection stopped")
        if sc.isEventhandling:
            TriggerHandler().stop()
            sc.isEventhandling = False
        if sc.isLiveStream == True:
            Camera().stopLiveStream()
            logger.debug("In resetServer - Live stream stopped")
        if sc.isLiveStream2 == True:
            Camera().stopLiveStream2()
            logger.debug("In resetServer - Live stream 2 stopped")
        logger.debug("Stopping camera system")
        time.sleep(3)
        Camera().stopCameraSystem()
        Camera.liveViewDeactivated = False
        Camera.thread = None
        Camera.thread2 = None
        Camera.videoThread = None
        Camera.photoSeriesThread = None
        reloadCameraSystem()

        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Camera system reloaded")
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        if sc.isVideoRecording:
            Camera().stopVideoRecording()
        if sc.isPhotoSeriesRecording == True:
            tl = PhotoSeriesCfg()
            sr = tl.curSeries
            sr.nextStatus("pause")
            sr.persist()
            Camera().stopPhotoSeries()
            logger.debug("In resetServer - photo series stopped")
        if sc.isTriggerRecording == True:
            MotionDetector().stopMotionDetection()
            sc.isTriggerRecording = False
            logger.debug("In resetServer - Motion detection stopped")
        if sc.isEventhandling:
            TriggerHandler().stop()
            sc.isEventhandling = False
        if sc.isLiveStream == True:
            Camera().stopLiveStream()
            logger.debug("In resetServer - Live stream stopped")
        if sc.isLiveStream2 == True:
            Camera().stopLiveStream2()
            logger.debug("In resetServer - Live stream 2 stopped")
        logger.debug("Stopping camera system")
        time.sleep(3)
        Camera().stopCameraSystem()
        Camera.liveViewDeactivated = False
        Camera.thread = None
        Camera.thread2 = None
        Camera.videoThread = None
        Camera.photoSeriesThread = None
        logger.debug("Resetting server configuration")
        setLoadConfigOnStart(cfgPath, False)
        photoRoot = sc.photoRoot
        backupPath = sc.cfgBackupPath
        prgOutputPath = sc.prgOutputPath
        database = sc.database
        actionPath = tc.actionPath
        cfg = CameraCfg()
        cfg.cameras = []
        cfg.sensorModes = []
        cfg.rawFormats = []

        cfg.resetActiveCameraSettings()
        
        cfg._cameraConfigs = []
        cfg.triggerConfig = TriggerConfig()
        cfg.serverConfig = ServerConfig()

        sc = cfg.serverConfig
        tc = cfg.triggerConfig
        sc.photoRoot = photoRoot
        sc.cfgBackupPath = backupPath
        sc.prgOutputPath = prgOutputPath
        sc.database = database
        tc.actionPath = actionPath
        cfg.streamingCfg = {}
        
        sc.isVideoRecording = False
        sc.isAudioRecording = False
        sc.isTriggerRecording = False
        sc.isPhotoSeriesRecording = False
        sc.isLiveStream = False
        sc.isLiveStream2 = False
        sc.checkMicrophone()
        sc.checkEnvironment()
        if sc.supportsExtMotionDetection == False:
            cfg.triggerConfig.motionDetectAlgos = ["Mean Square Diff",]
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
        sc.unsavedChanges = False
        sc.clearChangeLog()
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/configBackup", methods=("GET", "POST"))
@login_required
def configBackup():
    logger.debug("configBackup")
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
    backups = getBackupsList()
    sc.lastSettingsTab = "settingsconfig"

    if request.method == "POST":
        msg = ""
        backupRoot = sc.cfgBackupPath
        logger.debug("configBackup - backupRoot=%s", backupRoot)
        if not os.path.exists(backupRoot):
            os.makedirs(backupRoot, exist_ok=True)
        if request.form["configbackupname"]:
            backupName = request.form["configbackupname"]
            if backupName.strip() == "":
                msg = "Please enter a valid backup name"
        else:
            msg = "Please enter a valid backup name"
        if msg == "":
            backupPath = backupRoot + "/" + backupName
            logger.debug("configBackup - backupPath=%s", backupPath)
            if os.path.exists(backupPath):
                msg = "Backup name already exists. Please choose a different name."
        if msg == "":
            try:
                os.makedirs(backupPath, exist_ok=True)
                
                # Backup calib_data
                stc = cfg.stereoCfg
                src = sc.photoRoot + "/" + stc.calibDataSubPath
                dst = backupPath + "/static/" + stc.calibDataSubPath
                copyDir(src, dst)

                #Backup calib_photos
                src = sc.photoRoot + "/" + stc.calibPhotosSubPath
                dst = backupPath + "/static/" + stc.calibPhotosSubPath
                copyDir(src, dst)

                #Backup config
                src = sc.cfgPath
                dst = backupPath + "/static/" + "config"
                copyDir(src, dst)

                #Backup events
                tc = cfg.triggerConfig
                src = tc.actionPath
                dst = backupPath + "/static/" + "events"
                copyDir(src, dst)

                #Backup photos
                src = sc.photoRoot + "/photos"
                dst = backupPath + "/static/" + "photos"
                copyDir(src, dst)

                #Backup photo series
                ps = PhotoSeriesCfg()
                src = ps.rootPath
                dst = backupPath + "/static/" + "photoseries"
                copyDir(src, dst)
                
                # Backup database
                src = sc.database
                dst = backupPath + "/instance/" + "database"
                copyDir(src, dst)

            except Exception as e:
                msg = f"Error creating configuration backup: {e}"

        if msg == "":
            msg = "Configuration backup created under " +  backupPath
        flash(msg)
        los = getLoadConfigOnStart(cfgPath)
        backups = getBackupsList()
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

def copyDir(src: str, dst: str):
    """Recursively copy a directory from src to dst.

    Args:
        src (str): Source directory path.
        dst (str): Destination directory path.
    """
    logger.debug("copyDir - src: %s, dst: %s", src, dst)
    if not os.path.exists(src):
        logger.debug("copyDir - Source not found: %s", src)
        return

    if not os.path.exists(dst):
        os.makedirs(dst, exist_ok=True)
        logger.debug("copyDir - Destination directory created: %s", dst)

    if os.path.isdir(src) == True:
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                copyDir(s, d)
            else:
                shutil.copy2(s, d)
    if os.path.isfile(src) == True:
        shutil.copy2(src, dst)

def restoreDir(src: str, dst: str):
    """Recursively restore a directory from src to dst.

    Args:
        src (str): Source directory path.
        dst (str): Destination directory path.
    """
    logger.debug("restoreDir - src: %s, dst: %s", src, dst)
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        copyDir(src, dst)
    else:
        if os.path.exists(dst):
            shutil.rmtree(dst)

def getBackupsList() -> list:
    """Get the list of available backups.

    Returns:
        list: List of backup names.
    """
    logger.debug("getBackupsList")
    res = []
    cfg = CameraCfg()
    sc = cfg.serverConfig
    backupRoot = sc.cfgBackupPath
    if os.path.exists(backupRoot):
        for entry in os.listdir(backupRoot):
            backupPath = backupRoot + "/" + entry
            if os.path.isdir(backupPath):
                res.append(entry)
    logger.debug("getBackupsList - found %s backups", len(res))
    return res

@bp.route("/configRestore", methods=("GET", "POST"))
@login_required
def configRestore():
    logger.debug("configRestore")
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
    backups = getBackupsList()
    sc.lastSettingsTab = "settingsconfig"

    if request.method == "POST":
        msg = ""
        if request.form["configrestorename"]:
            backupName = request.form["configrestorename"]
            if backupName.strip() == "":
                msg = "Please select a valid backup name"
        else:
            msg = "Please select a valid backup name"

        if msg == "":
            backupRoot = sc.cfgBackupPath
            backupPath = backupRoot + "/" + backupName
            logger.debug("configBackup - backupPath=%s", backupPath)
            try:
                os.makedirs(backupPath, exist_ok=True)
                
                # Restore calib_data
                stc = cfg.stereoCfg
                dst = sc.photoRoot + "/" + stc.calibDataSubPath
                src = backupPath + "/static/" + stc.calibDataSubPath
                restoreDir(src, dst)

                #Restore calib_photos
                dst = sc.photoRoot + "/" + stc.calibPhotosSubPath
                src = backupPath + "/static/" + stc.calibPhotosSubPath
                restoreDir(src, dst)

                #Restore config
                dst = sc.cfgPath
                src = backupPath + "/static/" + "config"
                restoreDir(src, dst)

                #Restore events
                tc = cfg.triggerConfig
                dst = tc.actionPath
                src = backupPath + "/static/" + "events"
                restoreDir(src, dst)

                #Restore photos
                dst = sc.photoRoot + "/photos"
                src = backupPath + "/static/" + "photos"
                restoreDir(src, dst)

                #Restore photo series
                ps = PhotoSeriesCfg()
                dst = ps.rootPath
                src = backupPath + "/static/" + "photoseries"
                restoreDir(src, dst)
                
                # Restore database
                dst = sc.database
                src = backupPath + "/instance/" + "database" + "/raspiCamSrv.sqlite"
                shutil.copy2(src, dst)

            except Exception as e:
                msg = f"Error restoring backup {backupName}: {e}"

        if msg == "":
            msg = "Backup restored from " +  backupPath
        flash(msg)
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/configRemove", methods=("GET", "POST"))
@login_required
def configRemove():
    logger.debug("configRemove")
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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        msg = ""
        if request.form["configremovename"]:
            backupName = request.form["configremovename"]
            if backupName.strip() == "":
                msg = "Please select a valid backup name"
        else:
            msg = "Please select a valid backup name"
        if msg == "":
            backupRoot = sc.cfgBackupPath
            backupPath = backupRoot + "/" + backupName
            try:
                shutil.rmtree(backupPath)
            except Exception as e:
                msg = f"Error removing backup {backupName}: {e}"

        if msg == "":
            msg = f"Backup {backupName} was removed."
        flash(msg)
        los = getLoadConfigOnStart(cfgPath)
        backups = getBackupsList()
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/serverRestart", methods=("GET", "POST"))
@login_required
def serverRestart():
    logger.debug("serverRestart")
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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        msg = ""
        startup_source = detect_startup_source()
        logger.debug("Startup source detected: %s", startup_source)

        try:
            if startup_source == 1:
                result = subprocess.run(
                    ["sudo", "systemctl", "restart", "raspiCamSrv.service"],
                    capture_output=True, text=True
                )
            elif startup_source == 2:
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "raspiCamSrv.service"],
                    capture_output=True, text=True
                )
            elif startup_source == 3:
                msg = "Please restart the server from the command line."
            
            else:
                msg = "Unable to detect the server startup source. Please restart the server manually."

        except CalledProcessError as e:
            logger.error("serverRestart - CalledProcessError: %s", e)
            msg = "Error restarting server: " + str(e)
        except Exception as e:
            logger.error("serverRestart - Exception: %s", e)
            msg = "Error restarting server: " + str(e)

        if msg == "":
            msg = "Configuration backup created under " +  backupPath
        flash(msg)
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

def detect_startup_source():
    """Detect the source from which the application was started.

    Returns:
        int: Type of the startup source.
             1: systemd system unit
             2: systemd user unit
             3: command line
             0: unknown
    """
    logger.debug("detect_startup_source")
    ret = 0

    # Check parent
    parent = psutil.Process(os.getpid()).parent().name()

    # Check cgroup
    cgroup = Path("/proc/self/cgroup").read_text()

    # systemd user or system unit
    if "system.slice" in cgroup:
        ret = 1
    if "user.slice" in cgroup and ".service" in cgroup:
        ret = 2

    # Command line terminal
    if parent in ("bash", "zsh", "fish") or "session-" in cgroup:
        ret = 3

    logger.debug("detect_startup_source - ret=%s", ret)
    return ret

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
    backups = getBackupsList()

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
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    if request.method == "POST":
        return render_template("auth/register.html", sc=sc, cp=cp)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        cfgPath = current_app.static_folder + "/config"
        # Initialize the Photo viewer list
        sc = cfg.serverConfig
        sc.pvList = []
        sc.updateStreamingClients()
        cfg.persist(cfgPath)
        msg = "Configuration stored under " + cfgPath
        sc.unsavedChanges = False
        sc.clearChangeLog()
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        msg = ""
        # Stop background threads
        if sc.isVideoRecording:
            msg = "Please stop video recording before loading the configuration"
        if msg == "":
            if sc.isPhotoSeriesRecording == True:
                tl = PhotoSeriesCfg()
                sr = tl.curSeries
                #sr.nextStatus("pause")
                #sr.persist()
                Camera().stopPhotoSeries()
                logger.debug("In load_config - photo series stopped")
                restartPhotoSeries = True
            else:
                restartPhotoSeries = False
            if sc.isTriggerRecording == True:
                MotionDetector().stopMotionDetection()
                sc.isTriggerRecording = False
                logger.debug("In load_config - Motion detection stopped")
                restartTriggerRecording = True
            else:
                restartTriggerRecording = False
            if sc.isEventhandling:
                TriggerHandler().stop()
                sc.isEventhandling = False
                logger.debug("In load_config - Eventhandling stopped")
                restartEventhandling = True
            else:
                restartEventhandling = False
            if sc.isLiveStream == True:
                Camera().stopLiveStream()
                logger.debug("In load_config - Live stream stopped")
                restartLiveStream = True
            else:
                restartLiveStream = False
            if sc.isLiveStream2 == True:
                Camera().stopLiveStream2()
                logger.debug("In load_config - Live stream 2 stopped")
                restartLiveStream2 = True
            else:
                restartLiveStream2 = False
                
            # Load stored configuration
            cfg.loadConfig(cfgPath)
            msg = "Configuration loaded from " + cfgPath
            cam = Camera()
            cfg = CameraCfg()
            cs = cfg.cameras
            sc = cfg.serverConfig
            sc.checkMicrophone()
            cp = cfg.cameraProperties
            sc.curMenu = "settings"
            cfgPath = current_app.static_folder + "/config"
            los = getLoadConfigOnStart(cfgPath)

            # Restart threads
            if restartLiveStream == True:
                Camera().restartLiveStream()
                sc.isLiveStream = True
                logger.debug("In load_config - Live stream started")
            if restartLiveStream2 == True:
                Camera().restartLiveStream2()
                sc.isLiveStream2 = True
                logger.debug("In load_config - Live stream 2 started")
            if restartPhotoSeries == True:
                Camera().startPhotoSeries(sr)
                sc.isPhotoSeriesRecording = True
                logger.debug("In load_config - photo series started")
            if restartTriggerRecording == True:
                MotionDetector().startMotionDetection()
                sc.isTriggerRecording = True
                logger.debug("In load_config - Motion detection started")
            if restartEventhandling == True:
                TriggerHandler().start()
                sc.isEventhandling = True
                logger.debug("In load_config - Eventhandling started")
            sc.unsavedChanges = False
            sc.clearChangeLog()
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsconfig"
    if request.method == "POST":
        cb = not request.form.get("loadconfigonstartcb") is None
        setLoadConfigOnStart(cfgPath, cb)
        los = getLoadConfigOnStart(cfgPath)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/API Settings changed")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
    backups = getBackupsList()

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
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Versatile Buttons changed")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Versatile Buttons changed")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Action Buttons changed")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Action Buttons changed")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
                    if "calibration" in dt:
                        device.needsCalibration = True
            sc.gpioDevices.append(device)
            sc.curDeviceId = deviceId
            sc.curDevice = device
        
        if msg != "":
            flash(msg)
        if not deviceId is None:
            sc.unsavedChanges = True
            sc.addChangeLogEntry(f"Settings/Devices - new device added: {deviceId}")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = checkDeviceDeletion(sc.curDeviceId, tc)
        deviceDel = None
        if msg == "":
            deviceDel = sc.curDeviceId
            idxDel = -1
            idx = 0
            for device in sc.gpioDevices:
                if device.id == sc.curDeviceId:
                    idxDel = idx
                    break
                idx += 1
            if idxDel >= 0:
                dev = sc.curDevice
                if dev.needsCalibration == True:
                    if dev._deviceStateFile != "":
                        if os.path.exists(dev._deviceStateFile):
                            os.remove(dev._deviceStateFile)
                del sc.gpioDevices[idxDel]

            if len(sc.gpioDevices) > 0:
                sc.curDevice = sc.gpioDevices[0]
                sc.curDeviceId = sc.curDevice.id
                for deviceType in sc.deviceTypes:
                    if deviceType["type"] == sc.curDevice.type:
                        sc.curDeviceType = deviceType
            if not deviceDel is None:
                sc.unsavedChanges = True
                sc.addChangeLogEntry(f"Settings/Devices - device deleted: {deviceDel}")
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
        if not sc.curDeviceId is None:
            sc.unsavedChanges = True
            sc.addChangeLogEntry(f"Settings/Devices - device properties changed for {sc.curDeviceId}")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

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
    backups = getBackupsList()

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
                dev.setState(devObj)
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
                            dev.trackState(devObj)
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
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route('/calibrate_device', methods=("GET", "POST"))
@login_required
def calibrate_device():
    logger.debug("In calibrate_device")
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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"
    if request.method == "POST":
        msg = ""
        dev = sc.curDevice
        if dev.needsCalibration == True:
            dev.isCalibrating = True
            devClass = f"{dev.type}"
            devArgs = dev.params
            try:
                logger.debug("settings.calibrate_device -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
                dev.setState(devObj)
                if hasattr(devObj, "value"):
                    result["value"] = getattr(devObj, "value")
                dev.isCalibrating = True
                sc.unsavedChanges = True
                sc.addChangeLogEntry(f"Settings/Devices - device calibration started: {sc.curDeviceId}")
            except Exception as e:
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
        else:
            msg = f"Device {dev.id} does not need calibration."
        if msg != "":
            flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route('/calibrate_fbwd', methods=("GET", "POST"))
@login_required
def calibrate_fbwd():
    logger.debug("In calibrate_fbwd reqest.method=%s", request.method)
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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"

    msg = ""
    dev = sc.curDevice
    dev.isCalibrating = True        
    devType = sc.curDeviceType
    if "calibration" in devType:
        logger.debug("settings.calibrate_fbwd - calibrating")
        calibration = devType["calibration"]
        method = ""
        params = ""
        if "fbwd" in calibration:
            adjust = calibration["fbwd"]
            logger.debug("settings.calibrate_fbwd - calibrating method=%s", adjust)
            if "method" in adjust:
                method = adjust["method"]
            if "params" in adjust:
                params = adjust["params"]
        if method != "":
            devClass = f"{dev.type}"
            devArgs = dev.params
            try:
                logger.debug("settings.calibrate_fbwd -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
            except Exception as e:
                logger.debug("settings.calibrate_fbwd - Error while instantiating %s:%s, %s", devClass, type(e), e)
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
            if msg == "":
                dev.setState(devObj)
                if hasattr(devObj, method):
                    try:
                        attr = getattr(devObj, method)
                        if callable(attr) == True:
                            logger.debug("settings.calibrate_fbwd - calling %s.%s(**%s)", devClass, method, params)
                            res = attr(**params)
                        else:
                            msg = f"{devClass}.{method} is not callable."
                    except Exception as e:
                        msg = f"Error calling {devClass}.{method}: {type(e)} : {e}"
                dev.trackState(devObj)
                if hasattr(devObj, "value"):
                    try:
                        result["value"] = getattr(devObj, "value")
                    except Exception as e:
                        msg = f"Property Error {devClass}.value: {type(e)} : {e}"
    if msg != "":
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route('/calibrate_bwd', methods=("GET", "POST"))
@login_required
def calibrate_bwd():
    logger.debug("In calibrate_bwd reqest.method=%s", request.method)
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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"

    msg = ""
    dev = sc.curDevice
    dev.isCalibrating = True        
    devType = sc.curDeviceType
    if "calibration" in devType:
        logger.debug("settings.calibrate_bwd - calibrating")
        calibration = devType["calibration"]
        method = ""
        params = ""
        if "bwd" in calibration:
            adjust = calibration["bwd"]
            logger.debug("settings.calibrate_bwd - calibrating method=%s", adjust)
            if "method" in adjust:
                method = adjust["method"]
            if "params" in adjust:
                params = adjust["params"]
        if method != "":
            devClass = f"{dev.type}"
            devArgs = dev.params
            try:
                logger.debug("settings.calibrate_bwd -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
            except Exception as e:
                logger.debug("settings.calibrate_bwd - Error while instantiating %s:%s, %s", devClass, type(e), e)
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
            if msg == "":
                dev.setState(devObj)
                if hasattr(devObj, method):
                    try:
                        attr = getattr(devObj, method)
                        if callable(attr) == True:
                            logger.debug("settings.calibrate_bwd - calling %s.%s(**%s)", devClass, method, params)
                            res = attr(**params)
                        else:
                            msg = f"{devClass}.{method} is not callable."
                    except Exception as e:
                        msg = f"Error calling {devClass}.{method}: {type(e)} : {e}"
                dev.trackState(devObj)
                if hasattr(devObj, "value"):
                    try:
                        result["value"] = getattr(devObj, "value")
                    except Exception as e:
                        msg = f"Property Error {devClass}.value: {type(e)} : {e}"
    if msg != "":
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route('/docalibrate', methods=("GET", "POST"))
@login_required
def docalibrate():
    logger.debug("In docalibrate")
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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"

    msg = ""
    dev = sc.curDevice
    dev.isCalibrating = True        
    devType = sc.curDeviceType
    if "calibration" in devType:
        logger.debug("settings.docalibrate - calibrating")
        calibration = devType["calibration"]
        method = ""
        params = ""
        if "calibrate" in calibration:
            adjust = calibration["calibrate"]
            logger.debug("settings.docalibrate - calibrating method=%s", adjust)
            if "method" in adjust:
                method = adjust["method"]
            if "params" in adjust:
                params = adjust["params"]
        if method != "":
            devClass = f"{dev.type}"
            devArgs = dev.params
            try:
                logger.debug("settings.docalibrate -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
            except Exception as e:
                logger.debug("settings.docalibrate - Error while instantiating %s:%s, %s", devClass, type(e), e)
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
            if msg == "":
                dev.setState(devObj)
                if hasattr(devObj, method):
                    try:
                        attr = getattr(devObj, method)
                        if callable(attr) == True:
                            logger.debug("settings.docalibrate - calling %s.%s(**%s)", devClass, method, params)
                            res = attr(**params)
                        else:
                            if "value" in params:
                                value = params["value"]
                                logger.debug("settings.docalibrate - calling %s.%s", devClass, method)
                                setattr(devObj,"value", value)
                            else:
                                msg = f"'value' not not in {params}."
                    except Exception as e:
                        msg = f"Error calling {devClass}.{method}: {type(e)} : {e}"
                dev.trackState(devObj)
                if hasattr(devObj, "value"):
                    try:
                        result["value"] = getattr(devObj, "value")
                    except Exception as e:
                        msg = f"Property Error {devClass}.value: {type(e)} : {e}"
                dev.isCalibrating = False
                sc.unsavedChanges = True
                sc.addChangeLogEntry(f"Settings/Devices - device calibrated: {sc.curDeviceId}")
                
    if msg != "":
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route('/calibrate_fwd', methods=("GET", "POST"))
@login_required
def calibrate_fwd():
    logger.debug("In calibrate_fwd reqest.method=%s", request.method)
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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"

    msg = ""
    dev = sc.curDevice
    dev.isCalibrating = True        
    devType = sc.curDeviceType
    if "calibration" in devType:
        logger.debug("settings.calibrate_fwd - calibrating")
        calibration = devType["calibration"]
        method = ""
        params = ""
        if "fwd" in calibration:
            adjust = calibration["fwd"]
            logger.debug("settings.calibrate_fwd - calibrating method=%s", adjust)
            if "method" in adjust:
                method = adjust["method"]
            if "params" in adjust:
                params = adjust["params"]
        if method != "":
            devClass = f"{dev.type}"
            devArgs = dev.params
            try:
                logger.debug("settings.calibrate_fwd -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
            except Exception as e:
                logger.debug("settings.calibrate_fwd - Error while instantiating %s:%s, %s", devClass, type(e), e)
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
            if msg == "":
                dev.setState(devObj)
                if hasattr(devObj, method):
                    try:
                        attr = getattr(devObj, method)
                        if callable(attr) == True:
                            logger.debug("settings.calibrate_fwd - calling %s.%s(**%s)", devClass, method, params)
                            res = attr(**params)
                        else:
                            msg = f"{devClass}.{method} is not callable."
                    except Exception as e:
                        msg = f"Error calling {devClass}.{method}: {type(e)} : {e}"
                dev.trackState(devObj)
                if hasattr(devObj, "value"):
                    try:
                        result["value"] = getattr(devObj, "value")
                    except Exception as e:
                        msg = f"Property Error {devClass}.value: {type(e)} : {e}"
    if msg != "":
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route('/calibrate_ffwd', methods=("GET", "POST"))
@login_required
def calibrate_ffwd():
    logger.debug("In calibrate_ffwd reqest.method=%s", request.method)
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
    backups = getBackupsList()

    # Check connection and access of microphone
    sc.checkMicrophone()
    cp = cfg.cameraProperties
    sc.curMenu = "settings"
    sc.lastSettingsTab = "settingsdevices"

    msg = ""
    dev = sc.curDevice
    dev.isCalibrating = True        
    devType = sc.curDeviceType
    if "calibration" in devType:
        logger.debug("settings.calibrate_ffwd - calibrating")
        calibration = devType["calibration"]
        method = ""
        params = ""
        if "ffwd" in calibration:
            adjust = calibration["ffwd"]
            logger.debug("settings.calibrate_ffwd - calibrating method=%s", adjust)
            if "method" in adjust:
                method = adjust["method"]
            if "params" in adjust:
                params = adjust["params"]
        if method != "":
            devClass = f"{dev.type}"
            devArgs = dev.params
            try:
                logger.debug("settings.calibrate_ffwd -instantiating %s(**%s)", devClass, devArgs)
                devObj = globals()[devClass](**devArgs)
            except Exception as e:
                logger.debug("settings.calibrate_ffwd - Error while instantiating %s:%s, %s", devClass, type(e), e)
                msg = f"Error while instantiating class {devClass}: {type(e)} {e}"
            if msg == "":
                dev.setState(devObj)
                if hasattr(devObj, method):
                    try:
                        attr = getattr(devObj, method)
                        if callable(attr) == True:
                            logger.debug("settings.calibrate_ffwd - calling %s.%s(**%s)", devClass, method, params)
                            res = attr(**params)
                        else:
                            msg = f"{devClass}.{method} is not callable."
                    except Exception as e:
                        msg = f"Error calling {devClass}.{method}: {type(e)} : {e}"
                dev.trackState(devObj)
                if hasattr(devObj, "value"):
                    try:
                        result["value"] = getattr(devObj, "value")
                    except Exception as e:
                        msg = f"Property Error {devClass}.value: {type(e)} : {e}"
    if msg != "":
        flash(msg)
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/versionCheckEnabled", methods=("GET", "POST"))
@login_required
def versionCheckEnabled():
    logger.debug("versionCheckEnabled")
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
    backups = getBackupsList()

    sc.lastSettingsTab = "settingsupdate"
    if request.method == "POST":
        msg = ""
        versionCheckEnabled = not request.form.get("versioncheckenabledcb") is None
        if sc.versionCheckEnabled != versionCheckEnabled:
            sc.versionCheckEnabled = versionCheckEnabled
            sc.unsavedChanges = True
            sc.addChangeLogEntry(f"Settings/Update: Check for Updates changed to {sc.versionCheckEnabled}")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/serverUpdate", methods=("GET", "POST"))
@login_required
def serverUpdate():
    logger.debug("serverUpdate")
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
    backups = getBackupsList()
    sc.lastSettingsTab = "settingsupdate"
    if request.method == "POST":
        msg = ""
        if sc.versionCurrent == sc.versionLatest:
            msg = "You are already using the latest version."
        else:
            try:
                result = subprocess.run(
                    ["git", "fetch", "origin", "main", "--depth=1"],
                    capture_output=True, text=True
                )
                result = subprocess.run(
                    ["git", "reset", "--hard", "origin/main"],
                    capture_output=True, text=True
                )
                sc.updateDone = True
                msg = "raspiCamSrv updated successfully. Please restart the server to apply the update."
            except CalledProcessError as e:
                logger.error("serverUpdate - CalledProcessError: %s", e)
                msg = "Error updating server: " + str(e)
            except Exception as e:
                logger.error("serverUpdate - Exception: %s", e)
                msg = "Error updating server: " + str(e)
        if msg != "":
            flash(msg)

    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/updateIgnoreLatest", methods=("GET", "POST"))
@login_required
def updateIgnoreLatest():
    logger.debug("updateIgnoreLatest")
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
    backups = getBackupsList()
    sc.lastSettingsTab = "settingsupdate"
    if request.method == "POST":
        msg = ""
        sc.versionCheckFrom = sc.versionLatest
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Update: Ignored latest version {sc.versionLatest}")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/versionCheckIntervalHours", methods=("GET", "POST"))
@login_required
def versionCheckIntervalHours():
    logger.debug("versionCheckIntervalHours")
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
    backups = getBackupsList()
    sc.lastSettingsTab = "settingsupdate"
    if request.method == "POST":
        msg = ""
        intvl = int(request.form["versioncheckintervalhours"])
        sc.versionCheckIntervalHours = intvl
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Update: Version Check Interval changed to {sc.versionCheckIntervalHours} hours")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)

@bp.route("/versionCheckNow", methods=("GET", "POST"))
@login_required
def versionCheckNow():
    logger.debug("versionCheckNow")
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
    backups = getBackupsList()
    sc.lastSettingsTab = "settingsupdate"
    if request.method == "POST":
        msg = ""
        sc.getLatestVersion(now=True)
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Settings/Update: Version Check Interval changed to {sc.versionCheckIntervalHours} hours")
    return render_template("settings/main.html", sc=sc, tc=tc, cp=cp, cs=cs, los=los, result=result, backups=backups)
