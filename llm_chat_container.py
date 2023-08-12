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


class LLMChatContainer(GUIContainer):

    class ChatMessageUI(GUIContainer):
        @classmethod
        def from_json(cls, json, **kwargs):
            assert(json["class"] == cls.__name__)
            gui = kwargs.get('gui')
            assert(gui is not None)

            kwargs["default_setup"] = False
            instance = gui.create_control(json["class"], **kwargs)
            instance.set_bounds(*json["bounding_rect"])

            assert(len(json["children"]) == 2)
            assert(json["children"][0]["class"] == "Label")
            assert(json["children"][1]["class"] == "TextArea")

            for child_json in json["children"]:
                child_class_name = child_json["class"]
                child_class = GUI.control_class(child_class_name)
                child = child_class.from_json(child_json, **kwargs)
                instance.add_child(child)
                if child_class_name == "Label":
                    instance.label = child
                elif child_class_name == "TextArea":
                    instance.text_area = child
            return instance


        def __init__(self, children=None, role="User", text="", **kwargs):
            super().__init__(children=children, layout=ColumnLayout(), **kwargs)
            
            default_setup = kwargs.get('default_setup', True)
            if default_setup:
                self.label = Label(text=role, w=PANEL_WIDTH, h=20, **kwargs)
                self.add_child(self.label, add_to_focus_ring=False)

                self.text_area = TextArea(18, w=PANEL_WIDTH, h=PANEL_HEIGHT, **kwargs)
                self.text_area.text_buffer.set_text(text)
                self.add_child(self.text_area, add_to_focus_ring=False)


        def get_role(self):
            return self.label.text
        
        def set_role(self, role):
            self.label.text = role

        def get_text(self):
            return self.text_area.text_buffer.get_text()
        
        def set_text(self, text):
            self.text_area.text_buffer.set_text(text)

        def _set_focus(self, has_focus):
            if has_focus:
                return self.gui.set_focus(self.text_area)
            else:
                super()._set_focus(has_focus)


    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)
    

    def __init__(self, default_setup=True, **kwargs):
        super().__init__(**kwargs)
        self.draw_bounds = True
        
        self.set_layout(ColumnLayout())
        assert(self.focusRing is not None)
        self.system = None
        self.utterances = []

        if default_setup:
            self.add_child(Label(text="GPT-4 Chat", w=PANEL_WIDTH, h=20, **kwargs),
                           add_to_focus_ring=False)

            self.system = self.ChatMessageUI(role="System", **kwargs)
            # self.gui.set_focus(self.system)

            self.utterances = [self.system, self.ChatMessageUI(role="User", **kwargs)]
            for utterance in self.utterances:
                self.add_child(utterance, add_to_focus_ring=False)
                self.focusRing.add(utterance.text_area)

        # self.focusRing.focus(self.system.text_area)


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
            if child_class_name == "ChatMessageUI":
                instance.utterances.append(child)
                instance.focusRing.add(child.text_area)
        return instance


    def handle_event(self, event):
        if event.type == sdl2.SDL_KEYDOWN:
            # Cmd+G sends messages to GPT
            if event.key.keysym.sym == sdl2.SDLK_g and (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)):
                self.send()
                return True
            if event.key.keysym.sym == sdl2.SDLK_u and (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)): 
                # Cmd+U creates a new user message
                user = self.ChatMessageUI(role="User", renderer=self.renderer, font_manager=self.font_manager, gui=self.gui)
                self.add_child(user, add_to_focus_ring=False)
                self.utterances.append(user)
                self.focusRing.add(user.text_area)
                self.focusRing.focus(user.text_area)
                return True  # event was handled
            if event.key.keysym.sym == sdl2.SDLK_RETURN:
                # Delegate to GUIContainer
                handled = super().handle_event(event)
                if handled:
                    return True
            
        return self.parent.handle_event(event)


    def _set_focus(self, focus):
        return True


    def send(self):
        messages = [{"role": u.get_role().lower(), "content": u.get_text()} for u in self.utterances]
        print(messages)

        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")
        
        openai.api_key = OPENAI_API_KEY
        openai.organization = OPENAI_ORGANIZATION

        response = openai.ChatCompletion.create(model="gpt-4", messages=messages)

        answer = self.ChatMessageUI(role="Assistant", text=response['choices'][0]['message']['content'], renderer=self.renderer, font_manager=self.font_manager, gui=self.gui)
        self.add_child(answer, add_to_focus_ring=False)
        self.focusRing.add(answer.text_area, set_focus=True)

        for u in self.utterances:
            u.text_area.set_size(PANEL_WIDTH, 60)
        self.utterances.append(answer)
        self.updateLayout


    def get_json(self):
        return {
            "type": "LLMChatContainer",
            "version": 1,
            "system_text": self.system.text_area.text_buffer.get_text(),
        }


    def load(self):
        print("loading")
        try:
            with open("aish_workspace.json", "r") as f:
                data = json.load(f)
                self.system.text_area.text_buffer.set_text(data["system_text"])
                self.system.text_area.text_buffer.move_point_to_start()
                self.system.text_area.text_buffer.clear_mark()
        except FileNotFoundError:
            self.save()


GUI.register_control_type("LLMChatContainer", LLMChatContainer)
GUI.register_control_type("ChatMessageUI", LLMChatContainer.ChatMessageUI)