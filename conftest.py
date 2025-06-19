"""Pytest configuration that automatically starts the FastAPI server inside the
container so that HTTP-level integration tests can run successfully.

This fixture is session-scoped and starts *one* uvicorn instance on port 8001.
It is automatically applied (autouse=True), so individual tests do not need to
request it explicitly.
"""

import subprocess
import time
import signal
import os
import sys
from pathlib import Path

import pytest




PROJECT_ROOT = Path(__file__).resolve().parent

def _start_server() -> subprocess.Popen:
    """Spawn uvicorn serving api.main:app in a background process."""
    # Ensure we run from project root so import paths resolve
    cwd = PROJECT_ROOT
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8001",
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


@pytest.fixture(scope="session")
def fastapi_server():
    """Start the API server once for the entire test session."""
    proc = _start_server()

    # Simple readiness loop – give it up to 10 seconds to start listening
    for _ in range(30):
        time.sleep(0.5)
        if proc.poll() is not None:
            # Server crashed early
            raise RuntimeError("uvicorn terminated unexpectedly during startup")
        # Attempt a socket connection to the health endpoint using curl (lightweight)
        import http.client
        try:
            conn = http.client.HTTPConnection("localhost", 8001, timeout=0.2)
            conn.request("GET", "/health")
            resp = conn.getresponse()
            if resp.status == 200:
                conn.close()
                break
        except Exception:
            continue
    else:
        proc.terminate()
        raise RuntimeError("uvicorn did not become ready within timeout")

    yield  # Run the tests

    # Teardown: terminate server process
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
