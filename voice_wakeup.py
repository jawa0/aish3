from dotenv import load_dotenv
import logging
import os
import pvporcupine
import pyaudio
from queue import Empty, Queue


class PhraseListener:

    def __init__(self, detected_callback: callable = None):
        load_dotenv()
        self.PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

        self._on_detected_callback = detected_callback

    
    def start(self):
        self._pa = pyaudio.PyAudio()
        self._in_stream = None

        # @todo @bug what about multiple instance?
        PhraseListener._audio_q = None

        self._pv_handle = pvporcupine.create(
            access_key=self.PICOVOICE_ACCESS_KEY,
            keyword_paths=["./res/wake-phrases/Yar-assistant_en_mac_v2_2_0/Yar-assistant_en_mac_v2_2_0.ppn"]
        )

        logging.debug(f"PicoVoice expected sample rate (Hz): {self._pv_handle.sample_rate}")
        logging.debug(f"PicoVoice expected frame length: {self._pv_handle.frame_length}")

        PhraseListener._audio_q = Queue()

        self._in_stream = self._pa.open(
            rate=self._pv_handle.sample_rate,
            channels=1,
            format=pyaudio.paUInt8,
            input=True,
            frames_per_buffer=self._pv_handle.frame_length,
            stream_callback=PhraseListener._audio_input_stream_callback
        )


    def update(self):
        # logging.debug('PhraseListener.update()')
        if self._in_stream is None:
            return
        
        try:
            audio_bytes = PhraseListener._audio_q.get_nowait()
        except Empty:
            return

        logging.debug(f"PhraseListener.update() audio_bytes: {len(audio_bytes)}")

        i_keyword = self._pv_handle.process(audio_bytes)
        if i_keyword >= 0:
            logging.info('Detected wakeup phrase.')
            if self._on_detected_callback is not None:
                self._on_detected_callback()


    def stop(self):
        self._in_stream.stop_stream()
        self._in_stream.close()
        self._in_stream = None
        PhraseListener._audio_q = None

        self._pv_handle.delete()
        self._pv_handle = None

        self._pa.terminate()
        self._pa = None


    @staticmethod
    def _audio_input_stream_callback(in_data, frame_count, time_info, status_flags):
        PhraseListener._audio_q.put(in_data)
        return (None, pyaudio.paContinue)
