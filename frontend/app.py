import streamlit as st
import asyncio
from api_client import start_simulation, post_message

st.set_page_config(page_title="Local LLM Simulator", layout="wide")

st.title("🧠 Local LLM Simulator")

# --- Sidebar for settings ---
st.sidebar.header("Session Settings")
user_id = st.sidebar.text_input("Enter your User ID", value="default-user")

if st.sidebar.button("Clear Conversation"):
    st.session_state.messages = []
    st.session_state.session_id = None

# --- Main Chat Interface ---

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What would you like to discuss?"):
    if not user_id:
        st.warning("Please enter a User ID in the sidebar to begin.")
    else:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")

            async def get_ai_response():
                # Start a new session if one doesn't exist
                if not st.session_state.session_id:
                    sim_start_response = await start_simulation(user_id)
                    if sim_start_response:
                        st.session_state.session_id = sim_start_response.get("session_id")
                    else:
                        message_placeholder.error("Failed to start a new simulation session.")
                        return

                # Post the message to the backend
                ai_response = await post_message(st.session_state.session_id, prompt)
                if ai_response:
                    message_placeholder.markdown(ai_response.get("response"))
                    st.session_state.messages.append({"role": "assistant", "content": ai_response.get("response")})
                else:
                    message_placeholder.error("Failed to get a response from the backend.")

            # Run the async function
            asyncio.run(get_ai_response())
