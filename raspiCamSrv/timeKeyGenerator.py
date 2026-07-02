"""Gererator for unique time-based keys

The time part has millisecond precision and a counter is used
to ensure uniqueness within the same millisecond.
"""
import time
from itertools import count
from datetime import datetime

class TimeKeyGenerator():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TimeKeyGenerator, cls).__new__(cls)
            cls._counter = count()
            cls._last_sec = [None]
        return cls._instance

    def make_key(self, event_time=None):
        if event_time is None:
            event_time = datetime.now()
        ts = event_time.strftime("%Y-%m-%dT%H:%M:%S.%f")
        sec =ts[:19]  # reuse the formatted string as the reset key
        if self._last_sec[0] != sec:
            self._counter = count()
            self._last_sec[0] = sec
        return f"{ts}_{next(self._counter):04d}"
    
if __name__ == "__main__":
    for _ in range(10):
        print(TimeKeyGenerator().make_key())
        time.sleep(0.1)