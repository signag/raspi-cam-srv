from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.timelapseCfg import TimelapseCfg
from raspiCamSrv.timelapseCfg import Series
from raspiCamSrv.camera_pi import Camera
import os
import copy
from pathlib import Path
from datetime import datetime
from datetime import timedelta

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("timelapse", __name__)

logger = logging.getLogger(__name__)

def seriesLog(ser: Series, t:datetime, txt: str ):
    """ Append a log entry to the series log file
        ser:    Series
        t:      datetime
        txt:    Log text
    """
    f = open(ser.logFile, "a")
    ts = t.strftime("%Y-%m-%d %H:%M:%S.%f")
    f.write(ts + " | " + ser.status + "\t| " + txt + "\n")
    f.close()

@bp.route("/timelapse")
@login_required
def main():
    g.hostname = request.host
    # Although not directly needed here, the camara needs to be initialized
    # in order to load the camera-specific parameters into configuration
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/new_series", methods=("GET", "POST"))
@login_required
def new_series():
    logger.debug("In new_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
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
            try:
                Path(ser.logFile).touch()
                Path(ser.cfgFile).touch()
                logger.debug("ser.logFile created: %s", ser.logFile)
                logger.debug("ser.cfgFile created: %s", ser.cfgFile)
            except Exception:
                serOK = False
                msg = "Unable to create .log or .cfg File: " + ser.logFile
                flash(msg)
        if serOK:
            dt = datetime.now()
            dt = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
            ser.start = dt
            ser.end = ser.start
            ser.interval = 1.0
            ser.nrShots = 1
            ser.nextStatus("create")
            ser.persist()
            tl.appendSeries(ser)
            logger.debug("Series appended: %s", ser.name)
            tl.curSeries = ser
            logger.debug("Current series set to: %s", ser.name)
            sr=tl.curSeries
            
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/select_series", methods=("GET", "POST"))
@login_required
def select_series():
    logger.debug("In select_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        serName = request.form["selectseries"]
        logger.debug("selected series: %s", serName)
        for ser in tl.tlSeries:
            if ser.name == serName:
                tl.curSeries = ser
                break
        sr = tl.curSeries
        logger.debug("current series set to: %s", tl.curSeries.name)
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/start_series", methods=("GET", "POST"))
@login_required
def start_series():
    logger.debug("In start_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        if sr.status == "READY" or sr.status == "PAUSED":
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
        
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/pause_series", methods=("GET", "POST"))
@login_required
def pause_series():
    logger.debug("In pause_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sr.nextStatus("pause")
        sr.persist()
        Camera.stopTimelapseSeries()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/finish_series", methods=("GET", "POST"))
@login_required
def finish_series():
    logger.debug("In finish_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        Camera.stopTimelapseSeries()
        sr.nextStatus("finish")
        dt = datetime.now()
        dt = datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
        sr.ended = dt
        sr.persist()
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/continue_series", methods=("GET", "POST"))
@login_required
def continue_series():
    logger.debug("In continue_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sr.nextStatus("continue")
        sr.persist()
        Camera.startTimelapseSeries(sr)
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/remove_series", methods=("GET", "POST"))
@login_required
def remove_series():
    logger.debug("In remove_series")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        nam = sr.name
        path = sr.path
        tl.removeCurrentSeries()
        sr = tl.curSeries
        msg = "Timelapse series " + nam + " removed. Path: " + path
        flash(msg)
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/series_properties", methods=("GET", "POST"))
@login_required
def series_properties():
    logger.debug("In series_properties")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        serOK = True
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
            sertype = request.form["imgtype"]
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
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/attach_camera_cfg", methods=("GET", "POST"))
@login_required
def attach_camera_cfg():
    logger.debug("In attach_camera_cfg")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
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
        
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/activate_camera_cfg", methods=("GET", "POST"))
@login_required
def activate_camera_cfg():
    logger.debug("In activate_camera_cfg")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
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
        
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/show_preview", methods=("GET", "POST"))
@login_required
def show_preview():
    logger.debug("In show_preview")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sr.showPreview = True
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)

@bp.route("/hide_preview", methods=("GET", "POST"))
@login_required
def hide_preview():
    logger.debug("In hide_preview")
    g.hostname = request.host
    cam = Camera().cam
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tl = TimelapseCfg()
    sr = tl.curSeries
    sc.curMenu = "timelapse"
    if request.method == "POST":
        sr.showPreview = False
    return render_template("timelapse/main.html", sc=sc, tl=tl, sr=sr)
