class EventStream:
    def __init__(self):
        self._events = []

    
    def put(self, event: dict) -> None:
        print(f'EventStream.put({event})')
        self._events.append(event)