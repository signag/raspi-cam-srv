##############################################################################################
# Motion detection Algorithms after Isaac Berrios
# Source: https://medium.com/@itberrios6/introduction-to-motion-detection-part-1-e031b0bb9bb2
#
##############################################################################################
import cv2
import os
import shutil
from glob import glob
import copy
from _thread import get_ident
import re
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from datetime import datetime
from raspiCamSrv.camCfg import CameraCfg
import logging

logger = logging.getLogger(__name__)

class MotionDetectAlgoIB():
    """ Superclass for group of algorithms according to Isaac Berrios
    """
    def __init__(self) -> None:
        # Frames 2:t, 1:t-1
        self._frame1 = None
        self._frame2 = None
        self._frame1g = None
        self._frame2g = None
        self._detections = None
        # Algorithn reference and testing
        self._test = False
        self._testFrame1 = None
        self._testFrame2 = None
        self._testFrame3 = None
        self._testFrame4 = None
        
        # Variables for video generation
        self._cfg = CameraCfg()
        self._tc = self._cfg.triggerConfig
        self._recordFilename = None
        self._recordIdx = None
        self._frameSize = None
        self._framerate = 20
        self._recordingStart = None
        self._recordingActive = False
        self._video = None
    
    @property
    def frame1(self):
        return self._frame1

    @frame1.setter
    def frame1(self, value):
        self._frame1 = value
    
    @property
    def frame2(self):
        return self._frame2

    @frame2.setter
    def frame2(self, value):
        self._frame2 = value
    
    @property
    def frame1g(self):
        return self._frame1g

    @frame1g.setter
    def frame1g(self, value):
        self._frame1g = value
    
    @property
    def frame2g(self):
        return self._frame2g

    @frame2g.setter
    def frame2g(self, value):
        self._frame2g = value
    
    @property
    def detections(self):
        return self._detections

    @detections.setter
    def detections(self, value):
        self._detections = value
    
    @property
    def test(self) -> bool:
        return self._test

    @test.setter
    def test(self, value:bool):
        self._test = value
    
    @property
    def testFrame1(self):
        return self._testFrame1

    @testFrame1.setter
    def testFrame1(self, value):
        self._testFrame1 = value
    
    @property
    def testFrame2(self):
        return self._testFrame2

    @testFrame2.setter
    def testFrame2(self, value):
        self._testFrame2 = value
    
    @property
    def testFrame3(self):
        return self._testFrame3

    @testFrame3.setter
    def testFrame3(self, value):
        self._testFrame3 = value
    
    @property
    def testFrame4(self):
        return self._testFrame4

    @testFrame4.setter
    def testFrame4(self, value):
        self._testFrame4 = value

    @property
    def tc(self):
        return self._tc

    @tc.setter
    def tc(self, value):
        self._tc = value
    
    @property
    def recordFilename(self):
        return self._recordFilename

    @recordFilename.setter
    def recordFilename(self, value):
        self._recordFilename = value
    
    @property
    def recordIdx(self):
        return self._recordIdx

    @recordIdx.setter
    def recordIdx(self, value):
        self._recordIdx = value
    
    @property
    def frameSize(self):
        return self._frameSize

    @frameSize.setter
    def frameSize(self, value):
        self._frameSize = value
    
    @property
    def framerate(self):
        return self._framerate

    @framerate.setter
    def framerate(self, value):
        self._framerate = value
    
    @property
    def recordingStart(self):
        return self._recordingStart

    @recordingStart.setter
    def recordingStart(self, value):
        self._recordingStart = value
    
    @property
    def recordingActive(self):
        return self._recordingActive

    @recordingActive.setter
    def recordingActive(self, value):
        self._recordingActive = value
    
    @property
    def video(self):
        return self._video

    @video.setter
    def video(self, value):
        self._video = value
        
    def startRecordMotion(self, fnRaw) -> str:
        """ Start recording motion
        
            Input:
                fnRaw: Filename without extension
            Return
                Filename for video file
        """
        #logger.debug("Thread %s: MotionDetectFrameDiff.startRecordMotion", get_ident())
        done = False
        err = ""
        try:
            if self.recordingActive == False:
                self.recordFilename = fnRaw + ".mp4"
                save_path = os.path.join(self.tc.actionPath, self.recordFilename)
                #fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
                fourcc = cv2.VideoWriter_fourcc(*'avc1') 
                fps = self.framerate
                logger.debug("Thread %s: MotionDetectFrameDiff.startRecordMotion - fps:%s framesize:%s", get_ident(), fps, self.frameSize)
                self.video = cv2.VideoWriter(save_path, fourcc, fps, self.frameSize)
                assert self.video.isOpened()
                self.recordingActive = True
                self.recordIdx = 0
            self.recordMotion()
            done = True
        except Exception as e:
            logger.error("Thread %s: MotionDetectFrameDiff - error when starting recording: %s", get_ident(), e)
            err = str(e)
        return (done, self.recordFilename, err)

    def stopRecordMotion(self):
        """ Stop recording motion
        
        """
        #logger.debug("Thread %s: MotionDetectFrameDiff.stopRecordMotion", get_ident())
        if self.recordingActive == True:
            self.video.release()
            logger.debug("Thread %s: MotionDetectFrameDiff.stopRecordMotion - video released with %s frames", get_ident(), self.recordIdx)
            self.recordingActive = False

    def recordMotion(self):
        """ Record motion as series of png - add new frame
        
        """
        if self.recordingActive == True:
            #logger.debug("Thread %s: MotionDetectFrameDiff.recordMotion - recordIdx:%s", get_ident(), self.recordIdx)
            self._draw_bboxes()
            if len(self.frame2.shape) == 2:
                framergb = cv2.cvtColor(self.frame2, cv2.COLOR_YUV2RGB_I420)
            elif len(self.frame2.shape) == 3:
                if self.frame2.shape[2] == 4:
                    framergb = cv2.cvtColor(self.frame2, cv2.COLOR_RGBA2RGB)
                else:
                    framergb = self.frame2
            else:
                framergb = self.frame2
            self.video.write(framergb)
            self.recordIdx += 1

    def _frameToStream(self, frame):
        """Convert frame to bytestream"""
        frameb = None
        (stat, frame_jpg) = cv2.imencode(".jpg", frame)
        if stat == True:
            frame_jpg_arr = np.array(frame_jpg)
            frameb = frame_jpg_arr.tobytes()
        return frameb

    def _draw_bboxes(self):
        """ Draw bounding boxes"""
        #logger.debug("Thread %s: MotionDetectFrameDiff._draw_bboxes", get_ident())
        if not self.detections is None:
            for det in self.detections:
                x1,y1,x2,y2 = det
                cv2.rectangle(self.frame2, (x1,y1), (x2,y2), (0,255,0), 2)

    def _get_contour_detections(self, mask, thresh=400):
        """ Obtains initial proposed detections from contours discoverd on the mask. 
        
            Scores are taken as the bbox area, larger is higher.
            Inputs:
                mask - thresholded image mask
                thresh - threshold for contour size
            Outputs:
                detectons - array of proposed detection bounding boxes and scores [[x1,y1,x2,y2,s]]
            """
        # get mask contours
        contours, _ = cv2.findContours(mask, 
                                    cv2.RETR_EXTERNAL, # cv2.RETR_TREE, 
                                    cv2.CHAIN_APPROX_TC89_L1)
        detections = []
        for cnt in contours:
            x,y,w,h = cv2.boundingRect(cnt)
            area = w*h
            if area > thresh: 
                detections.append([x,y,x+w,y+h, area])

        return np.array(detections)

    def _non_max_suppression(self, boxes, scores, threshold=1e-1):
        """ Perform non-max suppression on a set of bounding boxes and corresponding scores
        
            Inputs:
                boxes: a list of bounding boxes in the format [xmin, ymin, xmax, ymax]
                scores: a list of corresponding scores 
                threshold: the IoU (intersection-over-union) threshold for merging bounding boxes
            Outputs:
                boxes - non-max suppressed boxes
        """
        # Sort the boxes by score in descending order
        boxes = boxes[np.argsort(scores)[::-1]]

        # remove all contained bounding boxes and get ordered index
        order = self._remove_contained_bboxes(boxes)

        keep = []
        while order:
            i = order.pop(0)
            keep.append(i)
            for j in order:
                # Calculate the IoU between the two boxes
                intersection = max(0, min(boxes[i][2], boxes[j][2]) - max(boxes[i][0], boxes[j][0])) * \
                            max(0, min(boxes[i][3], boxes[j][3]) - max(boxes[i][1], boxes[j][1]))
                union = (boxes[i][2] - boxes[i][0]) * (boxes[i][3] - boxes[i][1]) + \
                        (boxes[j][2] - boxes[j][0]) * (boxes[j][3] - boxes[j][1]) - intersection
                iou = intersection / union

                # Remove boxes with IoU greater than the threshold
                if iou > threshold:
                    order.remove(j)
                    
        return boxes[keep]

    def _remove_contained_bboxes(self, boxes):
        """ Removes all smaller boxes that are contained within larger boxes.
        
            Requires bboxes to be soirted by area (score)
            Inputs:
                boxes - array bounding boxes sorted (descending) by area 
                        [[x1,y1,x2,y2]]
            Outputs:
                keep - indexes of bounding boxes that are not entirely contained 
                    in another box
            """
        check_array = np.array([True, True, False, False])
        keep = list(range(0, len(boxes)))
        for i in keep: # range(0, len(bboxes)):
            for j in range(0, len(boxes)):
                # check if box j is completely contained in box i
                if np.all((np.array(boxes[j]) >= np.array(boxes[i])) == check_array):
                    try:
                        keep.remove(j)
                    except ValueError:
                        continue
        return keep

class MotionDetectFrameDiff(MotionDetectAlgoIB):
    """ Motion detection by Frame Differencing
    """
    def __init__(self) -> None:
        super().__init__()
        
        # Algorithn reference and testing
        self.algoReferenceTit = "Isaac Berrios - Introduction to Motion Detection: Part 1"
        self.algoReferenceURL = "https://medium.com/@itberrios6/introduction-to-motion-detection-part-1-e031b0bb9bb2"
        self.testFrame1Title = "Gray Scale Video"
        self.testFrame2Title = "Gray Scale Frame Difference"
        self.testFrame3Title = "Motion Mask"
        self.testFrame4Title = "Bounding Boxes after Non-Maximal Suppression"

        # Algorithm parameters
        self._bbox_threshold = 400
        self._nms_threshold = 0.001

    @property
    def bbox_threshold(self):
        return self._bbox_threshold

    @bbox_threshold.setter
    def bbox_threshold(self, value):
        self._bbox_threshold = value

    @property
    def nms_threshold(self):
        return self._nms_threshold

    @nms_threshold.setter
    def nms_threshold(self, value):
        self._nms_threshold = value

    def detectMotion(self, frame2, frame1):
        """ Use frame differencing method to detect motion
        
            Inputs:
                frame2 : frame at t+1
                frame1 : frame at t
            Returns:
                motion : True/False if motion has been detected (#bboxes > 0)
                trigger: Dict describing trigger
        """
        #logger.debug("Thread %s: MotionDetectFrameDiff.detectMotion", get_ident())
        motion = False
        self.frame2 = copy.copy(frame2)
        self.frame1 = copy.copy(frame1)
        self.frame2g = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)
        self.frame1g = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
        if self.test == True:
            self.testFrame1 = self._frameToStream(self.frame2g)
            #logger.debug("Thread %s: MotionDetectFrameDiff.detectMotion - staged frame_gray", get_ident())

        self.detections = self._get_detections(self.frame1g, self.frame2g, bbox_thresh=self.bbox_threshold, nms_thresh=self.nms_threshold)
        #logger.debug("Thread %s: MotionDetectFrameDiff.detectMotion - got detections: %s", get_ident(), self.detections)
        if self.test == True:
            if not self.detections is None:
                if len(self.detections) > 0:
                    self._draw_bboxes()
                    #logger.debug("Thread %s: MotionDetectFrameDiff.detectMotion - done draw_bboxes", get_ident())
            self.testFrame4 = self._frameToStream(self.frame2)
        else:
            if not self.detections is None:
                if len(self.detections) > 0:
                    motion = True
        trigger = {"trigger":"Motion Detection", "triggertype":"Frame Diff.", "triggerparam":{"BBox_thr": self.bbox_threshold, "IOU_thr": self.nms_threshold}}
        #logger.debug("Thread %s: MotionDetectFrameDiff.detectMotion - motion:%s", get_ident(), motion)
        return (motion, trigger)

    def _get_detections(self, frame1, frame2, bbox_thresh=400, nms_thresh=1e-3, mask_kernel=np.array((9,9), dtype=np.uint8)):
        """ Main function to get detections via Frame Differencing
        
            Inputs:
                frame1 - Grayscale frame at time t
                frame2 - Grayscale frame at time t + 1
                bbox_thresh - Minimum threshold area for declaring a bounding box 
                nms_thresh - IOU threshold for computing Non-Maximal Supression
                mask_kernel - kernel for morphological operations on motion mask
            Outputs:
                detections - list with bounding box locations of all detections
                    bounding boxes are in the form of: (xmin, ymin, xmax, ymax)
            """
        #logger.debug("Thread %s: MotionDetectFrameDiff._get_detections", get_ident())
        # get image mask for moving pixels
        mask = self._get_mask(frame1, frame2, mask_kernel)
        #logger.debug("Thread %s: MotionDetectFrameDiff._get_detections got mask", get_ident())
        if self.test == True:
            self.testFrame3 = self._frameToStream(mask)

        # get initially proposed detections from contours
        detections = self._get_contour_detections(mask, bbox_thresh)
        if len(detections) == 0:
            return None

        # separate bboxes and scores
        bboxes = detections[:, :4]
        scores = detections[:, -1]

        # perform Non-Maximal Supression on initial detections
        return self._non_max_suppression(bboxes, scores, nms_thresh)

    def _get_mask(self, frame1, frame2, kernel=np.array((9,9), dtype=np.uint8)):
        """ Obtains image mask
        
            Inputs: 
                frame1 - Grayscale frame at time t
                frame2 - Grayscale frame at time t + 1
                kernel - (NxN) array for Morphological Operations
            Outputs: 
                mask - Thresholded mask for moving pixels
            """
        frame_diff = cv2.subtract(frame2, frame1)

        # blur the frame difference
        frame_diff = cv2.medianBlur(frame_diff, 3)
        if self.test == True:
            self.testFrame2 = self._frameToStream(frame_diff)
        
        mask = cv2.adaptiveThreshold(frame_diff, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
                cv2.THRESH_BINARY_INV, 11, 3)

        mask = cv2.medianBlur(mask, 3)

        # morphological operations
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        return mask

class MotionDetectOpticalFlow(MotionDetectAlgoIB):
    """ Motion detection by Optical Flow
    """
    def __init__(self) -> None:
        super().__init__()
        
        # Algorithn reference and testing
        self.algoReferenceTit = "Isaac Berrios - Introduction to Motion Detection: Part 2"
        self.algoReferenceURL = "https://medium.com/@itberrios6/introduction-to-motion-detection-part-2-6ec3d6b385d4"
        self.testFrame1Title = "Gray Scale blurred"
        self.testFrame2Title = "Optical Flow"
        self.testFrame3Title = "Motion Mask"
        self.testFrame4Title = "Bounding Boxes after Non-Maximal Suppression"

        # Algorithm parameters
        self.bbox_threshold = 400
        self.nms_threshold = 0.001
        self.motion_threshold = 1

    def detectMotion(self, frame2, frame1):
        """ Use frame differencing method to detect motion
        
            Inputs:
                frame2 : frame at t+1
                frame1 : frame at t
            Returns:
                motion : True/False if motion has been detected
                trigger: Dict describing trigger
        """
        #logger.debug("Thread %s: MotionDetectOpticalFlow.detectMotion", get_ident())
        motion = False
        self.frame2 = copy.copy(frame2)
        self.frame1 = copy.copy(frame1)

        self.detections = self._get_detections(self.frame1, self.frame2, motion_thresh=self.motion_threshold, bbox_thresh=self.bbox_threshold, nms_thresh=self.nms_threshold)
        #logger.debug("Thread %s: MotionDetectOpticalFlow.detectMotion - got detections: %s", get_ident(), self.detections)
        if self.test == True:
            if not self.detections is None:
                if len(self.detections) > 0:
                    self._draw_bboxes()
                    #logger.debug("Thread %s: MotionDetectOpticalFlow.detectMotion - done draw_bboxes", get_ident())
            self.testFrame4 = self._frameToStream(self.frame2)
        else:
            if not self.detections is None:
                if len(self.detections) > 0:
                    motion = True
        trigger = {"trigger":"Motion Detection", "triggertype":"Optical Flow", "triggerparam":{"Motion_thr": self.motion_threshold, "BBox_thr": self.bbox_threshold, "IOU_thr": self.nms_threshold}}    
        #logger.debug("Thread %s: MotionDetectOpticalFlow.detectMotion - motion:%s", get_ident(), motion)
        return (motion, trigger)

    def _get_detections(self, frame1, frame2, motion_thresh=1, bbox_thresh=400, nms_thresh=0.1, mask_kernel=np.ones((7,7), dtype=np.uint8)):
        """ Main function to get detections via Frame Differencing
            Inputs:
                frame1 - Grayscale frame at time t
                frame2 - Grayscale frame at time t + 1
                motion_thresh - Minimum flow threshold for motion
                bbox_thresh - Minimum threshold area for declaring a bounding box 
                nms_thresh - IOU threshold for computing Non-Maximal Supression
                mask_kernel - kernel for morphological operations on motion mask
            Outputs:
                detections - list with bounding box locations of all detections
                    bounding boxes are in the form of: (xmin, ymin, xmax, ymax)
            """
        # get optical flow
        flow = self._compute_flow(frame1, frame2)
        if self.test == True:
            self.testFrame2 = self._frameToStream(self._get_flow_viz(flow))
            #logger.debug("Thread %s: MotionDetectOpticalFlow._get_detections - staged testFrame2", get_ident())

        # separate into magntiude and angle
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        motion_mask = self._get_motion_mask(mag, motion_thresh=motion_thresh, kernel=mask_kernel)
        if self.test == True:
            self.testFrame3 = self._frameToStream(motion_mask)

        # get initially proposed detections from contours
        detections = self._get_contour_detections(motion_mask, thresh=bbox_thresh)
        if len(detections) == 0:
            return None

        # separate bboxes and scores
        bboxes = detections[:, :4]
        scores = detections[:, -1]

        # perform Non-Maximal Supression on initial detections
        return self._non_max_suppression(bboxes, scores, threshold=nms_thresh)
    
    def _compute_flow(self, frame1, frame2):
        # convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)
        self.frame1g = gray1
        self.frame2g = gray2

        # blurr image
        gray1 = cv2.GaussianBlur(gray1, dst=None, ksize=(3,3), sigmaX=5)
        gray2 = cv2.GaussianBlur(gray2, dst=None, ksize=(3,3), sigmaX=5)
        if self.test == True:
            self.testFrame1 = self._frameToStream(gray2)
            #logger.debug("Thread %s: MotionDetectOpticalFlow._compute_flow - staged frame_gray", get_ident())

        flow = cv2.calcOpticalFlowFarneback(gray1, gray2, None,
                                            pyr_scale=0.75,
                                            levels=3,
                                            winsize=5,
                                            iterations=3,
                                            poly_n=10,
                                            poly_sigma=1.2,
                                            flags=0)
        return flow

    def _get_flow_viz(self, flow):
        """ Obtains BGR image to Visualize the Optical Flow 
        """
        hsv = np.zeros((flow.shape[0], flow.shape[1], 3), dtype=np.uint8)
        hsv[..., 1] = 255

        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        hsv[..., 0] = ang*180/np.pi/2
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        return rgb

    def _get_motion_mask(self, flow_mag, motion_thresh=1, kernel=np.ones((7,7))):
        """ Obtains Detection Mask from Optical Flow Magnitude
            Inputs:
                flow_mag (array) Optical Flow magnitude
                motion_thresh - thresold to determine motion
                kernel - kernal for Morphological Operations
            Outputs:
                motion_mask - Binray Motion Mask
            """
        motion_mask = np.uint8(flow_mag > motion_thresh)*255

        motion_mask = cv2.erode(motion_mask, kernel, iterations=1)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        return motion_mask

    def _get_contour_detections_2(self, mask, ang, angle_thresh=2, thresh=400):
        """ Obtains initial proposed detections from contours discoverd on the
            mask. Scores are taken as the bbox area, larger is higher.
            Inputs:
                mask - thresholded image mask
                angle_thresh - threshold for flow angle standard deviation
                thresh - threshold for contour size
            Outputs:
                detectons - array of proposed detection bounding boxes and scores 
                            [[x1,y1,x2,y2,s]]
            """
        # get mask contours
        contours, _ = cv2.findContours(mask, 
                                        cv2.RETR_EXTERNAL, # cv2.RETR_TREE, 
                                        cv2.CHAIN_APPROX_TC89_L1)
        temp_mask = np.zeros_like(mask) # used to get flow angle of contours
        angle_thresh = angle_thresh*ang.std()
        detections = []
        for cnt in contours:
            # get area of contour
            x,y,w,h = cv2.boundingRect(cnt)
            area = w*h

            # get flow angle inside of contour
            cv2.drawContours(temp_mask, [cnt], 0, (255,), -1)
            flow_angle = ang[np.nonzero(temp_mask)]

            if (area > thresh) and (flow_angle.std() < angle_thresh):
                detections.append([x,y,x+w,y+h, area])

        return np.array(detections)

class MotionDetectBgSubtract(MotionDetectAlgoIB):
    """ Motion detection by Background Subtraction
    """
    def __init__(self) -> None:
        super().__init__()
        
        # Algorithn reference and testing
        self.algoReferenceTit = "Isaac Berrios - Introduction to Motion Detection: Part 3"
        self.algoReferenceURL = "https://medium.com/@itberrios6/introduction-to-motion-detection-part-3-025271f66ef9"
        self.testFrame1Title = "Normal Video"
        self.testFrame2Title = "Current Background"
        self.testFrame3Title = "Motion Mask"
        self.testFrame4Title = "Bounding Boxes after Non-Maximal Suppression"

        # Algorithm parameters
        self.bbox_threshold = 400
        self.nms_threshold = 0.001
        self._backSubModel = "MOG2"
        self._backSub = cv2.createBackgroundSubtractorMOG2(varThreshold=16, detectShadows=True)
        self._backSub.setShadowThreshold(0.5)
    
    @property
    def backSubModel(self):
        return self._backSubModel

    @backSubModel.setter
    def backSubModel(self, value):
        logger.debug("Thread %s: MotionDetectBgSubtract.backSubModel - value: %s", get_ident(), value)
        if value == "MOG2":
            self._backSub = cv2.createBackgroundSubtractorMOG2(varThreshold=16, detectShadows=True)
            self._backSub.setShadowThreshold(0.5)
        elif value == "KNN":
            self._backSub = cv2.createBackgroundSubtractorKNN(dist2Threshold=1000, detectShadows=True)
        else:
            value = "MOG2"
            self._backSub = cv2.createBackgroundSubtractorMOG2(varThreshold=16, detectShadows=True)
            self._backSub.setShadowThreshold(0.5)
        self._backSubModel = value

    def detectMotion(self, frame2, frame1):
        """ Use frame differencing method to detect motion
        
            Inputs:
                frame2 : frame at t+1
                frame1 : frame at t
            Returns:
                motion : True/False if motion has been detected
                trigger: Dict describing trigger
        """
        #logger.debug("Thread %s: MotionDetectBgSubtract.detectMotion", get_ident())
        motion = False
        self.frame2 = copy.copy(frame2)
        self.frame1 = copy.copy(frame1)
        self.frame2g = cv2.cvtColor(self.frame2, cv2.COLOR_RGB2GRAY)
        self.frame1g = cv2.cvtColor(self.frame1, cv2.COLOR_RGB2GRAY)
        if self.test == True:
            self.testFrame1 = self._frameToStream(self.frame2)
            #logger.debug("Thread %s: MotionDetectBgSubtract.detectMotion - staged frame_gray", get_ident())

        kernel=np.array((9,9), dtype=np.uint8)
        self.detections = self._get_detections(self._backSub, self.frame2, bbox_thresh=self.bbox_threshold, nms_thresh=self.nms_threshold, kernel=kernel)
        #logger.debug("Thread %s: MotionDetectBgSubtract.detectMotion - got detections: %s", get_ident(), self.detections)
        if self.test == True:
            if not self.detections is None:
                if len(self.detections) > 0:
                    self._draw_bboxes()
                    #logger.debug("Thread %s: MotionDetectBgSubtract.detectMotion - done draw_bboxes", get_ident())
            self.testFrame4 = self._frameToStream(self.frame2)
        else:
            if not self.detections is None:
                if len(self.detections) > 0:
                    motion = True
        trigger = {"trigger":"Motion Detection", "triggertype":"BG Subtraction", "triggerparam":{"Model": self.backSubMod, "BBox_thr": self.bbox_threshold, "IOU_thr": self.nms_threshold}}    
        #logger.debug("Thread %s: MotionDetectBgSubtract.detectMotion - motion:%s", get_ident(), motion)
        return (motion, trigger)
    
    def _get_detections(self, backSub, frame, bbox_thresh=100, nms_thresh=0.1, kernel=np.array((9,9), dtype=np.uint8)):
        """ Main function to get detections via Frame Differencing
            Inputs:
                backSub - Background Subtraction Model
                frame - Current BGR Frame
                bbox_thresh - Minimum threshold area for declaring a bounding box
                nms_thresh - IOU threshold for computing Non-Maximal Supression
                kernel - kernel for morphological operations on motion mask
            Outputs:
                detections - list with bounding box locations of all detections
                    bounding boxes are in the form of: (xmin, ymin, xmax, ymax)
            """
        #logger.debug("Thread %s: MotionDetectBgSubtract._get_detections - backSub %s", get_ident(), backSub)
        # Update Background Model and get foreground mask
        fg_mask = backSub.apply(frame)
        if self.test == True:
            self.testFrame2 = self._frameToStream(backSub.getBackgroundImage())
            #logger.debug("Thread %s: MotionDetectBgSubtract._get_detections - staged background", get_ident())

        # get clean motion mask
        motion_mask = self._get_motion_mask(fg_mask, kernel=kernel)
        if self.test == True:
            self.testFrame3 = self._frameToStream(motion_mask)

        # get initially proposed detections from contours
        detections = self._get_contour_detections(motion_mask, bbox_thresh)
        if len(detections) == 0:
            return None

        # separate bboxes and scores
        bboxes = detections[:, :4]
        scores = detections[:, -1]

        # perform Non-Maximal Supression on initial detections
        return self._non_max_suppression(bboxes, scores, nms_thresh)
    
    def _get_motion_mask(self, fg_mask, min_thresh=0, kernel=np.array((9,9), dtype=np.uint8)):
        """ Obtains image mask
            Inputs: 
                fg_mask - foreground mask
                kernel - kernel for Morphological Operations
            Outputs: 
                mask - Thresholded mask for moving pixels
            """
        _, thresh = cv2.threshold(fg_mask,min_thresh,255,cv2.THRESH_BINARY)
        motion_mask = cv2.medianBlur(thresh, 3)
        
        # morphological operations
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        return motion_mask    
    