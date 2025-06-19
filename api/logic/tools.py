from typing import Optional, Type
from langchain_core.tools import BaseTool, tool
from api.services.web_search import web_search_service

# System prompt that will be added to the conversation to guide the agent
WEB_SEARCH_SYSTEM_PROMPT = """You are an AI assistant with access to web search. 

Use the web search tool when:
- You need current information (events, news, recent developments)
- You need to verify facts or get up-to-date information
- The user asks about something that may have changed recently
- You need more context about a specific topic

When using web search, be specific with your queries to get the most relevant results.
"""

@tool
async def web_search(query: str):
    """
    Performs a web search to find current information on a given topic. 
    
    Use this tool when you need to find up-to-date information, verify facts, 
    or get the latest news on a topic. The search will return relevant web pages 
    that can help answer the user's question.
    
    Args:
        query: The search query to find information about.
        
    Returns:
        str: Search results containing relevant information from the web.
    """
    try:
        return await web_search_service.search(query)
    except Exception as e:
        return f"Error performing web search: {str(e)}"

# This is where we will add more tools like Playwright, Wikipedia, etc.
tools = [web_search]
