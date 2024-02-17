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


import asyncio
from datetime import datetime
import sdl2
import json
import logging
import matplotlib
import os
import openai
from typing import Optional

from agent import Agent
from gui import GUI, GUIContainer
from label import Label
from textarea import TextArea
from gui_layout import ColumnLayout
from session import ChatCompletionHandler
from llm import LLMRequest
from llm_chat_container import LLMChatContainer
from memory import Memory
from prompt import LiteralPrompt, PromptTemplate

import getpass
import platform
import pytz
from tzlocal import get_localzone

from embeddings import embed


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


        self.notification_container = None

        self.agent = Agent()
        self.agent.start()

        self.agent_system_prompt = PromptTemplate(
"""
You are a conversational AI agent and assistant named "AISH".
""")
        
        self.agent_passhtrough_prompt = PromptTemplate(
"""
A user has sent you this message. Please respond. 

User message:

{{Content}}

Contextual information and metadata:

User: {{User}}
Client Platform: {{ClientPlatform}}
Client Timezone: {{ClientTimezone}}
Client UTC Time: {{ClientUTCTime}}
Client Local Time: {{ClientLocalTime}}
""")

        self.detect_info_to_store_template = PromptTemplate(
"""
You are a conversational AI agent. The following text is a message from a user to you.
Considering the content of the message, do you think that the user is teaching you some
information that the user wants you to remember? If so, then respond with exactly "is_info_chunk".
If not, or if you are unsure, respond with "unknown". Respond only with one of these two strings.
Do not emit any other text or punctuation.

Message:

{{ Content }}
""")


        self.extract_info_template = PromptTemplate(
"""
You are a conversational AI agent. The following text is a message from a user to you. Your job is
to return a string containing only the information that the user wants you to store, without any
preamble or postamble telling you to store the information. Return a string containing only the 
information. Do not emit any other text or punctuation.

Here are some examples:

"fact: water is wet" -> "water is wet"
"store: atoms are made of electrons, protons, and neutrons" -> "atoms are made of electrons, protons, and neutrons"
"Ottawa is the capital of Canada" -> "Ottawa is the capital of Canada"

Message:

{{ Content }}
""")

        self.factoid_keywords_prompt_template = PromptTemplate(
"""
You are a conversational AI agent. The following text is a message from a user to you.
Considering the content of the message, generate keywords for its content that can be used later 
to retrieve this message, using keyword search on the keywords. Return a JSON array of keyword
strings.

Example output:

{ "keywords": ["keyword 1", "keyword 2", "keyword 3", ... ] }

Message:

{{ Content }}
""")

        self.factoid_vss_summary_prompt_template = PromptTemplate(
"""
You are a conversational AI agent. The following text is a message from a user to you.
Considering the content of the message, generate a sentence that paraphrases and summarizes the 
message. The goalis to generate an embedding for this summary sentence that can later be used with vector similarity
search to retrieve the message. Include details that make this message different from other
messages. It should read like an item from a table of contents. If there is a key point to the 
message, make sure the summary includes that key point. Respond with a single sentence. 
Do not emit any other text or punctuation. Do not include text like "Summary:"

Message:

{{ Content }}
""")

        self.search_template = PromptTemplate(
"""
You are a conversational AI agent. The following text is a message from a user to you. Carefully examine
the message. If it is a request to search or recall or retrieve memories from your memory store, then generate a JSON
 function call using the tools that have been supplied to you. Return a JSON function call.

If the user message is asking you for similarity based on a string, phrase, or sentence, then do not interpret the 
contents of that string. Instead, pass the search string to the appropriate function in your tools.

Message:

{{ Content }}
""")

        self.is_function_call_template = PromptTemplate(
"""
You are a conversational AI agent. The following text is a message from a user to you. Carefully examine
the message. You have been provided with a list of tools (functions) that you can generate calls for, in JSON.
If the user's message is asking you to either 1) store or memorize textual information, or 2) search or recall or 
retrieve memories from your memory store, then generate a JSON function call using the tools that have been supplied
to you. Return a JSON function call.

In case (2), if the user message is asking you for similarity based on a string, phrase, or sentence, then do not 
interpret the contents of that string. Instead, pass the search string to the appropriate function in your tools.

Finally, if none of the tools or function you know how to use are appropriate to the user message, then simply 
return the JSON string "unknown".

Message:

{{ Content }}
""")

    def push_notification(self, notification: "GUIControl") -> None:
        if not self.notification_container:
            self._create_notification_container()
        self.notification_container.add_child(notification)

    
    def _create_notification_container(self) -> None:
        x_local = self.bounding_rect.w
        y_local = -self._inset[1]
        x, y = self.gui.local_to_local(self, self.parent, x_local, y_local)
        self.notification_container = GUIContainer(gui=self.gui, 
                                                   x=x, y=y, 
                                                   inset=(2, 2), 
                                                   name="Agent Notifcation Container", 
                                                   can_focus=False,
                                                   draggable=False,
                                                   saveable=False)
        self.notification_container.set_size(100, 20)
        self.notification_container.draw_bounds = False
        self.notification_container.set_layout(ColumnLayout())
        self.parent.add_child(self.notification_container)



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
        # Detect whether user is telling agent to:
        # * remember / store some information
        # * recall / retrieve some information
        # * none of the above
        #

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "store_info_chunk",
                    "description": "Store an info chunk to memory store.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text_info": {
                                "type": "string"
                            }   
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "retrieve_memories_by_keywords",
                    "description": "Retrieve stored memories by keywords.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }   
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "retrieve_memories_by_similarity",
                    "description": "Retrieve stored memories by similarity to the given string. Uses vector similarity search on an embedding of the search string.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_string": {
                                "type": "string"
                            }
                        }   
                    }
                }
            }
        ]

    
        def on_fncall_check_done(llm_request: LLMRequest):
            print(f'** CHECK FUNCALL ?\n"{llm_request.response_text}"')

            got_json = True
            s = llm_request.response_text.replace('```json', '').replace('```', '').strip()
            try:
                json_call = json.loads(s)
            except json.decoder.JSONDecodeError:
                print(f"** NOT JSON: {s}")
                got_json = False
            
            if not got_json or type(json_call) is not dict:
                print(f"** NOT FNCALL: {s}")

                #
                # Just send user message to the agent...
                #

                # @hack DRY
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

                self.agent_system_prompt.fill(**data)
                self.agent_passhtrough_prompt.fill(**data)

                prev_messages = [{"role": "system", 
                                  "content": self.agent_system_prompt.get_prompt_text()},
                ]


                def on_passthrough_response_start(llm_request: LLMRequest):
                    # Add response TextArea
                    cmui_answer = self.gui.create_control("ChatMessageUI", role="Answer", text='')
                    self.add_child(cmui_answer)
                    self.utterances.append(cmui_answer)


                def on_passthrough_response_next(llm_request: LLMRequest, chunk_text: str):
                    if chunk_text is not None and len(chunk_text) > 0:
                        ta_answer = self.utterances[-1].text_area
                        ta_answer.text_buffer.move_point_to_end()
                        ta_answer.text_buffer.insert(chunk_text)
                        ta_answer.set_needs_redraw()


                def on_passthrough_response_done(llm_request: LLMRequest):
                    event = {
                        "version": 0.1,
                        "type": "AgentResponseText",
                        "user": getpass.getuser(),
                        "client_platform": str(platform.platform()),
                        "message_text": llm_request.response_text,
                        **self.agent._get_time_metadata()
                    }
                    self.agent.put_event(event)


                llm_request = LLMRequest(session=self.gui.session,
                                         prompt=self.agent_passhtrough_prompt,
                                         previous_messages=prev_messages,
                                         handlers=[("start", on_passthrough_response_start),
                                                   ("next", on_passthrough_response_next),
                                                    ("stop", on_passthrough_response_done)])
                llm_request.send_nowait()

                event = {
                    "version": 0.1,
                    "type": "UserTextMessage",
                    "user": getpass.getuser(),
                    "client_platform": str(platform.platform()),
                    "message_text": content,
                    **self.agent._get_time_metadata()
                }
                self.agent.put_event(event)

            else:
                print(f'** JSON:\n{json_call}')

                # @todo move things like this to a sanitize utility
                # @bug OpenAI? Sometimes returned JSON does not include "tool_uses" list
                if "tool_uses" in json_call:
                    tu = json_call["tool_uses"][0]
                else:
                    tu = json_call

                if "recipient_name" in tu:
                    function_name = tu["recipient_name"]
                elif "function" in tu:
                    function_name = tu["function"]

                print(f" CALL {function_name} with {tu['parameters']}")

                if function_name == "functions.store_info_chunk":
                    mem_text = tu["parameters"]["text_info"]

                    event = {
                        "version": 0.1,
                        "type": "UserMemorizeRequest",
                        "text": mem_text,
                        "user": getpass.getuser(),
                        "client_platform": str(platform.platform()),
                        **self.agent._get_time_metadata()
                    }
                    self.agent.put_event(event)

                    # mem_uid = self.agent.memory.store(memory=Memory(text=mem_text))
                    mem_uid = self.agent.memorize_text(mem_text)
                    data = {"Content": mem_text}

                    # Add response TextArea
                    cmui_answer = self.gui.create_control("ChatMessageUI", role="Answer", text='')
                    self.add_child(cmui_answer)
                    self.utterances.append(cmui_answer)
                    cmui_answer.text_area.set_text("Stored info chunk with uid: " + str(mem_uid))

                    #
                    # Get keywords
                    #

                    self.factoid_keywords_prompt_template.fill(**data)

                    rq_keywords = LLMRequest(session=self.gui.session,
                                                prompt=self.factoid_keywords_prompt_template,
                                                handlers=[("stop", on_keywords_response_done)],
                                                respond_with_json=True,
                                                custom_data={"mem_uid": mem_uid})
                    
                    print('** SEND KEYWORDS REQUEST')
                    task_keyword = rq_keywords.send_nowait()

                    #
                    # Get summary sentence for embedding
                    #

                    self.factoid_vss_summary_prompt_template.fill(**data)
                    rq_vss = LLMRequest(session=self.gui.session,
                                            prompt=self.factoid_vss_summary_prompt_template,
                                            handlers=[("stop", on_vss_response_done)],
                                            custom_data={"mem_uid": mem_uid})
                    
                    print('** SEND VSS REQUEST')
                    task_vss = rq_vss.send_nowait()

                    print('** WAITING FOR KEYWORDS AND VSS')
                    # tg = asyncio.TaskGroup([task_keyword, task_vss])
                    # await asyncio.gather(task_keyword, task_vss)
                    # print('** DONE')

                elif function_name == "functions.retrieve_memories_by_keywords":
                    pass
                elif function_name == "functions.retrieve_memories_by_similarity":
                    query_string = tu["parameters"]["search_string"]

                    event = {
                        "version": 0.1,
                        "type": "UserRecallRequest",
                        "query": query_string,
                        "user": getpass.getuser(),
                        "client_platform": str(platform.platform()),
                        **self.agent._get_time_metadata()
                    }
                    self.agent.put_event(event)

                    # results = self.agent.memory.retrieve_by_similarity(text=query_string)
                    results = self.agent.recall_text_by_similarity(text=query_string)
                    if len(results) == 0:
                        text_result = "No memories matched above cutoff similarity threshold."
                    else:
                        text_result = ""
                        for similiarity, mem in results:
                            print(f'** SIMILARITY: {similiarity:0.3f}')
                            print(f'** MEMORY: {mem.summary_sentence}')
                            text_result += f"{similiarity:0.3f}: {mem.summary_sentence}\n"

                    # Add response TextArea
                    cmui_answer = self.gui.create_control("ChatMessageUI", role="Answer", text='')
                    self.add_child(cmui_answer)
                    self.utterances.append(cmui_answer)
                    cmui_answer.text_area.set_text(text_result)
        

        self.is_function_call_template.fill(**data)
        rq_is_fncall = LLMRequest(session=self.gui.session, 
                                 prompt=self.is_function_call_template,
                                 tools=tools,
                                 tool_choice="auto",
                                 handlers=[("stop", on_fncall_check_done)])
        rq_is_fncall.send_nowait()


        def on_keywords_response_done(llm_request: LLMRequest):
            print(f'** INFO CHUNK KEYWORDS (str): {llm_request.response_text}')
            kw_json = json.loads(llm_request.response_text)
            print(f'** INFO CHUNK KEYWORDS (JSON): {kw_json}')
            keywords = kw_json["keywords"]

            mem_uid = llm_request.custom_data["mem_uid"]
            assert(mem_uid is not None)
            mem = self.agent.memory.retrieve_by_uid(mem_uid)
            print(f'** UPDATING KEYWORDS for Memory {mem_uid}')
            mem.keywords = keywords


        
        def on_vss_response_done(llm_request: LLMRequest):
            print(f'** INFO CHUNK SUMMARY: {llm_request.response_text}')

            mem_uid = llm_request.custom_data["mem_uid"]
            assert(mem_uid is not None)
            mem = self.agent.memory.retrieve_by_uid(mem_uid)
            print(f'** UPDATING SUMMARY for Memory {mem_uid}')
            
            mem.summary_sentence = llm_request.response_text
            mem.summary_embedding = embed(mem.summary_sentence)[0]


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
            # We're going to handle save to save our agent's memories, but then pass the
            # event on to our parent so that it gets processed as though we hadn't hooked
            # it.
            if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_s and \
                (event.key.keysym.mod & sdl2.KMOD_GUI):

                self.agent.memory.save("memory.json")
                return False
            
            # Handle load
            if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_l \
                and (event.key.keysym.mod & sdl2.KMOD_GUI):

                self.agent.memory.load("memory.json")
                return False

            return self.parent.handle_event(event)


    def _on_quit(self):
        print('LLMAgentChat: Quit.')
        self.agent.stop()


    def on_update(self, dt):
        super().on_update(dt)
    

    def draw(self):
        super().draw()


GUI.register_control_type("LLMAgentChat", LLMAgentChat)