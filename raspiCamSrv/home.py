from flask import current_app, Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.auth import login_required
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from libcamera import controls
import os
import datetime
import time
import logging

bp = Blueprint("home", __name__)

logger = logging.getLogger(__name__)

@bp.route("/")
@login_required
def index():
    logger.info("In index")
    cam = Camera()
    logger.info("Camera instatntiated")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    logger.info("cp.hasFocus is %s", cp.hasFocus)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

def gen(camera):
    """Video streaming generator function."""
    logger.debug("In gen")
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()
        l = len(frame)
        logger.debug("Got frame of length %s", l)
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/video_feed")
@login_required
def video_feed():
    logger.debug("In video_feed")
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/focus_control", methods=("GET", "POST"))
@login_required
def focus_control():
    logger.info("In focus_control")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "focus"
    if request.method == "POST":
        if cp.hasFocus:
            afMode = int(request.form["afmode"])
            cc.afMode = afMode
            logger.info("afMode is %s", afMode)

            fDist = float(request.form["fdist"])
            logger.info("fDist is %s", fDist)
            cc.focalDistance = fDist
            lenspos = cc.lensePosition
            logger.info("lensePosition is %s", lenspos)

            afMetering = int(request.form["afmetering"])
            logger.info("afMetering is %s", afMetering)
            cc.afMetering = afMetering

            afPause = int(request.form["afpause"])
            logger.info("afPause is %s", afPause)
            cc.afPause = afPause

            afRange = int(request.form["afrange"])
            logger.info("afRange is %s", afRange)
            cc.afRange = afRange

            afSpeed = int(request.form["afspeed"])
            logger.info("afSpeed is %s", afSpeed)
            cc.afSpeed = afSpeed
            
            Camera().cam.set_controls({
                "AfMode": afMode, 
                "AfMetering": afMetering, 
                "AfPause": afPause, 
                "AfRange": afRange, 
                "AfSpeed": afSpeed, 
                "LensPosition": lenspos
            })
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
    
@bp.route("/trigger_autofocus", methods=("GET", "POST"))
@login_required
def trigger_autofocus():
    logger.debug("In trigger_autofocus")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "focus"
    if request.method == "POST":
        if cp.hasFocus:
            if cc.afMode == controls.AfModeEnum.Auto:
                success = Camera().cam.autofocus_cycle()
                if success:
                    msg = "Autofocus successful"
                else:
                    msg = "Autofocus not successful"
            else:
                msg="ERROR: Autofocus Mode must be set to 'Auto'!"
            flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
    
@bp.route("/set_zoom", methods=("GET", "POST"))
@login_required
def set_zoom():
    logger.info("In set_zoom")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int(request.form["zoomfactorstep"])
        sc.zoomFactorStep = step
        logger.info("sc.zoomFactorStep set to %s", step)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
    
@bp.route("/zoom_in", methods=("GET", "POST"))
@login_required
def zoom_in():
    logger.info("In zoom_in")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        logger.info("ScalerCrop old: %s", cc.scalerCrop)
        xCenter = int((cc.scalerCrop[0] + cc.scalerCrop[2])/2)
        yCenter = int((cc.scalerCrop[1] + cc.scalerCrop[3])/2)
        zfNext = sc.zoomFactor - sc.zoomFactorStep
        if zfNext < sc.zoomFactorStep:
            msg="WARNING: Minimum zoom factor reached!"
            flash(msg)
            zfNext = sc.zoomFactorStep
        width = int(cp.pixelArraySize[0] * zfNext / 100)
        height = int(cp.pixelArraySize[1] * zfNext / 100)
        sccrop = (int(xCenter - width/2), int(yCenter - height/2), width, height)
        sc.zoomFactor = zfNext
        cc.scalerCrop = sccrop
        logger.info("ScalerCrop new: %s", cc.scalerCrop)
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
    
@bp.route("/zoom_out", methods=("GET", "POST"))
@login_required
def zoom_out():
    logger.debug("In zoom_out")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        xCenter = int((cc.scalerCrop[0] + cc.scalerCrop[2])/2)
        yCenter = int((cc.scalerCrop[1] + cc.scalerCrop[3])/2)
        zfNext = sc.zoomFactor + sc.zoomFactorStep
        if zfNext >= 100:
            zfNext = 100
            width = cp.pixelArraySize[0]
            height = cp.pixelArraySize[1]
            sccrop = (0, 0, width, height)
        else:
            width = int(cp.pixelArraySize[0] * zfNext / 100)
            height = int(cp.pixelArraySize[1] * zfNext / 100)
            if width > cp.pixelArraySize[0]:
                width = cp.pixelArraySize[0]
                xOffset = 0
            else:
                xOffset = int(xCenter - width/2)
                if xOffset < 0:
                    xOffset = 0
            if height > cp.pixelArraySize[1]:
                height = cp.pixelArraySize[1]
                yOffset = 0
            else:
                yOffset = int(yCenter - height/2)
                if yOffset < 0:
                    yOffset = 0
            sccrop = (xOffset, yOffset, width, height)
        sc.zoomFactor = zfNext
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
    
@bp.route("/zoom_full", methods=("GET", "POST"))
@login_required
def zoom_full():
    logger.debug("In zoom_full")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        sc.zoomFactor = 100
        sccrop = (0, 0, cp.pixelArraySize[0], cp.pixelArraySize[1])
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
    
@bp.route("/pan_up", methods=("GET", "POST"))
@login_required
def pan_up():
    logger.debug("In pan_up")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((cp.pixelArraySize[1] * sc.zoomFactorStep)/100)
        yOffset = cc.scalerCrop[1] + step
        if yOffset + cc.scalerCrop[3] > cp.pixelArraySize[1]:
            yOffset = cp.pixelArraySize[1] - cc.scalerCrop[3]
            msg="WARNING: Upper border reached!"
            flash(msg)
        sccrop = (cc.scalerCrop[0], yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

@bp.route("/pan_left", methods=("GET", "POST"))
@login_required
def pan_left():
    logger.debug("In pan_left")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((cp.pixelArraySize[1] * sc.zoomFactorStep)/100)
        xOffset = cc.scalerCrop[0] - step
        if xOffset < 0:
            xOffset = 0
            msg="WARNING: Left border reached!"
            flash(msg)
        sccrop = (xOffset, cc.scalerCrop[1], cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

@bp.route("/pan_center", methods=("GET", "POST"))
@login_required
def pan_center():
    logger.debug("In pan_center")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        xOffset = int((cp.pixelArraySize[0] - cc.scalerCrop[2])/2)
        if xOffset < 0:
            xOffset = 0
        yOffset = int((cp.pixelArraySize[1] - cc.scalerCrop[3])/2)
        if yOffset < 0:
            yOffset = 0
        sccrop = (xOffset, yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

@bp.route("/pan_right", methods=("GET", "POST"))
@login_required
def pan_right():
    logger.debug("In pan_right")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((cp.pixelArraySize[1] * sc.zoomFactorStep)/100)
        xOffset = cc.scalerCrop[0] + step
        if xOffset + cc.scalerCrop[2] > cp.pixelArraySize[0]:
            xOffset = cp.pixelArraySize[0] - cc.scalerCrop[2]
            msg="WARNING: Right border reached!"
            flash(msg)
        sccrop = (xOffset, cc.scalerCrop[1], cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

@bp.route("/pan_down", methods=("GET", "POST"))
@login_required
def pan_down():
    logger.debug("In pan_down")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int((cp.pixelArraySize[1] * sc.zoomFactorStep)/100)
        yOffset = cc.scalerCrop[1] - step
        if yOffset < 0:
            yOffset = 0
            msg="WARNING: Bottom border reached!"
            flash(msg)
        sccrop = (cc.scalerCrop[0], yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        Camera().cam.set_controls({"ScalerCrop": sccrop})
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

@bp.route("/ae_control", methods=("GET", "POST"))
@login_required
def ae_control():
    logger.info("In ae_control")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "autoexposure"
    if request.method == "POST":
        aeConstraintMode = int(request.form["aeconstraintmode"])
        cc.aeConstraintMode = aeConstraintMode

        aeEnableForm = request.form.get("aeenable")
        logger.info("aeEnableForm: %s", aeEnableForm)
        if aeEnableForm is None:
            aeEnable = False
        else:
            aeEnable = True
        cc.aeEnable = aeEnable

        aeExposureMode = int(request.form["aeexposuremode"])
        cc.aeExposureMode = aeExposureMode

        aeMeteringMode = int(request.form["aemeteringmode"])
        cc.aeMeteringMode = aeMeteringMode

        aeFlickerMode = int(request.form["aeflickermode"])
        cc.aeFlickerMode = aeFlickerMode

        aeFlickerPeriod = int(request.form["aeflickerperiod"])
        cc.aeFlickerPeriod = aeFlickerPeriod
        
        Camera().cam.set_controls({
            "AeConstraintMode": aeConstraintMode, 
            "AeEnable": aeEnable, 
            "AeExposureMode": aeExposureMode, 
            "AeMeteringMode": aeMeteringMode, 
            "AeFlickerMode": aeFlickerMode, 
            "AeFlickerPeriod": aeFlickerPeriod
        })
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)

@bp.route("/exposure_control", methods=("GET", "POST"))
@login_required
def exposure_control():
    logger.info("In exposure_control")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "exposure"
    if request.method == "POST":
        analogueGain = float(request.form["analoguegain"])
        cc.analogueGain = analogueGain
        
        colourGainRed = float(request.form["colourgainred"])
        colourGainBlue = float(request.form["colourgainblue"])
        colourGains = (colourGainRed, colourGainBlue)
        cc.colourGains = colourGains

        exposureTimeSec = float(request.form["exposuretimesec"])
        cc.exposureTimeSec = exposureTimeSec
        exposureTime = cc.exposureTime

        exposureValue = float(request.form["exposurevalue"])
        cc.aeMeteringMode = exposureValue

        frameDurationLimitMax = int(request.form["framedurationlimitmax"])
        frameDurationLimitMin = int(request.form["framedurationlimitmin"])
        frameDurationLimits = (frameDurationLimitMax, frameDurationLimitMin)
        cc.frameDurationLimits = frameDurationLimits

        hdrMode = int(request.form["hdrmode"])
        cc.hdrMode = hdrMode
        
        Camera().cam.set_controls({
            "AnalogueGain": analogueGain, 
            "ColourGains": colourGains, 
            "ExposureTime": exposureTime, 
            "ExposureValue": exposureValue, 
            "FrameDurationLimits": frameDurationLimits, 
            "HdrMode": hdrMode
        })
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)
        
@bp.route("/take_image", methods=("GET", "POST"))
@login_required
def take_image():
    logger.debug("In take_image")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        path = request.form["filepath"]
        if not os.path.exists(path):
            path = current_app.instance_path
        filename = request.form["filename"]
        if len(filename) == 0:
            timeImg = datetime.datetime.now()
            filename = "image_" + timeImg.strftime("%Y%m%d_%H%M%S") + ".jpeg"
        fp = path + "/" + filename
        logger.debug("Saving image to %s", fp)
        Camera().takeImage(fp)
        msg="Image saved as " + fp
        flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp, ip=current_app.instance_path)        
