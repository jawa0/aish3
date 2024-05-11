import asyncio
import getpass
import json
import platform
import sys
import uuid
import weakref
from datetime import datetime
from typing import Dict, List, Tuple

import pystache
import pytz
from blinker import signal
from tzlocal import get_localzone

from agent_events import AgentEvents
from event_queue import EventQueue
from event_stream import EventStream
from llm import LLMRequest
from memory import Memory, MemoryStore
from prompt import PromptTemplate
from code_changes import HypotheticalScenario

TIME_UPDATE_INTERVAL_SECONDS = 0.2
MAX_PERCEPT_HISTORY_COUNT = 800

class Agent:
    def __init__(self, memory_filename="memory.json", percept_filename="agent_percepts.json", gui=None) -> None:
        self.memory = MemoryStore()

        self._percepts = EventStream()
        self._percepts.load(percept_filename)

        self._future_events = EventQueue()
        self._task = None
        self._gui = weakref.ref(gui) if gui else None

        signal('channel_raw_user_command').connect(self._log_raw_user_command)

        # @todo instead of connecting different functions, connect one on_command function
        # and route to the correct member function from there.
        
        signal('channel_command').connect(self._log_parsed_user_command)
        signal('channel_command').connect(self._on_cmd_show_logged_percepts)
        signal('channel_command').connect(self._on_cmd_memorize_text)
        signal('channel_command').connect(self._on_cmd_retrieve_memory)
        signal('channel_user_text_message').connect(self._on_user_text_message)

        self._memory_filename = memory_filename
        self.memory.load(self._memory_filename)
        self._ta_chat_answer: "TextArea" = None

        self._files = []
        self._hypotheticals: Dict[uuid.UUID, HypotheticalScenario] = {}


    def start(self) -> None:
        event = AgentEvents.create_event("SessionStart")
        self._percepts.put(event)

        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._go())


    def stop(self) -> None:
        event = AgentEvents.create_event("SessionEnd")
        self._percepts.put(event)

        if self._task is not None:
            self._task.cancel()
            self._task = None


    def put_event(self, event: dict) -> None:
        self._percepts.put(event)


    def memorize_text(self, text: str) -> uuid.UUID:
        print(f'*** Memorizing text: {text}')

        mem = Memory(text=text)
        mem_uid = self.memory.store(memory=mem)
        
        event = AgentEvents.create_event("MemorizedText", mem_uid=str(mem_uid), text=text)
        self._percepts.put(event)
        return mem_uid


    def recall_text_by_similarity(self, text: str) -> List[Tuple[float, "Memory"]]:
        results = self.memory.retrieve_by_similarity(text=text)
        for s, m in results:
            event = AgentEvents.create_event(
                "RememberedText",
                mem_uid=str(m.uid),
                similarity=float(s),  # float32 not JSON serializable
                summary=m.summary_sentence,
                text=m.text
            )
            self._percepts.put(event)
        return results


    def save_memories(self) -> None:
        self.memory.save(self._memory_filename)
        self._percepts.save("agent_percepts.json")


    async def _go(self):
        while True:
            # print('Agent._go() ...')

            # Stop sending TimeUpdate spam for now. Don't think it's necessary
            # since all events are timestamped.
            # event = AgentEvents.create_event("TimeUpdate")
            # self._percepts.put(event)

            # await asyncio.sleep(1.0 / 120)
            await asyncio.sleep(TIME_UPDATE_INTERVAL_SECONDS)


    def percept_history(self) -> List[dict]:
        return self._percepts.get_events()

    
    def _filtered_percepts(self) -> List[str]:
        filtered_result = ""
        print(f'*** len(percept_history): {len(self.percept_history())}')
        for e in self.percept_history()[-MAX_PERCEPT_HISTORY_COUNT:]:
            if e['type'] == "SessionStart":
                filtered_result += f"<event>\nSession started - client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} username: {e['user']}\n</event>\n"
            elif e['type'] == "SessionEnd":
                filtered_result += f"<event>\nSession ended - client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} username: {e['user']}\n</event>\n"
            elif e['type'] == "UserEnteredCommand":
                filtered_result += f"<event>\nUser sent you a text command - client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} username: {e['user']} user_text: {e['user_text']}\n</event>\n"
            elif e['type'] == "ParsedUserCommand":
                filtered_result += f"<event>\nYou decided that the user's text input matched one of your command functions - client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} username: {e['user']} command_text: {e['command_text']}\n</event>\n"
            elif e['type'] == "TextMessageFromUser":
                filtered_result += f"<event>\nUser sent you a text message - client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} username: {e['user']} user_text: {e['user_text']}\n</event>\n"
            elif e['type'] == "RememberedText":
                filtered_result += f"<event>\nYou recalled a text memory from your external memory store - memory_uid: {e['mem_uid']} vector similarity to query: {float(e['similarity'])} summary: {e['summary']}\n client_utc_time: {e['client_utc_time']}\n</event>\n"
            elif e['type'] == "MemorizedText":
                filtered_result += f"<event>\nYou memorized a text memory to your external memory store - memory_uid: {e['mem_uid']} contents_text: {e['text']}\nclient_utc_time: {e['client_utc_time']}\n</event>\n"
            elif e['type'] == "TextResponseFromAgentStart":
                filtered_result += f"<event>\nYou started a streaming text response to the user - username: {e['user']} client_utc_time: client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']}\n</event>\n"
            elif e['type'] == "TextResponseFromAgentDone":
                filtered_result += f"<event>\nYou finished streaming a text response to the user - username: {e['user']} client_utc_time: client_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} response_text: {e['response_text']}\n</event>\n"
            elif e['type'] == "OpenedFile":
                filtered_result += f"<event>\nYou opened a file - path: \"{e['path']}\"\nclient_utc_time: {e['client_utc_time']} client_timezone: {e['client_timezone']} client_local_time: {e['client_local_time']} client_platform: {e['client_platform']} username: {e['user']}\ncontents:\n\"\"\"\n{e['contents']}\n\"\"\"\n</event>\n"
            else:
                filtered_result += json.dumps(e, indent=2) + "\n"
        return filtered_result


    def _filter_chat_history_from_percepts(self) -> List[dict]:
        chat_history = []
        for e in self.percept_history():
            if e['type'] == "TextMessageFromUser":
                chat_history.append({'role': 'user', 'content': e['user_text']})
            elif e['type'] == "TextResponseFromAgentDone":
                chat_history.append({'role': 'assistant', 'content': e['response_text']})
        return chat_history


    def _log_raw_user_command(self, command_text: str) -> None:
        self.put_event(AgentEvents.create_event("UserEnteredCommand", user_text=command_text))


    def _log_parsed_user_command(self, command: dict) -> None:
        self.put_event(AgentEvents.create_event("ParsedUserCommand", command_text=command))


    def _on_cmd_show_logged_percepts(self, command_text: str) -> None:
        if command_text != "show_logged_percepts":
            return
        
        if not self._gui or not self._gui():   # Could be not set, or weakref could be gone
            return
        
        try:
            contents = self._filtered_percepts()
        except TypeError:
            contents = "Error serializing percept history to JSON"

        # Create a new TextArea to show the results
        gui = self._gui()
        vx, vy = gui.get_mouse_position()
        wx, wy = gui.view_to_world(vx, vy)
        ta: "TextArea" = gui.cmd_new_text_area(text=contents, wx=wx, wy=wy) 
        ta.set_size(580, 600)


    def _on_cmd_memorize_text(self, command_text: str) -> None:
        print(f'*** _on_cmd_memorize_text: {command_text}')
        if not command_text.startswith('memorize_text('):
            return
        
        text_to_memorize = self._extract_parameter(command_text)
        if text_to_memorize:
            self.memorize_text(text_to_memorize)


    def _on_cmd_retrieve_memory(self, command_text: str) -> None:
        print(f'*** _on_cmd_retrieve_memory: {command_text}')
        if not command_text.startswith('recall_memory('):
            return
        
        search_text = self._extract_parameter(command_text)
        if search_text:
            results = self.recall_text_by_similarity(search_text)

            contents = f"Recalled memories similar to '{search_text}':\n"
            for s, m in results:
                if s > 0:
                    contents += f"Similarity: {s}  Summary: {m.summary_sentence}\n"

            # Create a new TextArea to show the results
            gui = self._gui()
            vx, vy = gui.get_mouse_position()
            wx, wy = gui.view_to_world(vx, vy)
            ta: "TextArea" = gui.cmd_new_text_area(text=contents, wx=wx, wy=wy) 
            ta.set_size(1200, 200)

    
    def _on_user_text_message(self, text: str) -> None:
        print(f'*** _on_user_text_message: {text}')
        self.put_event(AgentEvents.create_event("TextMessageFromUser", user_text=text))

        # Does this text match any of our memories?
        # Create a new TextArea to show the results
        gui = self._gui()
        vx, vy = gui.get_mouse_position()
        wx, wy = gui.view_to_world(vx, vy)
        ta: "TextArea" = gui.cmd_new_text_area(text="", wx=wx, wy=wy) 
        ta.set_size(800, 600)

        recalled_results = self.recall_text_by_similarity(text)  # @note: writes percepts/event log
        # recalled_details = []
        for similarity, memory in recalled_results:
            if similarity > 0:
                ta.text_buffer.insert(f'{similarity:6.4f}:  {memory.summary_sentence}\n')

        # We want to memorize the user text, but not the full percept history, and
        # other context. So, memorize now, before filling in the prompt template.

        user_msg_memory_template = \
"""
The user sent you this message:
'''{{ Message }}'''

User metadata:

{{ UserInfo }}

Time metadata:

{{ TimeInfo }}
"""

        user_msg_memory_text = pystache.render(user_msg_memory_template,
            **{
                'Message': text,
                'UserInfo': json.dumps(AgentEvents.get_user_metadata()),
                'TimeInfo': json.dumps(AgentEvents.get_time_metadata())
            }
        )

        # Memorize what the user said
        self.memorize_text(text=user_msg_memory_text)

        # Now fill in the prompt template that we're going to send to an LLM to generate
        # a response to the user's message.

        sys_template = PromptTemplate(
"""
You are AISH, a conversational AI agent. You are interacting with a user. You
are implemented as a software system, of which LLMs are one part. You also have a memory
that is a separate subcomponent independent of LLMs.

""")
        try:
            percept_history_str = self._filtered_percepts()
        except TypeError as e:
            print(e)
            sys.exit(1)

        files_str = ""
        for f in self._files:
            # {'object_type': 'file', 'path': path_string, 'contents': contents}

            # Don't put in file contents, or we'll rapidly blow up our context.
            # files_str += f'File {f["path"]}:\nContents:\n\n{f["contents"]}\n\n'
            files_str += f'File: "{f["path"]}"\n\n'

        sys_prompt = sys_template.fill(**{'Percepts': percept_history_str, 'Files': files_str})

        user_template = PromptTemplate(
"""
User metadata:

{{ UserInfo }}

The user sent you this message:
'''{{ Message }}'''

Time metadata:

{{ TimeInfo }}

Respond to the user's message.
""")
        user_template.fill(
            **{
                'Message': text,
                'UserInfo': json.dumps(AgentEvents.get_user_metadata()),
                'TimeInfo': json.dumps(AgentEvents.get_time_metadata())
            }
        )

        user_messages = self._filter_chat_history_from_percepts()
        rq_chat = LLMRequest(prompt=user_template,
                             previous_messages=[{'role': 'system', 'content': sys_prompt}] + user_messages,
                             handlers=[("start", self._on_chat_response_start),
                                        ("next", self._on_chat_response_next),
                                        ("stop", self._on_chat_response_done),
                                        ("error", self._on_chat_response_error)])
        rq_chat.send_nowait()


    def _on_chat_response_start(self, llm_request: LLMRequest):
        event = {
            "version": 0.1,
            "type": "TextResponseFromAgentStart",
            **AgentEvents.get_user_metadata(),
            **AgentEvents.get_time_metadata()
        }
        self.put_event(event)

        # Create a new TextArea to show the results
        gui = self._gui()
        vx, vy = gui.get_mouse_position()
        wx, wy = gui.view_to_world(vx, vy)
        self._ta_chat_answer = gui.cmd_new_text_area(text="", wx=wx, wy=wy) 
        self._ta_chat_answer.set_size(600, 600)


    def _on_chat_response_next(self, llm_request: LLMRequest, chunk_text: str):
        if chunk_text is not None and len(chunk_text) > 0:
            self._ta_chat_answer.text_buffer.move_point_to_end()
            self._ta_chat_answer.text_buffer.insert(chunk_text)
            self._ta_chat_answer.set_needs_redraw()


    def _on_chat_response_error(self, llm_request: LLMRequest, error: str):
        if self._ta_chat_answer:
            self._ta_chat_answer.text_buffer.move_point_to_end()
            self._ta_chat_answer.text_buffer.insert(error)
            self._ta_chat_answer.set_needs_redraw()
            self._ta_chat_answer = None


    def _on_chat_response_done(self, llm_request: LLMRequest):
        event = {
            "version": 0.1,
            "type": "TextResponseFromAgentDone",
            "response_text": llm_request.response_text,
            **AgentEvents.get_user_metadata(),
            **AgentEvents.get_time_metadata()
        }
        self.put_event(event)

        response_memory_template = \
"""
You responded:
'''{{ Message }}'''

User metadata:

{{ UserInfo }}

Time metadata:

{{ TimeInfo }}
"""        
        memory_text = pystache.render(response_memory_template,
                                      {
                                          'Message': llm_request.response_text,
                                          'UserInfo': json.dumps(AgentEvents.get_user_metadata()),
                                          'TimeInfo': json.dumps(AgentEvents.get_time_metadata())
                                      })
                                      
        self.memorize_text(text=memory_text)
        self._ta_chat_answer = None


    # @todo if this works, then use it in gui.py command handlers as well...
    def _extract_parameter(self, command: str) -> str | None:
        prefix, suffix = command.split("(", 1)
        if suffix.endswith(")"):
            return suffix[:-1].strip()
        else:
            return None