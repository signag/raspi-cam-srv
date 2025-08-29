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
from raspiCamSrv.triggerHandler import TriggerHandler
from raspiCamSrv.version import version
from raspiCamSrv.home import generateHistogram

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
        if sc.displayContent == "hist":
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
        msg=f"Photo taken: {fp}"
        return jsonify(message=msg)
    else:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        return jsonify(message=msg), 500

@bp.route("/api/take_photo2", methods=["GET"])
@jwt_required()
def take_photo2():
    logger.debug("Thread %s: In /api/take_photo2", get_ident())
    if Camera().isCamera2Available():
        cfg = CameraCfg()
        sc = cfg.serverConfig
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Saving image %s", filename)
        fp = Camera().takeImage2(filename)
        if not sc.errorc2:
            logger.debug("take_photo2 - success")
            msg=f"Photo taken: {fp}"
            return jsonify(message=msg)
        else:
            msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("take_photo2 - %s", msg)
        return jsonify(message=msg), 500

@bp.route("/api/take_photo_both", methods=["GET"])
@jwt_required()
def take_photo_both():
    logger.debug("Thread %s: In /api/take_photo_both", get_ident())
    if Camera().isCamera2Available():
        cfg = CameraCfg()
        sc = cfg.serverConfig
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Saving image2 %s", filename)
        fp1 = Camera().takeImage(filename)
        fp2 = Camera().takeImage2(filename)
        msg = {}
        err = False
        if not sc.error:
            logger.debug("takeImage - success")
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg["Photo1"] = fp1
        else:
            msg["Photo1"] = "Error in " + sc.errorcSource + ": " + sc.errorc
            err = True
        if not sc.errorc2:
            logger.debug("takeImage2 - success")
            msg["Photo2"] = fp2
        else:
            msg["Photo2"] = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            err = True
        if not err:
            return jsonify(message=msg)
        else:
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("take_photo_both - %s", msg)
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
        logger.debug("take_raw_photo - success")
        if sc.displayContent == "hist":
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
        msg = f"Raw photo taken: {fp}"
        return jsonify(message=msg)
    else:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        return jsonify(message=msg), 500

@bp.route("/api/take_raw_photo2", methods=["GET"])
@jwt_required()
def take_raw_photo2():
    logger.debug("Thread %s: In /api/take_raw_photo2", get_ident())
    if Camera().isCamera2Available():
        cfg = CameraCfg()
        sc = cfg.serverConfig
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        logger.debug("Saving raw image %s", filenameRaw)
        fp = Camera().takeRawImage2(filenameRaw, filename)
        if not sc.error:
            logger.debug("take_raw_photo2 - success")
            msg=f"Raw photo taken: {fp}"
            return jsonify(message=msg)
        else:
            msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("take_raw_photo2 - %s", msg)
        return jsonify(message=msg), 500

@bp.route("/api/take_raw_photo_both", methods=["GET"])
@jwt_required()
def take_raw_photo_both():
    logger.debug("Thread %s: In /api/take_raw_photo_both", get_ident())
    if Camera().isCamera2Available():
        cfg = CameraCfg()
        sc = cfg.serverConfig
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        logger.debug("Saving raw images %s", filenameRaw)
        fp1 = Camera().takeRawImage(filenameRaw, filename)
        fp2 = Camera().takeRawImage2(filenameRaw, filename)
        msg = {}
        err = False
        if not sc.error:
            logger.debug("takeRawImage - success")
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg["Photo1"] = fp1
        else:
            msg["Photo1"] = "Error in " + sc.errorcSource + ": " + sc.errorc
            err = True
        if not sc.errorc2:
            logger.debug("takeRawImage2 - success")
            msg["Photo2"] = fp2
        else:
            msg["Photo2"] = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            err = True
        if not err:
            return jsonify(message=msg)
        else:
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("take_raw_photo_both - %s", msg)
        return jsonify(message=msg), 500

@bp.route("/api/start_triggered_capture", methods=["GET"])
@jwt_required()
def start_triggered_capture():
    logger.debug("In /api/start_triggered_capture")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    if tc.triggeredByMotion \
    or tc.triggeredByEvents:
        if tc.triggeredByMotion:
            MotionDetector().setAlgorithm()
            MotionDetector().startMotionDetection()
        if tc.triggeredByEvents:
            TriggerHandler().start()
        if sc.error:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            return jsonify(message=msg), 500
        elif tc.error:
            msg = "Error in " + tc.errorSource + ": " + tc.error
            return jsonify(message=msg), 500
        else:
            if tc.triggeredByMotion:
                sc.isTriggerRecording = True
                msg = "Motion detection started"
            if tc.triggeredByEvents:
                sc.isEventhandling = True
                msg = "Event handling started"
            if tc.triggeredByMotion \
            and tc.triggeredByEvents:
                msg = "Motion detection and event handlinfg started"
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
    if tc.triggeredByMotion \
    or tc.triggeredByEvents:
        if sc.isTriggerRecording:
            MotionDetector().stopMotionDetection()
            sc.isTriggerRecording = False
            msg = "Motion detection stopped"
        if sc.isEventhandling:
            TriggerHandler().stop()
            sc.isEventhandling = False
            msg = "Event handling stopped"
        if sc.isTriggerRecording \
        and sc.isEventhandling:
            msg = "Motion detection and event handling stopped"
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
    if len(cams) > 1:
        infoStatus["livestream2_active"] = sc.isLiveStream2
    infoStatus["photoseries_recording"] = sc.isPhotoSeriesRecording
    infoStatus["motion_capturing"] = sc.isTriggerRecording == True and tc.triggeredByMotion == True
    infoStatus["event_handling"] = sc.isEventhandling == True and sc.isEventsWaiting == False
    infoStatus["video_recording"] = sc.isVideoRecording
    infoStatus["audio_recording"] = sc.isAudioRecording
    if len(cams) > 1:
        infoStatus["video_recording2"] = sc.isVideoRecording2
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
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
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

@bp.route("/api/stop_video", methods=["GET"])
@jwt_required()
def stop_video():
    logger.debug("Thread %s: In /api/stop_video", get_ident())

    cfg = CameraCfg()
    sc = cfg.serverConfig
    if sc.isVideoRecording == True:
        fp = Camera().videoOutput
        Camera().stopVideoRecording()
        time.sleep(1)
        msg = {"Video": fp, "Status": "Stopped"}
        sc.isVideoRecording = False
        return jsonify(message=msg)
    else:
        msg = "No video recording in progress"
        return jsonify(message=msg), 500

@bp.route("/api/record_video2", methods=["GET"])
@jwt_required()
def record_video2():
    logger.debug("Thread %s: In /api/record_video2", get_ident())
    if Camera().isCamera2Available():
        data = request.get_json()
        duration = 0
        if "duration" in data:
            duration = data.get("duration")
        logger.debug("Thread %s: /api/record_video2 - requested duration: %s", get_ident(), duration)

        cfg = CameraCfg()
        cc = cfg.controls
        sc = cfg.serverConfig
        cp = cfg.cameraProperties
        timeImg = datetime.datetime.now()
        filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Recording a video %s", filenameVid)
        fp = Camera().recordVideo2(filenameVid, filename, duration)
        time.sleep(4)
        if not sc.errorc2:
            # Check whether video is being recorded
            if Camera.isVideoRecording2():
                logger.debug("Video recording 2 started")
                sc.isVideoRecording2 = True
                msg = "Video recorded to " + fp
                return jsonify(message=msg)
            else:
                logger.debug("Video recording 2 did not start")
                sc.isVideoRecording2 = False
                msg = "Video recording failed. Requested resolution too high"
                return jsonify(message=msg), 500
        else:
            msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("record_video2 - %s", msg)
        return jsonify(message=msg), 500

@bp.route("/api/stop_video2", methods=["GET"])
@jwt_required()
def stop_video2():
    logger.debug("Thread %s: In /api/stop_video2", get_ident())
    if Camera().isCamera2Available():
        cfg = CameraCfg()
        sc = cfg.serverConfig
        if sc.isVideoRecording2 == True:
            fp = Camera().videoOutput2
            Camera().stopVideoRecording2()
            time.sleep(1)
            msg = {"Video": fp, "Status": "Stopped"}
            sc.isVideoRecording2 = False
            return jsonify(message=msg)
        else:
            msg = "No video recording in progress"
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("stop_video2 - %s", msg)
        return jsonify(message=msg), 500

@bp.route("/api/record_video_both", methods=["GET"])
@jwt_required()
def record_video_both():
    logger.debug("Thread %s: In /api/record_video_both", get_ident())
    if Camera().isCamera2Available():
        data = request.get_json()
        duration = 0
        if "duration" in data:
            duration = data.get("duration")
        logger.debug("Thread %s: /api/record_video_both - requested duration: %s", get_ident(), duration)

        cfg = CameraCfg()
        sc = cfg.serverConfig

        timeImg = datetime.datetime.now()
        filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Recording 2 videos %s", filenameVid)
        fp1 = Camera().recordVideo(filenameVid, filename, duration)
        fp2 = Camera().recordVideo2(filenameVid, filename, duration)
        time.sleep(4)
        msg = {}
        err = False
        if not sc.error:
            # Check whether video is being recorded
            if Camera.isVideoRecording():
                logger.debug("Video recording 1 started")
                if sc.displayContent == "hist":
                    if sc.displayHistogram is None:
                        if sc.displayPhoto:
                            generateHistogram(sc)
                sc.isVideoRecording = True
                msg["Video 1"] = fp1
            else:
                logger.debug("Video recording 1 did not start")
                sc.isVideoRecording = False
                msg["Video 1"] = "Video recording failed"
                err = True
        else:
            err = True
            msg["Video 1"] = "Error in " + sc.errorSource + ": " + sc.error
        if not sc.errorc2:
            # Check whether video is being recorded
            if Camera.isVideoRecording2():
                logger.debug("Video recording 2 started")
                sc.isVideoRecording2 = True
                msg["Video 2"] = fp2
            else:
                logger.debug("Video recording 2 did not start")
                sc.isVideoRecording2 = False
                msg["Video 2"] = "Video recording failed"
                err = True
        else:
            msg["Video 2"] = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            err = True
        if err == False:
            return jsonify(message=msg)
        else:
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("record_video_both - %s", msg)
        return jsonify(message=msg), 500

@bp.route("/api/stop_video_both", methods=["GET"])
@jwt_required()
def stop_video_both():
    logger.debug("Thread %s: In /api/stop_video_both", get_ident())
    if Camera().isCamera2Available():
        cfg = CameraCfg()
        sc = cfg.serverConfig

        msg = {}
        err = False
        if sc.isVideoRecording == False:
            msg["Video 1"] = "No video recording in progress for camera 1"
            err = True
        else:
            fp1 = Camera().videoOutput
            Camera().stopVideoRecording()
            sc.isVideoRecording = False
            msg["Video 1"] = {"Video": fp1, "Status": "Stopped"}

        if sc.isVideoRecording2 == False:
            msg["Video 2"] = "No video recording in progress for camera 2"
            err = True
        else:
            fp2 = Camera().videoOutput2
            Camera().stopVideoRecording2()
            sc.isVideoRecording2 = False
            msg["Video 2"] = {"Video": fp2, "Status": "Stopped"}

        time.sleep(1)

        if err == False:
            return jsonify(message=msg)
        else:
            return jsonify(message=msg), 500
    else:
        msg = "Second camera is not available"
        logger.error("stop_video_both - %s", msg)
        return jsonify(message=msg), 500

def propGen(property):
    """Generator to yield properties of a property separated by dot."""
    while len(property) > 0:
        p = property.find(".")
        if p >= 0:
            if p == 0:
                method = ""
            else:
                method = property[:p]
            property = property[p + 1 :]
        else:
            method = property
            property = ""
        params = []
        ps = method.find("(")
        if ps >= 0:
            pe = method.find(")", ps)
            if pe < 0:
                raise ValueError("Missing closing parenthesis in method: " + method)
            else:
                pars = method[ps + 1 : pe]
                if len(pars) > 0:
                    params = [p.strip() for p in pars.split(",")]
            method = method[:ps]
        yield (method, params, len(property) == 0)

def probeTerm(property):
    """Evaluate a property."""
    logger.debug("Thread %s: In probeTerm - property=%s", get_ident(), property)
    res = None
    obj = None
    for prop, params, last in propGen(property):
        logger.debug("Thread %s: In probeTerm - prop=%s, params=%s, last=%s", get_ident(), prop, params, last)
        if obj is None:
            if len(params) > 0:
                obj = globals()[prop](**params)
            else:
                obj = globals()[prop]()
            if last == True:
                res = obj
            logger.debug("Thread %s: In probeTerm - Instantiated %s(%s)", get_ident(), prop, params)
        else:
            if hasattr(obj, prop):
                method = getattr(obj, prop)
                if callable(method):
                    logger.debug("Thread %s: In probeTerm - Calling method %s with params %s", get_ident(), prop, params)
                    if last == True:
                        if len(params) > 0:
                            res = method(*params)
                        else:
                            res = method()
                    else:
                        if len(params) > 0:
                            obj = method(*params)
                        else:
                            obj = method()
                else:
                    logger.debug("Thread %s: In probeTerm - Accessing property %s", get_ident(), prop)
                    if last == True:
                        res = method
                    else:
                        obj = method
                if obj is None:
                    logger.debug("Thread %s: In probeTerm - obj is None after accessing %s", get_ident(), prop)
                    break
            else:
                raise AttributeError(f"Object {obj} has no attribute {prop}")
    try:
        result = jsonify(res)
    except TypeError as e:
        if hasattr(res, "toDict"):
            res = res.toDict()
        elif hasattr(res, "__dict__"):
            res = res.__dict__
        else:
            logger.error("Error in probeTerm - jsonify(res), error: %s", str(e))
            res = "Error : " + str(e)
    except Exception as e:
        logger.error("Error in probeTerm - jsonify(res), error: %s", str(e))
        res = "Error : " + str(e)
    return res

@bp.route("/api/probe", methods=["GET"])
@jwt_required()
def probe():
    logger.debug("Thread %s: In /api/probe", get_ident())
    if CameraCfg().serverConfig.useStereo == True:
        from raspiCamSrv.stereoCam import StereoCam
    result = {}
    data = request.get_json()
    if "properties" in data:
        properties = data.get("properties")
    else:
        result["error"] = "No properties provided"
        return jsonify(result), 400

    if len(properties) == 0:
        result["error"] = "properties must not be empty"
        return jsonify(result), 400

    results = []
    result["results"] = results
    for t in properties:
        property = t["property"]
        logger.debug("Thread %s: In api/probe - property:%2s", get_ident(), property)
        res = {}
        try:
            res[property] = probeTerm(property)
        except Exception as e:
            logger.error("Error in api/probe - property: %s, error: %s", property, str(e))
            res["property"] = "ERROR:" + str(e)
        results.append(res)

    return jsonify(result)
