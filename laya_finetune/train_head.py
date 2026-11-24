from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import time
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file, save_file
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from laya.agent import _fix_tokenizer_config
from laya.common import QTYPES, build_model, build_sequence, proper_reward
from laya_finetune.model_source import download_checkpoint


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "laya_finetune" / "data"
DEFAULT_OUTPUT = ROOT / "laya_finetune" / "artifacts" / "shopkeeper-router-head"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def build_items(rows: list[dict], tokenizer, cfg: dict) -> list[dict]:
    items = []
    for row in rows:
        q = row["question"]
        keys = list(q["criteria"])
        seq, markers = build_sequence(
            tokenizer,
            row["state"],
            {"t": "choice", "ins": q["instructions"], "crit": q["criteria"]},
            cfg["max_len"],
            cfg["head_max_len"],
        )
        if len(markers) != len(keys):
            continue
        target = [0.0] * len(keys)
        target[keys.index(row["label"])] = 1.0
        items.append({"ids": seq, "markers": markers, "target": target, "label": keys.index(row["label"]), "qtype": QTYPES["choice"], "row": row})
    return items


def collate(items: list[dict], pad_id: int) -> dict[str, torch.Tensor]:
    length = max(len(item["ids"]) for item in items)
    k = max(len(item["markers"]) for item in items)
    ids = torch.full((len(items), length), pad_id, dtype=torch.long)
    attention = torch.zeros((len(items), length), dtype=torch.long)
    marker_pos = torch.zeros((len(items), k), dtype=torch.long)
    marker_mask = torch.zeros((len(items), k), dtype=torch.bool)
    target = torch.zeros((len(items), k), dtype=torch.float32)
    labels = []
    for index, item in enumerate(items):
        ids[index, : len(item["ids"])] = torch.tensor(item["ids"], dtype=torch.long)
        attention[index, : len(item["ids"])] = 1
        marker_pos[index, : len(item["markers"])] = torch.tensor(item["markers"], dtype=torch.long)
        marker_mask[index, : len(item["markers"])] = True
        target[index, : len(item["target"])] = torch.tensor(item["target"])
        labels.append(item["label"])
    return {"input_ids": ids, "attention_mask": attention, "marker_pos": marker_pos, "marker_mask": marker_mask, "target": target, "labels": torch.tensor(labels), "qtype": torch.zeros(len(items), dtype=torch.long)}


def logits_for(model, items: list[dict], tokenizer, device: torch.device, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    outputs, labels = [], []
    with torch.no_grad():
        for start in range(0, len(items), batch_size):
            batch = collate(items[start : start + batch_size], tokenizer.pad_token_id)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                logits, _ = model(batch["input_ids"].to(device), batch["attention_mask"].to(device), batch["marker_pos"].to(device), batch["marker_mask"].to(device), batch["qtype"].to(device))
            outputs.append(logits.float().cpu().numpy())
            labels.extend(batch["labels"].tolist())
    return np.concatenate(outputs), np.asarray(labels)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    z = torch.tensor(logits, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)
    log_t = torch.zeros(1, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        loss = torch.nn.functional.cross_entropy(z / log_t.exp(), y)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.clamp(log_t.exp(), 0.1, 10.0).item())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()

    selected = args.device
    if selected == "auto":
        selected = "cuda" if torch.cuda.is_available() else "cpu"
    if selected == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable in the current PyTorch environment")
    device = torch.device(selected)
    torch.manual_seed(20260922)
    random.seed(20260922)
    np.random.seed(20260922)

    model_dir = download_checkpoint()
    _fix_tokenizer_config(str(model_dir))
    cfg = json.loads(Path(model_dir, "rl_agent_config.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(Path(model_dir, "tokenizer"))
    train_items = build_items(load_rows(DATA_DIR / "train.jsonl"), tokenizer, cfg)
    dev_items = build_items(load_rows(DATA_DIR / "dev.jsonl"), tokenizer, cfg)
    print(f"items train={len(train_items)} dev={len(dev_items)} device={device}")

    model = build_model(cfg, encoder_dir=Path(model_dir, "encoder"))
    model.load_state_dict(load_file(Path(model_dir, "model.safetensors")), strict=True)
    for parameter in model.encoder.parameters():
        parameter.requires_grad = False
    model.to(device)
    model.train()
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs * math.ceil(len(train_items) / args.batch_size)), eta_min=args.lr * 0.05)

    start = time.perf_counter()
    history = []
    for epoch in range(args.epochs):
        random.shuffle(train_items)
        total_loss = 0.0
        batches = 0
        for offset in range(0, len(train_items), args.batch_size):
            batch = collate(train_items[offset : offset + args.batch_size], tokenizer.pad_token_id)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                logits, _ = model(batch["input_ids"].to(device), batch["attention_mask"].to(device), batch["marker_pos"].to(device), batch["marker_mask"].to(device), batch["qtype"].to(device))
            logits = logits.float()
            target = batch["target"].to(device)
            mask = batch["marker_mask"].to(device)
            loss = -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), dim=-1)).sum(dim=-1).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += float(loss.item())
            batches += 1
        with torch.no_grad():
            dev_logits, dev_labels = logits_for(model, dev_items, tokenizer, device, args.batch_size)
            dev_acc = float((dev_logits.argmax(-1) == dev_labels).mean())
        history.append({"epoch": epoch + 1, "loss": total_loss / max(1, batches), "dev_accuracy": dev_acc})
        print(f"epoch={epoch + 1}/{args.epochs} loss={total_loss / max(1, batches):.4f} dev_accuracy={dev_acc:.4f}")

    dev_logits, dev_labels = logits_for(model, dev_items, tokenizer, device, args.batch_size)
    temperature = fit_temperature(dev_logits, dev_labels)
    args.output.mkdir(parents=True, exist_ok=True)
    save_file({key: value.half().contiguous().cpu() for key, value in model.state_dict().items()}, args.output / "model.safetensors")
    model.encoder.config.save_pretrained(args.output / "encoder")
    tokenizer.save_pretrained(args.output / "tokenizer")
    output_cfg = dict(cfg)
    output_cfg.update({"fine_tuned": True, "model_name": "shopkeeper-router-head", "temperature": [temperature, 1.0, 1.0], "training": {"method": "frozen_encoder_head_only", "epochs": args.epochs, "batch_size": args.batch_size, "learning_rate": args.lr, "train_items": len(train_items), "dev_items": len(dev_items), "seconds": round(time.perf_counter() - start, 2)}})
    (args.output / "rl_agent_config.json").write_text(json.dumps(output_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "training_history.json").write_text(json.dumps({"history": history, "temperature": temperature}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={args.output} temperature={temperature:.4f} seconds={time.perf_counter() - start:.1f}")


if __name__ == "__main__":
    main()
