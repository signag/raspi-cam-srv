from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from flask import send_file, send_from_directory
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.version import version
import os
from datetime import datetime, timedelta
from io import BytesIO
from zipfile import ZipFile

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("images", __name__)

logger = logging.getLogger(__name__)

def getFileList() -> list:
    logger.debug("In images/getFileList")
    cfg = CameraCfg()
    sc = cfg.serverConfig
    # Get the filelist
    fp = sc.photoRoot + "/" + "photos/" + "camera_" + str(sc.pvCamera)    
    fl = os.listdir(fp)
    # Sort reverse
    fl.sort(reverse=True)
    logger.debug("%s files found in %s", len(fl), fp)
    
    dl = []
    p = 1
    cnt = 0
    for file in fl:
        name, ext = os.path.splitext(file)
        path = "photos/" + "camera_" + str(sc.pvCamera) + "/" + file
        fpath = os.path.join(fp, file)
        if ext.lower() != ".dng" \
        and ext.lower() != ".mp4" \
        and ext.lower() != ".h264" \
        and (not os.path.isdir(fpath)):
            nameOK = False
            try:
                dat =  datetime.strptime(name, "%Y%m%d_%H%M%S")
                nameOK = True
            except ValueError:
                nameOK = False
            if nameOK == True:
                include = False
                if dat >= sc.pvFrom and dat <= sc.pvTo:
                    include = True
            else:
                include = False
            if include == True:
                cnt += 1
                entry = {}
                entry["sel"] = False
                entry["path"] = path
                entry["file"] = file
                entry["name"] = name
                entry["type"] = "photo"
                entry["detailPath"] = path
                dl.append(entry)
    logger.debug("%s distinct files in selected range", cnt)

    for file in fl:
        name, ext = os.path.splitext(file)
        path = "photos/" + "camera_" + str(sc.pvCamera) + "/" + file
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
    sc.pvList = dl

@bp.route("/images")
@login_required
def main():
    logger.debug("In images/main")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if sc.pvCamera is None:
        sc.pvCamera = sc.activeCamera
    if sc.pvFrom is None:
        logger.debug("images/main - Setting sc.pvFrom to current date")
        pvFrom = datetime.now()
        sc.pvFrom = datetime(year=pvFrom.year, month=pvFrom.month, day=pvFrom.day, hour=0, minute=0, second=0)
    if sc.pvTo is None:
        logger.debug("images/main - Setting sc.pvTo to current date")
        pvTo = datetime.now()
        sc.pvTo = datetime(year=pvTo.year, month=pvTo.month, day=pvTo.day, hour=23, minute=59, second=59)
    getFileList()
    l = len(sc.pvList)
    if l > 0:
        msg = f'{l} distinct media files found in specified range (placeholders not included)'
    else:
        msg = f'No media files found in specified range'
    flash(msg)
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/control", methods=("GET", "POST"))
@login_required
def control():
    logger.debug("In images/control")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        sc.pvCamera = int(request.form["camera"])
        pvFromStr = request.form.get("pvfrom")
        sc.pvFromStr = pvFromStr
        pvToStr = request.form.get("pvto")
        sc.pvToStr = pvToStr
        getFileList() 
    l = len(sc.pvList)
    if l > 0:
        msg = f'{l} distinct media files found in specified range (placeholders not included)'
    else:
        msg = f'No media files found in specified range'
    flash(msg)
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/today", methods=("GET", "POST"))
@login_required
def today():
    logger.debug("In images/today")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        pvFrom = datetime.now()
        sc.pvFrom = datetime(year=pvFrom.year, month=pvFrom.month, day=pvFrom.day, hour=0, minute=0, second=0)
        pvTo = datetime.now()
        sc.pvTo = datetime(year=pvTo.year, month=pvTo.month, day=pvTo.day, hour=23, minute=59, second=59)
        getFileList()
    l = len(sc.pvList)
    if l > 0:
        msg = f'{l} distinct media files found in specified range (placeholders not included)'
    else:
        msg = f'No media files found in specified range'
    flash(msg)
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/all", methods=("GET", "POST"))
@login_required
def all():
    logger.debug("In images/all")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        sc.pvFrom = datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0)
        pvTo = datetime.now()
        sc.pvTo = datetime(year=pvTo.year, month=pvTo.month, day=pvTo.day, hour=23, minute=59, second=59)
        getFileList()
    l = len(sc.pvList)
    if l > 0:
        msg = f'{l} distinct media files found in specified range (placeholders not included)'
    else:
        msg = f'No media files found in specified range'
    flash(msg)
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/select_all", methods=("GET", "POST"))
@login_required
def select_all():
    logger.debug("In images/select_all")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        for entry in sc.pvList:
            entry["sel"] = True
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/deselect_all", methods=("GET", "POST"))
@login_required
def deselect_all():
    logger.debug("In images/deselect_all")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        for entry in sc.pvList:
            entry["sel"] = False
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/select", methods=("GET", "POST"))
@login_required
def select():
    logger.debug("In images/select")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        logger.debug("images/select - selecting")
        for entry in sc.pvList:
            name = entry["name"]
            id = "photo_" + name
            sel = not request.form.get(id) is None
            entry["sel"] = sel
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

@bp.route("/delete_selected", methods=("GET", "POST"))
@login_required
def delete_selected():
    logger.debug("In images/delete_selected")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        logger.debug("images/delete_selected - deleting")
        cnt = 0
        cntd = 0
        cntErr = 0
        for entry in sc.pvList:
            name = entry["name"]
            sel = entry["sel"]
            if sel == True:
                cntd += 1
                fp = sc.photoRoot + "/" + "photos/" + "camera_" + str(sc.pvCamera) + "/"
                fph = sc.photoRoot + "/" + "photos/" + "camera_" + str(sc.pvCamera) + "/hist/"
                # Delete histogram if it exists
                fnh = fph + name + ".jpg"
                cnt, cntErr = deleteFile(fnh, cnt, cntErr)
                if entry["type"] == "raw":
                    # Detete raw image
                    fnr = fp + name + ".dng"
                    cnt, cntErr = deleteFile(fnr, cnt, cntErr)
                if entry["type"] == "video":
                    # Detete video
                    fnv = fp + name + ".mp4"
                    cnt, cntErr = deleteFile(fnv, cnt, cntErr)
                    fnv = fp + name + ".h264"
                    cnt, cntErr = deleteFile(fnv, cnt, cntErr)
                # Delete photo or placeholder
                fn = sc.photoRoot + "/" + entry["path"]
                cnt, cntErr = deleteFile(fn, cnt, cntErr)
                
        # Clear displaybuffer
        if cntd > 0:
            sc.displayBufferClear()

        getFileList() 
                
        msg = f"{cntd} distinct media removed: {cnt} successful deletions, {cntErr} failed deletions"
        flash(msg)
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)

def deleteFile(fp: str, cntOK, cntErr):
    logger.debug("images/delete_selected - trying : %s", fp)
    if os.path.exists(fp):
        try:
            os.remove(fp)
            logger.debug("images/delete_selected - deleted: %s", fp)
            cntOK += 1
        except:
            cntErr += 1
    return cntOK, cntErr
    

@bp.route("/download_selected", methods=("GET", "POST"))
@login_required
def download_selected():
    logger.debug("In images/download_selected")
    g.hostname = request.host
    g.version = version
    cam = Camera()
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    cs = cfg.cameras
    sc.curMenu = "photos"
    if request.method == "POST":
        logger.debug("images/download_selected - Preparing download")
        # Setup filelist for compression
        fp = sc.photoRoot + "/" + "photos/" + "camera_" + str(sc.pvCamera) + "/"
        zl = []
        cnt = 0
        cntPhoto = 0
        cntRaw = 0
        cntVideo = 0
        for entry in sc.pvList:
            name = entry["name"]
            sel = entry["sel"]
            if sel == True:
                if entry["type"] == "photo":
                    fn = sc.photoRoot + "/" + entry["path"]
                    if os.path.exists(fn):
                        cnt += 1
                        cntPhoto += 1
                        logger.debug("images/download_selected - added %s", fn)
                        zl.append(fn)
                if entry["type"] == "raw":
                    fn = fp + name + ".dng"
                    if os.path.exists(fn):
                        cnt += 1
                        cntRaw += 1
                        logger.debug("images/download_selected - added %s", fn)
                        zl.append(fn)
                if entry["type"] == "video":
                    fn = fp + name + ".mp4"
                    if os.path.exists(fn):
                        cnt += 1
                        cntVideo += 1
                        logger.debug("images/download_selected - added %s", fn)
                        zl.append(fn)
                    fn = fp + name + ".h264"
                    if os.path.exists(fn):
                        cnt += 1
                        cntVideo += 1
                        logger.debug("images/download_selected - added %s", fn)
                        zl.append(fn)
        if len(zl) > 1:
            logger.debug("images/download_selected - Preparing archive")
            stream = BytesIO()
            with ZipFile(stream, 'w') as zf:
                for file in zl:
                    zf.write(file, os.path.basename(file))
            stream.seek(0)
            logger.debug("images/download_selected - archive done")

            now = datetime.now()
            zipName = "raspiCamSrvMedia_" + now.strftime("%Y%m%d_%H%M%S") + ".zip"
            logger.debug("images/download_selected - downloading as %s", zipName)
            msg = f"Downloading archive {zipName} with {cntPhoto} photos, {cntRaw} raw photos and {cntVideo} videos."
            flash(msg)
            return send_file(
                stream,
                as_attachment=True,
                download_name=zipName
            )
        elif len(zl) == 1:
            fp = zl[0]
            (path, file) = os.path.split(fp)
            msg = f"Downloading {file}"
            flash(msg)
            return send_file(
                fp,
                as_attachment=True,
                download_name=file
            )
            
    msg = "No files selected for download"
    flash(msg)
    return render_template("images/main.html", sc=sc, cp=cp, cs=cs)
