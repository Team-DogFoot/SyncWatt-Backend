import pandas as pd
import logging
from sqlmodel import Session, select
from app.db.session import engine
from app.models.smp import SMP
import os

logger = logging.getLogger(__name__)

class SMPService:
    def __init__(self):
        self.default_file_paths = []

    def load_smp_data(self, file_paths: list[str] = None):
        """
        Excel 파일에서 SMP 데이터를 로드하여 DB에 저장합니다.
        """
        target_paths = file_paths or self.default_file_paths
        if not target_paths:
            logger.warning("No SMP file paths provided for loading.")
            return

        logger.info(f"Starting SMP data loading from {len(target_paths)} files...")
        
        for file_path in target_paths:
            if not os.path.exists(file_path):
                logger.warning(f"SMP file not found: {file_path}")
                continue
            
            try:
                # 계통한계가격(SMP) 데이터 로드
                # 보통 '구분', '1시', '2시', ..., '24시', '평균' 형태이거나 
                # 날짜별 데이터가 행으로 나열됨.
                df = pd.read_excel(file_path)
                
                # 데이터 구조 파악 및 전처리 (KPX 육지 SMP 기준)
                # 보통 '거래일' 또는 '날짜' 컬럼이 있고 '평균' 컬럼이 있음
                # 컬럼명이 다를 수 있으므로 유연하게 처리
                date_col = None
                avg_col = None
                
                for col in df.columns:
                    if '거래일' in str(col) or '날짜' in str(col) or '일자' in str(col):
                        date_col = col
                    if '평균' in str(col):
                        avg_col = col
                
                if not date_col or not avg_col:
                    error_msg = f"Required columns (date/average) not found in {file_path}. Columns found: {df.columns.tolist()}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # 날짜 형식 변환
                df[date_col] = pd.to_datetime(df[date_col])
                df['year_month'] = df[date_col].dt.strftime('%Y-%m')
                
                # 월별 평균 계산
                monthly_avg = df.groupby('year_month')[avg_col].mean().reset_index()
                
                with Session(engine) as session:
                    for _, row in monthly_avg.iterrows():
                        ym = row['year_month']
                        avg_val = float(row[avg_col])
                        
                        # 이미 존재하는지 확인
                        statement = select(SMP).where(SMP.year_month == ym)
                        existing = session.exec(statement).first()
                        
                        if existing:
                            existing.avg_smp = avg_val
                            logger.info(f"Updated SMP for {ym}: {avg_val:.2f}")
                        else:
                            new_smp = SMP(year_month=ym, avg_smp=avg_val)
                            session.add(new_smp)
                            logger.info(f"Inserted SMP for {ym}: {avg_val:.2f}")
                    
                    session.commit()
                
            except Exception as e:
                logger.error(f"Error processing SMP file {file_path}: {str(e)}")

    def get_avg_smp(self, year_month: str) -> float:
        """
        특정 연월의 평균 SMP를 조회합니다.
        """
        with Session(engine) as session:
            statement = select(SMP).where(SMP.year_month == year_month)
            result = session.exec(statement).first()
            return result.avg_smp if result else None

smp_service = SMPService()
