import pytest
from unittest.mock import MagicMock, patch
from google.adk.runners import InMemoryRunner
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from app.services.ai.pipeline import pipeline
from app.schemas.ai.analysis import ImageAnalysisResult
from google.adk.agents import LlmAgent

@pytest.mark.asyncio
async def test_pipeline_execution():
    # Mock image bytes
    image_bytes = b"fake-image-data"
    
    # Mock Vision API response
    mock_vision_response = MagicMock()
    mock_text_annotation = MagicMock()
    mock_text_annotation.description = "Extracted text from image"
    mock_vision_response.text_annotations = [mock_text_annotation]
    
    # We mock the singleton client provider
    with patch('app.services.ai.vision_agent.get_vision_client') as mock_get_client:
        mock_vision_client = mock_get_client.return_value
        mock_vision_client.text_detection.return_value = mock_vision_response
        
        # Mock LlmAgent.run_async to yield a final event and set the state
        async def mock_llm_run_async(self, invocation_context, **kwargs):
            if self.name == "analyzer":
                analysis_result = ImageAnalysisResult(
                    summary="This is a summary",
                    extracted_data={"key": "value"},
                    detected_language="ko"
                )
                
                # Yield an event with state_delta as expected by ADK
                yield Event(
                    author="analyzer",
                    content=types.Content(parts=[types.Part(text="Analysis complete")]),
                    actions=EventActions(state_delta={"analysis_result": analysis_result}),
                    partial=False
                )
            else:
                async for event in LlmAgent._run_async_impl(self, invocation_context, **kwargs):
                    yield event

        with patch("google.adk.agents.LlmAgent.run_async", autospec=True, side_effect=mock_llm_run_async):
            runner = InMemoryRunner(agent=pipeline)
            runner.auto_create_session = True
            
            # Run the pipeline via runner
            async for event in runner.run_async(
                user_id="test-user",
                session_id="test-session",
                state_delta={"image_bytes": image_bytes},
                new_message=types.UserContent(parts=[types.Part(text="Analyze")])
            ):
                pass
                
            # Get session from runner's session service
            session = await runner.session_service.get_session(
                app_name=runner.app_name,
                user_id="test-user",
                session_id="test-session"
            )

            # Assertions
            assert session.state["raw_text"] == "Extracted text from image"
            assert "analysis_result" in session.state
            analysis = session.state["analysis_result"]
            if isinstance(analysis, dict):
                assert analysis["summary"] == "This is a summary"
                assert analysis["detected_language"] == "ko"
            else:
                assert analysis.summary == "This is a summary"
                assert analysis.detected_language == "ko"
