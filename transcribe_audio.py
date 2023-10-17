# Copyright 2023 Jabavu W. Adams

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
import os
from dotenv import load_dotenv
import openai
from gui import GUI, GUIContainer
from label import Label
from textarea import TextArea
from gui_layout import ColumnLayout
from gui_focus import FocusRing

from record_audio import MicrophoneStream, N_SAMPLES_PER_SECOND, N_CHUNK_SAMPLES, N_SAMPLE_BYTES

# import pyaudio
from multiprocessing import Process, Queue
import os
import assemblyai as aai
import webrtcvad
import threading
import queue

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


SAMPLE_RATE = 16000
N_RECORDING_CHANNELS = 1

N_BYTES_PER_20_MS = N_SAMPLES_PER_SECOND * N_SAMPLE_BYTES // 50  # The VAD can only handle chunks of 10, 20, or 30 ms.


PANEL_WIDTH = 350
PANEL_HEIGHT = 120


class VoiceTranscriptContainer(GUIContainer):
    STATE_IDLE = 0
    STATE_RECORDING = 1

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)
    

    def __init__(self, default_setup=True, **kwargs):
        super().__init__(**kwargs)
        self.draw_bounds = True
        
        self.set_layout(ColumnLayout())
        assert(self.focusRing is not None)

        if default_setup:
            self.label = Label(text="Voice Transcript", w=PANEL_WIDTH, h=20, **kwargs)
            self.add_child(self.label, add_to_focus_ring=False)

            self.text_area = TextArea(18, w=PANEL_WIDTH, h=PANEL_HEIGHT, **kwargs)
            self.add_child(self.text_area, add_to_focus_ring=False)
        
        self.state = self.STATE_IDLE
        self.vad = None
        self.stream = None
        self.transcriber = None
        self.incoming_text = queue.Queue()
        self.insertion_point = 0


    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        gui = kwargs.get('gui')
        assert(gui is not None)

        kwargs["default_setup"] = False
        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])

        for child_json in json["children"]:
            child_class_name = child_json["class"]
            # child = gui.create_control(child_class_name, **kwargs)
            child_class = GUI.control_class(child_class_name)
            child = child_class.from_json(child_json, **kwargs)
            instance.add_child(child, add_to_focus_ring=False)
            if child_class_name == "Label":
                instance.label = child
            elif child_class_name == "TextArea":
                instance.text_area = child
        return instance


    def _on_quit(self):
        if self.state == self.STATE_RECORDING:
            self.stop_recording()

        return super()._on_quit()
    

    def get_text(self):
        return self.text_area.text_buffer.get_text()
        

    def handle_event(self, event):
        if event.type == sdl2.SDL_KEYDOWN:
            cmdPressed = (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI))
            keySymbol = event.key.keysym.sym

            if cmdPressed and keySymbol == sdl2.SDLK_RETURN:
                print('Command: toggle recording')
                if self.state == self.STATE_IDLE:
                    self.start_recording()
                    return True
                    
                elif self.state == self.STATE_RECORDING:
                    self.stop_recording()
                    return True
            
        return self.parent.handle_event(event)


    def start_recording(self):
        assert(self.state == self.STATE_IDLE)

        self.vad = webrtcvad.Vad()

        self.stream = MicrophoneStream(N_SAMPLES_PER_SECOND, N_CHUNK_SAMPLES)
        self.stream.start()

        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=N_SAMPLES_PER_SECOND,
            on_data=self._on_transcribe_data,
            on_error=self._on_transcribe_error,
            on_open=self._on_transcribe_open,
            on_close=self._on_transcribe_close
        )
        self.transcriber.connect()
        self.state = self.STATE_RECORDING


    def stop_recording(self):
        assert(self.state == self.STATE_RECORDING)
        self.stream.stop()
        self.stream = None

        assert(self.transcriber is not None)
        self.transcriber.close()
        self.transcriber = None
        self.vad = None
        self.state = self.STATE_IDLE

    # @note: this is executing on a different thread than my app functions
    # like on_update()
    def _on_transcribe_data(self, transcript: aai.RealtimeTranscript):
        # print(f"_on_transcribe_data(): tid={threading.current_thread().ident}")
        # print(transcript)
        if not transcript.text:
            return

        if isinstance(transcript, aai.RealtimePartialTranscript):
            self.incoming_text.put((transcript.text, False))
        elif isinstance(transcript, aai.RealtimeFinalTranscript):
            self.incoming_text.put((transcript.text, True))


    def _on_transcribe_error(self, error: aai.RealtimeError):
        print(f"Assembly AI Error: {error}")


    def _on_transcribe_open(self, session_opened: aai.RealtimeSessionOpened):
        print(f"Assembly AI session opened with ID: {session_opened.session_id}")

    def _on_transcribe_close(self):
        # @note @bug whiy is this called twice on stop_recording?
        print("Assembly AI session closed.")


    def on_update(self, dt):
        # print(f"on_update(): tid={threading.current_thread().ident}")
        if self.state == self.STATE_RECORDING:
            assert(self.transcriber is not None)
            assert(self.stream is not None)
            audio_bytes = self.stream.get_nowait()
            n_audio_bytes = len(audio_bytes)
            n_audio_frames = n_audio_bytes // N_SAMPLE_BYTES // N_RECORDING_CHANNELS
            n_ms = n_audio_frames * 1000 // SAMPLE_RATE

            # print(dt, len(audio_bytes))
            if len(audio_bytes) > 0:
                print(f"Audio: {len(audio_bytes)} bytes ({n_audio_frames} frames; {n_ms} ms)")
                
                # Any speech detected in this audio chunk?
                is_speech = False
                for i in range(0, n_audio_bytes, N_BYTES_PER_20_MS):
                    vad_chunk = audio_bytes[i:i+N_BYTES_PER_20_MS]
                    is_speech = self.vad.is_speech(vad_chunk, N_SAMPLES_PER_SECOND)
                    if is_speech:
                        break

                if is_speech:
                    print('is_speech: True. Sending for transcription.')
                    self.transcriber.stream(audio_bytes)
                else:
                    print('is_speech: False.')

        text = ""
        was_final = False
        try:
            while True:
                (t, is_final) = self.incoming_text.get_nowait()
                if len(t) == 0:
                    continue

                if is_final:
                    text = t
                else:
                    text += t
                was_final = is_final

        except queue.Empty:
            if len(text) > 0:
                pass
                # print('**', text)

        if len(text) > 0:
            ta = self.text_area
            tb = self.text_area.text_buffer

            tb.set_mark(self.insertion_point)
            tb.move_point_to_end()
            tb.delete_selection()
            tb.insert(text)
            tb.clear_mark()
            if was_final:
                tb.insert('\n')
                self.insertion_point = tb.get_point()

            self.text_area.set_needs_redraw()

            focused_control = self.gui.get_focus()
            if was_final and \
                focused_control is not None and focused_control is not self and isinstance(focused_control, TextArea):
                
                ta = focused_control
                tb = ta.text_buffer
                tb.insert(text + '\n')
                ta.set_needs_redraw()


    def get_json(self):
        return {
            "type": "VoiceTranscriptContainer",
            "version": 1,
        }


GUI.register_control_type("VoiceTranscriptContainer", VoiceTranscriptContainer)
