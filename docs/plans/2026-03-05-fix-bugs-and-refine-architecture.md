# SyncWatt MVP 버그 수정 및 아키텍처 고도화 계획

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** OCR/진단 에이전트의 None 반환 및 날짜 오파싱 버그를 수정하고, 한전 계약 대상 SMP 포지셔닝 및 위치 처리 로직을 현실화합니다.

**Architecture:** 
1. **에이전트 신뢰도 강화**: `OcrRefiner`, `DirectVision`의 프롬프트 보강 및 `VerifierAgent`에 수치 검증(발전량*단가=공급가액) 로직 추가.
2. **비즈니스 로직 수정**: 손실 진단을 "KPX 전환 시 기대 수익" 관점으로 재정의하여 한전 계약 발전소 소장님께 유의미한 가치 전달.
3. **안정성 확보**: DB 저장 실패가 메시지 발송을 막지 않도록 비동기/예외 처리 강화.

**Tech Stack:** Python, SQLModel, Gemini ADK, KMA API.

---

### Task 1: 침묵하는 에러(None) 및 날짜 오파싱 수정

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/ocr_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/visual_agent.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`

**Step 1: OCR/Vision 에이전트 프롬프트 및 로그 보강**
- `year_month` 추출 시 "2019", "2023" 등 연도를 절대 놓치지 말 것을 강조.
- 추출된 원본 텍스트와 파싱된 객체를 각 단계에서 강제 로그 출력.
- OCR 정제 실패 시(None 반환 시) 원인 로그 출력하도록 `_run_async_impl` 수정.

**Step 2: DiagnosisAgent Fallback 제거**
- 진단 결과가 None임에도 메시지가 나가는 현상 차단. 
- 데이터 부족 시 "진단 불가" 메시지를 명확히 정의.

---

### Task 2: VerifierAgent 검증 기준 수립

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/verifier_agent.py`

**Step 1: 수치 정합성 검증 로직 주입**
- 프롬프트에 "단가 * 발전량 ≈ 공급가액" 인지 확인하는 검증 단계 추가.
- OCR과 Visual이 다를 경우, 위 수식에 더 가까운 값을 선택하도록 지침 수정.
- 선택 근거를 `selection_reason` 로그로 남기도록 수정.

---

### Task 3: 한전 계약 대응 및 SMP 계산식 포지셔닝 변경

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`
- Modify: `SyncWatt-Backend/app/services/telegram_service.py`

**Step 1: 진단 관점 변경 (한전 -> KPX 전환 유도)**
- 한전 계약 단가(기준단가)와 SMP의 차이를 인식.
- 메시지 문구를 "KPX로 계약을 전환했다면 얻었을 최적 수익"으로 변경.
- "한전 계약 소장님은 KPX 전환 시 약 {N}원의 추가 수익이 가능해요" 뉘앙스 적용.

---

### Task 4: 위치 처리 로직 개선 (도 단위 매핑)

**Files:**
- Modify: `SyncWatt-Backend/app/services/ai/data_agent.py`

**Step 1: 주요 도별 관측소 매핑 확대**
- 전남(목포/무안), 전북(전주), 충남(홍성), 경남(창원) 등 태양광 밀집 지역 관측소 코드 추가.
- 주소에서 "전남", "전라남도" 등의 키워드 검출 로직 강화.

**Step 2: 기상청 API 과거 데이터 호출 안정성**
- 2018년 등 아주 오래된 데이터 호출 시 타임아웃 처리 및 Mock 데이터 Fallback 로직 점검.

---

### Task 5: UX 및 서비스 안정화 (DB/메시지)

**Files:**
- Modify: `SyncWatt-Backend/app/services/telegram_service.py`

**Step 1: DB 저장 예외 격리**
- `_save_settlement_to_db`를 완전한 try-except로 감싸서 에러가 발생해도 `send_text_message`는 호출되도록 보장.

**Step 2: 최종 메시지 템플릿 최종 수정**
- 피드백 받은 계산식 및 가입 유도 문구의 톤앤매너 최종 적용.
