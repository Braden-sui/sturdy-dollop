import logging
from duckduckgo_search import DDGS
import httpx
from api.core.config import settings
from api.services.redis_client import redis_client

logger = logging.getLogger(__name__)

# Cache search results for 1 hour
CACHE_TTL_SECONDS = 3600

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        self.ddgs = DDGS()

    async def search(self, query: str, max_results: int = 5):
        cache_key = f"web_search:{query}:{max_results}"
        cached_results = await redis_client.get(cache_key)
        if cached_results:
            logger.info(f"Returning cached search results for query: {query}")
            return cached_results

        logger.info(f"No cache found. Performing live search for: {query}")
        results = await self._perform_live_search(query, max_results)

        if results:
            await redis_client.set(cache_key, results, ttl_seconds=CACHE_TTL_SECONDS)
        
        return results

    async def _perform_live_search(self, query: str, max_results: int = 5):
        # 1. Primary: DuckDuckGo
        try:
            logger.info(f"Searching with DuckDuckGo for: {query}")
            results = self.ddgs.text(query, max_results=max_results)
            if results:
                return [{"snippet": r['body'], "link": r['href']} for r in results]
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}. Falling back.")

        # 2. Secondary: SearxNG
        try:
            logger.info(f"Searching with SearxNG for: {query}")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    settings.SEARXNG_URL,
                    params={"q": query, "format": "json"}
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                if results:
                    return [{"snippet": r.get('content', ''), "link": r.get('url', '')} for r in results[:max_results]]
        except Exception as e:
            logger.warning(f"SearxNG search failed: {e}. Falling back.")

        # 3. Tertiary: Brave Search API
        if settings.BRAVE_API_KEY:
            try:
                logger.info(f"Searching with Brave for: {query}")
                headers = {"X-Subscription-Token": settings.BRAVE_API_KEY}
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://api.search.brave.com/res/v1/web/search?q={query}",
                        headers=headers
                    )
                    response.raise_for_status()
                    results = response.json().get('web', {}).get('results', [])
                    if results:
                        return [{"snippet": r.get('description', ''), "link": r.get('url', '')} for r in results[:max_results]]
            except Exception as e:
                logger.error(f"Brave Search failed: {e}")

        logger.error(f"All web search providers failed for query: {query}")
        return []

web_search_service = WebSearchService()

