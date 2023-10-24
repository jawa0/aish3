import logging
import pyaudio
import threading
from typing import Callable


class AudioService:
    _lock = threading.Lock()
    _pa = pyaudio.PyAudio()

    def __init__(self):
        pass


    def start(self):
        logging.debug('AudioService.start()')
        with AudioService._lock:
            if AudioService._pa is None:
                AudioService._pa = pyaudio.PyAudio()


    def stop(self):
        logging.debug('AudioService.stop()')
        with AudioService._lock:
            if AudioService._pa is not None:
                AudioService._pa.terminate()
                AudioService._pa = None


    @classmethod
    def get_wakeword_input_stream(cls, handler: Callable):
        logging.debug('AudioService.get_input_wakeword_stream()')
        with cls._lock:
            assert(cls._pa is not None)
            return cls._pa.open(
                rate=16_000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512,
                stream_callback=handler
            )


    def __del__(self):
        self.stop()