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
            logging.debug('AudioService.start(): GOT LOCK')
            if AudioService._pa is None:
                AudioService._pa = pyaudio.PyAudio()
        logging.debug('AudioService.start(): RELEASED LOCK')


    def stop(self):
        logging.debug('AudioService.stop()')
        with AudioService._lock:
            logging.debug('AudioService.stop(): GOT LOCK')
            if AudioService._pa is not None:
                logging.debug('AudioService.stop(): terminating PyAudio')
                AudioService._pa.terminate()
                logging.debug('AudioService.stop(): terminated PyAudio')
                AudioService._pa = None
        logging.debug('AudioService.stop(): RELEASED LOCK')


    @classmethod
    def get_wakeword_input_stream(cls, handler: Callable):
        logging.debug('AudioService.get_input_wakeword_stream()')
        with cls._lock:
            logging.debug('AudioService.get_input_wakeword_stream(): GOT LOCK')
            assert(cls._pa is not None)
            stream = cls._pa.open(
                rate=16_000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512,
                stream_callback=handler
            )
        logging.debug('AudioService.get_input_wakeword_stream(): RELEASED LOCK')
        return stream


    @classmethod
    def get_voice_input_stream(cls, handler: Callable):
        logging.debug('AudioService.get_voice_input_stream()')
        with cls._lock:
            logging.debug('AudioService.get_voice_input_stream(): GOT LOCK')
            assert(cls._pa is not None)
            stream = cls._pa.open(
                rate=16_000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=3200,
                stream_callback=handler
            )
        logging.debug('AudioService.get_voice_input_stream(): RELEASED LOCK')
        return stream


    @classmethod
    def get_voice_output_stream(cls, handler: Callable):
        logging.debug('AudioService.get_voice_output_stream()')
        with cls._lock:
            logging.debug('AudioService.get_voice_output_stream(): GOT LOCK')
            assert(cls._pa is not None)
            stream = cls._pa.open(
                rate=44_100,
                channels=1,
                format=pyaudio.paInt16,
                output=True,
                stream_callback=handler
            )
        logging.debug('AudioService.get_voice_output_stream(): RELEASED LOCK')
        return stream

    # def __del__(self):
    #     self.stop()