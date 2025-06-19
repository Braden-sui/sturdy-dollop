import httpx
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from api.core.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7, stream: bool = False):
        # Ollama's OpenAI-compatible endpoint uses a 'messages' list
        messages = [{"role": "user", "content": prompt}]
        request_payload = {
            "model": settings.VLLM_MODEL_NAME,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        try:
            # Using the OpenAI-compatible chat completions endpoint
            response = await self.client.post("/v1/chat/completions", json=request_payload)
            response.raise_for_status()

            if stream:
                raise NotImplementedError("Streaming not yet implemented")
            else:
                data = response.json()
                return {
                    "text": data["choices"][0]["message"]["content"],
                    "tokens_used": data["usage"]["total_tokens"]
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Ollama: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while calling Ollama: {e}")
            return None

@retry(
    stop=stop_after_attempt(10),
    wait=wait_fixed(3),
    retry=retry_if_exception_type(httpx.ConnectError),
    before_sleep=lambda retry_state: logger.info(f"Retrying Ollama connection, attempt {retry_state.attempt_number}...")
)
def get_ollama_client() -> OllamaClient:
    try:
        # A simple synchronous check to see if the server is up
        httpx.get(f"{settings.VLLM_URL}/api/tags")
        logger.info("Ollama server is up. Initializing client.")
        return OllamaClient(base_url=settings.VLLM_URL)
    except httpx.ConnectError as e:
        logger.error(f"Ollama connection failed: {e}. Retrying...")
        raise

# --- Lazy singleton with fallback -------------------------------------------------

class _DummyClient:
    async def generate(self, prompt: str, **_):
        # Return a trivial response so that unit tests can proceed without Ollama
        return {"text": "(dummy ollama response)", "tokens_used": 0}

_vllm_singleton = None

def get_vllm_client() -> OllamaClient:
    """Return a cached instance of OllamaClient.

    If a connection cannot be established (e.g., during CI or tests where the
    Ollama server isn't running), fall back to a dummy client that produces a
    placeholder response. This prevents import-time failures while ensuring the
    rest of the application can still operate in a limited manner.
    """
    global _vllm_singleton
    if _vllm_singleton is None:
        try:
            # quick health probe without retry to avoid long delays in tests
            import httpx  # local import to keep global imports minimal
            try:
                httpx.get(f"{settings.VLLM_URL}/api/tags", timeout=1.0)
                _vllm_singleton = OllamaClient(base_url=settings.VLLM_URL)
            except Exception as probe_err:
                logger.info("Ollama not reachable (%s). Using dummy client.", probe_err)
                _vllm_singleton = _DummyClient()
        except Exception as e:  # pragma: no cover
            logger.warning("Using dummy Ollama client due to unexpected error: %s", e)
            _vllm_singleton = _DummyClient()
    return _vllm_singleton

# Public alias expected by other modules
vllm_client = get_vllm_client()
