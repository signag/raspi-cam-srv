from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera
import os

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("images", __name__)

logger = logging.getLogger(__name__)

@bp.route("/images")
@login_required
def main():
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "photos"
    # Get the filelist
    fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath
    fl = os.listdir(fp)
    # Sort reverse
    fl.sort(reverse=True)
    
    dl = []
    for file in fl:
        name, ext = os.path.splitext(file)
        path = sc.cameraPhotoSubPath + "/" + file
        if ext.lower() != ".dng" \
        and ext.lower() != ".mp4" \
        and ext.lower() != ".h264":
            entry = {}
            entry["sel"] = False
            entry["path"] = path
            entry["file"] = file
            entry["name"] = name
            entry["type"] = "photo"
            entry["detailPath"] = path
            dl.append(entry)

    for file in fl:
        name, ext = os.path.splitext(file)
        path = sc.cameraPhotoSubPath + "/" + file
        if ext.lower() == ".dng" \
        or ext.lower() == ".mp4" \
        or ext.lower() == ".h264":
            # For raw and video, search the placeholder and update
            for entry in dl:
                if entry["name"] == name:
                    if ext.lower() == ".dng":
                        entry["type"] = "raw"
                        entry["file"] = file
                    else:
                        entry["type"] = "video"
                        entry["file"] = file
                        if ext.lower() == ".mp4":
                            entry["detailPath"] = path
                    break
        
    return render_template("images/main.html", sc=sc, cp=cp, dl=dl)
