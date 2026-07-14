from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

import praw
from praw.models import Comment, MoreComments


POST_ID = re.compile(r"(?:comments/|^)([a-z0-9]{5,10})(?:/|$)", re.I)
PRIVATE_MARKERS = {"[deleted]", "[removed]"}


@dataclass(frozen=True)
class CommentRecord:
    comment_id: str
    parent_id: str
    post_id: str
    author: str | None
    body: str | None
    created_utc: str
    edited_utc: str | None
    score: int
    depth: int
    permalink: str
    state: str
    scanned_at: str


def make_reddit(client_id: str, client_secret: str, user_agent: str) -> praw.Reddit:
    if not all(value.strip() for value in (client_id, client_secret, user_agent)):
        raise ValueError("Reddit client ID, client secret and user agent are required.")
    reddit = praw.Reddit(
        client_id=client_id.strip(),
        client_secret=client_secret.strip(),
        user_agent=user_agent.strip(),
        check_for_async=False,
        ratelimit_seconds=30,
        requestor_kwargs={"timeout": 30},
    )
    reddit.read_only = True
    return reddit


def extract_post_id(value: str) -> str:
    value = value.strip()
    match = POST_ID.search(value)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-z0-9]{5,10}", value, re.I):
        return value
    raise ValueError("Enter a Reddit post URL or submission ID.")


def _iso(timestamp: float | int | None) -> str | None:
    if timestamp in (None, False):
        return None
    return datetime.fromtimestamp(float(timestamp), timezone.utc).isoformat()


def _safe_body(body: str | None) -> tuple[str | None, str]:
    text = (body or "").strip()
    if text.lower() == "[deleted]":
        return None, "deleted"
    if text.lower() == "[removed]":
        return None, "removed"
    return text, "visible"


def scan_submission(
    reddit: praw.Reddit,
    post_url_or_id: str,
    more_limit: int = 8,
    max_comments: int = 5000,
) -> tuple[dict, list[dict]]:
    post_id = extract_post_id(post_url_or_id)
    submission = reddit.submission(id=post_id)
    submission._fetch()
    scanned_at = datetime.now(timezone.utc).isoformat()

    # Each MoreComments expansion costs requests. A finite limit keeps scans predictable.
    submission.comments.replace_more(limit=max(0, more_limit), threshold=0)
    rows: list[dict] = []
    for item in submission.comments.list():
        if isinstance(item, MoreComments) or not isinstance(item, Comment):
            continue
        body, state = _safe_body(item.body)
        row = CommentRecord(
            comment_id=item.id,
            parent_id=item.parent_id,
            post_id=post_id,
            author=str(item.author) if item.author else None,
            body=body,
            created_utc=_iso(item.created_utc) or scanned_at,
            edited_utc=_iso(item.edited),
            score=int(item.score or 0),
            depth=int(item.depth or 0),
            permalink=f"https://www.reddit.com{item.permalink}",
            state=state,
            scanned_at=scanned_at,
        )
        rows.append(asdict(row))
        if len(rows) >= max_comments:
            break

    post = {
        "post_id": post_id,
        "title": submission.title,
        "subreddit": str(submission.subreddit),
        "author": str(submission.author) if submission.author else None,
        "created_utc": _iso(submission.created_utc),
        "score": int(submission.score or 0),
        "upvote_ratio": float(submission.upvote_ratio or 0),
        "num_comments_public": int(submission.num_comments or 0),
        "permalink": f"https://www.reddit.com{submission.permalink}",
        "scanned_at": scanned_at,
        "comments_collected": len(rows),
    }
    return post, rows


def scan_subreddit(reddit: praw.Reddit, name: str, sort: str, limit: int) -> list[dict]:
    clean = name.strip().removeprefix("r/").strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_]{2,21}", clean):
        raise ValueError("Enter a valid subreddit name, such as Cricket.")
    listing: Iterable = getattr(reddit.subreddit(clean), sort)(limit=min(max(limit, 1), 100))
    scanned_at = datetime.now(timezone.utc).isoformat()
    return [{
        "post_id": item.id,
        "title": item.title,
        "author": str(item.author) if item.author else None,
        "created_utc": _iso(item.created_utc),
        "score": int(item.score or 0),
        "upvote_ratio": float(item.upvote_ratio or 0),
        "num_comments": int(item.num_comments or 0),
        "url": f"https://www.reddit.com{item.permalink}",
        "scanned_at": scanned_at,
    } for item in listing]

