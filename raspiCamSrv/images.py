from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera
import os

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("images", __name__)

logger = logging.getLogger(__name__)

def getFileList() -> list:
    logger.info("In images/getFileList")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    # Get the filelist
    fp = sc.photoRoot + "/" + sc.cameraPhotoSubPath
    fl = os.listdir(fp)
    # Sort reverse
    fl.sort(reverse=True)
    logger.info("%s files found in %s", len(fl), fp)

    cnt = 0
    for file in fl:
        name, ext = os.path.splitext(file)
        if ext.lower() != ".dng" \
        and ext.lower() != ".mp4" \
        and ext.lower() != ".h264":
            cnt += 1

    if cnt != sc.nrEntriesPhoto:
        sc.nrEntriesPhoto = cnt
        sc.nrPagesPhoto = int(cnt / sc.chunkSizePhoto)
        if sc.nrPagesPhoto * sc.chunkSizePhoto < len(fl):
            sc.nrPagesPhoto += 1
        sc.curPagePhoto = 1
        sc.firstPagePhoto = 1
        sc.lastPagePhoto = 4
        if sc.lastPagePhoto > sc.nrPagesPhoto:
            sc.lastPagePhoto = sc.nrPagesPhoto
    logger.info("Pagination uses %s pages with a chunk size of %s", sc.nrPagesPhoto, sc.chunkSizePhoto)
    
    dl = []
    p = 1
    cnt = 0
    for file in fl:
        name, ext = os.path.splitext(file)
        path = sc.cameraPhotoSubPath + "/" + file
        if ext.lower() != ".dng" \
        and ext.lower() != ".mp4" \
        and ext.lower() != ".h264":
            cnt += 1
            if cnt > sc.chunkSizePhoto:
                p += 1
                cnt = 1
                if p > sc.curPagePhoto:
                    break
            if p == sc.curPagePhoto:
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
    return dl

@bp.route("/images")
@login_required
def main():
    logger.info("In images/main")
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "photos"
    
    dl = getFileList()
            
    return render_template("images/main.html", sc=sc, cp=cp, dl=dl)

@bp.route("/page/<int:pagenr>", methods=("GET",))
@login_required
def page(pagenr):
    logger.info("In images/page")
    logger.info("request.method: %s", request.method)
    logger.info("pagenr: %s", pagenr)
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "photos"
    sc.curPagePhoto = pagenr
    logger.info("sc.curPagePhoto set to %s", pagenr)
    dl = getFileList()
            
    return render_template("images/main.html", sc=sc, cp=cp, dl=dl)

@bp.route("/backwards", methods=("GET",))
@login_required
def backwards():
    logger.info("In images/backwards")
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "photos"
    if sc.curPagePhoto > 1:
        sc.curPagePhoto -= 1
    if sc.curPagePhoto < sc.firstPagePhoto:
        sc.firstPagePhoto = sc.curPagePhoto
        sc.lastPagePhoto = sc.firstPagePhoto + 3
        if sc.lastPagePhoto > sc.nrPagesPhoto:
            sc.lastPagePhoto = sc.nrPagesPhoto
    dl = getFileList()
            
    return render_template("images/main.html", sc=sc, cp=cp, dl=dl)

@bp.route("/forwards", methods=("GET",))
@login_required
def forwards():
    logger.info("In images/forwards")
    g.hostname = request.host
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "photos"
    if sc.curPagePhoto < sc.nrPagesPhoto:
        sc.curPagePhoto += 1
    if sc.curPagePhoto > sc.lastPagePhoto:
        sc.lastPagePhoto = sc.curPagePhoto
        sc.firstPagePhoto = sc.lastPagePhoto - 3
        if sc.firstPagePhoto < 1:
            sc.firstPagePhoto = 1
    dl = getFileList()
            
    return render_template("images/main.html", sc=sc, cp=cp, dl=dl)
