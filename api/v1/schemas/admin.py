from pydantic import BaseModel, Field

class ModelLoadRequest(BaseModel):
    model_name: str = Field(..., description="The HuggingFace model identifier.")
    quantization: str = Field(default="none", description="Quantization method: 'awq', 'gptq', or 'none'.")

class ModelLoadResponse(BaseModel):
    loaded: bool
    vram_usage: float = Field(..., description="Estimated VRAM usage as a fraction (0.0 to 1.0).")
    load_time: float = Field(..., description="Time taken to load the model in seconds.")
