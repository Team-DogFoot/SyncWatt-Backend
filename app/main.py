import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.webhook import router as webhook_router
from app.api.calculator import router as calculator_router
from app.api.auth import router as auth_router
from app.core.config import settings
from app.db.session import init_db

# Structured logging: prod=JSON (K8s compatible), dev=colored text
_is_prod = os.getenv("ENV", "dev") in ("prod", "production")

if _is_prod:
    from pythonjsonlogger.json import JsonFormatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
else:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("========================================")
    logger.info("  SyncWatt-Backend Service Starting...  ")
    logger.info(f"  Project: {settings.PROJECT_NAME}")
    logger.info(f"  Model:   {settings.GEMINI_MODEL}")
    logger.info("========================================")
    init_db()
    logger.info("Database initialized (schema only)")
    logger.info("System initialization complete")
    yield


app = FastAPI(title="SyncWatt-Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://syncwatt.dog-foot.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(calculator_router)
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
