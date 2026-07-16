from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

from arxiv_scanner import fetch_since, merge_archive


def run_backfill(
    archive_path: Path,
    state_path: Path,
    *,
    all_remaining: bool = False,
    pause_seconds: float = 5.0,
) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    final = date.fromisoformat(state["range_end"])
    processed = 0

    while not state.get("complete", False):
        start = date.fromisoformat(state["next_since"])
        if start > final:
            state["complete"] = True
            break

        chunk_days = int(state.get("chunk_days", 7))
        end = min(start + timedelta(days=chunk_days - 1), final)
        papers = fetch_since(
            start.isoformat(),
            max_results=500,
            page_size=100,
            until=end.isoformat(),
        )
        merge_archive(archive_path, papers, len(papers), start.isoformat())

        window = {"since": start.isoformat(), "until": end.isoformat()}
        windows = state.setdefault("completed_windows", [])
        if window not in windows:
            windows.append(window)
        next_day = end + timedelta(days=1)
        state["next_since"] = next_day.isoformat()
        state["complete"] = next_day > final
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        processed += 1

        if state["complete"] or not all_remaining:
            break
        time.sleep(pause_seconds)

    return {"processed_windows": processed, **state}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("data/papers.json"))
    parser.add_argument("--state", type=Path, default=Path("data/backfill_state.json"))
    parser.add_argument("--all", action="store_true", dest="all_remaining")
    parser.add_argument("--pause", type=float, default=5.0)
    args = parser.parse_args()
    result = run_backfill(
        args.archive,
        args.state,
        all_remaining=args.all_remaining,
        pause_seconds=args.pause,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
