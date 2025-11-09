from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg, TuningConfig
from raspiCamSrv.version import version
import threading

from raspiCamSrv.auth import login_required
import logging

bp = Blueprint("info", __name__)

logger = logging.getLogger(__name__)

@bp.route("/info")
@login_required
def main():
    logger.debug("In info")
    cam = Camera().cam
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    cs = cfg.cameras
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sm = cfg.sensorModes
    logger.debug("In info - len(sm): %s", len(sm))
    tcs = {}
    for c in cs:
        camnum = str(c.num)
        if c.num == sc.activeCamera:
            tcs[camnum] = cfg.tuningConfig
        else:
            strc = cfg.streamingCfg
            if camnum in strc:
                cstrc = strc[camnum]
                if "tuningconfig" in cstrc:
                    tcs[camnum] = cstrc["tuningconfig"]
                else:
                    tcs[camnum] = []
            else:
                tcs[camnum] = TuningConfig()
        c.status = Camera.cameraStatus(c.num)
    # Update streaming clients
    sc.updateStreamingClients()
    sc.curMenu = "info"
    return render_template("info/info.html", sm=sm, sc=sc, tcs=tcs, cp=cp, cs=cs, cfg=cfg)
