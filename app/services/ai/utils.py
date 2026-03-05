from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types

def create_text_event(author: str, text: str, state_delta: dict = None) -> Event:
    """
    ADK 규격에 맞는 텍스트 이벤트를 생성하는 헬퍼 함수입니다.
    선택적으로 세션 상태를 업데이트할 state_delta를 포함할 수 있습니다.
    """
    return Event(
        author=author,
        content=types.Content(parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}),
        partial=False
    )
