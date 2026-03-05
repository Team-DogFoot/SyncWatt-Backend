from google.adk.agents import SequentialAgent, LlmAgent
from app.services.ai.vision_agent import VisionAgent
from app.services.ai.data_agent import DataFetcherAgent
from app.schemas.ai.analysis import ImageAnalysisResult
from app.schemas.ai.settlement import SettlementOcrData
from app.schemas.ai.diagnosis import DiagnosisResult
from app.core.config import settings

def create_settlement_pipeline():
    vision_agent = VisionAgent()
    
    ocr_refiner = LlmAgent(
        name="ocr_refiner",
        model=settings.GEMINI_MODEL,
        instruction="입력받은 OCR 텍스트에서 정산 정보를 추출하여 정형화된 데이터로 변환하세요. 필요시 세션의 {raw_text}를 참조할 수 있습니다.",
        output_schema=SettlementOcrData,
        output_key="settlement_data"
    )

    data_fetcher = DataFetcherAgent()

    return SequentialAgent(
        name="settlement_processing_pipeline",
        sub_agents=[vision_agent, ocr_refiner, data_fetcher]
    )

def create_analysis_pipeline():
    vision_agent = VisionAgent()
    
    ocr_refiner = LlmAgent(
        name="ocr_refiner",
        model=settings.GEMINI_MODEL,
        instruction="입력받은 OCR 텍스트에서 정산 정보를 추출하여 정형화된 데이터로 변환하세요. 필요시 세션의 {raw_text}를 참조할 수 있습니다.",
        output_schema=SettlementOcrData,
        output_key="settlement_data"
    )

    data_fetcher = DataFetcherAgent()

    diagnoser = LlmAgent(
        name="diagnoser",
        model=settings.GEMINI_MODEL,
        instruction="""
입력받은 정산 데이터 {settlement_data}와 외부 시장 데이터 {market_data}를 분석하여 수익 손실 진단을 수행하세요.

진단 기준:
1. 최적 수익 계산: 해당 월의 기상 기반 최적 발전량과 최적 SMP 단가, 예측 인센티브 추정치를 고려하여 최적 수익을 계산합니다.
2. 기회 비용 계산: (최적 수익) - {settlement_data}의 실제 수령액
3. 손실 원인 분류: 날씨(weather), 예측 오류(prediction_error), 시장 가격(market_price), 복합(mixed) 중 하나로 분류합니다.
4. 원인 메시지 생성: 소장님께 보낼 한 줄 메시지를 생성합니다. (예: "날씨: 이번달 손실 38만원. 일조량이 평균보다 18% 낮았어요.")

최종 결과는 DiagnosisResult 스키마에 맞춰 출력하세요.
""",
        output_schema=DiagnosisResult,
        output_key="diagnosis_result"
    )

    return SequentialAgent(
        name="mvp_analysis_pipeline",
        sub_agents=[vision_agent, ocr_refiner, data_fetcher, diagnoser]
    )

pipeline = create_settlement_pipeline()
analysis_pipeline = create_analysis_pipeline()
