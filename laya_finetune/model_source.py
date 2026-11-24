from pathlib import Path

from huggingface_hub import snapshot_download


MODEL_REPO = "convaiinnovations/laya"
MODEL_REVISION = "1c5edc17a7acd8701df6fc341c0d179f1c62c982"


def download_checkpoint(variant: str = "base") -> Path:
    prefix = "multilingual/" if variant == "multilingual" else ""
    files = ["model.safetensors", "rl_agent_config.json", "encoder/*", "tokenizer/*"]
    snapshot = snapshot_download(
        MODEL_REPO,
        revision=MODEL_REVISION,
        allow_patterns=[f"{prefix}{name}" for name in files],
    )
    return Path(snapshot, prefix)
