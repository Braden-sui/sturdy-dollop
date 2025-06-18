# Local Llama-cpp (.gguf) Setup


This repository is now configured to run **local GGUF models via `llama-cpp-python`** while keeping the existing OpenAI-compatible API surface.

---

## 1. Prerequisites

* Python 3.9-3.12
* C++14 compiler & CMake ≥ 3.22 (needed by llama-cpp)
* GPU build: CUDA 11.8+ or ROCm (optional but recommended)
* A `.gguf` model file (e.g. `TheBloke/Llama-2-13B-chat-GGUF` on Hugging Face)

---
## 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

The requirements now contain `llama-cpp-python` instead of `vllm`.

---
## 3. Environment variables

Create a `.env` (or copy `.env.example`) and set:

```bash
LLAMA_MODEL_PATH=/absolute/path/to/YOUR_MODEL.gguf
# optional – override port or host
VLLM_URL=http://localhost:8000
VLLM_MODEL_NAME=llama-2-13b-chat  # whatever you pass to --model
```

`VLLM_URL` is preserved for backward compatibility; it should point to the llama-cpp server address.

---
## 4. Start the llama-cpp server

### Option A: Local Development

```bash
python -m llama_cpp.server \
  --model "$LLAMA_MODEL_PATH" \
  --host 0.0.0.0 --port 8000 \
  --n_ctx 4096 --n_gpu_layers 100
```

This exposes an **OpenAI-compatible** REST API at `http://localhost:8000/v1/...` which the existing backend hits.

### Option B: Docker Setup

1. Place your `.gguf` model file in the `models/` directory
2. Update the `docker-compose.yml` file if needed (model path is already configured)
3. Start the containers:

```bash
docker compose up -d
```

The Docker setup includes a custom `llama-cpp-server` service that loads the model and exposes the OpenAI-compatible API at the same endpoint.

Tip: For convenience you can run it in a separate terminal or systemd / Docker.

---

## 5. Testing the API Integration

A test script is provided to verify that the llama-cpp server is working correctly and the API integration is functional:

```bash
python test_llama_cpp_api.py
```

This script will:

1. Check if the server is healthy
2. Verify the models endpoint is accessible
3. Test a simple completion request
## 6. Troubleshooting

### Model Loading Time
Larger GGUF models can take several minutes to load, especially on systems with limited RAM. Be patient during the initial startup.

### Memory Issues

If you encounter memory errors, try:

* Using a smaller quantized model (Q4_0 or Q4_K_M)
* Reducing the context size (`--n_ctx` parameter)
* Increasing swap space if running in Docker

### Docker-specific Issues

If you encounter Docker-related issues:

* Ensure the model file is correctly mounted in the container
* Check logs with `docker compose logs llama-cpp-server`
* The custom Dockerfile.llama-cpp contains all necessary dependencies

---

## 7. Run the FastAPI backend

```bash
uvicorn api.main:app --reload --port 9000
```

The simulator endpoints are now backed by your local GGUF model.

---

## 8. Quick test


```bash
curl http://localhost:9000/health        # backend health
curl http://localhost:8000/health        # llama-cpp server health
```

---

## 9. Troubleshooting


* *Model fails to load*: ensure the `.gguf` path is correct and you have enough VRAM / RAM.
* *Import errors*: run `pip install -r requirements.txt` again inside the virtual-env.
* *Slow inference*: tweak `--n_gpu_layers`, `--n_threads`, and `--n_batch` flags.

---

## 10. Optional clean-ups

* Rename `api/services/vllm_client.py` → `llama_client.py` and update imports (not required).
* Remove unused `vllm` code if you do not plan to switch back.

---
Happy local-LLM hacking!
