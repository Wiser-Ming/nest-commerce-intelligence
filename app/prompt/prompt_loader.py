from pathlib import Path


def load_prompt(name: str) -> str:
    """读取指定名称的 prompt 模板内容"""

    prompt_path = Path(__file__).parents[2] / "prompts" / f"{name}.prompt"
    return prompt_path.read_text(encoding="utf-8")
