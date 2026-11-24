# BGE Embedding 服务

默认使用 CPU 版 Hugging Face Text Embeddings Inference 运行 `BAAI/bge-large-zh-v1.5`，向量维度为 1024。服务通过 `127.0.0.1:8081` 提供 `/embed`、`/health` 接口，模型缓存保存在 Compose 的 `embedding_cache` 卷。

GPU 部署可通过 Compose override 指定对应的 TEI 镜像与 GPU 资源。选择方式见 [TEI 硬件支持](https://huggingface.co/docs/text-embeddings-inference/main/en/supported_models)。
