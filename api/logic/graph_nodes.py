import asyncio
from typing import AsyncIterator, Dict, Any
from langchain_core.messages import ToolMessage, AIMessageChunk, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END

from api.logic.graph_state import AgentState
from api.logic.tools import tools
from api.core.config import settings


async def should_continue(state: AgentState):
    """Determine whether to continue the graph or end."""
    # Since Gemma3 doesn't support tools, always end the conversation
    return END


async def call_model(state: AgentState):
    """The 'decide' node. Invokes the LLM to determine the next action."""
    from api.logic.tools import WEB_SEARCH_SYSTEM_PROMPT
    from langchain_core.messages import SystemMessage
    
    model = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_URL,
        temperature=0.7
    )
    
    # Bind tools to the model with better tool descriptions
    model_with_tools = model.bind_tools(
        tools,
        tool_choice="auto"  # Let the model decide when to use tools
    )
    
    # Add system message if this is the first message
    if len(state["messages"]) == 0 or not any(isinstance(m, SystemMessage) for m in state["messages"]):
        state["messages"].insert(0, SystemMessage(content=WEB_SEARCH_SYSTEM_PROMPT))
    
    # For non-streaming, keep the existing behavior
    if not state.get("streaming", False):
        response = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [response], "streaming": False}
    
    # For streaming, return a generator
    async def stream_response() -> AsyncIterator[Dict[str, Any]]:
        full_response = ""
        async for chunk in model_with_tools.astream(state["messages"]):
            if isinstance(chunk, AIMessageChunk):
                content = chunk.content or ""
                full_response += content
                yield {
                    "type": "chunk",
                    "content": content,
                    "done": False,
                    "tool_calls": getattr(chunk, 'tool_calls', None)  # Include any tool calls
                }
        
        # Send final message with full response
        yield {
            "type": "final",
            "content": full_response,
            "done": True,
            "tool_calls": getattr(chunk, 'tool_calls', None) if 'chunk' in locals() else None
        }
    
    return {
        "messages": [],  # Will be populated by the stream
        "streaming": True,
        "stream_generator": stream_response()
    }


async def call_tool(state: AgentState):
    """The 'act' node. Executes tools based on the model's decision."""
    last_message = state["messages"][-1]
    
    # LangGraph can handle multiple tool calls in parallel
    tool_calls = last_message.tool_calls
    
    tool_map = {t.name: t for t in tools}
    
    tasks = []
    for tool_call in tool_calls:
        tool_to_call = tool_map[tool_call["name"]]
        # The tool invocation is now asynchronous
        tasks.append(tool_to_call.ainvoke(tool_call["args"]))
        
    results = await asyncio.gather(*tasks)
    
    tool_messages = [
        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        for result, tool_call in zip(results, tool_calls)
    ]
    
    return {"messages": tool_messages}
