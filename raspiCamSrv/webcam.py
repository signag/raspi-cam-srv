from flask import (
    Blueprint,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, TuningConfig, StereoConfig, ServerConfig
from raspiCamSrv.version import version
from raspiCamSrv.home import generateHistogram
from _thread import get_ident
from pathlib import Path
import os
import datetime
import time
import copy

from raspiCamSrv.auth import login_required, login_for_streaming
import logging

bp = Blueprint("webcam", __name__)

logger = logging.getLogger(__name__)

# Try to import StereoCam
try:
    from raspiCamSrv.stereoCam import StereoCam
except ImportError:
    pass


@bp.route("/webcam")
@login_required
def webcam():
    logger.debug("In webcam")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    sc.error = None
    sc.errorc2 = None
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    Camera().startLiveStream()
    Camera().startLiveStream2()
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    if sc.useStereo == False:
        if sc.lastCamTab == "calibcam" or sc.lastCamTab == "stereocam":
            sc.lastCamTab = "webcam"
    if len(sc.supportedCameras) < 2:
        sc.lastCamTab = "webcam"

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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )

@bp.route("/store_streaming_config", methods=("GET", "POST"))
@login_required
def store_streaming_config():
    logger.debug("In store_streaming_config")
    Camera().startLiveStream()
    Camera().startLiveStream2()
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        scfg = cfg.streamingCfg[str(sc.activeCamera)]
        if sc.activeCameraIsUsb == False:
            scfg["tuningconfig"] = copy.deepcopy(cfg.tuningConfig)
        scfg["liveconfig"] = copy.deepcopy(cfg.liveViewConfig)
        scfg["photoconfig"] = copy.deepcopy(cfg.photoConfig)
        scfg["rawconfig"] = copy.deepcopy(cfg.rawConfig)
        scfg["videoconfig"] = copy.deepcopy(cfg.videoConfig)
        scfg["controls"] = copy.deepcopy(cfg.controls)
        sc.unsavedChanges = True
        sc.addChangeLogEntry(
            f"Camera settings for {sc.activeCameraInfo} saved for camera switch and streaming"
        )
        cfg.streamingCfgInvalid = False
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/sync_settings", methods=("GET", "POST"))
@login_required
def sync_settings():
    logger.debug("In sync_settings")
    Camera().startLiveStream()
    Camera().startLiveStream2()
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        if sc.activeCameraInfo[8:] == str2["camerainfo"][8:]:
            scfg = cfg.streamingCfg[str(Camera().camNum2)]
            if sc.activeCameraIsUsb == False:
                scfg["tuningconfig"] = copy.deepcopy(cfg.tuningConfig)
            scfg["liveconfig"] = copy.deepcopy(cfg.liveViewConfig)
            scfg["photoconfig"] = copy.deepcopy(cfg.photoConfig)
            scfg["rawconfig"] = copy.deepcopy(cfg.rawConfig)
            scfg["videoconfig"] = copy.deepcopy(cfg.videoConfig)
            scfg["controls"] = copy.deepcopy(cfg.controls)
            Camera().restartLiveStream2()
            sc.unsavedChanges = True
            sc.addChangeLogEntry(
                f"Camera settings for {sc.activeCameraInfo} synced with camera {str2['camerainfo']}"
            )
        else:
            flash("Camera settings can only be synced for the same camera model")
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/switch_cameras", methods=("GET", "POST"))
@login_required
def switch_cameras():
    logger.debug("In switch_cameras")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        msg = None
        activeCam = sc.activeCamera
        newCam = activeCam
        if sc.secondCamera is None:
            for cm in cs:
                if activeCam != cm.num:
                    newCam = cm.num
                    newCamInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
                    newCamModel = cm.model
                    newCamIsUsb = cm.isUsb
                    newCamUsbDev = cm.usbDev
                    break
        else:
            newCam = sc.secondCamera
            newCamInfo = sc.secondCameraInfo
            newCamModel = sc.secondCameraModel
            newCamIsUsb = sc.secondCameraIsUsb
            newCamUsbDev = sc.secondCameraUsbDev

        if newCam != sc.activeCamera:
            if sc.isTriggerRecording:
                msg = "Please go to 'Trigger' and stop the active process before changing the configuration"
            if sc.isVideoRecording == True:
                msg = "Please stop video recording before changing the tuning configuration"
            if sc.isPhotoSeriesRecording:
                msg = "Please go to 'Photo Series' and stop the active process before changing the tuning configuration"
            if not msg:
                sc.secondCamera = sc.activeCamera
                sc.secondCameraInfo = sc.activeCameraInfo
                sc.secondCameraModel = sc.activeCameraModel
                sc.secondCameraIsUsb = sc.activeCameraIsUsb
                sc.secondCameraUsbDev = sc.activeCameraUsbDev
                sc.activeCamera = newCam
                sc.activeCameraInfo = newCamInfo
                sc.activeCameraModel = newCamModel
                sc.activeCameraIsUsb = newCamIsUsb
                sc.activeCameraUsbDev = newCamUsbDev
                cfg.liveViewConfig.stream_size = None
                cfg.photoConfig.stream_size = None
                cfg.rawConfig.stream_size = None
                cfg.videoConfig.stream_size = None
                strCfg = cfg.streamingCfg
                newCamStr = str(newCam)
                if newCamStr in strCfg:
                    ncfg = strCfg[newCamStr]
                    if "tuningconfig" in ncfg:
                        cfg.tuningConfig = ncfg["tuningconfig"]
                    else:
                        cfg.tuningConfig = TuningConfig()
                else:
                    cfg.tuningConfig = TuningConfig()
                Camera.switchCamera()
                if sc.isLiveStream2:
                    str2 = cfg.streamingCfg[str(Camera().camNum2)]
                logger.debug(
                    "switch_cameras - active camera set to %s", sc.activeCamera
                )
                sc.unsavedChanges = True
                sc.addChangeLogEntry(
                    f"Cameras switched: Active camera now: {sc.activeCameraInfo}"
                )
                cfg.streamingCfgInvalid = False
        if msg:
            flash(msg)
        return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs)
    else:
        return redirect(url_for("webcam.webcam"))


@bp.route("/change_active_camera", methods=("GET", "POST"))
@login_required
def change_active_camera():
    logger.debug("In change_active_camera")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        msg = None
        newCam = int(request.form["activecamera"])
        secondCamera = -1
        if not sc.secondCamera is None:
            secondCamera = sc.secondCamera
        for cm in cs:
            if newCam == cm.num:
                newCamInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
                newCamModel = cm.model
                newCamIsUsb = cm.isUsb
                newCamUsbDev = cm.usbDev
                break

        if newCam != sc.activeCamera:
            if sc.isTriggerRecording:
                msg = "Please go to 'Trigger' and stop the active process before changing the configuration"
            if sc.isVideoRecording == True:
                msg = "Please stop video recording before changing the camera"
            if sc.isPhotoSeriesRecording:
                msg = "Please go to 'Photo Series' and stop the active process before changing the camera"
            if newCam == secondCamera:
                msg = "Active camera must be different from second camera. Use 'Switch Cameras' to swap the cameras."
            if not msg:
                sc.activeCamera = newCam
                sc.activeCameraInfo = newCamInfo
                sc.activeCameraModel = newCamModel
                sc.activeCameraIsUsb = newCamIsUsb
                sc.activeCameraUsbDev = newCamUsbDev
                cfg.liveViewConfig.stream_size = None
                cfg.photoConfig.stream_size = None
                cfg.rawConfig.stream_size = None
                cfg.videoConfig.stream_size = None
                strCfg = cfg.streamingCfg
                newCamStr = str(newCam)
                if newCamStr in strCfg:
                    ncfg = strCfg[newCamStr]
                    if "tuningconfig" in ncfg:
                        cfg.tuningConfig = ncfg["tuningconfig"]
                    else:
                        cfg.tuningConfig = TuningConfig()
                else:
                    cfg.tuningConfig = TuningConfig()
                Camera.switchCamera()
                if sc.isLiveStream2:
                    str2 = cfg.streamingCfg[str(Camera().camNum2)]
                logger.debug(
                    "switch_cameras - active camera set to %s", sc.activeCamera
                )
                sc.unsavedChanges = True
                sc.addChangeLogEntry(f"Active camera changed to: {sc.activeCameraInfo}")
                camL, camR = getStereoCameras()
                doInitCalibration(camL, camR)
        if msg:
            flash(msg)
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/change_second_camera", methods=("GET", "POST"))
@login_required
def change_second_camera():
    logger.debug("In change_second_camera")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        msg = None
        secondCam = int(request.form["secondcamera"])
        activeCam = sc.activeCamera
        newCam = secondCam
        for cm in cs:
            if newCam == cm.num:
                newCamInfo = "Camera " + str(cm.num) + " (" + cm.model + ")"
                newCamModel = cm.model
                newCamIsUsb = cm.isUsb
                newCamUsbDev = cm.usbDev
                break

        if newCam != sc.secondCamera:
            if newCam == activeCam:
                msg = "Second camera must be different from active camera. Use 'Switch Cameras' to swap the cameras."
            if not msg:
                sc.secondCamera = newCam
                sc.secondCameraInfo = newCamInfo
                sc.secondCameraModel = newCamModel
                sc.secondCameraIsUsb = newCamIsUsb
                sc.secondCameraUsbDev = newCamUsbDev
                Camera.switchCamera()
                if sc.isLiveStream2:
                    str2 = cfg.streamingCfg[str(Camera().camNum2)]
                logger.debug(
                    "switch_cameras - second camera set to %s", sc.secondCamera
                )
                sc.unsavedChanges = True
                sc.addChangeLogEntry(f"Second camera now: {sc.secondCameraInfo}")
        if msg:
            flash(msg)
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/photo_feed")
@login_for_streaming
def photo_feed():
    # logger.debug("Thread %s: In photo_feed", get_ident())
    Camera().startLiveStream()
    return Response(Camera().get_photoFrame(), mimetype="image/jpeg")


@bp.route("/photo_feed2")
@login_for_streaming
def photo_feed2():
    # logger.debug("Thread %s: In photo_feed2", get_ident())
    Camera().startLiveStream2()
    return Response(Camera().get_photoFrame2(), mimetype="image/jpeg")


@bp.route("/cam_take_photo", methods=("GET", "POST"))
@login_required
def cam_take_photo():
    logger.debug("Thread %s: In cam_take_photo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
                logger.debug(
                    "take_photo - sc.displayHistogram: %s", sc.displayHistogram
                )
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_take_raw_photo", methods=("GET", "POST"))
@login_required
def cam_take_raw_photo():
    logger.debug("Thread %s: In cam_take_raw_photo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        if sc.activeCameraIsUsb == False:
            filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        else:
            filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + ".tiff"
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_record_video", methods=("GET", "POST"))
@login_required
def cam_record_video():
    logger.debug("Thread %s: In cam_record_video", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_stop_recording", methods=("GET", "POST"))
@login_required
def cam_stop_recording():
    logger.debug("Thread %s: In cam_stop_recording", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/take_photo2", methods=("GET", "POST"))
@login_required
def take_photo2():
    logger.debug("Thread %s: In take_photo2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_take_raw_photo2", methods=("GET", "POST"))
@login_required
def cam_take_raw_photo2():
    logger.debug("Thread %s: In cam_take_raw_photo2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        if sc.secondCameraIsUsb == False:
            filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        else:
            filenameRaw = timeImg.strftime("%Y%m%d_%H%M%S") + ".tiff"
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_record_video2", methods=("GET", "POST"))
@login_required
def cam_record_video2():
    logger.debug("Thread %s: In cam_record_video2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_stop_recording2", methods=("GET", "POST"))
@login_required
def cam_stop_recording2():
    logger.debug("Thread %s: In cam_stop_recording2", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/take_photo_both", methods=("GET", "POST"))
@login_required
def take_photo_both():
    logger.debug("Thread %s: In take_photo_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )

@bp.route("/cam_take_raw_photo_both", methods=("GET", "POST"))
@login_required
def cam_take_raw_photo_both():
    logger.debug("Thread %s: In cam_take_raw_photo_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "multicam"
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        file = timeImg.strftime("%Y%m%d_%H%M%S") + "."
        filename1 = file + sc.photoType
        if sc.activeCameraIsUsb == False:
            filename1Raw = file + sc.rawPhotoType
        else:
            filename1Raw = file + "tiff"
        filename2 = file + sc.photoType
        if sc.secondCameraIsUsb == False:
            filename2Raw = file + sc.rawPhotoType
        else:
            filename2Raw = file + "tiff"
        logger.debug("Saving raw images as %s and %s", filename1Raw, filename2Raw)
        fp1 = Camera().takeRawImage(filename1Raw, filename1)
        fp2 = Camera().takeRawImage2(filename2Raw, filename2)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_record_video_both", methods=("GET", "POST"))
@login_required
def cam_record_video_both():
    logger.debug("Thread %s: In cam_record_video_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/cam_stop_recording_both", methods=("GET", "POST"))
@login_required
def cam_stop_recording_both():
    logger.debug("Thread %s: In cam_stop_recording_both", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
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

        time.sleep(2)
        flash(msg1)
        flash(msg2)
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/start_stereo_cam", methods=("GET", "POST"))
@login_required
def start_stereo_cam():
    logger.debug("Thread %s: In start_stereo_cam", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "stereocam"
    if request.method == "POST":
        err = None
        StereoCam().startStereoCam()
        if sc.error:
            logger.debug("In start_stereo_cam - StereoCam not started because of error")
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
            err = None
        else:
            sc.isStereoCamActive = True
            logger.debug("In start_stereo_cam - StereoCam started")
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/stop_stereo_cam", methods=("GET", "POST"))
@login_required
def stop_stereo_cam():
    logger.debug("Thread %s: In stop_stereo_cam", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "stereocam"
    if request.method == "POST":
        if sc.isStereoCamActive == True:
            scam = StereoCam()
            if sc.isStereoCamRecording == True:
                scam.stopRecordStereo()
                time.sleep(1)
            scam.stopStereoCam()
            sc.isStereoCamActive = False
            logger.debug("In stop_stereo_cam - StereoCam stopped")
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/stereo_cam_feed")
# @login_required
def stereo_cam_feed():
    # logger.debug("Thread %s: In stereo_cam_feed", get_ident())
    Camera().startLiveStream()
    Camera().startLiveStream2()
    scam = StereoCam()
    return Response(
        gen_stereoCamFrame(scam), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def gen_stereoCamFrame(stereoCam):
    """Stereo camera streaming generator function."""
    # logger.debug("Thread %s: In gen_stereoCamFrame", get_ident())
    yield b"--frame\r\n"
    while True:
        frame = stereoCam.get_stereoFrame()
        if frame:
            # logger.debug("Thread %s: gen_stereoCamFrame - Got frame of length %s: %s", get_ident(), len(frame), frame)
            yield b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n--frame\r\n"


@bp.route("/stereo_feed")
@login_for_streaming
def stereo_feed():
    logger.debug(
        "Thread %s: In stereo_feed - client IP: %s", get_ident(), request.remote_addr
    )
    sc = CameraCfg().serverConfig
    sc.registerStreamingClient(request.remote_addr, "stereo_feed", get_ident())
    Camera().startLiveStream()
    Camera().startLiveStream2()
    StereoCam().startStereoCam()
    sc.isStereoCamActive = True
    return Response(
        gen_stereoCamFrame(StereoCam()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@bp.route("/stereo_display", methods=("GET", "POST"))
@login_required
def stereo_display():
    logger.debug("Thread %s: In stereo_display", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "stereocam"
    if request.method == "POST":
        if not request.form.get("applycalibrectify") is None:
            ster.applyCalibRectify = True
        else:
            ster.applyCalibRectify = False
        logger.debug(
            "Thread %s: In stereo_display applyCalibRectify set to %s",
            get_ident(),
            ster.applyCalibRectify,
        )
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/stereo_config", methods=("GET", "POST"))
@login_required
def stereo_config():
    logger.debug("Thread %s: In stereo_config", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "stereocam"
    if request.method == "POST":
        err = ""
        done = False
        intent = None
        stereoAlgo = None
        if err == "":
            if not request.form.get("intent") is None:
                intent = request.form["intent"]
                logger.debug("webcam.stereo_config - intent=%s", intent)
                tmp["intent"] = intent

                if int(intent) != ster.intentIdx:
                    ster.intentIdx = int(intent)
                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(
                        f"Intent for Stereo Cam changed to {ster.intent}"
                    )
            else:
                err = " "
        if err == "":
            if not request.form.get("stereoalgo") is None:
                stereoAlgo = request.form["stereoalgo"]
                logger.debug("webcam.stereo_config - stereoAlgo=%s", stereoAlgo)
                tmp["stereoAlgo"] = stereoAlgo

                if int(stereoAlgo) != ster.intentAlgoIdx:
                    ster.intentAlgoIdx = int(stereoAlgo)
                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(
                        f"Algorithm for Stereo Cam changed to {ster.intentAlgo}"
                    )
            else:
                err = " "
        if err == "":
            if not intent is None:
                if intent == "0":
                    if not stereoAlgo is None:
                        if stereoAlgo == "0":
                            if not request.form.get("bmnumdisparitiesfactor") is None:
                                bm_numDisparitiesFactor = request.form.get(
                                    "bmnumdisparitiesfactor"
                                )
                            else:
                                err = " "
                            if not request.form.get("bmblocksize") is None:
                                bm_blockSize = request.form.get("bmblocksize")
                            else:
                                err = " "
                            if err == "":
                                try:
                                    ster.bm_numDisparitiesFactor = int(
                                        bm_numDisparitiesFactor
                                    )
                                    ster.bm_blockSize = int(bm_blockSize)
                                    done = True
                                except ValueError as e:
                                    err = e.args[0]
                        if stereoAlgo == "1":
                            if not request.form.get("sgbmmindisparity") is None:
                                sgbm_minDisparity = request.form.get("sgbmmindisparity")
                            else:
                                err = " "
                            if not request.form.get("sgbmnumdisparitiesfactor") is None:
                                sgbm_numDisparitiesFactor = request.form.get(
                                    "sgbmnumdisparitiesfactor"
                                )
                            else:
                                err = " "
                            if not request.form.get("sgbmblocksize") is None:
                                sgbm_blockSize = request.form.get("sgbmblocksize")
                            else:
                                err = " "
                            if not request.form.get("sgbmp1") is None:
                                sgbm_P1 = request.form.get("sgbmp1")
                            else:
                                err = " "
                            if not request.form.get("sgbmp2") is None:
                                sgbm_P2 = request.form.get("sgbmp2")
                            else:
                                err = " "
                            if not request.form.get("sgbmdisp12maxdiff") is None:
                                sgbm_disp12MaxDiff = request.form.get(
                                    "sgbmdisp12maxdiff"
                                )
                            else:
                                err = " "
                            if not request.form.get("sgbmprefiltercap") is None:
                                sgbm_preFilterCap = request.form.get("sgbmprefiltercap")
                            else:
                                err = " "
                            if not request.form.get("sgbmuniquenessratio") is None:
                                sgbm_uniquenessRatio = request.form.get(
                                    "sgbmuniquenessratio"
                                )
                            else:
                                err = " "
                            if not request.form.get("sgbmspecklewindowsize") is None:
                                sgbm_speckleWindowSize = request.form.get(
                                    "sgbmspecklewindowsize"
                                )
                            else:
                                err = " "
                            if not request.form.get("sgbmspecklerange") is None:
                                sgbm_speckleRange = request.form.get("sgbmspecklerange")
                            else:
                                err = " "
                            if not request.form.get("sgbmmode") is None:
                                sgbm_mode = request.form.get("sgbmmode")
                            else:
                                err = " "

                            if err == "":
                                try:
                                    ster.sgbm_minDisparity = int(sgbm_minDisparity)
                                    ster.sgbm_numDisparitiesFactor = int(
                                        sgbm_numDisparitiesFactor
                                    )
                                    ster.sgbm_blockSize = int(sgbm_blockSize)
                                    ster.sgbm_P1 = int(sgbm_P1)
                                    ster.sgbm_P2 = int(sgbm_P2)
                                    ster.sgbm_disp12MaxDiff = int(sgbm_disp12MaxDiff)
                                    ster.sgbm_preFilterCap = int(sgbm_preFilterCap)
                                    ster.sgbm_uniquenessRatio = int(
                                        sgbm_uniquenessRatio
                                    )
                                    ster.sgbm_speckleWindowSize = int(
                                        sgbm_speckleWindowSize
                                    )
                                    ster.sgbm_speckleRange = int(sgbm_speckleRange)
                                    ster.sgbm_mode = int(sgbm_mode)
                                    done = True
                                except ValueError as e:
                                    err = e.args[0]
        if err.strip() != "":
            flash(err)
        if done == True:
            sc.unsavedChanges = True
            sc.addChangeLogEntry(f"Stereo cam settings changed")

    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp
    )


@bp.route("/first_calib_photo", methods=("GET", "POST"))
@login_required
def first_calib_photo():
    logger.debug("Thread %s: In first_calib_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    for cam in ster.calibPhotosIdx:
        if ster.calibPhotosIdx[cam] > 0:
            ster.calibPhotosIdx[cam] = 0
    return redirect(url_for("webcam.webcam"))


@bp.route("/prev_calib_photo", methods=("GET", "POST"))
@login_required
def prev_calib_photo():
    logger.debug("Thread %s: In prev_calib_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    for cam in ster.calibPhotosIdx:
        if ster.calibPhotosIdx[cam] > 0:
            ster.calibPhotosIdx[cam] -= 1
    return redirect(url_for("webcam.webcam"))


@bp.route("/next_calib_photo", methods=("GET", "POST"))
@login_required
def next_calib_photo():
    logger.debug("Thread %s: In next_calib_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    for cam in ster.calibPhotosIdx:
        if (
            ster.calibPhotosIdx[cam] >= 0
            and ster.calibPhotosIdx[cam] < ster.calibPhotosCount[cam] - 1
        ):
            ster.calibPhotosIdx[cam] += 1
    return redirect(url_for("webcam.webcam"))


@bp.route("/last_calib_photo", methods=("GET", "POST"))
@login_required
def last_calib_photo():
    logger.debug("Thread %s: In last_calib_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    for cam in ster.calibPhotosIdx:
        ster.calibPhotosIdx[cam] = ster.calibPhotosCount[cam] - 1
    return redirect(url_for("webcam.webcam"))


def doRemoveCalibPhoto(sc: ServerConfig, ster: StereoConfig, idx: int) -> bool:
    """Remove a calibration photo with the given index for all cameras"""
    logger.debug("Thread %s: In doRemoveCalibPhoto - idx = %s", get_ident(), idx)
    res = True
    for cam in ster.calibPhotosIdx:
        sp = ster.calibPhotos[cam][idx]
        spC = ster.calibPhotosCrn[cam][idx]
        fp = sc.photoRoot + "/" + sp
        fpC = sc.photoRoot + "/" + spC
        logger.debug(
            "Thread %s: In doRemoveCalibPhoto - Trying to remove %s", get_ident(), fp
        )
        if os.path.exists(fp):
            try:
                os.remove(fp)
                os.remove(fpC)
                logger.debug(
                    "Thread %s: In doRemoveCalibPhoto - removed Photo %s",
                    get_ident(),
                    fp,
                )
            except Exception as e:
                logger.error(
                    "Thread %s: Error removing calibration photo %s: %s",
                    get_ident(),
                    fp,
                    e,
                )
                res = False
        else:
            logger.debug(
                "Thread %s: In doRemoveCalibPhoto - Photo %s does not exist",
                get_ident(),
                fp,
            )
        ster.calibPhotos[cam].pop(idx)
        ster.calibPhotosCrn[cam].pop(idx)
        ster.calibPhotosCount[cam] = len(ster.calibPhotos[cam])
        if ster.calibPhotosIdx[cam] >= ster.calibPhotosCount[cam]:
            ster.calibPhotosIdx[cam] = ster.calibPhotosCount[cam] - 1
        if ster.calibPhotosCount[cam] < ster.calibPhotosTarget:
            ster.calibPhotosOK[cam] = False
    return res


def getStereoCameras():
    """Get the two cameras to be involved in stereo processing"""
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL = str(cfg.serverConfig.activeCamera)
    if Camera().camNum2 is not None:
        camR = str(Camera().camNum2)
    else:
        camR = None
    return camL, camR


@bp.route("/remove_calib_photo", methods=("GET", "POST"))
@login_required
def remove_calib_photo():
    logger.debug("Thread %s: In remove_calib_photo", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    camL, camR = getStereoCameras()
    if doRemoveCalibPhoto(sc, ster, ster.calibPhotosIdx[camL]) == False:
        flash("Not all photos could be removed")
    else:
        doResetCalibration(camL, camR, keepPhotos=True)
    sc.unsavedChanges = True
    sc.addChangeLogEntry(f"Calibration photo removed")
    return redirect(url_for("webcam.webcam"))


@bp.route("/display_corners", methods=("GET", "POST"))
@login_required
def display_corners():
    logger.debug("Thread %s: In display_corners", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    if not request.form.get("displaycorners") is None:
        ster.calibShowCorners = True
    else:
        ster.calibShowCorners = False
    return redirect(url_for("webcam.webcam"))


@bp.route("/calib_settings", methods=("GET", "POST"))
@login_required
def calib_settings():
    logger.debug("Thread %s: In calib_settings", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    if request.method == "POST":
        logger.debug("Thread %s: In calib_settings - POST", get_ident())
        camL, camR = getStereoCameras()
        calibPatternIdx = ster.calibPatternIdx
        if not request.form.get("calibpattern") is None:
            calibPatternIdx = int(request.form.get("calibpattern"))
        if calibPatternIdx != ster.calibPatternIdx:
            logger.debug(
                "Thread %s: In calib_settings - calibPatternIdx changed", get_ident()
            )
            doResetCalibration(camL, camR)
            ster.calibPatternIdx = calibPatternIdx
            sc.unsavedChanges = True
            sc.addChangeLogEntry(
                f"Calibration pattern changed to {ster.calibPattern[calibPatternIdx]}"
            )
        else:
            (calibPatternSizeX, calibPatternSizeY) = ster.calibPatternSize
            if not request.form.get("calibpatternsize") is None:
                calibPatternSizeX = int(request.form.get("calibpatternsize"))
            if not request.form.get("calibpatternsizey") is None:
                calibPatternSizeY = int(request.form.get("calibpatternsizey"))
            if (calibPatternSizeX, calibPatternSizeY) != ster.calibPatternSize:
                logger.debug(
                    "Thread %s: In calib_settings - calibPatternSize changed %s -> %s",
                    get_ident(),
                    ster.calibPatternSize,
                    (calibPatternSizeX, calibPatternSizeY),
                )
                doResetCalibration(camL, camR)
                ster.calibPatternSize = (calibPatternSizeX, calibPatternSizeY)
                sc.unsavedChanges = True
                sc.addChangeLogEntry(
                    f"Calibration pattern size changed to {ster.calibPatternSize}"
                )
            else:
                calibPhotosTarget = ster.calibPhotosTarget
                if not request.form.get("calibphotostarget") is None:
                    calibPhotosTarget = int(request.form.get("calibphotostarget"))
                if calibPhotosTarget != ster.calibPhotosTarget:
                    logger.debug(
                        "Thread %s: In calib_settings - calibPhotosTarget changed from %s to %s",
                        get_ident(),
                        ster.calibPhotosTarget,
                        calibPhotosTarget,
                    )
                    ster.calibPhotosTarget = calibPhotosTarget
                    if ster.calibPhotosTarget > len(ster.calibPhotos[camL]):
                        doResetCalibration(camL, camR, keepPhotos=True)
                    elif ster.calibPhotosTarget < len(ster.calibPhotos[camL]):
                        doResetCalibration(camL, camR, keepPhotos=True)
                        ster.calibPhotosOK[camL] = True
                        ster.calibPhotosOK[camR] = True
                    else:
                        ster.calibPhotosOK[camL] = True
                        ster.calibPhotosOK[camR] = True
                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(
                        f"Calibration photos target changed to {ster.calibPhotosTarget}"
                    )
                rectifyScale = ster.rectifyScale
                if not request.form.get("rectifyscale") is None:
                    rectifyScale = int(request.form.get("rectifyscale"))
                if rectifyScale != ster.rectifyScale:
                    logger.debug(
                        "Thread %s: In calib_settings - rectifyScale changed from %s to %s",
                        get_ident(),
                        ster.rectifyScale,
                        rectifyScale,
                    )
                    ster.rectifyScale = rectifyScale
                    ster.calibCameraOK[camL] = False
                    if not camR is None:
                        ster.calibCameraOK[camR] = False
                    ster.calibStereoOK = False
                    ster.stereoRectifyOK = False
                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(
                        f"Rectify scale changed to {ster.rectifyScale}"
                    )
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/reset_calib_photos", methods=("GET", "POST"))
@login_required
def reset_calib_photos():
    logger.debug("Thread %s: In reset_calib_photos", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    if request.method == "POST":
        camL, camR = getStereoCameras()
        doResetCalibration(camL, camR)
        sc.unsavedChanges = True
        sc.addChangeLogEntry(f"Calibration was reset")
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/start_take_calib_photos", methods=("GET", "POST"))
@login_required
def start_take_calib_photos():
    logger.debug("Thread %s: In start_take_calib_photos", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    if request.method == "POST":
        msg = ""
        if ster.calibPhotosPath == "":
            msg = "Calibration photos path is not set."
        if msg == "":
            camL, camR = getStereoCameras()
            doInitCalibration(camL, camR)

            if camR is None:
                ster.calibPhotoRecordingMsg = f"Taking calibration photos... Place chessboard pattern in view of camera {caml}."
            else:
                ster.calibPhotoRecordingMsg = f"Taking calibration photos... Place chessboard pattern in view of cameras {camL} and {camR}."
            StereoCam().takeCalibrationPhotos(camL, camR)
        if msg != "":
            flash(msg)
    return redirect(url_for("webcam.webcam"))
    # return render_template("webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs)


@bp.route("/stop_take_calib_photos", methods=("GET", "POST"))
@login_required
def stop_take_calib_photos():
    logger.debug("Thread %s: In stop_take_calib_photos", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    if request.method == "POST":
        StereoCam().stoptakeCalibrationPhotos()
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


def doResetCalibration(camL: str, camR: str, keepPhotos: bool = False):
    """Reset the  camera calibration."""
    logger.debug("Thread %s: In doResetCalibration", get_ident())
    cfg = CameraCfg()
    sc = cfg.serverConfig
    ster = cfg.stereoCfg
    cs = cfg.cameras

    # Remove existing photos, if not excluded
    if not keepPhotos == True:
        while len(ster.calibPhotos[camL]) > 0:
            doRemoveCalibPhoto(sc, ster, 0)

    # Remove surplus photos
    while len(ster.calibPhotos[camL]) > ster.calibPhotosTarget:
        doRemoveCalibPhoto(sc, ster, len(ster.calibPhotos[camL]) - 1)

    doInitCalibration(camL, camR)
    doCleanup(sc, ster)

    ster.calibPhotosOK[camL] = False
    if not camR is None:
        ster.calibPhotosOK[camR] = False
    ster.calibCameraOK[camL] = False
    if not camR is None:
        ster.calibCameraOK[camR] = False
    ster.calibDate = None
    ster.calibDataOK = False
    ster.calibStereoOK = False
    ster.stereoRectifyOK = False
    ster.applyCalibRectify = False

    sc.unsavedChanges = True
    sc.addChangeLogEntry(f"Calibration photos were reset")


def doCleanup(sc: ServerConfig, ster: StereoConfig):
    """Clean up the calibration photo path"""
    logger.debug("Thread %s: In doCleanup", get_ident())

    # Create list of existing files
    root = sc.photoRoot + "/" + ster.calibPhotosSubPath
    rootPath = Path(root)

    # List all sub-directories
    camDirs = [a.name for a in rootPath.iterdir() if a.is_dir()]

    for cam in camDirs:
        logger.debug(
            "Thread %s: In doCleanup  - Searching in cam: %s", get_ident(), cam
        )
        if cam in ster.calibPhotos:
            camFiles = [f.name for f in (rootPath / cam).iterdir() if f.is_file()]
            for f in camFiles:
                logger.debug(
                    "Thread %s: In doCleanup  - Found file: %s", get_ident(), f
                )
                sp = ster.calibPhotosSubPath + cam + "/" + f
                if (
                    not sp in ster.calibPhotos[cam]
                    and not sp in ster.calibPhotosCrn[cam]
                ):
                    try:
                        fp = sc.photoRoot + "/" + sp
                        logger.debug(
                            "Thread %s: In doCleanup  - Removing file: %s",
                            get_ident(),
                            fp,
                        )
                        os.remove(fp)
                        logger.debug(
                            "Thread %s: In doRemoveCalibPhoto - removed Photo %s",
                            get_ident(),
                            fp,
                        )
                    except Exception as e:
                        logger.error(
                            "Thread %s: Error removing unused calibration photo %s: %s",
                            get_ident(),
                            fp,
                            e,
                        )
        else:
            logger.debug(
                "Thread %s: In doCleanup  - Ignoring subdirectory: %s", get_ident(), cam
            )


def doInitCalibration(camL: str, camR: str):
    """Initialize the  camera calibration, if required."""
    logger.debug("Thread %s: In doInitCalibration", get_ident())
    sc = CameraCfg().serverConfig
    ster = CameraCfg().stereoCfg

    if not camL in ster.calibPhotosOK:
        ster.calibPhotosOK[camL] = False
    if not camR is None:
        if not camR in ster.calibPhotosOK:
            ster.calibPhotosOK[camR] = False

    if not camL in ster.calibPhotos:
        ster.calibPhotos[camL] = []
        ster.calibPhotosCrn[camL] = []
    if not camR is None:
        if not camR in ster.calibPhotos:
            ster.calibPhotos[camR] = []
            ster.calibPhotosCrn[camR] = []

    if not camL in ster.calibPhotosCount:
        ster.calibPhotosCount[camL] = 0
    if not camR is None:
        if not camR in ster.calibPhotosCount:
            ster.calibPhotosCount[camR] = 0

    if not camL in ster.calibPhotosIdx:
        ster.calibPhotosIdx[camL] = -1
    if not camR is None:
        if not camR in ster.calibPhotosIdx:
            ster.calibPhotosIdx[camR] = -1

    if not camL in ster.calibCameraOK:
        ster.calibCameraOK[camL] = False
    if not camR is None:
        if not camR in ster.calibCameraOK:
            ster.calibCameraOK[camR] = False

    if not camL in ster.calibRmsReproError:
        ster.calibRmsReproError[camL] = 1.0
    if not camR is None:
        if not camR in ster.calibRmsReproError:
            ster.calibRmsReproError[camR] = 1.0

    calibRootPath = ster.calibPhotosPath
    os.makedirs(calibRootPath, exist_ok=True)
    calibCamPathL = calibRootPath + "/" + camL
    os.makedirs(calibCamPathL, exist_ok=True)
    if not camR is None:
        calibCamPathR = calibRootPath + "/" + camR
        os.makedirs(calibCamPathR, exist_ok=True)
    calibDataPath = sc.photoRoot + "/" + ster.calibDataSubPath
    os.makedirs(calibDataPath, exist_ok=True)


@bp.route("/calibrate_cameras", methods=("GET", "POST"))
@login_required
def calibrate_cameras():
    logger.debug("Thread %s: In calibrate_cameras", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "calibcam"
    if request.method == "POST":
        msg = ""
        camL, camR = getStereoCameras()
        try:
            StereoCam().calibrateCameras(camL, camR)
            sc.unsavedChanges = True
            sc.addChangeLogEntry(f"Camera(s) calibrated")
            msg = f"Cameras calibrated successfully. Calibration data in {ster.calibDataSubPath + ster.calibDataFile}"
        except Exception as e:
            logger.error("Thread %s: Error calibrating cameras: %s", get_ident(), e)
            msg = "Error calibrating cameras: {}".format(e)
        if msg != "":
            flash(msg)
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/start_record_stereo", methods=("GET", "POST"))
@login_required
def start_record_stereo():
    logger.debug("Thread %s: In start_record_stereo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "stereocam"
    if request.method == "POST":
        scam = StereoCam()
        if sc.isStereoCamRecording == False:
            timeImg = datetime.datetime.now()
            filenameVidRaw = timeImg.strftime("%Y%m%d_%H%M%S")
            done, fp, err = scam.startRecordStereo(filenameVidRaw)
            msg = ""
            if done == True:
                msg = f"Recording started successfully: {fp}"
            else:
                msg = f"Error starting recording: {err}"
            flash(msg)
        else:
            flash("Recording is already active.")
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )


@bp.route("/stop_record_stereo", methods=("GET", "POST"))
@login_required
def stop_record_stereo():
    logger.debug("Thread %s: In stop_record_stereo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    ster = cfg.stereoCfg
    cs = cfg.cameras
    camL, camR = getStereoCameras()
    doInitCalibration(camL, camR)
    tmp = {}
    tmp["intent"] = str(ster.intentIdx)
    tmp["stereoAlgo"] = str(ster.intentAlgoIdx)
    sc = cfg.serverConfig
    str2 = None
    if sc.isLiveStream2:
        str2 = cfg.streamingCfg[str(Camera().camNum2)]
    sc.curMenu = "webcam"
    sc.lastCamTab = "stereocam"
    if request.method == "POST":
        scam = StereoCam()
        if sc.isStereoCamRecording == True:
            scam.stopRecordStereo()
        else:
            flash("Recording is not active.")
    return render_template(
        "webcam/webcam.html", sc=sc, cfg=cfg, str2=str2, ster=ster, tmp=tmp, cs=cs
    )
