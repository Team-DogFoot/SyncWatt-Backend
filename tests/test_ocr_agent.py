import pytest
from unittest.mock import MagicMock, AsyncMock, patch
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
        
        # Check if raw_text was passed to ctx.inputs
        assert "raw_text" in ctx.inputs
        assert ctx.inputs["raw_text"] == "sample ocr text"
        
        # Check if instruction contains the placeholder
        assert "{raw_text}" in agent.instruction
