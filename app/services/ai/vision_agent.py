from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.cloud import vision
from google.genai import types
import asyncio

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="vision_ocr", description="Extracts text from image bytes using Google Cloud Vision")
        # Use a private attribute (starting with underscore) to avoid Pydantic field validation
        self._client = vision.ImageAnnotatorClient()

    async def _run_async_impl(self, ctx):
        # Image bytes are expected to be in the session state
        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            yield Event(
                author=self.name, 
                content=types.Content(parts=[types.Part(text="No image bytes found in session state.")])
            )
            return

        image = vision.Image(content=image_bytes)
        # Run synchronous GCP call in a thread pool to maintain async integrity
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._client.text_detection, image)
        
        texts = response.text_annotations
        extracted_text = texts[0].description if texts else ""
        
        # Save to state via EventActions for the next agent
        yield Event(
            author=self.name, 
            content=types.Content(parts=[types.Part(text=f"Extracted {len(extracted_text)} characters.")]),
            actions=EventActions(state_delta={"raw_text": extracted_text})
        )
        # Also update context session state for internal use if needed
        ctx.session.state["raw_text"] = extracted_text
