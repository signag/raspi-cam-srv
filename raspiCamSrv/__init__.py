import os
from pathlib import Path
from flask import Flask
import logging
from flask.logging import default_handler
from picamera2 import Picamera2

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "raspiCamSrv.sqlite"),
    )

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Configure loggers
    #Path(app.instance_path + "/raspiCamSrv.log").touch(exist_ok=True)
    #filehandler = logging.FileHandler(app.instance_path + "/raspiCamSrv.log")
    #filehandler.setFormatter(app.logger.handlers[0].formatter)
    for logger in(
        app.logger,
        logging.getLogger("werkzeug"),
        logging.getLogger("raspiCamSrv.camCfg"),
        logging.getLogger("raspiCamSrv.camera_base"),
        logging.getLogger("raspiCamSrv.camera_pi"),
        logging.getLogger("raspiCamSrv.config"),
        logging.getLogger("raspiCamSrv.home"),
        logging.getLogger("raspiCamSrv.images"),
        logging.getLogger("raspiCamSrv.info"),
        logging.getLogger("raspiCamSrv.settings"),
        logging.getLogger("raspiCamSrv.timelapse"),
        logging.getLogger("raspiCamSrv.timelapseCfg"),
    ):
        #logger.addHandler(filehandler)
        logger.setLevel(logging.ERROR)
    
    #Explicitely set specific log levels
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    
    #Set log level for picamera2 (DEBUG, INFO, WARNING, ERROR)
    Picamera2.set_logging(Picamera2.ERROR)
    
    #Set log level for libcamera (0:DEBUG, 1:INFO, 2:WARNING, 3:ERROR, 4:FATAL)
    os.environ["LIBCAMERA_LOG_LEVELS"] = "*:2"           

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # Make database available in the application context
    from . import db
    db.init_app(app)
    
    # Configure Config
    from . import camCfg
    from . import settings
    cfg = camCfg.CameraCfg()
    sc = cfg.serverConfig
    sc.photoRoot = app.static_folder
    sc.checkEnvironment()
    cfgPath = app.static_folder + "/config"
    if settings.getLoadConfigOnStart(cfgPath):
        cfg.loadConfig(cfgPath)
    
    # Configure Timelapse
    from . import timelapseCfg
    tlRootPath = app.static_folder + "/timelapse"
    os.makedirs(tlRootPath, exist_ok=True)
    tlCfg = timelapseCfg.TimelapseCfg()
    tlCfg.rootPath = tlRootPath
    tlCfg.initFromTlFolder()
    
    # Register required blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import home
    app.register_blueprint(home.bp)
    app.add_url_rule("/", endpoint="index")

    from . import config
    app.register_blueprint(config.bp)

    from . import images
    app.register_blueprint(images.bp)

    from . import info
    app.register_blueprint(info.bp)

    from . import settings
    app.register_blueprint(settings.bp)

    from . import timelapse
    app.register_blueprint(timelapse.bp)

    return app
