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
import logging
import matplotlib
import os
import openai
from typing import Optional
from gui import GUI, GUIContainer
from label import Label
from textarea import TextArea
from gui_layout import ColumnLayout
from gui_focus import FocusRing
from session import ChatCompletionHandler
from llm_chat_container import LLMChatContainer


PANEL_WIDTH = 600
PANEL_HEIGHT = 120


class LLMAgentChat(LLMChatContainer):

    
    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)
    

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        default_setup = kwargs.get('default_setup', True)
        if default_setup:
            self.title.set_text("Agent Chat")
            self.system.text_area.text_buffer.set_text("")


    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        kwargs = super(LLMAgentChat, cls)._enrich_kwargs(json, **kwargs)
        kwargs["default_setup"] = False

        gui = kwargs.get('gui')
        assert(gui is not None)

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
                instance.focus_ring.add(child.text_area)

        # @note Override settings on legacy saved components...
        for child in instance.children:
            # @todo fix @bug this is a nasty @hack that caused a bug on load when I changed the title
            if isinstance(child, Label) and \
                (child.get_text().startswith("LLM Chat") or \
                 child.get_text().startswith("Agent Chat")):
                
                instance.title = child
                break

        instance.title._draggable = False
        instance.title._editable = False
        for utterance in instance.utterances:
            utterance._draggable = False
            utterance._editable = False

            utterance.text_area._draggable = False
            utterance.label._draggable = False
            utterance.label._editable = False


        return instance


    def handle_event(self, event):
        if event.type == sdl2.SDL_KEYDOWN:
            cmdPressed = (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI))
            keySymbol = event.key.keysym.sym

            if cmdPressed:
                # Cmd+G sends messages to GPT
                if keySymbol == sdl2.SDLK_g:
                    self.send()
                    return True
                
                # Cmd+U creates a new user message
                elif keySymbol == sdl2.SDLK_u: 
                    user = LLMChatContainer.ChatMessageUI(role="User", gui=self.gui)
                    self.add_child(user, add_to_focus_ring=False)
                    self.utterances.append(user)
                    self.focus_ring.add(user.text_area)
                    self.gui.set_focus(user.text_area, True)
                    return True  # event was handled
                
                # Cmd+Backspace/Delete deletes the currently focused message
                # If the whole LLMChatContainer is focused, then delete this chat.
                elif keySymbol == sdl2.SDLK_BACKSPACE:
                    focused_control = self.gui.get_focus()
                    if focused_control is self:
                        self.parent.remove_child(self)
                        return True

            
            if keySymbol == sdl2.SDLK_RETURN:
                # Delegate to GUIContainer
                handled = super().handle_event(event)
                if handled:
                    return True
            
        return self.parent.handle_event(event)


    def on_update(self, dt):
        super().on_update(dt)
    

    def draw(self):
        super().draw()


GUI.register_control_type("LLMAgentChat", LLMAgentChat)