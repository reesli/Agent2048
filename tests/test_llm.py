"""Tests for LLM client: retry, embed cache, batch embed, streaming fallback."""

from unittest.mock import MagicMock, patch

import openai
import pytest

from agent2048.llm import LLMClient, FastEmbedProvider, OpenAIEmbeddingProvider, EmbeddingProvider


class FakeEmbedder:
    """Fake embedder that returns deterministic vectors."""

    def __init__(self):
        self.call_count = 0

    def embed(self, text: str) -> list[float]:
        self.call_count += 1
        # Deterministic embedding based on text hash
        h = hash(text) % 1000
        return [float(h) / 1000.0] * 384


class TestEmbedCache:
    def test_embed_cache_hit(self):
        """Repeated embed calls should use cache, not recompute."""
        client = LLMClient()
        client.embedder = FakeEmbedder()
        client._embed_cache = {}

        text = "hello world"
        result1 = client.embed(text)
        calls_after_first = client.embedder.call_count

        result2 = client.embed(text)
        calls_after_second = client.embedder.call_count

        assert result1 == result2
        assert calls_after_second == calls_after_first, "Cache should prevent second embed call"

    def test_embed_cache_miss_different_text(self):
        """Different text should trigger new embed call."""
        client = LLMClient()
        client.embedder = FakeEmbedder()
        client._embed_cache = {}

        client.embed("text A")
        calls_a = client.embedder.call_count

        client.embed("text B")
        calls_b = client.embedder.call_count

        assert calls_b > calls_a, "Different text should trigger new embed"

    def test_embed_batch_uses_cache(self):
        """embed_batch should use cache for duplicate texts."""
        client = LLMClient()
        client.embedder = FakeEmbedder()
        client._embed_cache = {}

        texts = ["alpha", "beta", "alpha", "gamma", "beta"]
        results = client.embed_batch(texts)

        assert len(results) == 5
        assert results[0] == results[2], "Duplicate 'alpha' should match"
        assert results[1] == results[4], "Duplicate 'beta' should match"


class TestEmbeddingProvider:
    def test_base_embed_raises(self):
        with pytest.raises(NotImplementedError):
            EmbeddingProvider().embed("text")


class TestOpenAIEmbeddingProvider:
    def test_embed_replaces_newlines(self):
        """OpenAIEmbeddingProvider should replace newlines and call API."""
        client = MagicMock()
        resp = MagicMock()
        resp.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        client.embeddings.create.return_value = resp

        provider = OpenAIEmbeddingProvider(client, "text-embedding-3-small")
        result = provider.embed("hello\nworld")

        assert result == [0.1, 0.2, 0.3]
        client.embeddings.create.assert_called_once_with(model="text-embedding-3-small", input="hello world")


class TestFastEmbedProvider:
    def test_embed(self):
        """FastEmbedProvider should wrap fastembed TextEmbedding."""
        fake_model = MagicMock()
        fake_array = MagicMock()
        fake_array.tolist.return_value = [0.1, 0.2, 0.3]
        fake_model.embed.return_value = iter([fake_array])

        with patch("fastembed.TextEmbedding", return_value=fake_model):
            provider = FastEmbedProvider("BAAI/bge-small-en")
            result = provider.embed("hello")

        assert result == [0.1, 0.2, 0.3]
        fake_model.embed.assert_called_once_with("hello")


class TestChatRetry:
    def test_chat_success_no_retry(self):
        """Successful chat should not trigger retry."""
        client = LLMClient()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Hello!"

        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp
        client.model = "test-model"

        result = client.chat([{"role": "user", "content": "hi"}])
        assert result == "Hello!"
        assert client.client.chat.completions.create.call_count == 1

    def test_chat_stream_fallback_on_error(self):
        """chat_stream should fall back to non-streaming on error."""
        client = LLMClient()
        client.model = "test-model"

        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Fallback response"

        client.client = MagicMock()
        # First call (stream=True) raises, second call (stream=False) succeeds
        client.client.chat.completions.create.side_effect = [
            Exception("Streaming not supported"),
            mock_resp,
        ]

        chunks = list(client.chat_stream([{"role": "user", "content": "hi"}]))
        assert chunks == ["Fallback response"]

    def test_chat_stream_fallback_success(self):
        """chat_stream fallback should return non-streaming content."""
        client = LLMClient()
        client.model = "test-model"

        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Non-stream response"

        client.client = MagicMock()
        client.client.chat.completions.create.side_effect = [
            openai.APIConnectionError(message="stream failed", request=MagicMock()),
            mock_resp,
        ]

        chunks = list(client.chat_stream([{"role": "user", "content": "hi"}]))
        assert chunks == ["Non-stream response"]

    def test_chat_stream_success(self):
        """chat_stream should yield chunks when streaming works."""
        client = LLMClient()
        client.model = "test-model"

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " world"

        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None

        client.client = MagicMock()
        client.client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])

        chunks = list(client.chat_stream([{"role": "user", "content": "hi"}]))
        assert chunks == ["Hello", " world"]

    def test_chat_stream_empty_content(self):
        """chat_stream should skip chunks with empty content."""
        client = LLMClient()
        client.model = "test-model"

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = ""

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "hi"

        client.client = MagicMock()
        client.client.chat.completions.create.return_value = iter([chunk1, chunk2])

        chunks = list(client.chat_stream([{"role": "user", "content": "hello"}]))
        assert chunks == ["hi"]


class TestListModels:
    def test_list_models_success(self):
        """list_models should return model IDs from API."""
        client = LLMClient()

        model1 = MagicMock()
        model1.id = "gpt-4o"
        model2 = MagicMock()
        model2.id = "gpt-4o-mini"

        mock_resp = MagicMock()
        mock_resp.data = [model1, model2]

        client.client = MagicMock()
        client.client.models.list.return_value = mock_resp

        models = client.list_models()
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models

    def test_list_models_error(self):
        """list_models should raise RuntimeError on API error."""
        client = LLMClient()
        client.client = MagicMock()
        client.client.models.list.side_effect = Exception("API error")

        with pytest.raises(RuntimeError, match="Failed to list models"):
            client.list_models()


class TestSummarizePair:
    def test_summarize_pair_calls_chat(self):
        """summarize_pair should call chat with merge prompt."""
        client = LLMClient()
        client.model = "test-model"

        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Merged summary"

        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp

        result = client.summarize_pair("fact A", "fact B", level=2)
        assert result == "Merged summary"


class TestReload:
    def test_reload_unknown_provider(self):
        """reload should raise ValueError for unknown embedding provider."""
        client = LLMClient()
        with patch("agent2048.llm.settings") as mock_settings:
            mock_settings.reload.return_value = None
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_base_url = "https://api.openai.com/v1"
            mock_settings.model = "gpt-4o"
            mock_settings.embedding_provider = "unknown"
            mock_settings.embedding_model = "text-embedding-3-small"
            with pytest.raises(ValueError, match="Unknown embedding provider"):
                client.reload()

    def test_reload_fastembed_provider(self):
        """reload should configure FastEmbedProvider when selected."""
        client = LLMClient()
        fake_model = MagicMock()
        fake_array = MagicMock()
        fake_array.tolist.return_value = [0.1] * 384
        fake_model.embed.return_value = iter([fake_array])

        with patch("agent2048.llm.settings") as mock_settings, patch("fastembed.TextEmbedding", return_value=fake_model):
            mock_settings.reload.return_value = None
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_base_url = "https://api.openai.com/v1"
            mock_settings.model = "gpt-4o"
            mock_settings.embedding_provider = "fastembed"
            mock_settings.embedding_model = "BAAI/bge-small-en"
            client.reload()

        assert isinstance(client.embedder, FastEmbedProvider)
        assert client.embedder.embed("test") == [0.1] * 384
