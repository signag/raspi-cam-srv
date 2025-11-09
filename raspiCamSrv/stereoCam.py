from raspiCamSrv.camera_pi import Camera
from raspiCamSrv.camCfg import CameraCfg
from raspiCamSrv.camCfg import StereoConfig
from _thread import get_ident
import time
import threading
import logging
import cv2
import numpy as np
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class StereoEvent(object):
    """An Event-like class that signals all active clients when a new stereo frame is
    available.
    """
    def __init__(self):
        #logger.debug("Thread %s: StereoEvent.__init__", get_ident())
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        #logger.debug("Thread %s: StereoEvent.wait", get_ident())
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
            #logger.debug("Thread %s: StereoEvent.wait - Event ident: %s added to events dict. time:%s", get_ident(), ident, self.events[ident][1])
        #for ident, event in self.events.items():
            #logger.debug("Thread %s: StereoEvent.wait - Event ident: %s Flag: %s Time: %s (Flag False -> blocking)", get_ident(), ident, self.events[ident][0].is_set(), event[1])
            
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by StereoCam when a new frame is available."""
        #logger.debug("Thread %s: StereoEvent.set", get_ident())
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
                #logger.debug("Thread %s: StereoEvent.set  - Event ident: %s Flag: False -> True (unblock/notify)", get_ident(), ident)
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                #logger.debug("Thread %s: StereoEvent.set  - Event ident: %s Flag: True (Last image not processed).", get_ident(), ident)
                if now - event[1] > 5:
                    #logger.debug("Thread %s: StereoEvent.set  - Event ident: %s  too old; marked for removal.", get_ident(), ident)
                    remove = ident
        if remove:
            del self.events[remove]
            #logger.debug("Thread %s: StereoEvent.set  - Event ident: %s removed.", get_ident(), ident)

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        ident = get_ident()
        if ident in self.events:
            self.events[get_ident()][0].clear()
        #logger.debug("Thread %s: StereoEvent.clear - Flag set to False -> blocking.", get_ident())

class StereoCam():
    """ Class for stereo camera handling.

    """
    logger.debug("Thread %s: StereoCam - setting class variables", get_ident())
    _instance = None

    def __new__(cls):
        logger.debug("Thread %s: StereoCam.__new__", get_ident())
        if cls._instance is None:
            logger.debug("Thread %s: StereoCam.__new__ - Instantiating Class", get_ident())
            cls._instance = super(StereoCam, cls).__new__(cls)
            cls.sThread = None
            cls.sThreadStop = False
            cls.pThread = None
            cls.pThreadStop = False
            cls.stereoFrameA = None
            cls.stereoFrame = None
            cls.event = StereoEvent()
            cls.camL = None
            cls.camR = None
            cls.leftStereoMap_x = None
            cls.leftStereoMap_y = None
            cls.rightStereoMap_x = None
            cls.rightStereoMap_y = None
            cls.last_access = 0                 # time of last client access to a stereo frame
            # Variables for video generation
            cls.recordFilename = None
            cls.recordIdx = None
            cls.frameSize = None
            cls.framerate = 20
            cls.recordingStart = None
            cls.recordingActive = False
            cls.video = None

        return cls._instance

    def get_stereoFrame(self):
        # logger.debug("Thread %s: StereoCam.get_stereoFrame", get_ident())
        self.last_access = time.time()
        self.event.wait()
        # logger.debug("Thread %s: StereoCam.get_stereoFrame - waiting done", get_ident())
        self.event.clear()
        return self.stereoFrame

    def _frameToStream(self, frame):
        """ Convert frame to bytestream"""
        # logger.debug("Thread %s: StereoCam._frameToStream", get_ident())
        frameb = None
        (stat, frame_jpg) = cv2.imencode(".jpg", frame)
        if stat == True:
            frame_jpg_arr = np.array(frame_jpg)
            frameb = frame_jpg_arr.tobytes()
        return frameb

    def _stereoBM(self, stc:StereoConfig, left, right):
        """StereoBM algorithm for stereo image processing
        """
        # Create a Stereo Block Matching (SBM) object
        sbm = cv2.StereoBM_create(
            numDisparities=stc.bm_numDisparitiesFactor * 16,
            blockSize=stc.bm_blockSize)

        # Compute the Disparity Map
        disparity = sbm.compute(left, right)

        # Normalize the Disparity Map for visualization
        disp_norm = cv2.normalize(
            disparity, 
            None, 
            alpha=0, 
            beta= 255, 
            norm_type=cv2.NORM_MINMAX, 
            dtype=cv2.CV_8U
        )
        return disp_norm

    def _stereoSGBM(self, stc: StereoConfig, left, right):
        """StereoSGBM algorithm for stereo image processing"""
        # Create a Stereo Block Matching (SBM) object
        sgbm = cv2.StereoSGBM_create(
            minDisparity=stc.sgbm_minDisparity,
            numDisparities=stc.sgbm_numDisparitiesFactor * 16,
            blockSize=stc.sgbm_blockSize,
            P1=stc.sgbm_P1,
            P2=stc.sgbm_P2,
            disp12MaxDiff=stc.sgbm_disp12MaxDiff,
            preFilterCap=stc.sgbm_preFilterCap,
            uniquenessRatio=stc.sgbm_uniquenessRatio,
            speckleWindowSize=stc.sgbm_speckleWindowSize,
            speckleRange=stc.sgbm_speckleRange,
            mode=stc.sgbm_mode,
        )

        # Compute the Disparity Map
        disparity = sgbm.compute(left, right)

        # Normalize the Disparity Map for visualization
        disp_norm = cv2.normalize(
            disparity,
            None,
            alpha=0,
            beta=255,
            norm_type=cv2.NORM_MINMAX,
            dtype=cv2.CV_8U,
        )
        return disp_norm

    def _3DVideo(self, stc: StereoConfig, left, right):
        """create 3D video from stereo images"""

        if stc.applyCalibRectify == True:
            left = cv2.remap(
                left,
                self.leftStereoMap_x,
                self.leftStereoMap_y,
                cv2.INTER_LANCZOS4,
                cv2.BORDER_CONSTANT,
                0,
            )
            right = cv2.remap(
                right,
                self.rightStereoMap_x,
                self.rightStereoMap_y,
                cv2.INTER_LANCZOS4,
                cv2.BORDER_CONSTANT,
                0,
            )

        v3d = right.copy()
        v3d[:, :, 0] = right[:, :, 0]
        v3d[:, :, 1] = right[:, :, 1]
        v3d[:, :, 2] = left[:, :, 2]

        # output = Left_nice+Right_nice
        # v3d = cv2.resize(v3d, (700, 700))

        return v3d

    def _processStereoImage(self, left, right):
        """ Process stereo image
        """
        # logger.debug("Thread %s: StereoCam._processStereoImage", get_ident())

        cfg = CameraCfg()
        stc = cfg.stereoCfg

        if stc.intent == "DepthMap":
            # Convert to grayscale
            left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
            # logger.debug("Thread %s: StereoCam._processStereoImage - left image converted to grayscale", get_ident())
            right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
            # logger.debug("Thread %s: StereoCam._processStereoImage - right image converted to grayscale", get_ident())

            if stc.applyCalibRectify == True:
                # logger.debug("Thread %s: StereoCam._processStereoImage - shape(leftStereoMap_x): %s shape(leftStereoMap_y): %s", get_ident(), self.leftStereoMap_x.shape, self.leftStereoMap_y.shape)
                left_rect = cv2.remap(
                    left_gray,
                    self.leftStereoMap_x,
                    self.leftStereoMap_y,
                    cv2.INTER_LANCZOS4,
                    cv2.BORDER_CONSTANT,
                    0,
                )
                # logger.debug("Thread %s: StereoCam._processStereoImage - done", get_ident())
                # logger.debug("Thread %s: StereoCam._processStereoImage - shape(rightStereoMap_x): %s shape(rightStereoMap_y): %s", get_ident(), self.rightStereoMap_x.shape, self.rightStereoMap_y.shape)
                right_rect = cv2.remap(
                    right_gray,
                    self.rightStereoMap_x,
                    self.rightStereoMap_y,
                    cv2.INTER_LANCZOS4,
                    cv2.BORDER_CONSTANT,
                    0,
                )
                # logger.debug("Thread %s: StereoCam._processStereoImage - done", get_ident())
            else:
                left_rect = left_gray
                right_rect = right_gray

            if stc.intentAlgo == "StereoBM":
                # Use StereoBM for depth map
                disp = self._stereoBM(stc, left_rect, right_rect)

            if stc.intentAlgo == "StereoSGBM":
                # Use StereoSGBM for depth map
                disp = self._stereoSGBM(stc, left_rect, right_rect)
        elif stc.intent == "3DVideo":
            # Create 3D video from stereo images
            disp = self._3DVideo(stc, left, right)
        else:
            logger.error("Thread %s: StereoCam._processStereoImage - Unknown stereo intent: %s", get_ident(), stc.intent)
            return

        # Convert to stream
        self.stereoFrameA = disp
        self.stereoFrame = self._frameToStream(disp)

        # Signal that a new stereo frame is available
        self.event.set()

    def _stereoThread(self):
        """ Stereo camera thread
        """
        logger.debug("Thread %s: StereoCam._stereoThread", get_ident())
        cam = Camera()
        cfg = CameraCfg()
        sc = cfg.serverConfig
        left = None
        right = None
        stop = False
        while not stop:
            if not cfg.serverConfig.isLiveStream:
                cam.startLiveStream()
            if not cfg.serverConfig.isLiveStream2:
                cam.startLiveStream2()
            try:
                # Just to keep the live stream running
                frame, frameRaw = cam.get_frame()
                left = cam.getLeftImageForStereo()
                # logger.debug("Thread %s: StereoCam._stereoThread - got left live view buffer", get_ident())
                frame2, frame2Raw = cam.get_frame2()
                right = cam.getRightImageForStereo()
                # logger.debug("Thread %s: StereoCam._stereoThread - got right live view buffer", get_ident())

                self._processStereoImage(left, right)

                if self.recordingActive == True:
                    self._recordStereo()

                if self.sThreadStop:
                    logger.debug("Thread %s: StereoCam._stereoThread - stop requested", get_ident())
                    stop = True

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - self.last_access > 10:
                    stop = True
                    logger.debug("Thread %s: StereoCam._stereoThread - Stopping camera thread due to inactivity.", get_ident())
                    break

            except Exception as e:
                logger.error("Exception in _stereoThread: %s", e)
                stop = True
        self.sThread = None
        sc.isStereoCamActive = False

    def startStereoCam(self):
        """ Start stereo camera processing
        
        """
        logger.debug("Thread %s: StereoCam.startStereoCam", get_ident())
        cfg = CameraCfg()
        sc = cfg.serverConfig
        stc = cfg.stereoCfg

        # Load calibration params
        if stc.applyCalibRectify == True:
            dataPath = sc.photoRoot + "/" + stc.calibDataSubPath
            dataFile = dataPath + stc.calibDataFile
            logger.debug("Thread %s: StereoCam.startStereoCam - Reading calibData from %s", get_ident(), dataFile)
            calibData = cv2.FileStorage(dataFile,cv2.FILE_STORAGE_READ,)
            logger.debug("Thread %s: StereoCam.startStereoCam - calibData read from %s", get_ident(), dataFile)

            self.leftStereoMap_x = calibData.getNode("Left_Stereo_Map_x").mat()
            self.leftStereoMap_y = calibData.getNode("Left_Stereo_Map_y").mat()
            self.rightStereoMap_x = calibData.getNode("Right_Stereo_Map_x").mat()
            self.rightStereoMap_y = calibData.getNode("Right_Stereo_Map_y").mat()
            calibData.release()
            logger.debug("Thread %s: StereoCam.startStereoCam - Stereo_Maps extracted", get_ident())

        sc = CameraCfg().serverConfig
        self.last_access = time.time()
        if self.sThread is None:
            sc.error = None
            if not CameraCfg().serverConfig.isLiveStream:
                Camera().startLiveStream()
            if not CameraCfg().serverConfig.isLiveStream2:
                Camera().startLiveStream2()
            if not sc.error:
                logger.debug("Thread %s: StereoCam.startStereoCam - starting new thread", get_ident())
                self.sThread = threading.Thread(target=self._stereoThread, daemon=True)
                self.sThread.start()
                logger.debug("Thread %s: StereoCam.startStereoCam - thread started", get_ident())
            else:
                logger.debug("Thread %s: StereoCam.startStereoCam - not started", get_ident())

    def stopStereoCam(self):
        """ Stop stereo camera processing
        
        """
        logger.debug("Thread %s: StereoCam.stopStereoCam", get_ident())
        if self.sThread is None:
            logger.debug("Thread %s: StereoCam.stopStereoCam - thread was not active", get_ident())
        else:
            logger.debug("Thread %s: StereoCam.stopStereoCam - stopping thread", get_ident())
            self.sThreadStop = True
            cnt = 0
            while self.sThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 500:
                    logger.error("Stereo thread did not stop within 5 sec")
                    if self.sThread.is_alive():
                        cnt = 0
                    else:
                        self.sThread = None
                    # raise TimeoutError("Stereo thread did not stop within 5 sec")
            self.sThreadStop = False
            self.leftStereoMap_x = None
            self.leftStereoMap_y = None
            self.rightStereoMap_x = None
            self.rightStereoMap_y = None
        logger.debug(
            "Thread %s: StereoCam.stopStereoCam: Thread has stopped", get_ident()
        )

    def _takeCalibPhotoThread(self):
        """ Taking photos for camera calibration
        """
        logger.debug("Thread %s: StereoCam._takeCalibPhotoThread camL: %s, camR: %s", get_ident(), self.camL, self.camR)
        cam = Camera()
        cfg = CameraCfg()
        stc = cfg.stereoCfg
        sc = cfg.serverConfig
        left = None
        right = None
        stop = False
        found = 0
        while not stop:
            if not cfg.serverConfig.isLiveStream:
                cam.startLiveStream()
            if not cfg.serverConfig.isLiveStream2:
                cam.startLiveStream2()
            try:
                # Get the left and right images
                # Call get_frame, Just to keep the live stream running
                frame, frameRaw = cam.get_frame()
                imgL = cam.getLeftImageForStereo()
                # logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - got left image", get_ident())

                if self.camR is not None:
                    frame2, frame2Raw = cam.get_frame2()
                    imgR = cam.getRightImageForStereo()
                    # logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - got right image", get_ident())

                # Convert images to grayscale
                grayL = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)
                if self.camR is not None:
                    grayR = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)
                # logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - converted to grayscale", get_ident())

                # Find the chess board corners
                if stc.calibPatternIdx == 0:  # Chessboard pattern
                    # logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - looking for chessboard corners", get_ident())
                    retL, cornersL = cv2.findChessboardCorners(grayL, stc.calibPatternSize, None)
                    # logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - done chessboard corners - retL=%s", get_ident(), retL)
                    retR = True
                    if self.camR is not None:
                        retR, cornersR = cv2.findChessboardCorners(grayR, stc.calibPatternSize, None)
                        # logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - done chessboard corners - retR=%s", get_ident(), retR)
                else:
                    logger.error("Thread %s: StereoCam._takeCalibPhotoThread - unknown calibration pattern", get_ident())
                    raise ValueError("Unknown calibration pattern")

                # If corners are detected, refine them and save the images
                if (retL == True) and (retR == True):
                    found += 1
                    count = stc.getNextPhotoIdx() + 1
                    fn = "img%03d.png" % count
                    fnC = "img%03d_corners.png" % count
                    fpL = stc.calibPhotosPath + self.camL + "/" + fn
                    fpLC = stc.calibPhotosPath + self.camL + "/" + fnC
                    fsL = stc.calibPhotosSubPath + self.camL + "/" + fn
                    fsLC = stc.calibPhotosSubPath + self.camL + "/" + fnC
                    logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Saving image to %s", get_ident(), fpL)
                    cv2.imwrite(fpL, imgL)
                    logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Image saved: %s", get_ident(), fsL)

                    # Refine the corner positions
                    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                    cv2.cornerSubPix(grayL, cornersL, (11, 11), (-1, -1), criteria)
                    # Create overlay images
                    cv2.drawChessboardCorners(imgL, stc.calibPatternSize, cornersL, retL)
                    cv2.imwrite(fpLC, imgL)
                    logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Image with corners saved: %s", get_ident(), fsLC)

                    if self.camL in stc.calibPhotos:
                        stc.calibPhotos[self.camL].insert(count-1, fsL)
                        stc.calibPhotosCrn[self.camL].insert(count - 1, fsLC)
                    else:
                        stc.calibPhotos[self.camL] = [fsL]
                        stc.calibPhotosCrn[self.camL] = [fsLC]
                    stc.calibPhotosIdx[self.camL] = count - 1
                    stc.calibPhotosCount[self.camL] = len(stc.calibPhotos[self.camL])

                    if self.camR is not None:
                        fpR = stc.calibPhotosPath + self.camR + "/" + fn
                        fsR = stc.calibPhotosSubPath + self.camR + "/" + fn
                        fpRC = stc.calibPhotosPath + self.camR + "/" + fnC
                        fsRC = stc.calibPhotosSubPath + self.camR + "/" + fnC
                        logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Saving image to %s", get_ident(), fpR)
                        cv2.imwrite(fpR, imgR)
                        logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Image saved: %s", get_ident(), fsR)

                        # Refine the corner positions
                        cv2.cornerSubPix(grayR, cornersR, (11, 11), (-1, -1), criteria)
                        # Create overlay images
                        cv2.drawChessboardCorners(imgR, stc.calibPatternSize, cornersR, retR)
                        cv2.imwrite(fpRC, imgR)
                        logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Image with corners saved: %s", get_ident(), fsRC)

                        if self.camR in stc.calibPhotos:
                            stc.calibPhotos[self.camR].insert(count - 1, fsR)
                            stc.calibPhotosCrn[self.camR].insert(count - 1, fsRC)
                        else:
                            stc.calibPhotos[self.camR] = [fsR]
                            stc.calibPhotosCrn[self.camR] = [fsRC]
                        stc.calibPhotosIdx[self.camR] = count - 1
                        stc.calibPhotosCount[self.camR] = len(stc.calibPhotos[self.camR])

                    sc.unsavedChanges = True
                    sc.addChangeLogEntry(f"Calibration photo(s) added")
                    stc.calibPhotoRecordingMsg = f"{len(stc.calibPhotos[self.camL])} of {stc.calibPhotosTarget} Calibration photo(s) taken: {fn}"

                    time.sleep(2)
                else:
                    if found > 0:
                        if self.camR is None:
                            stc.calibPhotoRecordingMsg = "No or not all chessboard corners found."
                        else:
                            stc.calibPhotoRecordingMsg = "No or not all chessboard corners found on both cameras."

                if stc.calibPhotosCount[self.camL] >= stc.calibPhotosTarget:
                    stc.calibPhotosOK[self.camL] = True
                    logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Target number of calibration photos reached for camera %s", get_ident(), self.camL)
                    if self.camR is not None:
                        if stc.calibPhotosCount[self.camR] >= stc.calibPhotosTarget:
                            stc.calibPhotosOK[self.camR] = True
                            logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Target number of calibration photos reached for camera %s", get_ident(), self.camR)
                    if stc.isCalibPhotosOK(self.camL, self.camR):
                        logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - Target number of calibration photos reached for both cameras", get_ident())
                        stop = True
                        stc.calibPhotoRecordingMsg = "Target number of calibration photos reached."
                        time.sleep(2)

                if self.pThreadStop:
                    logger.debug("Thread %s: StereoCam._takeCalibPhotoThread - stop requested", get_ident())
                    stop = True
                    stc.calibPhotoRecordingMsg = ""
            except Exception as e:
                logger.error("Exception in _takeCalibPhotoThread: %s", e)
                stc.calibPhotoRecordingMsg = f"Error while taking photos for calibration: {e}."
                stop = True
        self.pThread = None
        stc.calibPhotoRecording = False
        stc.calibPhotoRecordingMsg = ""

    def takeCalibrationPhotos(self, camL: str, camR: str):
        """ Take calibration photos for camera calibration
        """
        logger.debug("Thread %s: StereoCam.takeCalibrationPhotos - camL=%s, camR=%s", get_ident(), camL, camR)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        stc = cfg.stereoCfg
        if stc.isCalibPhotosOK(camL, camR) == False:
            logger.debug("Thread %s: StereoCam.takeCalibrationPhotos - isCalibPhotosOK= %s", get_ident(), stc.isCalibPhotosOK(camL, camR))
            if self.pThread is None:
                self.camL = camL
                self.camR = camR
                sc.error = None
                if not stc.calibPhotoRecording:
                    Camera().startLiveStream()
                if not CameraCfg().serverConfig.isLiveStream2:
                    Camera().startLiveStream2()
                if not sc.error:
                    logger.debug("Thread %s: StereoCam.takeCalibrationPhotos - starting new thread", get_ident())
                    self.pThread = threading.Thread(target=self._takeCalibPhotoThread, daemon=True)
                    self.pThread.start()
                    stc.calibPhotoRecording = True
                    logger.debug("Thread %s: StereoCam.takeCalibrationPhotos - thread started", get_ident())
                else:
                    logger.debug("Thread %s: StereoCam.takeCalibrationPhotos - not started", get_ident())
        else:
            logger.debug("Thread %s: StereoCam.takeCalibrationPhotos - isCalibPhotosOK= %s", get_ident(), stc.isCalibPhotosOK(camL, camR))

    def stoptakeCalibrationPhotos(self):
        """ Stop taking calibration photos
        
        """
        logger.debug("Thread %s: StereoCam.stoptakeCalibrationPhotos", get_ident())

        cfg = CameraCfg()
        stc = cfg.stereoCfg
        if self.pThread is None:
            logger.debug("Thread %s: StereoCam.stoptakeCalibrationPhotos - thread was not active", get_ident())
        else:
            logger.debug("Thread %s: StereoCam.stoptakeCalibrationPhotos - stopping thread", get_ident())
            self.pThreadStop = True
            cnt = 0
            while self.pThread:
                time.sleep(0.01)
                cnt += 1
                if cnt > 500:
                    logger.error("takeCalibPhotoThread did not stop within 5 sec")
                    if self.pThread.is_alive():
                        cnt = 0
                    else:
                        self.pThread = None
                    # raise TimeoutError("Stereo thread did not stop within 5 sec")
            self.pThreadStop = False
        stc.calibPhotoRecording = False
        logger.debug("Thread %s: StereoCam.stoptakeCalibrationPhotos: Thread has stopped", get_ident())

    def calibrateCameras(self, camL: str, camR: str):
        """ Calibrate the stereo cameras

            Source: https://learnopencv.com/camera-calibration-using-opencv/
        """
        logger.debug("Thread %s: StereoCam.calibrateCameras - camL=%s, camR=%s", get_ident(), camL, camR)
        cfg = CameraCfg()
        sc = cfg.serverConfig
        stc = cfg.stereoCfg

        # Termination criteria for refining the detected corners
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        logger.debug("Thread %s: StereoCam.calibrateCameras - Termination criteria set: %s", get_ident(), criteria)

        # Prepare 3D object points, like (0,0,0), (1,0,0), (2,0,0) ....,(9,6,0)
        objp = np.zeros((stc.calibPatternSize[0] * stc.calibPatternSize[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:stc.calibPatternSize[0], 0:stc.calibPatternSize[1]].T.reshape(-1, 2)
        # logger.debug("Thread %s: StereoCam.calibrateCameras - 3D Object points prepared: %s", get_ident(), objp)

        # Initialize lists for 2D image points and 3D object points
        img_ptsL = []
        img_ptsR = []
        obj_pts = []

        # Process all prepared calibration images
        for i in range(0, len(stc.calibPhotos[camL])):
            # Read images
            logger.debug("Thread %s: StereoCam.calibrateCameras - Loading image %s/%s", get_ident(), i + 1, len(stc.calibPhotos[camL]))
            pathL = sc.photoRoot + "/" + stc.calibPhotos[camL][i]
            imgL = cv2.imread(pathL)
            pathR = sc.photoRoot + "/" + stc.calibPhotos[camR][i]
            imgR = cv2.imread(pathR)
            logger.debug("Thread %s: StereoCam.calibrateCameras - Left and right image loaded", get_ident())

            # Convert to grayscale
            imgL_gray = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)
            imgR_gray = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)
            logger.debug("Thread %s: StereoCam.calibrateCameras - Images converted to grayscale", get_ident())

            outputL = imgL.copy()
            outputR = imgR.copy()
            logger.debug("Thread %s: StereoCam.calibrateCameras - Images copied", get_ident())

            # Find chessboard corners
            retL, cornersL = cv2.findChessboardCorners(imgL_gray, stc.calibPatternSize, None)
            retR, cornersR = cv2.findChessboardCorners(imgR_gray, stc.calibPatternSize, None)
            logger.debug("Thread %s: StereoCam.calibrateCameras - Corners found: L=%s, R=%s", get_ident(), retL, retR)
            # logger.debug("Thread %s: StereoCam.calibrateCameras - Corners Left: %s", get_ident(), cornersL)
            # logger.debug("Thread %s: StereoCam.calibrateCameras - Corners Right: %s", get_ident(), cornersR)

            if retR and retL:
                # If found, add object points, image points (after refining them)
                obj_pts.append(objp)
                logger.debug("Thread %s: StereoCam.calibrateCameras - object points appended", get_ident())

                cornersRefL = cv2.cornerSubPix(imgL_gray, cornersL, (11, 11), (-1, -1), criteria)
                cornersRefR = cv2.cornerSubPix(imgR_gray, cornersR, (11, 11), (-1, -1), criteria)
                # logger.debug("Thread %s: StereoCam.calibrateCameras - Refined corners Left: %s", get_ident(), cornersL)
                # logger.debug("Thread %s: StereoCam.calibrateCameras - Refined corners Right: %s", get_ident(), cornersR)

                img_ptsL.append(cornersRefL)
                img_ptsR.append(cornersRefR)
                logger.debug("Thread %s: StereoCam.calibrateCameras - image points appended", get_ident())

        # Calibrate left camera
        logger.debug("Thread %s: StereoCam.calibrateCameras - Calibrating left camera.", get_ident())
        retL, mtxL, distL, rvecsL, tvecsL = cv2.calibrateCamera(
            obj_pts, img_ptsL, imgL_gray.shape[::-1], None, None
        )
        stc.calibRmsReproError[camL] = retL
        # logger.debug("Thread %s: StereoCam.calibrateCameras - Camera matrix: \n%s", get_ident(), mtxL)
        # logger.debug("Thread %s: StereoCam.calibrateCameras - Distortion Coeff: \n%s", get_ident(), distL)
        # logger.debug("Thread %s: StereoCam.calibrateCameras - Rotation vectors: \n%s", get_ident(), rvecsL)
        # logger.debug("Thread %s: StereoCam.calibrateCameras - Translation vectors: \n%s", get_ident(), tvecsL)

        logger.debug("Thread %s: StereoCam.calibrateCameras - Optimizing camera matrix.", get_ident())
        hL, wL = imgL_gray.shape[:2]
        new_mtxL, roiL = cv2.getOptimalNewCameraMatrix(mtxL, distL, (wL, hL), 1, (wL, hL))
        stc._calibCameraOK[camL] = True
        # logger.debug("Thread %s: StereoCam.calibrateCameras - OptimizedCamera matrix: \n%s", get_ident(), new_mtxL)

        # Calibrate right camera
        logger.debug("Thread %s: StereoCam.calibrateCameras - Calibrating right camera.", get_ident())
        retR, mtxR, distR, rvecsR, tvecsR = cv2.calibrateCamera(
            obj_pts, img_ptsR, imgR_gray.shape[::-1], None, None
        )
        stc.calibRmsReproError[camR] = retR
        hR, wR = imgR_gray.shape[:2]
        new_mtxR, roiR = cv2.getOptimalNewCameraMatrix(mtxR, distR, (wR, hR), 1, (wR, hR))
        stc._calibCameraOK[camR] = True

        logger.debug("Thread %s: StereoCam.calibrateCameras - Stereo calibration started.", get_ident())
        flags = 0
        flags |= cv2.CALIB_FIX_INTRINSIC
        # Here we fix the intrinsic camara matrixes so that only Rot, Trns, Emat and Fmat are calculated.
        # Hence intrinsic parameters are the same

        criteria_stereo = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # This step is performed to transformation between the two cameras and calculate Essential and Fundamenatl matrix
        retS, new_mtxL, distL, new_mtxR, distR, Rot, Trns, Emat, Fmat = cv2.stereoCalibrate(
            obj_pts,
            img_ptsL,
            img_ptsR,
            new_mtxL,
            distL,
            new_mtxR,
            distR,
            imgL_gray.shape[::-1],
            criteria_stereo,
            flags,
        )
        stc.calibStereoOK = True

        # Once we know the transformation between the two cameras we can perform stereo rectification
        # StereoRectify function
        logger.debug("Thread %s: StereoCam.calibrateCameras - Stereo rectification started.", get_ident())
        rectify_scale = stc.rectifyScale  # if 0 image croped, if 1 image not croped
        rect_l, rect_r, proj_mat_l, proj_mat_r, Q, roiL, roiR = cv2.stereoRectify(
            new_mtxL,
            distL,
            new_mtxR,
            distR,
            imgL_gray.shape[::-1],
            Rot,
            Trns,
            rectify_scale,
            (0, 0),
        )

        # Use the rotation matrixes for stereo rectification and camera intrinsics for undistorting the image
        # Compute the rectification map (mapping between the original image pixels and
        # their transformed values after applying rectification and undistortion) for left and right camera frames
        Left_Stereo_Map = cv2.initUndistortRectifyMap(
            new_mtxL, distL, rect_l, proj_mat_l, imgL_gray.shape[::-1], cv2.CV_16SC2
        )
        Right_Stereo_Map = cv2.initUndistortRectifyMap(
            new_mtxR, distR, rect_r, proj_mat_r, imgR_gray.shape[::-1], cv2.CV_16SC2
        )
        stc.stereoRectifyOK = True

        dataPath = sc.photoRoot + "/" + stc.calibDataSubPath
        dataFile = dataPath + stc.calibDataFile
        os.makedirs(dataPath, exist_ok=True)
        logger.debug("Thread %s: StereoCam.calibrateCameras - Saving parameters to %s", get_ident(), dataFile)
        cv_file = cv2.FileStorage(dataFile, cv2.FILE_STORAGE_WRITE)
        cv_file.write("Left_Stereo_Map_x", Left_Stereo_Map[0])
        cv_file.write("Left_Stereo_Map_y", Left_Stereo_Map[1])
        cv_file.write("Right_Stereo_Map_x", Right_Stereo_Map[0])
        cv_file.write("Right_Stereo_Map_y", Right_Stereo_Map[1])
        cv_file.release()
        stc.calibDataOK = True
        stc.calibDate = datetime.now()
        logger.debug("Thread %s: StereoCam.calibrateCameras - Success", get_ident())

    def startRecordStereo(self, fnRaw) -> str:
        """ Start recording stereo video
        
            Input:
                fnRaw: Filename without extension
            Return
                Filename for video file
        """
        logger.debug("Thread %s: StereoCam.startRecordStereo", get_ident())
        done = False
        err = ""
        camCfg = CameraCfg()
        sc = camCfg.serverConfig
        try:
            if self.recordingActive == False:
                self.recordFilename = fnRaw + ".mp4"
                fp = sc.photoRoot + "/" + "photos/" + "camera_S"
                os.makedirs(fp, exist_ok=True)
                save_path = fp + "/" + self.recordFilename
                self.frameSize = CameraCfg().liveViewConfig.stream_size
                logger.debug("Thread %s: StereoCam.startRecordStereo - video path:%s", get_ident(), save_path)
                # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fourcc = cv2.VideoWriter_fourcc(*'avc1') 
                logger.debug("Thread %s: StereoCam.startRecordStereo - fps:%s framesize:%s", get_ident(), self.framerate, self.frameSize)
                self.video = cv2.VideoWriter(save_path, fourcc, self.framerate, self.frameSize)
                assert self.video.isOpened()
                self.recordingActive = True
                sc.isStereoCamRecording = True
                self.recordIdx = 0

                # Create placeholder image
                imgFilename = fnRaw + ".jpg"
                img_path = fp + "/" + imgFilename
                cv2.imwrite(img_path, self.stereoFrameA)

            self._recordStereo()
            done = True
        except AssertionError as e:
            logger.error("Thread %s: StereoCam - AssertionError when starting recording: %s", get_ident(), e)
            err = f"AssertionError: {e}"
        except Exception as e:
            logger.error("Thread %s: StereoCam - Exception when starting recording: %s", get_ident(), e)
            err = f"Exception: {e}"
        return (done, self.recordFilename, err)

    def stopRecordStereo(self):
        """ Stop recording stereo
        
        """
        logger.debug("Thread %s: StereoCam.stopRecordStereo", get_ident())
        camCfg = CameraCfg()
        sc = camCfg.serverConfig
        if self.recordingActive == True:
            self.video.release()
            logger.debug("Thread %s: StereoCam.stopRecordStereo - video released with %s frames", get_ident(), self.recordIdx)
            self.recordingActive = False
            sc.isStereoCamRecording = False

    def _recordStereo(self):
        """ Record stereo as series of png - add new frame
        
        """
        if self.recordingActive == True:
            logger.debug("Thread %s: StereoCam._recordStereo - recordIdx:%s", get_ident(), self.recordIdx)
            if len(self.stereoFrameA.shape) == 2:
                framergb = cv2.cvtColor(self.stereoFrameA, cv2.COLOR_YUV2RGB_I420)
            elif len(self.stereoFrameA.shape) == 3:
                if self.stereoFrameA.shape[2] == 4:
                    framergb = cv2.cvtColor(self.stereoFrameA, cv2.COLOR_RGBA2RGB)
                else:
                    framergb = self.stereoFrameA
            else:
                framergb = self.stereoFrameA
            self.video.write(framergb)
            self.recordIdx += 1
