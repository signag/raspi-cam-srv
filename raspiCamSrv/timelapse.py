from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("timelapse", __name__)

logger = logging.getLogger(__name__)

@bp.route("/timelapse")
@login_required
def main():
    g.hostname = request.host
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "timelapse"
    return render_template("timelapse/main.html", sc=sc, cp=cp)
