from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")


def merge_snapshot(post: dict, comments: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge current state locally without retaining deleted/removed text."""
    DATA_DIR.mkdir(exist_ok=True)
    post_path = DATA_DIR / "post_snapshots.csv"
    comment_path = DATA_DIR / "comment_snapshots.csv"
    posts = _read(post_path)
    current_comments = pd.DataFrame(comments)
    old_comments = _read(comment_path)

    posts = pd.concat([posts, pd.DataFrame([post])], ignore_index=True)
    if not current_comments.empty:
        # If Reddit now reports a comment deleted/removed, erase its historical body locally.
        unavailable = set(current_comments.loc[current_comments["state"] != "visible", "comment_id"])
        if unavailable and not old_comments.empty:
            old_comments.loc[old_comments["comment_id"].isin(unavailable), "body"] = pd.NA
            old_comments.loc[old_comments["comment_id"].isin(unavailable), "author"] = pd.NA
        old_comments = pd.concat([old_comments, current_comments], ignore_index=True)

    posts.to_csv(post_path, index=False)
    old_comments.to_csv(comment_path, index=False)
    return posts, old_comments


def _read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()

