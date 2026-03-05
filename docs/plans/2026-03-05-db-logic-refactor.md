# DB Setup and Logic Refactor Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement PostgreSQL database with SQLModel and refactor the loss diagnosis logic to be more precise and persistent.

**Architecture:** Use SQLModel for ORM, Docker Compose for PostgreSQL, and refactor existing agents to utilize the DB and updated diagnosis logic.

**Tech Stack:** Python, SQLModel, PostgreSQL, Docker Compose, Gemini API (ADK), Pandas (for Excel).

---

### Task 1: Docker Compose Setup

**Files:**
- Create: `./docker-compose.yml` (Root directory)
- Modify: `SyncWatt-Backend/.env`

**Step 1: Create docker-compose.yml in Root**
```yaml
version: '3.8'
services:
  db:
    image: postgres:16
    container_name: syncwatt-db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-syncwatt}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Step 2: Update SyncWatt-Backend/.env**
Ensure the database URL points to `localhost` for local development if the app runs outside Docker, or `db` if inside. Since we are running the backend app locally for now:
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=syncwatt
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/syncwatt
```

**Step 3: Run docker-compose up -d**
Verify container is running.

---

### Task 2: SQLModel Models Definition

**Files:**
- Create: `SyncWatt-Backend/app/models/user.py`
- Create: `SyncWatt-Backend/app/models/plant.py`
- Create: `SyncWatt-Backend/app/models/settlement.py`
- Create: `SyncWatt-Backend/app/models/contract.py`
- Create: `SyncWatt-Backend/app/models/smp.py`
- Create: `SyncWatt-Backend/app/db/session.py`

**Step 1: Create app/db/session.py**
Implement engine creation and `init_db()` to be called on app startup in `main.py`.

**Step 2: Define Models**
Accurately implement User, PowerPlant, MonthlySettlement, ContractHistory, and SMP models as per PRD requirements.

---

### Task 3: SMP Excel Data Loading & Logging Setup

**Files:**
- Create: `SyncWatt-Backend/app/services/external/smp_service.py`
- Modify: `SyncWatt-Backend/app/main.py`

**Step 1: Implement SMP Loader**
Parse `/Users/kkh/Downloads/smp_land_2026.xlsx` and `2025.xlsx`.
Calculate monthly average SMP and store it in the SMP table.
Add detailed logs: "Loading SMP data for {year_month}: Avg SMP = {avg_smp}".

**Step 2: Initialize DB and Load SMP on Startup**
Modify `main.py` to call `init_db()` and the SMP loader.

---

### Task 4: Refactor OCR & Diagnosis Agents with Enhanced Logging

**Files:**
- Modify: `SyncWatt-Backend/app/schemas/ai/settlement.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/ocr_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/data_agent.py`

**Step 1: Update OCR Agent**
Extract `address` and `year_month`, `generation_kwh`, `total_revenue_krw`.
Log: "OCR Extracted: {data}".

**Step 2: Update Data Agent**
- Fetch SMP from DB.
- Fetch Irradiance from KMA (current month vs last year same month).
- Log: "Market Data for {month}: Current SMP={smp}, Prev Month SMP={prev_smp}, Current Irradiance={irr}, Last Year Irr={prev_year_irr}".

**Step 3: Update Diagnosis Agent**
Implement the specific priority logic (Irradiance 10% -> SMP 10% -> Complex 5%).
Log: "Diagnosis Calculation: Optimal={optimal}, Actual={actual}, Loss={loss}, Reason={reason}".

---

### Task 5: Integration and Final Message

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/pipeline.py`
- Modify: `SyncWatt-Backend/app/services/telegram_service.py`

**Step 1: Save result to MonthlySettlement table**
Ensure `telegram_chat_id` is captured and saved.

**Step 2: Format final Telegram message**
Use the exact template provided, including the conditional location info.
Log: "Final Message Sent to {chat_id}: {message}".
