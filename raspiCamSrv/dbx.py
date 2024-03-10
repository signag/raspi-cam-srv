import sqlite3

import raspiCamSrv.camCfg as camCfg
import logging

logger = logging.getLogger(__name__)


def get_dbx():
    """ Get database outside of application context
    """
    database = camCfg.CameraCfg().serverConfig.database
    logger.debug("get_dbx - database: %s", database)
    db = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db
