from google.cloud import texttospeech
import logging
import pyaudio
import pydub


class VoiceOut:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(language_code='en-GB', name='en-GB-Neural2-F')
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0,
            sample_rate_hertz=44100,
            effects_profile_id=['headphone-class-device'])


    def say(self, text):
        logging.debug(f'VoiceOut.say: {text}')
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(input=synthesis_input, voice=self.voice, audio_config=self.audio_config)

        audio_bytes = response.audio_content
        logging.debug(f'audio_data: {len(audio_bytes)} bytes')

        audio = pydub.AudioSegment(data=audio_bytes, sample_width=2, frame_rate=44100, channels=1)
        # audio.play()

        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(audio.sample_width),
                        channels=audio.channels,
                        rate=audio.frame_rate,
                        output=True)

        # Just in case there were any exceptions/interrupts, we release the resource
        # So as not to raise OSError: Device Unavailable should play() be used again
        try:
            stream.write(audio_bytes)
        finally:
            stream.stop_stream()
            stream.close()

            p.terminate()




        return response.audio_content