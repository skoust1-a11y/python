"""Embedding generation service — OpenAI and Google GenAI."""

from google.genai import types
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import LLMProviderError
from app.observability.tracing import observe, update_current_generation
from app.utils.google_http import build_google_genai_http_options

SUPPORTED_EMBEDDING_PROVIDERS = frozenset({"openai", "google"})


def normalize_embedding_provider(provider: str) -> str:
    """Normalize embedding provider aliases to canonical names."""
    normalized = provider.strip().lower().replace("-", "_")
    if normalized in {"gemini", "google_genai"}:
        return "google"
    return normalized


class EmbeddingService:
    """Generate text embeddings via OpenAI or Google GenAI."""

    def __init__(self) -> None:
        self._provider = normalize_embedding_provider(settings.EMBEDDING_PROVIDER)
        self._model = self._resolve_model_name()

        if self._provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise LLMProviderError("openai", "OPENAI_API_KEY not configured")
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self._google_embedder: GoogleGenAIEmbedding | None = None
        elif self._provider == "google":
            if not settings.GEMINI_API_KEY:
                raise LLMProviderError("google", "GEMINI_API_KEY not configured")
            self._openai_client = None
            self._google_embedder = GoogleGenAIEmbedding(
                model_name=settings.GEMINI_EMBEDDING_MODEL,
                api_key=settings.GEMINI_API_KEY,
                embedding_config=types.EmbedContentConfig(
                    output_dimensionality=settings.VECTOR_DIMENSION,
                ),
                http_options=build_google_genai_http_options(),
            )
        else:
            raise LLMProviderError(self._provider, "Unknown embedding provider")

    def _resolve_model_name(self) -> str:
        if self._provider == "google":
            return settings.GEMINI_EMBEDDING_MODEL
        return settings.OPENAI_EMBEDDING_MODEL

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return self._provider

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @observe(name="text-embedding", as_type="embedding", capture_input=False, capture_output=False)
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        try:
            if self._provider == "openai":
                vector = (await self._embed_openai([text]))[0]
            else:
                vector = await self._google_embedder.aget_text_embedding(text)  # type: ignore[union-attr]
            update_current_generation(
                input={"text_length": len(text)},
                output={"dimensions": len(vector)},
                model=self._model,
                metadata={"provider": self._provider},
            )
            return vector
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(self._provider, str(exc)) from exc

    @observe(name="text-embedding-batch", as_type="embedding", capture_input=False, capture_output=False)
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, preserving input order."""
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("Cannot embed empty text in batch")

        try:
            if self._provider == "openai":
                vectors = await self._embed_openai(texts)
            else:
                vectors = await self._google_embedder.aget_text_embedding_batch(texts)  # type: ignore[union-attr]
            update_current_generation(
                input={"batch_size": len(texts)},
                output={"dimensions": len(vectors[0]) if vectors else 0},
                model=self._model,
                metadata={"provider": self._provider},
            )
            return vectors
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(self._provider, str(exc)) from exc

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        response = await self._openai_client.embeddings.create(  # type: ignore[union-attr]
            model=self._model,
            input=texts,
            dimensions=settings.VECTOR_DIMENSION,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]
