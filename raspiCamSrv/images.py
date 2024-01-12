from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
import os

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("images", __name__)

logger = logging.getLogger(__name__)

@bp.route("/images")
@login_required
def main():
    g.hostname = request.host
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "images"
    # Get the filelist
    fl = os.listdir(sc.photoPath)
    # Sort reverse
    fl.sort(reverse=True)
    # Create displaylist
    # Entries are tuples with elements:
    # - filename
    # - type ('video', 'photo')
    # - raw If there is a dng with the same name
    # - 
    dl = []
    for file in fl:
        name, ext = os.path.splitext(file)
        path = "photos" + "/" + file
        if ext.lower != "dng":
            entry = {}
            entry["sel"] = False
            entry["path"] = path
            entry["file"] = file
            entry["name"] = name
            if ext.lower == "mp4" \
            or ext.lower == "h264":
                entry["type"] = "video"
            else:
                entry["type"] = "photo"
            dl.append(entry)
        
    return render_template("images/main.html", sc=sc, cp=cp, dl=dl)
