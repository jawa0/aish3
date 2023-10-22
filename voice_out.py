from google.cloud import texttospeech
import logging
import pyaudio
import pydub
import threading


class VoiceOut:
    N_SAMPLES_PER_SECOND = 44_100
    N_BYTES_PER_SAMPLE = 2
    N_CHANNELS = 1

    _lock = threading.Lock()
    _current_speaker = None
    _pa = pyaudio.PyAudio()


    @classmethod
    def get_current_speaker(cls):
        with VoiceOut._lock:
            return VoiceOut._current_speaker
        

    def __init__(self, on_speech_done=[]):
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(language_code='en-GB', name='en-GB-Neural2-D')
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.2,
            pitch=-20.0,
            volume_gain_db=0.0,
            sample_rate_hertz=VoiceOut.N_SAMPLES_PER_SECOND,
            effects_profile_id=['headphone-class-device'])
        
        self._current_text = None
        self._current_audio = None
        self._current_byte_offset = None

        self.stream = None
        self._on_done = on_speech_done


    def grab_conch(self):
        with VoiceOut._lock:
            assert(VoiceOut._current_speaker is None)
            VoiceOut._current_speaker = self


    def drop_conch(self):
        with VoiceOut._lock:
            VoiceOut._current_speaker = None

        # self.stream.stop_stream()
        # self.stream.close()
        # self.stream = None


    def say(self, text):
        logging.debug(f'ENTER VoiceOut.say: """{text}"""')
        self.grab_conch()

        self._current_text = text

        # @todo this *is* a blocking call to get text -> audio
        # consider processing smaller amounts of text at a time.
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(input=synthesis_input, voice=self.voice, audio_config=self.audio_config)

        audio_bytes = response.audio_content
        logging.debug(f'audio_data: {len(audio_bytes)} bytes')

        audio = pydub.AudioSegment(data=audio_bytes, 
                                   sample_width=VoiceOut.N_BYTES_PER_SAMPLE, 
                                   frame_rate=VoiceOut.N_SAMPLES_PER_SECOND, 
                                   channels=VoiceOut.N_CHANNELS)
        self._current_audio = audio
        self._current_byte_offset = 0

        # We want to output what might be some long audio, but to do it without blocking our
        # thread. So, we use a callback.

        self.stream = VoiceOut._pa.open(format=VoiceOut._pa.get_format_from_width(audio.sample_width),
                        channels=audio.channels,
                        rate=audio.frame_rate,
                        output=True,
                        stream_callback=VoiceOut._stream_callback)

        # # Just in case there were any exceptions/interrupts, we release the resource
        # # So as not to raise OSError: Device Unavailable should play() be used again
        # try:
        #     stream.write(audio_bytes)
        # finally:
        #     stream.stop_stream()
        #     stream.close()


        logging.debug(f'EXIT VoiceOut.say')  # Demonstrate it's not blocking on audio output

    
    # @note that this is called from/in a different thread
    # Do not call logging or print from this function! It's time-critical!

    @staticmethod
    def _stream_callback(in_data, frame_count, time_info, status_flags):
        # Log entry to _stream_callback, and thread id
        # logging.debug(f'ENTER VoiceOut._stream_callback tid={threading.current_thread().ident}')

        vo = VoiceOut.get_current_speaker()
        audio = vo._current_audio
        i = vo._current_byte_offset

        n_bytes_requested = frame_count * VoiceOut.N_BYTES_PER_SAMPLE * VoiceOut.N_CHANNELS
        assert(n_bytes_requested >= 0)

        n_bytes_remaining = max(0, len(audio.raw_data) - i)
        is_last = n_bytes_remaining <= n_bytes_requested

        n_bytes_to_send = min(n_bytes_requested, n_bytes_remaining)

        audio_bytes = audio.raw_data[i:i + n_bytes_to_send]
        i += n_bytes_to_send
        vo._current_byte_offset = i

        # logging.debug(f'n_bytes_requested: {n_bytes_requested}, n_bytes_remaining: {n_bytes_remaining}, n_bytes_to_send: {n_bytes_to_send}, is_last: {is_last} audio_bytes: {len(audio_bytes)} bytes')
        if is_last:
            return_code = pyaudio.paComplete
            if n_bytes_remaining == 0:
                audio_bytes = None

            # logging.debug('OUTPUT STREAMING AUDIO DONE')
            vo.drop_conch()
            for callback in vo._on_done:
                callback()
        else:
            return_code = pyaudio.paContinue

        # logging.debug(f'EXIT VoiceOut._stream_callback')
        return (audio_bytes, return_code)
