import asyncio
import getpass
import json
import platform
import uuid
import weakref
from datetime import datetime
from typing import List, Tuple

from blinker import signal
import pytz
from tzlocal import get_localzone

from agent_events import AgentEvents
from event_queue import EventQueue
from event_stream import EventStream
from memory import Memory, MemoryStore


TIME_UPDATE_INTERVAL_SECONDS = 5


class Agent:
    def __init__(self, memory_filename="memory.json", gui=None) -> None:
        self.memory = MemoryStore()

        self._percepts = EventStream()
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

        self._memory_filename = memory_filename
        self.memory.load(self._memory_filename)


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
                similarity=s,
                summary=m.summary_sentence,
                text=m.text
            )
            self._percepts.put(event)
        return results


    def save_memories(self) -> None:
        self.memory.save(self._memory_filename)


    async def _go(self):
        while True:
            # print('Agent._go() ...')

            event = AgentEvents.create_event("TimeUpdate")
            self._percepts.put(event)

            # await asyncio.sleep(1.0 / 120)
            await asyncio.sleep(TIME_UPDATE_INTERVAL_SECONDS)


    def percept_history(self) -> List[dict]:
        return self._percepts.get_events()

    
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
            contents = json.dumps(self.percept_history(), indent=2)
        except json.JSONDecodeError:
            contents = "Error serializing percept history to JSON"

        # Create a new TextArea to show the results
        gui = self._gui()
        vx, vy = gui.get_mouse_position()
        wx, wy = gui.view_to_world(vx, vy)
        ta = gui.cmd_new_text_area(text=contents, wx=wx, wy=wy) 
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
            ta = gui.cmd_new_text_area(text=contents, wx=wx, wy=wy) 
            ta.set_size(1200, 200)


    # @todo if this works, then use it in gui.py command handlers as well...
    def _extract_parameter(self, command: str) -> str | None:
        prefix, suffix = command.split("(", 1)
        if suffix.endswith(")"):
            return suffix[:-1].strip()
        else:
            return None