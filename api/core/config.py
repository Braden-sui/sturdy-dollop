import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Local LLM Simulator"
    API_V1_STR: str = "/api/v1"

    # Environment variables
    VLLM_URL: str = os.getenv("VLLM_URL", "http://localhost:8000")
    MEM0_API_KEY: str = os.getenv("MEM0_API_KEY", "")
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8888")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a_very_secret_key_that_should_be_changed")
    VLLM_MODEL_NAME: str = os.getenv("VLLM_MODEL_NAME", "Magistral-Small-2506-Q4_0")  # Model name for llama-cpp-server
    JWT_ALGORITHM: str = "HS256"

    class Config:
        case_sensitive = True

settings = Settings()
