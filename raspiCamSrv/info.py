from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("info", __name__)

logger = logging.getLogger(__name__)

@bp.route("/info")
@login_required
def main():
    cam = Camera().cam
    props = cam.camera_properties
    return render_template("info/info.html", props=props)
