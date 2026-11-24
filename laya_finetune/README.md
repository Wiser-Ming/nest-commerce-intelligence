# 路由模型训练与评估

生产路由使用三个标签。只有 `database_query` 进入 Text-to-SQL。其余两类为 `non_database` 和 `clarification`。

训练从 [Laya 默认检查点](https://huggingface.co/convaiinnovations/laya) 初始化，冻结编码器并更新决策头。数据按样本来源 ID 确定性划分。训练集内部平衡采样，开发集用于温度拟合，测试集保留用于离线比较。样本以 [合成语料](../data/README.md) 为主，划分方法依照 `prepare_dataset.py` 中的实现。

在项目根目录执行：

```powershell
$env:HF_HOME = "$PWD/.model-cache"
uv run --locked python -m laya_finetune.prepare_dataset
uv run --locked python -m laya_finetune.train_head --device auto --epochs 8 --batch-size 4 --lr 0.001
uv run --locked python -m laya_finetune.evaluate_before_after --device auto
```

`--device auto` 优先使用 CUDA，未安装可用的 CUDA PyTorch 时使用 CPU。评估默认采用训练初始化使用的默认检查点。回放以 multilingual 为参照的历史口径时，追加 `--baseline multilingual`。

| 路径 | 内容 |
| --- | --- |
| `data/` | 训练、开发、测试划分 |
| `artifacts/shopkeeper-router-head/` | Laya 权重、模型配置和分词器 |
| `artifacts/before_after_report.json` | 对照指标、混淆矩阵和错分样本 |

生成物保留在本机。后端使用 `conf/app_config.yaml` 中的 `intent_router.model_path` 加载检查点。
