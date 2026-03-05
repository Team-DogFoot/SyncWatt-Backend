from pydantic import BaseModel, Field
from enum import Enum

class LossCause(str, Enum):
    WEATHER = "weather"
    PREDICTION_ERROR = "prediction_error"
    MARKET_PRICE = "market_price"
    MIXED = "mixed"

class DiagnosisResult(BaseModel):
    optimal_revenue_krw: int = Field(description="최적 수익 역산 결과 (원)")
    opportunity_loss_krw: int = Field(description="기회 비용 (손실액, 원)")
    loss_cause: LossCause = Field(description="손실 주 원인 분류")
    one_line_message: str = Field(description="소장님께 보낼 원인 한 줄 메시지")
