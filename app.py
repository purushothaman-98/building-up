from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path("data/papers.json")
SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
COLORS = {
    "Experimental": "#1d8a68",
    "Computational": "#4169a1",
    "Theory + Experiment": "#d59f20",
    "Unclassified": "#7b8581",
}

st.set_page_config(page_title="Exciton Research Scanner", page_icon="◌", layout="wide")
st.markdown("""
<style>
.stApp{background:#f5f3ed;color:#17221e}.block-container{max-width:1320px;padding-top:1.3rem}
[data-testid="stSidebar"]{display:none}
.hero{position:relative;overflow:hidden;background:#102f27;color:white;border-radius:26px;padding:42px 48px 38px;margin-bottom:20px}
.hero:after{content:"";position:absolute;width:440px;height:440px;border-radius:50%;right:-90px;top:-260px;
background:radial-gradient(circle,#e4b82f 0,#7f782c 36%,transparent 68%);opacity:.95}
.hero h1{font-size:3.15rem;letter-spacing:-.055em;margin:.25rem 0;position:relative;z-index:1}
.hero p{max-width:760px;color:#dce9e3;font-size:1.05rem;line-height:1.55;position:relative;z-index:1}
.eyebrow{font-size:.75rem;font-weight:800;letter-spacing:.1em;color:#e8c451;position:relative;z-index:1}
.section-head{display:flex;align-items:end;justify-content:space-between;margin:30px 0 8px}
.section-head h2{font-size:1.65rem;letter-spacing:-.025em;margin:0}.section-head span{color:#6d7873;font-size:.86rem}
.paper{background:#fff;border:1px solid #dedbd2;border-radius:17px;padding:20px 23px;margin:10px 0 4px;box-shadow:0 4px 16px #192d2509}
.paper:hover{border-color:#a9bdb5;box-shadow:0 8px 24px #193d3012}.paper h3{font-size:1.17rem;line-height:1.38;margin:0 0 7px}
.paper h3 a{color:#14251f;text-decoration:none}.paper h3 a:hover{color:#126149}.meta{color:#68756f;font-size:.83rem;line-height:1.55}
.preview{color:#34423c;line-height:1.58;margin:12px 0}.tag{display:inline-block;border-radius:999px;background:#edf1ef;
padding:4px 9px;margin:7px 4px 2px 0;font-size:.73rem}.kind{background:#e5eee9;color:#164f3f;font-weight:750}
.links{margin-top:12px}.links a{display:inline-block;border:1px solid #b7c9c1;border-radius:999px;padding:6px 12px;
margin-right:8px;color:#145944;text-decoration:none;font-size:.8rem;font-weight:750}.links a:hover{background:#145944;color:white}
[data-testid="stMetric"]{background:#fff;border:1px solid #dedbd2;padding:14px 17px;border-radius:15px}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:#17352c!important}
details{background:#fafbf9!important;border-radius:12px!important}
</style>
<div class="hero"><div class="eyebrow">ARXIV EXCITON FEED · DAILY UPDATE</div>
<h1>Exciton Research Scanner</h1>
<p>A transparent, date-ordered feed of every paper returned by the scoped arXiv exciton query. Classification labels describe the abstracts but never decide whether a paper is kept.</p>
</div>
""", unsafe_allow_html=True)


def load_archive() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"papers": [], "scans": []}


def pretty(value: str) -> str:
    value = re.sub(r"\$_(\d+)\$", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = re.sub(r"\$_\{(\d+)\}\$", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = re.sub(r"_\{(\d+)\}", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = value.replace("~", " ")
    return re.sub(r"\s+", " ", value).strip()


def paper_card(paper: dict) -> None:
    title = pretty(paper["title"])
    abstract = pretty(paper.get("abstract", ""))
    preview = abstract[:420].rsplit(" ", 1)[0] + ("…" if len(abstract) > 420 else "")
    authors = ", ".join(paper.get("authors", []))
    if len(authors) > 210:
        authors = authors[:207] + "…"
    kind = paper.get("study_type") or "Unclassified"
    label = "General / unclassified" if kind == "Unclassified" else kind
    tags = [label, *paper.get("materials", [])[:4], *paper.get("methods", [])[:5]]
    badges = "".join(
        f'<span class="tag {"kind" if i == 0 else ""}">{html.escape(tag)}</span>'
        for i, tag in enumerate(tags)
    )
    st.markdown(f"""
    <article class="paper">
      <h3><a href="{paper["arxiv_url"]}" target="_blank">{html.escape(title)}</a></h3>
      <div class="meta">{html.escape(authors)}</div>
      <div class="meta">{paper["submitted"][:10]} · updated {paper["updated"][:10]} ·
      arXiv:{paper["arxiv_id"]} · {", ".join(paper.get("categories", []))}</div>
      <div>{badges}</div><p class="preview">{html.escape(preview)}</p>
      <div class="links"><a href="{paper["arxiv_url"]}" target="_blank">arXiv page ↗</a>
      <a href="{paper["pdf_url"]}" target="_blank">PDF ↗</a></div>
    </article>
    """, unsafe_allow_html=True)
    with st.expander("Full abstract and detected metadata"):
        st.write(abstract)
        st.caption("Matched keywords: " + (", ".join(paper.get("matched_keywords", [])) or "none"))


archive = load_archive()
papers = sorted(archive.get("papers", []), key=lambda p: (p.get("submitted", ""), p.get("updated", "")), reverse=True)
today = datetime.now(timezone.utc).date().isoformat()
todays_papers = [paper for paper in papers if paper.get("submitted", "")[:10] == today]
last_scan = archive.get("last_scan")

metrics = st.columns(4)
metrics[0].metric("All raw papers", len(papers))
metrics[1].metric("Submitted today", len(todays_papers))
metrics[2].metric("Newest submission", papers[0]["submitted"][:10] if papers else "—")
metrics[3].metric("Pipeline scans", len(archive.get("scans", [])))

st.markdown(
    f'<div class="section-head"><h2>Today’s papers</h2><span>{today} UTC · {len(todays_papers)} papers</span></div>',
    unsafe_allow_html=True,
)
if todays_papers:
    for paper in todays_papers:
        paper_card(paper)
else:
    st.info("No new arXiv submissions have appeared today in the monitored exciton query. The complete feed continues below.")

st.markdown(
    f'<div class="section-head"><h2>Complete chronological feed</h2><span>Newest first · all {len(papers)} records</span></div>',
    unsafe_allow_html=True,
)
for paper in papers:
    paper_card(paper)

st.markdown('<div class="section-head"><h2>Weekly research activity</h2><span>Based on submission dates in the raw archive</span></div>', unsafe_allow_html=True)
if papers:
    frame = pd.DataFrame({
        "week": pd.to_datetime([p["submitted"] for p in papers], utc=True).tz_convert(None).to_period("W").start_time,
        "classification": [
            "General / unclassified" if p.get("study_type") == "Unclassified" else p.get("study_type")
            for p in papers
        ],
    })
    weekly = frame.groupby(["week", "classification"], as_index=False).size().rename(columns={"size": "papers"})
    chart = (
        alt.Chart(weekly).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("week:T", title="Submission week"),
            y=alt.Y("papers:Q", title="Papers"),
            color=alt.Color("classification:N", title="Abstract classification"),
            tooltip=["week:T", "classification:N", "papers:Q"],
        ).properties(height=340)
    )
    st.altair_chart(chart, use_container_width=True)

with st.expander("Collection scope and latest pipeline run"):
    st.write("Query: exciton OR excitonic, limited to the six configured arXiv physics and condensed-matter categories.")
    st.write("Ordering: submission date, newest first. No material, method, classification, or date filter is applied to this feed.")
    st.write(f"Last scan: {last_scan or 'not yet recorded'}")
    if archive.get("scans"):
        st.json(archive["scans"][-1])

st.caption("Metadata and author abstracts from the official arXiv API. Classification is descriptive and may require manual correction.")
