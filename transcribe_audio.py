"""This file should be imported from your main application script to make sure
that the app configuration is loaded, before it's needed."""

# Copyright 2023-2024 Jabavu W. Adams

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sdl2
import json
import logging
import os
import openai

from record_audio import MicrophoneStream, N_SAMPLES_PER_SECOND, N_CHUNK_SAMPLES, N_SAMPLE_BYTES

# import pyaudio
from multiprocessing import Process, Queue
import os
import assemblyai as aai
import webrtcvad
import queue
import wave
from datetime import datetime
from utils import unique_filename


aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


SAMPLE_RATE = 16000
N_RECORDING_CHANNELS = 1

N_BYTES_PER_20_MS = N_SAMPLES_PER_SECOND * N_SAMPLE_BYTES // 50  # The VAD can only handle chunks of 10, 20, or 30 ms.


PANEL_WIDTH = 350
PANEL_HEIGHT = 120


class VoiceTranscriber:

    def __init__(self, **kwargs):
        logging.debug("VoiceTranscriber.__init__()")
        self.vad = None
        self.stream = None
        self.recording_start_dt = None
        self.transcriber = None
        self.all_audio_bytes = b""
        self.incoming_text = Queue()  # Entries are (text: str, is_final: bool)

        self.session = kwargs.get("session")
        assert(self.session is not None)


    def start_recording(self):
        logging.debug("ENTER VoiceTranscriber.start_recording()")
        assert(not self.is_recording())

        self.vad = webrtcvad.Vad()

        self.stream = MicrophoneStream(N_SAMPLES_PER_SECOND, N_CHUNK_SAMPLES)
        self.stream.start()
        self.recording_start_dt = datetime.now()

        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=N_SAMPLES_PER_SECOND,
            on_data=self._on_transcribe_data,
            on_error=self._on_transcribe_error,
            on_open=self._on_transcribe_open,
            on_close=self._on_transcribe_close
        )
        self.transcriber.connect()

        logging.debug("EXIT VoiceTranscriber.start_recording()")


    def stop_recording(self):
        logging.debug("ENTER VoiceTranscriber.stop_recording()")
        if self.stream is None:
            return

        self.stream.stop()
        self.stream = None

        assert(self.transcriber is not None)
        self.transcriber.close()
        self.transcriber = None
        self.vad = None


        # Write audio to file
        # audio_filename = unique_filename(f"audio_in_{self.recording_start_dt.strftime('%Y-%m-%d_%H%Mh_%Ss')}.wav")
        # self._write_audio_file(audio_filename, self.all_audio_bytes)
        
        # n_frames = len(self.all_audio_bytes) // N_SAMPLE_BYTES // N_RECORDING_CHANNELS
        # c_seconds = n_frames / N_SAMPLES_PER_SECOND

        # logging.info(f"Wrote {c_seconds} seconds ({n_frames} frames) of audio to {audio_filename}")
        self.recording_start_dt = None
        self.all_audio_bytes = b""

        logging.debug("EXIT VoiceTranscriber.stop_recording()")


    def is_recording(self):
        return self.stream is not None
    

    # @note: this is executing on a different thread than my app functions
    # like on_update()
    def _on_transcribe_data(self, transcript: aai.RealtimeTranscript):
        # print(f"_on_transcribe_data(): tid={threading.current_thread().ident}")
        # 
        logging.debug(transcript)
        if not transcript.text:
            return

        if isinstance(transcript, aai.RealtimePartialTranscript):
            self.incoming_text.put((transcript.text, False))
        elif isinstance(transcript, aai.RealtimeFinalTranscript):
            self.incoming_text.put((transcript.text, True))


    def _on_transcribe_error(self, error: aai.RealtimeError):
        logging.error(f"Assembly AI Error: {error}")


    def _on_transcribe_open(self, session_opened: aai.RealtimeSessionOpened):
        logging.debug(f"Assembly AI session opened with ID: {session_opened.session_id}")

    def _on_transcribe_close(self):
        # @note @bug whiy is this called twice on stop_recording?
        logging.debug("Assembly AI session closed.")


    def update(self):
        # logging.debug('ENTER VoiceTranscriber.update()')
        # logging.debug(f"self.is_recording(): {self.is_recording()}")
        if self.is_recording():
            assert(self.transcriber is not None)

            audio_bytes = self.stream.get_nowait()
            n_audio_bytes = len(audio_bytes)
            n_audio_frames = n_audio_bytes // N_SAMPLE_BYTES // N_RECORDING_CHANNELS
            n_ms = n_audio_frames * 1000 // SAMPLE_RATE

            if len(audio_bytes) > 0:
                # logging.debug(f"Audio: {len(audio_bytes)} bytes ({n_audio_frames} frames; {n_ms} ms)")
                
                # Any speech detected in this audio chunk?
                is_speech = False
                for i in range(0, n_audio_bytes, N_BYTES_PER_20_MS):
                    vad_chunk = audio_bytes[i:i+N_BYTES_PER_20_MS]
                    is_speech = self.vad.is_speech(vad_chunk, N_SAMPLES_PER_SECOND)
                    if is_speech:
                        break

                if is_speech:
                    # logging.debug('is_speech: True. Sending for transcription.')
                    self.transcriber.stream(audio_bytes)
                else:
                    # logging.debug('is_speech: False.')
                    pass

                self.all_audio_bytes += audio_bytes
                # print(f"Total audio: {len(self.all_audio_bytes)} bytes")

        text = ""
        was_final = False
        try:
            while True:
                (text, is_final) = self.incoming_text.get_nowait()
                if len(text) == 0:
                    continue

                if is_final:
                    logging.debug(f"** FINAL text: '{text}'")
                else:
                    logging.debug(f"** PARTIAL text: '{text}'")
                
                self.session.publish("transcribed_text", (text, is_final))  # @todo use Blinker named signal instead
                
                was_final = is_final

        except queue.Empty:
            pass

        # logging.debug('EXIT VoiceTranscriber.update()')


    def _write_audio_file(self, filename, audio_bytes):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(N_RECORDING_CHANNELS)
            wf.setsampwidth(N_SAMPLE_BYTES)
            wf.setframerate(N_SAMPLES_PER_SECOND)
            wf.writeframes(audio_bytes)
