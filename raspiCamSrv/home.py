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
    g.hostname = request.host
    cam = Camera()
    logger.info("Camera instantiated")
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "live"
    logger.info("cp.hasFocus is %s", cp.hasFocus)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

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

@bp.route("/photos/<photo>")
@login_required
def displayImage(photo: str):
    logger.info("In displayImage")
    logger.info("photo=%s", photo)
    logger.info("current_app.root_path=%s", current_app.root_path)
    fp = current_app.root_path + "/photos/" + photo
    logger.info("fp = %s", fp)
    return Response(fp, mimetype='image/jpg')

@bp.route("/focus_control", methods=("GET", "POST"))
@login_required
def focus_control():
    logger.info("In focus_control")
    g.hostname = request.host
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
            else:
                cc.include_afWindows = True
                afWindowsStr = request.form["afwindows"]
                cc.afWindowsStr = afWindowsStr
                ctrls["AfWindows"] = cc.afWindows

            Camera().applyControls(cfg.liveViewConfig)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/trigger_autofocus", methods=("GET", "POST"))
@login_required
def trigger_autofocus():
    logger.debug("In trigger_autofocus")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "focus"
    if request.method == "POST":
        if cp.hasFocus:
            if cc.afMode == controls.AfModeEnum.Auto:
                Camera().applyControlsForAfCycle()
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
                    msg = "Autofocus not successful"
            else:
                msg="ERROR: Autofocus Mode must be set to 'Auto'!"
            flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/set_zoom", methods=("GET", "POST"))
@login_required
def set_zoom():
    logger.info("In set_zoom")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        step = int(request.form["zoomfactorstep"])
        sc.zoomFactorStep = step
        logger.info("sc.zoomFactorStep set to %s", step)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_in", methods=("GET", "POST"))
@login_required
def zoom_in():
    logger.info("In zoom_in")
    g.hostname = request.host
    cfg = CameraCfg()
    logger.info("cfg.liveViewConfig.controls=%s",cfg.liveViewConfig.controls)
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
        if zfNext < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        logger.info("ScalerCrop new: %s", cc.scalerCrop)
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_out", methods=("GET", "POST"))
@login_required
def zoom_out():
    logger.debug("In zoom_out")
    g.hostname = request.host
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
        if zfNext < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/zoom_full", methods=("GET", "POST"))
@login_required
def zoom_full():
    logger.debug("In zoom_full")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "zoom"
    if request.method == "POST":
        sc.zoomFactor = 100
        sccrop = (0, 0, cp.pixelArraySize[0], cp.pixelArraySize[1])
        cc.scalerCrop = sccrop
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
        cc.include_scalerCrop = False
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_up", methods=("GET", "POST"))
@login_required
def pan_up():
    logger.debug("In pan_up")
    g.hostname = request.host
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
            msg="WARNING: Upper border reached!"
            flash(msg)
        sccrop = (cc.scalerCrop[0], yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        if sc.zoomFactor < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_left", methods=("GET", "POST"))
@login_required
def pan_left():
    logger.debug("In pan_left")
    g.hostname = request.host
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
        if sc.zoomFactor < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_center", methods=("GET", "POST"))
@login_required
def pan_center():
    logger.debug("In pan_center")
    g.hostname = request.host
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
        if sc.zoomFactor < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/pan_right", methods=("GET", "POST"))
@login_required
def pan_right():
    logger.debug("In pan_right")
    g.hostname = request.host
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
        if sc.zoomFactor < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
    
@bp.route("/pan_down", methods=("GET", "POST"))
@login_required
def pan_down():
    logger.debug("In pan_down")
    g.hostname = request.host
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
            msg="WARNING: bottom border reached!"
            flash(msg)
        sccrop = (cc.scalerCrop[0], yOffset, cc.scalerCrop[2], cc.scalerCrop[3])
        cc.scalerCrop = sccrop
        if sc.zoomFactor < 100:
            cc.include_scalerCrop = True
        else:
            cc.include_scalerCrop = False
        Camera().applyControls(cfg.liveViewConfig)
        time.sleep(0.5)
        metadata = Camera().getMetaData()
        sc.scalerCropLiveView = metadata["ScalerCrop"]
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/ae_control", methods=("GET", "POST"))
@login_required
def ae_control():
    logger.info("In ae_control")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.lastLiveTab = "autoexposure"
    if request.method == "POST":
        if request.form.get("include_aeconstraintmode") is None:
            cc.include_aeConstraintMode = False
            logger.info("AeConstraintMode excluded")
        else:
            logger.info("AeConstraintMode included")
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
            logger.info("AeMeteringMode excluded")
        else:
            logger.info("AeMeteringMode included")
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

        Camera().applyControls(cfg.liveViewConfig)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/exposure_control", methods=("GET", "POST"))
@login_required
def exposure_control():
    logger.info("In exposure_control")
    g.hostname = request.host
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

        Camera().applyControls(cfg.liveViewConfig)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)

@bp.route("/image_control", methods=("GET", "POST"))
@login_required
def image_control():
    logger.info("In image_control")
    g.hostname = request.host
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

        Camera().applyControls(cfg.liveViewConfig)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
        
@bp.route("/meta_clear", methods=("GET", "POST"))
@login_required
def meta_clear():
    logger.debug("In meta_clear")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayMeta = None
        sc.displayPhoto = None
        sc.displayMetaFirst = 0
        sc.displayMetaLast = 999
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)
        
@bp.route("/meta_prev", methods=("GET", "POST"))
@login_required
def meta_prev():
    logger.debug("In meta_prev")
    g.hostname = request.host
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
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferAdd()
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
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/photoBuffer_prev", methods=("GET", "POST"))
@login_required
def photoBuffer_prev():
    logger.debug("In photoBuffer_prev")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferPrev()
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/photoBuffer_next", methods=("GET", "POST"))
@login_required
def photoBuffer_next():
    logger.debug("In photoBuffer_next")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        sc.displayBufferNext()
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/show_photo", methods=("GET", "POST"))
@login_required
def show_photo():
    logger.debug("In show_photo")
    g.hostname = request.host
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
    logger.debug("In take_photo")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        path =sc.photoPath
        timeImg = datetime.datetime.now()
        filename = "photo_" + timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        fp = path + "/" + filename
        logger.debug("Saving image to %s", fp)
        Camera().takeImage(path, filename)
        msg="Image saved as " + fp
        flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/take_raw_photo", methods=("GET", "POST"))
@login_required
def take_raw_photo():
    logger.debug("In take_raw_photo")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        path =sc.photoPath
        timeImg = datetime.datetime.now()
        filename = "photo_" + timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.photoType
        filenameRaw = "photo_" + timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.rawPhotoType
        fp = path + "/" + filenameRaw
        logger.debug("Saving raw image to %s", fp)
        Camera().takeRawImage(path, filenameRaw, filename)
        msg="Image saved as " + fp
        flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/record_video", methods=("GET", "POST"))
@login_required
def record_video():
    logger.info("In record_video")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        path =sc.photoPath
        timeImg = datetime.datetime.now()
        filename = "video_" + timeImg.strftime("%Y%m%d_%H%M%S") + "." + sc.videoType
        fp = path + "/" + filename
        logger.info("Saving video as %s", fp)
        logger.info("Recording a video")
        Camera.recordVideo(fp)
        time.sleep(4)
        # Check whether vido is being recorded
        if Camera.isVideoRecording():
            logger.info("Video recording started")
            sc.isVideoRecording = True
            msg="Video saved as " + fp
            flash(msg)
        else:
            logger.info("Video recording did not start")
            sc.isVideoRecording = False
            msg="Video recording failed. Requested resolution too high "
            flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        

@bp.route("/stop_recording", methods=("GET", "POST"))
@login_required
def stop_recording():
    logger.info("In stop_recording")
    g.hostname = request.host
    cfg = CameraCfg()
    cc = cfg.controls
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    if request.method == "POST":
        logger.info("Requesting video recording to stop")
        Camera().stopVideoRecording()
        sc.isVideoRecording = False
        msg="Video recording stopped"
        flash(msg)
    return render_template("home/index.html", cc=cc, sc=sc, cp=cp)        
