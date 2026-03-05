from pydantic import BaseModel, Field
from typing import List

class ExtractedInfo(BaseModel):
    key: str = Field(description="The label or category of the information")
    value: str = Field(description="The specific data value extracted")

class ImageAnalysisResult(BaseModel):
    summary: str = Field(description="A brief summary of the text found in the image")
    main_entities: List[ExtractedInfo] = Field(description="List of key information entities found (e.g. names, dates, amounts)")
    detected_language: str = Field(description="The primary language detected in the text")
