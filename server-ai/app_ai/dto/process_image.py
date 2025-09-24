from pydantic import BaseModel, Field


class ProcessImageRequest(BaseModel):
    image_bytes: bytes = Field(..., description="Raw image data in bytes")
    apply_denoise: bool = Field(False, description="Apply de-noising")
    apply_upscale: bool = Field(False, description="Apply up-scaling")
    apply_colorize: bool = Field(False, description="Apply colorization")
    enable_caching: bool = Field(True, description="Enable caching")

    denoise_strength: int | None = Field(None, description="Blur strength")
    upscale_strength: int | None = Field(None, description="Upscale factor")

    image_name: str | None = Field(None, description="Original image filename")
    image_url: str | None = Field(None, description="Original image URL")

    manga_title: str | None = Field(None, description="Manga series title")
    manga_chapter: str = Field(None, description="Manga chapter number/name")


class ProcessImageResponse(BaseModel):
    image_bytes: str = Field(..., description="Processed image data in bytes")
    processed_width: int = Field(..., description="Width of the processed image in pixels.")
    processed_height: int = Field(..., description="Height of the processed image in pixels.")