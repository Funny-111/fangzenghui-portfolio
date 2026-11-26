/**
 * Tailwind CSS 主题配置
 * 定义前端项目的字体、颜色和阴影扩展
 *
 * 主题策略：旧 token（parchment/ink/moss…）只改值不改名，组件 72 处类名零改动；
 * 新组件使用语义层（surface、text 语义、brand、pastel、warning 系）。
 */
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Inter",
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          '"Noto Sans SC"',
          "sans-serif",
        ],
        mono: ['"JetBrains Mono"', '"SFMono-Regular"', "Consolas", "monospace"],
      },
      colors: {
        // —— 旧 token（值已映射为白底 SaaS 体系，名字保留以兼容存量类名）——
        parchment: "#ffffff",
        ink: "#111827",
        soot: "#374151",
        moss: "#2f6b4f",
        brass: "#92400e",
        tomato: "#d64e3a",
        mist: "#f3f4f6",
        // —— 语义层：中性灰阶（新组件专用）——
        surface: "#ffffff",
        "surface-subtle": "#f9fafb",
        "surface-muted": "#f3f4f6",
        "surface-sunken": "#f1f3f5",
        line: "#e5e7eb",
        "line-strong": "#d1d5db",
        primary: "#111827",
        secondary: "#6b7280",
        tertiary: "#9ca3af",
        inverse: "#ffffff",
        // —— 语义层：品牌绿（保留 moss 基因，补层级）——
        brand: {
          50: "#eef6f1",
          100: "#d9ebe2",
          200: "#b7dac9",
          500: "#2f6b4f",
          600: "#2a6148",
          700: "#235240",
        },
        // —— 语义层：warning（承接原硬编码 #a16207 系）——
        warning: "#92400e",
        // —— 语义层：pastel 推荐卡（卡片底/图标块底/强调色）——
        "pastel-yellow": { card: "#fbf6e6", icon: "#f5e9c4", accent: "#9a6b12" },
        "pastel-purple": { card: "#f4f1fb", icon: "#e6dff8", accent: "#6b54ae" },
        "pastel-pink": { card: "#fcf0f4", icon: "#f6dde8", accent: "#b0506f" },
        "pastel-blue": { card: "#eef5fd", icon: "#d9e9fb", accent: "#3b6cb5" },
      },
      boxShadow: {
        line: "0 1px 2px rgba(17, 24, 39, 0.05)",
        panel: "0 8px 30px rgba(17, 24, 39, 0.08)",
        card: "0 1px 3px rgba(17, 24, 39, 0.06), 0 1px 2px rgba(17, 24, 39, 0.04)",
        pop: "0 16px 40px rgba(17, 24, 39, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;
