/**
 * Tailwind CSS 主题配置
 * 定义前端项目的字体、颜色和阴影扩展
 */
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"LXGW WenKai Screen"',
          '"Noto Sans SC"',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
        mono: ['"JetBrains Mono"', '"SFMono-Regular"', "Consolas", "monospace"],
      },
      colors: {
        parchment: "#eef1ed",
        ink: "#172019",
        soot: "#0d120f",
        moss: "#6c8d3f",
        brass: "#d8ef62",
        tomato: "#de725f",
        mist: "#d7e0d4",
      },
      boxShadow: {
        line: "0 1px 0 rgba(32, 32, 29, 0.08)",
        panel: "0 24px 70px rgba(45, 41, 37, 0.16)",
      },
    },
  },
  plugins: [],
} satisfies Config;
