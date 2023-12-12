from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("config", __name__)

logger = logging.getLogger(__name__)

@bp.route("/config")
@login_required
def main():
    return render_template("config/main.html")
