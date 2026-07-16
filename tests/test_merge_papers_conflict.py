from scripts.merge_papers_conflict import merge_archives


def test_merge_archives_preserves_concurrent_scans_and_versions():
    current = {
        "schema_version": 2,
        "papers": [{"arxiv_id": "2607.00001", "updated": "2026-07-01", "version": "v1", "versions_seen": ["v1"]}],
        "scans": [{"scanned_at": "2026-07-16T07:32:00Z", "new": 1, "updated": 0}],
    }
    incoming = {
        "schema_version": 2,
        "papers": [
            {"arxiv_id": "2607.00001", "updated": "2026-07-02", "version": "v2", "versions_seen": ["v1", "v2"]},
            {"arxiv_id": "2607.00002", "updated": "2026-07-02", "version": "v1", "versions_seen": ["v1"]},
        ],
        "scans": [{"scanned_at": "2026-07-16T07:46:00Z", "new": 1, "updated": 1}],
    }

    merged = merge_archives(current, incoming)

    assert merged["counts"] == {"total": 2, "new_this_scan": 1, "updated_this_scan": 1}
    assert [scan["scanned_at"] for scan in merged["scans"]] == [
        "2026-07-16T07:32:00Z",
        "2026-07-16T07:46:00Z",
    ]
    first = next(paper for paper in merged["papers"] if paper["arxiv_id"] == "2607.00001")
    assert first["version"] == "v2"
    assert first["versions_seen"] == ["v1", "v2"]
