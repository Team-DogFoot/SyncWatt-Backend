import logging
from typing import Dict, Any
from app.services.ai.agents.ocr_agent import OcrRefinerAgent
from app.services.ai.agents.data_agent import DataFetcherAgent
from app.services.ai.agents.diagnosis_agent import DiagnosisAgent
from app.services.ai.agents.visual_agent import DirectVisionAgent
from app.services.ai.agents.vision_agent import VisionAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Google ADK 패턴에 따라 에이전트를 관리하는 팩토리 클래스입니다.
    싱글톤 패턴을 적용하여 에이전트 인스턴스를 캐싱하고 재사용합니다.
    """
    _instances: Dict[str, Any] = {}

    @classmethod
    def _get_cached_instance(cls, agent_class):
        """인스턴스가 없으면 생성하고, 있으면 캐시된 인스턴스를 반환합니다."""
        class_name = agent_class.__name__
        if class_name not in cls._instances:
            logger.info(f"[AgentFactory] 새로운 {class_name} 인스턴스를 생성합니다.")
            cls._instances[class_name] = agent_class()
        return cls._instances[class_name]

    @classmethod
    def get_vision_agent(cls) -> VisionAgent:
        """기본 Google Cloud Vision OCR 에이전트를 반환합니다."""
        return cls._get_cached_instance(VisionAgent)

    @classmethod
    def get_ocr_refiner_agent(cls) -> OcrRefinerAgent:
        """OCR 텍스트를 정산 데이터로 정제하는 에이전트를 반환합니다."""
        return cls._get_cached_instance(OcrRefinerAgent)

    @classmethod
    def get_visual_agent(cls) -> DirectVisionAgent:
        """이미지를 직접 분석하는 시각 에이전트를 반환합니다."""
        return cls._get_cached_instance(DirectVisionAgent)

    @classmethod
    def get_data_fetcher_agent(cls) -> DataFetcherAgent:
        """외부 기상/시장 데이터를 조회하는 에이전트를 반환합니다."""
        return cls._get_cached_instance(DataFetcherAgent)

    @classmethod
    def get_diagnosis_agent(cls) -> DiagnosisAgent:
        """수익 손실을 최종 진단하는 에이전트를 반환합니다."""
        return cls._get_cached_instance(DiagnosisAgent)
