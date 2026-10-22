"""Manually run offline 019 build, native-writefile and control checks.

Does not start a model, import a game, execute recorded model code or contact a
network. Mounted checkpoint audit and real HTTP/serving remain separate stages.
"""
from __future__ import annotations

import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main():
    import nbformat
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.inputtransformer2 import TransformerManager
    from arc3_research.ple_microbench import cpu_check, validate_suite
    from arc3_research.ple_session import validate_config, normalized_args, resolve_inputs, audit_wheel_sources
    from arc3_research.ple_weights import decode_e4m3fn
    import math
    import zipfile

    records = []
    def checked(name, detail=None):
        records.append({"name": name, "passed": True, "detail": detail})

    checked("client_in_memory_protocol", cpu_check())
    suite_path = ROOT / "experiments/019-suite.json"
    checked("frozen_public_suite", validate_suite(json.loads(suite_path.read_text())))
    assert decode_e4m3fn(0x7e) == 448 and decode_e4m3fn(0x38) == 1 and math.isnan(decode_e4m3fn(0x7f))
    checked("fp8_boundary_values")
    shell, transformer = InteractiveShell.instance(), TransformerManager()
    for suffix in ["019-fp8-ple-cpu", "019-fp8-ple"]:
        directory = ROOT / "notebooks" / suffix
        if not directory.exists():
            continue
        notebook = nbformat.read(directory / "experiment.ipynb", as_version=4)
        nbformat.validate(notebook)
        meta = json.loads((directory / "kernel-metadata.json").read_text())
        manifest = json.loads((directory / "build-manifest.json").read_text())
        config = manifest["config"]
        validate_config(config)
        assert meta["id"].startswith("jiyujia/") and meta["is_private"] and not meta["enable_internet"]
        assert meta["enable_gpu"] == (config["mode"] == "microbench")
        assert hashlib.sha256((directory / "experiment.ipynb").read_bytes()).hexdigest() == manifest["notebook_sha256"]
        for key in ["account", "server_seed", "hard_limit_seconds", "phase_order"]:
            bad = deepcopy(config); bad[key] = None
            try:
                validate_config(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("Accepted changed frozen control: " + key)
        count = 0
        with tempfile.TemporaryDirectory(prefix="arc3-019-writefile-") as temporary:
            root = Path(temporary)
            for index, cell in enumerate(notebook.cells):
                if cell.cell_type != "code":
                    continue
                compile(transformer.transform_cell(cell.source), f"{suffix}:cell{index}", "exec")
                if "019-static-json-payload" in cell.metadata.get("tags", []):
                    # Only the generated XZ-to-JSON cell is executed here.
                    # Its decoded strings remain data, including model code.
                    code = cell.source.replace("/kaggle/working/019-code/", str(root) + "/")
                    namespace = {"Path": Path}
                    exec(compile(code, "static-json-decoder", "exec"), namespace)
                    assert (root / "suite.json").read_bytes() == suite_path.read_bytes()
                    assert hashlib.sha256((root / "suite.json").read_bytes()).hexdigest() == manifest["payload"]["sha256"]["suite.json"]
                    continue
                if not cell.source.startswith("%%writefile /kaggle/working/019-code/"):
                    continue
                header, body = cell.source.split("\n", 1)
                relative = header.removeprefix("%%writefile /kaggle/working/019-code/")
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    result = shell.run_cell("%%writefile " + str(target) + "\n" + body, store_history=False)
                assert result.success and target.read_text() == body
                if relative in manifest["payload"]["sha256"]:
                    assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest["payload"]["sha256"][relative]
                if relative.endswith(".py"):
                    compile(body, relative, "exec")
                elif relative.endswith(".json"):
                    json.loads(body)
                count += 1
            # Pinned installed-runtime gate exercised against actual ZIP bytes.
            wheelhouse = root / "wheelhouse/wheels"; wheelhouse.mkdir(parents=True)
            with zipfile.ZipFile(wheelhouse / "sglang-fixture.whl", "w") as archive:
                archive.writestr("sglang/example.py", "fixture\n")
            expected = {"sglang/example.py": hashlib.sha256(b"fixture\n").hexdigest()}
            assert audit_wheel_sources(wheelhouse.parent, expected)["passed"]
            assert not audit_wheel_sources(wheelhouse.parent, {"sglang/example.py": "0" * 64})["passed"]
            specs = config["inputs"]
            for key, relative in specs.items():
                target = root / "inputs" / relative; target.mkdir(parents=True)
                names = ["requirements.lock", "wheels", "hot_tokens_64k.pt"] if key == "wheelhouse" else ["config.json", "model.safetensors.index.json"]
                for name in names:
                    (target / name).write_text("{}")
            assert set(resolve_inputs(specs, root / "inputs")) == set(specs)
        checked(suffix + ":native_payload_and_config", {"payload_cells_written": count, "total_cells": len(notebook.cells), "notebook_sha256": manifest["notebook_sha256"]})
    args = ["sglang", "serve", "--model-path", "one", "--random-seed", "190018", "--max-running-requests", "10"]
    other = list(args); other[3] = "two"
    assert normalized_args(args) == normalized_args(other)
    other[-1] = "9"
    assert normalized_args(args) != normalized_args(other)
    checked("serving_comparison_preserves_nonpath_controls")
    report = {"passed": True, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "checks": records, "model_calls": 0, "game_actions": 0, "network_calls": 0,
              "limits": ["Only native writefile cells executed, redirected to temporary paths.",
                         "No real mounted model tensors, CUDA runtime or real server HTTP tested by this command.",
                         "The separate ple_weights synthetic corruption checks and remote CPU audit retain their own reports."]}
    destination = ROOT / "experiments/019-preparation/cpu-build-check.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": True, "checks": len(records), "report": str(destination)}))


if __name__ == "__main__":
    main()
