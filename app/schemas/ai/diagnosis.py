from pydantic import BaseModel, Field
from enum import Enum

class LossCause(str, Enum):
    WEATHER = "weather"
    SMP = "smp"
    COMPLEX = "complex"
    UNKNOWN = "unknown"

class DiagnosisResult(BaseModel):
    year_month: str = Field(description="정산 연월")
    generation_kwh: float = Field(default=0, description="발전량 (kWh)")
    capacity_kw: float | None = Field(default=None, description="설비용량 (kW)")
    utilization_pct: float | None = Field(default=None, description="이용률 (%)")
    unit_price: float = Field(default=0, description="정산 기준 단가 (원/kWh)")
    curr_smp: float = Field(default=0, description="당월 SMP 평균 (원/kWh)")
    actual_revenue_krw: int = Field(description="실제 수령액 (원)")
    optimal_revenue_krw: int = Field(description="최적 수익 (원)")
    opportunity_loss_krw: int = Field(description="손실액 (원)")
    potential_recovery_krw: int = Field(default=0, description="예측 오차 개선 가능 금액 (추산, 손실액의 40%)")
    loss_cause: LossCause = Field(description="손실 주 원인 분류")
    one_line_message: str = Field(description="원인 한 줄 메시지")
    smp_context_message: str = Field(default="", description="SMP 계절 변동 맥락 메시지")
    address_used: bool = Field(default=False, description="주소 사용 여부")
