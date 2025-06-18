import asyncio
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END

from api.logic.graph_state import AgentState
from api.logic.tools import tools
from api.core.config import settings


async def should_continue(state: AgentState):
    """Determine whether to continue the graph or end."""
    if state["messages"][-1].tool_calls:
        return "action"
    return END


async def call_model(state: AgentState):
    """The 'decide' node. Invokes the LLM to determine the next action."""
    model = ChatOpenAI(api_key="dummy", base_url=f"{settings.VLLM_URL}/v1").bind_tools(tools)
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


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
