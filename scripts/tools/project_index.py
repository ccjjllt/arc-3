#!/usr/bin/env python3
"""Refresh local project navigation from existing files; never run experiments."""
from __future__ import annotations

import argparse
from collections import defaultdict
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
NUMBER = re.compile(r"^(\d{3})(?:-|_)")
SCRIPT_NUMBER = re.compile(r"^[a-z]+_(\d{3})_")
CATEGORIES = {
    "analysis": "结果与证据分析",
    "checks": "手动 CPU 检查与预检",
    "build": "专用 Notebook 与输入包构建",
    "prepare": "实验输入准备",
    "replay": "前缀回放",
    "research": "专项研究工具",
    "tools": "通用日志与目录维护",
    "demos": "行为机制演示",
}


def link(source: Path, target: Path, label: str | None = None) -> str:
    relative = Path(os.path.relpath(target, source.parent)).as_posix()
    return f"[{label or target.name}]({relative})"


def collect() -> dict[str, dict[str, list[Path]]]:
    grouped = defaultdict(lambda: defaultdict(list))
    for category, folder in (
        ("计划", "docs/plan"), ("进展", "docs/progress"),
        ("交接", "docs/handoff"), ("研究笔记", "research/notes"),
        ("配置、冻结源码与审计记录", "experiments"),
        ("Notebook", "notebooks"), ("本地运行输出", "runs"),
    ):
        base = ROOT / folder
        if not base.is_dir():
            continue
        paths = base.rglob("*.md") if category == "研究笔记" else base.iterdir()
        for path in sorted(paths):
            match = NUMBER.match(path.name)
            if match:
                grouped[match[1]][category].append(path)
    for path in sorted((ROOT / "scripts").glob("*/*.py")):
        match = SCRIPT_NUMBER.match(path.name)
        if match:
            grouped[match[1]]["脚本"].append(path)
    return dict(sorted(grouped.items()))


def render() -> dict[Path, str]:
    grouped = collect()
    pages = {}
    index = ROOT / "docs/experiments/README.md"
    index_lines = [
        "# 实验索引", "", "由 `scripts/tools/project_index.py` 按实际目录生成。实验结论与运行状态见各编号的进展、研究笔记和原始记录。", "",
        "[项目首页](../../README.md) · [脚本目录](../../scripts/README.md) · [研究资料](../../research/README.md)", "",
        "| 编号 | 计划 / 进展 | 研究笔记 | Notebook | 配置与证据 | 脚本 | 本地输出 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for number, sections in grouped.items():
        page = ROOT / f"docs/experiments/{number}.md"
        doc_links = [link(index, p, kind) for kind in ("计划", "进展") for p in sections.get(kind, [])]
        counts = [str(len(sections.get(kind, []))) for kind in (
            "研究笔记", "Notebook", "配置、冻结源码与审计记录", "脚本", "本地运行输出")]
        index_lines.append(f"| {link(index, page, number)} | {' · '.join(doc_links) or '—'} | " + " | ".join(counts) + " |")
        lines = [f"# {number} 实验文件", "", "[全部实验](README.md) · [项目首页](../../README.md)", ""]
        for kind, paths in sections.items():
            lines.extend([f"## {kind}", ""])
            lines.extend(f"- {link(page, path)}" for path in paths)
            lines.append("")
        if "本地运行输出" in sections:
            lines.extend(["本地运行输出不纳入 Git；其他机器可能没有这些目录。", ""])
        pages[page] = "\n".join(lines)
    pages[index] = "\n".join(index_lines) + "\n"

    script_index = ROOT / "scripts/README.md"
    lines = ["# 脚本目录", "", "从项目根目录运行。按实验编号浏览见[实验索引](../docs/experiments/README.md)。", "",
             "## 通用入口", "",
             "以下三个入口被历史构建与冻结来源记录引用，保留原路径和内容。", ""]
    lines.extend(f"- {link(script_index, p)}" for p in sorted((ROOT / "scripts").glob("*.py")))
    for folder, title in CATEGORIES.items():
        paths = sorted((ROOT / "scripts" / folder).glob("*.py"))
        if paths:
            lines.extend(["", f"## {title} · `{folder}/`", ""])
            lines.extend(f"- {link(script_index, p)}" for p in paths)
    lines.extend(["", "构建、分析和检查脚本可能写出本地产物；具体参数与输入要求见脚本说明。", ""])
    pages[script_index] = "\n".join(lines)

    research_index = ROOT / "research/README.md"
    lines = ["# 研究资料", "", "[实验索引](../docs/experiments/README.md) · [项目首页](../README.md)", "",
             "## 通用总览", ""]
    lines.extend(f"- {link(research_index, p)}" for p in sorted((ROOT / "research/overview").glob("*.md")))
    lines.extend(["", "## 按实验编号的笔记", "",
                  "文件名和实验编号保持不变，目录按编号归组。跨实验笔记按文件名前三个数字存放。", ""])
    for number, sections in grouped.items():
        notes = sections.get("研究笔记", [])
        if notes:
            lines.append(f"- {link(research_index, ROOT / 'research/notes' / number, number)}：{len(notes)} 份 · "
                         + link(research_index, ROOT / f"docs/experiments/{number}.md", "实验入口"))
    lines.extend(["", "## 原始资料", ""])
    for folder, title in (
        ("snapshots", "官方、API 与讨论快照"), ("notebooks", "第三方 Notebook 与源码"),
        ("frontier", "前沿论文配套资料"), ("019-actual-wheel", "019 wheel 核验资料"),
        ("data", "本地数据与手动观察记录（Git 忽略）"),
        ("runtime-bundle", "基线运行时（Git 忽略）"),
    ):
        path = ROOT / "research" / folder
        if path.is_dir():
            lines.append(f"- {link(research_index, path, title)}")
    for path in sorted((ROOT / "research").glob("*.json")):
        lines.append(f"- {link(research_index, path)}")
    lines.append("")
    pages[research_index] = "\n".join(lines)

    for folder, title, description in (
        ("experiments", "实验配置与证据", "保存实验配置、冻结源码、构建检查和审计原件。既有文件保留原路径与字节，便于来源哈希与输入打包复核。"),
        ("notebooks", "实验 Notebook", "保存已构建或上传的 Notebook、metadata 与 manifest。不同版本、账号或上传尝试分别保留。"),
    ):
        page = ROOT / folder / "README.md"
        lines = [f"# {title}", "", description, "", "按编号浏览[完整实验索引](../docs/experiments/README.md)。", "",
                 "| 编号 | 当前目录条目 | 统一入口 |", "|---|---:|---|"]
        key = "Notebook" if folder == "notebooks" else "配置、冻结源码与审计记录"
        for number, sections in grouped.items():
            if key in sections:
                lines.append(f"| {number} | {len(sections[key])} | {link(page, ROOT / f'docs/experiments/{number}.md', '查看文件')} |")
        pages[page] = "\n".join(lines) + "\n"
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report stale navigation without writing files")
    args = parser.parse_args()
    pages = render()
    stale = [path for path, content in pages.items() if not path.is_file() or path.read_text() != content]
    if args.check:
        for path in stale:
            print(f"stale: {path.relative_to(ROOT)}")
        print(f"Checked {len(pages)} navigation pages; {len(stale)} stale.")
        raise SystemExit(bool(stale))
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(pages[path])
    print(f"Refreshed {len(stale)} of {len(pages)} navigation pages.")


if __name__ == "__main__":
    main()
