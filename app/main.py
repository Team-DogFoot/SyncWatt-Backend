import logging
from fastapi import FastAPI
from app.api.webhook import router as webhook_router

# 로깅 설정 추가
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SyncWatt-Backend", version="0.1.0")

# 라우터 등록
app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    logger.info("Health check called")
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    logger.info("SyncWatt-Backend is starting up...")
