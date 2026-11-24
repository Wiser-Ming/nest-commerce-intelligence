# Laya 意图评估数据

`intent_eval.jsonl` 是为电商问数 Agent 生成的中文评估集。每行一条 JSON，字段如下：

- `query`：用户输入
- `intent`：细分类别
- `needs_database`：是否需要访问真实业务数据库
- `difficulty`：`easy`、`normal`、`hard` 或 `adversarial`
- `tags`：场景标签
- `id`：稳定样本编号

当前类别包括：

- `database_query`：真实业务数据查询
- `general_qa`：知识、技术、写作和翻译问题
- `metric_explanation`：指标口径和业务概念解释
- `conversation`：闲聊和简单对话
- `clarification`：信息不完整，需要先澄清
- `unsupported`：写入、删除、越权或外部操作请求

生成数据：

```powershell
.\.venv-gpu\Scripts\python.exe app\scripts\generate_intent_dataset.py
```

用 GPU Laya 做六分类评估：

```powershell
$env:HF_HOME = "$PWD\.model-cache"
.\.venv-gpu\Scripts\python.exe app\scripts\evaluate_laya_intent.py --per-intent 30 --device cuda
```

只评估“是否需要访问数据库”的二分类门控：

```powershell
$env:HF_HOME = "$PWD\.model-cache"
.\.venv-gpu\Scripts\python.exe app\scripts\evaluate_laya_intent.py --per-intent 30 --binary --device cuda
```
