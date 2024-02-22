from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.timelapseCfg import TimelapseCfg
from raspiCamSrv.timelapseCfg import Series
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.version import version
import os
import copy
from pathlib import Path
from datetime import datetime
from datetime import timedelta

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("timelapse", __name__)

logger = logging.getLogger(__name__)

@bp.route("/timelapse")
@login_required
def main():
    g.hostname = request.host
    g.version = version
    # Although not directly needed here, the camara needs to be initialized
    # in order to load the camera-specific parameters into configuration
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    sc.lastTimelapseTab = "series"
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/new_series", methods=("GET", "POST"))
@login_required
def new_series():
    logger.debug("In new_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        seriesName = request.form["tlnewseries"]
        logger.debug("seriesName: %s", seriesName)
        if tl.nameExists(seriesName):
            msg = "Error: There is already a series with this name."
            flash(msg)
        else:
            ser = Series()
            ser.name = seriesName
            ser.path = tl.rootPath + "/" + ser.name
            serOK = True
            logger.debug("ser.path: %s", ser.path)
            try:
                os.makedirs(ser.path, exist_ok=False)
                logger.debug("ser.path created: %s", ser.path)
                if sc.useHistograms:
                    os.makedirs(ser.histogramPath, exist_ok=False)
            except FileExistsError:
                serOK = False
                msg = "A folder for this series name exists already: " + ser.path
                flash(msg)
            except OSError:
                serOK = False
                msg = "A folder with this name cannot be created: " + ser.path + " Choose a different name!"
                flash(msg)
            except Exception:
                serOK = False
                msg = "A folder with this name cannot be created: " + ser.path + " Choose a different name!"
                flash(msg)
        if serOK:
            ser.logFile = ser.path + "/" + ser.logFileName
            ser.cfgFile = ser.path + "/" + ser.cfgFileName
            ser.camFile = ser.path + "/" + ser.camFileName
            try:
                Path(ser.logFile).touch()
                Path(ser.cfgFile).touch()
                Path(ser.camFile).touch()
                logger.debug("ser.logFile created: %s", ser.logFile)
                logger.debug("ser.cfgFile created: %s", ser.cfgFile)
                logger.debug("ser.camFile created: %s", ser.camFile)
            except Exception:
                serOK = False
                msg = "Unable to create .log or .cfg or .cam File: " + ser.logFile
                flash(msg)
        if serOK:
            dt = datetime.now()
            dt = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
            ser.start = dt
            ser.end = ser.start
            ser.interval = 5.0
            ser.nrShots = 1
            ser.nextStatus("create")
            ser.persist()
            tl.appendSeries(ser)
            logger.debug("Series appended: %s", ser.name)
            tl.curSeries = ser
            logger.debug("Current series set to: %s", ser.name)
            sr=tl.curSeries
            
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/select_series", methods=("GET", "POST"))
@login_required
def select_series():
    logger.debug("In select_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        serName = request.form["selectseries"]
        logger.debug("selected series: %s", serName)
        for ser in tl.tlSeries:
            if ser.name == serName:
                tl.curSeries = ser
                break
        sr = tl.curSeries
        logger.debug("current series set to: %s", tl.curSeries.name)
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/start_series", methods=("GET", "POST"))
@login_required
def start_series():
    logger.debug("In start_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        if sr.status == "READY" or sr.status == "PAUSED":
            if sr.isExposureSeries:
                # For exposure series disable Auto and set fixed control parameter
                ctrl = cfg.controls
                ctrl.aeEnable = False
                ctrl.include_aeEnable = True
                ctrl.awbEnable = False
                ctrl.include_awbEnable = True
                if sr.isExpGainFix:
                    ctrl.include_analogueGain = True
                    ctrl.analogueGain = sr.expGainStart
                if sr.isExpExpTimeFix:
                    ctrl.include_exposureTime = True
                    ctrl.exposureTime = sr.expTimeStart
            if sr.isFocusStackingSeries:
                # For focus series, set Autofocus to manual
                ctrl = cfg.controls
                ctrl.afMode = 0
            # Ckeck whether series start is in the past
            dt = datetime.now() + timedelta(seconds=5)
            startnow = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
            startnow = startnow + timedelta(minutes=1)
            if sr.start < startnow:
                sr.start = startnow
                timedifSec = int(sr.interval * sr.nrShots)
                delta = timedelta(seconds=timedifSec)
                serEndRaw = sr.start + delta
                serEnd = datetime(year=serEndRaw.year, month=serEndRaw.month, day=serEndRaw.day, hour=serEndRaw.hour, minute=serEndRaw.minute)
                serEnd = serEnd + timedelta(minutes=1)
                sr.end = serEnd
            
            tlOK = True
            try:
                Camera.startTimelapseSeries(sr)
            except Exception as e:
                tlOK = False
                msg = "Error while starting Timelapse series " + str(e)
                flash(msg)
            if tlOK:
                sr.nextStatus("start")
                sr.persist()
        
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/pause_series", methods=("GET", "POST"))
@login_required
def pause_series():
    logger.debug("In pause_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        sr.nextStatus("pause")
        sr.persist()
        Camera.stopTimelapseSeries()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/finish_series", methods=("GET", "POST"))
@login_required
def finish_series():
    logger.debug("In finish_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        Camera.stopTimelapseSeries()
        sr.nextStatus("finish")
        dt = datetime.now()
        dt = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
        sr.ended = dt
        sr.persist()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/continue_series", methods=("GET", "POST"))
@login_required
def continue_series():
    logger.debug("In continue_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        sr.nextStatus("continue")
        sr.persist()
        Camera.startTimelapseSeries(sr)
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/remove_series", methods=("GET", "POST"))
@login_required
def remove_series():
    logger.debug("In remove_series")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        nam = sr.name
        path = sr.path
        tl.removeCurrentSeries()
        sr = tl.curSeries
        msg = "Timelapse series " + nam + " removed. Path: " + path
        flash(msg)
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/series_properties", methods=("GET", "POST"))
@login_required
def series_properties():
    logger.debug("In series_properties")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        serOK = True
        sertype = request.form["imgtype"]
        serStartFormIso = request.form["serstart"]
        sr.start = datetime.fromisoformat(serStartFormIso)
        serEndFormIso = request.form["serend"]
        serIntForm = float(request.form["serinterval"])
        serShtForm = int(request.form["sernrshots"])
        # Iso date from form does not include seconds, 
        # so we need to cut off the seconds from the stored series
        serEndOldIso = sr.endIso
        if len(serEndOldIso) > len(serEndFormIso):
            serEndOldIso = serEndOldIso[:len(serEndFormIso)]
        logger.debug("Series end Iso: old=%s form=%s", serEndOldIso, serEndFormIso)
        if serEndFormIso != serEndOldIso:
            # End time has been changed
            serEnd = datetime.fromisoformat(serEndFormIso)
            timedif = serEnd - sr.start
            timedifSec = timedif.total_seconds()
            if timedifSec <= 0:
                msg = "Series end must be later than series start!"
                flash(msg)
                serOK = False
            else:
                if serIntForm != sr.interval:
                    # Interval has been changed -> calculate nrShots
                    serInt = serIntForm
                    serNrShots = int(timedifSec / serInt)
                elif serShtForm != sr.nrShots:
                    # Nr shots has been changed -> calculate interval
                    serNrShots = serShtForm
                    serInt = int(10 * timedifSec / serNrShots) / 10
                else:
                    # Onlie series end has been changed -> keep interval and calculate nr shots
                    serInt = sr.interval
                    serNrShots = int(timedifSec / serInt)
        else:
            # Series end not changed -> calculate it from other params
            serInt = serIntForm
            serNrShots = serShtForm
            timedifSec = int(serInt * serNrShots)
            delta = timedelta(seconds=timedifSec)
            serEndRaw = sr.start + delta
            serEnd = datetime(year=serEndRaw.year, month=serEndRaw.month, day=serEndRaw.day, hour=serEndRaw.hour, minute=serEndRaw.minute)
            serEnd = serEnd + timedelta(minutes=1)
        if serOK:
            sr.type = sertype
            sr.end = serEnd
            sr.interval = serInt
            sr.nrShots = serNrShots
            sr.nextStatus("configure")
            sr.persist()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/attach_camera_cfg", methods=("GET", "POST"))
@login_required
def attach_camera_cfg():
    logger.debug("In attach_camera_cfg")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        sr = tl.curSeries
        if sr.type == "jpg":
            sr.cameraConfig = copy.deepcopy(cfg.photoConfig)
            msg = "Current 'Photo' configuration and Controls attached to Timelapse series."
        else:
            sr.cameraConfig = copy.deepcopy(cfg.rawConfig)
            msg = "Current 'Raw Photo' configuration and Controls attached to Timelapse series."
        sr.cameraControls = copy.deepcopy(cfg.controls)
        sr.persist()
        flash(msg)
        
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/activate_camera_cfg", methods=("GET", "POST"))
@login_required
def activate_camera_cfg():
    logger.debug("In activate_camera_cfg")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        sr = tl.curSeries
        if sr.cameraConfig:
            if sr.type == "jpg":
                cfg.photoConfig = copy.deepcopy(sr.cameraConfig)
                msg = "'Photo' configuration and Controls replaced with settings from Timelapse series."
            else:
                cfg.rawConfig = copy.deepcopy(sr.cameraConfig)
                msg = "'Raw Photo' configuration and Controls replaced with settings from Timelapse series."
            cfg.controls = copy.deepcopy(sr.cameraControls)
            Camera().applyControls(cfg.liveViewConfig)
            sr.persist()
            flash(msg)
        else:
            msg="The Timelapse series has no camera configuration attached."
            flash(msg)
        
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/show_preview", methods=("GET", "POST"))
@login_required
def show_preview():
    logger.debug("In show_preview")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        sr.showPreview = True
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

@bp.route("/hide_preview", methods=("GET", "POST"))
@login_required
def hide_preview():
    logger.debug("In hide_preview")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sc.lastTimelapseTab = "series"
        sr.showPreview = False
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

def calcExpSeries(start, stop, int):
    """ Iterate an Exposure Series and return number of shots and stop
    """
    if int == 0:
        fact = 2
    elif int == 1:
        fact = 2 ** (1.0 / 3)
    elif int == 2:
        fact = 4
    else:
        fact =  2
    v = start
    vv = v
    nrShot = 0
    while vv <= stop:
        v = vv
        nrShot += 1
        vv = vv * fact
    if v < stop:
        nrShot += 1
        v = v * fact
    return nrShot, v        

@bp.route("/expseries_properties", methods=("GET", "POST"))
@login_required
def expseries_properties():
    logger.debug("In expseries_properties")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        ok = True
        sc.lastTimelapseTab = "exposure"
        if request.form.get("isexposure") is None:
            sr.isExposureSeries = False
        else:
            msg = ""
            if sr.isFocusStackingSeries:
                ok = False
                msg = "The series is already marked as Focus Stack"
            else:
                sr.isExposureSeries = True
                if request.form.get("isexptimefix") is None:
                    sr.isExpExpTimeFix = False
                    if request.form.get("isexpgainfix") is None:
                        msg = "Select exactly one parameter as fix."
                        ok = False
                    else:
                        sr.isExpGainFix = True
                else:
                    sr.isExpExpTimeFix = True
                    if request.form.get("isexpgainfix") is None:
                        sr.isExpGainFix = False
                    else:
                        msg = "Select exactly one parameter as fix."
                        ok = False
            if ok:
                if sr.isExpGainFix:
                    expTimeStart = int(request.form["exptimestart"])
                    expTimeStop = int(request.form["exptimestop"])
                    expTimeStep = int(request.form["exptimestep"])
                    nrShots, expTimeStop = calcExpSeries(expTimeStart, expTimeStop, expTimeStep)
                    expGainFix = float(request.form["expgainstart"])
                    sr.nrShots = nrShots
                    sr.expTimeStart = expTimeStart
                    sr.expTimeStop = int(expTimeStop)
                    sr.expTimeStep = expTimeStep
                    sr.expGainStart = expGainFix
                    sr.expGainStop = expGainFix
                    sr.expGainStep = 0
                if sr.isExpExpTimeFix:
                    expGainStart = float(request.form["expgainstart"])
                    expGainStop = float(request.form["expgainstop"])
                    expGainStep = int(request.form["expgainstep"])
                    nrShots, expGainStop = calcExpSeries(expGainStart, expGainStop, expGainStep)
                    expTimeFix = int(request.form["exptimestart"])
                    sr.nrShots = nrShots
                    sr.expGainStart = expGainStart
                    sr.expGainStop = expGainStop
                    sr.expGainStep = expGainStep
                    sr.expTimeStart = expTimeFix
                    sr.expTimeStop = expTimeFix
                    sr.expGTimeStep = 0
            else:
                flash(msg)
        if ok:
            sr.nextStatus("configure")
            sr.persist()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)

def calcFocusSeries(start, stop, intv):
    """ Iterate an Exposure Series and return number of shots and stop
    """
    nrShot = int((stop - start) / intv) + 1
    v = start + (nrShot - 1) * intv
    if intv < 0:
        if v > stop:
            if v + intv > 0:
                nrShot += 1
    else:
        if v < stop:
            nrShot += 1
    v = start + (nrShot - 1) * intv
    v = round(v, 2)
    return nrShot, v        

@bp.route("/focusstack_properties", methods=("GET", "POST"))
@login_required
def focusstack_properties():
    logger.debug("In focusstack_properties")
    g.hostname = request.host
    g.version = version
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    if request.method == "POST":
        ok = True
        sc.lastTimelapseTab = "focusstack"
        if request.form.get("isfocusstack") is None:
            sr.isFocusStackingSeries = False
        else:
            msg = ""
            if sr.isExposureSeries:
                ok = False
                msg = "The series is already marked as Exposure Series!"
            else:
                focusStart = float(request.form["focaldiststart"])
                focusStop = float(request.form["focaldiststop"])
                focusStep = float(request.form["focaldiststep"])
                if focusStart <= 0.0:
                    msg = "The start value must be > 0!"
                    ok = False
                else:
                    if focusStop > focusStart:
                        if focusStep > 0.0:
                            pass
                        else:
                            msg = "If Stop > Start, Interval must be > 0!"
                            ok = False
                    elif focusStop == 0.0:
                        msg = "Stop must not be 0!"
                        ok = False
                    else:
                        if focusStep < 0.0:
                            pass
                        else:
                            msg = "If Stop < Start, Interval must be < 0!"
                            ok = False
            if ok:
                sr.isFocusStackingSeries = True
                nrShots, focusStop = calcFocusSeries(focusStart, focusStop, focusStep)
                sr.focalDistStart = focusStart
                sr.focalDistStop = focusStop
                sr.focalDistStep = focusStep
                sr.nrShots = nrShots
            else:
                flash(msg)
        if ok:
            sr.nextStatus("configure")
            sr.persist()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr, cp=cp)
