# ThreadScope

An OAuth-only Streamlit dashboard for scanning public Reddit posts and subreddit listings. It is designed as the base for timestamped sports match-thread analysis.

## Why PRAW

PRAW is the maintained Python Reddit API wrapper. It authenticates with OAuth, observes Reddit rate-limit responses, and traverses nested comment forests. This project does not crawl Reddit HTML or rely on unauthenticated `.json` URLs.

## Features

- scan a public post by URL or submission ID
- browse public subreddit listings
- bounded `MoreComments` expansion and configurable row caps
- five-minute Streamlit cache to avoid duplicate calls
- timestamped post/comment snapshots
- deduplication-ready stable Reddit IDs
- deleted/removed bodies are not stored, and later deletion observations erase historical local text
- CSV download and a ten-minute publication timeline

## Configure Reddit access

Create an approved Reddit application and add the credentials to `.streamlit/secrets.toml` locally or Streamlit Community Cloud **App settings → Secrets**:

```toml
[reddit]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
user_agent = "web:threadscope:0.1 (by /u/YOUR_REDDIT_USERNAME)"
```

Never commit the secrets file.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Local CSV snapshots are stored under `data/` and ignored by Git. Streamlit Cloud's local filesystem is not durable; a later scheduled match monitor should write snapshots to a proper database.

## Planned match-monitor layer

The next layer can scan a configured match thread every ten minutes, append counters and new/edited comment states to a durable database, and calculate comment velocity, score-event reactions, active discussion topics, frequently mentioned players, questions, and phase-by-phase conversation. Scheduling should be external to Streamlit.

## Responsible use

Follow Reddit's current Developer Terms, Data API Terms, Responsible Builder Policy, attribution requirements and rate limits. Do not use collected data for surveillance, user profiling, model training, or attempts to recover removed content.
