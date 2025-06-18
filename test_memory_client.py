#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append('/app')

from api.services.memory_client import memory_client

async def test_memory_client():
    print("Testing Memory Client Implementation")
    print("=" * 50)
    
    # Check if client is enabled
    print(f"Memory client enabled: {memory_client.enabled}")
    if memory_client.enabled:
        print(f"API Key: {memory_client.api_key[:15]}...")
        print(f"Org ID: {memory_client.org_id}")
        print(f"Project ID: {memory_client.project_id}")
        print(f"Base URL: {memory_client.base_url}")
    else:
        print("Memory client is disabled - missing API key")
        return
    
    print("\n1. Testing add_memory...")
    test_messages = [
        {"role": "user", "content": "I love chocolate ice cream"},
        {"role": "assistant", "content": "That's wonderful! Chocolate ice cream is delicious."}
    ]
    
    add_result = await memory_client.add_memory(
        user_id="test-user-123",
        messages=test_messages,
        metadata={"test": "integration"}
    )
    print(f"Add memory result: {add_result}")
    
    if add_result:
        print("\n2. Testing search_memory...")
        search_result = await memory_client.search_memory(
            user_id="test-user-123",
            query="chocolate ice cream",
            limit=5
        )
        print(f"Search memory result: {search_result}")
        
        print("\n3. Testing get_all_memories...")
        all_memories = await memory_client.get_all_memories("test-user-123")
        print(f"All memories result: {all_memories}")
        
        if all_memories and len(all_memories) > 0:
            memory_id = all_memories[0].get("id")
            if memory_id:
                print(f"\n4. Testing get_memory with ID: {memory_id}")
                get_result = await memory_client.get_memory(memory_id)
                print(f"Get memory result: {get_result}")
                
                print(f"\n5. Testing update_memory with ID: {memory_id}")
                update_result = await memory_client.update_memory(
                    memory_id, 
                    {"content": "Updated memory content"}
                )
                print(f"Update memory result: {update_result}")
                
                print(f"\n6. Testing get_memory_history with ID: {memory_id}")
                history_result = await memory_client.get_memory_history(memory_id)
                print(f"Memory history result: {history_result}")
                
                print(f"\n7. Testing delete_memory with ID: {memory_id}")
                delete_result = await memory_client.delete_memory(memory_id)
                print(f"Delete memory result: {delete_result}")
    
    print("\n8. Testing delete_all_user_memories...")
    delete_all_result = await memory_client.delete_all_user_memories("test-user-123")
    print(f"Delete all memories result: {delete_all_result}")

if __name__ == "__main__":
    asyncio.run(test_memory_client())