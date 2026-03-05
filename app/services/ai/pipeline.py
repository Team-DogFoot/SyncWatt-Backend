from google.adk.agents import SequentialAgent, LlmAgent
from app.services.ai.vision_agent import VisionAgent
from app.schemas.ai import ImageAnalysisResult
from app.core.config import settings

def create_analysis_pipeline():
    vision_agent = VisionAgent()
    
    analysis_agent = LlmAgent(
        name="analyzer",
        model=settings.GEMINI_MODEL,
        instruction="Analyze the following raw OCR text and provide a structured summary: {raw_text}",
        output_schema=ImageAnalysisResult,
        output_key="analysis_result"
    )

    return SequentialAgent(
        name="image_processing_pipeline",
        sub_agents=[vision_agent, analysis_agent]
    )

pipeline = create_analysis_pipeline()
