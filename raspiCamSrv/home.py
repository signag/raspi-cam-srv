from flask import current_app, Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.auth import login_required
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, ServerConfig
from raspiCamSrv.version import version
from libcamera import controls
from _thread import get_ident
import math
import os
import datetime
import time
import logging

bp = Blueprint("home", __name__)

logger = logging.getLogger(__name__)

@bp.route("/")
@login_required
def index():
    logger.debug("Thread %s: In index", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.error = None
    Camera().startLiveStream()
    logger.debug("Thread %s: Camera instantiated", get_ident())
    sc.curMenu = "live"
    logger.debug("Thread %s: cp.hasFocus is %s", get_ident(), cp.hasFocus)
    if sc.error:
        msg = "Error in " + sc.errorSource + ": " + sc.error
        flash(msg)
        if sc.error2:
            flash(sc.error2)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

def gen(camera):
    """Video streaming generator function."""
    #logger.debug("Thread %s: In gen", get_ident())
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()
        if frame:
            #logger.debug("Thread %s: gen - Got frame of length %s", get_ident(), len(frame))
            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

def gen2(camera):
    """Video streaming generator function."""
    #logger.debug("Thread %s: In gen", get_ident())
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame2()
        if frame:
            #logger.debug("Thread %s: gen - Got frame of length %s", get_ident(), len(frame))
            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/video_feed")
# @login_required
def video_feed():
    logger.debug("Thread %s: In video_feed", get_ident())
    Camera().startLiveStream()
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/video_feed2")
# @login_required
def video_feed2():
    logger.debug("Thread %s: In video_feed2", get_ident())
    Camera().startLiveStream2()
    return Response(gen2(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/photos/<photo>")
@login_required
def displayImage(photo: str):
    logger.debug("In displayImage")
    logger.debug("photo=%s", photo)
    logger.debug("current_app.root_path=%s", current_app.root_path)
    fp = current_app.root_path + "/photos/" + photo
    logger.debug("fp = %s", fp)
    return Response(fp, mimetype='image/jpg')

@bp.route("/focus_control", methods=("GET", "POST"))
@login_required
def focus_control():
    logger.debug("In focus_control")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "focus"
    if request.method == "POST":
        if cp.hasFocus:
            ctrls = {}
            if request.form.get("include_afmode") is None:
                cc.include_afMode = False
            else:
                cc.include_afMode = True
                afMode = int(request.form["afmode"])
                cc.afMode = afMode
                ctrls["AfMode"] = afMode

            if request.form.get("include_lensposition") is None:
                cc.include_lensPosition = False
            else:
                cc.include_lensPosition = True
                fDist = float(request.form["fdist"])
                cc.focalDistance = fDist
                lensPosition = cc.lensPosition
                ctrls["LensPosition"] = lensPosition

            if request.form.get("include_afmetering") is None:
                cc.include_afMetering = False
            else:
                cc.include_afMetering = True
                afMetering = int(request.form["afmetering"])
                cc.afMetering = afMetering
                ctrls["AfMetering"] = afMetering

            if request.form.get("include_afpause") is None:
                cc.include_afPause = False
            else:
                cc.include_afPause = True
                afPause = int(request.form["afpause"])
                cc.afPause = afPause
                ctrls["AfPause"] = afPause

            if request.form.get("include_afrange") is None:
                cc.include_afRange = False
            else:
                cc.include_afRange = True
                afRange = int(request.form["afrange"])
                cc.afRange = afRange
                ctrls["AfRange"] = afRange

            if request.form.get("include_afspeed") is None:
                cc.include_afSpeed = False
            else:
                cc.include_afSpeed = True
                afSpeed = int(request.form["afspeed"])
                cc.afSpeed = afSpeed
                ctrls["AfSpeed"] = afSpeed

            if request.form.get("include_afwindows") is None:
                cc.include_afWindows = False
                afWindowsStr = "()"
                cc.afWindowsStr = afWindowsStr
                ctrls["AfWindows"] = cc.afWindows
            else:
                cc.include_afWindows = True
                afWindowsStr = request.form["afwindows"]
                cc.afWindowsStr = afWindowsStr
                ctrls["AfWindows"] = cc.afWindows
                if len(cc.afWindows) == 0:
                    cc.include_afWindows = False

            Camera().applyControlsForLivestream()
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/trigger_autofocus", methods=("GET", "POST"))
@login_required
def trigger_autofocus():
    logger.debug("In trigger_autofocus")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "focus"
    if request.method == "POST":
        if cp.hasFocus:
            if cc.afMode == controls.AfModeEnum.Auto:
                Camera().applyControlsForAfCycle(cfg.liveViewConfig)
                success = Camera().cam.autofocus_cycle()
                if success:
                    lp = Camera().getLensPosition()
                    #lp = int(100 * lp) / 100
                    if lp > 0:
                        cc.lensPosition = lp
                        cc.include_lensPosition = True
                        cc.afMode = 0
                        msg = "Autofocus successful. See Focal Distance. Autofocus Mode set to 'Manual'."
                    else:
                        msg = "Camera returned LensPosition 0. Ignored"
                else:
                    msg = "Autofocus not successful"
            else:
                msg="ERROR: Autofocus Mode must be set to 'Auto'!"
            flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/set_zoom", methods=("GET", "POST"))
@login_required
def set_zoom():
    logger.debug("In set_zoom")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int(request.form["zoomfactorstep"])
        sc.zoomFactorStep = step
        logger.debug("sc.zoomFactorStep set to %s", step)
        if  sc.isZoomModeDraw == True:
            sc.isZoomModeDraw = False
            scalerCropStr = request.form["scalercrop"]
            logger.debug("Form scalerCrop: %s", scalerCropStr)
            sc.scalerCropLiveViewStr = scalerCropStr
            logger.debug("sc.scalerCropLiveView: %s", sc.scalerCropLiveView)
            cc.scalerCropStr = scalerCropStr
            logger.debug("cc.scalerCrop: %s", cc.scalerCrop)
            cc.include_scalerCrop = True
            Camera().applyControlsForLivestream()
            time.sleep(0.5)
            metadata = Camera().getMetaData()
            sc.scalerCropLiveView = metadata["ScalerCrop"]
            zoomFactor = sc.zoomFactorStep * math.floor((100 * cc.scalerCrop[2] / cp.pixelArraySize[0]) / sc.zoomFactorStep)
            if zoomFactor <= 0:
                zoomFactor = sc.zoomFactorStep
            sc.zoomFactor = zoomFactor
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_in", methods=("GET", "POST"))
@login_required
def zoom_in():
    logger.debug("In zoom_in")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    logger.debug("cfg.liveViewConfig.controls=%s",cfg.liveViewConfig.controls)
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        logger.debug("ScalerCrop old: %s", cc.scalerCrop)
        xCenter = cc.scalerCrop[0] + int(cc.scalerCrop[2]/2)
        yCenter = cc.scalerCrop[1] + int(cc.scalerCrop[3]/2)
        zfNext = sc.zoomFactor - sc.zoomFactorStep
        msg = []
        if zfNext < sc.zoomFactorStep:
            msg.append("WARNING: Minimum zoom factor reached!")
            zfNext = sc.zoomFactorStep
        width = int(sc.scalerCropDef[2] * zfNext / 100)
        height = int(sc.scalerCropDef[3] * zfNext / 100)

        if width < sc.scalerCropMin[2]:
            height = int(height * sc.scalerCropMin[2] / width)
            width = sc.scalerCropMin[2]
            msg.append("WARNING: Smallest ScalerCrop width reached")
        if height < sc.scalerCropMin[3]:
            width = int(width * sc.scalerCropMin[3] / height)
            height = sc.scalerCropMin[3]
            msg.append("WARNING: Smallest ScalerCrop height reached")

        if len(msg) > 0:
            for m in msg:
                flash(m)
            
        sccrop = (int(xCenter - width/2), int(yCenter - height/2), width, height)
        sc.zoomFactor = zfNext
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        logger.debug("ScalerCrop new: %s", cc.scalerCrop)
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

def checkScalerCrop(crop: tuple, range: tuple) -> tuple:
    """Check given cropping rectangle with respect to maximum rectangle
    
    Params:
        crop:   cropping rectangle to be tested (xOffset, yOffset, width, height)
        range:  allowed range (xOffset, yOffset, width, height)
        
    Return:
        crop: cropping rectangle with initial dimensions but eventually adjusted offset
        msg:  Message list with modifications made
    """
    res = crop
    msg = []
    x0 = crop[0]
    y0 = crop[1]
    width = crop[2]
    height = crop[3]
    if x0 < range[0]:
        msg.append("WARNING: left border reached")
        x0 = range[0]
    if y0 < range[1]:
        msg.append("WARNING: upper border reached")
        y0 = range[1]
    if x0 + width > range[0] + range[2]:
        msg.append("WARNING: right border reached")
        x0 = range[0] + range[2] - width
    if y0 + height > range[1] + range[3]:
        msg.append("WARNING: lower border reached")
        y0 = range[1] + range[3] - height
    return ((x0, y0, crop[2], crop[3]), msg)
    
@bp.route("/zoom_out", methods=("GET", "POST"))
@login_required
def zoom_out():
    logger.debug("In zoom_out")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        xCenter = cc.scalerCrop[0] + int(cc.scalerCrop[2]/2)
        yCenter = cc.scalerCrop[1] + int(cc.scalerCrop[3]/2)
        zfNext = sc.zoomFactor + sc.zoomFactorStep
        msg0 = ""
        if zfNext >= 100:
            zfNext = 100
            width = sc.scalerCropDef[2]
            height = sc.scalerCropDef[3]
            msg0 = "WARNING: Maximum zoom reached"
        else:
            width = int(sc.scalerCropDef[2] * zfNext / 100)
            height = int(sc.scalerCropDef[3] * zfNext / 100)
            
        ll = (xCenter - int(width / 2), yCenter - int(height / 2))
        sccrop = (ll[0], ll[1], width, height)
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        if msg0 != "":
            msg.append(msg0)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        sc.zoomFactor = zfNext
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_full", methods=("GET", "POST"))
@login_required
def zoom_full():
    logger.debug("In zoom_full")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        sc.isZoomModeDraw = False
        sc.zoomFactor = 100
        width = sc.scalerCropDef[2]
        height = sc.scalerCropDef[3]
        xCenter = cc.scalerCrop[0] + int(cc.scalerCrop[2]/2)
        yCenter = cc.scalerCrop[1] + int(cc.scalerCrop[3]/2)
        xOffset = int(xCenter - width / 2)
        yOffset = int(yCenter - height / 2)
        sccrop = (xOffset, yOffset, width, height)
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_up", methods=("GET", "POST"))
@login_required
def pan_up():
    logger.debug("In pan_up")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((sc.scalerCropDef[2] * sc.zoomFactorStep)/100)
        yOffset = cc.scalerCrop[1] - step
        sccrop = (cc.scalerCrop[0], yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_left", methods=("GET", "POST"))
@login_required
def pan_left():
    logger.debug("In pan_left")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((sc.scalerCropDef[2] * sc.zoomFactorStep)/100)
        xOffset = cc.scalerCrop[0] - step
        sccrop = (xOffset, cc.scalerCrop[1], cc.scalerCrop[2], cc.scalerCrop[3])
        logger.debug("pan_left - scalarCropDef   : %s", sc.scalerCropDef)
        logger.debug("pan_left - scalarCrop old  : %s", cc.scalerCrop)
        logger.debug("pan_left - scalarCrop Max  : %s", sc.scalerCropMax)
        logger.debug("pan_left - step: %s xOffset: %s", step, xOffset)
        logger.debug("pan_left - scalarCrop Init : %s", sccrop)
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        logger.debug("pan_left - scalarCrop Final: %s", sccrop)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_center", methods=("GET", "POST"))
@login_required
def pan_center():
    logger.debug("In pan_center")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        logger.debug("pan_center scalerCropDef: %s", sc.scalerCropDef)
        logger.debug("pan_center scalerCrop   : %s", cc.scalerCrop)
        xOffset = int(sc.scalerCropDef[0] + sc.scalerCropDef[2]/2 - cc.scalerCrop[2]/2)
        yOffset = int(sc.scalerCropDef[1] + sc.scalerCropDef[3]/2 - cc.scalerCrop[3]/2)
        logger.debug("pan_center xOffset: %s, yOffset: %s", xOffset, yOffset)
        sccrop = (xOffset, yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        logger.debug("pan_center - sccrop initial: %s", sccrop)
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        logger.debug("pan_center - sccrop final  : %s", sccrop)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_right", methods=("GET", "POST"))
@login_required
def pan_right():
    logger.debug("In pan_right")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((sc.scalerCropDef[2] * sc.zoomFactorStep)/100)
        xOffset = cc.scalerCrop[0] + step
        sccrop = (xOffset, cc.scalerCrop[1], cc.scalerCrop[2], cc.scalerCrop[3])
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/pan_down", methods=("GET", "POST"))
@login_required
def pan_down():
    logger.debug("In pan_down")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((sc.scalerCropDef[2] * sc.zoomFactorStep)/100)
        yOffset = cc.scalerCrop[1] + step
        sccrop = (cc.scalerCrop[0], yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        (sccrop, msg) = checkScalerCrop(sccrop, sc.scalerCropMax)
        if len(msg) > 0:
            for m in msg:
                flash(m)
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        if cc.scalerCrop != sc.scalerCropDef:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_default", methods=("GET", "POST"))
@login_required
def zoom_default():
    logger.debug("In zoom_default")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        sc.isZoomModeDraw = False
        sc.zoomFactor = 100
        sccrop = sc.scalerCropDef
        cc.scalerCrop = sccrop
        cc.include_scalerCrop = True
        Camera().applyControlsForLivestream()
        time.sleep(0.5)
        cc.include_scalerCrop = False
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_draw", methods=("GET", "POST"))
@login_required
def zoom_draw():
    logger.debug("In zoom_draw")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        sc.isZoomModeDraw = True
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/ae_control", methods=("GET", "POST"))
@login_required
def ae_control():
    logger.debug("In ae_control")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "autoexposure"
    if request.method == "POST":
        if request.form.get("include_aeconstraintmode") is None:
            cc.include_aeConstraintMode = False
        else:
            cc.include_aeConstraintMode = True
            aeConstraintMode = int(request.form["aeconstraintmode"])
            cc.aeConstraintMode = aeConstraintMode
            
        if request.form.get("include_aeenable") is None:
            cc.include_aeEnable = False
        else:
            cc.include_aeEnable = True
            aeEnable = not request.form.get("aeenable") is None
            cc.aeEnable = aeEnable

        if request.form.get("include_aeexposuremode") is None:
            cc.include_aeExposureMode = False
        else:
            cc.include_aeExposureMode = True
            aeExposureMode = int(request.form["aeexposuremode"])
            cc.aeExposureMode = aeExposureMode

        if request.form.get("include_aemeteringmode") is None:
            cc.include_aeMeteringMode = False
        else:
            cc.include_aeMeteringMode = True
            aeMeteringMode = int(request.form["aemeteringmode"])
            cc.aeMeteringMode = aeMeteringMode

        if cp.hasFlicker:
            if request.form.get("include_aeflickermode") is None:
                cc.include_aeFlickerMode = False
            else:
                cc.include_aeFlickerMode = True
                aeFlickerMode = int(request.form["aeflickermode"])
                cc.aeFlickerMode = aeFlickerMode

            if request.form.get("include_aeflickerperiod") is None:
                cc.include_aeFlickerPeriod = False
            else:
                cc.include_aeFlickerPeriod = True
                aeFlickerPeriod = int(request.form["aeflickerperiod"])
                cc.aeFlickerPeriod = aeFlickerPeriod

        Camera().applyControlsForLivestream()
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/exposure_control", methods=("GET", "POST"))
@login_required
def exposure_control():
    logger.debug("In exposure_control")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "exposure"
    if request.method == "POST":
        if request.form.get("include_analoguegain") is None:
            cc.include_analogueGain = False
        else:
            cc.include_analogueGain = True
            analogueGain = float(request.form["analoguegain"])
            cc.analogueGain = analogueGain
        
        if request.form.get("include_colourgains") is None:
            cc.include_colourGains = False
        else:
            cc.include_colourGains = True
            colourGainRed = float(request.form["colourgainred"])
            colourGainBlue = float(request.form["colourgainblue"])
            colourGains = (colourGainRed, colourGainBlue)
            cc.colourGains = colourGains
        
        if request.form.get("include_exposuretime") is None:
            cc.include_exposureTime = False
        else:
            cc.include_exposureTime = True
            exposureTimeSec = float(request.form["exposuretimesec"])
            cc.exposureTimeSec = exposureTimeSec
            exposureTime = cc.exposureTime
        
        if request.form.get("include_exposurevalue") is None:
            cc.include_exposureValue = False
        else:
            cc.include_exposureValue = True
            exposureValue = float(request.form["exposurevalue"])
            cc.exposureValue = exposureValue

        if request.form.get("include_framedurationlimits") is None:
            cc.include_frameDurationLimits = False
        else:
            cc.include_frameDurationLimits = True
            frameDurationLimitMax = int(request.form["framedurationlimitmax"])
            frameDurationLimitMin = int(request.form["framedurationlimitmin"])
            frameDurationLimits = (frameDurationLimitMax, frameDurationLimitMin)
            cc.frameDurationLimits = frameDurationLimits

        if cp.hasHdr:
            if request.form.get("include_hdrmode") is None:
                cc.include_hdrMode = False
            else:
                cc.include_hdrMode = True
                hdrMode = int(request.form["hdrmode"])
                cc.hdrMode = hdrMode

        Camera().applyControlsForLivestream()
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/image_control", methods=("GET", "POST"))
@login_required
def image_control():
    logger.debug("In image_control")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "image"
    if request.method == "POST":
        if request.form.get("include_noisereductionmode") is None:
            cc.include_noiseReductionMode = False
        else:
            cc.include_noiseReductionMode = True
            noiseReductionMode = int(request.form["noisereductionmode"])
            cc.noiseReductionMode = noiseReductionMode
        
        if request.form.get("include_saturation") is None:
            cc.include_saturation = False
        else:
            cc.include_saturation = True
            saturation = float(request.form["saturation"])
            cc.saturation = saturation
        
        if request.form.get("include_sharpness") is None:
            cc.include_sharpness = False
        else:
            cc.include_sharpness = True
            sharpness = float(request.form["sharpness"])
            cc.sharpness = sharpness
            
        if request.form.get("include_awbenable") is None:
            cc.include_awbEnable = False
        else:
            cc.include_awbEnable = True
            awbEnable = not request.form.get("awbenable") is None
            cc.awbEnable = awbEnable
        
        if request.form.get("include_awbmode") is None:
            cc.include_awbMode = False
        else:
            cc.include_awbMode = True
            awbMode = int(request.form["awbmode"])
            cc.awbMode = awbMode
        
        if request.form.get("include_contrast") is None:
            cc.include_contrast = False
        else:
            cc.include_contrast = True
            contrast = float(request.form["contrast"])
            cc.contrast = contrast

        if request.form.get("include_brightness") is None:
            cc.include_brightness = False
        else:
            cc.include_brightness = True
            brightness = float(request.form["brightness"])
            cc.brightness = brightness

        Camera().applyControlsForLivestream()
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
        
@bp.route("/meta_clear", methods=("GET", "POST"))
@login_required
def meta_clear():
    logger.debug("In meta_clear")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayMeta = None
        sc.displayPhoto = None
        sc.displayHistogram = None
        sc.displayMetaFirst = 0
        sc.displayMetaLast = 999
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
        
@bp.route("/meta_prev", methods=("GET", "POST"))
@login_required
def meta_prev():
    logger.debug("In meta_prev")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayMetaFirst -= 10
        if sc.displayMetaFirst < 0:
            sc.displayMetaFirst = 0
        sc.displayMetaLast = sc.displayMetaFirst + 10
        if sc.displayMetaLast > len(sc.displayMeta):
            sc.displayMetaLast = 999
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
        
@bp.route("/meta_next", methods=("GET", "POST"))
@login_required
def meta_next():
    logger.debug("In meta_next")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayMetaFirst += 10
        sc.displayMetaLast = sc.displayMetaFirst + 10
        if sc.displayMetaLast > len(sc.displayMeta):
            sc.displayMetaLast = 999
            sc.displayMetaFirst = len(sc.displayMeta) - 10
            if sc.displayMetaFirst < 0:
                sc.displayMetaFirst = 0
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/photoBuffer_add", methods=("GET", "POST"))
@login_required
def photoBuffer_add():
    logger.debug("In photoBuffer_add")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferAdd()
        if sc.displayContent == "hist":
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/photoBuffer_remove", methods=("GET", "POST"))
@login_required
def photoBuffer_remove():
    logger.debug("In photoBuffer_remove")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferRemove()
        if sc.displayContent == "hist":
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/photoBuffer_prev", methods=("GET", "POST"))
@login_required
def photoBuffer_prev():
    logger.debug("In photoBuffer_prev")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferPrev()
        if sc.displayContent == "hist":
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/photoBuffer_next", methods=("GET", "POST"))
@login_required
def photoBuffer_next():
    logger.debug("In photoBuffer_next")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferNext()
        if sc.displayContent == "hist":
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/show_photo", methods=("GET", "POST"))
@login_required
def show_photo():
    logger.debug("In show_photo")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.isDisplayHidden = False
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/hide_photo", methods=("GET", "POST"))
@login_required
def hide_photo():
    logger.debug("In hide_photo")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.isDisplayHidden = True
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/clear_buffer", methods=("GET", "POST"))
@login_required
def clear_buffer():
    logger.debug("In clear_buffer")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferClear()        
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        
            
@bp.route("/take_photo", methods=("GET", "POST"))
@login_required
def take_photo():
    logger.debug("Thread %s: In take_photo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Saving image %s", filename)
        fp = Camera().takeImage(filename)
        if not sc.error:
            logger.debug("take_photo - success")
            logger.debug("take_photo - sc.displayContent: %s", sc.displayContent)
            if sc.displayContent == "hist":
                logger.debug("take_photo - sc.displayHistogram: %s", sc.displayHistogram)
                if sc.displayHistogram is None:
                    logger.debug("take_photo - sc.displayPhoto: %s", sc.displayPhoto)
                    if sc.displayPhoto:
                        generateHistogram(sc)
            msg="Image saved as " + fp
            flash(msg)
        else:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/take_raw_photo", methods=("GET", "POST"))
@login_required
def take_raw_photo():
    logger.debug("Thread %s: In take_raw_photo", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
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
            msg="Image saved as " + fp
            flash(msg)
        else:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/record_video", methods=("GET", "POST"))
@login_required
def record_video():
    logger.debug("Thread %s: In record_video", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        timeImg = datetime.datetime.now()
        filenameVid = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        filename = timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        logger.debug("Recording a video %s", filenameVid)
        fp = Camera().recordVideo(filenameVid, filename)
        #TODO: Check sleep time. This might lead to errors when stopping video within that time
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
                msg="Video saved as " + fp
                flash(msg)
            else:
                logger.debug("Video recording did not start")
                sc.isVideoRecording = False
                sc.isAudioRecording = False
                msg="Video recording failed. Requested resolution too high "
                flash(msg)
        else:
            msg = "Error in " + sc.errorSource + ": " + sc.error
            flash(msg)
            if sc.error2:
                flash(sc.error2)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/stop_recording", methods=("GET", "POST"))
@login_required
def stop_recording():
    logger.debug("Thread %s: In stop_recording", get_ident())
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        logger.debug("Requesting video recording to stop")
        Camera().stopVideoRecording()
        sc.isVideoRecording = False
        sc.isAudioRecording = False
        #sleep a little bit to avoid race condition with restoreLiveStream in video thread
        time.sleep(2)
        msg="Video recording stopped"
        flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

def generateHistogram(sc:ServerConfig):
    """ Generate a histogram for the specified image
    """
    logger.debug("In generateHistogram ")
    import cv2
    import numpy as np
    from matplotlib import pyplot as plt

    source = sc.photoRoot + "/" + sc.displayPhoto
    destPath = sc.photoRoot + "/" + sc.cameraHistogramSubPath
    if not os.path.exists(destPath):
        os.makedirs(destPath)
        logger.debug("generateHistogram - Created directory %s", destPath)
    file = sc.displayFile
    if not file.endswith(".jpg"):
        file = file[:len(file)-4] + ".jpg"
    dest = destPath + "/" + file
    try:
        plt.figure()    
        img = cv2.imread(source)
        color = ('b','g','r')
        for i,col in enumerate(color):
            histr = cv2.calcHist([img],[i],None,[256],[0,256],accumulate = False)
            plt.plot(histr,color = col)
            plt.xlim([0,256])
        plt.savefig(dest)
        sc.displayHistogram = sc.cameraHistogramSubPath + "/" + file
        logger.debug("In generateHistogram - Histogram success: %s", sc.displayHistogram)
    except Exception as e:
        sc.displayHistogram = "histogramfailed.jpg"
        logger.error("Histogram generation error: %s", e)

@bp.route("/show_histogram", methods=("GET", "POST"))
@login_required
def show_histogram():
    logger.debug("In show_histogram")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        if sc.useHistograms:
            if sc.displayHistogram is None:
                if sc.displayPhoto:
                    generateHistogram(sc)
            sc.displayContent = "hist"
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/show_metadata", methods=("GET", "POST"))
@login_required
def show_metadata():
    logger.debug("In show_metadata")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayContent = "meta"
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        
