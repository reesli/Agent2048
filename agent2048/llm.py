"""OpenAI-compatible LLM wrapper with pluggable embeddings."""

from collections.abc import Generator
from typing import Any

import httpx
import openai
from openai.types.chat import ChatCompletionMessageParam

from agent2048.config import settings


class EmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, client: openai.OpenAI, model: str):
        self.client = client
        self.model = model

    def embed(self, text: str) -> list[float]:
        text = text.replace("\n", " ")
        resp = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return resp.data[0].embedding


class FastEmbedProvider(EmbeddingProvider):
    def __init__(self, model: str):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model)

    def embed(self, text: str) -> list[float]:
        return list(self.model.embed(text))[0].tolist()


class LLMClient:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        settings.reload()
        self.client = openai.OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.model
        if settings.embedding_provider == "openai":
            self.embedder = OpenAIEmbeddingProvider(self.client, settings.embedding_model)
        elif settings.embedding_provider == "fastembed":
            self.embedder = FastEmbedProvider(settings.embedding_model)
        else:
            raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")

    def chat(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.2,
        max_tokens: int = 8192,
        top_p: float = 0.95,
    ) -> str:
        """Send a chat completion request and return the text content."""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )
        content = resp.choices[0].message.content
        return content or ""

    def chat_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.2,
        max_tokens: int = 8192,
        top_p: float = 0.95,
    ) -> Generator[str, None, None]:
        """Stream chat completion chunks.

        Falls back to non-streaming if the provider does not support streaming.
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception:
            yield self.chat(messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p)

    def list_models(self) -> list[str]:
        """Fetch available models from the current provider's API."""
        try:
            resp = self.client.models.list()
            return [m.id for m in resp.data if hasattr(m, "id")]
        except Exception as e:
            raise RuntimeError(f"Failed to list models: {e}") from e

    def embed(self, text: str) -> list[float]:
        """Embed text using the configured embedding provider.

        Results are cached by text hash to avoid redundant computation.
        """
        import hashlib
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if not hasattr(self, "_embed_cache"):
            self._embed_cache: dict[str, list[float]] = {}
        if cache_key in self._embed_cache:
            return self._embed_cache[cache_key]
        result = self.embedder.embed(text)
        self._embed_cache[cache_key] = result
        return result

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, using cache for duplicates.

        FastEmbed supports batch embedding natively, but this method also
        works with OpenAI embeddings by processing sequentially with cache.
        """
        import hashlib
        if not hasattr(self, "_embed_cache"):
            self._embed_cache: dict[str, list[float]] = {}

        results: list[list[float]] = []
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self._embed_cache:
                results.append(self._embed_cache[cache_key])
            else:
                results.append([])
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            if isinstance(self.embedder, FastEmbedProvider):
                embeddings = list(self.embedder.model.embed(uncached_texts))
                for idx, emb, text in zip(uncached_indices, embeddings, uncached_texts):
                    vec = emb.tolist()
                    cache_key = hashlib.md5(text.encode()).hexdigest()
                    self._embed_cache[cache_key] = vec
                    results[idx] = vec
            else:
                for idx, text in zip(uncached_indices, uncached_texts):
                    vec = self.embedder.embed(text)
                    cache_key = hashlib.md5(text.encode()).hexdigest()
                    self._embed_cache[cache_key] = vec
                    results[idx] = vec

        return results

    def summarize_pair(self, a: str, b: str, level: int) -> str:
        """Ask LLM to merge two memory items into a higher-level abstraction."""
        prompt = f"""You are merging two related memory items into a single higher-level abstraction.

Level of abstraction: {level}

Memory A:
{a}

Memory B:
{b}

Write a concise, clear summary that captures the common pattern or principle. Avoid repeating specific examples unless they are essential. Keep it useful for an AI agent that will read this later to understand the project context.
"""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": "You compress similar memories into reusable abstractions."},
            {"role": "user", "content": prompt},
        ]
        return self.chat(messages)


llm = LLMClient()
