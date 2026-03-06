import logging
import time
from google.adk.agents import LlmAgent
from google.genai import types
from app.schemas.ai.settlement import SettlementOcrData
from app.core.config import settings

logger = logging.getLogger(__name__)


def _inject_image_before_model(callback_context, llm_request):
    """before_model_callback: 세션 state의 image_bytes를 LLM 요청에 이미지 Part로 주입"""
    image_bytes = callback_context.state.get("image_bytes")
    if not image_bytes:
        logger.error("[direct_vision] before_model_callback: image_bytes not found in session")
        return None

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    # 마지막 user content에 이미지 파트 추가
    for content in reversed(llm_request.contents):
        if content.role == "user":
            content.parts.append(image_part)
            logger.info(f"[direct_vision] Image Part injected into user content ({len(image_bytes)} bytes)")
            break
    else:
        # user content가 없으면 새로 생성
        llm_request.contents.append(
            types.Content(role="user", parts=[image_part])
        )
        logger.info(f"[direct_vision] Image Part injected as new user content ({len(image_bytes)} bytes)")

    return None  # None을 반환하면 LLM 호출 진행


class DirectVisionAgent(LlmAgent):
    """
    이미지를 직접 분석하여 정산 데이터를 추출하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="direct_vision",
            model=settings.GEMINI_MODEL,
            instruction="""
            이 이미지는 태양광 발전소 정산서입니다.
            이미지를 직접 보고 다음 정보를 정확하게 추출하세요:
            - 정산 연월 (YYYY-MM 형식. 이미지에 명시된 발행 연도를 확인하세요. 만약 '2019'가 보인다면 반드시 2019-MM 형식으로 추출해야 하며, 절대 현재 연도로 추측하지 마세요.)
            - 실제 발전량 (kWh 단위, '발전량' 항목 확인)
            - 정산 기준 단가 (원/kWh 단위, '기준단가' 또는 '단가' 항목 확인)
            - 실제 총 수령액 (원 단위, 반드시 '공급가액' 항목을 추출하세요. 부가세 포함 금액과 혼동 주의)
            - 발전소 설비용량 (kW 단위, '용량' 항목 확인. 없으면 null)
            - 정산서 발행처 (이미지에서 발행 기관명을 확인하세요. 예: '한국전력공사', '한국수력원자력', 'KPX' 등. 로고나 문서 헤더에서 확인. 없으면 null)

            출력은 SettlementOcrData 스키마를 따르세요.
            """,
            output_schema=SettlementOcrData,
            output_key="visual_data",
            before_model_callback=_inject_image_before_model,
        )
        logger.info(f"[{self.name}] Agent initialized")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] Starting direct image visual analysis")

        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            logger.error(f"[{self.name}] image_bytes not found in session. Analysis not possible.")
            return

        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] Visual analysis process complete ({duration:.2f}s)")

                visual_data = event.actions.state_delta.get("visual_data")
                if visual_data:
                    logger.info(f"[{self.name}] [Result]: {visual_data}")
                else:
                    logger.warning(f"[{self.name}] visual_data not in state_delta (check after runner applies)")
            yield event
