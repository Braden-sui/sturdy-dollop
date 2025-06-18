from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid

class SimulateStartRequest(BaseModel):
    mode: str
    agent_config: Dict[str, Any]
    user_id: str

class SimulateStartResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    model_loaded: str

class SimulateMessageRequest(BaseModel):
    content: str
    attachments: Optional[List[Any]] = []

class SimulateMessageResponse(BaseModel):
    response: str
    thinking_time: float
    tokens_used: int
    model: str

class SimulateStatusResponse(BaseModel):
    status: str
    iterations: int
    memory_size: int
    gpu_memory_used: float

class MemoryMessage(BaseModel):
    role: str
    content: str

class MemoryAddRequest(BaseModel):
    messages: List[MemoryMessage]  # Changed from content: str
    metadata: Optional[Dict[str, Any]] = None  # Added
    infer: bool = True  # Added
    # importance: float  # Removed

class MemoryAddResponse(BaseModel):
    result: Any  # mem0.add result structure can vary
    stored: bool
    # memory_id: Optional[str] = None # Depending on mem0.add result
    # embedding_time: float # Removed

# --- New Schemas for Full CRUD --- 

class BaseMemoryData(BaseModel):
    # Common fields we expect in a memory object from mem0
    # This is an assumption; actual fields might differ based on mem0's response
    id: str
    text: str
    user_id: str
    timestamp: str # Assuming ISO format string
    metadata: Optional[Dict[str, Any]] = None
    # Add other fields like score, source, etc., if commonly returned

class MemoryResponse(BaseMemoryData):
    pass

class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse]

class MemoryUpdateRequest(BaseModel):
    data: Dict[str, Any] # The data to update the memory with

class MemoryUpdateResponse(BaseModel):
    result: Any # Result from mem0.update
    updated: bool

class MemoryDeleteResponse(BaseModel):
    result: Any # Result from mem0.delete or delete_all
    deleted: bool

class MemoryHistoryEntry(BaseModel):
    # Assuming history entries have a timestamp and some data representation
    # This is a placeholder; actual structure depends on mem0.history response
    timestamp: str
    change_description: str # Or 'snapshot_data: Dict[str, Any]'
    # ... other relevant history fields

class MemoryHistoryResponse(BaseModel):
    memory_id: str
    history: List[MemoryHistoryEntry]
