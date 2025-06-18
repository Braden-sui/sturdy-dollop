from langchain_core.tools import tool
from api.services.web_search import web_search_service

@tool
async def web_search(query: str):
    """Perform a web search to find information on a given topic."""
    return await web_search_service.search(query)

# This is where we will add more tools like Playwright, Wikipedia, etc.
tools = [web_search]
