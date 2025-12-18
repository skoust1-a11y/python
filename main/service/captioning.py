"""Image Captioning Service Module
Handles image captioning operations.

This module provides:
- Caption generation interface for extracted images
"""
import logging
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def generate_caption(image_path: str, prompt: Optional[str] = None) -> str:
    """
    Generate a caption for an image.
    
    Args:
        image_path: Path to the image file
        prompt: Optional custom prompt for caption generation
        
    Returns:
        str: Generated caption text
    """
    logger.info(f"Generating caption for image: {image_path}")
    load_dotenv()

    if prompt is None:
        prompt = (
            "Describe the content and purpose of this image in a concise caption, "
            "focusing on any nutritional or dietary information."
        )

    # TODO: Implement image captioning and return a caption string.
    #
    # 1) Read image bytes
    # with open(image_path, "rb") as f:
    #     image_bytes = f.read()
    #
    # 2) Call your vision model (e.g., Azure OpenAI vision / OpenAI vision)
    # HINT: Provide both the prompt text and the image payload.
    # HINT: If your API expects a data URL, base64-encode the image bytes.
    #
    # 3) Parse response and return caption string
    # caption = ...
    # return caption

    raise NotImplementedError(
        "generate_caption method is not implemented yet. Please complete the implementation."
    )
