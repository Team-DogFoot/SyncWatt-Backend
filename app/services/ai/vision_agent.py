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
        response = await asyncio.to_thread(client.text_detection, image=image)
        
        texts = response.text_annotations
        extracted_text = texts[0].description if texts else ""
        
        # 텍스트 자체를 content로 내보내어 다음 Agent가 자연스럽게 받도록 함
        # 동시에 다른 Agent가 상태에서 조회할 수 있게 state_delta도 유지
        yield create_text_event(
            self.name, 
            extracted_text,
            state_delta={"raw_text": extracted_text}
        )
