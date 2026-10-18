# V17 (prvsiyan, Apache-2.0): per-stream timing log, logging only. It times every chat request that the harness sends to the
# local model server, keyed by the harness game thread, and changes nothing: requests, responses and exceptions pass through.
# On by default in interactive runs; off in the competition rerun, whose outputs are never visible. V17_TIMING_LOG=0 disables it.
import requests

V17_TIMING = {"on": (not TRUE_SUBMISSION) and os.environ.get("V17_TIMING_LOG", "1") != "0", "records": 0, "logging_errors": 0,
              "max_records": 200000, "path": str(WORKING_DIR / "v17_timing" / "requests.jsonl"),
              "prefix": SERVER_BASE_URL.rstrip("/") + "/chat/completions"}
V17_TIMING_LOCK = threading.Lock()
_v17_original_send = requests.Session.send


def _v17_log(record):
    try:
        with V17_TIMING_LOCK:
            if V17_TIMING["records"] >= V17_TIMING["max_records"]:
                return
            with open(V17_TIMING["path"], "a") as f:
                f.write(json.dumps(record) + "\n")
            V17_TIMING["records"] += 1
    except Exception:
        V17_TIMING["logging_errors"] += 1


def _v17_timed_send(self, request, **kwargs):
    record = None
    try:
        if str(getattr(request, "url", "")).startswith(V17_TIMING["prefix"]):
            record = {"thread": threading.current_thread().name, "t0": time.time(), "stream": bool(kwargs.get("stream"))}
    except Exception:
        record = None
    try:
        response = _v17_original_send(self, request, **kwargs)
    except BaseException as exc:
        if record is not None:
            try:
                record.update(t1=time.time(), error=type(exc).__name__)
            except Exception:
                pass
            _v17_log(record)
        raise
    if record is not None:
        try:
            record.update(t1=time.time(), status=getattr(response, "status_code", None))
        except Exception:
            pass
        _v17_log(record)
    return response


if V17_TIMING["on"]:
    Path(V17_TIMING["path"]).parent.mkdir(parents=True, exist_ok=True)
    requests.Session.send = _v17_timed_send
    print("V17 timing log on ->", V17_TIMING["path"], flush=True)
else:
    print("V17 timing log off (competition rerun, or V17_TIMING_LOG=0)", flush=True)
