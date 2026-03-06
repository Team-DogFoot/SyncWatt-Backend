import asyncio
import httpx
import logging
import time
from app.schemas.telegram import Update
from app.services.ai.pipeline import pipeline
from app.schemas.ai.diagnosis import DiagnosisResult
from app.services.telegram_client import TelegramClient
from app.services.message_formatter import build_response_message
from app.services.rate_limiter import RateLimiter
from google.adk.runners import InMemoryRunner
from google.genai import types
from sqlmodel import Session
from app.db.session import engine
from app.models.settlement import MonthlySettlement

logger = logging.getLogger(__name__)


class TelegramService:
    """
    텔레그램 봇의 메시지 수신 및 응답을 처리하는 서비스 클래스입니다.
    """
    def __init__(self):
        self.client = TelegramClient()
        self.rate_limiter = RateLimiter()
        # ADK 실행을 위한 Runner 초기화
        self.runner = InMemoryRunner(agent=pipeline)
        self.runner.auto_create_session = True
        logger.info("TelegramService initialized.")

    def _save_settlement_to_db(self, chat_id: int, analysis: DiagnosisResult, settlement_data, market_data: dict):
        """분석 결과를 MonthlySettlement 테이블에 저장합니다."""
        try:
            # settlement_data가 Pydantic 객체일 수 있으므로 속성 접근 사용
            if hasattr(settlement_data, "generation_kwh"):
                gen_kwh = settlement_data.generation_kwh
            elif isinstance(settlement_data, dict):
                gen_kwh = settlement_data.get("generation_kwh", 0)
            else:
                gen_kwh = 0

            with Session(engine) as session:
                new_settlement = MonthlySettlement(
                    telegram_chat_id=str(chat_id),
                    year_month=analysis.year_month,
                    actual_generation_kwh=gen_kwh,
                    actual_revenue_krw=analysis.actual_revenue_krw,
                    smp_avg=market_data.get("curr_smp") if isinstance(market_data, dict) else None,
                    irradiance_avg=market_data.get("curr_irr") if isinstance(market_data, dict) else None,
                    optimal_revenue_krw=analysis.optimal_revenue_krw,
                    opportunity_cost_krw=analysis.opportunity_loss_krw,
                    loss_reason=analysis.loss_cause.value,
                    source="ocr"
                )
                session.add(new_settlement)
                session.commit()
                logger.info(f"[DB] MonthlySettlement saved for chat_id: {chat_id}, month: {analysis.year_month}")
        except Exception as e:
            logger.error(f"[DB] Failed to save settlement: {str(e)}")

    async def handle_text_message(self, update: Update):
        """텍스트 메시지를 수신하여 안내 메시지를 전송합니다."""
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        logger.info(f"[Telegram] Text received (chat_id: {chat_id}): {update.message.text[:50]}")

        await self.client.send_message(
            chat_id,
            "📸 정산서 이미지를 보내주세요!\n사진으로 찍어서 보내주시면 AI가 자동으로 분석해드려요.",
        )

    async def handle_photo_message(self, update: Update):
        """이미지 메시지를 수신하여 분석 파이프라인을 실행합니다."""
        if not update.message or not update.message.photo:
            return

        start_time = time.perf_counter()
        chat_id = update.message.chat.id

        # 레이트 리밋 체크
        if not self.rate_limiter.check(chat_id):
            logger.info(f"[RateLimit] chat_id={chat_id}: daily limit exceeded")
            await self.client.send_message(
                chat_id,
                "📊 오늘 무료 분석 3회를 모두 사용했어요.\n\n"
                "더 자세한 분석과 무제한 이용은 SyncWatt에서!\n"
                "👉 syncwatt.com/signup",
            )
            return

        # 가장 높은 해상도의 사진 선택
        best_photo = update.message.photo[-1]
        file_id = best_photo.file_id
        user_id_str = str(update.message.from_user.id) if update.message.from_user else str(chat_id)
        session_id = f"tg_{chat_id}_{update.message.message_id}"

        logger.info(f"[Telegram] New image received (user: {user_id_str}, session: {session_id})")

        try:
            # 1. 초기 접수 알림 (분석 완료 후 삭제)
            loading_msg_id = await self.client.send_message(chat_id, "🔍 정산서 이미지를 확인했습니다. 분석을 시작합니다... (약 10~15초 소요)")

            # 2. 이미지 다운로드
            image_bytes = await self.client.download_file(file_id)
            
            logger.info(f"[Telegram] Image download complete (size: {len(image_bytes)} bytes)")

            # 2-1. S3에 원본 이미지 백그라운드 저장
            asyncio.create_task(self._save_image_to_s3(image_bytes, chat_id, session_id))

            # 3. ADK 파이프라인 실행 (세션 state 초기화 포함)
            logger.info("[Pipeline] Analysis pipeline starting")
            initial_state = {
                "image_bytes": image_bytes,
                "raw_text": None,
                "settlement_data": None,
                "visual_data": None,
                "market_data": None,
                "diagnosis_calc": None,
                "analysis_result": None,
            }
            async for event in self.runner.run_async(
                user_id=user_id_str,
                session_id=session_id,
                state_delta=initial_state,
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
            settlement_data = session.state.get("settlement_data")
            market_data = session.state.get("market_data")
            
            # 초기 알림 삭제
            if loading_msg_id:
                await self.client.delete_message(chat_id, loading_msg_id)

            if analysis_data:
                # 결과 데이터 파싱 (Pydantic 모델 검증)
                if isinstance(analysis_data, DiagnosisResult):
                    analysis = analysis_data
                else:
                    analysis = DiagnosisResult.model_validate(analysis_data)

                # DB 저장 (예외 격리)
                try:
                    self._save_settlement_to_db(chat_id, analysis, settlement_data, market_data)
                except Exception as e:
                    logger.error(f"[DB] Save failed (message delivery continues): {e}")

                response_text = build_response_message(analysis)

                await self.client.send_message(chat_id, response_text)
                self.rate_limiter.increment(chat_id)
                logger.info(f"[Telegram] Analysis result sent (session: {session_id})")
                logger.info(f"[Final Message Sent to {chat_id}]: {response_text}")

                # 상세 보고서 버튼 (누르면 사전예약 안내로 이어짐)
                await self.client.send_inline_keyboard(
                    chat_id,
                    "더 자세한 분석이 궁금하시다면:",
                    [[{"text": "📊 상세 보고서 보기", "callback_data": "show_report_detail"}]],
                )
            else:
                logger.warning(f"[Telegram] Analysis result missing (session: {session_id})")
                await self.client.send_message(chat_id, "⚠️ 이미지에서 정보를 충분히 읽어내지 못했습니다. 글자가 잘 보이게 다시 찍어서 보내주세요.")

        except httpx.HTTPStatusError as e:
            logger.error(f"[Telegram] API communication error: {str(e)}")
            await self.client.send_message(chat_id, "⚠️ 텔레그램 서버와 통신 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            logger.error(f"[Telegram] Fatal error occurred: {str(e)}", exc_info=True)
            await self.client.send_message(chat_id, "⚠️ 분석 중 예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        finally:
            duration = time.perf_counter() - start_time
            logger.info(f"[Telegram] Total processing time: {duration:.2f}s")

    async def handle_callback_query(self, callback_query):
        """InlineKeyboard 버튼 클릭(callback_query)을 처리합니다."""
        cb_id = callback_query.id
        data = callback_query.data
        chat_id = callback_query.message.chat.id if callback_query.message else None

        if not chat_id:
            return

        logger.info(f"[Telegram] Callback query: chat_id={chat_id}, data={data}")

        try:
            # Telegram callback 응답 (로딩 표시 제거)
            await self.client.answer_callback_query(cb_id)

            if data == "show_report_detail":
                await self.client.send_inline_keyboard(
                    chat_id,
                    "📊 *상세 리포트는 4월에 오픈 예정이에요.*\n오픈 시 알림을 받아보시겠어요?",
                    [[
                        {"text": "알림 받기 ✅", "callback_data": "preregister_yes"},
                        {"text": "괜찮아요", "callback_data": "preregister_no"},
                    ]],
                )
            elif data == "preregister_yes":
                self._save_pre_registration(chat_id)
                await self.client.send_message(
                    chat_id,
                    "✅ 등록 완료! 상세 리포트가 오픈되면 가장 먼저 알려드릴게요."
                )
            elif data == "preregister_no":
                await self.client.send_message(
                    chat_id,
                    "알겠어요. 나중에 언제든 문의해 주세요!"
                )
        except Exception as e:
            logger.error(f"[Telegram] Callback processing failed: {str(e)}", exc_info=True)

    def _save_pre_registration(self, chat_id: int):
        """사전예약 정보를 DB에 저장합니다."""
        from app.models.pre_registration import PreRegistration
        try:
            with Session(engine) as session:
                existing = session.query(PreRegistration).filter(
                    PreRegistration.telegram_chat_id == str(chat_id)
                ).first()
                if existing:
                    logger.info(f"[DB] PreRegistration already exists for chat_id: {chat_id}")
                    return
                reg = PreRegistration(telegram_chat_id=str(chat_id))
                session.add(reg)
                session.commit()
                logger.info(f"[DB] PreRegistration saved for chat_id: {chat_id}")
        except Exception as e:
            logger.error(f"[DB] PreRegistration save failed: {str(e)}")

    @staticmethod
    async def _save_image_to_s3(image_bytes: bytes, chat_id: int, session_id: str):
        """Save image to S3 in background. Failure does not affect analysis."""
        from app.services.external.s3_service import upload_image_to_s3
        try:
            await asyncio.to_thread(upload_image_to_s3, image_bytes, chat_id, session_id)
        except Exception as e:
            logger.error(f"[S3] Background upload failed: {e}")

telegram_service = TelegramService()
