def v17_timing_summary(path, slots=10):
    """Per harness thread: requests, busy and idle seconds, idle fraction, gap quantiles. Overall: mean requests in flight,
    idle share of the server's request slots, and the share of time with every slot busy (client-side view)."""
    try:
        records = [json.loads(line) for line in open(path)]
    except FileNotFoundError:
        records = []
    done = sorted((r for r in records if "t1" in r and "t0" in r), key=lambda r: r["t0"])
    per = {}
    for r in done:
        per.setdefault(r["thread"], []).append(r)
    def q(xs, f):
        return round(xs[min(len(xs) - 1, int(f * len(xs)))], 2) if xs else None
    streams = {}
    for thread, rs in sorted(per.items()):
        gaps = sorted(max(0.0, b["t0"] - a["t1"]) for a, b in zip(rs, rs[1:]))
        span = rs[-1]["t1"] - rs[0]["t0"]
        streams[thread] = {"requests": len(rs), "errors": sum("error" in r for r in rs), "busy_s": round(sum(r["t1"] - r["t0"] for r in rs), 1),
                           "idle_s": round(sum(gaps), 1), "span_s": round(span, 1), "idle_fraction": round(sum(gaps) / span, 4) if span > 0 else None,
                           "gap_p50_s": q(gaps, 0.5), "gap_p90_s": q(gaps, 0.9)}
    events = sorted([(r["t0"], 1) for r in done] + [(r["t1"], -1) for r in done])
    area = full = 0.0
    inflight, last = 0, (events[0][0] if events else 0.0)
    for t, step in events:
        area += inflight * (t - last)
        full += (t - last) if inflight >= slots else 0.0
        inflight, last = inflight + step, t
    window = (events[-1][0] - events[0][0]) if events else 0.0
    return {"records": len(records), "completed": len(done), "threads": len(streams), "window_s": round(window, 1), "slots": slots,
            "mean_in_flight": round(area / window, 3) if window else None,
            "slot_idle_fraction": round(1 - area / window / slots, 4) if window else None,
            "all_slots_busy_fraction": round(full / window, 4) if window else None,
            "idle_fraction_mean_over_threads": round(sum(s["idle_fraction"] or 0 for s in streams.values()) / len(streams), 4) if streams else None,
            "per_thread": streams}
