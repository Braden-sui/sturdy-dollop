import uuid
from typing import Dict, Any

class SessionManager:
    def __init__(self):
        self.sessions: Dict[uuid.UUID, Dict[str, Any]] = {}

    def create_session(self, user_id: str, mode: str) -> uuid.UUID:
        session_id = uuid.uuid4()
        self.sessions[session_id] = {
            "user_id": user_id,
            "mode": mode,
            "history": []
        }
        return session_id

    def get_session(self, session_id: uuid.UUID) -> Dict[str, Any] | None:
        return self.sessions.get(session_id)

    def update_history(self, session_id: uuid.UUID, user_message: str, ai_message: str):
        if session := self.get_session(session_id):
            session["history"].append({"user": user_message, "ai": ai_message})

session_manager = SessionManager()
