import requests
import json
import time
import sys
import uuid

API_BASE_URL = "http://localhost:8001/api/v1"

def check_api_health(url="http://localhost:8001/health"):
    """Check if the API service is healthy."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                return True
        print(f"API health check failed: Status {response.status_code}, Response: {response.text}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"API health check connection error: {e}")
        return False

def start_simulation_session(user_id: str = "test_user"):
    """Starts a new simulation session and returns the session_id."""
    try:
        payload = {"user_id": user_id, "mode": "test", "agent_config": {}}
        response = requests.post(f"{API_BASE_URL}/simulate/start", json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        print(f"Started session: {data}")
        return data.get("session_id")
    except requests.exceptions.RequestException as e:
        print(f"Error starting simulation session: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def post_simulation_message(session_id: str, message: str):
    """Posts a message to an active simulation session and gets a response."""
    try:
        payload = {"content": message}
        response = requests.post(f"{API_BASE_URL}/simulate/{session_id}/message", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Simulation message response: {json.dumps(data, indent=2)}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error posting simulation message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def main():
    max_retries = 10 # Reduced retries for faster feedback during testing
    retry_interval = 15  # seconds

    print("Testing API integration with Ollama backend...")

    for i in range(max_retries):
        print(f"Attempt {i+1}/{max_retries} to connect to API service...")

        if check_api_health():
            print("API health check passed!")

            session_id = start_simulation_session()
            if session_id:
                print(f"Successfully started simulation session: {session_id}")
                
                test_prompt = "Explain the theory of relativity in one sentence."
                print(f"Sending prompt: '{test_prompt}'")
                simulation_response = post_simulation_message(session_id, test_prompt)
                
                if simulation_response and simulation_response.get("response"):
                    print("Simulation message test passed!")
                    print(f"AI Response: {simulation_response.get('response')}")
                    print("All tests passed successfully!")
                    return 0
                else:
                    print("Simulation message test failed or got no AI response.")
            else:
                print("Failed to start simulation session.")
        
        print(f"Waiting {retry_interval} seconds before next attempt...")
        time.sleep(retry_interval)

    print("Failed to complete tests after maximum retries.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
