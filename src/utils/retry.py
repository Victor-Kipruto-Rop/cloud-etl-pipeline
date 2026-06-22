import functools
import logging
import time

logger = logging.getLogger(__name__)


def retry(exceptions=(Exception,), retries=3, base_delay=1.0, backoff=2.0):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries:
                        logger.error(f"Retry exhausted for {func.__name__}: {e}")
                        raise
                    logger.warning(
                        f"Attempt {attempt} for {func.__name__} failed: {e}; retrying in {delay}s"
                    )
                    time.sleep(delay)
                    delay *= backoff

        return wrapper

    return deco
