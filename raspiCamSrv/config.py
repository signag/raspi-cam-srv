from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required

bp = Blueprint("config", __name__)

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

@bp.route("/config")
@login_required
def main():
    return render_template("config/main.html")
