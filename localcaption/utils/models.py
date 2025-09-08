import os
import tarfile
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional

from .config import user_models_dir


@dataclass
class ModelInfo:
    id: str
    name: str
    url: str
    folder_name: str  # expected folder after extraction


# Minimal registry; extend as needed
MODEL_REGISTRY: Dict[str, ModelInfo] = {
    "zipformer-en-20M-2023-02-17": ModelInfo(
        id="zipformer-en-20M-2023-02-17",
        name="Zipformer EN Tiny (20M)",
        url=(
            "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
            "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2"
        ),
        folder_name="sherpa-onnx-streaming-zipformer-en-20M-2023-02-17",
    ),
}


def ensure_model_downloaded(model_id: str) -> Optional[str]:
    info = MODEL_REGISTRY.get(model_id)
    if not info:
        return None
    models_dir = user_models_dir()
    target_root = os.path.join(models_dir, info.folder_name)
    if os.path.isdir(target_root) and os.path.isfile(os.path.join(target_root, "tokens.txt")):
        return target_root
    os.makedirs(models_dir, exist_ok=True)
    archive = os.path.join(models_dir, os.path.basename(info.url))
    if not os.path.isfile(archive):
        urllib.request.urlretrieve(info.url, archive)
    if not os.path.isdir(target_root):
        with tarfile.open(archive, "r:bz2") as tf:
            tf.extractall(models_dir)
    return target_root if os.path.isdir(target_root) else None
