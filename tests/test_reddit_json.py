import json

from reddit_client import extract_post_id, parse_reddit_json


def sample_payload():
    return [
        {"data": {"children": [{"kind": "t3", "data": {
            "id": "1uw2r8b", "title": "Match Thread", "subreddit": "Cricket",
            "author": "matchbot", "created_utc": 1_700_000_000, "score": 42,
            "upvote_ratio": 0.95, "num_comments": 3,
            "permalink": "/r/Cricket/comments/1uw2r8b/match_thread/",
        }}]}},
        {"data": {"children": [
            {"kind": "t1", "data": {
                "id": "c1", "parent_id": "t3_1uw2r8b", "author": "fan1",
                "body": "Great over", "created_utc": 1_700_000_100, "score": 5,
                "depth": 0, "permalink": "/r/Cricket/comments/1uw2r8b/x/c1/",
                "replies": {"data": {"children": [{"kind": "t1", "data": {
                    "id": "c2", "parent_id": "t1_c1", "author": "fan2",
                    "body": "[deleted]", "created_utc": 1_700_000_200,
                    "score": 0, "depth": 1,
                    "permalink": "/r/Cricket/comments/1uw2r8b/x/c2/", "replies": "",
                }}]}},
            }},
            {"kind": "more", "data": {"children": ["c3"]}},
        ]}},
    ]


def test_extract_post_id_from_match_url():
    url = "https://www.reddit.com/r/Cricket/comments/1uw2r8b/match_thread/"
    assert extract_post_id(url) == "1uw2r8b"


def test_parse_nested_json_and_delete_body():
    post, comments = parse_reddit_json(json.dumps(sample_payload()).encode())
    assert post["post_id"] == "1uw2r8b"
    assert post["comments_collected"] == 2
    assert comments[0]["body"] == "Great over"
    assert comments[1]["state"] == "deleted"
    assert comments[1]["body"] is None
    assert comments[1]["author"] is None

