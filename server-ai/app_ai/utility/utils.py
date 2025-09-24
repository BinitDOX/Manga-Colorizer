import random
import string
from functools import wraps
from fastapi import HTTPException, status

import numpy as np
import PIL.Image
import PIL.ImageChops
import PIL.ImageOps
import torch
import gc
import re
import logging

from app_ai.configuration.config import settings
from app_ai.exception.processing_exceptions import InvalidImageError, ImageProcessingError

logger = logging.getLogger(settings.PROJECT_NAME)


# --- Image Handling Utilities ---
def distance_from_grayscale(image: np.ndarray) -> float:
    """
    Calculates the average color distance of a NumPy array image from its grayscale equivalent.
    A higher value indicates a more colorful image. A value near 0 indicates grayscale.
    """
    try:
        if image.ndim != 3 or image.shape[2] != 3:
            logger.warning("Received an image that is not 3-channel RGB. Returning 0.0.")
            return 0.0

        gray = np.mean(image, axis=2, keepdims=True)
        gray_rgb = np.repeat(gray, 3, axis=2)
        dist = np.abs(image.astype(np.int32) - gray_rgb.astype(np.int32)).mean()
        return float(dist)
    except Exception as e:
        logger.warning(f"Error calculating distance from grayscale: {e}. Returning 0.0", exc_info=True)
        return 0.0


def save_image(image, filename, format="WEBP"):
    image_pil = PIL.Image.fromarray(image)
    image_pil.save(filename, format=format)


# --- Torch/CUDA Utilities ---
def clear_torch_cache():
    """Clears PyTorch CUDA cache and runs garbage collector."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("Cleared PyTorch CUDA cache.")
    gc.collect()
    logger.info("Ran Python garbage collector.")


# --- String Utilities ---
def sanitize_string(s: str) -> str:
    """Sanitizes a string for use in filenames/paths."""
    s = re.sub(r'[^\w\s-]', '', s)
    s = s.replace(' ', '_').replace('-', '_')
    s = re.sub(r'_{2,}', '_', s)
    s = s.strip('_')
    return s


# --- API Utilities ---
def generate_random_id(length=8):
    characters = string.ascii_uppercase + string.digits
    random_id = ''.join(random.choices(characters, k=length))
    return random_id


def handle_api_errors(func):
    """
    A decorator that wraps API endpoint functions to provide standardized error handling.
    It catches specific, custom service-layer exceptions and translates them into FastAPI HTTPExceptions.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        rid = kwargs.get('rid', 'REQ-UNKNOWN')
        try:
            return await func(*args, **kwargs)

        # --- Catch our specific, expected custom exceptions ---

        except InvalidImageError as e:
            logger.warning(f"[{rid}] Invalid image request: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)  # Pass the clear error message to the client
            )

        except ImageProcessingError as e:
            logger.error(f"[{rid}] Internal processing error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred during image processing."  # Keep the client message generic
            )

        # --- Fallback for any other unexpected error ---
        except Exception as e:
            logger.critical(f"[{rid}] An unexpected critical error occurred: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected server error occurred. The team has been notified."
            )

    return wrapper
