# SMP 적재 로직 수정 및 가입 유도 문구 추가 구현 계획

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 상용 환경에 부적합한 자동 SMP 로딩 로직을 제거하고, 손실 진단 결과에 예측 오차 개선 가능 금액(손실액의 40%)을 포함한 가입 유도 문구를 추가합니다.

**Architecture:** 
1. `app/main.py`의 시작 시 자동 적재 로직 제거 (적재는 `scripts/seed_smp.py` 전담).
2. `DiagnosisAgent`에서 잠재적 회수 금액 계산 로직 추가.
3. `TelegramService`의 메시지 템플릿 업데이트 및 조건부 출력 처리.

**Tech Stack:** Python, SQLModel, Gemini ADK (Agent).

---

### Task 1: 상용 환경 부적합 로직 제거 (자동 적재 중단)

**Files:**
- Modify: `SyncWatt-Backend/app/main.py`

**Step 1: main.py 수정**
- `startup_event`에서 `smp_service.load_smp_data()` 호출부 삭제.
- 불필요한 `from app.services.external.smp_service import smp_service` 임포트 제거.

---

### Task 2: 진단 스키마 및 에이전트 로직 수정

**Files:**
- Modify: `SyncWatt-Backend/app/schemas/ai/diagnosis.py`
- Modify: `SyncWatt-Backend/app/services/ai/agents/diagnosis_agent.py`

**Step 1: DiagnosisResult 스키마 업데이트**
```python
class DiagnosisResult(BaseModel):
    # ... 기존 필드 ...
    potential_recovery_krw: int = Field(default=0, description="예측 오차 개선 가능 금액 (추산)")
```

**Step 2: DiagnosisAgent 지침 업데이트**
- 지침(Instruction)에 "잠재적 회수 금액 = 손실액 * 0.4 (소수점 버림)" 계산 규칙 추가.
- 주석으로 "해당 수치는 입찰 예측 최적화를 통한 40% 회수 가능성을 가정한 추산값임" 명시.

---

### Task 3: 텔레그램 메시지 템플릿 및 조건부 출력 구현

**Files:**
- Modify: `SyncWatt-Backend/app/services/telegram_service.py`

**Step 1: 메시지 포맷 수정**
- 손실액(`opportunity_loss_krw`)이 0보다 큰 경우에만 가입 유도 문구 노출.
- 금액 천 단위 콤마 포맷 적용.

**Step 2: 최종 메시지 템플릿 적용**
```text
📝 지난달 손실 진단 결과

이번 달은 약 {손실액}원의 손실이 발생했습니다.

최적 수익 {최적수익}원 - 실제 수령 {실제수령}원 = {손실액}원

💡 주요 원인
{원인 한 줄}

📈 이 중 약 {예측오차개선가능금액}원은 입찰 예측값 최적화로 회수 가능해요.
가입 후 매일 아침 입찰 추천값을 받아보세요.

🔗 상세 리포트 보기
```

---

### Task 4: 검증 및 로깅 확인

**Step 1: 단위 테스트 또는 로그 확인**
- 손실이 있는 경우와 없는 경우의 메시지 분기 처리 확인.
- 계산 로직(`loss * 0.4`) 결과값이 로그에 정확히 찍히는지 확인.
