import httpx
import logging
import time
from app.core.config import settings
from app.schemas.telegram import Update
from app.services.ai.pipeline import pipeline
from app.schemas.ai.diagnosis import DiagnosisResult
from google.adk.runners import InMemoryRunner
from google.genai import types

logger = logging.getLogger(__name__)

class TelegramService:
    """
    텔레그램 봇의 메시지 수신 및 응답을 처리하는 서비스 클래스입니다.
    """
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"{settings.TELEGRAM_API_URL}{self.bot_token}"
        # ADK 실행을 위한 Runner 초기화
        self.runner = InMemoryRunner(agent=pipeline)
        self.runner.auto_create_session = True
        logger.info("TelegramService가 성공적으로 초기화되었습니다.")

    async def send_text_message(self, chat_id: int, text: str):
        """사용자에게 텍스트 메시지를 전송합니다."""
        try:
            async with httpx.AsyncClient() as client:
                data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
                response = await client.post(f"{self.base_url}/sendMessage", data=data)
                response.raise_for_status()
                logger.debug(f"[Telegram] 메시지 전송 완료 (chat_id: {chat_id})")
        except Exception as e:
            logger.error(f"[Telegram] 메시지 전송 실패: {str(e)}")

    async def handle_photo_message(self, update: Update):
        """이미지 메시지를 수신하여 분석 파이프라인을 실행합니다."""
        if not update.message or not update.message.photo:
            return

        start_time = time.perf_counter()
        chat_id = update.message.chat.id
        # 가장 높은 해상도의 사진 선택
        best_photo = update.message.photo[-1]
        file_id = best_photo.file_id
        user_id_str = str(update.message.from_user.id) if update.message.from_user else str(chat_id)
        session_id = f"tg_{chat_id}_{update.message.message_id}"

        logger.info(f"[Telegram] 새 이미지 수신 (사용자: {user_id_str}, 세션: {session_id})")

        try:
            # 1. 초기 접수 알림
            await self.send_text_message(chat_id, "🔍 정산서 이미지를 확인했습니다. 분석을 시작합니다... (약 10~15초 소요)")

            # 2. 이미지 다운로드
            async with httpx.AsyncClient() as client:
                # 파일 경로 획득
                path_resp = await client.get(f"{self.base_url}/getFile", params={"file_id": file_id})
                path_resp.raise_for_status()
                file_path = path_resp.json()["result"]["file_path"]
                
                # 실제 이미지 데이터 다운로드
                download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                img_resp = await client.get(download_url)
                img_resp.raise_for_status()
                image_bytes = img_resp.content
            
            logger.info(f"[Telegram] 이미지 다운로드 완료 (크기: {len(image_bytes)} bytes)")

            # 3. ADK 파이프라인 실행
            logger.info("[Pipeline] 분석 파이프라인 가동 시작")
            async for event in self.runner.run_async(
                user_id=user_id_str,
                session_id=session_id,
                state_delta={"image_bytes": image_bytes},
                new_message=types.UserContent(parts=[types.Part(text="정산서 분석 시작")])
            ):
                logger.debug(f"[Pipeline Event] {event.author}: {event.content}")

            # 4. 분석 결과 추출
            session = await self.runner.session_service.get_session(
                app_name=self.runner.app_name,
                user_id=user_id_str,
                session_id=session_id
            )
            
            analysis_data = session.state.get("analysis_result")
            
            if analysis_data:
                # 결과 데이터 파싱 (Pydantic 모델 검증)
                analysis = DiagnosisResult.model_validate(analysis_data)
                
                # 금액 천단위 콤마 처리
                loss_formatted = format(int(analysis.opportunity_loss_krw), ",")
                
                # PRD 규격에 맞춘 최종 응답 구성
                response_text = (
                    f"📝 *지난달 손실 진단 결과 (이중 검증 완료)*\n\n"
                    f"이번 달은 약 *{loss_formatted}원*의 손실이 발생했습니다.\n\n"
                    f"💡 *진단 원인*\n{analysis.one_line_message}\n\n"
                    f"🔗 [상세 리포트 보기](https://syncwatt.com/report/sample)"
                )
                await self.send_text_message(chat_id, response_text)
                logger.info(f"[Telegram] 분석 결과 전송 완료 (세션: {session_id})")
            else:
                logger.warning(f"[Telegram] 분석 결과 누락 (세션: {session_id})")
                await self.send_text_message(chat_id, "⚠️ 이미지에서 정보를 충분히 읽어내지 못했습니다. 글자가 잘 보이게 다시 찍어서 보내주세요.")

        except httpx.HTTPStatusError as e:
            logger.error(f"[Telegram] API 통신 에러: {str(e)}")
            await self.send_text_message(chat_id, "⚠️ 텔레그램 서버와 통신 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            logger.error(f"[Telegram] 치명적 에러 발생: {str(e)}", exc_info=True)
            await self.send_text_message(chat_id, f"⚠️ 분석 중 예상치 못한 오류가 발생했습니다: {str(e)}")
        finally:
            duration = time.perf_counter() - start_time
            logger.info(f"[Telegram] 전체 처리 시간: {duration:.2f}초")

telegram_service = TelegramService()
