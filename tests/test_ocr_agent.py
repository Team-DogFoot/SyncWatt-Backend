import pytest
from unittest.mock import MagicMock, patch
from app.services.ai.agents.ocr_agent import OcrRefinerAgent

@pytest.mark.asyncio
async def test_ocr_agent_passes_raw_text():
    agent = OcrRefinerAgent()
    ctx = MagicMock()
    ctx.session.state = {"raw_text": "sample ocr text"}
    ctx.inputs = {}
    
    with patch("google.adk.agents.LlmAgent._run_async_impl") as mock_super:
        async def mock_gen(*args, **kwargs):
            mock_event = MagicMock()
            mock_event.partial = False
            yield mock_event
            
        mock_super.side_effect = mock_gen
        
        async for _ in agent._run_async_impl(ctx):
            pass
        
        # Verify super()._run_async_impl(ctx) is called
        # LlmAgent will use session.state.get("raw_text") for the template
        assert ctx.session.state["raw_text"] == "sample ocr text"
        assert mock_super.called

