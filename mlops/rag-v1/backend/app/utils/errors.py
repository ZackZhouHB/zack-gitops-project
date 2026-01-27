"""Retry logic and error handling utilities"""
import asyncio
import logging
from functools import wraps
from typing import Type, Tuple

logger = logging.getLogger(__name__)

class RetryConfig:
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    EXPONENTIAL_BASE = 2

def retry_async(
    retries: int = RetryConfig.MAX_RETRIES,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    exponential_backoff: bool = True
):
    """Decorator for async retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:
                        delay = RetryConfig.BASE_DELAY * (
                            RetryConfig.EXPONENTIAL_BASE ** attempt if exponential_backoff else 1
                        )
                        logger.warning(f"{func.__name__} failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator

class RAGError(Exception):
    """Base exception for RAG errors"""
    pass

class EmbeddingError(RAGError):
    """Error during embedding generation"""
    pass

class RetrievalError(RAGError):
    """Error during document retrieval"""
    pass

class GenerationError(RAGError):
    """Error during LLM generation"""
    pass

def handle_bedrock_error(e: Exception) -> RAGError:
    """Convert Bedrock errors to RAG errors"""
    error_str = str(e)
    if "ThrottlingException" in error_str:
        return RAGError("Service is busy, please retry")
    if "ValidationException" in error_str:
        return RAGError("Invalid model configuration")
    if "AccessDeniedException" in error_str:
        return RAGError("Model access not enabled")
    return RAGError(f"Service error: {error_str}")
