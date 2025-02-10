from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from werkzeug.exceptions import abort
from raspiCamSrv.db import get_db

from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, TuningConfig
from _thread import get_ident
import datetime
import time
from raspiCamSrv.motionDetector import MotionDetector
from raspiCamSrv.version import version

from raspiCamSrv.auth import login_required
import logging

# Try to import flask_jwt_extended to avoid errors when upgrading to V2.11 from earlier versions
try:
    from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
except ImportError:
    pass


bp = Blueprint("api", __name__)

logger = logging.getLogger(__name__)

@bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    db = get_db()
    error = None
    user = db.execute(
        "SELECT * FROM user WHERE username = ?", (username,)
    ).fetchone()

    if user is None:
        error = "Invalid username or password"
    elif not check_password_hash(user["password"], password):
        error = "Invalid username or password"

    if error is None:
        if len(user) == 5:
            if user["isinitial"] == 1:
                error = "Password change required. Please log in through UI!"

    if error is None:
        cfg = CameraCfg()
        sc = cfg.serverConfig

        access_token = create_access_token(identity=username)
        if sc.jwtAccessTokenExpirationMin == 0:
            return jsonify(access_token=access_token)
        else:
            refresh_token = create_refresh_token(identity=username)
            return jsonify(access_token=access_token, refresh_token=refresh_token)
    return jsonify({"error": error}), 401

@bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True) 
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token)

@bp.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(message=f"Hello, {current_user}! You accessed a protected route.")
            
@bp.route("/api/take_photo", methods=["GET"])
@jwt_required()
def take_photo():
    logger.debug("Thread %s: In /api/take_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    timeImg = datetime.datetime.now()
    filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
    logger.debug("Saving image %s", filename)
    fp = Camera().takeImage(filename)
    if not sc.error:
        logger.debug("take_photo - success")
        msg=f"Photo taken: {fp}"
        return jsonify(message=msg)
    else:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        return jsonify(message=msg), 500

@bp.route("/api/take_raw_photo", methods=["GET"])
@jwt_required()
def take_raw_photo():
    logger.debug("Thread %s: In /api/take_raw_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    timeImg = datetime.datetime.now()
    filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
    filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
    logger.debug("Saving raw image %s", filenameRaw)
    fp = Camera().takeRawImage(filenameRaw, filename)
    if not sc.error:
        logger.debug("take_photo - success")
        msg=f"Raw photo taken: {fp}"
        return jsonify(message=msg)
    else:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        return jsonify(message=msg), 500

@bp.route("/api/start_triggered_capture", methods=["GET"])
@jwt_required()
def start_triggered_capture():
    logger.debug("In /api/start_triggered_capture")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    if tc.triggeredByMotion:
        MotionDetector().setAlgorithm()
        MotionDetector().startMotionDetection()
        if sc.error:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            return jsonify(message=msg), 500
        elif tc.error:
            msg = "Error in " + tc.errorSource + ": " + tc.error
            return jsonify(message=msg), 500
        else:
            sc.isTriggerRecording = True
            msg = "Motion detection started"
            return jsonify(message=msg)
    else:
        msg = "There is no trigger activated"
        return jsonify(message=msg), 500

@bp.route("/api/stop_triggered_capture", methods=["GET"])
@jwt_required()
def stop_triggered_capture():
    logger.debug("In /api/stop_triggered_capture")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    if tc.triggeredByMotion:
        MotionDetector().stopMotionDetection()
        sc.isTriggerRecording = False
        msg = "Motion detection stopped"
        return jsonify(message=msg)
    else:
        msg = "There is no trigger activated"
        return jsonify(message=msg), 500

@bp.route("/api/info", methods=["GET"])
@jwt_required()
def info():
    logger.debug("In /api/info")
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tc = cfg.triggerConfig
    
    info = {}
    info["version"] = "raspiCamSrv " + version
    info["server"] = request.host
    info["active_camera"] = sc.activeCameraInfo
    infoCams = []
    cams = cfg.cameras
    logger.debug("/api/info - cams: %s", cams)
    for cam in cams:
        infoCam = {}
        infoCam["num"] = cam.num
        infoCam["model"] = cam.model
        infoCam["is_usb"] = cam.isUsb
        if cam.num == sc.activeCamera:
            infoCam["active"] = True
        else:
            infoCam["active"] = False
        infoCam["status"] = Camera.cameraStatus(cam.num)
        infoCams.append(infoCam)
    info["cameras"] = infoCams
    infoStatus = {}
    infoStatus["livestream_active"] = sc.isLiveStream
    infoStatus["livestream2_active"] = sc.isLiveStream2
    infoStatus["photoseries_recording"] = sc.isPhotoSeriesRecording
    infoStatus["motion_capturing"] = sc.isTriggerRecording == True and tc.triggeredByMotion == True
    infoStatus["video_recording"] = sc.isVideoRecording
    infoStatus["audio_recording"] = sc.isAudioRecording
    info["operation_status"] = infoStatus
    
    return jsonify(message=info)

@bp.route("/api/switch_cameras", methods=["GET"])
@jwt_required()
def switch_cameras():
    logger.debug("In /api/switch_cameras")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
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
            msg = "Cameras cannot be switched because triggered capturing is active"
        if sc.isVideoRecording == True:
            msg = "Cameras cannot be switched because trigvideorecording is active"
        if sc.isPhotoSeriesRecording:
            msg = "Cameras cannot be switched because photo series recording is active"
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
            logger.debug("/api/switch_cameras - active camera set to %s", sc.activeCamera)
    else:
        msg = "No other camera available"
    if msg:
        return jsonify(message=msg), 500
    else:
        msg = "Camera switch successful"
        return jsonify(message=msg)

@bp.route("/api/record_video", methods=["GET"])
@jwt_required()
def record_video():
    logger.debug("Thread %s: In /api/record_video", get_ident())
    data = request.get_json()
    duration = 0
    if "duration" in data:
        duration = data.get("duration")
    logger.debug("Thread %s: /api/record_video - requested duration: %s", get_ident(), duration)

    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    timeImg = datetime.datetime.now()
    filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
    filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
    logger.debug("Recording a video %s", filenameVid)
    fp = Camera().recordVideo(filenameVid, filename, duration)
    time.sleep(4)
    if not sc.error:
        # Check whether video is being recorded
        if Camera.isVideoRecording():
            logger.debug("Video recording started")
            sc.isVideoRecording = True
            if sc.recordAudio:
                sc.isAudioRecording = True
            msg="Video recorded to " + fp
            return jsonify(message=msg)
        else:
            logger.debug("Video recording did not start")
            sc.isVideoRecording = False
            sc.isAudioRecording = False
            msg="Video recording failed. Requested resolution too high"
            return jsonify(message=msg), 500
    else:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        return jsonify(message=msg), 500
