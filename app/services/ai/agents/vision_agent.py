import logging
import asyncio
import time
from google.adk.agents import BaseAgent
from google.cloud import vision
from app.core.gcp import get_vision_client
from app.services.ai.utils import create_text_event

logger = logging.getLogger(__name__)

class VisionAgent(BaseAgent):
    """
    Google Cloud Vision API를 사용하여 이미지에서 텍스트를 추출하는 기본 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="vision_ocr", 
            description="이미지 바이트 데이터에서 텍스트를 추출합니다."
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 이미지 텍스트 추출 시작")
        
        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            logger.error(f"[{self.name}] 세션에 이미지 데이터가 없습니다.")
            yield create_text_event(self.name, "분석할 이미지 데이터가 세션에 존재하지 않습니다.")
            return

        try:
            client = get_vision_client()
            image = vision.Image(content=image_bytes)
            
            response = await asyncio.to_thread(client.text_detection, image)
            
            texts = response.text_annotations
            extracted_text = texts[0].description if texts else ""
            
            duration = time.perf_counter() - start_t
            logger.info(f"[{self.name}] 텍스트 추출 완료 (길이: {len(extracted_text)}, 소요시간: {duration:.2f}초)")
            
            yield create_text_event(
                self.name, 
                f"이미지에서 {len(extracted_text)}자의 텍스트를 추출했습니다.",
                state_delta={"raw_text": extracted_text}
            )
        except Exception as e:
            logger.error(f"[{self.name}] OCR 처리 중 오류 발생: {str(e)}", exc_info=True)
            yield create_text_event(self.name, f"이미지 분석 중 오류가 발생했습니다: {str(e)}")
