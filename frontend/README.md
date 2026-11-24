# NEST 前端

React、TypeScript、Vite 与 Tailwind CSS 构建的电商查询工作台。输入支持中文、示例模板和浏览器侧取消。查询响应以 SSE 更新路由反馈、执行轨迹及结果表格。

```sh
pnpm install --frozen-lockfile
pnpm dev
pnpm build
```

Vite 默认将 `/api` 代理到 `http://127.0.0.1:8000`。参见 [环境配置模板](.env.example) 中的 `VITE_DEV_PROXY_TARGET` 与 `VITE_API_BASE_URL`。生产部署采用同源 API 反代时，避免对 SSE 使用代理缓冲。

后端与基础设施的运行方式见 [项目 README](../README.md)。
