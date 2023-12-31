import logging
import os
import platform
import pvporcupine
import pyaudio
from queue import Empty, Queue
import struct
from audio_service import AudioService


def bytes_to_ints(byte_data):
    """Convert a byte array into a list of integers. Each integer is two bytes. Endeaness is unspecified."""
    return struct.unpack(str(len(byte_data) // 2) + 'h', byte_data)


class PhraseListener:

    def __init__(self, detected_callback: callable = None):
        logging.debug('PhraseListener.__init__()')
        self._on_detected_callback = detected_callback

        self._pv_handle = None

        PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
        if not PICOVOICE_ACCESS_KEY:
            logging.error("PICOVOICE_ACCESS_KEY is not set. Cannot enable voice input. Either set the environment variable, or disable voice input.")
            raise Exception("PICOVOICE_ACCESS_KEY is not set. Cannot enable voice input. Either set the environment variable, or disable voice input.")

    
    def start(self):
        logging.debug('PhraseListener.start()')
        self._in_stream = None

        # @todo @bug what about multiple instance?
        PhraseListener._audio_q = None

        keyword_paths = {"macOS": "./res/wake-phrases/Yar-assistant_en_mac_v2_2_0/Yar-assistant_en_mac_v2_2_0.ppn",
                "RaspberryPi": "./res/wake-phrases/Yarr-Assistant_en_raspberry_pi_v3_0_0/Yarr-Assistant_en_raspberry_pi_v3_0_0.ppn",
        }

        if platform.system() == "Darwin":
            KEYWORD_PATH = keyword_paths["macOS"]
        elif platform.system() == "Linux" and platform.machine().startswith("armv"):
            KEYWORD_PATH = keyword_paths["RaspberryPi"]
        else:
            raise NotImplementedError("Platform not supported.")

        self._pv_handle = pvporcupine.create(
            access_key=os.getenv("PICOVOICE_ACCESS_KEY"),
            keyword_paths=[KEYWORD_PATH],
        )

        logging.debug(f"PicoVoice expected sample rate (Hz): {self._pv_handle.sample_rate}")
        logging.debug(f"PicoVoice expected frame length: {self._pv_handle.frame_length}")

        PhraseListener._audio_q = Queue()

        self._in_stream = AudioService.get_wakeword_input_stream(PhraseListener._audio_input_stream_callback)


    def update(self):
        # logging.debug('PhraseListener.update()')
        if self._in_stream is None:
            return
        
        try:
            audio_ints = PhraseListener._audio_q.get_nowait()
        except Empty:
            return

        # logging.debug(f"PhraseListener.update() audio_ints: {len(audio_ints)}")

        i_keyword = self._pv_handle.process(audio_ints)
        if i_keyword >= 0:
            logging.info('Detected wakeup phrase.')
            if self._on_detected_callback is not None:
                self._on_detected_callback()


    def stop(self):
        logging.debug('PhraseListener.stop()')
        self._in_stream.stop_stream()
        self._in_stream.close()
        self._in_stream = None
        PhraseListener._audio_q = None

        self._pv_handle.delete()
        self._pv_handle = None


    @staticmethod
    def _audio_input_stream_callback(in_data, frame_count, time_info, status_flags):
        audio_ints = bytes_to_ints(in_data)
        PhraseListener._audio_q.put(audio_ints)
        return (None, pyaudio.paContinue)
