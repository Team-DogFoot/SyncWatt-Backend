# SyncWatt 전체 파이프라인 로깅 강화 계획

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 분석 파이프라인의 모든 단계에서 입출력 데이터와 계산 근거를 상세히 로깅하여, 수치 오류나 파싱 실패의 원인을 즉각적으로 파악할 수 있게 합니다.

**Architecture:** 
1. **Raw 데이터 가시화**: LLM의 Raw JSON 응답을 파싱 전 로그에 출력.
2. **계산 과정 상세화**: 수식 적용 시 변수값과 결과값을 문장 형태로 로깅 (예: "6600kWh * 83.6원 = 551,760원").
3. **결정 근거 로깅**: `CodeVerifierAgent`에서 어떤 필드가 왜 불일치했는지 비교 세부 내역 출력.

**Tech Stack:** Python Logging.

---

### Task 1: 추출 에이전트 Raw 로깅 강화 (OCR/Visual)

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/ocr_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/visual_agent.py`

**Step 1: LLM Raw Response 로그 추가**
- 파이프라인 각 단계 종료 직후 `ctx.session.state`에 저장된 결과 객체를 `model_dump_json()`으로 출력.
- 파싱 실패 시 LLM이 보낸 전체 텍스트를 로그에 남기도록 방어 코드 작성.

---

### Task 2: CodeVerifierAgent 비교 내역 상세화

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/code_verifier.py`

**Step 1: 필드별 비교 로그 추가**
- OCR과 Visual 데이터의 `generation_kwh`, `unit_price`, `total_revenue_krw` 값을 1:1로 비교하여 차이가 발생하는 필드를 로그에 명시.
- `Integrity check` 수행 시의 상세 계산 식을 `logger.info`로 격상.

---

### Task 3: DiagnosisAgent 계산 수식 로깅

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`

**Step 1: 수식 로그 추가**
- 최적 수익 계산 시: `f"Optimal Calculation: {gen}kWh * {smp}원 = {result}원"`
- 손실액 계산 시: `f"Loss Calculation: {optimal}원 - {actual}원 = {loss}원"`
- 원인 판별 기준값 로그: `f"Weather Diff: {curr_irr} vs {prev_irr} ({diff}%)"`

---

### Task 4: TelegramService 최종 데이터 로깅

**Files:**
- Modify: `SyncWatt-Backend/app/services/telegram_service.py`

**Step 1: 최종 구조화 데이터 로그 추가**
- 메시지 발송 직전, 화면에 뿌려질 모든 변수(formatted values)를 하나의 딕셔너리로 묶어 로그 출력.

---

### Task 5: 검증 및 로그 확인

**Step 1: 테스트 실행 및 로그 분석**
- 정산서 업로드 후 `kubectl logs`를 통해 위 단계에서 정의한 상세 수식과 Raw 데이터가 순서대로 찍히는지 확인.
