"""将电商问数的 yaml 元数据转换为 Dify 知识库可导入的 Markdown 文件。

读取 实战项目-电商问数/yaml/ 下的全量元数据，
生成三个按"三路召回"组织的文档：
  01-表字段库.md   — 每张表一个章节（字段/类型/别名/说明/示例值）
  02-指标库.md     — 每个指标一个章节（定义/关联字段/别名）
  03-真实取值库.md — 每个带示例值的字段一个章节（字段真实取值列表）

用法: python dify/gen_kb_docs.py
"""

import sys
from pathlib import Path

import yaml

ROOT = Path("C:/Users/Administrator/Desktop/电商问数")
YAML_DIR = ROOT / "实战项目-电商问数" / "yaml"
OUT_DIR = ROOT / "dify" / "知识库导入"


def load_yaml(name: str) -> list:
    """读取 yaml 文件并返回列表，文件缺失时直接报错退出。"""
    path = YAML_DIR / name
    if not path.exists():
        sys.exit(f"缺少源文件: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        sys.exit(f"文件内容不是列表结构: {path}")
    return data


def fmt_examples(examples: object) -> str:
    """把示例值列表格式化为一行可读文本。"""
    if not examples:
        return "（无）"
    return "、".join(str(x) for x in examples)


def render_tables(tables: list) -> str:
    """渲染表字段库文档：每张表一个 ## 章节（不带一级标题，避免产生空分段）。"""
    parts: list[str] = []
    for t in tables:
        parts.append(f"## 表 {t['name']}（{t.get('role', '')}）\n")
        parts.append(f"说明：{t.get('description', '')}\n")
        for c in t.get("columns", []):
            alias = "、".join(c.get("alias", [])) or "（无）"
            parts.append(
                f"- 字段 `{c['name']}`（{c.get('type', '')}，角色 {c.get('role', '')}）："
                f"{c.get('description', '')}；别名：{alias}；"
                f"示例值：{fmt_examples(c.get('examples'))}"
            )
        parts.append("")
    return "\n".join(parts)


def render_metrics(metrics: list) -> str:
    """渲染指标库文档：每个指标一个 ## 章节（不带一级标题）。"""
    parts: list[str] = []
    for m in metrics:
        alias = "、".join(m.get("alias", [])) or "（无）"
        cols = "、".join(m.get("relevant_columns", [])) or "（无）"
        parts.append(f"## 指标 {m['name']}\n")
        parts.append(f"定义：{m.get('description', '')}\n")
        parts.append(f"关联字段：{cols}")
        parts.append(f"别名：{alias}\n")
    return "\n".join(parts)


def render_values(tables: list) -> str:
    """渲染真实取值库：每个带示例值的字段一个 ## 章节（不带一级标题）。"""
    parts: list[str] = []
    for t in tables:
        for c in t.get("columns", []):
            examples = c.get("examples")
            if not examples:
                continue
            parts.append(f"## 字段 {t['name']}.{c['name']}\n")
            parts.append(f"含义：{c.get('description', '')}\n")
            parts.append(f"真实取值：{fmt_examples(examples)}\n")
    return "\n".join(parts)


def main() -> None:
    """主入口：读取 yaml 并写出三个 Markdown 文件。"""
    tables = load_yaml("table_infos.yaml")
    metrics = load_yaml("metric_infos.yaml")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        OUT_DIR / "01-表字段库.md": render_tables(tables),
        OUT_DIR / "02-指标库.md": render_metrics(metrics),
        OUT_DIR / "03-真实取值库.md": render_values(tables),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"已生成: {path} ({len(content)} 字符)")


if __name__ == "__main__":
    main()
