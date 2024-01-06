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


from datetime import datetime
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
from session import ChatCompletionHandler
from llm_chat_container import LLMChatContainer

import getpass
import platform
import pystache
import pytz
from tzlocal import get_localzone




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

            # We don't have a system prompt, so remove the one created in LLMChatContainer
            system = self.system
            self.remove_child(system)
            self.utterances.remove(system)
            del self.system

        self.system_prompt = \
"""
You are an AI assistant. We are engaging in a dialogue where I take the role of the 
teacher and you take the role of the student. I will be telling you things, and I 
want you to remember these things by storing what I tell you to your knowledge base. 
Let's call these things I tell you "factoids". For each factoid you are told, you 
should also remember the time you were told it, and by whom.
"""

        self.factoid_prompt_template = \
"""
Factoid:

{{ Content }}

Metadata:

Source of factoid (User): {{ User }}
Client Software: AISH3 Python GUI client
Client System Platform: {{ ClientPlatform }}
Client Timezone {{ ClientTimezone }}
Client UTC Time {{ ClientUTCTime }}
Client Local Time {{ ClientLocalTime }}

"""        
# Client Location: {{ClientLocation}}
# User Location: {{UserLocation}}
        
        self.factoid_ner_prompt_template = \
"""
Do Named Entity Extraction (NER) to discover all entities mentioned in the following text:

{{ Content }}
"""
        self.factoid_vss_summary_prompt_template = \
"""
Generate a one sentence summary of this information that can be used to search for it
later, using vector similarity search on the sentence embedding of the summary:

{{ Content }}
"""

        self.factoid_keywords_prompt_template = \
"""
Generate keywords for this information that can be used later to do keyword search for it
later:

{{ Content }}
"""

    def send(self):
        if len(self.utterances) == 0 or self.utterances[-1].get_role() != "User":
            return
        
        content = self.utterances[-1].get_text()

        now_utc = datetime.now(pytz.utc)
        tz_local = get_localzone()
        now_local = now_utc.astimezone(tz_local)
            
        data = {
            "Content": content,
            "User": getpass.getuser(),
            "ClientPlatform": str(platform.platform()),
            "ClientTimezone": str(tz_local),
            "ClientUTCTime": str(now_utc),
            "ClientLocalTime": str(now_local),
        }

        # 
        # Factoid storage
        #

        prompt = pystache.render(self.factoid_prompt_template, data)
        
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}]

        factoid_handler = ChatCompletionHandler(start_handler=self.on_llm_response_start,
                                        chunk_handler=self.on_llm_response_chunk,
                                        done_handler=self.on_llm_response_done)

        self.pulse_busy = True
        self._t_busy = 0.0

        # Add Answer TextArea
        answer = self.gui.create_control("ChatMessageUI", role="Assistant", text='')
        self.add_child(answer)
        self.utterances.append(answer)

        model = 'gpt-4-1106-preview'
        # self.gui.session.llm_send_chat_request(model, messages, handlers=[factoid_handler])
        self.gui.session.llm_send_streaming_chat_request(model, messages, handlers=[factoid_handler])

        #
        # Named Entity Recognition (NER)
        #

        data["Content"] = content
        ner_prompt = pystache.render(self.factoid_ner_prompt_template, data)
        ner_messages = [{"role": "system", "content": ""}, {"role": "user", "content": ner_prompt}]
        ner_handler = ChatCompletionHandler(start_handler=self.on_ner_response_start,
                                        chunk_handler=self.on_ner_response_chunk,
                                        done_handler=self.on_ner_response_done)

        # Add NER TextArea
        ner = self.gui.create_control("ChatMessageUI", role="NER", text='')
        self.add_child(ner)
        self.current_ner_destination = ner
        # self.utterances.append(ner)

        self.gui.session.llm_send_streaming_chat_request(model, ner_messages, handlers=[ner_handler])

        #
        # Summary sentence for vector similarity search
        #

        data["Content"] = content
        vss_prompt = pystache.render(self.factoid_vss_summary_prompt_template, data)
        vss_messages = [{"role": "system", "content": ""}, {"role": "user", "content": vss_prompt}]
        vss_handler = ChatCompletionHandler(start_handler=self.on_vss_response_start,
                                        chunk_handler=self.on_vss_response_chunk,
                                        done_handler=self.on_vss_response_done)

        # Add VSS TextArea
        vss = self.gui.create_control("ChatMessageUI", role="Summary Sentence", text='')
        self.add_child(vss)
        self.current_vss_destination = vss

        self.gui.session.llm_send_streaming_chat_request(model, vss_messages, handlers=[vss_handler])

        #
        # Summary keywords for keyword search
        #

        data["Content"] = content
        kw_prompt = pystache.render(self.factoid_keywords_prompt_template, data)
        kw_messages = [{"role": "system", "content": ""}, {"role": "user", "content": kw_prompt}]
        kw_handler = ChatCompletionHandler(start_handler=self.on_keywords_response_start,
                                        chunk_handler=self.on_keywords_response_chunk,
                                        done_handler=self.on_keywords_response_done)

        # Add Keywords TextArea
        keywords = self.gui.create_control("ChatMessageUI", role="Summary Keywords", text='')
        self.add_child(keywords)
        self.current_kw_destination = keywords

        self.gui.session.llm_send_streaming_chat_request(model, kw_messages, handlers=[kw_handler])


    def on_ner_response_start(self) -> None:
        self.ner_response_text = ""


    def on_ner_response_chunk(self, chunk_text: Optional[str]) -> None:
        if chunk_text is not None:
            assert(self.current_ner_destination is not None)
            self.current_ner_destination.text_area.text_buffer.move_point_to_end()
            self.current_ner_destination.text_area.text_buffer.insert(chunk_text)
            self.current_ner_destination.text_area.set_needs_redraw()

            self.ner_response_text += chunk_text


    def on_ner_response_done(self) -> None:
        self.current_ner_destination = None


    def on_vss_response_start(self) -> None:
        self.vss_response_text = ""


    def on_vss_response_chunk(self, chunk_text: Optional[str]) -> None:
        if chunk_text is not None:
            assert(self.current_vss_destination is not None)
            self.current_vss_destination.text_area.text_buffer.move_point_to_end()
            self.current_vss_destination.text_area.text_buffer.insert(chunk_text)
            self.current_vss_destination.text_area.set_needs_redraw()

            self.vss_response_text += chunk_text


    def on_vss_response_done(self) -> None:
        self.current_vss_destination = None


    def on_keywords_response_start(self) -> None:
        self.keywords_response_text = ""


    def on_keywords_response_chunk(self, chunk_text: Optional[str]) -> None:
        if chunk_text is not None:
            assert(self.current_kw_destination is not None)
            self.current_kw_destination.text_area.text_buffer.move_point_to_end()
            self.current_kw_destination.text_area.text_buffer.insert(chunk_text)
            self.current_kw_destination .text_area.set_needs_redraw()

            self.keywords_response_text += chunk_text


    def on_keywords_response_done(self) -> None:
        self.keywords_response_text = None


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
            instance.add_child(child)
            if child_class_name == "ChatMessageUI":
                instance.utterances.append(child)

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
        handled = super().handle_event(event)

        if handled:
            return True
        else:
            return self.parent.handle_event(event)


    def on_update(self, dt):
        super().on_update(dt)
    

    def draw(self):
        super().draw()


GUI.register_control_type("LLMAgentChat", LLMAgentChat)