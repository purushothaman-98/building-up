from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from reddit_client import make_reddit, parse_reddit_json, scan_submission, scan_subreddit
from storage import merge_snapshot


st.set_page_config(page_title="ThreadScope", page_icon="◉", layout="wide")
st.markdown("""
<style>
.stApp{background:#f5f4ef}.block-container{max-width:1400px;padding-top:1.5rem}
.hero{padding:34px 38px;border-radius:22px;background:linear-gradient(120deg,#111827,#172554 65%,#ea580c);color:white;margin-bottom:22px}
.hero h1{font-size:52px;letter-spacing:-.045em;margin:4px 0}.hero p{color:#dbeafe;max-width:760px}
[data-testid="stMetric"]{background:white;border:1px solid #dedbd2;padding:14px;border-radius:14px}
</style>
<div class="hero"><small>REDDIT DISCUSSION MONITOR</small><h1>ThreadScope</h1>
<p>OAuth-only collection for public Reddit discussions, with bounded expansion, cached scans and privacy-safe deletion handling.</p></div>
""", unsafe_allow_html=True)


def credentials() -> tuple[str, str, str] | None:
    try:
        cfg = st.secrets["reddit"]
        return cfg["client_id"], cfg["client_secret"], cfg["user_agent"]
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def cached_thread(client_id: str, client_secret: str, agent: str, target: str, more: int, cap: int):
    return scan_submission(make_reddit(client_id, client_secret, agent), target, more, cap)


@st.cache_data(ttl=300, show_spinner=False)
def cached_listing(client_id: str, client_secret: str, agent: str, name: str, sort: str, limit: int):
    return scan_subreddit(make_reddit(client_id, client_secret, agent), name, sort, limit)


oauth = credentials()
thread_tab, upload_tab, subreddit_tab, method_tab = st.tabs(["OAuth thread scanner", "No-credential JSON", "Subreddit browser", "Method & safety"])

with thread_tab:
    if oauth is None:
        st.info("OAuth credentials are not configured. Use the no-credential JSON upload tab, or add Streamlit Secrets to enable live scans.")
        st.code('[reddit]\nclient_id="..."\nclient_secret="..."\nuser_agent="web:threadscope:0.1 (by /u/your_username)"', language="toml")
    else:
        client_id, client_secret, agent = oauth
    target = st.text_input("Reddit post URL or ID", placeholder="https://www.reddit.com/r/Cricket/comments/...")
    a, b = st.columns(2)
    more_limit = a.slider("More-comments expansions", 0, 20, 8, help="Higher values improve coverage but use more API requests.")
    max_comments = b.number_input("Maximum comments per scan", 100, 20000, 5000, 100)
    if st.button("Scan public thread", type="primary", disabled=not target or oauth is None):
        try:
            with st.spinner("Reading the public thread through Reddit OAuth…"):
                post, rows = cached_thread(client_id, client_secret, agent, target, more_limit, int(max_comments))
                posts_history, comment_history = merge_snapshot(post, rows)
                st.session_state["thread_result"] = (post, rows, posts_history, comment_history)
        except Exception as exc:
            st.error(f"Scan failed: {exc}")

    if "thread_result" in st.session_state:
        post, rows, posts_history, comment_history = st.session_state["thread_result"]
        st.subheader(post["title"])
        st.caption(f'r/{post["subreddit"]} · scanned {post["scanned_at"]} · [open original]({post["permalink"]})')
        metrics = st.columns(5)
        metrics[0].metric("Public comments", f'{post["num_comments_public"]:,}')
        metrics[1].metric("Collected", f'{post["comments_collected"]:,}')
        metrics[2].metric("Score", f'{post["score"]:,}')
        metrics[3].metric("Upvote ratio", f'{post["upvote_ratio"]:.0%}')
        metrics[4].metric("Stored scans", len(posts_history[posts_history["post_id"] == post["post_id"]]))
        frame = pd.DataFrame(rows)
        if not frame.empty:
            visible = frame[frame["state"] == "visible"].copy()
            visible["created_utc"] = pd.to_datetime(visible["created_utc"], utc=True)
            timeline = visible.assign(period=visible["created_utc"].dt.floor("10min")).groupby("period", as_index=False).size()
            fig = px.area(timeline, x="period", y="size", markers=True, labels={"size":"Comments published", "period":"UTC"})
            fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")
            st.plotly_chart(fig, width="stretch")
            st.dataframe(visible[["created_utc","author","score","depth","body","permalink"]].sort_values("created_utc", ascending=False), hide_index=True, width="stretch", column_config={"permalink":st.column_config.LinkColumn("Open")})
            st.download_button("Download current scan", frame.to_csv(index=False), f'{post["post_id"]}-comments.csv', "text/csv")

with upload_tab:
    st.subheader("Analyze a Reddit JSON file locally")
    st.write("Open a public comments page manually, append `.json` to its URL if Reddit serves it to your browser, save the response, and upload it here. The app makes no request to Reddit in this mode.")
    uploaded = st.file_uploader("Reddit comments JSON", type=["json"])
    if uploaded is not None:
        try:
            post, rows = parse_reddit_json(uploaded.getvalue())
            frame = pd.DataFrame(rows)
            st.success(f'Parsed {len(frame):,} comments from “{post["title"]}”.')
            if post["num_comments_public"] > len(frame):
                st.warning("The file contains fewer comments than Reddit's public counter. JSON `more` placeholders cannot be expanded without additional authenticated requests.")
            if not frame.empty:
                st.dataframe(frame[["created_utc", "author", "score", "depth", "body", "permalink"]], hide_index=True, width="stretch", column_config={"permalink": st.column_config.LinkColumn("Open")})
                st.download_button("Download parsed comments", frame.to_csv(index=False), f'{post["post_id"]}-parsed.csv', "text/csv")
        except Exception as exc:
            st.error(f"Could not parse this file: {exc}")

with subreddit_tab:
    if oauth is None:
        st.info("Live subreddit browsing requires Reddit OAuth credentials.")
    c1, c2, c3 = st.columns([2,1,1])
    subreddit = c1.text_input("Subreddit", value="Cricket")
    sort = c2.selectbox("Sort", ["new", "hot", "top", "rising"])
    listing_limit = c3.number_input("Posts", 5, 100, 25, 5)
    if st.button("Load public posts", disabled=oauth is None):
        try:
            client_id, client_secret, agent = oauth
            posts = pd.DataFrame(cached_listing(client_id, client_secret, agent, subreddit, sort, int(listing_limit)))
            st.dataframe(posts, hide_index=True, width="stretch", column_config={"url":st.column_config.LinkColumn("Open")})
        except Exception as exc:
            st.error(f"Subreddit scan failed: {exc}")

with method_tab:
    st.markdown("""
### Collection rules

- Uses Reddit OAuth through PRAW; it does not crawl HTML or bypass access controls.
- Runs only when a user starts a scan. Results are cached for five minutes.
- Limits comment-tree expansion and total collected rows per scan.
- Stores public content only. When a later scan reports deleted or removed content, stored text and author fields are erased.
- Never collects private subreddits, private messages, account profiles or authentication cookies.
- Public comment totals may exceed collected rows because Reddit can withhold, collapse, remove or defer parts of a tree.

For a later ten-minute match monitor, use an external scheduler and durable database. Streamlit itself is the dashboard, not a reliable background scheduler.
""")

st.caption("Independent project; not endorsed by Reddit. Public discussion metrics are not representative polling.")
