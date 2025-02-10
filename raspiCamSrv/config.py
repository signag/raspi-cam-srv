from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for, current_app
from flask import send_file
from werkzeug.exceptions import abort
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.version import version
from picamera2 import Picamera2
import os
import shutil
import json

from raspiCamSrv.auth import login_required
import logging

# Try to import platform, which does not exist in Bullseye Picamera2 distributions
try:
    import picamera2.platform as Platform
    usePlatform = True
except ImportError:
    usePlatform = False


bp = Blueprint("config", __name__)

logger = logging.getLogger(__name__)

@bp.route("/config")
@login_required
def main():
    g.hostname = request.host
    g.version = version
    # Although not directly needed here, the camara needs to be initialized
    # in order to load the camera-specific parameters into configuration
    cam = Camera().cam
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.curMenu = "config"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

def doSyncTransform(hflip: bool, vflip: bool, tgt: list) -> bool:
    """ Synchronize the transform settings of target configurations with reference
    
        Parameters:
        hflip:    horizontal flip
        vflip:    vertical flip
        tgt  :    list of configurations for which to adjust the aspect ratio
        
        Return:
        True if transform settings for Live View was changed
    """
    logger.debug("In doSyncTransform")
    ret = False
    cfg = CameraCfg()
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    for conf in tgt:
        if conf == "Live View":
            if cfglive.transform_hflip != hflip \
            or cfglive.transform_vflip != vflip:
                ret = True
            cfglive.transform_hflip = hflip
            cfglive.transform_vflip = vflip
        elif conf == "Photo":
            cfgphoto.transform_hflip = hflip
            cfgphoto.transform_vflip = vflip
        elif conf == "Raw Photo":
            cfgraw.transform_hflip = hflip
            cfgraw.transform_vflip = vflip
        elif conf == "Video":
            cfgvideo.transform_hflip = hflip
            cfgvideo.transform_vflip = vflip
    logger.debug("doSyncTransform %s", ret)
    return ret

def doSyncAspectRatio(ref: tuple, tgt: list) -> bool:
    """ Synchronize the aspect ratio of target configurations with reference
    
        Parameters:
        ref:    reference size (width, height)
        tgt:    list of configurations for which to adjust the aspect ratio
        
        Return:
        True if Stream Size for Live View was changed
    """
    logger.debug("In doSyncAspectRatio")
    ret = False
    cfg = CameraCfg()
    aspRatioRef = ref[0] / ref[1]
    for conf in tgt:
        if conf == "Live View":
            size = cfg.liveViewConfig.stream_size
        elif conf == "Photo":
            size = cfg.photoConfig.stream_size
        elif conf == "Raw Photo":
            size = cfg.rawConfig.stream_size
        elif conf == "Video":
            size = cfg.videoConfig.stream_size
        else:
            size = None
        if not size is None:
            log = f"Changed Stream Size for {conf} from {size} to "
            aspRatio = size[0] / size[1]
            if aspRatio != aspRatioRef:
                width = size[0]
                height = round(size[0] / aspRatioRef)
                if not (height % 2) == 0:
                    height += 1
                if height > cfg.cameraProperties.pixelArraySize[1]:
                    height = cfg.cameraProperties.pixelArraySize[1]
                    width = round(height * aspRatioRef)
                    if not (width % 2) == 0:
                        width += 1
                size = (width, height)
                
                sm = "custom"
                for mode in cfg.sensorModes:
                    if mode.size[0] == width \
                    and mode.size[1] == height:
                        sm = str(mode.id)
                        break
                    
                logger.debug(log + str(size))
                if conf == "Live View":
                    cfg.liveViewConfig.stream_size = size
                    cfg.liveViewConfig.sensor_mode = sm
                    ret = True
                elif conf == "Photo":
                    cfg.photoConfig.stream_size = size
                    cfg.photoConfig.sensor_mode = sm
                elif conf == "Raw Photo":
                    cfg.rawConfig.stream_size = size
                    cfg.rawConfig.sensor_mode = sm
                elif conf == "Video":
                    cfg.videoConfig.stream_size = size
                    cfg.videoConfig.sensor_mode = sm
                else:
                    pass
    logger.debug("doSyncAspectRatio %s", ret)
    return ret

@bp.route("/syncAspectRatio", methods=("GET", "POST"))
@login_required
def syncAspectRatio():
    logger.debug("In syncAspectRatio")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        lastTab = sc.lastConfigTab
        selTab = request.form.get("activecfgtab")
        if selTab != "-":
            lastTab = selTab
        sc.lastConfigTab = lastTab
        syncAspectRatio = not request.form.get("syncaspectratio") is None
        sc.syncAspectRatio = syncAspectRatio
        logger.debug("syncAspectRatio - lastTab: %s", lastTab)
        if syncAspectRatio == True:
            if lastTab == "cfglive":
                aspRef = cfglive.stream_size
                aspTgt = ["Photo", "Raw Photo", "Video"]
                doSyncAspectRatio(aspRef, aspTgt)
            elif lastTab == "cfgphoto":
                aspRef = cfgphoto.stream_size
                aspTgt = ["Live View", "Raw Photo", "Video"]
                doSyncAspectRatio(aspRef, aspTgt)
            elif lastTab == "cfgraw":
                aspRef = cfgraw.stream_size
                aspTgt = ["Live View", "Photo", "Video"]
                doSyncAspectRatio(aspRef, aspTgt)
            elif lastTab == "cfgvideo":
                aspRef = cfgvideo.stream_size
                aspTgt = ["Live View", "Photo", "Raw Photo"]
                doSyncAspectRatio(aspRef, aspTgt)
            else:
                pass
            Camera.resetScalerCropRequested = True
            Camera().restartLiveStream()
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

def findTuningFile(tuning_file: str, dir=None) -> str:
    """Find the given tuning file and return its path

    Code has been copied from Picamera2.load_tuning_file(...)
    Args:
        - tuning_file (str): filename of tuning file
        - dir (str, optional): Directory to search. If None, search standard installation dirs

    Returns:
        - str: Path of tuning file; None, if not found
    """
    tfPath = None
    if dir is not None:
        dirs = [dir]
    else:
        if usePlatform:
            platform_dir = "vc4" if Picamera2.platform == Platform.Platform.VC4 else "pisp"
            dirs = [os.path.expanduser("~/libcamera/src/ipa/rpi/" + platform_dir + "/data"),
                    "/usr/local/share/libcamera/ipa/rpi/" + platform_dir,
                    "/usr/share/libcamera/ipa/rpi/" + platform_dir]
        else: 
             dirs = [os.path.expanduser("~/libcamera/src/ipa/rpi/vc4/data"),
                    "/usr/local/share/libcamera/ipa/rpi/vc4",
                    "/usr/share/libcamera/ipa/rpi/vc4"]                       
    for directory in dirs:
        file = os.path.join(directory, tuning_file)
        if os.path.isfile(file):
            tfPath = file
    return tfPath

def isTuningFile(file: str, folder:str) -> bool:
    logger.debug("In isTuningFile")
    logger.debug("isTuningFile - file=%s", file)
    logger.debug("isTuningFile - folder=%s", folder)
    res = False
    try:
        tf = Picamera2.load_tuning_file(file, folder)
        res = True
    except RuntimeError as e:
        res = False
    logger.debug("isTuningFile - res=%s", res)
    return res
    
def getTuningFiles(folder, defFile) -> list:
    """Create a list of all .json files in the given folder

    Args:
        - folder (str): Folder to search
        - defFile (str): Name of default file
    Returns:
        - list: list with filenames of .json files
    """
    tfl = []
    defFileFound = False
    if folder is not None:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if os.path.isfile(os.path.join(folder, f)):
                    if f == defFile:
                        defFileFound = True
                    nam, ext = os.path.splitext(f)
                    if ext.lower() == ".json":
                        tfl.append(f)
    if defFile:
        if defFileFound == False:
            tfl.append(defFile)
    return tfl

@bp.route("/tuningCfg", methods=("GET", "POST"))
@login_required
def tuningCfg():
    logger.debug("In tuningCfg")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgtuning"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        msg = ""
        restart = False
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the tuning configuration"
            msg = err
        if sc.isPhotoSeriesRecording:
            err = "Please go to 'Photo Series' and stop the active process before changing the tuning configuration"
            msg = err
        if sc.isVideoRecording == True:
            err = "Please stop video recording before changing the tuning configuration"
            msg = err
        if not err:
            loadTuningFile = not request.form.get("loadtuningfile") is None
            fd = request.form["tuningfolder"]
            if fd == "":
                fd = None
            fn = request.form["tuningfile"]
            if loadTuningFile:
                if isTuningFile(fn, fd) == True:
                    tc.tuningFolder = fd
                    tc.tuningFile = fn
                    tc.loadTuningFile = loadTuningFile
                    restart = True
                else:
                    msg = "Specify an existing tuning file before activating to load it"
            else:
                tc.tuningFolder = fd
                tc.tuningFile = fn
                if tc.loadTuningFile != loadTuningFile:
                    restart = True
                tc.loadTuningFile = loadTuningFile
        if restart:
            Camera().restartLiveStream()
        if len(msg) > 0:
            flash(msg)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/customTuning", methods=("GET", "POST"))
@login_required
def customTuning():
    logger.debug("In customTuning")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgtuning"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        msg = ""
        restart = False
        if tc.loadTuningFile == True:
            if sc.isTriggerRecording:
                err = "Please go to 'Trigger' and stop the active process before changing the tuning configuration"
                msg = err
            if sc.isPhotoSeriesRecording:
                err = "Please go to 'Photo Series' and stop the active process before changing the tuning configuration"
                msg = err
            if sc.isVideoRecording == True:
                err = "Please stop video recording before changing the tuning configuration"
                msg = err
        if not err:
            fd = tc.tuningFolder
            fn = tc.tuningFile
            fdCustom = current_app.static_folder + "/tuning"
            if fd == fdCustom:
                msg = "No changes. Custom folder was already set."
            else:
                try:
                    os.makedirs(fdCustom, exist_ok=True)
                    tc.tuningFolder = fdCustom
                except Exception as e:
                    msg = "Error while creating custom folder " + fdCustom + ":" + e
                if msg == "":
                    if fn != "":
                        if isTuningFile(fn, fdCustom) == True:
                            if tc.loadTuningFile == True:
                                msg = "Tuning file switched to custom file."
                                restart = True
                        else:
                            if isTuningFile(fn, None) == True:
                                fpCustom = os.path.join(fdCustom, fn)
                                fpDefault = findTuningFile(fn, None)
                                if fpDefault is not None:
                                    try:
                                        shutil.copyfile(fpDefault, fpCustom)
                                        msg = "Tuning file " + fn + " copied to custom directory."
                                        if tc.loadTuningFile == True:
                                            restart = True
                                    except Exception as e:
                                        logger.debug("error while copying tuning file: %s", str(e))
                                        msg = "Tuning file directory switched to custom directory, but tuning file " + fn + " could not be copied."
                                        fn = ""
                                        if tc.loadTuningFile == True:
                                            restart = True
                                        tc.loadTuningFile = False
                                else:
                                    tc.tuningFile = ""
                                    if tc.loadTuningFile == True:
                                        restart = True
                                        tc.loadTuningFile = False
                            else:
                                tc.tuningFile = ""
                                if tc.loadTuningFile == True:
                                    restart = True
                                    tc.loadTuningFile = False
        if restart:
            Camera().restartLiveStream()
        if len(msg) > 0:
            flash(msg)
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/defaultTuning", methods=("GET", "POST"))
@login_required
def defaultTuning():
    logger.debug("In defaultTuning")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgtuning"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        msg = ""
        restart = False
        if tc.loadTuningFile == True:
            if sc.isTriggerRecording:
                err = "Please go to 'Trigger' and stop the active process before changing the tuning configuration"
                msg = err
            if sc.isPhotoSeriesRecording:
                err = "Please go to 'Photo Series' and stop the active process before changing the tuning configuration"
                msg = err
            if sc.isVideoRecording == True:
                err = "Please stop video recording before changing the tuning configuration"
                msg = err
        if not err:
            fd = tc.tuningFolder
            fn = tc.tuningFile
            fdDefault = tc.tuningFolderDef
            if fd == fdDefault:
                msg = "No changes. Default folder was already set."
            else:
                tc.tuningFolder = fdDefault
                if fn != "":
                    if isTuningFile(fn, fd) == True:
                        if tc.loadTuningFile == True:
                            msg = "Tuning file switched to default file."
                            restart = True
                    else:
                        fn = sc.activeCameraModel + ".json"
                        if isTuningFile(fn, fd) == True:
                            tc.tuningFile = fn
                            if tc.loadTuningFile == True:
                                msg = "Tuning file switched to default file."
                                restart = True
                        else:
                            tc.tuningFile = ""
                            if tc.loadTuningFile == True:
                                restart = True
        if restart:
            Camera().restartLiveStream()
        if len(msg) > 0:
            flash(msg)
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/deleteTuningFile", methods=("GET", "POST"))
@login_required
def deleteTuningFile():
    logger.debug("In deleteTuningFile")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgtuning"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        restart = False
        if tc.isDefaultFolder == True:
            msg = "You cannot delete a tuning file from the default folder"
        else:
            fd = tc.tuningFolder
            fn = tc.tuningFile
            fp = findTuningFile(fn, fd)
            if fp is not None:
                os.remove(fp)
                msg = f"Tuning File deleted: {fp}"
            else:
                msg = "Tuning file not found"
            tc.tuningFile = ""
            if tc.loadTuningFile == True:
                restart = True
                tc.loadTuningFile = False
        tfl = getTuningFiles(tc.tuningFolder, None)
        if len(tfl) > 0:
            fn = sc.activeCameraModel + ".json"
            found = False
            for f in tfl:
                if f == fn:
                    tc.tuningFile = fn
                    found = True
                    break
            if found == False:
                tc.tuningFile = tfl[0]
        else:
            logger.debug("deleteTuningFile - No more tuning files in custom folder")
            fn = sc.activeCameraModel + ".json"
            tc.tuningFolder = None
            logger.debug("deleteTuningFile - fn=%s tuningFolder=%s isTuningFile=%s", fn, tc.tuningFolder, isTuningFile(fn, tc.tuningFolder))
            if isTuningFile(fn, tc.tuningFolder) == True:
                tc.tuningFile = fn
                logger.debug("deleteTuningFile - tc.tuningFile set to %s", tc.tuningFile)
            else:
                tc.loadTuningFile = False
        tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
        if restart:
            Camera().restartLiveStream()
        if msg != "":
            flash(msg)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/downloadTuningFile", methods=("GET", "POST"))
@login_required
def downloadTuningFile():
    logger.debug("In downloadTuningFile")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgtuning"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        fd = tc.tuningFolder
        fn = tc.tuningFile
        fp = findTuningFile(fn, fd)
        if fp is not None:
            msg = f"Downloading {fn}"
            flash(msg)
            return send_file(
                fp,
                as_attachment=True,
                download_name=fn
            )
        else:
            msg = "Tuning file not found"
            flash(msg)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/uploadTuningFile", methods=("GET", "POST"))
@login_required
def uploadTuningFile():
    logger.debug("In uploadTuningFile")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgtuning"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        msg = ""
        if tc.tuningFolder is None:
            msg = "You may only upload to a custom folder!"
        else:
            if os.path.exists(tc.tuningFolder) == False:
                try:
                    os.makedirs(tc.tuningFolder)
                except Exception as e:
                    msg = f"Error creating folder {tc.tuningFolder}: {str(e)}"
        if msg == "":
            if "tuningfile" not in request.files:
                msg = "No file to save"
            else:
                files = request.files.getlist("tuningfile")
                countSel = len(files)
                #tf = request.files["tuningfile"]
                logger.debug("uploadTuningFile - %s files selected", countSel)
                countUp = 0
                for tf in files:
                    fn = tf.filename
                    logger.debug("uploadTuningFile - selected file: %s", fn)
                    nam, ext = os.path.splitext(fn)
                    if ext.lower() == ".json":
                        fp = os.path.join(tc.tuningFolder, fn)
                        tf.save(fp)
                        msg = f"Tuning file saved as {fp}."
                        countUp += 1
                if countSel > 1:
                    msg = f"{countUp} of {countSel} files uploaded."
                    if countUp < countSel:
                        msg = msg + " Not all files were .json files."
        if msg != "":
            flash(msg)
        tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/liveViewCfg", methods=("GET", "POST"))
@login_required
def liveViewCfg():
    logger.debug("In liveViewCfg")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfglive"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
            msg = err
        if not err:
            transform_hflip = not request.form.get("LIVE_transform_hflip") is None
            cfglive.transform_hflip = transform_hflip        
            transform_vflip = not request.form.get("LIVE_transform_vflip") is None
            cfglive.transform_vflip = transform_vflip
            colour_space = request.form["LIVE_colour_space"]
            cfglive.colour_space = colour_space
            buffer_count = int(request.form["LIVE_buffer_count"])
            cfglive.buffer_count = buffer_count
            queue = not request.form.get("LIVE_queue") is None
            cfglive.queue = queue
            stream = request.form["LIVE_stream"]
            sensor_mode = request.form["LIVE_sensor_mode"]
            if sensor_mode == "custom":
                size_width = int(request.form["LIVE_stream_size_width"])
                if not (size_width % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                size_height = int(request.form["LIVE_stream_size_height"])
                if not (size_height % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                if stream == "lores":
                    if cfgphoto.stream == "main":
                        if size_width > cfgphoto.stream_size[0] \
                        or size_height > cfgphoto.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Photo)"
                    if not err \
                    and cfgvideo.stream == "main":
                        if size_width > cfgvideo.stream_size[0] \
                        or size_height > cfgvideo.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Video)"
                if stream == "main":
                    if cfgphoto.stream == "lores":
                        if size_width < cfgphoto.stream_size[0] \
                        or size_height < cfgphoto.stream_size[1]:
                            err = "lores Stream Size (Photo) must not exceed main Stream Size"
                    if not err \
                    and cfgvideo.stream == "lores":
                        if size_width < cfgvideo.stream_size[0] \
                        or size_height < cfgvideo.stream_size[1]:
                            err = "lores Stream Size (Video) must not exceed main Stream Size"
                if not err:
                    cfglive.stream = stream
                    cfglive.sensor_mode = sensor_mode
                    cfglive.stream_size = (size_width, size_height)
                    cfglive.stream_size_align = not request.form.get("LIVE_stream_size_align") is None
            else:
                mode = sm[int(sensor_mode)]
                if stream == "lores":
                    if cfgphoto.stream == "main":
                        if mode.size[0] > cfgphoto.stream_size[0] \
                        or mode.size[1] > cfgphoto.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Photo)"
                    if not err \
                    and cfgvideo.stream == "main":
                        if mode.size[0] > cfgvideo.stream_size[0] \
                        or mode.size[1] > cfgvideo.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Video)"
                if stream == "main":
                    if cfgphoto.stream == "lores":
                        if mode.size[0] < cfgphoto.stream_size[0] \
                        or mode.size[1] < cfgphoto.stream_size[1]:
                            err = "lores Stream Size (Photo) must not exceed main Stream Size"
                    if not err \
                    and cfgvideo.stream == "lores":
                        if mode.size[0] < cfgvideo.stream_size[0] \
                        or mode.size[1] < cfgvideo.stream_size[1]:
                            err = "lores Stream Size (Video) must not exceed main Stream Size"
                if not err:
                    cfglive.stream = stream
                    cfglive.sensor_mode = sensor_mode
                    cfglive.stream_size = mode.size
                    cfglive.stream_size_align = not request.form.get("LIVE_stream_size_align") is None
            format = request.form["LIVE_format"]
            cfglive.display = None
            cfglive.encode = cfglive.stream
            if sc.syncAspectRatio == True:
                doSyncAspectRatio(cfglive.stream_size, ["Photo", "Raw Photo", "Video"])
            Camera.resetScalerCropRequested = True
            doSyncTransform(transform_hflip, transform_vflip, ["Photo", "Raw Photo", "Video"])
            Camera().restartLiveStream()

            msg = ""
            if err:
                msg = err
            if sc.raspiModelLower5:
                if cfglive.stream == "lores":
                    if format == "YUV420":
                        cfglive.format = format
                    else:
                        if msg != "":
                            msg = msg + "\n"
                        msg = msg + "For Raspberry Pi models < 5, the lowres stream format must be YUV"
                else:
                    cfglive.format = format
            else:
                cfglive.format = format

            if cfglive.stream != "lores":
                if msg != "":
                    msg = msg + "\n"
                msg = msg + "WARNING: If you do not set Stream to 'lores', the Live Stream cannot be shown parallel to other activities!"
        if len(msg) > 0:
            flash(msg)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/addLiveViewControls", methods=("GET", "POST"))
@login_required
def addLiveViewControls():
    logger.debug("In addLiveViewControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfglive"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            for key, value in cc.dict().items():
                if value[0] == True:
                    if key not in cfg.liveViewConfig.controls:
                        cfg.liveViewConfig.controls[key] = value[1]
            Camera().restartLiveStream()
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/remLiveViewControls", methods=("GET", "POST"))
@login_required
def remLiveViewControls():
    logger.debug("In remLiveViewControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfglive"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            cnt = 0
            for ctrl in cfg.liveViewConfig.controls:
                logger.debug("Checking checkbox ID:" + "sel_LIVE_" + ctrl)
                if request.form.get("sel_LIVE_" + ctrl) is not None:
                    cnt += 1
            logger.debug("Nr controls: %s - selected: %s", len(cfg.liveViewConfig.controls), cnt)
            if cnt > 0:
                if cnt < len(cfg.liveViewConfig.controls):
                    while cnt > 0:
                        for ctrl in cfg.liveViewConfig.controls:
                            if request.form.get("sel_LIVE_" + ctrl) is not None:
                                ctrlDel = ctrl
                                break
                        del cfg.liveViewConfig.controls[ctrlDel]
                        cnt -= 1
                    Camera().restartLiveStream()
                else:
                    msg="At least one control must remain in the configuration"
                    flash(msg)
            else:
                msg="No controls were selected"
                flash(msg)
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/photoCfg", methods=("GET", "POST"))
@login_required
def photoCfg():
    logger.debug("In photoCfg")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgphoto"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            transform_hflip = not request.form.get("FOTO_transform_hflip") is None
            cfgphoto.transform_hflip = transform_hflip        
            transform_vflip = not request.form.get("FOTO_transform_vflip") is None
            cfgphoto.transform_vflip = transform_vflip
            colour_space = request.form["FOTO_colour_space"]
            cfgphoto.colour_space = colour_space
            buffer_count = int(request.form["FOTO_buffer_count"])
            cfgphoto.buffer_count = buffer_count
            queue = not request.form.get("FOTO_queue") is None
            cfgphoto.queue = queue
            stream = request.form["FOTO_stream"]
            sensor_mode = request.form["FOTO_sensor_mode"]
            if sensor_mode == "custom":
                size_width = int(request.form["FOTO_stream_size_width"])
                if not (size_width % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                size_height = int(request.form["FOTO_stream_size_height"])
                if not (size_height % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                if stream == "lores":
                    if cfglive.stream == "main":
                        if size_width > cfglive.stream_size[0] \
                        or size_height > cfglive.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Live View)"
                    if not err \
                    and cfgvideo.stream == "main":
                        if size_width > cfgvideo.stream_size[0] \
                        or size_height > cfgvideo.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Video)"
                if stream == "main":
                    if cfglive.stream == "lores":
                        if size_width < cfglive.stream_size[0] \
                        or size_height < cfglive.stream_size[1]:
                            err = "lores Stream Size (Live View) must not exceed main Stream Size"
                    if not err \
                    and cfgvideo.stream == "lores":
                        if size_width < cfgvideo.stream_size[0] \
                        or size_height < cfgvideo.stream_size[1]:
                            err = "lores Stream Size (Video) must not exceed main Stream Size"
                if not err:
                    cfgphoto.stream = stream
                    cfgphoto.sensor_mode = sensor_mode
                    cfgphoto.stream_size = (size_width, size_height)
                    cfgphoto.stream_size_align = not request.form.get("FOTO_stream_size_align") is None
            else:
                mode = sm[int(sensor_mode)]
                if stream == "lores":
                    if cfglive.stream == "main":
                        if mode.size[0] > cfglive.stream_size[0] \
                        or mode.size[1] > cfglive.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Live View)"
                    if not err \
                    and cfgvideo.stream == "main":
                        if mode.size[0] > cfgvideo.stream_size[0] \
                        or mode.size[1] > cfgvideo.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Video)"
                if stream == "main":
                    if cfglive.stream == "lores":
                        if mode.size[0] < cfglive.stream_size[0] \
                        or mode.size[1] < cfglive.stream_size[1]:
                            err = "lores Stream Size (Live View) must not exceed main Stream Size"
                    if not err \
                    and cfgvideo.stream == "lores":
                        if mode.size[0] < cfgvideo.stream_size[0] \
                        or mode.size[1] < cfgvideo.stream_size[1]:
                            err = "lores Stream Size (Video) must not exceed main Stream Size"
                if not err:
                    cfgphoto.stream = stream
                    cfgphoto.sensor_mode = sensor_mode
                    cfgphoto.stream_size = mode.size
                    cfgphoto.stream_size_align = not request.form.get("FOTO_stream_size_align") is None
            format = request.form["FOTO_format"]
            cfgphoto.format = format
            cfgphoto.display = None
            cfgphoto.encode = "main"
            cc, cr =  Camera().ctrl.requestConfig(cfgphoto, test=True)
            if cc:
                msg = "This modification will cause the live stream to be interrupted when a photo is taken!\nReason: " + cr
                flash(msg)
            if sc.syncAspectRatio == True:
                doSyncAspectRatio(cfgphoto.stream_size, ["Live View", "Raw Photo", "Video"])
            Camera.resetScalerCropRequested = True
            doSyncTransform(transform_hflip, transform_vflip, ["Live View", "Raw Photo", "Video"])
            Camera().restartLiveStream()
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/addPhotoControls", methods=("GET", "POST"))
@login_required
def addPhotoControls():
    logger.debug("In addPhotoControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgphoto"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            for key, value in cc.dict().items():
                if value[0] == True:
                    if key not in cfg.photoConfig.controls:
                        cfg.photoConfig.controls[key] = value[1]
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/remPhotoControls", methods=("GET", "POST"))
@login_required
def remPhotoControls():
    logger.debug("In remPhotoControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgphoto"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            cnt = 0
            for ctrl in cfg.photoConfig.controls:
                if request.form.get("sel_FOTO_" + ctrl) is not None:
                    cnt += 1
            if cnt > 0:
                if cnt < len(cfg.photoConfig.controls):
                    while cnt > 0:
                        for ctrl in cfg.photoConfig.controls:
                            if request.form.get("sel_FOTO_" + ctrl) is not None:
                                ctrlDel = ctrl
                                break
                        del cfg.photoConfig.controls[ctrlDel]
                        cnt -= 1
                else:
                    msg="At least one control must remain in the configuration"
                    flash(msg)
            else:
                msg="No controls were selected"
                flash(msg)
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/rawCfg", methods=("GET", "POST"))
@login_required
def rawCfg():
    logger.debug("In rawCfg")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgraw"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg.rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            transform_hflip = not request.form.get("PRAW_transform_hflip") is None
            cfgraw.transform_hflip = transform_hflip        
            transform_vflip = not request.form.get("PRAW_transform_vflip") is None
            cfgraw.transform_vflip = transform_vflip
            colour_space = request.form["PRAW_colour_space"]
            cfgraw.colour_space = colour_space
            queue = not request.form.get("PRAW_queue") is None
            cfgraw.queue = queue
            sensor_mode = request.form["PRAW_sensor_mode"]
            if sensor_mode == "custom":
                size_width = int(request.form["PRAW_stream_size_width"])
                if not (size_width % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                size_height = int(request.form["PRAW_stream_size_height"])
                if not (size_height % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                if not err:
                    cfgraw.sensor_mode = sensor_mode
                    cfgraw.stream_size = (size_width, size_height)
                    cfgraw.stream_size_align = not request.form.get("PRAW_stream_size_align") is None
            else:
                mode = sm[int(sensor_mode)]
                if not err:
                    cfgraw.sensor_mode = sensor_mode
                    cfgraw.stream_size = mode.size
                    cfgraw.stream_size_align = not request.form.get("PRAW_stream_size_align") is None
            cfgraw.sensor_mode = sensor_mode
            format = request.form["PRAW_format"]
            cfgraw.format = format
            cfgraw.display = None
            cfgraw.encode = None
            if sc.syncAspectRatio == True:
                doSyncAspectRatio(cfgraw.stream_size, ["Live View", "Photo", "Video"])
            Camera.resetScalerCropRequested = True
            doSyncTransform(transform_hflip, transform_vflip, ["Live View", "Photo", "Video"])
            Camera().restartLiveStream()
        if err:
            flash(err)            
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/addRawControls", methods=("GET", "POST"))
@login_required
def addRawControls():
    logger.debug("In addRawControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgraw"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            for key, value in cc.dict().items():
                if value[0] == True:
                    if key not in cfg.rawConfig.controls:
                        cfg.rawConfig.controls[key] = value[1]
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/remRawControls", methods=("GET", "POST"))
@login_required
def remRawControls():
    logger.debug("In remRawControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgraw"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            cnt = 0
            for ctrl in cfg.rawConfig.controls:
                if request.form.get("sel_PRAW_" + ctrl) is not None:
                    cnt += 1
            if cnt > 0:
                if cnt < len(cfg.rawConfig.controls):
                    while cnt > 0:
                        for ctrl in cfg.rawConfig.controls:
                            if request.form.get("sel_PRAW_" + ctrl) is not None:
                                ctrlDel = ctrl
                                break
                        del cfg.rawConfig.controls[ctrlDel]
                        cnt -= 1
                else:
                    msg="At least one control must remain in the configuration"
                    flash(msg)
            else:
                msg="No controls were selected"
                flash(msg)
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/videoCfg", methods=("GET", "POST"))
@login_required
def videoCfg():
    logger.debug("In videoCfg")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgvideo"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            transform_hflip = not request.form.get("VIDO_transform_hflip") is None
            cfgvideo.transform_hflip = transform_hflip        
            transform_vflip = not request.form.get("VIDO_transform_vflip") is None
            cfgvideo.transform_vflip = transform_vflip
            colour_space = request.form["VIDO_colour_space"]
            cfgvideo.colour_space = colour_space
            buffer_count = int(request.form["VIDO_buffer_count"])
            cfgvideo.buffer_count = buffer_count
            queue = not request.form.get("VIDO_queue") is None
            cfgvideo.queue = queue
            stream = request.form["VIDO_stream"]
            sensor_mode = request.form["VIDO_sensor_mode"]
            if sensor_mode == "custom":
                size_width = int(request.form["VIDO_stream_size_width"])
                if not (size_width % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                size_height = int(request.form["VIDO_stream_size_height"])
                if not (size_height % 2) == 0:
                    err = "Stream Size (width, height) must be even"
                if stream == "lores":
                    if cfglive.stream == "main":
                        if size_width > cfglive.stream_size[0] \
                        or size_height > cfglive.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Live View)"
                    if not err \
                    and cfgphoto.stream == "main":
                        if size_width > cfgphoto.stream_size[0] \
                        or size_height > cfgphoto.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Photo)"
                if stream == "main":
                    if cfglive.stream == "lores":
                        if size_width < cfglive.stream_size[0] \
                        or size_height < cfglive.stream_size[1]:
                            err = "lores Stream Size (Live View) must not exceed main Stream Size"
                    if not err \
                    and cfgphoto.stream == "lores":
                        if size_width < cfgphoto.stream_size[0] \
                        or size_height < cfgphoto.stream_size[1]:
                            err = "lores Stream Size (Photo) must not exceed main Stream Size"
                if not err:
                    cfgvideo.stream = stream
                    cfgvideo.sensor_mode = sensor_mode
                    cfgvideo.stream_size = (size_width, size_height)
                    cfgvideo.stream_size_align = not request.form.get("VIDO_stream_size_align") is None
            else:
                mode = sm[int(sensor_mode)]
                if stream == "lores":
                    if cfglive.stream == "main":
                        if mode.size[0] > cfglive.stream_size[0] \
                        or mode.size[1] > cfglive.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Live View)"
                    if not err \
                    and cfgphoto.stream == "main":
                        if mode.size[0] > cfgphoto.stream_size[0] \
                        or mode.size[1] > cfgphoto.stream_size[1]:
                            err = "lores Stream Size must not exceed main Stream Size (Photo)"
                if stream == "main":
                    if cfglive.stream == "lores":
                        if mode.size[0] < cfglive.stream_size[0] \
                        or mode.size[1] < cfglive.stream_size[1]:
                            err = "lores Stream Size (Live View) must not exceed main Stream Size"
                    if not err \
                    and cfgphoto.stream == "lores":
                        if mode.size[0] < cfgphoto.stream_size[0] \
                        or mode.size[1] < cfgphoto.stream_size[1]:
                            err = "lores Stream Size (Photo) must not exceed main Stream Size"
                if not err:
                    cfgvideo.stream = stream
                    cfgvideo.sensor_mode = sensor_mode
                    cfgvideo.stream_size = mode.size
                    cfgvideo.stream_size_align = not request.form.get("VIDO_stream_size_align") is None
            format = request.form["VIDO_format"]
            cfgvideo.format = format
            cfgvideo.display = None
            cfgvideo.encode = "main"
            if sc.syncAspectRatio == True:
                doSyncAspectRatio(cfgvideo.stream_size, ["Live View", "Photo", "Raw Photo"])
            Camera.resetScalerCropRequested = True
            doSyncTransform(transform_hflip, transform_vflip, ["Live View", "Photo", "Raw Photo"])
            Camera().restartLiveStream()
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/addVideoControls", methods=("GET", "POST"))
@login_required
def addVideoControls():
    logger.debug("In addVideoControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cc = cfg.controls
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgvideo"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            for key, value in cc.dict().items():
                if value[0] == True:
                    if key not in cfg.videoConfig.controls:
                        cfg.videoConfig.controls[key] = value[1]
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)

@bp.route("/remVideoControls", methods=("GET", "POST"))
@login_required
def remVideoControls():
    logger.debug("In remVideoControls")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    rf = cfg.rawFormats
    sc = cfg.serverConfig
    tc = cfg.tuningConfig
    sc.lastConfigTab = "cfgvideo"
    cfgs = cfg.cameraConfigs
    cfglive = cfg.liveViewConfig
    cfgphoto = cfg.photoConfig
    cfgraw = cfg._rawConfig
    cfgvideo =cfg.videoConfig
    cfgrf = cfg.rawFormats
    if tc.tuningFile == "":
        fn = sc.activeCameraModel + ".json"
        if isTuningFile(fn, tc.tuningFolder) == True:
            tc.tuningFile = fn
    tfl = getTuningFiles(tc.tuningFolder, tc.tuningFile)
    if request.method == "POST":
        err = None
        if sc.isTriggerRecording:
            err = "Please go to 'Trigger' and stop the active process before changing the configuration"
        if not err:
            cnt = 0
            for ctrl in cfg.videoConfig.controls:
                if request.form.get("sel_VIDO_" + ctrl) is not None:
                    cnt += 1
            if cnt > 0:
                if cnt < len(cfg.videoConfig.controls):
                    while cnt > 0:
                        for ctrl in cfg.videoConfig.controls:
                            if request.form.get("sel_VIDO_" + ctrl) is not None:
                                ctrlDel = ctrl
                                break
                        del cfg.videoConfig.controls[ctrlDel]
                        cnt -= 1
                else:
                    msg="At least one control must remain in the configuration"
                    flash(msg)
            else:
                msg="No controls were selected"
                flash(msg)
        if err:
            flash(err)
    return render_template("config/main.html", sc=sc, tc=tc, cp=cp, sm=sm, rf=rf, cfglive=cfglive, cfgphoto=cfgphoto, cfgraw=cfgraw, cfgvideo=cfgvideo, cfgrf=cfgrf, cfgs=cfgs, tfl=tfl)
