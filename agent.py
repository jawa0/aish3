from agent_events import AgentEvents
import asyncio
from datetime import datetime
from event_stream import EventStream
import getpass
from memory import Memory, MemoryStore
import platform
import pytz
from typing import Tuple
from tzlocal import get_localzone
import uuid
from event_queue import EventQueue


TIME_UPDATE_INTERVAL_SECONDS = 5


class Agent:
    def __init__(self) -> None:
        self.memory = MemoryStore()
        self.memory.load('memory.json')

        self._percepts = EventStream()
        self._future_events = EventQueue()
        self._task = None


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
        mem_uid = self.memory.store(memory=Memory(text=text))
        event = AgentEvents.create_event("MemorizedText", mem_uid=str(mem_uid), text=text)
        self._percepts.put(event)
        return mem_uid


    def recall_text_by_similarity(self, text: str) -> [Tuple[float, "Memory"]]:
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


    async def _go(self):
        while True:
            # print('Agent._go() ...')

            event = AgentEvents.create_event("TimeUpdate")
            self._percepts.put(event)

            # await asyncio.sleep(1.0 / 120)
            await asyncio.sleep(TIME_UPDATE_INTERVAL_SECONDS)
