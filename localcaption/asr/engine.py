from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional, Any

import numpy as np

try:
    import sherpa_onnx
except Exception:  # pragma: no cover - optional dependency during early dev
    sherpa_onnx = None  # type: ignore


@dataclass
class RecognitionResult:
    text: str
    latency_ms: float
    is_final: bool


class StreamingASREngine:
    """A thin wrapper around sherpa-onnx OnlineRecognizer for streaming ASR."""

    def __init__(
        self,
        model_dir: str,
        sample_rate: int = 16000,
        feature_dim: int = 80,
        use_cpu: bool = True,
    ) -> None:
        if sherpa_onnx is None:
            raise RuntimeError("sherpa-onnx is not installed")

        self._sample_rate = sample_rate
        self._last_partial: str = ""

        model_dir = os.path.abspath(model_dir)

        def _find(glob_pat: str) -> Optional[str]:
            import glob

            matches = glob.glob(os.path.join(model_dir, "**", glob_pat), recursive=True)
            return matches[0] if matches else None

        tokens = _find("tokens.txt")
        encoder = _find("encoder*.onnx") or _find("*encoder*.onnx")
        decoder = _find("decoder*.onnx") or _find("*decoder*.onnx")
        joiner = _find("joiner*.onnx") or _find("*joiner*.onnx")

        if not all([tokens, encoder, decoder, joiner]):
            raise FileNotFoundError(
                f"Model files not found under: {model_dir}. "
                f"Expected tokens/encoder*/decoder*/joiner* ONNX files."
            )

        recognizer: Any = None

        # Prefer factory if available (v1.12.x compatible) — positional args
        from_transducer = getattr(getattr(sherpa_onnx, "OnlineRecognizer", object), "from_transducer", None)
        if callable(from_transducer):
            recognizer = from_transducer(
                tokens,  # type: ignore[arg-type]
                encoder,  # type: ignore[arg-type]
                decoder,  # type: ignore[arg-type]
                joiner,  # type: ignore[arg-type]
                num_threads=2,
                sample_rate=sample_rate,
                feature_dim=feature_dim,
                decoding_method="greedy_search",
                provider="cpu" if use_cpu else "cpu",
            )

        # Try config-based API (newer versions)
        if recognizer is None:
            try:
                OnlineRecognizerConfig = getattr(sherpa_onnx, "OnlineRecognizerConfig", None)
                FeatureConfig = getattr(sherpa_onnx, "FeatureConfig", None)
                OnlineTransducerModelConfig = getattr(sherpa_onnx, "OnlineTransducerModelConfig", None)
                if OnlineRecognizerConfig and FeatureConfig and OnlineTransducerModelConfig:
                    feat_config = FeatureConfig(sample_rate=sample_rate, feature_dim=feature_dim)  # type: ignore[misc]
                    model_config = OnlineTransducerModelConfig(  # type: ignore[misc]
                        encoder=encoder,
                        decoder=decoder,
                        joiner=joiner,
                        tokens=tokens,
                        num_threads=2,
                        provider="cpu" if use_cpu else "",
                    )
                    config = OnlineRecognizerConfig(  # type: ignore[misc]
                        feat_config=feat_config,
                        model_config=model_config,
                        decoding_method="greedy_search",
                    )
                    recognizer = sherpa_onnx.OnlineRecognizer(config)  # type: ignore[call-arg]
            except Exception:
                recognizer = None

        if recognizer is None:
            raise RuntimeError("Unable to construct sherpa-onnx OnlineRecognizer for this version.")

        self._recognizer: Any = recognizer
        self._stream: Any = self._recognizer.create_stream()

    def accept_pcm(self, pcm_f32: np.ndarray, sample_rate: int, timestamp: float) -> Optional[RecognitionResult]:
        """Accept a chunk of PCM float32 data and return partial/final result if available."""
        if pcm_f32.ndim == 2:
            pcm_f32 = np.mean(pcm_f32, axis=1)
        if sample_rate != self._sample_rate:
            # resample using simple linear method for MVP
            pcm_f32 = self._resample_linear(pcm_f32, sample_rate, self._sample_rate)

        start = time.perf_counter()
        self._stream.accept_waveform(self._sample_rate, pcm_f32.tolist())

        result: Optional[RecognitionResult] = None
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)
            r = self._recognizer.get_result(self._stream)
            partial = self._extract_text(r)
            partial = partial.strip()
            if partial and partial != self._last_partial:
                self._last_partial = partial
                result = RecognitionResult(text=partial, latency_ms=(time.perf_counter() - start) * 1000, is_final=False)

        if self._recognizer.is_endpoint(self._stream):
            r = self._recognizer.get_result(self._stream)
            self._recognizer.reset(self._stream)
            final_text = self._extract_text(r).strip()
            if final_text:
                result = RecognitionResult(text=final_text, latency_ms=(time.perf_counter() - start) * 1000, is_final=True)
                self._last_partial = ""

        return result

    @staticmethod
    def _extract_text(result_obj) -> str:  # type: ignore[no-untyped-def]
        if isinstance(result_obj, str):
            return result_obj
        text_attr = getattr(result_obj, "text", None)
        if isinstance(text_attr, str):
            return text_attr
        if isinstance(result_obj, dict):
            v = result_obj.get("text")
            if isinstance(v, str):
                return v
        return str(result_obj)

    @staticmethod
    def _resample_linear(pcm: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
        if src_sr == dst_sr:
            return pcm
        duration = pcm.shape[0] / float(src_sr)
        dst_len = int(duration * dst_sr)
        if dst_len <= 1:
            return np.zeros(0, dtype=np.float32)
        x_old = np.linspace(0.0, duration, num=pcm.shape[0], endpoint=False)
        x_new = np.linspace(0.0, duration, num=dst_len, endpoint=False)
        return np.interp(x_new, x_old, pcm).astype(np.float32)
