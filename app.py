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
.stTabs [data-baseweb="tab-list"]{gap:10px;border-bottom:1px solid #d9d6ce;margin-top:18px}
.stTabs [data-baseweb="tab"]{height:46px;padding:0 18px;color:#52625b!important}
.stTabs [aria-selected="true"]{background:#e3eee9!important;color:#105a44!important;font-weight:800;border-radius:11px 11px 0 0}
.date-band{display:flex;align-items:center;justify-content:space-between;margin:30px 0 10px;padding:11px 15px;
background:#e8eee9;border-left:4px solid #17684f;border-radius:0 12px 12px 0}
.date-band h2{font-size:1.18rem;margin:0;color:#173d31}.date-band span{font-size:.82rem;color:#62726b}
</style>
<div class="hero"><div class="eyebrow">ARXIV EXCITON FEED · DAILY AT 05:17 UTC</div>
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
last_scan = archive.get("last_scan")
latest_date = papers[0]["submitted"][:10] if papers else None
latest_count = sum(p.get("submitted", "")[:10] == latest_date for p in papers) if latest_date else 0

metrics = st.columns(4)
metrics[0].metric("All raw papers", len(papers))
metrics[1].metric("Latest arXiv day", latest_count)
metrics[2].metric("Newest submission", latest_date or "—")
metrics[3].metric("Pipeline scans", len(archive.get("scans", [])))

feed_tab, analysis_tab = st.tabs(["Daily paper feed", "Time series & analysis"])

with feed_tab:
    st.caption("Every raw record, grouped by its arXiv submission date. Newest day first.")
    grouped_dates = {}
    for paper in papers:
        grouped_dates.setdefault(paper["submitted"][:10], []).append(paper)
    for submission_date, day_papers in grouped_dates.items():
        display_date = datetime.strptime(submission_date, "%Y-%m-%d").strftime("%A, %d %B %Y")
        st.markdown(
            f'<div class="date-band"><h2>{display_date}</h2><span>{len(day_papers)} papers</span></div>',
            unsafe_allow_html=True,
        )
        for paper in day_papers:
            paper_card(paper)

with analysis_tab:
    st.markdown('<div class="section-head"><h2>Submission time series</h2><span>Daily and weekly activity</span></div>', unsafe_allow_html=True)
    if papers:
        daily = pd.DataFrame({"date": pd.to_datetime([p["submitted"][:10] for p in papers])})
        daily = daily.groupby("date", as_index=False).size().rename(columns={"size": "papers"})
        daily_chart = (
            alt.Chart(daily).mark_line(point=True, color="#17684f", strokeWidth=2.5).encode(
                x=alt.X("date:T", title="Submission date"),
                y=alt.Y("papers:Q", title="Papers per day"),
                tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("papers:Q", title="Papers")],
            ).properties(height=300)
        )
        st.altair_chart(daily_chart, use_container_width=True)

        frame = pd.DataFrame({
            "week": pd.to_datetime([p["submitted"] for p in papers], utc=True).tz_convert(None).to_period("W").start_time,
            "classification": [
                "General / unclassified" if p.get("study_type") == "Unclassified" else p.get("study_type")
                for p in papers
            ],
        })
        weekly = frame.groupby(["week", "classification"], as_index=False).size().rename(columns={"size": "papers"})
        weekly_chart = (
            alt.Chart(weekly).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X("week:T", title="Submission week"),
                y=alt.Y("papers:Q", title="Papers"),
                color=alt.Color("classification:N", title="Abstract classification"),
                tooltip=["week:T", "classification:N", "papers:Q"],
            ).properties(height=330)
        )
        st.altair_chart(weekly_chart, use_container_width=True)

        left, right = st.columns(2)
        classification_counts = Counter(
            "General / unclassified" if p.get("study_type") == "Unclassified" else p.get("study_type")
            for p in papers
        )
        composition = pd.DataFrame(
            [{"classification": key, "papers": value} for key, value in classification_counts.items()]
        )
        donut = (
            alt.Chart(composition).mark_arc(innerRadius=58, outerRadius=105).encode(
                theta=alt.Theta("papers:Q"),
                color=alt.Color("classification:N", title="Classification"),
                tooltip=["classification:N", "papers:Q"],
            ).properties(title="Classification composition", height=310)
        )
        left.altair_chart(donut, use_container_width=True)

        category_counts = Counter(category for p in papers for category in p.get("categories", []))
        categories = pd.DataFrame(
            [{"category": key, "papers": value} for key, value in category_counts.most_common(12)]
        )
        category_chart = (
            alt.Chart(categories).mark_bar(color="#416f91", cornerRadiusEnd=3).encode(
                x=alt.X("papers:Q", title="Papers"),
                y=alt.Y("category:N", sort="-x", title=None),
                tooltip=["category:N", "papers:Q"],
            ).properties(title="Top arXiv categories", height=310)
        )
        right.altair_chart(category_chart, use_container_width=True)

    st.markdown('<div class="section-head"><h2>Pipeline history</h2><span>What each automated scan produced</span></div>', unsafe_allow_html=True)
    scans = archive.get("scans", [])
    if scans:
        scan_frame = pd.DataFrame(scans)
        scan_frame["scanned_at"] = pd.to_datetime(scan_frame["scanned_at"], utc=True)
        scan_long = scan_frame.melt(
            id_vars=["scanned_at"], value_vars=["fetched", "new", "updated", "total"],
            var_name="metric", value_name="papers",
        )
        scan_chart = (
            alt.Chart(scan_long).mark_line(point=True, strokeWidth=2.4).encode(
                x=alt.X("scanned_at:T", title="Scan time (UTC)"),
                y=alt.Y("papers:Q", title="Paper count"),
                color=alt.Color("metric:N", title="Metric"),
                tooltip=["scanned_at:T", "metric:N", "papers:Q"],
            ).properties(height=290)
        )
        st.altair_chart(scan_chart, use_container_width=True)
        st.dataframe(
            scan_frame[["scanned_at", "since", "fetched", "new", "updated", "total"]]
            .sort_values("scanned_at", ascending=False),
            hide_index=True, use_container_width=True,
        )

    with st.expander("Collection scope and latest pipeline run"):
        st.write("Query: exciton OR excitonic, limited to the six configured arXiv physics and condensed-matter categories.")
        st.write("The feed applies no material, method, classification, or date filter.")
        st.write(f"Last scan: {last_scan or 'not yet recorded'}")
        if scans:
            st.json(scans[-1])

st.caption("Metadata and author abstracts from the official arXiv API. Classification is descriptive and may require manual correction.")
