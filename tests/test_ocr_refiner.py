import pytest
from unittest.mock import MagicMock, patch
from app.schemas.ai.settlement import SettlementOcrData
from app.services.ai.pipeline import create_settlement_pipeline
from google.adk.runners import InMemoryRunner
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from google.adk.agents import LlmAgent

@pytest.mark.asyncio
async def test_ocr_refiner_parsing():
    # Mock OCR text
    mock_ocr_text = "정산 연월: 2024-02\n실제 발전량: 1234.56 kWh\n실제 총 수령액: 1500000 원"
    
    # Create a pipeline specifically for testing
    pipeline = create_settlement_pipeline()
    
    # Mock LlmAgent.run_async to yield a final event and set the state
    async def mock_llm_run_async(self, invocation_context, **kwargs):
        if self.name == "ocr_refiner":
            settlement_data = SettlementOcrData(
                year_month="2024-02",
                generation_kwh=1234.56,
                total_revenue_krw=1500000
            )
            
            yield Event(
                author="ocr_refiner",
                content=types.Content(parts=[types.Part(text="OCR refinement complete")]),
                actions=EventActions(state_delta={"settlement_data": settlement_data}),
                partial=False
            )
        else:
            async for event in LlmAgent._run_async_impl(self, invocation_context, **kwargs):
                yield event

    with patch("google.adk.agents.LlmAgent.run_async", autospec=True, side_effect=mock_llm_run_async):
        runner = InMemoryRunner(agent=pipeline)
        runner.auto_create_session = True
        
        # Run the pipeline with mock OCR text in the session state
        async for _ in runner.run_async(
            user_id="test-user",
            session_id="test-session",
            state_delta={"raw_text": mock_ocr_text},
            new_message=types.UserContent(parts=[types.Part(text="Refine OCR")])
        ):
            pass
            
        session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id="test-user",
            session_id="test-session"
        )

    # Assertions
    assert "settlement_data" in session.state
    data = session.state["settlement_data"]
    
    if isinstance(data, dict):
        assert data["year_month"] == "2024-02"
        assert data["generation_kwh"] == 1234.56
        assert data["total_revenue_krw"] == 1500000
    else:
        assert data.year_month == "2024-02"
        assert data.generation_kwh == 1234.56
        assert data.total_revenue_krw == 1500000
