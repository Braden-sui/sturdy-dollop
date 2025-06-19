from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    # Optional dependency: allow running without SQLite checkpoint support
    SqliteSaver = None

from api.logic.graph_state import AgentState
from api.logic.graph_nodes import call_model, call_tool, should_continue

import logging
logger = logging.getLogger(__name__)

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

app_graph = None # Will be initialized at FastAPI startup or on first use
_compilation_attempted = False
_last_checkpointer = None

def compile_global_graph(checkpointer_instance):
    """Compile the global conversation graph with checkpointer."""
    global app_graph, _compilation_attempted, _last_checkpointer
    
    _compilation_attempted = True
    _last_checkpointer = checkpointer_instance
    
    logger.info(f"Attempting to compile global graph. Checkpointer provided: {checkpointer_instance is not None}")
    logger.info(f"Workflow object: {workflow}")
    logger.info(f"Graph nodes: agent={call_model}, action={call_tool}, should_continue={should_continue}")
    
    try:
        if checkpointer_instance:
            logger.info("Compiling graph WITH checkpointer")
            app_graph = workflow.compile(checkpointer=checkpointer_instance)
            logger.info(f"Global graph compiled successfully WITH checkpointer: {app_graph}")
        else:
            logger.warning("Compiling global graph WITHOUT checkpointer.")
            app_graph = workflow.compile()
            logger.info(f"Global graph compiled successfully WITHOUT checkpointer: {app_graph}")
            
        # Test that the graph is actually functional
        if app_graph is not None:
            logger.info("Graph compilation completed successfully, app_graph is not None")
        else:
            logger.error("CRITICAL: Graph compilation returned None!")
            
    except Exception as e:
        logger.error(f"Exception during graph compilation: {e}", exc_info=True)
        app_graph = None # Ensure app_graph is None if compilation fails

def get_compiled_graph():
    """Get the compiled graph, compiling it lazily if needed (for TestClient compatibility)."""
    global app_graph, _compilation_attempted
    
    # If graph is already compiled, return it
    if app_graph is not None:
        return app_graph
    
    # If compilation was never attempted (e.g., TestClient), compile without checkpointer
    if not _compilation_attempted:
        logger.warning("Graph not compiled during startup (likely TestClient). Compiling lazily without checkpointer.")
        compile_global_graph(None)
    
    return app_graph
