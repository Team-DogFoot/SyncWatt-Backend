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
    logger.info(f"Webhook received update_id: {update.update_id}")
    
    # 보안: 텔레그램 설정 시 지정한 시크릿 토큰 검증
    if settings.WEBHOOK_SECRET_TOKEN and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET_TOKEN:
        logger.warning("Invalid secret token received")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # 이미지가 포함된 메시지인 경우 백그라운드에서 처리
    if update.message and update.message.photo:
        logger.info(f"Photo received from chat_id: {update.message.chat.id}")
        background_tasks.add_task(telegram_service.handle_photo_message, update)

    return {"ok": True}
