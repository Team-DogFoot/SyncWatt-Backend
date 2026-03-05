import logging
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from app.schemas.telegram import Update
from app.services.telegram_service import telegram_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["Telegram"])

@router.post("/telegram")
async def telegram_webhook(
    update: Update,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(None)
):
    # 보안: 시크릿 토큰 검증 로그 (토큰 자체는 절대 찍지 않음)
    if settings.WEBHOOK_SECRET_TOKEN:
        if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET_TOKEN:
            logger.warning(f"[Webhook] Unauthorized request: Invalid secret token (Update ID: {update.update_id})")
            raise HTTPException(status_code=403, detail="Invalid secret token")
        logger.debug(f"[Webhook] Secret token verified for update_id: {update.update_id}")

    # 메시지 기본 정보 로깅
    chat_id = "N/A"
    username = "unknown"
    if update.message:
        chat_id = update.message.chat.id
        username = update.message.from_user.username if update.message.from_user else "no-user"

    logger.info(f"[Webhook] Incoming update: {update.update_id} | Chat: {chat_id} | From: @{username}")
    
    # 이미지가 포함된 메시지인 경우 백그라운드에서 처리
    if update.message and update.message.photo:
        logger.info(f"[Webhook] Photo update detected (Photo count: {len(update.message.photo)})")
        background_tasks.add_task(telegram_service.handle_photo_message, update)
    elif update.message and update.message.text:
        logger.info(f"[Webhook] Text update detected: {update.message.text[:50]}...")
    else:
        logger.info(f"[Webhook] Other update type received (id: {update.update_id})")

    return {"ok": True}
