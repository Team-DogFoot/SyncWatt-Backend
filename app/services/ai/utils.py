from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types

def create_text_event(author: str, text: str, state_delta: dict = None) -> Event:
    """Helper to create a standard text Event with optional state_delta."""
    return Event(
        author=author,
        content=types.Content(parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}),
        partial=False
    )
