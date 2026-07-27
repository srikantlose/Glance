from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.adapters.errors import AdapterError
from app.config import ADAPTER_MAX_RETRIES


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, AdapterError):
        return exc.retryable
    return True


# 0.5s / 1s / 2s per the spec's retry constants
with_retry = retry(
    reraise=True,
    stop=stop_after_attempt(ADAPTER_MAX_RETRIES),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception(_is_retryable),
)
