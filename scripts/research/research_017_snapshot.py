"""Read current Kaggle competition evidence; never launches or submits work.

Run with the installed Kaggle CLI Python environment. Authentication is handled
by its existing configuration; no credentials are written to the snapshot.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path

from kaggle import api
from kagglesdk.competitions.types.competition_api_service import (
    ApiGetCompetitionRequest, ApiGetLeaderboardRequest, ApiGetSubmissionRequest,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/snapshots/2026-10-18"
COMPETITION = "arc-prize-2026-arc-agi-3"


def plain(value):
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value.to_dict() if hasattr(value, "to_dict") else value


def save(name, value):
    data = plain(value)
    (OUT / (name + ".json")).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return data


def competition():
    with api.build_kaggle_client() as client:
        request = ApiGetCompetitionRequest()
        request.competition_name = COMPETITION
        return client.competitions.competition_api_client.get_competition(request)


def leaderboard():
    entries, token = [], None
    with api.build_kaggle_client() as client:
        for page in range(1, 6):
            request = ApiGetLeaderboardRequest()
            request.competition_name = COMPETITION
            request.override_public = True
            request.page_size = 100
            if token:
                request.page_token = token
            response = client.competitions.competition_api_client.get_leaderboard(request)
            save(f"leaderboard-page-{page}", response)
            entries.extend(plain(response.submissions))
            token = response.next_page_token
            if not token:
                break
    assert len({entry["teamId"] for entry in entries}) == len(entries)
    return {"submissions": entries, "next_page_token": token,
            "note": "Up to 500 rows, sequential pages rather than an atomic full-board snapshot."}


def data_files():
    entries, token = [], None
    while True:
        response = api.competition_list_files(COMPETITION, page_token=token, page_size=100)
        entries.extend(plain(response.files))
        token = response.next_page_token
        if not token:
            break
    return {"files": entries, "next_page_token": token}


def submission():
    with api.build_kaggle_client() as client:
        request = ApiGetSubmissionRequest()
        request.ref = 57101330
        return client.competitions.competition_api_client.get_submission(request)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {
        "competition": competition,
        "leaderboard-first-500": leaderboard,
        "data-files": data_files,
        "competition-pages": lambda: api.competition_list_pages(COMPETITION),
        "topics-recent": lambda: api.competition_list_topics(COMPETITION, sort_by="recent", page=1),
        "topic-745079": lambda: api.competition_list_topic_messages(COMPETITION, 745079, page_size=-1),
        "topic-748593": lambda: api.competition_list_topic_messages(COMPETITION, 748593, page_size=-1),
        "submission-57101330": submission,
        "submissions": lambda: api.competition_submissions(COMPETITION, page_size=20),
        "quota-ccjjllt": api.quota_view,
    }
    manifest = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "read_only": True, "results": {}}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                save(name, future.result())
                manifest["results"][name] = {"status": "saved"}
            except Exception as exc:
                manifest["results"][name] = {"status": "error", "type": type(exc).__name__, "message": str(exc)[:500]}
            print(name, manifest["results"][name]["status"], flush=True)
            save("read-manifest", manifest)
    manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    save("read-manifest", manifest)


if __name__ == "__main__":
    main()
