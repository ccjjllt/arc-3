"""Read-only source analysis of archived Kaggle responses; never executes notebook code."""
from __future__ import annotations

import ast
import collections
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOKS = HERE.parent
OLD = {
    "jeroencottaar__tufa-labs-duck-harness-june-30-milestone-winner": "jeroencottaar__tufa-labs-duck-harness-june-30-milestone-winner.ipynb",
    "scottlegrand__taaf-flashnext-sheetu12b-0922": "scottlegrand__taaf-flashnext-sheetu12b-0922.ipynb",
    "lordhansolo__built-on-tufa-labs-duck-harness-milestone-2": "lordhansolo__built-on-tufa-labs-duck-harness-milestone-2.ipynb",
    "sirikilohit__arc-agi-3-duck-18-1gc-submit": "sirikilohit__arc-agi-3-duck-18-1gc-submit.ipynb",
    "dfranzen__arc-agi-3-milestone-2-solution": "dfranzen__arc-agi-3-milestone-2-solution.ipynb",
    "jingshuifu__arc3-m2-solution-v2": "2026-10-13/jingshuifu-m2-v2/mcp-source.ipynb",
    "jingshuifu__arc3-m2-solution-v3": "2026-10-13/jingshuifu-m2-v2/mcp-source.ipynb",
    "heliosli__try-merging-it-you-might-get-lucky-and-win-gold": "2026-10-13/heliosli-update/mcp-source.ipynb",
    "sujanmajhisuzan__arc-agi-3-m2-top-submission": "2026-10-13/sujan-update/mcp-source.ipynb",
    "professorice__arc-agi-3-m2-qwen3-8-27b": "dfranzen__arc-agi-3-milestone-2-solution.ipynb",
}


def source(cell):
    text = cell.get("source", "")
    return "".join(text) if isinstance(text, list) else text


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    rows = []
    for directory in sorted(HERE.iterdir()):
        if not directory.is_dir():
            continue
        response_path = directory / "mcp-response.json"
        response = json.loads(response_path.read_text())
        data = json.loads(response["content"][0]["text"])
        metadata = data["metadata"]
        payload = data["blob"]["source"]
        notebook = json.loads(payload)
        cells = [source(c) for c in notebook["cells"]]
        row = {
            "ref": metadata["ref"],
            "version": metadata["current_version_number"],
            "metadata_last_run_time_as_returned": metadata["last_run_time"],
            "source_payload_sha256": sha(payload.encode()),
            "source_file_sha256": sha((directory / "source.ipynb").read_bytes()),
            "cell_source_sha256": sha("\n".join(cells).encode()),
            "response_file_sha256": sha(response_path.read_bytes()),
            "cell_count": len(cells),
            "cell_types": dict(collections.Counter(c["cell_type"] for c in notebook["cells"])),
            "outputs_count_in_returned_source": sum(len(c.get("outputs", [])) for c in notebook["cells"]),
            "score_bound_to_exact_source": None,
            "submission_id_bound_to_exact_source": None,
        }
        if directory.name in OLD:
            old_path = NOTEBOOKS / OLD[directory.name]
            old_cells = [source(c) for c in json.loads(old_path.read_text())["cells"]]
            row.update({
                "compared_to": str(old_path.relative_to(NOTEBOOKS)),
                "same_cell_sources": cells == old_cells,
                "changed_cells_zero_based": [i for i, (a, b) in enumerate(zip(old_cells, cells)) if a != b],
            })
            (directory / "source.diff").write_text("".join(difflib.unified_diff(
                "\n\n".join(old_cells).splitlines(True),
                "\n\n".join(cells).splitlines(True),
                fromfile=str(old_path.relative_to(NOTEBOOKS)),
                tofile=str((directory / "source.ipynb").relative_to(NOTEBOOKS)),
            )))
        rows.append(row)
    report = {
        "client_date_timezone": "2026-10-17 Asia/Shanghai",
        "method": "Kaggle MCP search_notebooks ScoreDescending/DateRun top 20 and get_notebook_info current source; static cell diffs and literal extraction only",
        "notebook_code_executed": False,
        "gpu_started": False,
        "submission_created": False,
        "remote_outputs_downloaded": False,
        "score_binding": "No returned API field binds a numerical leaderboard score or submission ID to these exact source payloads.",
        "notebooks": rows,
    }
    (HERE / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"notebooks": len(rows), "unchanged": [r["ref"] for r in rows if r.get("same_cell_sources")]}))


if __name__ == "__main__":
    main()
