import logging
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from api.core.config import settings

logger = logging.getLogger(__name__)

class MemoryClient:
    def __init__(self):
        if not settings.MEM0_API_KEY:
            logger.warning("MEM0_API_KEY not found. Memory operations will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.api_key = settings.MEM0_API_KEY
            self.org_id = settings.MEM0_ORG_ID
            self.project_id = settings.MEM0_PROJECT_ID
            self.base_url = "https://api.mem0.ai/v2"
            self.headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def add_memory(self, user_id: str, messages: List[Dict[str, str]], metadata: Optional[Dict[str, Any]] = None, infer: bool = True):
        """
        Adds memories using direct API calls to mem0 v2 endpoint.
        Example messages: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        if not self.enabled:
            return None
        
        try:
            payload = {
                "messages": messages,
                "user_id": user_id,
                "org_id": self.org_id,
                "project_id": self.project_id
            }
            
            if metadata:
                payload["metadata"] = metadata
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/memories/",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Memory added for user {user_id}. Result: {result}")
                    return result
                else:
                    logger.error(f"Failed to add memory for user {user_id}. Status: {response.status_code}, Response: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error adding memory for user {user_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def get_memory(self, memory_id: str):
        if not self.enabled:
            logger.warning("MEM0_API_KEY not configured. Skipping get memory.")
            return None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/memories/{memory_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    memory = response.json()
                    logger.info(f"Retrieved memory with ID {memory_id}.")
                    return memory
                else:
                    logger.error(f"Failed to get memory {memory_id}. Status: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def get_all_memories(self, user_id: str):
        if not self.enabled:
            logger.warning(f"MEM0_API_KEY not configured. Skipping get all memories for user {user_id}.")
            return []
        try:
            payload = {
                "filters": {
                    "AND": [
                        {"user_id": user_id}
                    ]
                },
                "org_id": self.org_id,
                "project_id": self.project_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/memories/search/",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    memories = result.get("memories", [])
                    logger.info(f"Retrieved {len(memories)} memories for user {user_id}.")
                    return memories
                else:
                    logger.error(f"Failed to get memories for user {user_id}. Status: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error retrieving all memories for user {user_id}: {e}")
            return []

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def search_memory(self, user_id: str, query: str, limit: int = 5):
        if not self.enabled:
            logger.warning("MEM0_API_KEY not configured. Skipping memory search.")
            return []
        
        try:
            payload = {
                "filters": {
                    "AND": [
                        {"user_id": user_id}
                    ]
                },
                "query": query,
                "org_id": self.org_id,
                "project_id": self.project_id,
                "limit": limit
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/memories/search/",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    memories = result.get("memories", [])
                    logger.info(f"Found {len(memories)} memories for user {user_id} matching query.")
                    return memories[:limit]
                else:
                    logger.warning(f"Failed to search memory for user {user_id}. Status: {response.status_code}, Response: {response.text}")
                    return []
                    
        except Exception as e:
            logger.warning(f"Failed to search memory for user {user_id}: {e}")
            return []

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def update_memory(self, memory_id: str, data: Dict[str, Any]):
        if not self.enabled:
            logger.warning(f"MEM0_API_KEY not configured. Skipping update memory {memory_id}.")
            return None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/memories/{memory_id}",
                    headers=self.headers,
                    json=data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Memory {memory_id} updated. Result: {result}")
                    return result
                else:
                    logger.error(f"Failed to update memory {memory_id}. Status: {response.status_code}, Response: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def delete_memory(self, memory_id: str):
        if not self.enabled:
            logger.warning(f"MEM0_API_KEY not configured. Skipping delete memory {memory_id}.")
            return None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/memories/{memory_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Memory {memory_id} deleted. Result: {result}")
                    return result
                else:
                    logger.error(f"Failed to delete memory {memory_id}. Status: {response.status_code}, Response: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def delete_all_user_memories(self, user_id: str):
        if not self.enabled:
            logger.warning(f"MEM0_API_KEY not configured. Skipping delete all memories for user {user_id}.")
            return None
        try:
            # First get all memories for the user to delete them individually
            memories = await self.get_all_memories(user_id)
            if not memories:
                logger.info(f"No memories found for user {user_id} to delete.")
                return {"deleted_count": 0}
            
            deleted_count = 0
            async with httpx.AsyncClient() as client:
                for memory in memories:
                    memory_id = memory.get("id")
                    if memory_id:
                        response = await client.delete(
                            f"{self.base_url}/memories/{memory_id}",
                            headers=self.headers,
                            timeout=30.0
                        )
                        if response.status_code == 200:
                            deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} memories for user {user_id}.")
            return {"deleted_count": deleted_count}
        except Exception as e:
            logger.error(f"Error deleting all memories for user {user_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def get_memory_history(self, memory_id: str):
        if not self.enabled:
            logger.warning(f"MEM0_API_KEY not configured. Skipping get memory history for {memory_id}.")
            return None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/memories/{memory_id}/history",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    history = response.json()
                    logger.info(f"Retrieved history for memory {memory_id}.")
                    return history
                else:
                    logger.error(f"Failed to get memory history {memory_id}. Status: {response.status_code}, Response: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error retrieving history for memory {memory_id}: {e}")
            return None

memory_client = MemoryClient()
