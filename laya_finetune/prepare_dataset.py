from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "intent_eval.jsonl"
OUT = ROOT / "laya_finetune" / "data"
LABELS = ["database_query", "non_database", "clarification"]

REAL_SAMPLES = [
    ("统计 2025 年第一季度各大区的 GMV，并按 GMV 从高到低排序", "database_query", "real_log"),
    ("统计 2025 年 3 月各商品品类的销量和销售额", "database_query", "real_log"),
    ("按会员等级统计 2025 年第一季度的订单数和销售额", "database_query", "real_log"),
    ("你能告诉我我前面两个问题是什么吗", "non_database", "real_log_misroute"),
]

CLARIFICATION_EXPANSIONS = [
    "查一下{period}{region}的数据",
    "查一下{period}的{metric}",
    "统计{region}的{metric}",
    "查询{dimension}的情况",
    "帮我看看{period}的数据",
    "给我{dimension}排名",
    "分析一下{period}{region}的表现",
    "对比一下{dimension}的{metric}",
    "找出{region}最好的商品",
    "看看{period}的库存",
    "算一下{period}的增长率",
    "查询{region}的订单",
    "统计{dimension}的情况",
    "看一下{metric}",
    "帮我分析{period}的结果",
]
PERIODS = ["昨天", "上个月", "今年", "第一季度", "最近30天", "春节期间", "本周"]
METRICS = ["销售额", "订单数", "销量", "GMV", "退款金额", "毛利率", "客单价"]
REGIONS = ["华北", "华东", "华南", "北京", "上海", "全国"]
DIMENSIONS = ["各大区", "各品类", "会员等级", "销售渠道", "门店"]
GENERAL_TOPICS = ["Python装饰器", "HTTP缓存", "Docker镜像", "Git分支", "机器学习过拟合", "正则表达式", "JWT", "异步编程", "向量数据库", "消息队列", "SQL索引", "REST API"]
GENERAL_TEMPLATES = [
    "什么是{topic}？",
    "请解释一下{topic}",
    "如何学习{topic}？",
    "{topic}有什么用？",
    "请给我一个{topic}的简单例子",
    "如何排查{topic}相关问题？",
]


def normalize_label(row: dict) -> str:
    if row["intent"] == "database_query":
        return "database_query"
    if row["intent"] == "clarification":
        return "clarification"
    return "non_database"


def make_rows() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        source = json.loads(line)
        query = source["query"].strip()
        if query and query not in seen:
            seen.add(query)
            rows.append({"query": query, "label": normalize_label(source), "source": "generated", "source_id": source["id"], "tags": source["tags"]})

    for query, label, source in REAL_SAMPLES:
        if query not in seen:
            seen.add(query)
            rows.append({"query": query, "label": label, "source": source, "source_id": source, "tags": ["真实日志"]})

    for template in CLARIFICATION_EXPANSIONS:
        for period in PERIODS:
            for metric in METRICS:
                for region in REGIONS:
                    for dimension in DIMENSIONS:
                        query = template.format(period=period, metric=metric, region=region, dimension=dimension)
                        if query not in seen:
                            seen.add(query)
                            rows.append({"query": query, "label": "clarification", "source": "clarification_synthetic", "source_id": hashlib.sha1(query.encode()).hexdigest()[:12], "tags": ["信息不完整", "合成扩展"]})

    for template in GENERAL_TEMPLATES:
        for topic in GENERAL_TOPICS:
            query = template.format(topic=topic)
            if query not in seen:
                seen.add(query)
                rows.append({"query": query, "label": "non_database", "source": "general_synthetic", "source_id": hashlib.sha1(query.encode()).hexdigest()[:12], "tags": ["知识问答", "合成扩展"]})

    return rows


def split_by_query(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["source_id"], []).append(row)
    grouped = list(groups.values())
    random.Random(20260922).shuffle(grouped)
    buckets = {"train": [], "dev": [], "test": []}
    for group in grouped:
        digest = int(hashlib.sha1(group[0]["source_id"].encode()).hexdigest()[:8], 16) % 100
        target = "train" if digest < 70 else "dev" if digest < 85 else "test"
        buckets[target].extend(group)
    return buckets


def rebalance(rows: list[dict], limit: int, seed: int, oversample: bool = False) -> list[dict]:
    grouped = {label: [row for row in rows if row["label"] == label] for label in LABELS}
    rng = random.Random(seed)
    for values in grouped.values():
        rng.shuffle(values)
    selected = []
    for label in LABELS:
        values = grouped[label]
        if oversample and values:
            values = [values[index % len(values)] for index in range(limit)]
        selected.extend(values[:limit])
    rng.shuffle(selected)
    return selected


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for index, row in enumerate(rows, 1):
            item = {
                "id": f"{path.stem}-{index:04d}",
                "state": {"query": row["query"]},
                "question": {
                    "type": "choice",
                    "instructions": "判断用户问题应该进入哪个处理分支。只有明确要求读取真实业务数据时才进入数据库查询。",
                    "criteria": {
                        "database_query": "需要查询、统计、筛选、比较真实业务数据库中的销售、订单、商品、客户或库存数据",
                        "non_database": "不需要读取真实业务数据库，包括知识问答、技术问题、指标解释、闲聊、写作、翻译或越权写操作",
                        "clarification": "有潜在业务查询意图，但缺少时间范围、对象、指标或其他关键条件，需要先澄清",
                    },
                },
                "label": row["label"],
                "source": row["source"],
                "tags": row["tags"],
            }
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    rows = make_rows()
    splits = split_by_query(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    train = rebalance(splits["train"], 500, 1, oversample=True)
    dev = rebalance(splits["dev"], 100, 2)
    test = rebalance(splits["test"], 100, 3)
    for name, values in (("train", train), ("dev", dev), ("test", test)):
        write_jsonl(OUT / f"{name}.jsonl", values)
        print(name, len(values), {label: sum(x["label"] == label for x in values) for label in LABELS})
    print("all_rows", len(rows), "output", OUT)


if __name__ == "__main__":
    main()
