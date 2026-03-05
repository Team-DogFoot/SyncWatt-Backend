from google.adk.agents import BaseAgent
from google.adk.types import Event
from google.cloud import vision
import asyncio

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="vision_ocr", description="Extracts text from image bytes using Google Cloud Vision")
        # Note: In a real environment, you might need to handle client initialization differently
        # (e.g., passing credentials or using a singleton).
        self.client = vision.ImageAnnotatorClient()

    async def run_async_impl(self, ctx):
        # Image bytes are expected to be in the session state
        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            yield Event(author=self.name, content="No image bytes found in session state.")
            return

        image = vision.Image(content=image_bytes)
        # Run synchronous GCP call in a thread pool to maintain async integrity
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.client.text_detection, image)
        
        texts = response.text_annotations
        extracted_text = texts[0].description if texts else ""
        
        # Save to state for next agent
        ctx.session.state["raw_text"] = extracted_text
        
        yield Event(author=self.name, content=f"Extracted {len(extracted_text)} characters.")
