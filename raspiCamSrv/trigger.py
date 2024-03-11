from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.motionDetector import MotionDetector
from raspiCamSrv.version import version
from datetime import datetime
from datetime import timedelta

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("trigger", __name__)

logger = logging.getLogger(__name__)

@bp.route("/trigger")
@login_required
def trigger():
    logger.debug("In trigger")
    cam = Camera().cam
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    if tc.evStart == None:
        tc.evStart = datetime.now()
    if tc.calStart == None:
        tc.calStart = datetime.now()
    sc.curMenu = "trigger"
    #logger.debug("event list: %s", tc.eventList)
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/control", methods=("GET", "POST"))
@login_required
def control():
    logger.debug("In control")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcontrol"
    if request.method == "POST":
        err = None
        if request.form.get("triggerbymotion") is None:
            tc.triggeredByMotion = False
        else:
            tc.triggeredByMotion = True
        if request.form.get("triggervideo") is None:
            tc.actionVideo = False
        else:
            tc.actionVideo = True
        if request.form.get("triggerphoto") is None:
            tc.actionPhoto = False
        else:
            tc.actionPhoto = True
        if tc.actionVideo:
            if not tc.actionPhoto:
                err = "Together with videos, you must capture at least one photo."
                tc.actionPhoto = True
        for key, value in tc.operationWeekdays.items():
            if request.form.get("opweekday" + key) is None:
                tc.operationWeekdays[key] = False
            else:
                tc.operationWeekdays[key] = True
        opStartStr = request.form["opstart"]
        tc.operationStartStr = opStartStr
        opEndStr = request.form["opend"]
        tc.operationEndStr = opEndStr
        if request.form.get("opautostart") is None:
            tc.operationAutoStart = False
        else:
            tc.operationAutoStart = True
        detectDelay = int(request.form["opdelay"])
        tc.detectionDelaySec = detectDelay
        detectPause = int(request.form["oppause"])
        tc.detectionPauseSec = detectPause
        retPeriod = int(request.form["retentionperiod"])
        tc.retentionPeriod = retPeriod
        if err:
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/motion", methods=("GET", "POST"))
@login_required
def motion():
    logger.debug("In motion")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    logger.debug("tc.motionDetectAlgo: %s", tc.motionDetectAlgo)
    sc.lastTriggerTab = "trgmotion"
    if request.method == "POST":
        algo = int(request.form["motiondetectionalgo"])
        logger.debug("algo: %s", algo)
        thrsh = int(request.form["msdthreshold"])
        tc.motionDetectAlgo = algo
        tc.msdThreshold = thrsh
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/action", methods=("GET", "POST"))
@login_required
def action():
    logger.debug("In action")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    logger.debug("tc.actionVR: %s", tc.actionVR)
    sc.lastTriggerTab = "trgaction"
    if request.method == "POST":
        err = None
        vr = int(request.form["actionvr"])
        logger.debug("vr: %s", vr)
        if vr == 1:
            tc.actionVR = vr
        else:
            err = "Circular output is currently not supported"
        cbs = int(request.form["actioncircsize"])
        tc.actionCircSize = cbs
        dur = int(request.form["actionvideoduration"])
        tc.actionVideoDuration = dur
        pb = int(request.form["actionphotoburst"])
        tc.actionPhotoBurst = pb
        pbd = int(request.form["actionphotoburstdelaysec"])
        tc.actionPhotoBurstDelaySec = pbd
        if err:
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/start_triggered_capture", methods=("GET", "POST"))
@login_required
def start_triggered_capture():
    logger.debug("In start_triggered_capture")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcontrol"
    if request.method == "POST":
        err = None
        if tc.triggeredByMotion:
            MotionDetector().startMotionDetection()
            sc.isTriggerRecording = True
            logger.debug("In motion detection started")
        else:
            err = "There is no trigger activated"
        if err:
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/stop_triggered_capture", methods=("GET", "POST"))
@login_required
def stop_triggered_capture():
    logger.debug("In stop_triggered_capture")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcontrol"
    if request.method == "POST":
        if sc.isTriggerRecording:
            MotionDetector().stopMotionDetection()
            sc.isTriggerRecording = False
            logger.debug("In motion - detection stopped")
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/prev_month", methods=("GET", "POST"))
@login_required
def prev_month():
    logger.debug("In prev_month")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(hours=-168)
    tc.evStartMidnight()
    return redirect(url_for("trigger.trigger"))

@bp.route("/prev_day", methods=("GET", "POST"))
@login_required
def prev_day():
    logger.debug("In prev_day")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(hours=-24)
    tc.evStartMidnight()
    return redirect(url_for("trigger.trigger"))

@bp.route("/set_date", methods=("GET", "POST"))
@login_required
def set_date():
    logger.debug("In set_date")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    if request.method == "POST":
        tc.evStartDateStr = request.form.get("evstartdate")
        tc.evStartMidnight()
    return redirect(url_for("trigger.trigger"))

@bp.route("/next_day", methods=("GET", "POST"))
@login_required
def next_day():
    logger.debug("In next_day")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(hours=24)
    tc.evStartMidnight()
    return redirect(url_for("trigger.trigger"))

@bp.route("/next_month", methods=("GET", "POST"))
@login_required
def next_month():
    logger.debug("In next_month")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(hours=168)
    tc.evStartMidnight()
    return redirect(url_for("trigger.trigger"))

@bp.route("/prev_hor", methods=("GET", "POST"))
@login_required
def prev_hor():
    logger.debug("In prev_hor")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(hours=-1)
    return redirect(url_for("trigger.trigger"))

@bp.route("/prev_quarter", methods=("GET", "POST"))
@login_required
def prev_quarter():
    logger.debug("In prev_quarter")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(minutes=-15)
    return redirect(url_for("trigger.trigger"))

@bp.route("/set_time", methods=("GET", "POST"))
@login_required
def set_time():
    logger.debug("In set_time")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    if request.method == "POST":
        tc.evStartTimeStr = request.form.get("evstarttime")
    return redirect(url_for("trigger.trigger"))

@bp.route("/next_quarter", methods=("GET", "POST"))
@login_required
def next_quarter():
    logger.debug("In next_quarter")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(minutes=15)
    return redirect(url_for("trigger.trigger"))

@bp.route("/next_hour", methods=("GET", "POST"))
@login_required
def next_hour():
    logger.debug("In next_hour")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = tc.evStart + timedelta(hours=1)
    return redirect(url_for("trigger.trigger"))

@bp.route("/events_now", methods=("GET", "POST"))
@login_required
def events_now():
    logger.debug("In events_now")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    tc.evStart = datetime.now()
    return redirect(url_for("trigger.trigger"))

@bp.route("/event_include_video", methods=("GET", "POST"))
@login_required
def event_include_video():
    logger.debug("In event_include_video")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    if request.method == "POST":
        if request.form.get("evincludevideo") is None:
            tc.evIncludeVideo = False
        else:
            tc.evIncludeVideo = True
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/event_include_photo", methods=("GET", "POST"))
@login_required
def event_include_photo():
    logger.debug("In event_include_photo")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    if request.method == "POST":
        if request.form.get("evincludephoto") is None:
            tc.evIncludePhoto = False
        else:
            tc.evIncludePhoto = True
    return render_template("trigger/trigger.html", tc=tc, sc=sc)

@bp.route("/do_refresh", methods=("GET", "POST"))
@login_required
def do_refresh():
    logger.debug("In do_refresh")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgevents"
    if request.method == "POST":
        pass
    return redirect(url_for("trigger.trigger"))

@bp.route("/prev_cal_month", methods=("GET", "POST"))
@login_required
def prev_cal_month():
    logger.debug("In prev_cal_month")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    tc.calStart = tc.calStart + timedelta(hours=-24)
    return redirect(url_for("trigger.trigger"))

@bp.route("/set_cal_month", methods=("GET", "POST"))
@login_required
def set_cal_month():
    logger.debug("In set_cal_month")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    if request.method == "POST":
        tc.calStartDateStr = request.form.get("setcalmonth")
    return redirect(url_for("trigger.trigger"))

@bp.route("/next_cal_month", methods=("GET", "POST"))
@login_required
def next_cal_month():
    logger.debug("In next_cal_month")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    tc.calStart = tc.calStart + timedelta(hours=750)
    return redirect(url_for("trigger.trigger"))

@bp.route("/calendar_now", methods=("GET", "POST"))
@login_required
def calendar_now():
    logger.debug("In calendar_now")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    tc.calStart = datetime.now()
    return redirect(url_for("trigger.trigger"))

@bp.route("/do_refresh_calendar", methods=("GET", "POST"))
@login_required
def do_refresh_calendar():
    logger.debug("In do_refresh_calendar")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    if request.method == "POST":
        pass
    return redirect(url_for("trigger.trigger"))

@bp.route("/calendar_goto", methods=("GET", "POST"))
@login_required
def calendar_goto():
    logger.debug("In calendar_goto")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    if request.method == "POST":
        day = request.form.get("selectedday")
        logger.debug("selected day: %s", day)
        tc.evStartDateStr = day
        tc.evStartTimeStr = "00:00:00"
        logger.debug("evStart: %s", tc.evStart)
        sc.lastTriggerTab = "trgevents"
    return redirect(url_for("trigger.trigger"))

@bp.route("/do_cleanup", methods=("GET", "POST"))
@login_required
def do_cleanup():
    logger.debug("In do_cleanup")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcalendar"
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "You need to stop trigger recording before cleanup!"
        if not err:
            try:
                tc.cleanupEvents()
                err = "Cleanup successfull"
            except Exception as e:
                err = "Cleanup error: " + str(e)
        flash(err)
    return redirect(url_for("trigger.trigger"))
