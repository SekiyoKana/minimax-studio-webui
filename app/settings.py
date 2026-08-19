from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMFY_ROOT = Path(
    os.getenv("H3_COMFY_ROOT", str(PROJECT_ROOT.parent / "ComfyUI"))
)
DEFAULT_WORKFLOW_ROOT = PROJECT_ROOT / "workflows"


@dataclass(frozen=True)
class Settings:
    root: Path = Path(os.getenv("H3_ROOT", str(PROJECT_ROOT)))
    host: str = os.getenv("H3_HOST", "0.0.0.0")
    port: int = int(os.getenv("H3_PORT", "8193"))
    desktop_mode: bool = os.getenv("H3_DESKTOP_MODE", "0") == "1"
    api_key: str = os.getenv("H3_API_KEY", "")
    incognito_code: str = os.getenv("H3_INCOGNITO_CODE", "change-me-before-use")
    gpu_label: str = os.getenv("H3_GPU_LABEL", "MiniMax H3 FP8 / ComfyUI")
    engine_backend: str = os.getenv("H3_ENGINE", "comfyui")
    comfy_url: str = os.getenv("H3_COMFY_URL", "http://127.0.0.1:8188")
    default_comfy_url: str = os.getenv("H3_DEFAULT_COMFY_URL", comfy_url)
    default_comfy_name: str = os.getenv("H3_DEFAULT_COMFY_NAME", "Local ComfyUI")
    default_comfy_api_key: str = os.getenv("H3_DEFAULT_COMFY_API_KEY", "")
    comfy_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_fl2va_fp8_720p_15s_api.json"),
        )
    )
    comfy_ref2va_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_REF2VA_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_ref2va_fp8_scaled_api.json"),
        )
    )
    comfy_turbo_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_TURBO_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_fl2va_fp8_turbo_lora_api.json"),
        )
    )
    comfy_ref2va_turbo_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_REF2VA_TURBO_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_ref2va_fp8_turbo_lora_api.json"),
        )
    )
    comfy_nsfw_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_NSFW_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_ref2va_fp8_nsfw_lora_api.json"),
        )
    )
    comfy_digital_human_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_DIGITAL_HUMAN_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_ref2va_fp8_digital_human_api.json"),
        )
    )
    comfy_tts_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_TTS_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_h3_ref2va_fp8_tts_api.json"),
        )
    )
    comfy_music3_workflow: Path = Path(
        os.getenv(
            "H3_COMFY_MUSIC3_WORKFLOW",
            str(DEFAULT_WORKFLOW_ROOT / "minimax_music3_int8_api.json"),
        )
    )
    comfy_input_dir: Path = Path(
        os.getenv("H3_COMFY_INPUT_DIR", str(DEFAULT_COMFY_ROOT / "input"))
    )
    comfy_output_dir: Path = Path(
        os.getenv("H3_COMFY_OUTPUT_DIR", str(DEFAULT_COMFY_ROOT / "output"))
    )
    comfy_poll_seconds: float = float(os.getenv("H3_COMFY_POLL_SECONDS", "2"))
    remote_reconnect_seconds: float = float(
        os.getenv("H3_REMOTE_RECONNECT_SECONDS", "120")
    )
    sglang_url: str = os.getenv("H3_SGLANG_URL", "http://127.0.0.1:8194")
    sglang_model: str = os.getenv(
        "H3_SGLANG_MODEL", str(PROJECT_ROOT / "models" / "sglang-h3" / "Ref2VA")
    )
    sglang_poll_seconds: float = float(os.getenv("H3_SGLANG_POLL_SECONDS", "2"))
    vram_limit_gb: float = float(os.getenv("H3_VRAM_LIMIT_GB", "19"))
    min_free_vram_gb: float = float(os.getenv("H3_MIN_FREE_VRAM_GB", "20"))
    max_upload_mb: int = int(os.getenv("H3_MAX_UPLOAD_MB", "512"))
    fake_engine: bool = os.getenv("H3_FAKE_ENGINE", "0") == "1"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def dit_path(self) -> Path:
        return self.models_dir / "diffsynth-nf4" / "minimax-h3-ref2va-nf4.safetensors"

    @property
    def text_encoder_path(self) -> Path:
        return self.models_dir / "diffsynth-nf4" / "minimax-h3-text-encoder-nf4.safetensors"

    @property
    def video_vae_path(self) -> Path:
        return self.models_dir / "comfy-source" / "minimax_h3_video_vae_fp16.safetensors"

    @property
    def audio_vae_path(self) -> Path:
        return self.models_dir / "comfy-source" / "minimax_h3_audio_vae_fp32.safetensors"

    @property
    def processor_path(self) -> Path:
        return self.models_dir / "official" / "Ref2VA" / "processor"

    def ensure_directories(self) -> None:
        for path in (self.uploads_dir, self.outputs_dir, self.jobs_dir):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
