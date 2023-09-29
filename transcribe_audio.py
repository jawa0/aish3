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

import pyaudio
from multiprocessing import Process, Queue
import os


SAMPLE_RATE = 16000
SAMPLE_FORMAT = pyaudio.paInt16
N_RECORDING_CHANNELS = 1


PANEL_WIDTH = 350
PANEL_HEIGHT = 120


class VoiceTranscriptContainer(GUIContainer):

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

        self.command_q = Queue()
        self.recording_q = Queue()

        self.recording_process = Process(target=VoiceTranscriptContainer.recordingProcessMain, args=(self.command_q, self.recording_q))
        self.recording_process.start()


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
        self.command_q.put("q")
        return super()._on_quit()
    

    @staticmethod
    def recordingProcessMain(commandQueue, outputQueue):
        STATE_UNINITIALIZED = 0
        STATE_INITIALIZED = 1
        STATE_RECORDING = 2

        state = STATE_UNINITIALIZED
        stream = None


        def info(msg):
            print(f"[INFO] pid: {os.getpid()}, msg: '{msg}'")


        def stop_recording(stream, state):
            if stream:
                stream.stop_stream()
                stream.close()
                stream = None

            info("Recording stopped")
            state = STATE_INITIALIZED


        info("Recording process started")

        pa = pyaudio.PyAudio()
        state = STATE_INITIALIZED
        info("Recording process initialized")
        info(f"* Sample rate: {SAMPLE_RATE}; Sample format: {SAMPLE_FORMAT}; Channels: {N_RECORDING_CHANNELS}")
        info(f"Waiting for commands...")

        while True:
            cmd = commandQueue.get()    # Blocks until command is received
            info(f"Received command: {cmd}")
            if cmd == "q":
                break

            if cmd == "r":
                if state < STATE_INITIALIZED:
                    info("Command ignored: recording process not initialized")
                    continue
                elif state == STATE_RECORDING:
                    info("Command ignored: already recording")
                    continue

                stream = pa.open(format=SAMPLE_FORMAT, channels=N_RECORDING_CHANNELS, rate=SAMPLE_RATE, input=True, )
                state = STATE_RECORDING
                info("Recording started")

                audio_data = b''
                while state == STATE_RECORDING:
                    n_frames_available = stream.get_read_available()
                    if n_frames_available:
                        audio_data += stream.read(n_frames_available)

                    # @todo: do I really need to use exceptions here? @perf
                    try:
                        cmd = commandQueue.get_nowait()
                        if cmd == "r":
                            stop_recording(stream, state)
                    except:
                        pass
                outputQueue.put(audio_data)
        
        pa.terminate()
        stop_recording(stream, state)
        state = STATE_UNINITIALIZED


    def get_text(self):
        return self.text_area.text_buffer.get_text()
        

    def handle_event(self, event):
        if event.type == sdl2.SDL_KEYDOWN:
            cmdPressed = (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI))
            keySymbol = event.key.keysym.sym

            if cmdPressed:
                # Cmd+R toggles recording audio
                if keySymbol == sdl2.SDLK_r:
                    # self.send()
                    return True
                            
            if keySymbol == sdl2.SDLK_RETURN:
                # Delegate to GUIContainer
                handled = super().handle_event(event)
                if handled:
                    return True
            
        return self.parent.handle_event(event)


    def get_json(self):
        return {
            "type": "VoiceTranscriptContainer",
            "version": 1,
        }


GUI.register_control_type("VoiceTranscriptContainer", VoiceTranscriptContainer)
