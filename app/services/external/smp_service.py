import logging
from sqlmodel import Session, select
from app.db.session import engine
from app.models.smp import SMP

logger = logging.getLogger(__name__)

class SMPService:
    """
    SMP 데이터 조회 전용 서비스입니다.
    적재는 scripts/seed_smp.py를 사용하세요.
    """
    def get_avg_smp(self, year_month: str) -> float:
        """
        특정 연월의 평균 SMP를 조회합니다.
        """
        with Session(engine) as session:
            statement = select(SMP).where(SMP.year_month == year_month)
            result = session.exec(statement).first()
            return result.avg_smp if result else None

smp_service = SMPService()
