import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


APP_NAME = "LocalCaption"


def user_data_dir() -> str:
    # Prefer LOCALAPPDATA on Windows, fallback to HOME
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def user_models_dir() -> str:
    path = os.path.join(user_data_dir(), "models")
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class AppConfig:
    selected_model_id: Optional[str] = None
    selected_device_index: Optional[int] = None
    tts_enabled: bool = False
    tts_speak_partials: bool = False
    tts_rate_wpm: Optional[int] = None
    tts_voice_id: Optional[str] = None
    stt_backend: str = "local"  # "local" | "deepgram"
    deepgram_api_key: Optional[str] = None
    deepgram_model: Optional[str] = None  # e.g., "nova-2", defaults server-side
    audio_source: str = "internal"  # "internal" | "microphone"


def config_path() -> str:
    return os.path.join(user_data_dir(), "config.json")


def load_config() -> AppConfig:
    path = config_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            return AppConfig(**data)
        except Exception:
            return AppConfig()
    return AppConfig()


def save_config(cfg: AppConfig) -> None:
    path = config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
    except Exception:
        pass
