from blinker import signal
import logging

from openai import OpenAI, chat
import os
from queue import Queue
from typing import Callable, Dict, List, Optional

from audio_service import AudioService


class Session:
    def __init__(self):
        logging.debug("Client Session.__init__")

        self._user_command_channel = signal('channel_raw_user_command')

        print('BEFORE creating openai_client...')
        print(f'os.getenv("OPENAI_API_KEY"): {os.getenv("OPENAI_API_KEY")}')
        
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) 
                                    # organization=os.getenv("OPENAI_ORGANIZATION"))
                                    
        print('AFTER creating openai_client.')

        self._tasks = []
        
        self._audio = AudioService()
        self._channels = {}

        self.gui = None


    def start(self):
        logging.debug("Client Session.start")
        self._audio.start()

    
    def stop(self):
        logging.debug("Client Session.stop")
        self._audio.stop()


    def publish(self, channel_name, obj):
        if channel_name in self._channels:
            for q in self._channels[channel_name]:
                q.put(obj)


    def subscribe(self, channel_name: str) -> Queue:
        q = Queue()
        if channel_name not in self._channels:
            self._channels[channel_name] = []
        self._channels[channel_name].append(q)
        return q
