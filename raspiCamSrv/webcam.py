from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, TuningConfig
from raspiCamSrv.version import version
from raspiCamSrv.home import generateHistogram
from _thread import get_ident
import datetime
import time
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
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        scfg = cfg.streamingCfg[str(sc.activeCamera)]
        scfg["tuningconfig"] = copy.deepcopy(cfg.tuningConfig)
        scfg["liveconfig"] = copy.deepcopy(cfg.liveViewConfig)
        scfg["photoconfig"] = copy.deepcopy(cfg.photoConfig)
        scfg["rawconfig"] = copy.deepcopy(cfg.rawConfig)
        scfg["videoconfig"] = copy.deepcopy(cfg.videoConfig)
        scfg["controls"] = copy.deepcopy(cfg.controls)
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Camera settings for {sc.activeCameraInfo} saved for camera switch and streaming")
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
    sc.lastCamTab = "multicam"
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
                sc.unsavedChanges = True
                sc.addChangeLogEntry(f"Cameras switched: Active camera now: {sc.activeCameraInfo}")
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

@bp.route("/cam_take_photo", methods=("GET", "POST"))
@login_required
def cam_take_photo():
    logger.debug("Thread %s: In cam_take_photo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Saving image %s", filename)
        fp = Camera().takeImage(filename)
        if not sc.error:
            logger.debug("take_photo - sc.displayContent: %s", sc.displayContent)
            if sc.displayContent == "hist":
                logger.debug("take_photo - sc.displayHistogram: %s", sc.displayHistogram)
                if sc.displayHistogram is None:
                    logger.debug("take_photo - sc.displayPhoto: %s", sc.displayPhoto)
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg = "Image saved as " + fp
            flash(msg)
        else:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

@bp.route("/cam_take_raw_photo", methods=("GET", "POST"))
@login_required
def cam_take_raw_photo():
    logger.debug("Thread %s: In cam_take_raw_photo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        logger.debug("Saving raw image %s", filenameRaw)
        fp = Camera().takeRawImage(filenameRaw, filename)
        if not sc.error:
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg = "Image saved as " + fp
            flash(msg)
        else:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_record_video", methods=("GET", "POST"))
@login_required
def cam_record_video():
    logger.debug("Thread %s: In cam_record_video", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Recording a video %s", filenameVid)
        fp = Camera().recordVideo(filenameVid, filename)
        time.sleep(4)
        if not sc.error:
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
            # Check whether video is being recorded
            if Camera.isVideoRecording():
                logger.debug("Video recording started")
                sc.isVideoRecording = True
                if sc.recordAudio:
                    sc.isAudioRecording = True
                msg = "Video saved as " + fp
                flash(msg)
            else:
                logger.debug("Video recording did not start")
                sc.isVideoRecording = False
                sc.isAudioRecording = False
                msg = "Video recording failed. Requested resolution too high "
                flash(msg)
        else:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_stop_recording", methods=("GET", "POST"))
@login_required
def cam_stop_recording():
    logger.debug("Thread %s: In cam_stop_recording", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        logger.debug("Requesting video recording to stop")
        Camera().stopVideoRecording()
        sc.isVideoRecording = False
        sc.isAudioRecording = False
        # sleep a little bit to avoid race condition with restoreLiveStream in video thread
        time.sleep(2)
        msg = "Video recording stopped"
        flash(msg)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

@bp.route("/take_photo2", methods=("GET", "POST"))
@login_required
def take_photo2():
    logger.debug("Thread %s: In take_photo2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Saving image %s", filename)
        fp = Camera().takeImage2(filename)
        if not sc.errorc2:
            logger.debug("take_photo - success")
            msg = "Image saved as " + fp
            flash(msg)
        else:
            msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            flash(msg)
            if sc.errorc22:
                flash(sc.errorc22)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)

@bp.route("/cam_take_raw_photo2", methods=("GET", "POST"))
@login_required
def cam_take_raw_photo2():
    logger.debug("Thread %s: In cam_take_raw_photo2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        logger.debug("Saving raw image %s", filenameRaw)
        fp = Camera().takeRawImage2(filenameRaw, filename)
        if not sc.errorc2:
            msg = "Image saved as " + fp
            flash(msg)
        else:
            msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            flash(msg)
            if sc.errorc22:
                flash(sc.errorc22)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_record_video2", methods=("GET", "POST"))
@login_required
def cam_record_video2():
    logger.debug("Thread %s: In cam_record_video2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Recording a video %s", filenameVid)
        fp = Camera().recordVideo2(filenameVid, filename)
        time.sleep(4)
        if not sc.errorc2:
            # Check whether video is being recorded
            if Camera.isVideoRecording2():
                logger.debug("Video recording started")
                sc.isVideoRecording2 = True
                msg = "Video saved as " + fp
                flash(msg)
            else:
                logger.debug("Video recording did not start")
                sc.isVideoRecording2 = False
                msg = "Video recording failed. Requested resolution too high "
                flash(msg)
        else:
            msg = "Error in " + sc.errorc2Source + ": " + sc.errorc2
            flash(msg)
            if sc.errorc22:
                flash(sc.errorc22)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_stop_recording2", methods=("GET", "POST"))
@login_required
def cam_stop_recording2():
    logger.debug("Thread %s: In cam_stop_recording2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        logger.debug("Requesting video recording to stop")
        Camera().stopVideoRecording2()
        sc.isVideoRecording2 = False
        # sleep a little bit to avoid race condition with restoreLiveStream in video thread
        time.sleep(2)
        msg = "Video recording stopped"
        flash(msg)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/take_photo_both", methods=("GET", "POST"))
@login_required
def take_photo_both():
    logger.debug("Thread %s: In take_photo_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Saving image %s", filename)
        fp1 = Camera().takeImage(filename)
        fp2 = Camera().takeImage2(filename)
        msg1 = ""
        msg2 = ""
        if not sc.error:
            logger.debug("takeImage - success")
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg1 = f"Photo saved as {fp1}"
        else:
            msg1 = "Error in " + sc.errorcSource + ": " + sc.errorc
        if not sc.errorc2:
            logger.debug("takeImage2 - success")
            msg2 = f"Photo saved as {fp2}"
        else:
            msg2 = "Error in " + sc.errorc2Source + ": " + sc.errorc2
        flash(msg1)
        flash(msg2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_take_raw_photo_both", methods=("GET", "POST"))
@login_required
def cam_take_raw_photo_both():
    logger.debug("Thread %s: In cam_take_raw_photo_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        logger.debug("Saving raw image %s", filenameRaw)
        fp1 = Camera().takeRawImage(filenameRaw, filename)
        fp2 = Camera().takeRawImage2(filenameRaw, filename)
        msg1 = ""
        msg2 = ""
        if not sc.error:
            logger.debug("takeRawImage - success")
            if sc.displayContent == "hist":
                if sc.displayHistogram is None:
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg1 = f"Raw Photo saved as {fp1}"
        else:
            msg1 = "Error in " + sc.errorcSource + ": " + sc.errorc
        if not sc.errorc2:
            logger.debug("takeRawImage2 - success")
            msg2 = f"Raw Photo saved as {fp2}"
        else:
            msg2 = "Error in " + sc.errorc2Source + ": " + sc.errorc2
        flash(msg1)
        flash(msg2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_record_video_both", methods=("GET", "POST"))
@login_required
def cam_record_video_both():
    logger.debug("Thread %s: In cam_record_video_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Recording a video %s", filenameVid)
        fp1 = Camera().recordVideo(filenameVid, filename)
        fp2 = Camera().recordVideo2(filenameVid, filename)
        time.sleep(4)
        msg1 = ""
        msg2 = ""
        if not sc.error:
            # Check whether video is being recorded
            if Camera.isVideoRecording():
                logger.debug("Video recording 1 started")
                sc.isVideoRecording = True
                if sc.recordAudio:
                    sc.isAudioRecording = True
                if sc.displayContent == "hist":
                    if sc.displayHistogram is None:
                        if sc.displayPhoto:
                            generateHistogram(sc)
                msg1 = f"Video saved as {fp1}"
            else:
                logger.debug("Video recording 1 did not start")
                sc.isVideoRecording = False
                msg1 = "Video recording failed"
        else:
            err = True
            msg1 = "Error in " + sc.errorSource + ": " + sc.error
        if not sc.errorc2:
            # Check whether video is being recorded
            if Camera.isVideoRecording2():
                logger.debug("Video recording 2 started")
                sc.isVideoRecording2 = True
                msg2 = f"Video saved as {fp2}"
            else:
                logger.debug("Video recording 2 did not start")
                sc.isVideoRecording2 = False
                msg2 = "Video recording failed"
        else:
            msg2 = "Error in " + sc.errorc2Source + ": " + sc.errorc2
        flash(msg1)
        flash(msg2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)


@bp.route("/cam_stop_recording_both", methods=("GET", "POST"))
@login_required
def cam_stop_recording_both():
    logger.debug("Thread %s: In cam_stop_recording_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        logger.debug("Requesting video recording to stop")
        msg1 = ""
        msg2 = ""
        if sc.isVideoRecording == False:
            msg1 = "No video recording in progress for camera 1"
        else:
            fp1 = Camera().videoOutput
            Camera().stopVideoRecording()
            sc.isVideoRecording = False
            mag1 = f"Stopped Video: {fp1}"

        if sc.isVideoRecording2 == False:
            msg2 = "No video recording in progress for camera 2"
        else:
            fp2 = Camera().videoOutput2
            Camera().stopVideoRecording2()
            sc.isVideoRecording2 = False
            mag2 = f"Stopped Video: {fp2}"

        time.sleep(1)
        flash(msg1)
        flash(msg2)
    return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2)
