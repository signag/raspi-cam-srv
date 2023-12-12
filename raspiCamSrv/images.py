from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("images", __name__)

logger = logging.getLogger(__name__)

@bp.route("/images")
@login_required
def main():
    return render_template("images/main.html")
