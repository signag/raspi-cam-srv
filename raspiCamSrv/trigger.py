from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.version import version

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("trigger", __name__)

logger = logging.getLogger(__name__)

@bp.route("/trigger")
@login_required
def trigger():
    cam = Camera().cam
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    sc.curMenu = "info"
    return render_template("trigger/trigger.html", sm=sm, sc=sc, cp=cp, cs=cs, cfg=cfg)
