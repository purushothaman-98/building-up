from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge_archives(current: dict, incoming: dict) -> dict:
    papers: dict[str, dict] = {}
    for archive in (current, incoming):
        for paper in archive.get("papers", []):
            paper_id = paper["arxiv_id"]
            previous = papers.get(paper_id)
            if previous is None or paper.get("updated", "") >= previous.get("updated", ""):
                chosen = dict(paper)
            else:
                chosen = dict(previous)
            versions = []
            for source in (previous or {}, paper):
                versions.extend(source.get("versions_seen", [source.get("version", "v1")]))
            chosen["versions_seen"] = list(dict.fromkeys(v for v in versions if v))
            papers[paper_id] = chosen

    scans: dict[str, dict] = {}
    for archive in (current, incoming):
        for scan in archive.get("scans", []):
            scanned_at = scan.get("scanned_at")
            if scanned_at:
                scans[scanned_at] = scan
    ordered_scans = sorted(scans.values(), key=lambda item: item["scanned_at"])[-500:]
    latest_scan = ordered_scans[-1] if ordered_scans else {}

    return {
        "schema_version": max(current.get("schema_version", 2), incoming.get("schema_version", 2)),
        "last_scan": latest_scan.get("scanned_at"),
        "papers": sorted(papers.values(), key=lambda item: item.get("updated", ""), reverse=True),
        "scans": ordered_scans,
        "counts": {
            "total": len(papers),
            "new_this_scan": latest_scan.get("new", 0),
            "updated_this_scan": latest_scan.get("updated", 0),
        },
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: merge_papers_conflict.py BASE CURRENT INCOMING")
    _, current_path, incoming_path = sys.argv
    merged = merge_archives(load(current_path), load(incoming_path))
    Path(current_path).write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
