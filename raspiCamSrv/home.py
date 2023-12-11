from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required
from raspiCamSrv.db import get_db
from raspiCamSrv.camera import get_camera

bp = Blueprint("home", __name__)

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

@bp.route("/")
@login_required
def index():
    return render_template("home/index.html")

@bp.route("/video_feed")
@login_required
def video_feed():
    logging.debug("In video_feed")
    cam = get_camera()
    logging.debug("Got camera")
    strm = cam.getStream()
    logging.debug("Got stream: %s", strm)
    return Response(strm, mimetype="multipart/x-mixed-replace; boundary=frame")