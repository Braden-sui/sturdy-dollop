from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from api.v1.schemas.simulate import (
    SimulateStartRequest, SimulateStartResponse,
    SimulateMessageRequest, SimulateMessageResponse,
    SimulateStatusResponse,
    # Updated and new Memory Schemas
    MemoryAddRequest, MemoryAddResponse,
    MemoryResponse, MemoryListResponse,
    MemoryUpdateRequest, MemoryUpdateResponse,
    MemoryDeleteResponse, MemoryHistoryResponse, MemoryMessage
)
import uuid
import time
from api.services.vllm_client import vllm_client
from api.services.memory_client import memory_client
from api.services.session_manager import session_manager
from api.logic import conversation_graph
from langchain_core.messages import HumanMessage
from api.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/simulate/start", response_model=SimulateStartResponse)
async def start_simulation(request: SimulateStartRequest):
    try:
        session_id = session_manager.create_session(user_id=request.user_id, mode=request.mode)
        # Each session has a unique graph config
        config = {"configurable": {"thread_id": str(session_id)}}
        session_manager.get_session(session_id)['graph_config'] = config

        return SimulateStartResponse(
            session_id=session_id,
            status="initialized",
            model_loaded=settings.OLLAMA_MODEL
        )
    except Exception as e:
        logger.error(f"Error in start_simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/simulate/{session_id}/message", response_model=SimulateMessageResponse)
async def post_message(
    session_id: uuid.UUID, 
    request: SimulateMessageRequest,
    stream: bool = False
):
    try:
        session = session_manager.get_session(session_id)
        if not session or 'graph_config' not in session:
            logger.error(f"Session {session_id} not found or not initialized")
            raise HTTPException(status_code=404, detail="Session not found or not initialized")

        # Get the app_graph dynamically to avoid import timing issues
        logger.info("Getting app_graph from conversation_graph module...")
        app_graph = conversation_graph.get_compiled_graph()
        logger.info(f"app_graph retrieved: {app_graph}")
        
        if app_graph is None:
            logger.error("CRITICAL: Conversation graph not initialized - app_graph is None")
            raise HTTPException(status_code=500, detail="Conversation graph not initialized")

        start_time = time.time()

        # 1. Search for relevant memories
        logger.info(f"Searching for memories for user_id: {session['user_id']}")
        try:
            relevant_memories = await memory_client.search_memory(user_id=session['user_id'], query=request.content)
            logger.info(f"Found {len(relevant_memories) if relevant_memories else 0} relevant memories")
        except Exception as e:
            logger.error(f"Memory search failed: {e}", exc_info=True)
            relevant_memories = []  # Continue without memories if search fails
        
        # 2. Construct the initial messages for the graph
        logger.info("Constructing graph input messages...")
        graph_input_messages = []
        if relevant_memories:
            memory_str = "You have the following relevant memories:\n"
            for mem in relevant_memories:
                memory_content = mem.get('text', '') if isinstance(mem, dict) else getattr(mem, 'text', '')
                if memory_content:
                    memory_str += f"- {memory_content}\n"
            if len(memory_str) > len("You have the following relevant memories:\n"):
                 graph_input_messages.append(HumanMessage(content=memory_str))
        
        graph_input_messages.append(HumanMessage(content=request.content))
        logger.info(f"Created {len(graph_input_messages)} input messages for graph")

        # 3. Prepare the state with streaming flag
        state = {
            "messages": graph_input_messages,
            "streaming": stream
        }

        # For streaming responses
        if stream:
            from fastapi.responses import StreamingResponse
            
            async def stream_response():
                try:
                    # Invoke the graph
                    logger.info("Invoking graph with streaming enabled")
                    result = await app_graph.ainvoke(state, config=session['graph_config'])
                    
                    if "stream_generator" in result:
                        full_response = ""
                        async for chunk in result["stream_generator"]:
                            if chunk["type"] == "chunk":
                                content = chunk["content"]
                                full_response += content
                                yield f"data: {content}\n\n"
                            elif chunk["type"] == "final":
                                # Store the conversation in memory
                                try:
                                    conversation_to_log = [
                                        MemoryMessage(role="user", content=request.content).model_dump(),
                                        MemoryMessage(role="assistant", content=full_response).model_dump()
                                    ]
                                    await memory_client.add_memory(
                                        user_id=session['user_id'], 
                                        messages=conversation_to_log
                                    )
                                    logger.info("Memory stored successfully")
                                except Exception as e:
                                    logger.error(f"Memory storage failed: {e}", exc_info=True)
                                
                                # Update session with the new message exchange
                                try:
                                    session_manager.update_history(session_id, request.content, full_response)
                                    await session_manager.update_session(session_id, {
                                        'last_activity': int(time.time()),
                                        'message_count': session.get('message_count', 0) + 1
                                    })
                                    logger.info("Session updated successfully")
                                except Exception as e:
                                    logger.error(f"Session update failed: {e}", exc_info=True)
                                
                                break
                        
                        logger.info("Streaming completed successfully")
                except Exception as e:
                    logger.error(f"Error in streaming response: {e}", exc_info=True)
                    yield f"data: [ERROR] {str(e)}\n\n"
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # For non-streaming responses
        else:
            # 3. Invoke the graph
            logger.info("Preparing to invoke graph...")
            inputs = {"messages": graph_input_messages, "streaming": False}
            logger.info(f"Graph inputs: {inputs}")
            logger.info(f"Session graph config: {session['graph_config']}")
            
            try:
                logger.info("Calling app_graph.ainvoke...")
                graph_result = await app_graph.ainvoke(inputs, config=session['graph_config'])
                logger.info(f"Graph invocation completed successfully: {type(graph_result)}")
            except Exception as e:
                logger.error(f"Graph invocation failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Graph invocation failed: {str(e)}")
            
            # 4. Extract AI response
            logger.info("Extracting AI response from graph result...")
            try:
                ai_response_message = graph_result['messages'][-1]
                ai_response_content = ai_response_message.content if hasattr(ai_response_message, 'content') else str(ai_response_message)
                logger.info(f"AI response extracted: {ai_response_content[:100]}...")
            except Exception as e:
                logger.error(f"Failed to extract AI response: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to extract AI response: {str(e)}")

            # 5. Store the conversation in memory
            logger.info("Storing conversation in memory...")
            try:
                conversation_to_log = [
                    MemoryMessage(role="user", content=request.content).model_dump(),
                    MemoryMessage(role="assistant", content=ai_response_content).model_dump()
                ]
                await memory_client.add_memory(
                    user_id=session['user_id'], 
                    messages=conversation_to_log
                )
                logger.info("Memory stored successfully")
            except Exception as e:
                logger.error(f"Memory storage failed: {e}", exc_info=True)
                # Continue even if memory storage fails

            # 6. Update session with the new message exchange
            logger.info("Updating session...")
            try:
                session_manager.update_history(session_id, request.content, ai_response_content)
                await session_manager.update_session(session_id, {
                    'last_activity': int(time.time()),
                    'message_count': session.get('message_count', 0) + 1
                })
                logger.info("Session updated successfully")
            except Exception as e:
                logger.error(f"Session update failed: {e}", exc_info=True)
                # Continue even if session update fails

            # 7. Prepare response
            logger.info("Preparing response...")
            thinking_time = time.time() - start_time
            
            return SimulateMessageResponse(
                response=ai_response_content,
                thinking_time=thinking_time,
                tokens_used=0,  # TODO: Track token usage
                model=settings.OLLAMA_MODEL
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in post_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/simulate/{session_id}/status", response_model=SimulateStatusResponse)
async def get_status(session_id: uuid.UUID):
    """Return real-time stats for a running simulation session."""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")

        # Iterations = number of message exchanges so far (user -> assistant)
        iterations: int = session.get("message_count", len(session.get("history", [])))

        # Total memories stored for this user
        memory_size: int = 0
        try:
            memories = await memory_client.get_all_memories(user_id=session["user_id"])
            memory_size = len(memories)
        except Exception as mem_err:
            logger.warning(f"Could not fetch memories for status endpoint: {mem_err}")

        # GPU memory usage – Ollama does not expose this directly; return 0 for now.
        gpu_memory_used: float = 0.0

        return {
            "status": "active",
            "iterations": iterations,
            "memory_size": memory_size,
            "gpu_memory_used": gpu_memory_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/simulate/{session_id}/memory", response_model=MemoryAddResponse)  # Corrected path
async def add_memory_endpoint(session_id: uuid.UUID, request: MemoryAddRequest):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")

        start_time = time.time()
        result = None
        stored = False
        try:
            result = await memory_client.add_memory(
                user_id=session['user_id'], 
                messages=[msg.model_dump() for msg in request.messages],
                metadata=request.metadata,
                infer=request.infer
            )
            if result:
                stored = True
        except Exception as e:
            logger.error(f"Error in add_memory_endpoint: {e}", exc_info=True)
            stored = False
        
        end_time = time.time()

        return MemoryAddResponse(
            result=result, 
            stored=stored
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add_memory_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/simulate/{session_id}/export")
def export_session(session_id: uuid.UUID):
    try:
        return {
            "session_id": str(session_id),
            "status": "exported",
            "path": f"/path/to/export/{session_id}.json" # Placeholder
        }
    except Exception as e:
        logger.error(f"Error in export_session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/simulate/{session_id}/memory/{memory_id}", response_model=Optional[MemoryResponse])
async def get_memory(session_id: uuid.UUID, memory_id: str):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        memory_data = await memory_client.get_memory(memory_id=memory_id)
        if not memory_data:
            logger.error(f"Memory {memory_id} not found")
            raise HTTPException(status_code=404, detail="Memory not found")
        return MemoryResponse(**memory_data) if isinstance(memory_data, dict) else memory_data 
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/simulate/{session_id}/memory", response_model=MemoryListResponse)
async def get_all_user_memories(session_id: uuid.UUID):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        memories_data = await memory_client.get_all_memories(user_id=session['user_id'])
        transformed_memories = [MemoryResponse(**mem) if isinstance(mem, dict) else mem for mem in memories_data]
        return MemoryListResponse(memories=transformed_memories)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_all_user_memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/simulate/{session_id}/memory/{memory_id}", response_model=MemoryUpdateResponse)
async def update_memory(session_id: uuid.UUID, memory_id: str, request: MemoryUpdateRequest):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        result = await memory_client.update_memory(memory_id=memory_id, data=request.data)
        updated = False
        if result:
            updated = True
        return MemoryUpdateResponse(result=result, updated=updated)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/simulate/{session_id}/memory/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(session_id: uuid.UUID, memory_id: str):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        result = await memory_client.delete_memory(memory_id=memory_id)
        deleted = False
        if result:
            deleted = True
        return MemoryDeleteResponse(result=result, deleted=deleted)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/simulate/{session_id}/memory", response_model=MemoryDeleteResponse)
async def delete_all_session_user_memories(session_id: uuid.UUID):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        result = await memory_client.delete_all_user_memories(user_id=session['user_id'])
        deleted = False
        if result:
            deleted = True
        return MemoryDeleteResponse(result=result, deleted=deleted)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_all_session_user_memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/simulate/{session_id}/memory/{memory_id}/history", response_model=Optional[MemoryHistoryResponse])
async def get_memory_history(session_id: uuid.UUID, memory_id: str):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        history_data = await memory_client.get_memory_history(memory_id=memory_id)
        if not history_data:
            logger.error(f"Memory history {memory_id} not found")
            raise HTTPException(status_code=404, detail="Memory history not found or memory does not exist")
        if isinstance(history_data, list):
            return MemoryHistoryResponse(memory_id=memory_id, history=[entry for entry in history_data])
        return history_data
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_memory_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
