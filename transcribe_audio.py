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


    # def send(self):
    #     messages = [{"role": u.get_role().lower(), "content": u.get_text()} for u in self.utterances]
    #     print(messages)

    #     OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    #     OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")
        
    #     openai.api_key = OPENAI_API_KEY
    #     openai.organization = OPENAI_ORGANIZATION

    #     # Add Answer TextArea
    #     answer = self.gui.create_control("ChatMessageUI", role="Assistant", text='')
    #     self.add_child(answer, add_to_focus_ring=False)
    #     self.focusRing.add(answer.text_area, set_focus=True)

    #     # Shrink previous messages
    #     for u in self.utterances:
    #         u.text_area.set_size(PANEL_WIDTH, 60)
    #     self.utterances.append(answer)
    #     self.updateLayout

    #     completion = openai.ChatCompletion.create(model="gpt-4", messages=messages, stream=True)
    #     self.gui._running_completions[self] = completion


    def get_json(self):
        return {
            "type": "VoiceTranscriptContainer",
            "version": 1,
        }


    # def load(self):
    #     print("loading")
    #     try:
    #         with open("aish_workspace.json", "r") as f:
    #             data = json.load(f)
    #             self.system.text_area.text_buffer.set_text(data["system_text"])
    #             self.system.text_area.text_buffer.move_point_to_start()
    #             self.system.text_area.text_buffer.clear_mark()
    #     except FileNotFoundError:
    #         self.save()


GUI.register_control_type("VoiceTranscriptContainer", VoiceTranscriptContainer)
