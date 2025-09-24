# app_ai/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import torch
import gc

from app_ai.configuration.config import settings
from app_ai.route.processing_route import router as processing_router
from app_ai.service.processing_service import ai_models

logger = logging.getLogger(settings.PROJECT_NAME)

# --- FastAPI App Definition ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI service for Manga Colorization, Denoising, and Upscaling.",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# --- CORS Middleware ---
if settings.ENVIRONMENT == "local":
    if settings.CORS_ORIGINS == "*":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

# --- Include Routers ---
app.include_router(processing_router)


# --- Startup and Shutdown Event Handlers ---
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application startup event triggered.")
    _ = ai_models
    logger.info("AI model initialization check complete.")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleans up resources when the FastAPI application shuts down.
    """
    logger.info("FastAPI application shutdown event triggered.")
    if settings.DEVICE == 'cuda':
        torch.cuda.empty_cache()
    gc.collect()
    logger.info("Resources cleared on shutdown.")


# --- Health check endpoint ---
@app.get("/", summary="Health check endpoint for root path")
@app.get(f"{settings.API_V1_STR}/health", summary="Health check endpoint")
async def health_check():
    logger.info("Health check endpoint hit.")
    return {"status": "ok", "message": f"{settings.PROJECT_NAME} is Up and Running!"}
