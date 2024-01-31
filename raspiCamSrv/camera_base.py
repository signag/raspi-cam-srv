import time
import threading
from _thread import get_ident
import logging

logger = logging.getLogger(__name__)

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        #logger.debug("CameraEvent.__init__")
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        #logger.debug("CameraEvent.wait")
        ident = get_ident()
        #logger.debug("Thread %s: CameraEvent.wait - waiting requested", ident)
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
            #logger.debug("Thread %s: CameraEvent.wait - added to events dict.", ident)
        #logger.debug("Thread %s: CameraEvent.wait - Flag is %s", ident, self.events[ident][0].is_set())
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        #logger.debug("CameraEvent.set")
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
                #logger.debug("Thread %s: CameraEvent.set - Flag for event %s changed from False to True -> unblock.", get_ident(), ident)
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                #logger.debug("Thread %s: CameraEvent.set - Flag for event %s was already True.", get_ident(), ident)
                if now - event[1] > 5:
                    #logger.debug("Thread %s: CameraEvent.set - Flag for event %s too old; marked for removal.", get_ident(), ident)
                    remove = ident
        if remove:
            #logger.debug("Thread %s: CameraEvent.set - Event %s removed.", get_ident(), ident)
            del self.events[remove]

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        #logger.debug("Thread %s: CameraEvent.clear - Flag set to False -> blocking.", get_ident())
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    thread = None               # background thread that reads frames from camera
    liveViewDeactivated = False
    videoThread = None
    timelapseThread = None
    frame = None                    # current frame is stored here by background thread
    last_access = 0                 # time of last client access to the camera
    stopRequested = False           # Request to stop the background thread
    stopVideoRequested = False      # Request to stop the video thread
    stopTimelapseRequested = False  # Request to stop the timelapse thread
    event = CameraEvent()

    def __init__(self):
        """Start the background camera thread if it isn't running yet."""
        logger.debug("Thread %s: BaseCamera.__init__", get_ident())
        #Only start the background thread for live view if the video thread is not running
        if BaseCamera.videoThread or BaseCamera.liveViewDeactivated:
            logger.debug("Thread %s: Not starting Live View thread. Video thread running or Live View deactivated")
        else:
            if BaseCamera.thread is None:
                logger.debug("Thread %s: BaseCamera.__init__: Starting new thread", get_ident())
                BaseCamera.last_access = time.time()

                # start background frame thread
                BaseCamera.thread = threading.Thread(target=self._thread)
                BaseCamera.thread.start()
                logger.debug("Thread %s: BaseCamera.__init__ - Thread started", get_ident())

                # wait until first frame is available
                logger.debug("Thread %s: BaseCamera.__init__ - waiting for frame", get_ident())
                BaseCamera.event.wait()
            else:
                logger.debug("Thread %s: BaseCamera.__init__ - Thread exists", get_ident())
                if not BaseCamera.thread.is_alive:
                    logger.debug("Thread %s: BaseCamera.__init__ - Thread is not alive", get_ident())
                    BaseCamera.thread = threading.Thread(target=self._thread)
                    BaseCamera.thread.start()
                    logger.debug("Thread %s: BaseCamera.__init__ - Thread started", get_ident())
                

    def get_frame(self):
        """Return the current camera frame."""
        #logger.debug("BaseCamera.get_frame")
        BaseCamera.last_access = time.time()

        # wait for a signal from the camera thread
        #logger.debug("Thread %s: BaseCamera.get_frame - waiting for frame", get_ident())
        BaseCamera.event.wait()
        #logger.debug("Thread %s: BaseCamera.get_frame - continue", get_ident())
        BaseCamera.event.clear()

        #logger.debug("Returning frame")
        return BaseCamera.frame

    @staticmethod
    def frames():
        """"Generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    @classmethod
    def _thread(cls):
        """Camera background thread."""
        logger.debug("Thread %s: BaseCamera._thread", get_ident())
        try:
            frames_iterator = cls.frames()
            logger.debug("Thread %s: BaseCamera._thread - frames_iterator instantiated", get_ident())
            for frame in frames_iterator:
                BaseCamera.frame = frame
                #logger.debug("Thread %s: BaseCamera._thread - received frame from camera", get_ident())
                BaseCamera.event.set()  # send signal to clients
                time.sleep(0)
                
                # Check whether stop is requested
                if BaseCamera.stopRequested:
                    frames_iterator.close()
                    BaseCamera.stopRequested = False
                    logger.debug("Thread %s: BaseCamera._thread - Thread is requested to stop.", get_ident())
                    break

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - BaseCamera.last_access > 10:
                    frames_iterator.close()
                    logger.debug("Thread %s: BaseCamera._thread - Stopping camera thread due to inactivity.", get_ident())
                    break
        except Exception:
            logger.error("Thread %s: BaseCamera._thread - Exception.", get_ident())
            if frames_iterator:
                frames_iterator.close()
            BaseCamera.event.clear()
                
        BaseCamera.thread = None
