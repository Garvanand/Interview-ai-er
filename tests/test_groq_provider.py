import os
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from app.ai.providers.groq import GroqProvider
from app.ai.providers import get_ai_provider


class SampleAssessmentSchema(BaseModel):
    score: int
    feedback: str
    strengths: list[str]


def test_groq_provider_init_requires_key():
    with patch.dict(os.environ, {}, clear=True):
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]
        with pytest.raises(ValueError, match="GROQ_API_KEY environment variable is required"):
            GroqProvider()


def test_groq_provider_metadata():
    provider = GroqProvider(api_key="mock_key", model_name="openai/gpt-oss-120b", reasoning_effort="medium")
    meta = provider.get_metadata()
    assert meta["provider"] == "groq"
    assert meta["model_name"] == "openai/gpt-oss-120b"
    assert meta["reasoning_effort"] == "medium"


def test_groq_provider_generate_structured_success():
    provider = GroqProvider(api_key="mock_key", model_name="openai/gpt-oss-120b")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"score": 90, "feedback": "Solid implementation", "strengths": ["Clean logic"]}'
    mock_chat_completion.choices = [mock_choice]

    with patch.object(provider.client.chat.completions, "create", return_value=mock_chat_completion) as mock_create:
        result, telemetry = provider.generate_structured("Evaluate candidate code", SampleAssessmentSchema)
        assert isinstance(result, SampleAssessmentSchema)
        assert result.score == 90
        assert result.feedback == "Solid implementation"
        assert result.strengths == ["Clean logic"]
        assert telemetry.get("schema_validation") is True
        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["model"] == "openai/gpt-oss-120b"
        assert kwargs["response_format"] == {"type": "json_object"}
        assert kwargs["reasoning_effort"] == "medium"


def test_groq_provider_generate_structured_strips_markdown_codeblock():
    provider = GroqProvider(api_key="mock_key", model_name="openai/gpt-oss-120b")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"score": 85, "feedback": "Good", "strengths": []}\n```'
    mock_chat_completion.choices = [mock_choice]

    with patch.object(provider.client.chat.completions, "create", return_value=mock_chat_completion):
        result, telemetry = provider.generate_structured("Evaluate", SampleAssessmentSchema)
        assert result.score == 85
        assert result.feedback == "Good"


def test_groq_provider_stream_completion():
    provider = GroqProvider(api_key="mock_key", model_name="openai/gpt-oss-120b")

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Hello "

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "world!"

    with patch.object(provider.client.chat.completions, "create", return_value=[chunk1, chunk2]):
        tokens = list(provider.stream_completion("Hi"))
        assert tokens == ["Hello ", "world!"]


def test_get_ai_provider_factory_selects_groq():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock_groq_key", "AI_PROVIDER": "groq"}):
        provider = get_ai_provider()
        assert isinstance(provider, GroqProvider)
