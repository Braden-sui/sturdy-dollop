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

# Singleton instance of the client, initialized with retry logic
vllm_client = get_ollama_client()
