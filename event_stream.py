from typing import List

class EventStream:
    def __init__(self):
        self._events = []


    def put(self, event: dict) -> None:
        print(f'EventStream.put({event})')
        self._events.append(event)


    def get_events(self) -> List[dict]:
        return self._events
    
