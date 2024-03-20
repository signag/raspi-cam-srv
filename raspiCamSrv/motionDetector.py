from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
import numpy as np
from _thread import get_ident
import threading
import time
from datetime import datetime
from datetime import timedelta
import logging
from raspiCamSrv.dbx import get_dbx

logger = logging.getLogger(__name__)

class MotionDetector():
    """ Class for detection of motion and triggering actions
    

    """
    logger.debug("Thread %s: MotionDetector - setting class variables", get_ident())
    _instance = None
    db = None
    mThread = None
    mThreadStop = False
    eventKey = None
    eventStart = None
    nrPhotos = 0
    lastPhoto = None
    videoStart = None
    videoKey = None
    videoStop = None
    videoEncoder = None
    videoCircOutput = None
    videoName = None


    def __new__(cls):
        logger.debug("Thread %s: MotionDetector.__new__", get_ident())
        if cls._instance is None:
            logger.debug("Thread %s: MotionDetector.__new__ - Instantiating Class", get_ident())
            cls._instance = super(MotionDetector, cls).__new__(cls)
            
        return cls._instance
    
    @classmethod
    def _motionDetected(cls, fCur, fPrv) -> tuple:
        """ Analyze input frames to detect motion
        
        """
        tc = CameraCfg().triggerConfig
        #logger.debug("Thread %s: MotionDetector._motionDetected - algo: %s", get_ident(), tc.motionDetectAlgo)
        motion = False
        
        if tc.motionDetectAlgo == 1:
            (motion, trigger) = cls._motionAlgo_MeanSquare(fCur, fPrv)
        
        return (motion, trigger)
    
    @staticmethod
    def _motionAlgo_MeanSquare(fCur, fPrv) -> tuple:
        """ Mean Square algorithm for motion detection
        
        """
        #logger.debug("Thread %s: MotionDetector._motionAlgo_MeanSquare", get_ident())
        
        motion = False
        msd = np.square(np.subtract(fCur, fPrv)).mean()
        #logger.debug("Thread %s: MotionDetector._motionAlgo_MeanSquare msd: %s", get_ident(), msd)
        if msd > CameraCfg().triggerConfig.msdThreshold:
            motion = True
        #logger.debug("Thread %s: MotionDetector._motionAlgo_MeanSquare - motion: %s", get_ident(), motion)
        return (motion, {"trigger":"Motion Detection", "triggertype":"Mean Square Diff", "triggerparam":"msd: " + str(round(msd, 3))})
    
    @classmethod
    def _doAction(cls, trigger: str):
        """ Execute action
        
        """
        #logger.debug("Thread %s: MotionDetector._doAction", get_ident())
        tc = CameraCfg().triggerConfig

        logEvent = False
        
        now = datetime.now()
        if cls.eventStart is None:
            cls.eventKey = now.strftime("%Y-%m-%dT%H:%M:%S")
            cls.eventStart = now
            logEvent = True
            
        delta = now - cls.eventStart
        deltaSec = delta.total_seconds()

        if deltaSec > tc.detectionPauseSec:
            #Difference to previous event is larger than pause -> new event
            #logger.debug("Thread %s: MotionDetector._doAction - Starting new event", get_ident())
            cls.eventKey = now.strftime("%Y-%m-%dT%H:%M:%S")
            cls.eventStart = now
            cls.nrPhotos = 0
            cls.lastPhoto = None
            cls._stopAction(force=True)
            cls.videoStart = None
            cls.videoStop = None
            if tc.actionVR == 1:
                cls.videoEncoder = None
            cls.videoName = None
            deltaSec = 0
            logEvent = True

        startVideo = False
        doPhoto = False
        
        if deltaSec >= tc.detectionDelaySec:
            if tc.actionVideo == True:
                if cls.videoStart is None:
                    startVideo = True
                    cls.videoStart = now
            
            if tc.actionPhoto == True:
                if cls.nrPhotos == 0:
                    doPhoto = True
                    cls.lastPhoto = now
                    cls.nrPhotos = 1
                else:
                    if cls.nrPhotos < tc.actionPhotoBurst:
                        deltaP = now - cls.lastPhoto
                        deltaPSec = deltaP.total_seconds()
                        if deltaPSec >= tc.actionPhotoBurstDelaySec:
                            doPhoto = True
                            cls.nrPhotos += 1
                            cls.lastPhoto = now
                        
        fnRaw = now.strftime("%Y-%m-%dT%H-%M-%S")
        logTS = now.strftime("%Y-%m-%dT%H:%M:%S")
        fnPhoto = fnRaw + ".jpg"
        fnVideo = fnRaw + ".mp4"
        
        if logEvent:
            with open(tc.logFilePath, "a") as f:
                f.write(logTS + " Event  detected       Trigger: " + trigger["trigger"] + " - '" + trigger["triggertype"] + "' " + trigger["triggerparam"] + "\n")
            key = cls.eventKey
            #logger.debug("Thread %s: MotionDetector._doAction - INSERT INTO events - timestamp: %s", get_ident(), key)
            cls.db.execute(
                "INSERT INTO events (timestamp, date, minute, time, type, trigger, triggertype, triggerparam) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (key, key[:10], key[11:16], key[11:19], "Motion", trigger["trigger"], trigger["triggertype"], trigger["triggerparam"])
            )
            cls.db.commit()
            #logger.debug("Thread %s: MotionDetector._doAction - DB committed", get_ident())
                    
        if startVideo:
            logger.debug("Thread %s: MotionDetector._doAction - Starting video", get_ident())
            if tc.actionVR == 1:
               (done, encoder, err) = Camera.quickVideoStart(tc.actionPath + "/" + fnVideo)
            else:
                (done, err) = Camera.recordCircular(cls.videoCircOutput, tc.actionPath + "/" + fnVideo)
                encoder = cls.videoEncoder
            if done:
                cls.videoEncoder = encoder
                cls.videoName = fnVideo
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Video: " + fnVideo + " started" + "\n")
                cls.videoKey = logTS
                #logger.debug("Thread %s: MotionDetector._doAction - INSERT INTO eventactions - Video", get_ident())
                cls.db.execute(
                    "INSERT INTO eventactions (event, timestamp, date, time, actiontype, actionduration, filename, fullpath) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (cls.eventKey, logTS, logTS[:10], logTS[11:19], "Video", tc.actionVideoDuration, fnVideo, tc.actionPath + "/" + fnVideo)
                )
                cls.db.commit()
                #logger.debug("Thread %s: MotionDetector._doAction - DB committed", get_ident())
            else:
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Video: " + fnVideo + " Start   Error: " + err + "\n")
        
        if doPhoto:
            (done, err) = Camera.quickPhoto(tc.actionPath + "/" + fnPhoto)
            if done:
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Photo: " + fnPhoto + "\n")
                #logger.debug("Thread %s: MotionDetector._doAction - INSERT INTO eventactions - Photo", get_ident())
                cls.db.execute(
                    "INSERT INTO eventactions (event, timestamp, date, time, actiontype, actionduration, filename, fullpath) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (cls.eventKey, logTS, logTS[:10], logTS[11:19], "Photo", 0, fnPhoto, tc.actionPath + "/" + fnPhoto)
                )
                cls.db.commit()
                #logger.debug("Thread %s: MotionDetector._doAction - DB committed", get_ident())
            else:
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Photo: " + fnPhoto + " Error:  " + err + "\n")
                    
    @classmethod
    def _cleanupEvent(cls):
        """ Cleanup event data
        """
        cls._stopAction(force=True)
        cls.eventKey = None
        cls.eventStart = None
        cls.lastPhoto = None
        cls.nrPhotos = 0
        if CameraCfg().triggerConfig.actionVR == 1:
           cls.videoEncoder = None
        cls.videoKey = None
        cls.videoName = None
        cls.videoStart = None
        cls.videoStop = None

    @classmethod
    def _stopAction(cls, force = False):
        """ Stop an active action, if required
        """
        if not cls.videoStart is None:
            if cls.videoStop is None:
                if not cls.videoName is None:
                    tc = CameraCfg().triggerConfig
                    now = datetime.now()
                    dur = now-cls.videoStart
                    durSec = dur.total_seconds()
                    if durSec > tc.actionVideoDuration or force:
                        logger.debug("Thread %s: MotionDetector._stopAction - stopping video", get_ident())
                        if tc.actionVR == 1:
                            (done, err) = Camera.quickVideoStop(cls.videoEncoder)
                        else:
                            (done, err) = Camera.stopRecordingCircular(cls.videoCircOutput)
                        logTS = now.strftime("%Y-%m-%d %H:%M:%S")
                        if done:
                            cls.videoEncoder = None
                            with open(tc.logFilePath, "a") as f:
                                f.write(logTS + " Video: " + cls.videoName + " stopped" + "\n")
                            #logger.debug("Thread %s: MotionDetector._doAction - UPDATE eventactions", get_ident())
                            cls.db.execute(
                                "UPDATE eventactions set actionduration = ? WHERE event = ? AND timestamp = ? AND actiontype = ?",
                                (round(durSec,0), cls.eventKey, cls.videoKey, "Video")
                            )
                            cls.db.commit()
                            #logger.debug("Thread %s: MotionDetector._doAction - DB committed", get_ident())
                        else:
                            with open(tc.logFilePath, "a") as f:
                                f.write(logTS + " Video: " + cls.videoName + " Stop     Error" + err + "\n")
                        cls.videoStop = now
                    
    @staticmethod
    def _isActive() -> bool:
        """ Check whether trigger is supposed to be active
        """
        active = True
        cfg = CameraCfg()
        tc = cfg.triggerConfig
        
        now = datetime.now()
        wd = str(now.isoweekday())
        if tc.operationWeekdays[wd] == True:
            h = now.hour
            m = now.minute
            dm = 60 * h + m
            if dm >= tc.operationStartMinute \
            and dm <= tc.operationEndMinute:
                active = True
            else:
                active = False
        else:
            active = False
        if active:
            cfg.serverConfig.isTriggerWaiting = False
        else:
            cfg.serverConfig.isTriggerWaiting = True
        return active
        
    @classmethod
    def _motionThread(cls):
        """ Motion detection thread
        """
        logger.debug("Thread %s: MotionDetector._motionThread", get_ident())
        cls.db = get_dbx()
        logger.debug("Thread %s: MotionDetector._motionThread - got database", get_ident())
        cam = Camera()
        cfg = CameraCfg()
        prv = None
        (w, h) = cfg.liveViewConfig.stream_size
        logger.debug("Thread %s: MotionDetector._motionThread w: %s h: %s", get_ident(), w, h)
        if cfg.triggerConfig.actionVR == 2:
            (done, circ, encoder, err) = cam.startCircular()
            if done:
                logger.debug("Thread %s: MotionDetector._motionThread - Encoder for circular output started", get_ident())
                cls.videoCircOutput = circ
                cls.videoEncoder = encoder
            else:
                logger.error("Circular output not started: %s", err)
                cfg.triggerConfig.actionVR = 1
        stop = False
        while not stop:
            if cls._isActive():
                if not cfg.serverConfig.isLiveStream:
                    cam.startLiveStream()
                try:
                    # Just to keep the live stream running
                    frame = cam.get_frame()
                    cur = cam.getLiveViewBuffer()
                    cur = cur[:w * h].reshape(h, w)
                    #logger.debug("Thread %s: MotionDetector._motionThread - got live view buffer", get_ident())
                    if prv is not None:
                        (motion, trigger) = cls._motionDetected(cur, prv)
                        if motion:
                            #logger.debug("Thread %s: MotionDetector._motionThread - motion detected", get_ident())
                            cls._doAction(trigger)
                        cls._stopAction()
                    prv = cur
                    if cls.mThreadStop:
                        #logger.debug("Thread %s: MotionDetector._motionThread - stop requested", get_ident())
                        cls._stopAction(force=True)
                        stop = True
                except Exception as e:
                    cls._cleanupEvent()
                    logger.error("Exception in _motionThread: %s", e)
                    stop = True
            else:
                cls._cleanupEvent()
                time.sleep(2)
                if cls.mThreadStop:
                    stop = True
        
        if cfg.triggerConfig.actionVR == 2:
            (done, err) = cam.stopCircular(cls.videoEncoder)
            if done:
                logger.debug("Thread %s: MotionDetector._motionThread - Encoder for circular output stopped", get_ident())
                cls.videoCircOutput = None
                cls.videoEncoder = None
            else:
                logger.error("Circular output not stopped: %s", err)
        cls.mThread = None
        
    @classmethod
    def startMotionDetection(cls):
        """ Start motion detection
        
        """
        logger.debug("Thread %s: MotionDetector.startMotionDetection", get_ident())
        if cls.mThread is None:
            if not CameraCfg().serverConfig.isLiveStream:
                Camera().startLiveStream()
            logger.debug("Thread %s: MotionDetector.startMotionDetection - starting new thread", get_ident())
            cls.mThread = threading.Thread(target=cls._motionThread, daemon=True)
            cls.mThread.start()
            logger.debug("Thread %s: MotionDetector.startMotionDetection - thread started", get_ident())
        
    @classmethod
    def stopMotionDetection(cls):
        """ Stop motion detection
        
        """
        logger.debug("Thread %s: MotionDetector.stopMotionDetection", get_ident())
        if cls.mThread is None:
            logger.debug("Thread %s: MotionDetector.stopMotionDetection - thread was not active", get_ident())
        else:
            logger.debug("Thread %s: MotionDetector.stopMotionDetection - stopping thread", get_ident())
            cls.mThreadStop = True
            cnt = 0
            while cls.mThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 500:
                    logger.error("Motion detection thread did not stop within 5 sec")
                    if cls.mThread.is_alive():
                        cnt = 0
                    else:
                        cls.mThread = None
                    #raise TimeoutError("Motion detection thread did not stop within 5 sec")
            cls.mThreadStop = False
            cls._cleanupEvent()
        logger.debug("Thread %s: MotionDetector.stopMotionDetection: Thread has stopped", get_ident())
        
        