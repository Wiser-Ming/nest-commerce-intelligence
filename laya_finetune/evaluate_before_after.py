"""Compare base and fine-tuned Laya on one immutable test split."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import laya
import torch

from laya_finetune.model_source import download_checkpoint


ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "laya_finetune" / "data" / "test.jsonl"
FINETUNED = ROOT / "laya_finetune" / "artifacts" / "shopkeeper-router-head"
REPORT = ROOT / "laya_finetune" / "artifacts" / "before_after_report.json"
LABELS = ["database_query", "non_database", "clarification"]


def rows() -> list[dict]:
    return [json.loads(line) for line in TEST.read_text(encoding="utf-8").splitlines()]


def question(row: dict) -> dict:
    return {"intent": row["question"]}


def metrics(items: list[dict]) -> dict:
    matrix = Counter((x["gold"], x["predicted"]) for x in items)
    accuracy = sum(x["gold"] == x["predicted"] for x in items) / len(items)
    per_class = {}
    f1_values = []
    for label in LABELS:
        tp = matrix[(label, label)]
        fp = sum(matrix[(other, label)] for other in LABELS if other != label)
        fn = sum(matrix[(label, other)] for other in LABELS if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"count": tp + fn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
        f1_values.append(f1)
    brier = 0.0
    for item in items:
        for label in LABELS:
            target = 1.0 if item["gold"] == label else 0.0
            brier += (item["probabilities"].get(label, 0.0) - target) ** 2
    brier /= len(items) * len(LABELS)
    buckets = []
    for lower in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        bucket = [x for x in items if lower <= x["confidence"] < lower + 0.1]
        if bucket:
            buckets.append({"confidence": round(sum(x["confidence"] for x in bucket) / len(bucket), 4), "accuracy": round(sum(x["gold"] == x["predicted"] for x in bucket) / len(bucket), 4), "count": len(bucket)})
    return {"count": len(items), "accuracy": round(accuracy, 4), "macro_f1": round(sum(f1_values) / len(f1_values), 4), "brier": round(brier, 4), "database_recall": per_class["database_query"]["recall"], "per_class": per_class, "confusion": {f"{a}->{b}": n for (a, b), n in sorted(matrix.items())}, "calibration_buckets": buckets}


def run(agent, test_rows: list[dict]) -> tuple[list[dict], float]:
    outputs = []
    start = time.perf_counter()
    for row in test_rows:
        t0 = time.perf_counter()
        result = agent.predict(row["state"], question(row))
        latency_ms = (time.perf_counter() - t0) * 1000
        answer = result["answers"]["intent"]
        outputs.append({"id": row["id"], "query": row["state"]["query"], "gold": row["label"], "predicted": answer["choice"], "confidence": float(answer.get("confidence", 0.0)), "probabilities": answer.get("probabilities", {}), "latency_ms": round(latency_ms, 3)})
    return outputs, (time.perf_counter() - start) / len(test_rows) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--baseline", choices=["base", "multilingual"], default="base")
    args = parser.parse_args()
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable in the current PyTorch environment")

    test_rows = rows()
    report = {"test_file": str(TEST), "sample_count": len(test_rows), "device": device, "baseline": args.baseline, "models": {}}

    base = laya.load(str(download_checkpoint(args.baseline)), device=device)
    base_outputs, base_latency = run(base, test_rows)
    report["models"]["base"] = {**metrics(base_outputs), "mean_latency_ms": round(base_latency, 3), "errors": [x for x in base_outputs if x["gold"] != x["predicted"]]}
    del base
    if device == "cuda":
        torch.cuda.empty_cache()

    tuned = laya.load(str(FINETUNED), device=device)
    tuned_outputs, tuned_latency = run(tuned, test_rows)
    report["models"]["fine_tuned"] = {**metrics(tuned_outputs), "mean_latency_ms": round(tuned_latency, 3), "errors": [x for x in tuned_outputs if x["gold"] != x["predicted"]]}
    report["delta"] = {key: round(report["models"]["fine_tuned"][key] - report["models"]["base"][key], 4) for key in ["accuracy", "macro_f1", "brier", "database_recall"]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sample_count": report["sample_count"], "base": {k: report["models"]["base"][k] for k in ["accuracy", "macro_f1", "brier", "database_recall", "mean_latency_ms"]}, "fine_tuned": {k: report["models"]["fine_tuned"][k] for k in ["accuracy", "macro_f1", "brier", "database_recall", "mean_latency_ms"]}, "delta": report["delta"]}, ensure_ascii=False, indent=2))
    print(f"report={REPORT}")


if __name__ == "__main__":
    main()
