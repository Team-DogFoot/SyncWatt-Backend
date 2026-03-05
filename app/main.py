import logging
from fastapi import FastAPI
from app.api.webhook import router as webhook_router
from app.core.config import settings
from app.db.session import init_db

# 로깅 설정 최적화
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SyncWatt-Backend", version="0.1.0")

# 라우터 등록
app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    logger.info("========================================")
    logger.info("  SyncWatt-Backend Service Starting...  ")
    logger.info(f"  Project: {settings.PROJECT_NAME}")
    logger.info(f"  Model:   {settings.GEMINI_MODEL}")
    logger.info("========================================")
    
    # DB 초기화 (테이블 생성만)
    init_db()
    logger.info("Database initialized (schema only)")
    
    logger.info("System initialization complete")
