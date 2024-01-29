import asyncio
from datetime import datetime
from event_stream import EventStream
import getpass
from memory import MemoryStore
import platform
import pystache
import pytz
from tzlocal import get_localzone


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

            await asyncio.sleep(2)


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
