import functools
from raspiCamSrv.version import version

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from raspiCamSrv.camCfg import CameraCfg

from raspiCamSrv.db import get_db
from raspiCamSrv.auth_su import superuser_required
import logging

bp = Blueprint("auth", __name__, url_prefix="/auth")

logger = logging.getLogger(__name__)

@bp.route("/register", methods=("GET", "POST"))
@superuser_required
def register():
    logger.debug("In register")
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "register"
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        
        # Get number of registered users
        nrUsers = 0
        try:
            nrUsers = db.execute("SELECT COUNT(*) from user").fetchone()[0]
        except db.Error as e:
            logger.error("Database error: %s", e)
            nrUsers = 0
        logger.debug("Found %s users", nrUsers)
            
        error = None
        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            if nrUsers == 0:
                isSuperUser = 1
                isInitial = 0
            else:
                isSuperUser = 0
                isInitial = 1

            schemaOK = True
            try:
                db.execute(
                    "INSERT INTO user (username, password, issuperuser, isinitial) VALUES (?, ?, ?, ?)",
                    (username, generate_password_hash(password), isSuperUser, isInitial),
                )
                db.commit()
                logger.debug("Insert with new schema OK")
            except db.IntegrityError:
                error = f"User {username} is already registered."
            except db.OperationalError:
                logger.debug("Got OperationalError")
                schemaOK = False
                
            if not schemaOK:
                # Try with old db schema
                logger.debug("Traying with old schema")
                try:
                    db.execute(
                        "INSERT INTO user (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    db.commit()
                    logger.debug("Insert with old schema OK")
                except db.IntegrityError:
                    error = f"User {username} is already registered."
        if error is None:
            logger.debug("g.user: %s", g.user)
            if g.user:
                return redirect(url_for("settings.main"))
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html", sc=sc, cp=cp)


@bp.route("/login", methods=("GET", "POST"))
def login():
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "login"
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        error = None
        user = db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."

        if error is None:
            if len(user) == 5:
                if user["isinitial"] == 1:
                    return redirect(url_for("auth.password"))
                else:
                    session.clear()
                    session["user_id"] = user["id"]
                    return redirect(url_for("index"))
            else:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("index"))
            
        flash(error)

    return render_template("auth/login.html", sc=sc, cp=cp)

@bp.route("/password", methods=("GET", "POST"))
def password():
    g.hostname = request.host
    g.version = version
    cfg = CameraCfg()
    sc = cfg.serverConfig
    cp = cfg.cameraProperties
    sc.curMenu = "password"
    if request.method == "POST":
        username = request.form["username"]
        oldpassword = request.form["oldpassword"]
        newpassword = request.form["newpassword"]
        newpassword2 = request.form["newpassword2"]
        db = get_db()
        error = None
        user = db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], oldpassword):
            error = "Old password is not correct."

        if error is None:
            if len(newpassword) <= 1:
                error = "New password too short. Must be at least 2 characters."
            elif newpassword2 != newpassword:
                error = "New password repetition incorrect."
        
        if error is None:
            schemaOK = True
            isInitial = 0
            try:
                db.execute(
                    "UPDATE user SET password = ?, isinitial = ? WHERE id = ?",
                    (generate_password_hash(newpassword), isInitial, user["id"]),
                )
                db.commit()
                logger.debug("Update with new schema OK")
            except db.IntegrityError as e:
                error = f"Error {e} during update."
            except db.OperationalError:
                logger.debug("Got OperationalError")
                schemaOK = False
                
            if not schemaOK:
                # Try with old db schema
                logger.debug("Traying with old schema")
                try:
                    db.execute(
                        "UPDATE user SET password = ? WHERE id = ?",
                        (generate_password_hash(newpassword), user["id"]),
                    )
                    db.commit()
                    logger.debug("Update with old schema OK")
                except db.IntegrityError as e:
                    error = f"Error {e} during update."
        
        if error is None:
            return redirect(url_for("auth.login"))
        else:
            flash(error)
    return render_template("auth/password.html", sc=sc, cp=cp)


@bp.before_app_request
def load_logged_in_user():
    logger.debug("In load_logged_in_user")
    user_id = session.get("user_id")
    logger.debug("user_id (session): %s ", user_id)

    if user_id is None:
        g.user = None
    else:
        userdb = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )
        logger.debug("userdb: %s", userdb)
        if userdb == None:
            g.user = None
            session.clear()
        else:
            user = {}
            user["id"] = userdb["id"]
            user["username"] = userdb["username"]
            if len(userdb) == 5:
                user["issuperuser"] = userdb["issuperuser"]
                user["isinitial"] = userdb["isinitial"]
            else:
                user["issuperuser"] = 1
                user["isinitial"] = 0
            g.user = user
    logger.debug("Current user: %s", g.user)
        
    g.nrUsers = get_db().execute("SELECT count(*) FROM user").fetchone()[0]
    logger.debug("Found %s users", g.nrUsers)
    usersdb = get_db().execute("SELECT * FROM user").fetchall()
    
    users = []
    for userdb in usersdb:
        user = {}
        user["id"] = userdb["id"]
        user["username"] = userdb["username"]
        if len(userdb) == 5:
            user["issuperuser"] = userdb["issuperuser"]
            user["isinitial"] = userdb["isinitial"]
        users.append(user)
    g.users = users
    logger.debug("g.users: %s", g.users)        

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        if g.user is None:
            db = get_db()
            nrUsers = 0
            try:
                nrUsers = db.execute("SELECT COUNT(*) from user").fetchone()[0]
            except db.Error as e:
                logger.error("Database error: %s", e)
                nrUsers = 0
            if nrUsers == 0:
                return redirect(url_for("auth.register"))
            else:
                return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view

def login_for_streaming(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        sc = CameraCfg().serverConfig
        if sc.requireAuthForStreaming == True:
            if g.user is None:
                db = get_db()
                nrUsers = 0
                try:
                    nrUsers = db.execute("SELECT COUNT(*) from user").fetchone()[0]
                except db.Error as e:
                    logger.error("Database error: %s", e)
                    nrUsers = 0
                if nrUsers == 0:
                    return redirect(url_for("auth.register"))
                else:
                    return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
