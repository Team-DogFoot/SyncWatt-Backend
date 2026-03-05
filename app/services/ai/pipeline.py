from google.adk.agents import SequentialAgent, LlmAgent
from app.services.ai.vision_agent import VisionAgent
from app.schemas.ai.analysis import ImageAnalysisResult
from app.core.config import settings

def create_analysis_pipeline():
    vision_agent = VisionAgent()
    
    analysis_agent = LlmAgent(
        name="analyzer",
        model=settings.GEMINI_MODEL,
        instruction="입력받은 OCR 텍스트를 분석하여 핵심 정보를 추출하세요. 필요시 세션의 {raw_text}를 참조할 수 있습니다.",
        output_schema=ImageAnalysisResult,
        output_key="analysis_result"
    )

    return SequentialAgent(
        name="image_processing_pipeline",
        sub_agents=[vision_agent, analysis_agent]
    )

pipeline = create_analysis_pipeline()
