# SyncWatt MVP (Monthly Loss Diagnosis) Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the full MVP flow where a user uploads a settlement statement photo and receives a calculated loss amount with a one-line cause.

**Architecture:** A Google ADK pipeline using `VisionAgent` for OCR, a custom `EconomicDataAgent` for external API fetching, and a `DiagnosisAgent` (LLM) for final calculation and one-line cause generation. Data is persisted in PostgreSQL via SQLAlchemy.

**Tech Stack:** Python, FastAPI, Google ADK, Google Cloud Vision, Gemini 2.0, SQLAlchemy, PostgreSQL, httpx.

---

### Task 1: Database Schema & Models

**Files:**
- Create: `app/core/database.py`
- Create: `app/models/base.py`
- Create: `app/models/user.py`
- Create: `app/models/plant.py`
- Create: `app/models/settlement.py`

**Step 1: Setup SQLAlchemy Base and Engine**
Implement the async engine and session factory in `app/core/database.py`.

**Step 2: Define Models based on PRD**
- `User`: `telegram_chat_id`, `plan`.
- `PowerPlant`: `user_id`, `address`, `capacity_kw`, `lat`, `lng`.
- `MonthlySettlement`: `plant_id`, `year_month`, `actual_generation_kwh`, `actual_revenue_krw`, `opportunity_loss_krw`, `loss_cause`.

**Step 3: Commit**
```bash
git add app/core/database.py app/models/
git commit -m "feat: implement database models for MVP"
```

---

### Task 2: External Data Integration (KMA & KPX Tools)

**Files:**
- Create: `app/services/external/kma_service.py`
- Create: `app/services/external/kpx_service.py`
- Modify: `app/core/config.py` (Add API Keys)

**Step 1: Implement KMA (Weather) Service**
Fetch monthly average irradiance for a given coordinate/address.

**Step 2: Implement KPX (SMP/REC) Service**
Fetch monthly average SMP and REC prices.

**Step 3: Commit**
```bash
git add app/services/external/ app/core/config.py
git commit -m "feat: add KMA and KPX external data services"
```

---

### Task 3: Refined OCR Schema & Agent

**Files:**
- Create: `app/schemas/ai/settlement.py`
- Modify: `app/services/ai/pipeline.py`

**Step 1: Define Settlement OCR Schema**
```python
class SettlementOcrData(BaseModel):
    year_month: str
    generation_kwh: float
    total_revenue_krw: int
```

**Step 2: Update Pipeline to extract specific data**
Add an `LlmAgent` immediately after `VisionAgent` to convert raw text into `SettlementOcrData`.

**Step 3: Commit**
```bash
git add app/schemas/ai/settlement.py app/services/ai/pipeline.py
git commit -m "feat: add structured OCR extraction for settlements"
```

---

### Task 4: Implement Economic Data Fetcher Agent

**Files:**
- Create: `app/services/ai/data_agent.py`

**Step 1: Create DataFetcherAgent (BaseAgent)**
This agent reads the `year_month` and `plant_id` from the session, calls KMA/KPX services, and stores the market/weather data in the session state.

**Step 2: Commit**
```bash
git add app/services/ai/data_agent.py
git commit -m "feat: implement DataFetcherAgent for market/weather data"
```

---

### Task 5: Final Diagnosis Agent & Pipeline Assembly

**Files:**
- Create: `app/schemas/ai/diagnosis.py`
- Modify: `app/services/ai/pipeline.py`

**Step 1: Define Diagnosis Result Schema**
Includes `loss_krw`, `reason_category`, and `one_line_message`.

**Step 2: Implement DiagnosisAgent (LlmAgent)**
An LLM agent that takes OCR data + External data, performs the "Opportunity Cost" calculation (using the formula in PRD), and formats the one-line response.

**Step 3: Assemble Sequential Pipeline**
`VisionAgent` -> `OcrRefinerAgent` -> `DataFetcherAgent` -> `DiagnosisAgent`.

**Step 4: Commit**
```bash
git add app/schemas/ai/diagnosis.py app/services/ai/pipeline.py
git commit -m "feat: assemble final MVP analysis pipeline"
```

---

### Task 6: Telegram Persistence & Response

**Files:**
- Modify: `app/services/telegram_service.py`

**Step 1: Implement Data Persistence**
After pipeline completion, save the results into the `MonthlySettlement` table.

**Step 2: Format Telegram Response**
Match the PRD example: "📝 지난달 42만원 손실이에요. 원인: 일조량이 평균보다 18% 낮았어요. [상세보기 링크]"

**Step 3: Commit**
```bash
git add app/services/telegram_service.py
git commit -m "feat: persist analysis results and send PRD-compliant telegram response"
```

---

### Task 7: E2E Verification

**Step 1: Create integration test with real/mock API responses**
**Step 2: Verify database records**
**Step 3: Commit**
```bash
git commit -m "test: verify full MVP flow from photo upload to loss diagnosis"
```
