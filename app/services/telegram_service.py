import httpx
import logging
import time
from app.core.config import settings
from app.schemas.telegram import Update
from app.services.ai.pipeline import pipeline
from app.schemas.ai.diagnosis import DiagnosisResult
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
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"{settings.TELEGRAM_API_URL}{self.bot_token}"
        # ADK 실행을 위한 Runner 초기화
        self.runner = InMemoryRunner(agent=pipeline)
        self.runner.auto_create_session = True
        logger.info("TelegramService가 성공적으로 초기화되었습니다.")

    async def send_text_message(self, chat_id: int, text: str) -> int | None:
        """사용자에게 텍스트 메시지를 전송하고 message_id를 반환합니다."""
        try:
            async with httpx.AsyncClient() as client:
                data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
                response = await client.post(f"{self.base_url}/sendMessage", data=data)
                response.raise_for_status()
                msg_id = response.json().get("result", {}).get("message_id")
                logger.debug(f"[Telegram] 메시지 전송 완료 (chat_id: {chat_id}, message_id: {msg_id})")
                return msg_id
        except Exception as e:
            logger.error(f"[Telegram] 메시지 전송 실패: {str(e)}")
            return None

    async def delete_message(self, chat_id: int, message_id: int):
        """텔레그램 메시지를 삭제합니다."""
        try:
            async with httpx.AsyncClient() as client:
                data = {'chat_id': chat_id, 'message_id': message_id}
                response = await client.post(f"{self.base_url}/deleteMessage", data=data)
                response.raise_for_status()
                logger.debug(f"[Telegram] 메시지 삭제 완료 (chat_id: {chat_id}, message_id: {message_id})")
        except Exception as e:
            logger.debug(f"[Telegram] 메시지 삭제 실패 (무시): {str(e)}")

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

    @staticmethod
    def _build_response_message(analysis: DiagnosisResult) -> str:
        """DiagnosisResult를 텔레그램 최종 메시지로 변환합니다."""
        f = format  # shorthand
        loss_val = int(analysis.opportunity_loss_krw)
        loss_abs = f(abs(loss_val), ",")
        optimal = f(int(analysis.optimal_revenue_krw), ",")
        actual = f(int(analysis.actual_revenue_krw), ",")
        gen = f(int(analysis.generation_kwh), ",")
        recovery = int(analysis.potential_recovery_krw) if analysis.potential_recovery_krw else 0

        # ── 헤더 ──
        ym = analysis.year_month
        parts = ym.split("-")
        header = f"📝 *{parts[0]}년 {int(parts[1])}월 정산 분석*" if len(parts) == 2 else f"📝 *{ym} 정산 분석*"

        # ── 이번 달 요약 ──
        summary_lines = [f"• 발전량: {gen} kWh"]

        if analysis.capacity_kw and analysis.utilization_pct is not None:
            cap = f(int(analysis.capacity_kw), ",")
            summary_lines.append(f"• 설비용량 {cap}kW 기준 이용률 {analysis.utilization_pct}%")

        unit_str = f"{analysis.unit_price:.1f}" if analysis.unit_price else "?"
        summary_lines.append(f"• 실제 수령: {actual}원 (단가 {unit_str}원/kWh)")

        smp_str = f"{analysis.curr_smp:.1f}" if analysis.curr_smp else "?"
        summary_lines.append(f"• 전력시장 직접 판매 시(KPX): {optimal}원 (시장가(SMP) 평균 {smp_str}원/kWh)")

        summary = "\n".join(summary_lines)

        # ── 손익 판정 ──
        if loss_val > 0:
            verdict = f"→ 이번 달은 약 *{loss_abs}원*의 기회손실이 있었어요."
        elif loss_val == 0:
            verdict = "→ 이번 달은 전력시장 직접 판매 시와 동일해요."
        else:
            verdict = f"→ 한전 고정단가 계약이 이번달 기준 *{loss_abs}원* 유리했어요."

        # ── 원인 ──
        if loss_val > 0:
            cause_section = f"💡 *주요 원인*\n{analysis.one_line_message}"
        else:
            cause_section = f"💡 *참고*\n이번달 {self._simplify_cause(analysis.one_line_message)} 한전 고정단가가 시장가(SMP)보다 높아 오히려 유리했어요."

        # ── SMP 맥락 ──
        smp_section = ""
        if analysis.smp_context_message:
            smp_section = f"\n\n📈 *알아두시면 좋아요*\n{analysis.smp_context_message}"

        # ── 회수 가능 (손실 양수일 때만) ──
        recovery_section = ""
        if loss_val > 0 and recovery > 0:
            recovery_fmt = f(recovery, ",")
            recovery_section = f"\n\n🔧 이 중 약 *{recovery_fmt}원*은 입찰 예측값 최적화로 회수 가능해요."

        # ── 가입 CTA ──
        cta = (
            "\n\n✅ *가입하면 받을 수 있어요*\n"
            "• 매일 아침 최적 입찰가 추천\n"
            "• 월간 발전소 성적표\n"
            "• 연간 누적 기회비용 분석"
        )

        # ── 위치 안내 ──
        location = ""
        if not analysis.address_used:
            location = "\n\n📍 현재 전국 평균 일조량으로 분석했어요. 위치를 등록하면 우리 발전소 지역 기반 정밀 분석이 가능해요."

        # ── 조립 ──
        msg = (
            f"{header}\n\n"
            f"📊 *이번 달 요약*\n"
            f"{summary}\n"
            f"{verdict}\n\n"
            f"{cause_section}"
            f"{smp_section}"
            f"{recovery_section}"
            f"{cta}"
            f"{location}"
            f"\n\n🔗 [상세 리포트 보기](https://syncwatt.com/report/sample)"
        )
        return msg

    @staticmethod
    def _simplify_cause(one_line: str) -> str:
        """'주요 원인은 ... 때문이에요' → '일조량이 ... 낮았지만,' 형태로 변환합니다."""
        s = one_line.replace("주요 원인은 ", "").replace("이번달 ", "")
        s = s.replace("때문이에요.", "").replace("때문이에요", "")
        s = s.strip()
        if s:
            return f"{s}지만,"
        return ""

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
            # 1. 초기 접수 알림 (분석 완료 후 삭제)
            loading_msg_id = await self.send_text_message(chat_id, "🔍 정산서 이미지를 확인했습니다. 분석을 시작합니다... (약 10~15초 소요)")

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

            # 3. ADK 파이프라인 실행 (세션 state 초기화 포함)
            logger.info("[Pipeline] 분석 파이프라인 가동 시작")
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
                await self.delete_message(chat_id, loading_msg_id)

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
                    logger.error(f"[DB] 저장 실패 (메시지 발송은 계속 진행): {e}")

                response_text = self._build_response_message(analysis)

                await self.send_text_message(chat_id, response_text)
                logger.info(f"[Telegram] 분석 결과 전송 완료 (세션: {session_id})")
                logger.info(f"[Final Message Sent to {chat_id}]: {response_text}")
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
