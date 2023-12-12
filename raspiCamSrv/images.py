from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required

bp = Blueprint("images", __name__)

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

@bp.route("/images")
@login_required
def main():
    return render_template("images/main.html")
