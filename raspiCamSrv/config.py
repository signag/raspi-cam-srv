from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("config", __name__)

logger = logging.getLogger(__name__)

@bp.route("/config")
@login_required
def main():
    g.hostname = request.host
    cfg = CameraCfg()
    sm = cfg.sensorModes
    sc = cfg.serverConfig
    sc.curMenu = "config"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.stillConfig
    cfgvideo =cfg.videoConfig
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/liveViewCfg", methods=("GET", "POST"))
@login_required
def liveViewCfg():
    logger.info("In liveViewCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    sm = cfg.sensorModes
    sc = cfg.serverConfig
    sc.lastConfigTab = "cfglive"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.stillConfig
    cfgvideo =cfg.videoConfig
    if request.method == "POST":
        pass
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgvideo=cfgvideo, cfgs=cfgs)
