import logging
import os
import warnings
from typing import Literal, Any

import torch
from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Basic Logging Setup ---
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(name)s | %(levelname)-8s | [%(funcName)-20s:%(lineno)-3d] | %(message)s"
)
logger = logging.getLogger(__name__)


# --- Environment File Loader ---
def _get_env_file() -> str | None:
    env = os.getenv("ENVIRONMENT", "local").lower()
    if env == "production":
        return None
    return os.path.join(os.path.dirname(__file__), f"envs/.env.{env}")


# --- Settings Class ---
class Settings(BaseSettings):
    """Configuration for the Manga Colorizer AI Service."""
    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    # --- Core Application ---
    PROJECT_NAME: str = "Manga Colorizer AI Service"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "development", "staging", "production"] = "local"
    CORS_ORIGINS: list[HttpUrl] | str = "*"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- AI Model Settings ---
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    COLORIZER_PATH: str = "app_ai/ai/networks/generator.zip"
    UPSCALER_PATH: str = "app_ai/ai/networks/RealESRGAN_x4plus_anime_6B.pt"
    EXTRACTOR_PATH: str = "app_ai/ai/networks/extractor.pth"

    COLORIZE_ENABLED: bool = True
    UPSCALE_ENABLED: bool = True
    DENOISE_ENABLED: bool = True

    UPSCALER_TYPE: Literal["ESRGAN", "GigaGAN"] = "ESRGAN"
    COLORIZER_TILE_SIZE: int = 0
    UPSCALER_TILE_SIZE: int = 256
    TILE_PAD: int = 8
    COLORIZED_IMAGE_SIZE: int = 576
    UPSCALE_FACTOR: Literal[2, 4] = 4
    DENOISE_SIGMA: int = 25

    # --- Validation ---
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v: Any) -> list[str] | str:
        if isinstance(v, str) and "," in v:
            return [uri.strip() for uri in v.split(",")]
        return v

    @field_validator("UPSCALE_FACTOR", mode="before")
    def parse_upscale_factor(cls, v):
        return int(v)

    def model_post_init(self, __context: Any) -> None:
        # Validate UPSCALE_FACTOR
        if self.UPSCALE_FACTOR not in [2, 4]:
            warnings.warn(f"Invalid UPSCALE_FACTOR: {self.UPSCALE_FACTOR}. Defaulting to 4.", UserWarning)
            self.UPSCALE_FACTOR = 4

        # Validate UPSCALER_TYPE
        if self.UPSCALER_TYPE not in ["ESRGAN", "GigaGAN"]:
            warnings.warn(f"Invalid UPSCALER_TYPE: {self.UPSCALER_TYPE}. Defaulting to ESRGAN.", UserWarning)
            self.UPSCALER_TYPE = "ESRGAN"

        # Ensure CUDA device availability
        if self.DEVICE == "cuda" and not torch.cuda.is_available():
            warnings.warn("CUDA requested but not available. Falling back to CPU.", UserWarning)
            self.DEVICE = "cpu"

        self._setup_logging()

    def _setup_logging(self):
        logging.getLogger().setLevel(self.LOG_LEVEL)
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(self.LOG_LEVEL)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        warnings.filterwarnings("ignore", category=UserWarning)


# --- Single Instance ---
try:
    settings = Settings()
except Exception as e:
    logger.critical(f"FATAL: Could not load settings. Error: {e}", exc_info=True)
    raise SystemExit(f"Configuration Error: {e}")

