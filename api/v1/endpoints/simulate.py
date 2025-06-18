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
from api.logic.conversation_graph import app_graph
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post("/simulate/start", response_model=SimulateStartResponse)
async def start_simulation(request: SimulateStartRequest):
    session_id = session_manager.create_session(user_id=request.user_id, mode=request.mode)
    # Each session has a unique graph config
    config = {"configurable": {"thread_id": str(session_id)}}
    session_manager.get_session(session_id)['graph_config'] = config

    return SimulateStartResponse(
        session_id=session_id,
        status="initialized",
        model_loaded="llama2-13b"  # Will be dynamic later
    )

@router.post("/simulate/{session_id}/message", response_model=SimulateMessageResponse)
async def post_message(session_id: uuid.UUID, request: SimulateMessageRequest):
    session = session_manager.get_session(session_id)
    if not session or 'graph_config' not in session:
        raise HTTPException(status_code=404, detail="Session not found or not initialized")

    start_time = time.time()

    # 1. Search for relevant memories
    relevant_memories = await memory_client.search_memory(user_id=session['user_id'], query=request.content)
    
    # 2. Construct the initial messages for the graph
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

    # 3. Invoke the graph
    inputs = {"messages": graph_input_messages}
    graph_result = await app_graph.ainvoke(inputs, config=session['graph_config'])
    
    ai_response_message = graph_result['messages'][-1]
    ai_response_content = ai_response_message.content if hasattr(ai_response_message, 'content') else str(ai_response_message)

    # 4. Add new information to memory
    conversation_to_log = [
        MemoryMessage(role="user", content=request.content).model_dump(),
        MemoryMessage(role="assistant", content=ai_response_content).model_dump()
    ]
    await memory_client.add_memory(user_id=session['user_id'], messages=conversation_to_log)


    # TODO: Token usage is not easily available from LangGraph invoke, will need custom callback
    tokens_used = 0 

    end_time = time.time()

    return SimulateMessageResponse(
        response=ai_response_content,
        thinking_time=end_time - start_time,
        tokens_used=tokens_used,
        model="llama2-13b"  # This will be made dynamic later
    )

@router.get("/simulate/{session_id}/status", response_model=SimulateStatusResponse)
def get_status(session_id: uuid.UUID):
    # Placeholder logic
    return {
        "status": "active",
        "iterations": 5,
        "memory_size": 1024,
        "gpu_memory_used": 0.75
    }

@router.post("/simulate/{session_id}/memory", response_model=MemoryAddResponse)  # Corrected path
async def add_memory_endpoint(session_id: uuid.UUID, request: MemoryAddRequest):
    session = session_manager.get_session(session_id)
    if not session:
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
        logger.error(f"Error in add_memory_endpoint: {e}")
        stored = False
    
    end_time = time.time()

    return MemoryAddResponse(
        result=result, 
        stored=stored
    )

@router.get("/simulate/{session_id}/export")
def export_session(session_id: uuid.UUID):
    return {
        "session_id": str(session_id),
        "status": "exported",
        "path": f"/path/to/export/{session_id}.json" # Placeholder
    }

@router.get("/simulate/{session_id}/memory/{memory_id}", response_model=Optional[MemoryResponse])
async def get_memory(session_id: uuid.UUID, memory_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    memory_data = await memory_client.get_memory(memory_id=memory_id)
    if not memory_data:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryResponse(**memory_data) if isinstance(memory_data, dict) else memory_data 

@router.get("/simulate/{session_id}/memory", response_model=MemoryListResponse)
async def get_all_user_memories(session_id: uuid.UUID):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    memories_data = await memory_client.get_all_memories(user_id=session['user_id'])
    transformed_memories = [MemoryResponse(**mem) if isinstance(mem, dict) else mem for mem in memories_data]
    return MemoryListResponse(memories=transformed_memories)

@router.put("/simulate/{session_id}/memory/{memory_id}", response_model=MemoryUpdateResponse)
async def update_memory(session_id: uuid.UUID, memory_id: str, request: MemoryUpdateRequest):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await memory_client.update_memory(memory_id=memory_id, data=request.data)
    updated = False
    if result:
        updated = True
    return MemoryUpdateResponse(result=result, updated=updated)

@router.delete("/simulate/{session_id}/memory/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(session_id: uuid.UUID, memory_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await memory_client.delete_memory(memory_id=memory_id)
    deleted = False
    if result:
        deleted = True
    return MemoryDeleteResponse(result=result, deleted=deleted)

@router.delete("/simulate/{session_id}/memory", response_model=MemoryDeleteResponse)
async def delete_all_session_user_memories(session_id: uuid.UUID):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await memory_client.delete_all_user_memories(user_id=session['user_id'])
    deleted = False
    if result:
        deleted = True
    return MemoryDeleteResponse(result=result, deleted=deleted)

@router.get("/simulate/{session_id}/memory/{memory_id}/history", response_model=Optional[MemoryHistoryResponse])
async def get_memory_history(session_id: uuid.UUID, memory_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    history_data = await memory_client.get_memory_history(memory_id=memory_id)
    if not history_data:
        raise HTTPException(status_code=404, detail="Memory history not found or memory does not exist")
    if isinstance(history_data, list):
        return MemoryHistoryResponse(memory_id=memory_id, history=[entry for entry in history_data])
    return history_data
