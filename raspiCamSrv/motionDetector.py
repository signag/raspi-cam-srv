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
import smtplib
from email.message import EmailMessage
import mimetypes
import copy

logger = logging.getLogger(__name__)

class MotionEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        #logger.debug("Thread %s: CameraEvent.__init__", get_ident())
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        #logger.debug("Thread %s: CameraEvent.wait", get_ident())
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
            #logger.debug("Thread %s: CameraEvent.wait - Event ident: %s added to events dict. time:%s", get_ident(), ident, self.events[ident][1])
        #for ident, event in self.events.items():
            #logger.debug("Thread %s: CameraEvent.wait - Event ident: %s Flag: %s Time: %s (Flag False -> blocking)", get_ident(), ident, self.events[ident][0].is_set(), event[1])
            
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by MotionDetector when a new frame is available."""
        #logger.debug("Thread %s: CameraEvent.set", get_ident())
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
                #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s Flag: False -> True (unblock/notify)", get_ident(), ident)
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s Flag: True (Last image not processed).", get_ident(), ident)
                if now - event[1] > 5:
                    #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s  too old; marked for removal.", get_ident(), ident)
                    remove = ident
        if remove:
            del self.events[remove]
            #logger.debug("Thread %s: CameraEvent.set  - Event ident: %s removed.", get_ident(), ident)

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        ident = get_ident()
        if ident in self.events:
            self.events[get_ident()][0].clear()
        #logger.debug("Thread %s: CameraEvent.clear - Flag set to False -> blocking.", get_ident())

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
    notificationDone = None
    notifyMail = None
    notifyBuffer = []
    mdAlgo = None
    event = MotionEvent()

    def __new__(cls):
        logger.debug("Thread %s: MotionDetector.__new__", get_ident())
        if cls._instance is None:
            logger.debug("Thread %s: MotionDetector.__new__ - Instantiating Class", get_ident())
            cls._instance = super(MotionDetector, cls).__new__(cls)
            cfg = CameraCfg()
            tc = cfg.triggerConfig
            if tc.motionDetectAlgo in range(2, 5):
                if CameraCfg().serverConfig.supportsExtMotionDetection == True:
                    import raspiCamSrv.motionAlgoIB as mda
                    if tc.motionDetectAlgo == 2:
                        cls.mdAlgo = mda.MotionDetectFrameDiff()
                    elif tc.motionDetectAlgo == 3:
                        cls.mdAlgo = mda.MotionDetectOpticalFlow()
                    else:
                        cls.mdAlgo = mda.MotionDetectBgSubtract()
                else:
                    tc.error = f"Error while initializing MotionDetector: algorithm {tc.motionDetectAlgo} currently not supported."
                    tc.errorSource = "MotionDetector.__new__"
                    logger.error("Error while initializing MotionDetector: algorithm %s currently not supported", tc.motionDetectAlg)
                    
        return cls._instance
    
    @classmethod
    def setAlgorithm(cls) -> bool:
        """ Set the motion detection algorithm
        
            The currently active algorithm is taken from trigger configuration
            
            Return:
                True : requested algorithm has been set
                False: requested algorithm could not be set
        """
        ret = False
        cls.mdAlgo = None
        cfg = CameraCfg()
        tc = cfg.triggerConfig
        logger.debug("Thread %s: MotionDetector.setAlgorithm - set algorithm to %s", get_ident(), tc.motionDetectAlgo)
        if tc.motionDetectAlgo == 1:
            ret = True
        if tc.motionDetectAlgo in range(2, 5):
            if CameraCfg().serverConfig.supportsExtMotionDetection == True:
                import raspiCamSrv.motionAlgoIB as mda
                if tc.motionDetectAlgo == 2:
                    cls.mdAlgo = mda.MotionDetectFrameDiff()
                elif tc.motionDetectAlgo == 3:
                    cls.mdAlgo = mda.MotionDetectOpticalFlow()
                else:
                    cls.mdAlgo = mda.MotionDetectBgSubtract()
                    cls.mdAlgo.backSubModel = tc.backSubModel
                ret = True
        return ret

    def get_testFrame1(self):
        if not MotionDetector.mdAlgo is None:
            MotionDetector.event.wait()
            MotionDetector.event.clear()
            return MotionDetector.mdAlgo.testFrame1
        else:
            return None

    def get_testFrame2(self):
        if not MotionDetector.mdAlgo is None:
            MotionDetector.event.wait()
            MotionDetector.event.clear()
            return MotionDetector.mdAlgo.testFrame2
        else:
            return None

    def get_testFrame3(self):
        if not MotionDetector.mdAlgo is None:
            MotionDetector.event.wait()
            MotionDetector.event.clear()
            return MotionDetector.mdAlgo.testFrame3
        else:
            return None

    def get_testFrame4(self):
        if not MotionDetector.mdAlgo is None:
            MotionDetector.event.wait()
            MotionDetector.event.clear()
            return MotionDetector.mdAlgo.testFrame4
        else:
            return None
    
    @classmethod
    def _motionDetected(cls, fCur, fPrv) -> tuple:
        """ Analyze input frames to detect motion
        
        """
        tc = CameraCfg().triggerConfig
        #logger.debug("Thread %s: MotionDetector._motionDetected - algo: %s", get_ident(), tc.motionDetectAlgo)
        motion = False
        trigger = {}
        
        if tc.motionDetectAlgo == 1:
            (motion, trigger) = cls._motionAlgo_MeanSquare(fCur, fPrv)
        if tc.motionDetectAlgo > 1:
            (motion, trigger) = cls.mdAlgo.detectMotion(fCur, fPrv)
            cls.event.set()
        
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
        return (motion, {"trigger":"Motion Detection", "triggertype":"Mean Square Diff", "triggerparam":{"msd": str(round(msd, 3))}})
    
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
        recordVideo = False
        doPhoto = False
        doNotify = False
        
        if deltaSec >= tc.detectionDelaySec:
            if tc.actionVideo == True:
                if cls.videoStart is None:
                    startVideo = True
                    cls.videoStart = now
                else:
                    if cls.videoStop is None:
                        recordVideo = True
            
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

            if tc.actionNotify == True:
                if logEvent == True:
                    if cls.notificationDone is None:
                        doNotify = True
                    else:
                        notifyDelta = now - cls.notificationDone
                        notifyDeltaSec = notifyDelta.total_seconds()
                        if notifyDeltaSec >= tc.notifyPause:
                            doNotify = True
                        
        fnRaw = now.strftime("%Y-%m-%dT%H-%M-%S")
        logTS = now.strftime("%Y-%m-%dT%H:%M:%S")
        fnPhoto = fnRaw + ".jpg"
        fnVideo = fnRaw + ".mp4"
        
        if logEvent:
            with open(tc.logFilePath, "a") as f:
                f.write(logTS + " Event  detected       Trigger: " + trigger["trigger"] + " - '" + trigger["triggertype"] + "' " + str(trigger["triggerparam"]) + "\n")
            key = cls.eventKey
            #logger.debug("Thread %s: MotionDetector._doAction - INSERT INTO events - timestamp: %s", get_ident(), key)
            cls.db.execute(
                "INSERT INTO events (timestamp, date, minute, time, type, trigger, triggertype, triggerparam) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (key, key[:10], key[11:16], key[11:19], "Motion", trigger["trigger"], trigger["triggertype"], str(trigger["triggerparam"]))
            )
            cls.db.commit()
            #logger.debug("Thread %s: MotionDetector._doAction - DB committed", get_ident())
                    
        if startVideo:
            done = False
            logger.debug("Thread %s: MotionDetector._doAction - Starting video", get_ident())
            if tc.motionDetectAlgo == 1 \
            or tc.videoBboxes == False:
                if tc.actionVR == 1:
                    (done, encoder, err) = Camera.quickVideoStart(tc.actionPath + "/" + fnVideo)
                else:
                    (done, err) = Camera.recordCircular(cls.videoCircOutput, tc.actionPath + "/" + fnVideo)
                    encoder = cls.videoEncoder
            if tc.motionDetectAlgo > 1 \
            and tc.videoBboxes == True:
                (done, fnVideo, err) = cls.mdAlgo.startRecordMotion(fnRaw)
                encoder = None
            if done == True:
                if encoder:
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
        
        photoDone = False
        if doPhoto:
            (done, err) = Camera.quickPhoto(tc.actionPath + "/" + fnPhoto)
            photoDone = done
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
                if not cls.notifyMail is None:
                    if tc.notifyIncludePhoto == True:
                        cls._attachToNotification(cls.notifyMail, fnPhoto)
                        if cls.nrPhotos >= tc.actionPhotoBurst:
                            if tc.notifyIncludeVideo == True:
                                if not cls.videoStop is None:
                                    cls._sendNotification()
                            else:
                                cls._sendNotification()
            else:
                with open(tc.logFilePath, "a") as f:
                    f.write(logTS + " Photo: " + fnPhoto + " Error:  " + err + "\n")
                    
        if doNotify:
            cls.notificationDone = now
            cls.notifyMail = cls._initNotificationMessage(logTS, trigger)
            if tc.notifyIncludePhoto:
                if photoDone:
                    cls._attachToNotification(cls.notifyMail, fnPhoto)
            if tc.notifyIncludeVideo == False \
            and (tc.notifyIncludePhoto == False \
            or  (tc.notifyIncludePhoto == True \
            and tc.actionPhotoBurst <= 1)):
                cls._sendNotification()
    
    @staticmethod            
    def _initNotificationMessage(logTS, trigger) -> EmailMessage:
        """ Set up an eMail Message for notification
        """
        logger.debug("Thread %s: MotionDetector._initNotificationMessage", get_ident())
        msg = EmailMessage()
        tc = CameraCfg().triggerConfig
        msg["From"] = tc.notifyFrom
        msg["To"] = tc.notifyTo
        msg["Subject"] = tc.notifySubject
        msg.set_content(
            "Notification on an event\n\n" \
            "Time   : " + logTS + "\n" \
            "Trigger: " + trigger["trigger"] + "\n" \
            "Type   : " + trigger["triggertype"] + "\n" \
            "MSD    : " + str(trigger["triggerparam"])
        )
        logger.debug("Thread %s: MotionDetector._initNotificationMessage - done", get_ident())
        return msg
    
    @staticmethod            
    def _attachToNotification(msg, fn):
        """ Attach a photo to a notification mail
        """
        logger.debug("Thread %s: MotionDetector._attachToNotification - fn: %s", get_ident(), fn)
        tc = CameraCfg().triggerConfig
        img = tc.actionPath + "/" + fn
        ctype, encoding = mimetypes.guess_type(img)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        with open(img, 'rb') as fp:
            msg.add_attachment(fp.read(),
                                maintype=maintype,
                                subtype=subtype,
                                filename=fn)
        logger.debug("Thread %s: MotionDetector._attachToNotification - done", get_ident())
                    
    @classmethod
    def _sendNotificationThread(cls):
        """ Send notification mail in own thread
        """
        logger.debug("Thread %s: MotionDetector._sendNotificationThread", get_ident())
        tc = CameraCfg().triggerConfig
        scr =CameraCfg().secrets
        msg = cls.notifyBuffer.pop(0)
        try:
            if tc.notifyUseSSL == True:
                server = smtplib.SMTP_SSL(host=tc.notifyHost, port=tc.notifyPort)
            else:
                server = smtplib.SMTP(host=tc.notifyHost, port=tc.notifyPort)
            server.connect(tc.notifyHost)
            
            if tc.notifyAuthenticate == True:
                logger.debug("Thread %s: MotionDetector._sendNotificationThread - Authentication with user/pwd", get_ident())
                server.login(scr.notifyUser, scr.notifyPwd)
            else:
                logger.debug("Thread %s: MotionDetector._sendNotificationThread - Authentication skipped", get_ident())
            server.ehlo()
            server.send_message(msg)
            server.quit()
        except Exception as e:
            tc.error = "Error sending notification mail: " + str(e)
            tc.errorSource = "MotionDetector._sendNotificationThread"
            logger.error("Error sending notification mail: %s", e)
        logger.debug("Thread %s: MotionDetector._sendNotificationThread - done", get_ident())

    @classmethod
    def _sendNotification(cls):
        """ Send notification mail
        """
        logger.debug("Thread %s: MotionDetector._sendNotification", get_ident())
        msg = copy.copy(cls.notifyMail)
        cls.notifyBuffer.append(msg)
        thread = threading.Thread(target=cls._sendNotificationThread)
        thread.start()
        cls.notifyMail = None
        logger.debug("Thread %s: MotionDetector._sendNotification - done", get_ident())
                    
    @classmethod
    def _cleanupEvent(cls):
        """ Cleanup event data
        """
        logger.debug("Thread %s: MotionDetector._cleanupEvent", get_ident())
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
        if not cls.notifyMail is None:
            cls._sendNotification()

    @classmethod
    def _stopAction(cls, force = False):
        """ Stop an active action, if required
        """
        #logger.debug("Thread %s: MotionDetector._stopAction", get_ident())
        if not cls.videoStart is None:
            if cls.videoStop is None:
                if not cls.videoName is None:
                    tc = CameraCfg().triggerConfig
                    now = datetime.now()
                    dur = now-cls.videoStart
                    durSec = dur.total_seconds()
                    if durSec > tc.actionVideoDuration or force:
                        logger.debug("Thread %s: MotionDetector._stopAction - stopping video", get_ident())
                        done = False
                        if tc._motionDetectAlgo == 1 \
                        or tc.videoBboxes == False:
                            if tc.actionVR == 1:
                                (done, err) = Camera.quickVideoStop(cls.videoEncoder)
                            else:
                                (done, err) = Camera.stopRecordingCircular(cls.videoCircOutput)
                        if tc._motionDetectAlgo > 1 \
                        and tc.videoBboxes == True:
                            cls.mdAlgo.stopRecordMotion()
                            done = True
                        logTS = now.strftime("%Y-%m-%d %H:%M:%S")
                        if done:
                            cls.videoEncoder = None
                            with open(tc.logFilePath, "a") as f:
                                f.write(logTS + " Video: " + cls.videoName + " stopped" + "\n")
                            logger.debug("Thread %s: MotionDetector._stopAction - UPDATE eventactions", get_ident())
                            cls.db.execute(
                                "UPDATE eventactions set actionduration = ? WHERE event = ? AND timestamp = ? AND actiontype = ?",
                                (round(durSec,0), cls.eventKey, cls.videoKey, "Video")
                            )
                            cls.db.commit()
                            logger.debug("Thread %s: MotionDetector._stopAction - DB committed", get_ident())
                            if not cls.notifyMail is None:
                                if tc.notifyIncludeVideo == True:
                                    cls._attachToNotification(cls.notifyMail, cls.videoName)
                                cls._sendNotification()
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
        tc = cfg.triggerConfig
        startTime = datetime.now()
        count = 0
        tc.motionTestFramerate = 0
        prv = None
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
                    cur = cam.getLiveViewImageForMotionDetection()
                    #logger.debug("Thread %s: MotionDetector._motionThread - got live view buffer", get_ident())
                    if prv is not None:
                        (motion, trigger) = cls._motionDetected(cur, prv)
                        if not cls.mdAlgo is None:
                            if cls.mdAlgo.test == True:
                                count += 1
                                timeDelta = datetime.now() - startTime
                                timeDeltaSec = timeDelta.total_seconds()
                                if timeDeltaSec > 0.5:
                                    tc.motionTestFramerate = count / timeDeltaSec
                        else:
                            count += 1
                            timeDelta = datetime.now() - startTime
                            timeDeltaSec = timeDelta.total_seconds()
                            if timeDeltaSec > 0.5:
                                tc.motionTestFramerate = count / timeDeltaSec
                            if timeDeltaSec > 3600:
                                count = 0
                                startTime = datetime.now()
                        if motion:
                            #logger.debug("Thread %s: MotionDetector._motionThread - motion detected", get_ident())
                            cls._doAction(trigger)
                        cls._stopAction()
                        #logger.debug("Thread %s: MotionDetector._motionThread - stopAction done", get_ident())
                        if tc.motionDetectAlgo > 1 \
                        and tc.videoBboxes == True:
                            if not cls.videoStart is None \
                            and cls.videoStop is None:
                                cls.mdAlgo.recordMotion()
                    prv = cur
                    if cls.mThreadStop:
                        logger.debug("Thread %s: MotionDetector._motionThread - stop requested", get_ident())
                        cls._stopAction(force=True)
                        stop = True
                except Exception as e:
                    cls._cleanupEvent()
                    logger.error("Exception in _motionThread: %s", e)
                    cfg.triggerConfig.error = "Error in motion detection: " + str(e)
                    cfg.triggerConfig.errorSource = "motionDetector._motionThread"
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
        sc = CameraCfg().serverConfig
        tc = CameraCfg().triggerConfig
        if cls.mThread is None:
            sc.error = None
            tc.error = None
            if tc.motionDetectAlgo == 2:
                cls.mdAlgo.bbox_threshold = tc.bboxThreshold
                cls.mdAlgo.nms_threshold = tc.nmsThreshold
                cls.mdAlgo.frameSize = CameraCfg().liveViewConfig.stream_size
                cls.mdAlgo.framerate = 15
            if tc.motionDetectAlgo == 3:
                cls.mdAlgo.motion_threshold = tc.motionThreshold
                cls.mdAlgo.nms_threshold = tc.nmsThreshold
                cls.mdAlgo.backSubMod = tc.backSubModel
                cls.mdAlgo.frameSize = CameraCfg().liveViewConfig.stream_size
                cls.mdAlgo.framerate = 5
            if tc.motionDetectAlgo == 4:
                cls.mdAlgo.bbox_threshold = tc.bboxThreshold
                cls.mdAlgo.nms_threshold = tc.nmsThreshold
                cls.mdAlgo.backSubMod = tc.backSubModel
                cls.mdAlgo.frameSize = CameraCfg().liveViewConfig.stream_size
                cls.mdAlgo.framerate = 15
            if sc.isTriggerTesting == True:
                logger.debug("Thread %s: MotionDetector.startMotionDetection - Activating test mode", get_ident())
                cls.mdAlgo.test = True
                tc._motionTestFrame1Title = cls.mdAlgo.testFrame1Title
                tc._motionTestFrame2Title = cls.mdAlgo.testFrame2Title
                tc._motionTestFrame3Title = cls.mdAlgo.testFrame3Title
                tc._motionTestFrame4Title = cls.mdAlgo.testFrame4Title
                tc.motionRefTit = cls.mdAlgo.algoReferenceTit
                tc.motionRefURL = cls.mdAlgo.algoReferenceURL
            else:
                logger.debug("Thread %s: MotionDetector.startMotionDetection - Activating normal mode", get_ident())
                if not cls.mdAlgo is None:
                    cls.mdAlgo.test = False
            if not CameraCfg().serverConfig.isLiveStream:
                Camera().startLiveStream()
            if not sc.error:
                logger.debug("Thread %s: MotionDetector.startMotionDetection - starting new thread", get_ident())
                cls.mThread = threading.Thread(target=cls._motionThread, daemon=True)
                cls.mThread.start()
                logger.debug("Thread %s: MotionDetector.startMotionDetection - thread started", get_ident())
            else:
                logger.debug("Thread %s: MotionDetector.startMotionDetection - not started", get_ident())
        
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
        
        