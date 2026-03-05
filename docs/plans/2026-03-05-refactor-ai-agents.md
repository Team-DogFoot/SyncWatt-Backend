# AI Agents Refactor and Bug Fixes Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor and fix bugs in AI agents (`visual_agent.py`, `ocr_agent.py`, `diagnosis_agent.py`, `code_verifier.py`, `data_agent.py`) to ensure correct data flow, calculation logic, and validation.

**Architecture:** Use ADK's `LlmAgent` and `BaseAgent` more effectively by passing explicit inputs, moving calculations to Python, and improving data validation and fallback mechanisms.

**Tech Stack:** Python, Google ADK, Pydantic, Gemini Pro Vision/Flash.

---

### Task 1: Fix `visual_agent.py` to pass image bytes to LLM

**Files:**
- Modify: `app/services/ai/agents/visual_agent.py`
- Create: `tests/test_visual_agent.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.ai.agents.visual_agent import DirectVisionAgent

@pytest.mark.asyncio
async def test_visual_agent_passes_image_bytes():
    agent = DirectVisionAgent()
    ctx = MagicMock()
    ctx.session.state = {"image_bytes": b"fake_image_bytes"}
    
    with patch("google.adk.agents.LlmAgent._run_async_impl", new_callable=AsyncMock) as mock_super:
        mock_super.return_value = []
        async for _ in agent._run_async_impl(ctx):
            pass
        
        # Check if the image bytes were passed in some form to super()._run_async_impl
        # This depends on how we implement the fix. If we use ctx.inputs, we check mock_super call.
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_visual_agent.py -v`
Expected: FAIL (Image bytes not passed to LLM)

**Step 3: Write minimal implementation**

```python
from google.generativeai.types import Part

# In _run_async_impl
image_bytes = ctx.session.state.get("image_bytes")
if image_bytes:
    # Option 1: Inject into ctx.inputs (if ADK supports)
    # Option 2: Pass directly to super call if it accepts inputs
    # Let's use the most standard ADK way once verified
    pass
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_visual_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/ai/agents/visual_agent.py tests/test_visual_agent.py
git commit -m "fix(ai): pass image bytes to LLM in visual_agent"
```

---

### Task 2: Fix `ocr_agent.py` to explicitly pass `raw_text` to LLM

**Files:**
- Modify: `app/services/ai/agents/ocr_agent.py`
- Create: `tests/test_ocr_agent.py`

**Step 1: Write the failing test**

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
Modify `instruction` to use `{raw_text}` and ensure it's available in the context.

**Step 4: Run test to verify it passes**

**Step 5: Commit**

---

### Task 3: Refactor `diagnosis_agent.py` (Calculations & Imports)

**Files:**
- Modify: `app/services/ai/agents/diagnosis_agent.py`
- Create: `tests/test_diagnosis_agent.py`

**Step 1: Write the failing test**

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
- Move `DiagnosisResult`, `LossCause` imports to top-level.
- In `_run_async_impl`, calculate `optimal_revenue_krw` and `opportunity_loss_krw` in Python.
- Pass these pre-calculated values to LLM via `ctx.session.state`.
- Update `instruction` to use these values instead of asking LLM to calculate.
- Use `.model_dump_json()` for Pydantic objects in instructions if needed.

**Step 4: Run test to verify it passes**

**Step 5: Commit**

---

### Task 4: Improve `code_verifier.py` (Validation Logic)

**Files:**
- Modify: `app/services/ai/agents/code_verifier.py`
- Create: `tests/test_code_verifier.py`

**Step 1: Write the failing test**
Test cases for:
- 1000 KRW tolerance vs 2% tolerance.
- Both invalid results fallback.
- Pydantic object equality check.

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
- `tolerance = max(1000, data.total_revenue_krw * 0.02)`
- Fallback logic: compare `ocr_diff` and `vis_diff`, pick smaller.
- `_is_same` method for comparing core fields.

**Step 4: Run test to verify it passes**

**Step 5: Commit**

---

### Task 6: Complete `data_agent.py` (Missing Logic & Address Mapping)

**Files:**
- Modify: `app/services/ai/agents/data_agent.py`
- Create: `tests/test_data_agent.py`

**Step 1: Write the failing test**

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
- Implement 전년 동월 일조량 비교용 변수 (`prev_year_dt`).
- Handle SMP `None` by setting an error flag or keeping it as `None` for later agents to handle gracefully.
- Add more address keywords (경기도 안성/평택, 강원도, 경북 의성/영주, 전남 해남/영암).

**Step 4: Run test to verify it passes**

**Step 5: Commit**
