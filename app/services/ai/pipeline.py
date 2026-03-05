import logging
from google.adk.agents import SequentialAgent
from app.services.ai.factory import AgentFactory

logger = logging.getLogger(__name__)

def create_mvp_analysis_pipeline() -> SequentialAgent:
    """
    SyncWatt MVP의 핵심 로직인 '정산서 분석 및 손실 진단' 파이프라인을 생성합니다.
    Agent Factory를 사용하여 선언적으로 에이전트들을 조립합니다.
    
    흐름:
    1. VisionAgent: 이미지에서 텍스트 추출 (raw_text)
    2. OcrRefinerAgent: 텍스트에서 정산 데이터 추출 (settlement_data)
    3. DataFetcherAgent: 해당 월의 기상/시장 데이터 조회 (market_data)
    4. DiagnosisAgent: 최종 손실액 계산 및 진단 (analysis_result)
    """
    logger.info("MVP 분석 파이프라인 조립 시작")
    
    pipeline = SequentialAgent(
        name="syncwatt_mvp_pipeline",
        sub_agents=[
            AgentFactory.get_vision_agent(),
            AgentFactory.get_ocr_refiner_agent(),
            AgentFactory.get_data_fetcher_agent(),
            AgentFactory.get_diagnosis_agent()
        ]
    )
    
    logger.info("MVP 분석 파이프라인 조립 완료")
    return pipeline

# 서비스 전역에서 사용할 파이프라인 인스턴스
pipeline = create_mvp_analysis_pipeline()
analysis_pipeline = pipeline
