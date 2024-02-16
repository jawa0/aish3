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


TIME_UPDATE_INTERVAL_SECONDS = 5

class Agent:
    def __init__(self) -> None:
        self.memory = MemoryStore()
        self.memory.load('memory.json')

        self._event_stream = EventStream()
        self._task = None


    def start(self) -> None:
        event = {
            "version": 0.1,
            "type": "SessionStart",
            "user": getpass.getuser(),
            "client_platform": str(platform.platform()),
            **self._get_time_metadata()
        }
        self._event_stream.put(event)

        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._go())


    def stop(self) -> None:
        event = {
            "version": 0.1,
            "type": "SessionEnd",
            "user": getpass.getuser(),
            "client_platform": str(platform.platform()),
            **self._get_time_metadata()
        }
        self._event_stream.put(event)

        if self._task is not None:
            self._task.cancel()
            self._task = None

        
    def put_event(self, event: dict) -> None:
        self._event_stream.put(event)


    def memorize_text(self, text: str) -> uuid.UUID:
        mem_uid = self.memory.store(memory=Memory(text=text))
        event = {
            "version": 0.1,
            "type": "MemorizedText",
            "mem_uid": str(mem_uid),
            "text": text,
            "user": getpass.getuser(),
            "client_platform": str(platform.platform()),
            **self._get_time_metadata()
        }
        self._event_stream.put(event)
        return mem_uid


    def recall_text_by_similarity(self, text: str) -> [Tuple[float, "Memory"]]:
        results = self.memory.retrieve_by_similarity(text=text)
        for s, m in results:
            event = {
                "version": 0.1,
                "type": "RememberedText",
                "mem_uid": str(m.uid),
                "similarity": s,
                "summary": m.summary_sentence,
                "text": m.text,
                "user": getpass.getuser(),
                "client_platform": str(platform.platform()),
                **self._get_time_metadata()
            }
            self._event_stream.put(event)
        return results
    

    async def _go(self):
        while True:
            print('Agent._go() ...')

            event = {
                "version": 0.1,
                "type": "TimeUpdate",
                "user": getpass.getuser(),
                "client_platform": str(platform.platform()),
                **self._get_time_metadata()
            }
            self._event_stream.put(event)

            await asyncio.sleep(TIME_UPDATE_INTERVAL_SECONDS)


    def _get_time_metadata(self):
        now_utc = datetime.now(pytz.utc)
        tz_local = get_localzone()
        now_local = now_utc.astimezone(tz_local)

        time_details = {
            "client_timezone": str(tz_local),
            "client_utc_time": str(now_utc),
            "client_local_time": str(now_local),
        }
        return time_details
