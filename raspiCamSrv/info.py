from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("info", __name__)

logger = logging.getLogger(__name__)

@bp.route("/info")
@login_required
def main():
    cam = Camera().cam
    props = cam.camera_properties
    g.hostname = request.host
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    sc.curMenu = "info"
    return render_template("info/info.html", props=props, sm=sm, sc=sc, cp=cp, cs=cs, cfg=cfg)
