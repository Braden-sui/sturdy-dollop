import httpx
import streamlit as st

# The backend URL is determined by the Docker Compose service name
BACKEND_URL = "http://api:8001"

async def start_simulation(user_id: str, mode: str = "human-ai"):
    """Calls the backend to start a new simulation session."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/simulate/start",
                json={"user_id": user_id, "mode": mode, "agent_config": {}},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"HTTP error starting simulation: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            st.error(f"Error connecting to backend: {e}")
        return None

async def post_message(session_id: str, message: str):
    """Sends a message to the backend and gets the AI's response."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/simulate/{session_id}/message",
                json={"content": message},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"HTTP error sending message: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            st.error(f"Error connecting to backend: {e}")
        return None
