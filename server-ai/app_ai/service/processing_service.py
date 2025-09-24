import io
import time
import logging
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

import torch

from app_ai.ai.colorizator import MangaColorizator
from app_ai.ai.denoisator import MangaDenoiser
from app_ai.ai.upscalator import MangaUpscaler
from app_ai.exception.processing_exceptions import InvalidImageError, ImageProcessingError
from app_ai.configuration.config import settings

logger = logging.getLogger(settings.PROJECT_NAME)


# --- Pydantic Model for Processing Options ---
class ProcessingOptions(BaseModel):
    apply_colorize: bool = Field(False, description="Apply colorization")
    apply_upscale: bool = Field(False, description="Apply up-scaling")
    denoise_strength: int = Field(default_factory=lambda: settings.DENOISE_SIGMA)
    upscale_factor: int = Field(default_factory=lambda: settings.UPSCALE_FACTOR)


# --- AI Model Holder (Singleton) ---
class AIModels:
    _instance = None
    colorizer: MangaColorizator | None = None
    upscaler: MangaUpscaler | None = None
    denoiser: MangaDenoiser | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIModels, cls).__new__(cls)
            cls._instance._initialize_models()
        return cls._instance

    def _initialize_models(self):
        logger.info(f"[{settings.PROJECT_NAME}] Initializing AI models on device: {settings.DEVICE}")
        try:
            if settings.COLORIZE_ENABLED:
                logger.info(f"Loading Colorizer model from {settings.COLORIZER_PATH}...")
                colorizer_config = type('ColorizerConfig', (object,),
                                        {'device': settings.DEVICE, 'colorizer_tile_size': settings.COLORIZER_TILE_SIZE,
                                         'tile_pad': settings.TILE_PAD, 'colorizer_path': settings.COLORIZER_PATH})()
                self.colorizer = MangaColorizator(colorizer_config)
            if settings.UPSCALE_ENABLED:
                logger.info(f"Loading Upscaler model from {settings.UPSCALER_PATH}...")
                upscaler_config = type('UpscalerConfig', (object,),
                                       {'device': settings.DEVICE, 'upscaler_tile_size': settings.UPSCALER_TILE_SIZE,
                                        'tile_pad': settings.TILE_PAD, 'upscaler_path': settings.UPSCALER_PATH,
                                        'upscaler_type': settings.UPSCALER_TYPE})()
                self.upscaler = MangaUpscaler(upscaler_config)
            if settings.DENOISE_ENABLED:
                logger.info("Initializing Denoiser...")
                denoiser_config = type('DenoiserConfig', (object,), {'device': settings.DEVICE})()
                self.denoiser = MangaDenoiser(denoiser_config)
            if settings.DEVICE == 'cuda':
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception as e:
            logger.error(f"Error loading AI models: {e}", exc_info=True)
            raise RuntimeError("Failed to load AI models.") from e

    def get_colorizer(self) -> MangaColorizator | None:
        return self.colorizer

    def get_upscaler(self) -> MangaUpscaler | None:
        return self.upscaler

    def get_denoiser(self) -> MangaDenoiser | None:
        return self.denoiser


# Instantiate AIModels once per process
ai_models = AIModels()


# --- ImageProcessor Class ---
class ImageProcessor:
    """Encapsulates the individual steps of the image processing pipeline."""

    def __init__(self, rid: str, options: ProcessingOptions):
        self.rid = rid
        self.options = options
        self.denoiser = ai_models.get_denoiser()
        self.colorizer = ai_models.get_colorizer()
        self.upscaler = ai_models.get_upscaler()

    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        start_time = time.time()
        denoised_image = self.denoiser.denoise(image, self.options.denoise_strength)
        elapsed_time = time.time() - start_time
        logger.info(
            f"[{self.rid}] Denoised image {[*image.shape]} -> {[*denoised_image.shape]} "
            f"in {elapsed_time:.2f} seconds."
        )
        return denoised_image

    def _colorize_image(self, image: np.ndarray) -> np.ndarray:
        start_time = time.time()
        # Convert image to (0-1) float32 for the colorizer
        self.colorizer.set_image((image.astype('float32') / 255), settings.COLORIZED_IMAGE_SIZE)
        colorized_image = self.colorizer.colorize()
        elapsed_time = time.time() - start_time
        logger.info(
            f"[{self.rid}] Colorized image {[*image.shape]} -> {[*colorized_image.shape]} "
            f"in {elapsed_time:.2f} seconds."
        )
        return colorized_image

    def _upscale_image(self, image: np.ndarray) -> np.ndarray:
        start_time = time.time()
        # Convert image to (0-1) float32 for the upscaler
        upscaled_image = self.upscaler.upscale((image.astype('float32') / 255), self.options.upscale_factor)
        elapsed_time = time.time() - start_time
        logger.info(
            f"[{self.rid}] Upscaled (x{self.options.upscale_factor}) image {[*image.shape]} -> {[*upscaled_image.shape]} "
            f"in {elapsed_time:.2f} seconds."
        )
        return upscaled_image

    def run_pipeline(self, initial_image: np.ndarray) -> np.ndarray:
        """Executes the full processing pipeline based on the provided options."""
        processed_image = initial_image

        # Step 1: De-noising (Always Applied)
        if settings.DENOISE_ENABLED and self.denoiser:
            processed_image = self._denoise_image(processed_image)

        # Step 2: Colorization (Conditional)
        if self.options.apply_colorize and settings.COLORIZE_ENABLED and self.colorizer:
            processed_image = self._colorize_image(processed_image)

        # Step 3: Upscaling (Conditional)
        if self.options.apply_upscale and settings.UPSCALE_ENABLED and self.upscaler:
            processed_image = self._upscale_image(processed_image)

        return processed_image


# --- Main Service Function (High-Level Orchestrator) ---
async def process_image(
        image_bytes: bytes,
        options: ProcessingOptions,
        rid: str,
) -> tuple[bytes, int, int]:
    """
    High-level service function to orchestrate the image processing.
    """
    # 1. Load and Prepare Image
    try:
        img_io = io.BytesIO(image_bytes)
        pil_image = Image.open(img_io).convert("RGB")
        original_image_np = np.array(pil_image)

        # Check for pre-colored images
        # coloredness = distance_from_grayscale(original_image_np)
        # if coloredness > 1:
        #     logger.info(f"[{rid}] Image appears to be already colored. Skipping AI processing.")
        #     output_io = io.BytesIO()
        #     pil_image.save(output_io, format="PNG")
        #     output_io.seek(0)
        #     return output_io.getvalue(), pil_image.width, pil_image.height
    except Exception as e:
        logger.error(f"[{rid}] Error loading or preparing image: {e}", exc_info=True)
        raise InvalidImageError(f"Invalid image file or format: {e}")

    # 2. Run the Processing Pipeline
    try:
        processor = ImageProcessor(rid, options)
        processed_image_np = processor.run_pipeline(original_image_np)
    except Exception as e:
        # Catch errors from any step in the pipeline
        logger.error(f"[{rid}] An error occurred during the AI pipeline: {e}", exc_info=True)
        raise ImageProcessingError(f"AI processing pipeline failed: {e}")

    # 3. Format and Return the Result
    try:
        final_pil_image = Image.fromarray(processed_image_np)
        output_io = io.BytesIO()
        final_pil_image.save(output_io, format="PNG")
        output_io.seek(0)

        logger.info(f"[{rid}] Image processing pipeline finished successfully.")
        return output_io.getvalue(), final_pil_image.width, final_pil_image.height
    except Exception as e:
        logger.error(f"[{rid}] Error preparing final image for response: {e}", exc_info=True)
        raise ImageProcessingError(f"Failed to generate output image: {e}")
