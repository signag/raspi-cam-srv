from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.version import version
import subprocess
from subprocess import CalledProcessError
from raspiCamSrv.triggerHandler import TriggerHandler


from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("console", __name__)

logger = logging.getLogger(__name__)

@bp.route("/console")
@login_required
def console():
    cam = Camera().cam
    props = cam.camera_properties
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    if sc.vButtonHasCommandLine == True:
        if sc.vButtonCommand is None:
            sc.vButtonCommand = ""
    sc.curMenu = "console"
    return render_template("console/console.html", props=props, sc=sc)

@bp.route("/execute/<row>/<col>", methods=("GET", "POST"))
@login_required
def execute(row:None, col=None):
    logger.debug("In execute - row=%s, col=%s", row, col)
    cam = Camera().cam
    props = cam.camera_properties
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    sc.curMenu = "console"
    sc.vButtonCommand = None
    sc.vButtonArgs = None
    sc.vButtonReturncode = None
    sc.vButtonStderr = None
    sc.vButtonStdout = None
    sc.lastConsoleTab = "versbuttons"
    if request.method == "POST":
        msg = ""
        r = int(row)
        c = int(col)
        btn = sc.vButtons[r][c]
        cmd = btn.buttonExec
        sc.vButtonCommand = cmd
        args = cmd.rsplit(" ")
        sc.vButtonArgs = args
        
        msg = "Command successfully executed."
        result = None
        if cmd != "":
            try:
                result = subprocess.run(args, capture_output=True, text=True, check=False)            
            except CalledProcessError as e:
                msg = f"Command executed with error: {e}."
            except Exception as e:
                msg = f"Command executed with error: {e}."
            if result:
                sc.vButtonReturncode = result.returncode
                sc.vButtonStdout = result.stdout
                sc.vButtonStderr = result.stderr
        else:
            msg = "No command executed"
        
        if msg != "":
            flash(msg)
    return render_template("console/console.html", props=props, sc=sc)

@bp.route("/execCommandline", methods=("GET", "POST"))
@login_required
def execCommandline():
    logger.debug("In execCommandline")
    cam = Camera().cam
    props = cam.camera_properties
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    if request.method == "POST":
        msg = ""
        cmd = request.form["commandline"]
        sc.vButtonCommand = cmd
        args = cmd.rsplit(" ")
        sc.vButtonArgs = args
        
        msg = "Command successfully executed."
        result = None
        if cmd != "":
            try:
                result = subprocess.run(args, capture_output=True, text=True, check=False)            
            except CalledProcessError as e:
                msg = f"Command executed with error: {e}."
            except Exception as e:
                msg = f"Command executed with error: {e}."
            if result:
                sc.vButtonReturncode = result.returncode
                sc.vButtonStdout = result.stdout
                sc.vButtonStderr = result.stderr
        else:
            msg = "No command executed"
        
        if msg != "":
            flash(msg)
    return render_template("console/console.html", props=props, sc=sc)

@bp.route("/do_action/<row>/<col>", methods=("GET", "POST"))
@login_required
def do_action(row:None, col=None):
    logger.debug("In do_action - row=%s, col=%s", row, col)
    cam = Camera().cam
    props = cam.camera_properties
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    sc.curMenu = "console"
    sc.vButtonCommand = None
    sc.vButtonArgs = None
    sc.vButtonReturncode = None
    sc.vButtonStderr = None
    sc.vButtonStdout = None
    sc.lastConsoleTab = "actionbuttons"
    if request.method == "POST":
        msg = ""
        r = int(row)
        c = int(col)
        btn = sc.aButtons[r][c]
        action = btn.buttonAction
        
        msg = "Action successfully executed."
        result = None
        if action != "":
            msg = TriggerHandler.doAction(action)
        else:
            msg = "No Action executed"
        
        if msg != "":
            flash(msg)
    return render_template("console/console.html", props=props, sc=sc)
