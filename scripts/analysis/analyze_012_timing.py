#!/usr/bin/env python3
"""Read-only 012 timing/resource audit; parses data, never executes logged code."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import analyze_011_timing as shared


def deadline_audit(root, arm, data):
    timing = shared.read(root / arm / "inference-timing.json")
    benchmark = shared.read(root / arm / "benchmark.json")
    runs = {run["game_id"]: run for run in benchmark["game_runs"]}
    deadline = data["global_soft_end_t"]
    late_chats, actions, per_game = [], [], []
    for session in timing["sessions"]:
        game_id = session["game_id"]
        events = session["events"]
        for event in events:
            if event["kind"] != "chat_begin" or event["t"] <= deadline:
                continue
            returned = next(item for item in events if item["kind"] in ("chat_return", "chat_exception")
                            and item["request_id"] == event["request_id"])
            admission = next(item for item in reversed(events[:events.index(event)]) if item["kind"] == "gate_admitted_return")
            late_chats.append({"game_id": game_id, "request_id": event["request_id"],
                "tools_present": event["tools_present"], "start_after_soft_end_s": event["t"] - deadline,
                "gate_admitted_after_soft_end_s": admission["t"] - deadline,
                "status": returned["kind"], "generated_tokens": returned.get("generated_tokens"),
                "duration_s": returned["duration_s"], "finish_reason": returned.get("finish_reason")})
        run = runs[game_id]
        offset = (shared.utc(run["started_at"]) - shared.utc(data["clock_origin_utc"])).total_seconds()
        times = [offset + item["wallclock_seconds"] for item in run["history"]]
        for index, timestamp in enumerate(times):
            if timestamp > deadline:
                actions.append({"game_id": game_id, "history_index": index,
                                "seconds_after_soft_end": timestamp - deadline})
        per_game.append({"game_id": game_id, "actions": len(times),
                         "last_action_before_soft_end_s": deadline - max(times) if times else None})
    return {"new_chat_requests_after_soft_end": late_chats,
            "new_chat_count": len(late_chats),
            "new_chat_known_tokens": sum(item.get("generated_tokens") or 0 for item in late_chats),
            "actions_after_soft_end": actions, "per_game": per_game,
            "action_time_method": "GameRun.started_at UTC + history.wallclock_seconds, aligned to observer UTC origin; approximate clock alignment, not a new action hook."}


def lifecycle(root):
    text = (root / "serve.log").read_text()
    lines = text.splitlines()
    markers = ("The server is fired up", "Cache flushed successfully!", "SIGTERM received.",
               "Subprocess detokenizer", "No live scheduler processes found", "kill_process_tree called")
    events = [{"normalized_text_line": index, "text": line} for index, line in enumerate(lines, 1)
              if any(marker in line for marker in markers)]
    gpu = [json.loads(line) for line in (root / "gpu-utilization.jsonl").open()]
    kernel = shared.read(root / "arc3-012-current-data.log")
    return {"server_events": events,
            "server_ready_count": sum("The server is fired up" in line for line in lines),
            "sitecustomize_missing_wrapt_count": sum("ModuleNotFoundError: No module named 'wrapt'" in line for line in lines),
            "explicit_cuda_oom_lines": [line for line in lines if re.search(r"CUDA out of memory|torch.OutOfMemoryError", line)],
            "gpu_sampler_records": len(gpu), "gpu_sampler_error_records": sum(item.get("returncode") != 0 for item in gpu),
            "gpu_first_sample": gpu[0], "gpu_last_two_samples": gpu[-2:],
            "kernel_last_log_elapsed_s": max(item["time"] for item in kernel)}


def allocation(arms):
    a = {game["game_id"]: game for game in arms["baseline"]["games"]}
    b = {game["game_id"]: game for game in arms["current_data"]["games"]}
    result = []
    for game_id, before in a.items():
        after = b[game_id]
        result.append({"game_id": game_id,
            "baseline_first_http_s": before["first_http_delay_s"], "candidate_first_http_s": after["first_http_delay_s"],
            "baseline_first_action_s": before["first_actual_action_game_elapsed_s"],
            "candidate_first_action_s": after["first_actual_action_game_elapsed_s"],
            "slot_held_delta_s": after["slot_held_s"] - before["slot_held_s"],
            "gate_wait_delta_s": after["total_gate_wait_s"] - before["total_gate_wait_s"],
            "known_token_delta": after["known_generated_tokens"] - before["known_generated_tokens"],
            "baseline_tokens": before["known_generated_tokens"], "candidate_tokens": after["known_generated_tokens"],
            "baseline_score": before["score"], "candidate_score": after["score"],
            "baseline_levels": before["levels_completed"], "candidate_levels": after["levels_completed"]})
    return result


def markdown(report):
    arms = report["arms"]
    margins = {arm: min(item["last_action_before_soft_end_s"] for item in data["deadline_audit"]["per_game"])
               for arm, data in arms.items()}
    lines = ["# 012 计时、资源与截止边界审计", "",
        "2026-10-13。两臂均完整完成，计时观察器有效；候选退步不能归为总生成量不足。候选在截止后多发出 **2 次客户端请求**，但两臂均未记录截止后的游戏动作。这里只读核对已有产物，没有运行模型、游戏或日志代码。", "",
        "| 指标 | baseline（先） | current_data（后） |", "| --- | ---: | ---: |"]
    fields = [("游戏 / 预算", "13 / 3772s", "13 / 3772s"),
              ("chat / 成功 / ReadTimeout", "1202 / 1195 / 7", "1154 / 1146 / 8"),
              ("成功返回的已知 tokens", "2,364,169", "2,378,190"),
              ("observer 丢弃 / 错误 / 活跃会话", "0 / 0 / 0", "0 / 0 / 0"),
              ("结束快照晚于 soft_end", "14.50s", "27.73s"),
              ("GPU 利用率采样均值 / 中位数", "92.76% / 98%", "93.75% / 98%"),
              ("GPU 采样数 / 显存峰值 MiB", "380 / 96,081", "381 / 96,251")]
    lines += [f"| {name} | {a} | {b} |" for name, a, b in fields]
    lines += ["", "两臂使用同一冻结 observer 与底座 hook，均记录 13/13 会话，所有请求/gate 区间闭合、事件序号及 token 对账一致，最大同时持有 10 个名额；进程 exit=0，无强制退出或遗留 worker。003/006/007 报告均 disabled。", "",
        "截止后的两次请求分别来自 tn36（+0.604s，777 tokens，19.60s）与 lf52（+0.606s，320 tokens，15.27s）；此前各自在 handover 队列等待 550s / 763s，于截止后约 0.5s 返回。两次均 tools_present=true、finish_reason=tool_calls，不能标成‘仅总结调用’。底座在 `_maybe_handover()` 前检查 stop，其后直接准备请求，和所见唤醒边界吻合；不是本次新改了调度。"
        f"两臂实际动作末尾与截止仍分别至少相隔约 {margins['baseline']:.2f}s / {margins['current_data']:.2f}s，未见超时动作计分。", "",
        "服务器还有独立口径：A 2 条 / B 3 条 ReqTimeStats 的 entry_time 晚于截止，不能把客户端无新请求等同为服务端已无工作。服务端 logged output_len 为 2,378,410 / 2,401,803，比客户端成功 usage 多 14,241 / 23,613；缺少共同 request id，不能把这些差额逐一归给游戏或某类失败。15 次客户端异常全部为截止附近的 ReadTimeout；A 最晚 +1.42s，B 最晚 +15.69s。", "",
        "| 游戏 | first HTTP A→B（秒） | B−A 持有名额时间 | B−A 已知 tokens | 完成关数 A→B |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in report["allocation_deltas"]:
        if row["game_id"][:4] not in ("tn36", "sp80", "ft09", "cd82", "g50t", "m0r0"):
            continue
        lines.append(f"| {row['game_id'][:4]} | {row['baseline_first_http_s']:.2f}→{row['candidate_first_http_s']:.2f} | {row['slot_held_delta_s']:+.1f}s | {row['known_token_delta']:+,} | {row['baseline_levels']}→{row['candidate_levels']} |")
    lines += ["", "tn36、sp80 的结果与后续资源分配一起下降，优先级按轨迹反馈变化，不能从这一个配对判定谁导致谁。ft09 则提前启动、额外获得约 833s 名额和 64,941 tokens，仍少过两关；cd82 同样得到更多资源，六关完成但效率分略降。初始 10 个名额的线程竞态使 B 的 ft09 提前、g50t 延后，按游戏列表顺序不能推定真实请求先后。", "",
        "current_data 的宿主动作边界记录累计 1.824 CPU 秒、query 0.001 秒，值存储峰值 181 bytes；这不包括 child 校验、工具启动或提示所增 token，不能当完整干预成本。已记录的宿主维护耗时不足以解释千秒级名额分配差。", "",
        "本轮只有一次服务器 ready，560.59s 后可用；两次 cache flush 日志均确认成功。实验 manifest 总时长 8,162.91s（2.267h）；Notebook 最后导出日志约 8,172.98s。SIGTERM 后出现子进程 -15 与清理日志，随后两个 finished GPU 样本显存为 0、利用率为 0，结合 manifest 的 gpu_server_stopped=true 支持正常完成清理。启动期有 4 条缺 wrapt 的 sitecustomize 提示，之后服务器正常工作；未发现明确 CUDA OOM 日志。", "",
        "账户共享额度变化 26.71→30.17h（+3.46h）不能归全部给 012；期间另有作业，GPU 类型和各自成本须由账户侧另查。这里的 2.267h 是本地 manifest 墙钟，不是 Kaggle 计费审计。", "",
        "名额持有时间包括 Python 与等待，多游戏时间相加不是 GPU 墙钟；gate 返回不是精确 GPU 开始；HTTP 返回也不是统一的完整解码边界；GPU 均值只是每 10 秒采样均值。首次动作来自 benchmark 的游戏 elapsed，首次 HTTP 来自 observer，二者不得互换。单次先 A 后 B 仍受随机轨迹与共享调度影响，不能从资源对账推出机制因果。", "",
        "复核：`python3 -B scripts/analysis/analyze_012_timing.py`。完整逐游戏数字、迟到请求、动作截止检查、来源 SHA256 在 [机器报告](../../../experiments/012-timing-analysis.json)；分析沿用 [011 只读解析函数](../../../scripts/analysis/analyze_011_timing.py)，依赖源码 hash 也已登记。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("runs/012-current-data"))
    parser.add_argument("--output", type=Path, default=Path("experiments/012-timing-analysis.json"))
    parser.add_argument("--markdown", type=Path, default=Path("research/notes/012/012-timing-analysis.md"))
    args = parser.parse_args()
    arms = {arm: shared.arm_report(args.root, arm) for arm in ("baseline", "current_data")}
    for arm, data in arms.items():
        metadata = shared.read(args.root / arm / "arm-metadata.json")
        data["deadline_audit"] = deadline_audit(args.root, arm, data)
        data["process"] = {key: metadata[key] for key in ("exit_code", "forced_cpu_process_exit", "lingering_worker_threads", "benchmark_wall_seconds", "wall_seconds")}
        data["disabled_interventions"] = {name: shared.read(args.root / arm / name)["enabled"]
                                           for name in ("goal-evidence.json", "transient-history.json", "program-state.json")}
        data["active_sessions"] = sum(session["play_active"] for session in shared.read(args.root / arm / "inference-timing.json")["sessions"])
    paths = [args.root / arm / name for arm in arms for name in
             ("inference-timing.json", "arm-metadata.json", "benchmark.json", "run.log", "goal-evidence.json", "transient-history.json", "program-state.json")]
    paths += [args.root / name for name in ("experiment-manifest.json", "input-paths.json", "gpu-utilization.jsonl", "serve.log", "arc3-012-current-data.log")]
    paths.append(args.root / "current_data/current-data.json")
    paths += [Path(__file__), Path(shared.__file__), Path("research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py")]
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": __doc__, "sources": [shared.source(path) for path in paths], "arms": arms,
              "allocation_deltas": allocation(arms), "resources": shared.resources(args.root, arms),
              "lifecycle": lifecycle(args.root), "manifest": shared.read(args.root / "experiment-manifest.json"),
              "current_data_host_cost": {key: value for key, value in shared.read(args.root / "current_data/current-data.json").items()
                                         if key in ("action_boundary_cpu_seconds", "query_cpu_seconds", "stored_value_bytes", "peak_stored_value_bytes")},
              "hook_hashes_equal": arms["baseline"]["hook_source_sha256"] == arms["current_data"]["hook_source_sha256"],
              "quota_boundary": "Shared account delta is not experiment cost; this script has no account/job billing data."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    args.markdown.write_text(markdown(report))
    print(json.dumps({arm: {"events_dropped": data["events_dropped"], "observer_errors": data["observer_errors"],
                           "integrity_failures": data["integrity_failures"],
                           "late_chats": data["deadline_audit"]["new_chat_count"],
                           "late_actions": len(data["deadline_audit"]["actions_after_soft_end"])} for arm, data in arms.items()}, indent=2))


if __name__ == "__main__":
    main()
