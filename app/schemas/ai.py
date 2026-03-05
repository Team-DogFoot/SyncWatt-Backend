from pydantic import BaseModel, Field

class ImageAnalysisResult(BaseModel):
    summary: str = Field(description="A brief summary of the text found in the image")
    extracted_data: dict = Field(description="Key-value pairs of important information extracted")
    detected_language: str = Field(description="The primary language detected in the text")
