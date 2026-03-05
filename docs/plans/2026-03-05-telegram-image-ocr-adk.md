# Telegram Image Analysis with Google ADK Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a Telegram bot feature that extracts and analyzes text from images using Google ADK, Google Cloud Vision, and Gemini.

**Architecture:** A Google ADK pipeline consisting of a custom `VisionAgent` (BaseAgent) for OCR and an `AnalysisAgent` (LlmAgent) for structured interpretation, orchestrated via a `SequentialAgent`.

**Tech Stack:** Python, FastAPI, Google ADK (`google-adk`), Google Cloud Vision, Pydantic, Gemini 2.0.

---

### Task 1: Environment & Dependency Setup

**Files:**
- Modify: `requirements.txt`
- Modify: `app/core/config.py`

**Step 1: Update requirements.txt**
Add `google-adk` and `google-cloud-vision` to the dependencies.

```text
google-adk
google-cloud-vision
```

**Step 2: Update Configuration**
Add necessary settings for Google Cloud and Gemini.

```python
# app/core/config.py
class Settings(BaseSettings):
    # ... existing ...
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
```

**Step 3: Install dependencies**
Run: `pip install -r requirements.txt`

**Step 4: Commit**
```bash
git add requirements.txt app/core/config.py
git commit -m "chore: add google-adk and vision dependencies"
```

---

### Task 2: Define Output Schemas

**Files:**
- Create: `app/schemas/ai.py`

**Step 1: Create the Pydantic schema for analysis results**
This schema will be used by the `LlmAgent` to provide structured output.

```python
from pydantic import BaseModel, Field

class ImageAnalysisResult(BaseModel):
    summary: str = Field(description="A brief summary of the text found in the image")
    extracted_data: dict = Field(description="Key-value pairs of important information extracted")
    detected_language: str = Field(description="The primary language detected in the text")
```

**Step 2: Commit**
```bash
git add app/schemas/ai.py
git commit -m "feat: define AI output schemas"
```

---

### Task 3: Implement Vision Agent (BaseAgent)

**Files:**
- Create: `app/services/ai/vision_agent.py`

**Step 1: Implement the VisionAgent using BaseAgent**
This agent will handle the Google Cloud Vision OCR call asynchronously.

```python
from google.adk.agents import BaseAgent
from google.adk.types import Event
from google.cloud import vision
import asyncio

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="vision_ocr", description="Extracts text from image bytes using Google Cloud Vision")
        self.client = vision.ImageAnnotatorClient()

    async def run_async_impl(self, ctx):
        # Image bytes are expected to be in the session state
        image_bytes = ctx.session.state.get("image_bytes")
        if not image_bytes:
            yield Event(author=self.name, content="No image bytes found in session state.")
            return

        image = vision.Image(content=image_bytes)
        # Run synchronous GCP call in a thread pool to maintain async integrity
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.client.text_detection, image)
        
        texts = response.text_annotations
        extracted_text = texts[0].description if texts else ""
        
        # Save to state for next agent
        ctx.session.state["raw_text"] = extracted_text
        
        yield Event(author=self.name, content=f"Extracted {len(extracted_text)} characters.")
```

**Step 2: Commit**
```bash
git add app/services/ai/vision_agent.py
git commit -m "feat: implement VisionAgent for OCR"
```

---

### Task 4: Implement Analysis Agent & Pipeline

**Files:**
- Create: `app/services/ai/pipeline.py`

**Step 1: Define the LLM Agent and Sequential Pipeline**
Combine the VisionAgent and LlmAgent into a single declarative pipeline.

```python
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
```

**Step 2: Commit**
```bash
git add app/services/ai/pipeline.py
git commit -m "feat: implement ADK analysis pipeline"
```

---

### Task 5: Integrate with Telegram Service

**Files:**
- Modify: `app/services/telegram_service.py`

**Step 1: Update handle_photo_message to invoke the ADK pipeline**
Replace the TODO with the actual pipeline execution.

```python
# app/services/telegram_service.py
from app.services.ai.pipeline import pipeline
from google.adk.session import Session

# ... inside handle_photo_message ...
    # 2. 인메모리 다운로드
    image_bytes = await self.download_image_to_memory(file_path)
    
    # 3. ADK 파이프라인 실행
    session = Session(state={"image_bytes": image_bytes})
    result_event = await pipeline.run_async(session=session)
    
    # 결과 추출 (analysis_result는 SequentialAgent의 마지막 결과로 세션에 저장됨)
    analysis = session.state.get("analysis_result")
    if analysis:
        response_text = f"📝 요약: {analysis.summary}\n🌐 언어: {analysis.detected_language}"
        await self.send_text_message(chat_id, response_text)
```

**Step 2: Commit**
```bash
git add app/services/telegram_service.py
git commit -m "feat: integrate ADK pipeline into telegram service"
```

---

### Task 6: Verification & Testing

**Step 1: Create a mock test script for the pipeline**
Verify the ADK flow without needing a real Telegram webhook.

**Step 2: Run verification**
Run: `pytest tests/test_ai_pipeline.py`

**Step 3: Final Commit**
```bash
git commit -m "test: add verification tests for AI pipeline"
```
