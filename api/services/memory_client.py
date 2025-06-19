import logging
import os
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from api.core.config import settings

logger = logging.getLogger(__name__)

class MemoryClient:
    def __init__(self):
        if not settings.MEM0_API_KEY:
            logger.warning("MEM0_API_KEY not found. Memory operations will be disabled.")
            self.enabled = False
            self.client = None
        else:
            try:
                # Set environment variable for mem0ai SDK
                os.environ["MEM0_API_KEY"] = settings.MEM0_API_KEY
                
                # Import and initialize the official mem0ai client
                from mem0 import MemoryClient as Mem0Client
                self.client = Mem0Client()
                self.enabled = True
                
                logger.info("Mem0 client initialized successfully")
            except ImportError as e:
                logger.error(f"Failed to import mem0ai package: {e}")
                self.enabled = False
                self.client = None
            except Exception as e:
                logger.error(f"Failed to initialize Mem0 client: {e}")
                self.enabled = False
                self.client = None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def add_memory(self, user_id: str, messages: List[Dict[str, str]], metadata: Optional[Dict[str, Any]] = None, infer: bool = True):
        """
        Adds memories using the official mem0ai SDK.
        Example messages: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping add_memory.")
            return None
        
        try:
            # Use the official SDK's add method
            result = self.client.add(messages, user_id=user_id, metadata=metadata)
            logger.info(f"Memory added successfully for user {user_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error adding memory for user {user_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def get_memory(self, memory_id: str):
        """Get a specific memory by ID."""
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping get_memory.")
            return None
        
        try:
            result = self.client.get(memory_id)
            logger.info(f"Retrieved memory {memory_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def update_memory(self, memory_id: str, data: Dict[str, Any]):
        """Update a memory by ID."""
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping update_memory.")
            return None
        
        try:
            result = self.client.update(memory_id, data)
            logger.info(f"Updated memory {memory_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def delete_memory(self, memory_id: str):
        """Delete a memory by ID."""
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping delete_memory.")
            return False
        
        try:
            result = self.client.delete(memory_id)
            logger.info(f"Deleted memory {memory_id}: {result}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def get_all_memories(self, user_id: str):
        """Get all memories for a user."""
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping get_all_memories.")
            return []
        
        try:
            result = self.client.get_all(user_id=user_id)
            logger.info(f"Retrieved all memories for user {user_id}: {len(result) if result else 0} memories")
            return result if result else []
        except Exception as e:
            logger.error(f"Error retrieving all memories for user {user_id}: {e}")
            return []

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def search_memory(self, user_id: str, query: str, limit: int = 5):
        """Search memories for a user using the official SDK."""
        if not self.enabled or not self.client:
            logger.warning("MEM0_API_KEY not configured. Skipping memory search.")
            return []
        
        try:
            result = self.client.search(query, user_id=user_id, limit=limit)
            logger.info(f"Memory search for user {user_id} with query '{query}': {len(result) if result else 0} results")
            return result if result else []
        except Exception as e:
            logger.error(f"Error searching memories for user {user_id}: {e}")
            return []

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def delete_all_memories(self, user_id: str):
        """Delete all memories for a user."""
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping delete_all_memories.")
            return False
        
        try:
            result = self.client.delete_all(user_id=user_id)
            logger.info(f"Deleted all memories for user {user_id}: {result}")
            return True
        except Exception as e:
            logger.error(f"Error deleting all memories for user {user_id}: {e}")
            return False

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def get_memory_history(self, memory_id: str):
        """Get the history of a memory."""
        if not self.enabled or not self.client:
            logger.warning("Mem0 client not available. Skipping get_memory_history.")
            return []
        
        try:
            result = self.client.history(memory_id)
            logger.info(f"Retrieved history for memory {memory_id}: {len(result) if result else 0} entries")
            return result if result else []
        except Exception as e:
            logger.error(f"Error retrieving history for memory {memory_id}: {e}")
            return []

# Initialize the global memory client instance
memory_client = MemoryClient()
