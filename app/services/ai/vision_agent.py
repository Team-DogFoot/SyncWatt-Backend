from google.adk.agents import BaseAgent
from google.cloud import vision
import asyncio
from app.core.gcp import get_vision_client
from app.services.ai.utils import create_text_event

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="vision_ocr", description="Extracts text from image bytes using Google Cloud Vision")

    async def _run_async_impl(self, ctx):
        # Image bytes are expected to be in the session state
        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            yield create_text_event(self.name, "No image bytes found in session state.")
            return

        image = vision.Image(content=image_bytes)
        # Use singleton client
        client = get_vision_client()
        
        # Run synchronous GCP call in a thread pool to maintain async integrity
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, client.text_detection, image)
        
        texts = response.text_annotations
        extracted_text = texts[0].description if texts else ""
        
        # Rely on EventActions for state propagation as per ADK architecture
        yield create_text_event(
            self.name, 
            f"Extracted {len(extracted_text)} characters.",
            state_delta={"raw_text": extracted_text}
        )
