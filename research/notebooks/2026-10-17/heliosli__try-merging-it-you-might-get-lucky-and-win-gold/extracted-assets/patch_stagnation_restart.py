"""Apply the single V4 policy change to the exact original harness."""
import ast
import hashlib
from pathlib import Path
import sys

ORIGINAL_BLOB = "84a9cdda9c851ea2dcf3eea9f0b3158d437bea16"


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise RuntimeError("Expected exactly one patch anchor: " + before[:100])
    return source.replace(before, after, 1)


def apply(root):
    root = Path(root)
    path = root / "inference/agent/tool_agent.py"
    # Git may check out CRLF on Windows; Kaggle source bundles use LF.
    raw = path.read_text(encoding="utf-8").encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != ORIGINAL_BLOB:
        raise RuntimeError("V4 must start from the exact original tool agent")
    source = raw.decode("utf-8")
    anchor = "from inference.agent.python_tool_sandbox import run_sandboxed_python\n"
    source = replace_once(source, anchor, anchor +
        "from inference.utils.stagnation_restart import maybe_restart\n")
    anchor = "            self._history_messages = []\n            self._session_total_tokens = 0\n"
    source = replace_once(source, anchor,
        "            self._stagnation_restarted_levels = set()\n"
        "            self._stagnation_pending_notice = None\n" + anchor)
    anchor = "        current_frame, history_entries = load_runtime_state(state_path)\n        user_prompt = self._build_user_prompt(\n"
    source = replace_once(source, anchor,
        "        current_frame, history_entries = load_runtime_state(state_path)\n"
        "        restart_notice = maybe_restart(self, current_frame)\n"
        "        user_prompt = restart_notice + self._build_user_prompt(\n")
    ast.parse(source)
    path.write_text(source, encoding="utf-8", newline="\n")
    helper = Path(__file__).with_name("stagnation_restart.py").read_text(encoding="utf-8")
    ast.parse(helper)
    (root / "inference/utils/stagnation_restart.py").write_text(helper, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    apply(sys.argv[1])
