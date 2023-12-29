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
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

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
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
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
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/photoCfg", methods=("GET", "POST"))
@login_required
def photoCfg():
    logger.info("In photoCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    sm = cfg.sensorModes
    sc = cfg.serverConfig
    sc.lastConfigTab = "cfgphoto"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    if request.method == "POST":
        transform_hflip = not request.form.get("FOTO_transform_hflip") is None
        cfgphoto.transform_hflip = transform_hflip        
        transform_vflip = not request.form.get("FOTO_transform_vflip") is None
        cfgphoto.transform_vflip = transform_vflip
        colour_space = request.form["FOTO_colour_space"]
        cfgphoto.colour_space = colour_space
        buffer_count = int(request.form["FOTO_buffer_count"])
        cfgphoto.buffer_count = buffer_count
        queue = not request.form.get("FOTO_queue") is None
        cfgphoto.queue = queue
        sensor_mode = int(request.form["FOTO_sensor_mode"])
        cfgphoto.sensor_mode = str(sensor_mode)
        cfgphoto.display = None
        cfgphoto.encode = "main"
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/rawCfg", methods=("GET", "POST"))
@login_required
def rawCfg():
    logger.info("In rawCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    sm = cfg.sensorModes
    sc = cfg.serverConfig
    sc.lastConfigTab = "cfgraw"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    if request.method == "POST":
        transform_hflip = not request.form.get("PRAW_transform_hflip") is None
        cfgraw.transform_hflip = transform_hflip        
        transform_vflip = not request.form.get("PRAW_transform_vflip") is None
        cfgraw.transform_vflip = transform_vflip
        colour_space = request.form["PRAW_colour_space"]
        cfgraw.colour_space = colour_space
        buffer_count = int(request.form["PRAW_buffer_count"])
        cfgraw.buffer_count = buffer_count
        queue = not request.form.get("PRAW_queue") is None
        cfgraw.queue = queue
        sensor_mode = int(request.form["PRAW_sensor_mode"])
        cfgraw.sensor_mode = str(sensor_mode)
        cfgraw.display = None
        cfgraw.encode = "raw"
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/videoCfg", methods=("GET", "POST"))
@login_required
def videoCfg():
    logger.info("In videoCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    sm = cfg.sensorModes
    sc = cfg.serverConfig
    sc.lastConfigTab = "cfgvideo"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    if request.method == "POST":
        transform_hflip = not request.form.get("VIDO_transform_hflip") is None
        cfgvideo.transform_hflip = transform_hflip        
        transform_vflip = not request.form.get("VIDO_transform_vflip") is None
        cfgvideo.transform_vflip = transform_vflip
        colour_space = request.form["VIDO_colour_space"]
        cfgvideo.colour_space = colour_space
        buffer_count = int(request.form["VIDO_buffer_count"])
        cfgvideo.buffer_count = buffer_count
        queue = not request.form.get("VIDO_queue") is None
        cfgvideo.queue = queue
        sensor_mode = int(request.form["VIDO_sensor_mode"])
        cfgvideo.sensor_mode = str(sensor_mode)
        cfgvideo.display = None
        cfgvideo.encode = "main"
    return render_template("config/main.html", sc=sc, sm=sm, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)
