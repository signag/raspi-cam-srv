import os
from flask import Flask
import logging
from flask.logging import default_handler

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "raspiCamSrv.sqlite"),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Make database available in the application context
    from . import db
    db.init_app(app)
    
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
    
    # Configure loggers
    for logger in(
        app.logger,
        logging.getLogger("raspiCamSrv.home"),
        logging.getLogger("raspiCamSrv.camera_base"),
        logging.getLogger("raspiCamSrv.camera_pi"),
        logging.getLogger("raspiCamSrv.config"),
        logging.getLogger("raspiCamSrv.images"),
    ):
        logger.setLevel(logging.ERROR)
    logging.getLogger("raspiCamSrv.camera_pi").setLevel(logging.ERROR),

    return app
