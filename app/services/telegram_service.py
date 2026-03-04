import httpx
import logging
from app.core.config import settings
from app.schemas.telegram import Update

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"{settings.TELEGRAM_API_URL}{self.bot_token}"

    async def get_file_path(self, file_id: str) -> str:
        """getFile API를 통해 파일의 상대 경로 획득"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getFile", params={"file_id": file_id})
            response.raise_for_status()
            return response.json()["result"]["file_path"]

    async def download_image_to_memory(self, file_path: str) -> bytes:
        """[핵심] 디스크에 저장하지 않고 바이트 데이터를 메모리에 로드"""
        download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url)
            response.raise_for_status()
            # bytes로 리턴하여 메모리에서 처리
            return response.content

    async def send_photo_echo(self, chat_id: int, photo_bytes: bytes):
        """
        [TEST ONLY] 수신 확인용으로 이미지를 다시 사용자에게 전송
        (배포 시/OCR 연동 완료 후 삭제 예정)
        """
        async with httpx.AsyncClient() as client:
            files = {'photo': ('echo_test.jpg', photo_bytes, 'image/jpeg')}
            data = {'chat_id': chat_id, 'caption': "이미지 수신 확인 (In-memory 테스트)"}
            
            response = await client.post(
                f"{self.base_url}/sendPhoto",
                data=data,
                files=files,
                timeout=15.0 # 이미지 업로드 타임아웃 고려
            )
            response.raise_for_status()
            logger.info(f"Test image echoed to chat_id: {chat_id}")

    async def handle_photo_message(self, update: Update):
        """이미지 처리 비즈니스 로직 메인"""
        if not update.message or not update.message.photo:
            return

        chat_id = update.message.chat.id
        # 가장 해상도가 높은 이미지 선택
        best_photo = update.message.photo[-1]
        file_id = best_photo.file_id

        try:
            # 1. 파일 경로 획득
            file_path = await self.get_file_path(file_id)
            # 2. 인메모리 다운로드
            image_bytes = await self.download_image_to_memory(file_path)
            
            logger.info(f"Image processed in-memory: {len(image_bytes)} bytes")
            
            # 3. [TEST] 수신 확인용 Echo 전송 (나중에 삭제 예정)
            await self.send_photo_echo(chat_id, image_bytes)
            
            # TODO: OCR 서비스 연동 로직
            # result = await ocr_service.process(image_bytes)
            
        except Exception as e:
            logger.error(f"Telegram image processing error: {e}")

telegram_service = TelegramService()
