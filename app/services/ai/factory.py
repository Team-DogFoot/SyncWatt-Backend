import logging
from typing import Any
from app.services.ai.agents.ocr_agent import OcrRefinerAgent
from app.services.ai.agents.data_agent import DataFetcherAgent
from app.services.ai.agents.diagnosis_agent import DiagnosisAgent, DiagnosisCalculatorAgent
from app.services.ai.agents.visual_agent import DirectVisionAgent
from app.services.ai.agents.vision_agent import VisionAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Google ADK 패턴에 따라 에이전트를 관리하는 팩토리 클래스입니다.
    싱글톤 패턴을 적용하여 에이전트 인스턴스를 캐싱하고 재사용합니다.
    """
    _instances: dict[str, Any] = {}

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
        return cls._get_cached_instance(VisionAgent)

    @classmethod
    def get_ocr_refiner_agent(cls) -> OcrRefinerAgent:
        return cls._get_cached_instance(OcrRefinerAgent)

    @classmethod
    def get_visual_agent(cls) -> DirectVisionAgent:
        return cls._get_cached_instance(DirectVisionAgent)

    @classmethod
    def get_data_fetcher_agent(cls) -> DataFetcherAgent:
        return cls._get_cached_instance(DataFetcherAgent)

    @classmethod
    def get_diagnosis_calculator_agent(cls) -> DiagnosisCalculatorAgent:
        return cls._get_cached_instance(DiagnosisCalculatorAgent)

    @classmethod
    def get_diagnosis_agent(cls) -> DiagnosisAgent:
        return cls._get_cached_instance(DiagnosisAgent)
