"""Evaluate the local Laya multilingual checkpoint on the generated dataset."""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import laya


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "intent_eval.jsonl"
REPORT = ROOT / "data" / "laya_intent_report.json"
LABELS = ["database_query", "general_qa", "metric_explanation", "conversation", "clarification", "unsupported"]


def load_rows(per_intent: int, seed: int) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    with DATASET.open(encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            grouped[row["intent"]].append(row)
    rng = random.Random(seed)
    rows = []
    for label in LABELS:
        candidates = grouped[label][:]
        rng.shuffle(candidates)
        rows.extend(candidates[:per_intent])
    rng.shuffle(rows)
    return rows


def load_binary_rows(per_class: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows = [json.loads(line) for line in DATASET.open(encoding="utf-8")]
    database = [row for row in rows if row["needs_database"]]
    non_database = [row for row in rows if not row["needs_database"]]
    rng.shuffle(database)
    rng.shuffle(non_database)
    selected = database[:per_class] + non_database[:per_class]
    rng.shuffle(selected)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-intent", type=int, default=30)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--binary", action="store_true", help="Evaluate only the database/non-database gate")
    args = parser.parse_args()

    report_path = ROOT / "data" / ("laya_intent_report_binary.json" if args.binary else "laya_intent_report_sixway.json")

    rows = load_binary_rows(args.per_intent, seed=20260922) if args.binary else load_rows(args.per_intent, seed=20260922)
    agent = laya.load("convaiinnovations/laya", subfolder="multilingual", device=args.device)
    questions = {
        "intent": {
            "type": "choice",
            "instructions": "判断用户问题最适合由哪个能力处理。只有明确要求读取、统计、筛选或比较真实业务数据时才选择 database_query；解释指标概念不要查库。",
            "criteria": {
                "database_query": "需要读取真实业务数据库中的销售、订单、商品、客户、库存或统计数据",
                "general_qa": "普通知识、技术、写作、翻译或解释问题，不需要真实业务数据",
                "metric_explanation": "解释业务指标、数据口径、统计概念或分析方法，不要求查询真实数据",
                "conversation": "问候、闲聊、感谢、情绪交流或简单对话",
                "clarification": "有潜在查询意图但缺少时间、对象、范围等关键信息，应先澄清",
                "unsupported": "要求写入、删除、修改数据，执行外部操作，越权或不安全的行为",
            },
        }
    }
    if args.binary:
        questions = {
            "intent": {
                "type": "choice",
                "instructions": "判断这个问题是否必须访问真实业务数据库才能回答。只有用户明确要求读取、统计、筛选、比较真实业务数据时选择 database_query；概念解释、技术问题、闲聊、澄清和写入操作都选择 non_database。",
                "criteria": {
                    "db_required": "需要访问真实业务数据库才能回答，例如查询、统计、筛选或比较订单、销售、商品、客户数据",
                    "no_db": "不需要访问真实业务数据库，例如概念解释、知识问答、闲聊、信息不足、写入或越权操作",
                },
            }
        }

    confusion: Counter[tuple[str, str]] = Counter()
    details = []
    start = time.perf_counter()
    for row in rows:
        result = agent.predict({"query": row["query"]}, questions)
        answer = result["answers"]["intent"]
        predicted = answer["choice"]
        if args.binary:
            gold = "db_required" if row["needs_database"] else "no_db"
        else:
            gold = row["intent"]
        confidence = float(answer.get("confidence", 0.0))
        confusion[(gold, predicted)] += 1
        details.append({"id": row["id"], "query": row["query"], "gold": gold, "predicted": predicted, "confidence": confidence, "needs_database": row["needs_database"], "original_intent": row["intent"]})

    correct = sum(item["gold"] == item["predicted"] for item in details)
    if args.binary:
        db_correct = sum(item["needs_database"] == (item["predicted"] == "db_required") for item in details)
    else:
        db_correct = sum(item["needs_database"] == (item["predicted"] == "database_query") for item in details)
    low_confidence = [item for item in details if item["confidence"] < 0.70]
    per_class = {}
    report_labels = ["db_required", "no_db"] if args.binary else LABELS
    for label in report_labels:
        own = [item for item in details if item["gold"] == label]
        per_class[label] = {"count": len(own), "accuracy": round(sum(item["gold"] == item["predicted"] for item in own) / len(own), 4) if own else 0.0}

    report = {
        "model": "convaiinnovations/laya/multilingual",
        "mode": "binary_database_gate" if args.binary else "six_way_intent",
        "device": args.device,
        "sample_count": len(details),
        "elapsed_seconds": round(time.perf_counter() - start, 2),
        "accuracy": round(correct / len(details), 4),
        "database_gate_accuracy": round(db_correct / len(details), 4),
        "low_confidence_count": len(low_confidence),
        "per_class": per_class,
        "confusion": {f"{gold}->{predicted}": count for (gold, predicted), count in sorted(confusion.items())},
        "errors": [item for item in details if item["gold"] != item["predicted"]],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("model", "device", "sample_count", "elapsed_seconds", "accuracy", "database_gate_accuracy", "low_confidence_count", "per_class")}, ensure_ascii=False, indent=2))
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
