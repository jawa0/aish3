import json
from typing import List

class EventStream:
    def __init__(self):
        self._events = []


    def put(self, event: dict) -> None:
        print(f'EventStream.put({event})')
        self._events.append(event)


    def get_events(self) -> List[dict]:
        return self._events


    def save(self, filename: str):
        with open(filename, "w") as f:
            json.dump(self._events, f, indent=2)


    def load(self, filename: str):
        try:
            with open(filename, "r") as f:
                self._events = json.load(f)
        except FileNotFoundError:
            self._events = []
