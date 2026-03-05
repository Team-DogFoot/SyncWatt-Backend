import logging
from google.adk.agents import BaseAgent
from google.cloud import vision
import asyncio
from app.core.gcp import get_vision_client
from app.services.ai.utils import create_text_event

logger = logging.getLogger(__name__)

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="vision_ocr", description="Extracts text from image bytes using Google Cloud Vision")

    async def _run_async_impl(self, ctx):
        import time
        start_time = time.perf_counter()
        
        # Image bytes are expected to be in the session state
        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            logger.error(f"[{self.name}] Image bytes missing in session state")
            yield create_text_event(self.name, "No image bytes found in session state.")
            return

        logger.info(f"[{self.name}] Starting OCR detection (image size: {len(image_bytes)} bytes)")
        
        try:
            image = vision.Image(content=image_bytes)
            client = get_vision_client()
            
            # Run synchronous GCP call in a thread pool
            response = await asyncio.to_thread(client.text_detection, image=image)
            
            texts = response.text_annotations
            extracted_text = texts[0].description if texts else ""
            
            duration = time.perf_counter() - start_time
            logger.info(f"[{self.name}] OCR completed in {duration:.2f}s (extracted: {len(extracted_text)} chars)")
            
            if not extracted_text:
                logger.warning(f"[{self.name}] No text detected in the provided image")

            yield create_text_event(
                self.name, 
                extracted_text,
                state_delta={"raw_text": extracted_text}
            )
        except Exception as e:
            logger.error(f"[{self.name}] Error during vision detection: {str(e)}", exc_info=True)
            # 다음 Agent의 KeyError를 방지하기 위해 빈 텍스트라도 상태에 저장
            yield create_text_event(
                self.name, 
                f"Error: {str(e)}",
                state_delta={"raw_text": ""}
            )
