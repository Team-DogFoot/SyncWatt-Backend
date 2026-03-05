# SyncWatt MVP 아키텍처 고도화 및 버그 수정 계획

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `VerifierAgent`(LLM)를 제거하고 Python 기반의 `CodeVerifierAgent`로 교체하여 정합성 검증의 신뢰도를 확보합니다. 또한 OCR/진단 단계의 `None` 반환 버그를 근본적으로 수정하고 도메인 로직(한전/KPX)을 현실화합니다.

**Architecture:** 
1. **검증 로직의 코드화**: LLM은 오직 데이터 추출(`OcrRefiner`, `DirectVision`)만 담당하며, 두 결과의 비교 및 수치 정합성 체크는 Python 코드로 수행합니다.
2. **파싱 신뢰도 확보**: ADK의 자동 파싱에만 의존하지 않고, LLM 응답을 명시적으로 로깅하고 필요시 수동 파싱 로직을 보강하여 `None` 반환 문제를 해결합니다.
3. **도메인 정합성**: 한전 계약 유형에 대한 섣부른 추천을 제거하고 "KPX 전환 시의 기회 수익 분석"이라는 일관된 관점을 유지합니다.

**Tech Stack:** Python, SQLModel, Gemini ADK (BaseAgent).

---

### Task 1: 스키마 보강 및 VerifierAgent(LLM) 제거

**Files:**
- Modify: `SyncWatt-Backend/app/schemas/ai/settlement.py`
- Delete: `SyncWatt-Backend/app/services/ai/agents/verifier_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/factory.py`

**Step 1: SettlementOcrData 스키마에 단가(unit_price) 추가**
- 정산서에 적힌 '기준단가'를 추출할 수 있도록 필드 추가. 검증 수식에 활용.

**Step 2: 기존 LLM 기반 VerifierAgent 삭제**
- `verifier_agent.py` 파일 삭제 및 팩토리 메서드 제거.

---

### Task 2: Python 기반 CodeVerifierAgent 구현

**Files:**
- Create: `SyncWatt-Backend/app/services/ai/agents/code_verifier.py`
- Modify: `SyncWatt-Backend/app/services/ai/pipeline.py`

**Step 1: 코드 기반 검증 에이전트 작성**
- `BaseAgent`를 상속받아 `_run_async_impl` 구현.
- `ocr_data`와 `visual_data`를 입력받아 다음 로직 수행:
  1. 두 데이터가 일치하면 즉시 채택.
  2. 불일치 시 `abs(단가 * 발전량 - 공급가액) < 1000` 수식으로 정합성이 맞는 쪽 선택.
  3. 둘 다 틀리거나 데이터 부족 시, 공급가액이 존재하는 쪽을 우선하되 로그에 "신뢰도 낮음" 기록.
- 선택 사유를 `selection_reason`에 명시하고 `settlement_data` 세션 상태에 저장.

---

### Task 3: OCR/진단 None 버그 근본 수정 및 로깅

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/ocr_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`

**Step 1: OcrRefinerAgent 파싱 로직 강화**
- `LlmAgent` 대신 `BaseAgent`를 사용하거나, `LlmAgent` 내부에서 발생하는 파싱 에러를 캐치하도록 수정.
- LLM이 반환하는 JSON 앞뒤의 코드 블록(```json)을 제거하는 전처리 로직 확인 및 보강.
- 필수 필드 누락 시 `None`이 되는 대신, 추출된 부분이라도 반환하도록 유연한 모델링 적용.

---

### Task 4: 기상청 기본값 명확화 및 추천 로직 제거

**Files:**
- Modify: `SyncWatt-Backend/app/services/external/kma_service.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`
- Modify: `SyncWatt-Backend/app/services/telegram_service.py`

**Step 1: 기상청 기본값(Proxy) 상수화**
- `DEFAULT_IRRADIANCE = 15.5` 상수를 정의하고 사용 시 `[KMA] Using default irradiance: 15.5` 로그 강제 출력.

**Step 2: 위험한 추천 분기 제거**
- `DiagnosisAgent`에서 "유지 추천" 메시지 삭제.
- 오직 "시장가 적용 시 수익 차이" 정보만 제공하도록 수정.

---

### Task 5: 통합 테스트 및 최종 검증

**Step 1: 동일 이미지 재테스트**
- 버그가 발생했던 2019년 12월 정산서 이미지로 다시 테스트.
- 로그를 통해 `CodeVerifierAgent`가 올바른 데이터를 선택하는지, `None`이 발생하지 않는지 최종 확인.
