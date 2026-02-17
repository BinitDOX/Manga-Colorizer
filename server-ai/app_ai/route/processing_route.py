from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Depends
from fastapi.responses import Response
import logging
from urllib.parse import quote

from app_ai.configuration.config import settings
from app_ai.service.processing_service import process_image, ProcessingOptions
from app_ai.utility.utils import handle_api_errors, generate_random_id

logger = logging.getLogger(settings.PROJECT_NAME)

router = APIRouter()


# --- Dependency for generating a unique request ID ---
async def get_request_id() -> str:
    """A simple dependency to generate a unique ID for each request."""
    return f"REQ-{generate_random_id()}"


@router.post(
    f"{settings.API_V1_STR}/process-image",
    summary="Process (denoise, colorize, upscale) a manga image",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}},
        400: {"description": "Bad Request"},
        424: {"description": "Feature Not Available"},
        500: {"description": "Internal Server Error"},
    })
@handle_api_errors
async def process_image_endpoint(
        # --- Dependencies ---
        rid: str = Depends(get_request_id),

        # --- Form Data ---
        image_file: UploadFile = File(..., description="Manga panel image file"),
        apply_colorize: bool = Form(..., description="Whether to apply colorization."),
        apply_upscale: bool = Form(..., description="Whether to apply upscaling."),
        denoise_strength: int | None = Form(None, description="De-noising sigma value."),
        upscale_factor: int | None = Form(None, description="Upscale factor (2 or 4)."),
        image_name: str | None = Form(None, description="Original image filename for logging."),
        manga_title: str | None = Form(None, description="Manga series title for logging."),
        manga_chapter: str | None = Form(None, description="Manga chapter for logging."),
):
    """
    This endpoint processes an uploaded manga image based on the provided form parameters.
    Error handling is managed by the @handle_api_errors decorator.
    """
    logger.info(f"[{rid}] Incoming request for image processing")
    logger.debug(f"[{rid}] Request params: colorize={apply_colorize}, upscale={apply_upscale}")

    image_bytes = await image_file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty.")

    options_data = {"apply_colorize": apply_colorize, "apply_upscale": apply_upscale}
    if denoise_strength is not None:
        options_data["denoise_strength"] = denoise_strength
    if upscale_factor is not None:
        if upscale_factor not in [2, 4]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="upscale_factor must be 2 or 4.")
        options_data["upscale_factor"] = upscale_factor

    processing_options = ProcessingOptions(**options_data)

    processed_image_bytes, width, height = await process_image(image_bytes, processing_options, rid)

    raw_filename = image_name or image_file.filename or "image.png"
    safe_filename = quote(raw_filename)

    headers = {
        "X-Processed-Width": str(width),
        "X-Processed-Height": str(height),
        "X-Upscale-Applied": "True" if processing_options.apply_upscale else "False",
        "Content-Disposition": f'inline; filename="processed_{safe_filename}"'
    }

    logger.info(f"[{rid}] Image processing completed, returning response with headers.")
    return Response(content=processed_image_bytes, media_type="image/png", headers=headers)
