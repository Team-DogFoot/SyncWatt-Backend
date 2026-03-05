from pydantic import BaseModel, Field
from enum import Enum

class LossCause(str, Enum):
    WEATHER = "weather"
    SMP = "smp"
    COMPLEX = "complex"
    UNKNOWN = "unknown"

class DiagnosisResult(BaseModel):
    year_month: str = Field(description="정산 연월")
    actual_revenue_krw: int = Field(description="실제 수령액 (원)")
    optimal_revenue_krw: int = Field(description="최적 수익 (원)")
    opportunity_loss_krw: int = Field(description="손실액 (원)")
    potential_recovery_krw: int = Field(default=0, description="예측 오차 개선 가능 금액 (추산, 손실액의 40%)")
    loss_cause: LossCause = Field(description="손실 주 원인 분류")
    one_line_message: str = Field(description="원인 한 줄 메시지")
    address_used: bool = Field(default=False, description="주소 사용 여부")
