"""Google Gemini LLM Provider using Google GenAI SDK."""

import logging
import time
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from src.application.interfaces.llm_provider import ILLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class GeminiLLMProvider(ILLMProvider):
    """Google Gemini LLM provider implementation using GenAI SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """Initialize Gemini LLM provider.

        Args:
            api_key: Google AI Studio API key
            model: Model to use (default: gemini-2.5-flash)
        """
        self._api_key = api_key
        self._model = model
        self._client = genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        """Get provider name identifier."""
        return "gemini"

    @property
    def display_name(self) -> str:
        """Get human-readable provider name."""
        return "Google Gemini"

    @property
    def default_model(self) -> str:
        """Get default model name."""
        return "gemini-2.5-flash"

    async def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 150,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> LLMResponse:
        """Generate response using Gemini API via GenAI SDK.

        Args:
            messages: List of chat messages (conversation history)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 - 1.0)
            response_format: Optional response format ("json" for JSON output)

        Returns:
            LLM response with generated text

        Raises:
            RuntimeError: If API call fails
        """
        start_time = time.perf_counter()

        # Convert messages to GenAI SDK format
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        # Build generation config
        config_kwargs: dict = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        if response_format == "json":
            config_kwargs["response_mime_type"] = "application/json"
            if self._is_thinking_model():
                config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        config = types.GenerateContentConfig(**config_kwargs)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.error("Gemini API failed: %s", e)
            raise RuntimeError("LLM service temporarily unavailable") from e

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract content from response, skipping internal thought parts
        content = ""
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text and not getattr(part, "thought", False):
                        content += part.text

        # Extract token usage if available
        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self._model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response from the LLM via GenAI SDK.

        Args:
            messages: List of chat messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Yields:
            Response text chunks as they are generated

        Raises:
            RuntimeError: If streaming fails
        """
        # Convert messages to GenAI SDK format
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        config_kwargs: dict = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_kwargs)

        try:
            async for chunk in self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config=config,
            ):
                if chunk.candidates and len(chunk.candidates) > 0:
                    candidate = chunk.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                yield part.text
        except Exception as e:
            logger.error("Gemini streaming API failed: %s", e)
            raise RuntimeError("LLM streaming service temporarily unavailable") from e

    def _is_thinking_model(self) -> bool:
        """Return True if this model supports thinkingConfig (gemini-2.5+).

        Only the 2.5 family supports thinking budgets.  Older models (2.0, 1.5)
        will return a 400 error if thinkingConfig is present in the request.
        """
        return "gemini-2.5" in self._model

    async def health_check(self) -> bool:
        """Check if the Gemini API is available.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            test_messages = [LLMMessage(role="user", content="Hi")]
            await self.generate(test_messages, max_tokens=5)
            return True
        except Exception:
            return False
