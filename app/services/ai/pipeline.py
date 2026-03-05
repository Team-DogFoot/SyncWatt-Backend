import logging
from google.adk.agents import SequentialAgent, ParallelAgent
from app.services.ai.factory import AgentFactory

logger = logging.getLogger(__name__)

def create_mvp_analysis_pipeline() -> SequentialAgent:
    """
    병렬 검증 로직이 포함된 SyncWatt MVP 분석 파이프라인을 생성합니다.
    
    구조:
    1. ParallelAgent (병렬 실행)
       - OCR 경로: VisionAgent -> OcrRefinerAgent (settlement_data)
       - Visual 경로: DirectVisionAgent (visual_data)
    2. VerifierAgent: 두 결과를 비교하여 최종 settlement_data 확정
    3. DataFetcherAgent: 시장/기상 데이터 조회 (market_data)
    4. DiagnosisAgent: 최종 손실 진단 (analysis_result)
    """
    logger.info("병렬 검증 MVP 분석 파이프라인 조립 시작")
    
    # 1. 병렬 실행 경로 레이어 정의
    ocr_path = SequentialAgent(
        name="ocr_path",
        sub_agents=[
            AgentFactory.get_vision_agent(),
            AgentFactory.get_ocr_refiner_agent()
        ]
    )
    
    visual_path = AgentFactory.get_visual_agent()
    
    parallel_layer = ParallelAgent(
        name="parallel_verification_layer",
        sub_agents=[ocr_path, visual_path]
    )
    
    # 2. 전체 순차 파이프라인 조립
    from app.services.ai.agents.code_verifier import CodeVerifierAgent
    
    pipeline = SequentialAgent(
        name="syncwatt_mvp_pipeline",
        sub_agents=[
            parallel_layer,
            CodeVerifierAgent(),
            AgentFactory.get_data_fetcher_agent(),
            AgentFactory.get_diagnosis_agent()
        ]
    )
    
    logger.info("병렬 검증 MVP 분석 파이프라인 조립 완료")
    return pipeline

# 서비스 전역에서 사용할 파이프라인 인스턴스
pipeline = create_mvp_analysis_pipeline()
analysis_pipeline = pipeline
