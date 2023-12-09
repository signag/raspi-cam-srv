from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from raspiCamSrv.auth import login_required
from raspiCamSrv.db import get_db

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("home/index.html")

