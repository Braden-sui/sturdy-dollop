from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from api.logic.graph_state import AgentState
from api.logic.graph_nodes import call_model, call_tool, should_continue

# Define the graph workflow
workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool)

# Set the entrypoint
workflow.set_entry_point("agent")

# Add the conditional edge
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "action": "action",
        END: END
    }
)

# Add the normal edge
workflow.add_edge('action', 'agent')

import logging
logger = logging.getLogger(__name__)

app_graph = None # Will be initialized at FastAPI startup

def compile_global_graph(checkpointer_instance):
    global app_graph
    # 'workflow' is defined globally in the preceding part of this file
    
    logger.info(f"Attempting to compile global graph. Checkpointer provided: {checkpointer_instance is not None}")
    try:
        if checkpointer_instance:
            app_graph = workflow.compile(checkpointer=checkpointer_instance)
            logger.info(f"Global graph compiled successfully WITH checkpointer: {app_graph}")
        else:
            logger.warning("Compiling global graph WITHOUT checkpointer.")
            app_graph = workflow.compile()
            logger.info(f"Global graph compiled successfully WITHOUT checkpointer: {app_graph}")
    except Exception as e:
        logger.error(f"Exception during graph compilation: {e}", exc_info=True)
        app_graph = None # Ensure app_graph is None if compilation fails
        raise # Re-raise the exception to make startup fail clearly
