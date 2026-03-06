import logging
import time
from google.adk.agents import BaseAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.services.ai.utils import create_text_event

logger = logging.getLogger(__name__)

class CodeVerifierAgent(BaseAgent):
    """
    Python 코드를 사용하여 OCR 추출 결과와 시각 분석 결과를 수치적으로 검증하고 
    최적의 데이터를 선택하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="code_verifier",
            description="Verifies and selects the best settlement data using Python logic."
        )

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] Starting code-based data verification")

        ocr_data_dict = ctx.session.state.get("settlement_data")
        visual_data_dict = ctx.session.state.get("visual_data")

        # 딕셔너리 또는 Pydantic 객체 대응
        ocr = self._to_model(ocr_data_dict)
        visual = self._to_model(visual_data_dict)

        logger.info(f"[{self.name}] OCR Data: {ocr}")
        logger.info(f"[{self.name}] Visual Data: {visual}")

        # 필드별 차이점 비교 로그 추가
        if ocr and visual:
            diffs = []
            if ocr.year_month != visual.year_month:
                diffs.append(f"year_month ({ocr.year_month} vs {visual.year_month})")
            if ocr.generation_kwh != visual.generation_kwh:
                diffs.append(f"generation_kwh ({ocr.generation_kwh} vs {visual.generation_kwh})")
            if ocr.total_revenue_krw != visual.total_revenue_krw:
                diffs.append(f"total_revenue_krw ({ocr.total_revenue_krw} vs {visual.total_revenue_krw})")
            if diffs:
                logger.info(f"[{self.name}] [Data Discrepancy Found]: {', '.join(diffs)}")
            else:
                logger.info(f"[{self.name}] [Data Match]: OCR and Visual results are identical.")

        final_choice = None
        reason = ""

        if not ocr and not visual:
            reason = "둘 다 데이터를 추출하지 못했습니다."
        elif ocr and not visual:
            final_choice = ocr
            reason = "시각 분석 결과가 없어 OCR 결과를 채택했습니다."
        elif visual and not ocr:
            final_choice = visual
            reason = "OCR 결과가 없어 시각 분석 결과를 채택했습니다."
        else:
            # 둘 다 있는 경우 수치 정합성 체크
            ocr_valid = self._check_integrity(ocr)
            visual_valid = self._check_integrity(visual)

            if ocr_valid and not visual_valid:
                final_choice = ocr
                reason = "수치 정합성이 맞는 OCR 결과를 채택했습니다."
            elif visual_valid and not ocr_valid:
                final_choice = visual
                reason = "수치 정합성이 맞는 시각 분석 결과를 채택했습니다."
            elif self._is_same(ocr, visual):
                final_choice = ocr
                reason = "두 결과가 주요 필드에서 일치하여 채택했습니다."
            else:
                # 둘 다 정합성이 맞거나 둘 다 틀린 경우 -> 오차가 더 적은 것 선택
                ocr_diff = self._get_integrity_diff(ocr)
                vis_diff = self._get_integrity_diff(visual)
                
                if ocr_diff <= vis_diff:
                    final_choice = ocr
                    reason = f"두 결과가 다르므로 수치 오차가 더 적은 OCR 결과를 채택했습니다 (OCR 오차: {ocr_diff:.0f}, Visual 오차: {vis_diff:.0f})."
                else:
                    final_choice = visual
                    reason = f"두 결과가 다르므로 수치 오차가 더 적은 시각 분석 결과를 채택했습니다 (OCR 오차: {ocr_diff:.0f}, Visual 오차: {vis_diff:.0f})."

        if final_choice:
            # 보조 필드 보정: capacity_kw가 비정상이면 다른 결과에서 가져오기
            if ocr and visual:
                self._merge_auxiliary_fields(final_choice, ocr, visual)

            final_choice.selection_reason = reason
            logger.info(f"[{self.name}] Final selection: {final_choice.model_dump()}, reason: {reason}")
            
            yield create_text_event(
                self.name,
                f"데이터 검증 완료: {reason}",
                state_delta={"settlement_data": final_choice}
            )
        else:
            logger.error(f"[{self.name}] Verification failed: no valid data found")
            yield create_text_event(self.name, "데이터 검증 중 오류가 발생했습니다. 유효한 정보를 찾을 수 없습니다.")

        duration = time.perf_counter() - start_t
        logger.info(f"[{self.name}] Verification complete ({duration:.2f}s)")

    def _to_model(self, data):
        if not data:
            return None
        try:
            if isinstance(data, SettlementOcrData):
                return data
            return SettlementOcrData.model_validate(data)
        except Exception:
            return None

    def _is_same(self, ocr: SettlementOcrData, visual: SettlementOcrData) -> bool:
        """
        주요 필드(연월, 발전량, 총 수령액)가 일치하는지 확인합니다.
        """
        return (
            ocr.year_month == visual.year_month and
            ocr.generation_kwh == visual.generation_kwh and
            ocr.total_revenue_krw == visual.total_revenue_krw
        )

    def _get_integrity_diff(self, data: SettlementOcrData) -> float:
        """
        수치 정합성 오차를 계산합니다.
        """
        if not data.unit_price or not data.generation_kwh or not data.total_revenue_krw:
            return float('inf')
        expected_revenue = data.unit_price * data.generation_kwh
        return abs(expected_revenue - data.total_revenue_krw)

    def _merge_auxiliary_fields(self, final: SettlementOcrData, ocr: SettlementOcrData, visual: SettlementOcrData):
        """보조 필드(capacity_kw, address)를 두 결과에서 가장 합리적인 값으로 보정합니다."""
        # capacity_kw: 1kW 미만은 비정상 (단위 오류), 더 큰 쪽 채택
        ocr_cap = ocr.capacity_kw or 0
        vis_cap = visual.capacity_kw or 0
        if ocr_cap > 0 or vis_cap > 0:
            best_cap = max(ocr_cap, vis_cap) if max(ocr_cap, vis_cap) >= 1 else None
            if best_cap != final.capacity_kw:
                logger.info(f"[{self.name}] capacity_kw corrected: {final.capacity_kw} -> {best_cap}")
                final.capacity_kw = best_cap

        # address: 없으면 다른 쪽에서 가져오기
        if not final.address:
            other = visual if final is ocr else ocr
            if other.address:
                final.address = other.address

        # issuer: 없으면 다른 쪽에서 가져오기
        if not final.issuer:
            other = visual if final is ocr else ocr
            if other.issuer:
                final.issuer = other.issuer

    def _check_integrity(self, data: SettlementOcrData) -> bool:
        """
        단가 * 발전량 ≈ 총 수령액(공급가액) 인지 확인합니다.
        오차 범위: max(1000, 총 수령액 * 0.02) 이내면 정상으로 판단합니다.
        """
        if not data.unit_price or not data.generation_kwh or not data.total_revenue_krw:
            logger.info(f"[{self.name}] [Integrity Check Skip]: Missing required fields for calculation.")
            return False
        
        diff = self._get_integrity_diff(data)
        tolerance = max(1000, data.total_revenue_krw * 0.02)
        
        is_valid = diff <= tolerance
        logger.info(f"[{self.name}] [Integrity Check]: Diff: {diff:.0f}, Tolerance: {tolerance:.0f} -> Valid: {is_valid}")
        return is_valid
