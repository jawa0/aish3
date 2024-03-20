import heapq
from datetime import datetime


class EventQueue:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        """Add an event to the priority queue."""
        heapq.heappush(self.events, (event['time'], event))

    def get_past_events(self, current_time):
        """Get all events whose time has already passed."""
        past_events = []
        while self.events and self.events[0][0] < current_time:
            past_events.append(heapq.heappop(self.events)[1])
        return past_events

    def get_next_event(self):
        """Get the next current or future event."""
        return self.events[0][1] if self.events else None

# Example usage
event_queue = EventQueue()
event_queue.add_event({'name': 'Event 1', 'time': datetime(2024, 3, 20, 15, 0)})
event_queue.add_event({'name': 'Event 2', 'time': datetime(2024, 3, 21, 18, 30)})
event_queue.add_event({'name': 'Event 3', 'time': datetime(2024, 3, 22, 12, 45)})

current_time = datetime.utcnow()

# Get all past events
past_events = event_queue.get_past_events(current_time)
print("Past events:", past_events)

# Get the next current or future event
next_event = event_queue.get_next_event()
print("Next event:", next_event)
