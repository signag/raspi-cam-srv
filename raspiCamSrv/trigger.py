from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, Trigger, Action, ServerConfig, TriggerConfig
from raspiCamSrv.motionDetector import MotionDetector
from raspiCamSrv.triggerHandler import TriggerHandler
from raspiCamSrv.version import version
from _thread import get_ident
from datetime import datetime
from datetime import timedelta
import ast
import copy

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
    tc = cfg.triggerConfig
    if tc.evStart == None:
        tc.evStart = datetime.now()
    if tc.calStart == None:
        tc.calStart = datetime.now()
    sc.curMenu = "trigger"
    tmp = {}
    #logger.debug("event list: %s", tc.eventList)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

@bp.route("/trgcontrol", methods=("GET", "POST"))
@login_required
def trgcontrol():
    logger.debug("In trgcontrol")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgcontrol"
    tmp = {}
    if request.method == "POST":
        err = None
        if request.form.get("triggerbymotion") is None:
            tc.triggeredByMotion = False
        else:
            tc.triggeredByMotion = True
        if request.form.get("triggerbyevents") is None:
            tc.triggeredByEvents = False
        else:
            tc.triggeredByEvents = True
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
        if request.form.get("triggernotify") is None:
            tc.actionNotify = False
        else:
            tc.actionNotify = True
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
        
        if tc.triggeredByEvents == True \
        and tc.triggeredByMotion == False:
            tc.actionVideo = False
            tc.actionPhoto = False
            tc.actionNotify = False
            err = "Actions have been deactivated because they are currently supported only in combination with Motion Detection"
        if err:
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

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
    tmp = {}
    if request.method == "POST":
        algo = int(request.form["motiondetectionalgo"])
        tc.motionDetectAlgo = algo
        if not request.form.get("msdthreshold") is None:
            msdThreshold = int(request.form["msdthreshold"])
            tc.msdThreshold = msdThreshold
        if not request.form.get("bboxthreshold") is None:
            bboxThreshold = int(request.form["bboxthreshold"])
            tc.bboxThreshold = bboxThreshold
        if not request.form.get("nmsthreshold") is None:
            nmsThreshold = float(request.form["nmsthreshold"])
            tc.nmsThreshold = nmsThreshold
        if not request.form.get("motionthreshold") is None:
            motionThreshold = int(request.form["motionthreshold"])
            tc.motionThreshold = motionThreshold
        if not request.form.get("backsubmodel") is None:
            backSubModel = int(request.form["backsubmodel"])
            tc.backSubModel = backSubModel
        if request.form.get("videobboxes") is None:
            tc.videoBboxes = False
        else:
            tc.videoBboxes = True
        if sc.isTriggerTesting == True:
            msg = "Please restart Motion Detection test to use the changed parameters!"
            flash(msg)
        else:
            if sc.isTriggerRecording == True:
                msg = "Please restart motion detection to use the changed parameters!"
                flash(msg)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

@bp.route("/test_motion_detection", methods=("GET", "POST"))
@login_required
def test_motion_detection():
    logger.debug("In test_motion_detection")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgmotion"
    tmp = {}
    if request.method == "POST":
        if tc.motionDetectAlgo != 1:
            if tc.triggeredByMotion:
                if sc.isTriggerRecording == True:
                    MotionDetector().stopMotionDetection()
                    sc.isTriggerRecording = False
                err = None
                sc.isTriggerTesting = True
                MotionDetector().setAlgorithm()
                MotionDetector().startMotionDetection()
                if sc.error:
                    logger.debug("In motion detection - test not started because of error")
                    msg = "Error in " + sc.errorSource + ": " + sc.error
                    flash(msg)
                    if sc.error2:
                        flash(sc.error2)
                    err = None
                elif tc.error:
                    logger.debug("In motion detection - test not started because of error")
                    msg = "Error in " + tc.errorSource + ": " + tc.error
                    flash(msg)
                    if tc.error2:
                        flash(tc.error2)
                    err = None
                else:
                    sc.isTriggerRecording = True
                    logger.debug("In motion detection - test started")
            else:
                err = "Motion detection is not activated activated"
            if err:
                flash(err)
        else:
            msg = f"For this Motion Detection Algoritm there is no test. Current framerate is {round(tc.motionTestFramerate, 1)} fps"
            flash(msg)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

@bp.route("/stop_test_motion_detection", methods=("GET", "POST"))
@login_required
def stop_test_motion_detection():
    logger.debug("In stop_test_motion_detection")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgmotion"
    tmp = {}
    if request.method == "POST":
        if sc.isTriggerRecording:
            MotionDetector().stopMotionDetection()
            sc.isTriggerTesting = False
            sc.isTriggerRecording = False
            logger.debug("In motion - detection stopped")
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

@bp.route("/test_frame1_feed")
# @login_required
def test_frame1_feed():
    #logger.debug("Thread %s: In test_frame1_feed", get_ident())
    Camera().startLiveStream()
    md = MotionDetector()
    return Response(gen_testFrame1(md),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_testFrame1(motionDetector):
    """Video streaming generator function."""
    #logger.debug("Thread %s: In gen_testFrame1", get_ident())
    yield b'--frame\r\n'
    while True:
        frame = motionDetector.get_testFrame1()
        if frame:
            #logger.debug("Thread %s: gen_gray - Got frame of length %s", get_ident(), len(frame))
            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/test_frame2_feed")
# @login_required
def test_frame2_feed():
    #logger.debug("Thread %s: In test_frame2_feed", get_ident())
    Camera().startLiveStream()
    md = MotionDetector()
    return Response(gen_testFrame2(md),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_testFrame2(motionDetector):
    """Video streaming generator function."""
    #logger.debug("Thread %s: In gen_testFrame2", get_ident())
    yield b'--frame\r\n'
    while True:
        frame = motionDetector.get_testFrame2()
        if frame:
            #logger.debug("Thread %s: gen_gray - Got frame of length %s", get_ident(), len(frame))
            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/test_frame3_feed")
# @login_required
def test_frame3_feed():
    #logger.debug("Thread %s: In test_frame3_feed", get_ident())
    Camera().startLiveStream()
    md = MotionDetector()
    return Response(gen_testFrame3(md),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_testFrame3(motionDetector):
    """Video streaming generator function."""
    #logger.debug("Thread %s: In gen_testFrame3", get_ident())
    yield b'--frame\r\n'
    while True:
        frame = motionDetector.get_testFrame3()
        if frame:
            #logger.debug("Thread %s: gen_gray - Got frame of length %s", get_ident(), len(frame))
            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@bp.route("/test_frame4_feed")
# @login_required
def test_frame4_feed():
    #logger.debug("Thread %s: In test_frame4_feed", get_ident())
    Camera().startLiveStream()
    md = MotionDetector()
    return Response(gen_testFrame4(md),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_testFrame4(motionDetector):
    """Video streaming generator function."""
    #logger.debug("Thread %s: In gen_testFrame4", get_ident())
    yield b'--frame\r\n'
    while True:
        frame = motionDetector.get_testFrame4()
        if frame:
            #logger.debug("Thread %s: gen_gray - Got frame of length %s", get_ident(), len(frame))
            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

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
    tmp = {}
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
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

@bp.route("/notify", methods=("GET", "POST"))
@login_required
def notify():
    logger.debug("In notify")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgnotify"
    scr = cfg.secrets
    tmp = {}
    if request.method == "POST":
        err = ""
        tc.notifyHost = request.form["notifyhost"]
        tc.notifyPort = int(request.form["notifyport"])
        tc.notifyFrom = request.form["notifyfrom"]
        tc.notifyTo = request.form["notifyto"]
        tc.notifySubject = request.form["notifysubject"]
        if tc.notifySubject == "":
            err = "Please enter 'Subject'"
        if tc.notifyTo == "":
            err = "Please enter 'To e-Mail'"
        if tc.notifyFrom == "":
            err = "Please enter 'From e-Mail'"
        if tc.notifyHost == "":
            err = "Please enter 'SMTP Server'"
        if request.form.get("notifyauthenticate") is None:
            tc.notifyAuthenticate = False
        else:
            tc.notifyAuthenticate = True
        if tc.notifyAuthenticate == True:
            user = request.form["notifyuser"]
            pwd = request.form["notifypassword"]
            if user == "" or pwd == "":
                if tc.notifyConOK:
                    if user == "":
                        user = scr.notifyUser
                    if pwd == "":
                        pwd = scr.notifyPwd
            if user == "" or pwd == "":
                err = "Please provide 'User' and 'Password'"
            else:
                if request.form.get("notifysavepwd") is None:
                    tc.notifySavePwd = False
                else:
                    tc.notifySavePwd = True
                tc.notifyPwdPath = request.form["notifypwdpath"]
                if tc.notifySavePwd == True:
                    if tc.notifyPwdPath == "":
                        err = "Please provide 'Credentials File Path'"
                else:
                    tc.notifyPwdPath = ""
            
        if err != "":
            tc.notifyConOK = False
            flash(err)
        else:
            if request.form.get("notifyusessl") is None:
                tc.notifyUseSSL = False
            else:
                tc.notifyUseSSL = True
            if tc.notifyAuthenticate == False:
                user = ""
                pwd = ""
                tc.notifySavePwd = False
                tc.notifyPwdPath = ""
            tc.notifyPause = int(request.form["notifypause"])
            if request.form.get("notifyincludevideo") is None:
                tc.notifyIncludeVideo = False
            else:
                tc.notifyIncludeVideo = True
            if request.form.get("notifyincludephoto") is None:
                tc.notifyIncludePhoto = False
            else:
                tc.notifyIncludePhoto = True
            if tc.notifyConOK:
                if user == "":
                    user = scr.notifyUser
                if pwd == "":
                    pwd = scr.notifyPwd
            (user, pwd, err) = tc.checkNotificationRecipient(user=user, pwd=pwd)
            if err != "":
                flash(err)
            else:
                scr.notifyUser = user
                scr.notifyPwd = pwd
                flash("Connection test successful")
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

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
    tmp = {}
    if request.method == "POST":
        err = None
        if tc.triggeredByMotion \
        or tc.triggeredByEvents:
            if tc.triggeredByMotion:
                MotionDetector().setAlgorithm()
                MotionDetector().startMotionDetection()
            if tc.triggeredByEvents:
                TriggerHandler().start()
            if sc.error:
                logger.debug("In motion detection not started because of error")
                msg = "Error in " + sc.errorSource + ": " + sc.error
                flash(msg)
                if sc.error2:
                    flash(sc.error2)
                err = None
            elif tc.error:
                logger.debug("In motion detection not started because of error")
                msg = "Error in " + tc.errorSource + ": " + tc.error
                flash(msg)
                if tc.error2:
                    flash(tc.error2)
                err = None
            else:
                if tc.triggeredByMotion:
                    sc.isTriggerRecording = True
                if tc.triggeredByEvents:
                    sc.isEventhandling = True
                logger.debug("In motion detection started")
        else:
            err = "There is no trigger activated"
        if err:
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

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
    tmp = {}
    if request.method == "POST":
        if sc.isTriggerRecording:
            MotionDetector().stopMotionDetection()
            sc.isTriggerRecording = False
            logger.debug("In motion - detection stopped")
        if sc.isEventhandling:
            TriggerHandler().stop()
            sc.isEventhandling = False
            logger.debug("In Eventhandling stopped")
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

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
    tmp = {}
    if request.method == "POST":
        if request.form.get("evincludevideo") is None:
            tc.evIncludeVideo = False
        else:
            tc.evIncludeVideo = True
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

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
    tmp = {}
    if request.method == "POST":
        if request.form.get("evincludephoto") is None:
            tc.evIncludePhoto = False
        else:
            tc.evIncludePhoto = True
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

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

@bp.route("/new_trigger", methods=("GET", "POST"))
@login_required
def new_trigger():
    logger.debug("In new_trigger")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgtriggers"
    tmp = {}
    if request.method == "POST":
        err = ""
        if err == "":
            triggerSource = request.form["triggersource"]
            logger.debug("trigger.new_trigger - triggerSource=%s", triggerSource)
            tmp["triggerSource"] = triggerSource
        if err == "":
            if not request.form.get("triggerdevice") is None:
                triggerDevice = request.form["triggerdevice"]
                logger.debug("trigger.new_trigger - triggerDevice=%s", triggerDevice)
                tmp["triggerDevice"] = triggerDevice
            else:
                err = " "
        triggerEventSettings = {}
        triggerControl = {}
        if err == "":
            if not request.form.get("triggerevent") is None:
                triggerEvent = request.form["triggerevent"]
                logger.debug("trigger.new_trigger - triggerEvent=%s", triggerEvent)
                tmp["triggerEvent"] = triggerEvent
            else:
                err = " "
        if err == "":
            events, eventSettings, control = tc.triggerEvents(triggerSource, triggerDevice)
            if len(eventSettings) > 0:
                triggerEventSettings = copy.deepcopy(eventSettings)
                tmp["triggerEventSettings"] = triggerEventSettings
                for param, val in triggerEventSettings.items():
                    elmtId = f"trigger_{ param }_value"
                    if not request.form.get(elmtId) is None:
                        value = request.form.get(elmtId)
                        err, triggerEventSettings[param] = castType(value, val)
                        tmp["triggerEventSettings"] = triggerEventSettings
                    else:
                        err = " "
                        break
                logger.debug("trigger.new_trigger - eventsettings=%s", triggerEventSettings)
                
            logger.debug("trigger.new_trigger - control=%s", control)
            if len(control) > 0:
                triggerControl = copy.deepcopy(control)
                tmp["triggerControl"] = triggerControl
                for cparam, cval in triggerControl.items():
                    elmtId = f"triggerctrl{ cparam }_value"
                    if not request.form.get(elmtId) is None:
                        cvalue = request.form.get(elmtId)
                        err, triggerControl[cparam] = castType(cvalue, cval)
                        tmp["triggerControl"] = triggerControl
                    else:
                        err = " "
                        break
                logger.debug("trigger.new_trigger - control=%s", triggerControl)
                
        if err == "":
            if not request.form.get("triggerid") is None:
                triggerId = request.form["triggerid"]
                logger.debug("trigger.new_trigger - triggerId=%s", triggerId)
                if triggerId != "":
                    if tc.getTrigger(triggerId) is not None:
                        err = f"A trigger with ID {triggerId} exists already."
                    else:
                        tmp["triggerId"] = triggerId
                else:
                    err = "Please enter a unique trigger ID"
            else:
                err = " "
        if err == "":
            trigger = Trigger()
            trigger.id = triggerId
            trigger.source = triggerSource
            trigger.device = triggerDevice
            trigger.event = triggerEvent
            trigger.params = triggerEventSettings
            trigger.control = triggerControl
            if sc.isEventhandling:
                trigger.isActive = False
                err = "New trigger was not activated because event detection is active"
            else:
                if countEvent(triggerSource, triggerDevice, triggerEvent, tc) > 0:
                    trigger.isActive = False
                    err = "New trigger was not activated because another active trigger uses the same event"
                else:
                    trigger.isActive = True
            tc.triggers.append(trigger)
            tmp = {}
        
        if err.strip() != "":
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

def countEvent(source:str, device:str, event:str, tc:TriggerConfig) -> int:
    """ Check the number of triggers with the same event

    Args:
        sourve (str): Source
        device (str): Device
        event (str): Event

    Returns:
        int: _description_Number of triggers with the same event
    """
    cnt = 0
    for trigger in tc.triggers:
        if  trigger.source == source \
        and trigger.device == device \
        and trigger.event == event \
        and trigger.isActive == True:
            cnt += 1
    return cnt

def checkTrigger(tc:TriggerConfig) -> bool:
    """ Check triggers for duplicate event

    Sterting from first to last trigger:
    If another trigger withthe same event is found, the candidate trigger is deactivated    

    Returns:
        bool: True: No status changes made
    """
    res = True
    for trigger in tc.triggers:
        if countEvent(trigger.source, trigger.device, trigger.event, tc) > 1:
            trigger.isActive = False
            res = False
    return res

@bp.route("/trigger_activation", methods=("GET", "POST"))
@login_required
def trigger_activation():
    logger.debug("In trigger_activation")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgtriggers"
    tmp = {}
    if request.method == "POST":
        err = ""
        cnt = 0
        newTriggers = []
        for trigger in tc.triggers:
            elmtid = f"trigger{trigger.id}_isactive"
            trigger.isActive = not request.form.get(elmtid) is None
            elmtiddel = f"trigger{trigger.id}_delete"
            delete = not request.form.get(elmtiddel) is None
            if delete == False:
                newTriggers.append(trigger)
            else:
                cnt += 1
        if cnt > 0:
            tc.triggers = newTriggers
            
        if checkTrigger(tc) == False:
            err = "Some triggers werde deactivated because they used the same event"
        if err.strip() != "":
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

def parseTuple(stuple: str) -> tuple[str, tuple]:
    """ Parse a string which is assumed to be a tuple

    Args:
        stuple (str): string to be tuplelized

    Returns:
        tuple[str, tuple]: 
            - error
            - tuplelized string    
    """
    rest = stuple
    err = ""
    try:
        tpl = ast.literal_eval(str(stuple))
        if type(tpl) is tuple:
            rest = tpl
        else:
            err = f"{stuple} could not be cast to type of tuple!"
    except Exception as e:
        err = f"Error parsing {stuple} to tuple: {type(e):{e}}"
    return err, rest

def castType(val:str, tpl:object) ->tuple[str, object]:
    """ Cast the given value to the type of the given template

    Args:
        val (str)   : Value to be casted
        tpl (object): template

    Returns:
        tuple[str, object]: 
            - Error message
            - type-converted value
    """
    err = ""
    res = val
    if type(val) is str:
        try:
            if type(tpl) is str:
                pass
            elif type(tpl) is int:
                res = int(val)
            elif type(tpl) is float:
                res = float(val)
            elif type(tpl) is bool:
                if val == "0":
                    res = False
                elif val == "1":
                    res = True
                elif val.casefold() == "false":
                    res = False
                elif val.casefold == "true":
                    res = True
                else:
                    err = "String does not represent boolean."            
            elif type(tpl) is tuple:
                l = len(tpl)
                err, valt = parseTuple(val)
                if err == "":
                    ll = len(valt)
                    if ll != l:
                        err = f"{val} should be a tuple of length {l}"
                    else:
                        for n in range(0, l):
                            if type(valt[n]) != type(tpl[n]):
                                err = f"{val} : elements of tuple do not have the expected type"
                                break
                        if err == "":
                            res = valt
        except TypeError as e:
            err = f"Type error for {val}: {e}"
        except Exception as e:
            err = f"{type(e)} error for {val}: {e}"
    else:
        err = f"{val} should be a string rather than {type(val)}"
    return err, res

@bp.route("/new_action", methods=("GET", "POST"))
@login_required
def new_action():
    logger.debug("In new_action")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgactions"
    tmp = {}
    if request.method == "POST":
        err = ""
        if err == "":
            actionSource = request.form["actionsource"]
            logger.debug("action.new_action - actionSource=%s", actionSource)
            tmp["actionSource"] = actionSource
        if err == "":
            if not request.form.get("actiondevice") is None:
                actionDevice = request.form["actiondevice"]
                logger.debug("action.new_action - actionDevice=%s", actionDevice)
                tmp["actionDevice"] = actionDevice
            else:
                err = " "
        actionTarget = {}
        if err == "":
            if not request.form.get("actionmethod") is None:
                method = request.form["actionmethod"]
                logger.debug("action.new_action - method=%s", method)
                actionTarget["method"] = method
                tmp["actionTarget"] = actionTarget
            else:
                err = " "
        if err == "":
            actionTargets = tc.actionTargets(actionSource, actionDevice)
            if len(actionTargets) > 0:
                for target in actionTargets:
                    if target["method"] == method:
                        ctarget = copy.deepcopy(target)
                        if "params" in ctarget:
                            params = ctarget["params"]
                            if len(params) > 0:
                                for param, paramVal in params.items():
                                    elmtId = f"action_{method}_param_{param}_value"
                                    if not request.form.get(elmtId) is None:
                                        value = request.form.get(elmtId)
                                        err, params[param] = castType(value, paramVal)
                                        tmp["actionTarget"] = ctarget
                                    else:
                                        err = " "
                                        break
                        else:
                            params = {}
                        if err == "":
                            if "control" in ctarget:
                                control = ctarget["control"]
                                if len(control) > 0:
                                    for ctrl, ctrlVal in control.items():
                                        elmtId = f"action_{method}_control_{ctrl}_value"
                                        if not request.form.get(elmtId) is None:
                                            value = request.form.get(elmtId)
                                            err, control[ctrl] = castType(value, ctrlVal)
                                            tmp["actionTarget"] = ctarget
                                        else:
                                            err = " "
                                            break
                            else:
                                control = {}
                            
                logger.debug("action.new_action - tmp=%s", tmp)
                
        if err == "":
            if not request.form.get("actionid") is None:
                actionId = request.form["actionid"]
                logger.debug("action.new_action - actionId=%s", actionId)
                if actionId != "":
                    if tc.getAction(actionId) is not None:
                        err = f"An action with ID {actionId} exists already."
                    else:
                        tmp["actionId"] = actionId
                else:
                    err = "Please enter a unique action ID"
            else:
                err = " "
                    
        if err == "":
            action = Action()
            action.id = actionId
            action.source = actionSource
            action.device = actionDevice
            action.method = method
            action.params = params
            action.control = control
            action.isActive = True
            tc.actions.append(action)
            tmp = {}

        if err == "":
            if "steps" in control \
            and "duration" in control:
                if control["steps"] > 1 \
                and control["duration"] > 0.0:
                    err = "Graduall approach in steps is currently not yet supported."
                    control["steps"] = 1
                    control["duration"] = 0.0
                
        if err.strip() != "":
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

def checkActionUsage(actionId:str, actionUsage: list, sc:ServerConfig) -> tuple[bool, list]:
    """ Check whether an action is still in use in an action button

    Args:
        actionId (str): Action ID to be checked

    Returns:
        bool: True when action is in use
        list: Action buttons where action is used
    """
    used = False
    for row in sc.aButtons:
        for button in row:
            if button.buttonAction == actionId:
                used = True
                actionUsage.append(button.buttonText)
    return used, actionUsage

@bp.route("/action_activation", methods=("GET", "POST"))
@login_required
def action_activation():
    logger.debug("In action_activation")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgactions"
    tmp = {}
    actionUsage = []
    nondelete = []
    if request.method == "POST":
        err = ""
        cnt = 0
        newActions = []
        for action in tc.actions:
            elmtid = f"action{action.id}_isactive"
            action.isActive = not request.form.get(elmtid) is None
            elmtiddel = f"action{action.id}_delete"
            delete = not request.form.get(elmtiddel) is None
            if delete == False:
                newActions.append(action)
            else:
                use, actionUsage = checkActionUsage(action.id, actionUsage, sc)
                if use == False:
                    for trg in tc.triggers:
                        if action.id in trg.actions:
                            trg.actions.pop(action.id)
                    cnt += 1
                else:
                    nondelete.append(action.id)
                    newActions.append(action)
        if cnt > 0:
            tc.actions = newActions
        if len(nondelete) > 0:
            err = f"Actions {nondelete} could not be deleted because they are used in action buttons {actionUsage}"
        
        if err.strip() != "":
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)

@bp.route("/trigger_action", methods=("GET", "POST"))
@login_required
def trigger_action():
    logger.debug("In trigger_action")
    cfg = CameraCfg()
    g.hostname = request.host
    g.version = version
    sc = cfg.serverConfig
    tc = cfg._triggerConfig
    sc.lastTriggerTab = "trgtriggeractions"
    tmp = {}
    if request.method == "POST":
        err = ""
        for trigger in tc.triggers:
            tid = trigger.id
            for action in tc.actions:
                aid = action.id
                elmId = f"triggeraction_{tid}_{aid}"
                if request.form.get(elmId) is None:
                    trigger.actions[aid] = False
                else:
                    trigger.actions[aid] = True
        if err.strip() != "":
            flash(err)
    return render_template("trigger/trigger.html", tc=tc, sc=sc, tmp=tmp)
