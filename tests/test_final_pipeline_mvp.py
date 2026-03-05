import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from google.adk.runners import InMemoryRunner
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from app.services.ai.pipeline import create_analysis_pipeline
from app.schemas.ai.settlement import SettlementOcrData
from app.schemas.ai.diagnosis import DiagnosisResult, LossCause
from google.adk.agents import LlmAgent

@pytest.mark.asyncio
async def test_full_mvp_pipeline_execution():
    # 1. Setup Mock Data
    image_bytes = b"fake-image-data"
    
    # Mock Vision API response
    mock_vision_response = MagicMock()
    mock_text_annotation = MagicMock()
    mock_text_annotation.description = "2024년 2월 발전량 1200kWh, 총수익 150000원"
    mock_vision_response.text_annotations = [mock_text_annotation]
    
    # Mock External Services for DataFetcherAgent
    mock_irradiance = MagicMock()
    mock_irradiance.avg_irradiance = 15.5
    mock_irradiance.unit = "MJ/m²"
    mock_irradiance.model_dump = MagicMock(return_value={
        "year": 2024, "month": 2, "avg_irradiance": 15.5, "unit": "MJ/m²"
    })
    
    mock_market_data = MagicMock()
    mock_market_data.avg_smp = 180.0
    mock_market_data.avg_rec = 70.0
    mock_market_data.model_dump = MagicMock(return_value={
        "year": 2024, "month": 2, "avg_smp": 180.0, "avg_rec": 70.0
    })

    # 2. Mock Pipeline Components
    with patch('app.services.ai.vision_agent.get_vision_client') as mock_get_client, \
         patch("app.services.external.kma_service.kma_service.get_monthly_avg_irradiance", new_callable=AsyncMock) as mock_kma, \
         patch("app.services.external.kpx_service.kpx_service.get_monthly_avg_prices", new_callable=AsyncMock) as mock_kpx:
        
        mock_vision_client = mock_get_client.return_value
        mock_vision_client.text_detection.return_value = mock_vision_response
        
        mock_kma.return_value = mock_irradiance
        mock_kpx.return_value = mock_market_data
        
        # Mock LlmAgent.run_async to yield final events for ocr_refiner and diagnoser
        async def mock_llm_run_async(self, invocation_context, **kwargs):
            if self.name == "ocr_refiner":
                settlement_data = SettlementOcrData(
                    year_month="2024-02",
                    generation_kwh=1200.0,
                    total_revenue_krw=150000
                )
                yield Event(
                    author=self.name,
                    content=types.Content(parts=[types.Part(text="OCR Refined")]),
                    actions=EventActions(state_delta={"settlement_data": settlement_data}),
                    partial=False
                )
            elif self.name == "diagnoser":
                diagnosis_result = DiagnosisResult(
                    optimal_revenue_krw=180000,
                    opportunity_loss_krw=30000,
                    loss_cause=LossCause.WEATHER,
                    one_line_message="날씨: 이번달 손실 3만원. 일조량이 평균보다 낮았어요."
                )
                yield Event(
                    author=self.name,
                    content=types.Content(parts=[types.Part(text="Diagnosis Complete")]),
                    actions=EventActions(state_delta={"diagnosis_result": diagnosis_result}),
                    partial=False
                )
            else:
                # Fallback to original implementation if any other LlmAgent
                async for event in LlmAgent._run_async_impl(self, invocation_context, **kwargs):
                    yield event

        with patch("google.adk.agents.LlmAgent.run_async", autospec=True, side_effect=mock_llm_run_async):
            # Create the pipeline
            mvp_pipeline = create_analysis_pipeline()
            runner = InMemoryRunner(agent=mvp_pipeline)
            runner.auto_create_session = True
            
            # 3. Run the pipeline
            async for event in runner.run_async(
                user_id="test-user",
                session_id="test-session",
                state_delta={"image_bytes": image_bytes},
                new_message=types.UserContent(parts=[types.Part(text="Analyze this image")])
            ):
                pass
                
            # 4. Assertions
            session = await runner.session_service.get_session(
                app_name=runner.app_name,
                user_id="test-user",
                session_id="test-session"
            )

            # Check raw_text from VisionAgent
            assert session.state["raw_text"] == "2024년 2월 발전량 1200kWh, 총수익 150000원"
            
            # Check settlement_data from ocr_refiner
            assert "settlement_data" in session.state
            assert session.state["settlement_data"].year_month == "2024-02"
            
            # Check market_data from data_fetcher
            assert "market_data" in session.state
            assert session.state["market_data"]["avg_irradiance"] == 15.5
            
            # Check diagnosis_result from diagnoser
            assert "diagnosis_result" in session.state
            diagnosis = session.state["diagnosis_result"]
            assert diagnosis.opportunity_loss_krw == 30000
            assert diagnosis.loss_cause == LossCause.WEATHER
            assert "날씨" in diagnosis.one_line_message
