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
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    sc.curMenu = "config"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    return render_template("config/main.html", sc=sc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/liveViewCfg", methods=("GET", "POST"))
@login_required
def liveViewCfg():
    logger.info("In liveViewCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    sc.lastConfigTab = "cfglive"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    if request.method == "POST":
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
        sensor_mode = request.form["LIVE_sensor_mode"]
        cfglive.sensor_mode = sensor_mode
        if sensor_mode == "custom":
            size_width = int(request.form["LIVE_stream_size_width"])
            size_height = int(request.form["LIVE_stream_size_height"])
            cfglive.stream_size = (size_width, size_height)
            cfglive.stream_size_align = not request.form.get("LIVE_stream_size_align") is None
        else:
            mode = sm[int(sensor_mode)]
            cfglive.stream_size = mode.size
            cfglive.stream_size_align = not request.form.get("LIVE_stream_size_align") is None
        format = request.form["LIVE_format"]
        cfglive.format = format
        cfglive.display = None
        cfglive.encode = "main"
        Camera().restartLiveView()
    return render_template("config/main.html", sc=sc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/photoCfg", methods=("GET", "POST"))
@login_required
def photoCfg():
    logger.info("In photoCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
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
        sensor_mode = request.form["FOTO_sensor_mode"]
        cfgphoto.sensor_mode = sensor_mode
        if sensor_mode == "custom":
            size_width = int(request.form["FOTO_stream_size_width"])
            size_height = int(request.form["FOTO_stream_size_height"])
            cfgphoto.stream_size = (size_width, size_height)
            cfgphoto.stream_size_align = not request.form.get("FOTO_stream_size_align") is None
        else:
            mode = sm[int(sensor_mode)]
            cfgphoto.stream_size = mode.size
            cfgphoto.stream_size_align = not request.form.get("FOTO_stream_size_align") is None
        format = request.form["FOTO_format"]
        cfgphoto.format = format
        cfgphoto.display = None
        cfgphoto.encode = "main"
    return render_template("config/main.html", sc=sc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/rawCfg", methods=("GET", "POST"))
@login_required
def rawCfg():
    logger.info("In rawCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
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
        queue = not request.form.get("PRAW_queue") is None
        cfgraw.queue = queue
        sensor_mode = request.form["PRAW_sensor_mode"]
        cfgraw.sensor_mode = sensor_mode
        mode = sm[int(sensor_mode)]
        cfgraw.stream_size = mode.size
        cfgraw.stream_size_align = not request.form.get("PRAW_stream_size_align") is None
        format = request.form["PRAW_format"]
        cfgraw.format = format
        cfgraw.display = None
        cfgraw.encode = None
    return render_template("config/main.html", sc=sc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)

@bp.route("/videoCfg", methods=("GET", "POST"))
@login_required
def videoCfg():
    logger.info("In videoCfg")
    g.hostname = request.host
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
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
        sensor_mode = request.form["VIDO_sensor_mode"]
        cfgvideo.sensor_mode = sensor_mode
        if sensor_mode == "custom":
            size_width = int(request.form["VIDO_stream_size_width"])
            size_height = int(request.form["VIDO_stream_size_height"])
            cfgvideo.stream_size = (size_width, size_height)
            cfgvideo.stream_size_align = not request.form.get("VIDO_stream_size_align") is None
        else:
            mode = sm[int(sensor_mode)]
            cfgvideo.stream_size = mode.size
            cfgvideo.stream_size_align = not request.form.get("VIDO_stream_size_align") is None
        format = request.form["VIDO_format"]
        cfgvideo.format = format
        cfgvideo.display = None
        cfgvideo.encode = "main"
    return render_template("config/main.html", sc=sc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgs=cfgs)
