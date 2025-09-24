class AIProcessingBaseError(Exception):
    """Base exception for all errors in the AI processing service."""
    pass


class InvalidImageError(AIProcessingBaseError):
    """Raised when the input image is invalid, corrupt, or has an unsupported format."""
    pass


class ImageProcessingError(AIProcessingBaseError):
    """Raised when a failure occurs during an AI processing step (denoise, colorize, etc.)."""
    pass


class ModelNotLoadedError(AIProcessingBaseError):
    """Raised when an AI model required for a task is not available."""
    pass
