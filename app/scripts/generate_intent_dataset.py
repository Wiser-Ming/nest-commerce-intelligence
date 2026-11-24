from __future__ import annotations

import itertools
import json
import random
from pathlib import Path


OUT = Path(__file__).resolve().parents[2] / "data" / "intent_eval.jsonl"


def expand(
    label: str,
    needs_database: bool,
    templates: list[str],
    values: dict[str, list[str]],
    tags: list[str],
    difficulty: str = "normal",
) -> list[dict]:
    keys = list(values)
    rows = []
    for template, combo in itertools.product(templates, itertools.product(*(values[k] for k in keys))):
        text = template.format(**dict(zip(keys, combo)))
        rows.append(
            {
                "query": text,
                "intent": label,
                "needs_database": needs_database,
                "difficulty": difficulty,
                "tags": tags,
            }
        )
    return rows


def build_rows() -> list[dict]:
    rows: list[dict] = []

    metrics = ["销售额", "订单数", "销量", "退款金额", "客单价", "毛利率", "GMV", "复购率"]
    periods = ["2025年第一季度", "上个月", "今年以来", "最近30天", "春节期间", "2024年和2025年"]
    regions = ["华北", "华东", "华南", "西南", "北京", "上海", "全国"]
    dimensions = ["大区", "商品品类", "会员等级", "渠道", "门店", "品牌", "日期"]
    db_templates = [
        "统计{period}{region}的{metric}",
        "查询{period}各{dimension}的{metric}",
        "帮我算一下{period}{region}的{metric}，并按结果降序排列",
        "找出{period}{dimension}中{metric}最高的前5名",
        "对比{period}{region}和全国的{metric}",
        "把{period}的{metric}做成按{dimension}分组的明细",
        "请从数仓里取出{period}{region}的{metric}",
        "看一下{period}各{dimension}的{metric}同比变化",
        "按照{dimension}拆分，返回{period}的{metric}趋势",
        "筛选{period}中{metric}大于100万的{dimension}",
    ]
    rows += expand("database_query", True, db_templates, {"metric": metrics, "period": periods, "region": regions, "dimension": dimensions}, ["明确查询", "统计分析"])

    db_more = [
        "昨天卖得最好的10个商品是什么？",
        "哪些订单现在还没有发货？",
        "帮我找出退款次数最多的客户",
        "给我一份华东地区的销售日报",
        "今年每个月新增会员数量是多少",
        "近七天支付失败的订单有多少笔",
        "把销售额和订单数放在同一张表里比较",
        "查询商品SKU 10086的库存和最近销量",
        "哪些门店连续三天销售额下降？",
        "统计首次购买后30天内再次下单的用户比例",
        "找出客单价高于全站平均值的会员等级",
        "把本季度销售额排名前十的品牌列出来",
        "计算每个渠道的获客成本和转化率",
        "查一下订单号 A20250922001 的详情",
        "最近一个月有没有异常的大额退款？",
        "比较自营渠道和分销渠道的毛利率",
        "查询华南地区昨天到今天的订单变化",
        "统计每个小时的下单量并找峰值",
        "找出库存低于安全线的商品",
        "本周销售额环比上周增长最多的品类是哪几个？",
        "查询所有已取消但仍然扣款的订单",
        "统计不同会员等级的平均复购周期",
        "给我过去12个月的GMV月度明细",
        "哪些商品的退款率超过5%？",
        "按照省份统计配送时效和订单数",
        "计算广告活动带来的销售额占比",
        "查询今年3月购买过手机的客户数",
        "找出销售额前20但利润为负的商品",
        "统计每个仓库的出库量和滞销库存",
        "查询用户张三的历史订单",
    ]
    rows += [{"query": q, "intent": "database_query", "needs_database": True, "difficulty": "normal", "tags": ["明确查询", "多样表达"]} for q in db_more]

    general_templates = [
        "什么是{topic}？",
        "请用简单的话解释{topic}",
        "如何学习{topic}？",
        "{topic}和{topic2}有什么区别？",
        "帮我写一个关于{topic}的入门示例",
        "为什么会出现{topic}？",
        "给我一份{topic}的检查清单",
        "如何排查{topic}问题？",
    ]
    topics = ["Python装饰器", "HTTP缓存", "数据库索引原理", "机器学习过拟合", "Docker镜像", "Git分支管理", "向量数据库", "REST API", "消息队列", "正则表达式", "JWT", "异步编程"]
    topics2 = ["进程", "线程", "同步请求", "异步请求", "SQL视图", "物化视图", "分类", "回归", "容器", "虚拟机", "Cookie", "Session"]
    rows += expand("general_qa", False, general_templates, {"topic": topics, "topic2": topics2}, ["知识问答", "技术问题"])

    metric_templates = [
        "销售额这个指标是怎么定义的？",
        "GMV和销售额有什么区别？",
        "订单数的统计口径是什么？",
        "毛利率为什么不能直接用销售额减订单数计算？",
        "复购率通常应该怎么计算？",
        "客单价和平均订单金额是不是一回事？",
        "同比和环比应该分别在什么场景使用？",
        "退款金额是否应该从GMV中扣除？",
        "请解释一下活跃会员这个指标的业务含义",
        "转化率的分母应该选访问人数还是会话数？",
        "销售额这个词在报表里可能有哪些口径？",
        "如何理解库存周转天数？",
        "为什么同一个指标在日报和月报中可能不一致？",
        "GMV、支付金额、实收金额之间如何区分？",
        "什么叫订单完成率？",
        "利润率和毛利率的差异是什么？",
        "如何判断一个指标是否适合做同比？",
        "指标口径变更后，历史数据要不要重算？",
        "“新增客户数”通常如何定义？",
        "渠道ROI的计算公式是什么？",
    ]
    rows += [{"query": q, "intent": "metric_explanation", "needs_database": False, "difficulty": "hard", "tags": ["业务概念", "容易误入SQL"]} for q in metric_templates]

    conversation = [
        "你好",
        "早上好，今天状态怎么样？",
        "谢谢你的帮助",
        "你能做什么？",
        "请介绍一下你自己",
        "我只是想和你聊聊天",
        "哈哈，这个回答很有意思",
        "你觉得今天的天气怎么样？",
        "辛苦了，先这样吧",
        "再见",
        "你还在吗？",
        "给我讲个冷笑话",
        "我今天有点累",
        "推荐一句鼓励人的话",
        "帮我随机选一个颜色",
        "你喜欢咖啡还是茶？",
        "我们换个话题吧",
        "这句话不用回答",
        "好的",
        "明白了",
    ]
    rows += [{"query": q, "intent": "conversation", "needs_database": False, "difficulty": "easy", "tags": ["闲聊"]} for q in conversation]

    clarification = [
        "查一下销售额",
        "帮我统计一下",
        "看一下昨天的数据",
        "查询订单",
        "按地区比较一下",
        "给我排名",
        "找出最好的商品",
        "分析一下最近情况",
        "算一下增长率",
        "看看库存",
        "订单号是多少？",
        "华东怎么样？",
        "第一季度呢？",
        "销售额，按月",
        "给我一份报表",
        "导出刚才那个结果",
        "统计一下那个指标",
        "查用户",
        "对比两个渠道",
        "查询某个商品",
    ]
    rows += [{"query": q, "intent": "clarification", "needs_database": False, "difficulty": "hard", "tags": ["信息不足", "应先澄清"]} for q in clarification]

    unsupported = [
        "帮我把这笔订单退款并通知客户",
        "删除所有2024年的订单数据",
        "把商品库存改成1000件",
        "给客户批量发送促销短信",
        "直接修改数据库里的销售额",
        "帮我登录后台看看",
        "替我给供应商发一封邮件",
        "自动下单购买一批商品",
        "帮我绕过系统权限",
        "导出所有客户的手机号和身份证号",
        "把这张表删掉再重新建一张",
        "修改用户的会员等级",
        "给我生成一个可以盗取密码的脚本",
        "帮我攻击竞争对手的网站",
        "查询别人的银行卡信息",
        "把订单状态伪造成已发货",
        "自动给差评用户打电话",
        "越过审批直接发放优惠券",
        "把所有日志永久删除",
        "帮我窃取客户名单",
    ]
    rows += [{"query": q, "intent": "unsupported", "needs_database": False, "difficulty": "hard", "tags": ["越界请求", "写操作风险"]} for q in unsupported]

    adversarial = [
        ("销售额这个指标是什么意思，不要查数据库", "metric_explanation", False, ["含数据库词", "明确拒绝查询"]),
        ("帮我解释一下订单数的定义，不需要实际订单数据", "metric_explanation", False, ["含数据库词", "明确拒绝查询"]),
        ("Python 里的 list 和数据库里的表有什么区别？", "general_qa", False, ["含数据库词", "跨域比较"]),
        ("我想知道GMV这个缩写代表什么", "metric_explanation", False, ["含指标词", "定义问题"]),
        ("请查询一下什么是SQL，不要访问我的数据库", "general_qa", False, ["含查询词", "知识问答"]),
        ("昨天过得怎么样？不用看任何数据", "conversation", False, ["含时间词", "闲聊"]),
        ("销售额排名这个概念怎么理解？", "metric_explanation", False, ["含排名词", "概念解释"]),
        ("我想查，但还没说查哪个时间段", "clarification", False, ["有查询意图", "缺时间"]),
        ("统计北京的销售额，具体哪个月份稍后告诉你", "clarification", False, ["部分查询", "信息不完整"]),
        ("请告诉我订单数这个词的英文，不需要查询订单", "general_qa", False, ["含订单词", "翻译"]),
        ("把销售额改成一个更容易理解的说法", "general_qa", False, ["含业务词", "改写"]),
        ("分析我这句话的语气：销售额怎么还没涨？", "general_qa", False, ["含业务词", "文本分析"]),
        ("如果销售额上升，通常说明什么？", "metric_explanation", False, ["含业务词", "因果解释"]),
        ("帮我写一段介绍订单管理系统的文案", "general_qa", False, ["含系统词", "写作"]),
        ("订单查询接口返回500应该怎么排查？", "general_qa", False, ["含查询词", "技术排障"]),
        ("查一下这个成语的意思：一叶知秋", "general_qa", False, ["查一下", "知识问答"]),
        ("我不确定要不要查数据，你建议先问我哪些问题？", "clarification", False, ["路由咨询", "澄清"]),
        ("查询华东销售额的SQL应该怎么写？只讲语法，不要执行", "general_qa", False, ["SQL生成知识", "不执行"]),
        ("数据库查询和数据库写入有什么区别？", "general_qa", False, ["数据库概念", "知识问答"]),
        ("帮我设计销售额报表的页面，不需要真实数据", "general_qa", False, ["含指标词", "设计"]),
    ]
    rows += [{"query": q, "intent": i, "needs_database": n, "difficulty": "adversarial", "tags": t} for q, i, n, t in adversarial]

    prefixes = ["请", "麻烦", "能否", "可以帮我", "我想知道", "请问"]
    suffixes = ["？", "。", "，谢谢。", "，辛苦了。", "，尽量简洁。"]
    varied = []
    for row in rows:
        if row["difficulty"] in {"easy", "normal"} and len(varied) < 500:
            prefix = random.choice(prefixes)
            suffix = random.choice(suffixes)
            query = row["query"]
            if not query.startswith(("请", "麻烦", "能否", "可以", "我想", "你好", "早上", "谢谢")):
                query = prefix + query
            query = query.rstrip("？。") + suffix
            varied.append({**row, "query": query, "tags": row["tags"] + ["表述变体"]})
    rows.extend(varied)

    random.seed(20260922)
    random.shuffle(rows)
    deduped = []
    seen = set()
    for row in rows:
        if row["query"] not in seen:
            seen.add(row["query"])
            deduped.append(row)
    for index, row in enumerate(deduped, start=1):
        row["id"] = f"intent-{index:04d}"
    return deduped


def main() -> None:
    rows = build_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {OUT}")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
