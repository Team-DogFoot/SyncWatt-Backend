import argparse
import logging
import os
import sys
import pandas as pd
from sqlmodel import Session, select

# Ensure the app directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine, init_db
from app.models.smp import SMP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seed_smp")

def load_smp_data(file_paths: list[str]):
    """
    Excel 파일에서 SMP 데이터를 직접 로드하여 DB에 저장합니다.
    """
    logger.info(f"Starting SMP data loading from {len(file_paths)} files...")
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.warning(f"SMP file not found: {file_path}")
            continue
        
        try:
            logger.info(f"Processing file: {file_path}")
            df = pd.read_excel(file_path, header=1)
            
            date_col = None
            avg_col = None
            
            for col in df.columns:
                if any(x in str(col) for x in ['거래일', '날짜', '일자', '구분']):
                    date_col = col
                if '평균' in str(col):
                    avg_col = col
            
            if not date_col or not avg_col:
                error_msg = f"Required columns not found in {file_path}. Columns: {df.columns.tolist()}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Convert date column to string to ensure correct parsing
            df[date_col] = df[date_col].astype(str)
            df[date_col] = pd.to_datetime(df[date_col], format='%Y%m%d', errors='coerce')
            
            # Remove rows where date parsing failed
            df = df.dropna(subset=[date_col])
            
            df['year_month'] = df[date_col].dt.strftime('%Y-%m')
            monthly_avg = df.groupby('year_month')[avg_col].mean().reset_index()
            
            with Session(engine) as session:
                for _, row in monthly_avg.iterrows():
                    ym = row['year_month']
                    avg_val = float(row[avg_col])
                    
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
            raise e

def main():
    parser = argparse.ArgumentParser(description="Seed SMP data from Excel files directly to the database.")
    parser.add_argument(
        "--files", 
        nargs="+", 
        required=True,
        help="List of Excel file paths to load."
    )
    
    args = parser.parse_args()
    
    logger.info("Initializing database tables...")
    init_db()
    
    try:
        load_smp_data(args.files)
        logger.info("SMP data seeding complete.")
    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
