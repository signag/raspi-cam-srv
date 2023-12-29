from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("config", __name__)

logger = logging.getLogger(__name__)

@bp.route("/config")
@login_required
def main():
    g.hostname = request.host
    # Although not directly needed here, the camara needs to be initialized
    # in order to load the camera-specific parameters into configuration
    cam = Camera().cam
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
#        id = request.form["LIVE_id"]
#        use_case = request.form["LIVE_use_case"]
        transform_hflip = not request.form.get("LIVE_transform_hflip") is None
        cfglive.transform_hflip = transform_hflip        
        transform_vflip = not request.form.get("LIVE_transform_vflip") is None
        cfglive.transform_vflip = transform_vflip
        colour_space = request.form["LIVE_colour_space"]
        cfglive.colour_space = colour_space
        buffer_count = int(request.form["LIVE_buffer_count"])
        cfglive.buffer_count = buffer_count
        queue = not request.form.get("LIVE_queue") is None
        cfglive.queue = queue
        sensor_mode = int(request.form["LIVE_sensor_mode"])
        cfglive.sensor_mode = str(sensor_mode)
#        display = request.form["LIVE_display"]
        cfglive.display = None
#        encode = request.form["LIVE_encode"]
        cfglive.encode = "main"
        Camera().restartLiveView()
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgvideo=cfgvideo, cfgs=cfgs)
