import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("########## api/main.py: TOP OF FILE ##########")

from fastapi import FastAPI
from api.v1.api import api_router
from api.core.config import settings
import os
import pathlib
from contextlib import asynccontextmanager
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from api.logic.conversation_graph import compile_global_graph, app_graph as global_app_graph # Import app_graph to check it


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI app startup: Initializing resources...")
    # Ensure data directory exists
    data_dir = pathlib.Path("data")
    data_dir.mkdir(parents=True, exist_ok=True) # parents=True to create intermediate dirs if needed
    db_path = data_dir / "checkpoints.sqlite"
    logger.info(f"SQLite DB path: {db_path.resolve()}")

    conn = None
    try:
        conn = await aiosqlite.connect(db_path)
        app.state.db_conn = conn
        logger.info(f"Successfully connected to SQLite DB: {db_path}")
        
        checkpointer = AsyncSqliteSaver(conn=conn)
        app.state.checkpointer = checkpointer # Store if needed elsewhere
        logger.info(f"AsyncSqliteSaver initialized: {checkpointer}")

        compile_global_graph(checkpointer) # This will set the global_app_graph in conversation_graph.py
        logger.info(f"Global graph compilation triggered from lifespan startup. Compiled graph: {global_app_graph}")
        if global_app_graph is None:
            logger.error("CRITICAL: Global app_graph is None after compilation attempt in lifespan!")
            # Depending on strictness, you might want to raise an error here to stop startup
            # raise RuntimeError("Failed to compile app_graph during startup.")
        
        yield # Application runs here
        
    except Exception as e:
        logger.error(f"Error during FastAPI startup: {e}", exc_info=True)
        # Optionally re-raise or handle to prevent app from starting in a bad state
        raise
    finally:
        if hasattr(app.state, 'db_conn') and app.state.db_conn:
            await app.state.db_conn.close()
            logger.info("SQLite connection closed.")
        logger.info("FastAPI app shutdown: Resources cleaned up.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "ok"}
