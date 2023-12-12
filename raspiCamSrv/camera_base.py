import time
import threading
from greenlet import getcurrent as get_ident
import logging

logger = logging.getLogger(__name__)

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        logger.debug("CameraEvent.__init__")
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        logger.debug("CameraEvent.wait")
        ident = get_ident()
        logger.debug("Register client with ident %s", ident)
        if ident not in self.events:
            logger.debug("Adding to events dict")
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        logger.debug("CameraEvent.set")
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                if now - event[1] > 5:
                    remove = ident
        if remove:
            del self.events[remove]

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        logger.debug("CameraEvent.clear")
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera
    event = CameraEvent()

    def __init__(self):
        """Start the background camera thread if it isn't running yet."""
        logger.debug("BaseCamera.__init__")
        if BaseCamera.thread is None:
            logger.debug("Starting new thread")
            BaseCamera.last_access = time.time()

            # start background frame thread
            BaseCamera.thread = threading.Thread(target=self._thread)
            BaseCamera.thread.start()
            logger.debug("Thread started")

            # wait until first frame is available
            BaseCamera.event.wait()

    def get_frame(self):
        """Return the current camera frame."""
        #logger.debug("BaseCamera.get_frame")
        BaseCamera.last_access = time.time()

        # wait for a signal from the camera thread
        #logger.debug("Waiting for signal from camera thread")
        BaseCamera.event.wait()
        #logger.debug("Clearing events")
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
        logger.debug("BaseCamera._thread")
        frames_iterator = cls.frames()
        logger.debug("frames_iterator instantiated")
        for frame in frames_iterator:
            BaseCamera.frame = frame
            BaseCamera.event.set()  # send signal to clients
            time.sleep(0)

            # if there hasn't been any clients asking for frames in
            # the last 10 seconds then stop the thread
            if time.time() - BaseCamera.last_access > 10:
                frames_iterator.close()
                logger.debug('Stopping camera thread due to inactivity.')
                break
        BaseCamera.thread = None
