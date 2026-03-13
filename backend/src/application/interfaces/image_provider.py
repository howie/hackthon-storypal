"""Image Provider Interface (Port)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ImageGenerationResult:
    """Result from image generation API."""

    image_bytes: bytes
    mime_type: str
    provider: str
    model: str
    latency_ms: int


class IImageProvider(ABC):
    """Abstract interface for image generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get provider name identifier (e.g., 'gemini-imagen')."""
        ...

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
    ) -> ImageGenerationResult:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate.
            aspect_ratio: Aspect ratio (e.g. '1:1', '16:9').

        Returns:
            Image generation result with raw bytes.

        Raises:
            ImageProviderError: If generation fails.
        """
        ...
