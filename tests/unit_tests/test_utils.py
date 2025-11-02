"""Unit tests for utils module."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from react_agent.utils import get_message_text, load_chat_model


class TestGetMessageText:
    """Tests for get_message_text function."""

    def test_get_message_text_with_string_content(self) -> None:
        """Test extracting text from message with string content."""
        msg = HumanMessage(content="Hello world")
        assert get_message_text(msg) == "Hello world"

    def test_get_message_text_with_dict_content(self) -> None:
        """Test extracting text from message with dict content."""
        msg = AIMessage(content=[{"type": "text", "text": "AI response"}])
        assert get_message_text(msg) == "AI response"

    def test_get_message_text_with_dict_content_no_text_key(self) -> None:
        """Test extracting text from dict content without 'text' key."""
        msg = AIMessage(content=[{"type": "image", "data": "..."}])
        assert get_message_text(msg) == ""

    def test_get_message_text_with_list_content(self) -> None:
        """Test extracting text from message with list content."""
        msg = AIMessage(content=["Hello", " ", "world"])
        assert get_message_text(msg) == "Hello world"

    def test_get_message_text_with_list_of_dicts(self) -> None:
        """Test extracting text from message with list of dicts."""
        msg = AIMessage(content=[{"text": "Hello"}, {"text": " world"}])
        assert get_message_text(msg) == "Hello world"

    def test_get_message_text_with_mixed_list(self) -> None:
        """Test extracting text from message with mixed string and dict content."""
        msg = AIMessage(content=["Hello", {"text": " world"}, "!"])
        assert get_message_text(msg) == "Hello world!"

    def test_get_message_text_with_empty_content(self) -> None:
        """Test extracting text from message with empty content."""
        msg = HumanMessage(content="")
        assert get_message_text(msg) == ""

    def test_get_message_text_strips_whitespace(self) -> None:
        """Test that get_message_text strips leading/trailing whitespace."""
        msg = AIMessage(content=["  ", "text", "  "])
        assert get_message_text(msg) == "text"


class TestLoadChatModel:
    """Tests for load_chat_model function."""

    @patch("react_agent.utils.init_chat_model")
    def test_load_chat_model_with_openai(self, mock_init: MagicMock) -> None:
        """Test loading OpenAI model."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model

        result = load_chat_model("openai/gpt-4o-mini")

        mock_init.assert_called_once_with("gpt-4o-mini", model_provider="openai")
        assert result == mock_model

    @patch("react_agent.utils.init_chat_model")
    def test_load_chat_model_with_anthropic(self, mock_init: MagicMock) -> None:
        """Test loading Anthropic model."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model

        result = load_chat_model("anthropic/claude-3-5-sonnet-20241022")

        mock_init.assert_called_once_with(
            "claude-3-5-sonnet-20241022", model_provider="anthropic"
        )
        assert result == mock_model

    @patch("react_agent.utils.init_chat_model")
    def test_load_chat_model_with_fireworks(self, mock_init: MagicMock) -> None:
        """Test loading Fireworks model."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model

        result = load_chat_model("fireworks/accounts/fireworks/models/llama-v3-70b")

        mock_init.assert_called_once_with(
            "accounts/fireworks/models/llama-v3-70b", model_provider="fireworks"
        )
        assert result == mock_model

    def test_load_chat_model_with_invalid_format(self) -> None:
        """Test loading model with invalid format (no slash)."""
        with pytest.raises(ValueError):
            load_chat_model("invalid-model-name")

    @patch("react_agent.utils.init_chat_model")
    def test_load_chat_model_with_multiple_slashes(self, mock_init: MagicMock) -> None:
        """Test loading model with multiple slashes in model name."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model

        result = load_chat_model("provider/path/to/model")

        # Should split only on first slash
        mock_init.assert_called_once_with("path/to/model", model_provider="provider")
        assert result == mock_model
