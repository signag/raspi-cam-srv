import functools

from flask import (
    g,
    redirect,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from raspiCamSrv.camCfg import CameraCfg

from raspiCamSrv.db import get_db
import logging

logger = logging.getLogger(__name__)

def superuser_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        logger.debug("superuser_required. g.user: %s", g.user)
        if g.user is None:
            db = get_db()
            nrUsers = 0
            try:
                nrUsers = db.execute("SELECT COUNT(*) from user").fetchone()[0]
            except db.Error as e:
                logger.error("Database error: %s", e)
                nrUsers = 0
            if nrUsers > 0:
                logger.debug("found %s users. Redirecting to login", nrUsers)
                return redirect(url_for("auth.login"))
        else:
            if g.user["issuperuser"] == 0:
                logger.debug("Logged-In user is not SuperUser. Redirecting to index")
                return redirect(url_for("index"))
        logger.debug("Allowing access")
        return view(**kwargs)

    return wrapped_view
