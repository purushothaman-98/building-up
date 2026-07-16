from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from ai_classifier import EXPERIMENTAL_METHODS, PROMPT_VERSION

DATA = Path("data/papers.json")
AI_DATA = Path("data/ai_classifications.json")
AI_OVERRIDES = Path("data/ai_overrides.json")
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
[data-testid="stSidebar"]{background:#112b24;border-right:1px solid #28463d}
[data-testid="stSidebar"] *{color:#eef6f2}
[data-testid="stSidebar"] [data-baseweb="select"]>div,[data-testid="stSidebar"] input{background:#0d1714!important;border-color:#35564b!important}
[data-testid="stSidebar"] h2{color:#fff!important;margin-bottom:.15rem}
[data-testid="stSidebar"] .stCaption{color:#b9cbc4!important}
.hero{position:relative;overflow:hidden;background:#102f27;color:white;border-radius:24px;padding:34px 42px 30px;margin-bottom:18px}
.hero:after{content:"";position:absolute;width:440px;height:440px;border-radius:50%;right:-90px;top:-260px;
background:radial-gradient(circle,#e4b82f 0,#7f782c 36%,transparent 68%);opacity:.95}
.hero h1{font-size:2.75rem;letter-spacing:-.05em;margin:.2rem 0;position:relative;z-index:1}
.hero p{max-width:760px;color:#dce9e3;font-size:1.05rem;line-height:1.55;position:relative;z-index:1}
.eyebrow{font-size:.75rem;font-weight:800;letter-spacing:.1em;color:#e8c451;position:relative;z-index:1}
.section-head{display:flex;align-items:end;justify-content:space-between;margin:30px 0 8px}
.section-head h2{font-size:1.65rem;letter-spacing:-.025em;margin:0}.section-head span{color:#6d7873;font-size:.86rem}
.paper{background:#fff;border:1px solid #dedbd2;border-left:5px solid #9aa6a1;border-radius:15px;padding:16px 20px;margin:8px 0 3px;box-shadow:0 4px 16px #192d2509}
.paper:hover{border-color:#a9bdb5;box-shadow:0 8px 24px #193d3012}.paper h3{font-size:1.17rem;line-height:1.38;margin:0 0 7px}
.paper.experimental{border-left-color:#1d8a68}.paper.computational{border-left-color:#4169a1}
.paper.theory-plus-experiment{border-left-color:#d59f20}.paper.unclassified{border-left-color:#96a09c}
.paper h3 a{color:#14251f;text-decoration:none}.paper h3 a:hover{color:#126149}.meta{color:#68756f;font-size:.83rem;line-height:1.55}
.preview{color:#34423c;line-height:1.5;margin:9px 0}.tag{display:inline-block;border-radius:999px;padding:4px 9px;margin:6px 4px 1px 0;font-size:.71rem;font-weight:700}
.tag.kind{background:#dcefe7;color:#12533d}.tag.nature{background:#eee4f7;color:#62357c}.tag.material{background:#e3edf9;color:#285682}
.tag.expmethod{background:#fff0d6;color:#875500}.tag.compmethod{background:#dff2ef;color:#176359}.tag.property{background:#f9e1ed;color:#8b315e}
.tag.relevance{background:#e7ecea;color:#3f5049}.tag.core{background:#d8f0e5;color:#126143}.tag.adjacent{background:#fff0cb;color:#795500}
.links{margin-top:12px}.links a{display:inline-block;border:1px solid #b7c9c1;border-radius:999px;padding:6px 12px;
margin-right:8px;color:#145944;text-decoration:none;font-size:.8rem;font-weight:750}.links a:hover{background:#145944;color:white}
[data-testid="stMetric"]{background:linear-gradient(145deg,#fff,#f6faf8);border:1px solid #d5ddd9;border-top:4px solid #1d8a68;padding:14px 17px;border-radius:15px;box-shadow:0 5px 16px #193d300b}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:#17352c!important}
details{background:#fafbf9!important;border-radius:12px!important}
.stRadio [role="radiogroup"]{display:inline-flex!important;gap:6px;background:#e5ece8;border:1px solid #c8d7d1;padding:6px;border-radius:14px;margin:18px 0 8px}
.stRadio [role="radiogroup"] label{background:#fff!important;border:1px solid #b8cbc3!important;border-radius:10px!important;padding:8px 15px!important}
.stRadio [role="radiogroup"] label p{color:#174f3f!important;font-weight:750!important}
.stRadio [role="radiogroup"] label:has(input:checked){background:#17684f!important;border-color:#17684f!important}
.stRadio [role="radiogroup"] label:has(input:checked) p{color:#fff!important}
.date-band{display:flex;align-items:center;justify-content:space-between;margin:30px 0 10px;padding:11px 15px;
background:#e8eee9;border-left:4px solid #17684f;border-radius:0 12px 12px 0}
.date-band h2{font-size:1.18rem;margin:0;color:#173d31}.date-band span{font-size:.82rem;color:#62726b}
.week-summary{background:#143d31;color:white;border-radius:16px;padding:18px 22px;margin:16px 0 8px}
.week-summary strong{font-size:1.18rem}.week-summary span{float:right;color:#d8e6df}
.filter-panel{margin-top:22px;background:#e9efec;border:1px solid #cad8d2;border-radius:18px;padding:17px 20px 5px}
.filter-panel h2{font-size:1.25rem;margin:0;color:#173d31}.filter-panel p{margin:.3rem 0 .6rem;color:#65736d;font-size:.86rem}
.result-strip{display:flex;justify-content:space-between;align-items:center;background:#173d31;color:white;border-radius:12px;padding:11px 15px;margin:12px 0}
.result-strip span{color:#cfe0d8;font-size:.82rem}
.back-top{position:fixed;right:24px;bottom:22px;z-index:99;background:#173d31;color:white!important;text-decoration:none;padding:9px 13px;border-radius:999px;box-shadow:0 5px 18px #0003;font-size:.78rem;font-weight:800}
.stButton>button{border-radius:999px!important;border:1px solid #abc1b8!important;background:#fff!important;
color:#155540!important;font-weight:750!important}.stButton>button:hover{background:#155540!important;color:white!important}
</style>
<a id="top"></a><div class="hero"><div class="eyebrow">ARXIV EXCITON FEED · DAILY AT 05:17 UTC</div>
<h1>Exciton Research Scanner</h1>
<p>A transparent, date-ordered feed of every paper returned by the scoped arXiv exciton query. Classification labels describe the abstracts but never decide whether a paper is kept.</p>
</div>
""", unsafe_allow_html=True)


def load_archive() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"papers": [], "scans": []}

def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def pretty(value: str) -> str:
    value = re.sub(r"\$_(\d+)\$", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = re.sub(r"\$_\{(\d+)\}\$", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = re.sub(r"_\{(\d+)\}", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = value.replace("~", " ")
    return re.sub(r"\s+", " ", value).strip()


def paper_card(paper: dict) -> None:
    title = pretty(paper["title"])
    abstract = pretty(paper.get("abstract", ""))
    preview = abstract[:255].rsplit(" ", 1)[0] + ("…" if len(abstract) > 255 else "")
    author_list = paper.get("authors", [])
    authors = ", ".join(author_list[:3]) + (" et al." if len(author_list) > 3 else "")
    kind = paper.get("study_type") or "Unclassified"
    kind_class = kind.lower().replace(" + ", "-plus-").replace(" ", "-")
    label = "Unclassified" if kind == "Unclassified" else kind
    decision = paper.get("ai_decision")
    relevance = paper.get("relevance", "Pending AI review" if not decision else "Uncertain")
    badge_items = [(relevance, "relevance core" if relevance == "Core exciton paper" else "relevance adjacent" if relevance == "Exciton-adjacent" else "relevance"), (label, "kind"), (paper.get("paper_nature", "Unclassified nature"), "nature")]
    material_labels = [*paper.get("material_families", [])[:1], *paper.get("materials", [])[:1]]
    badge_items.extend((x, "material") for x in material_labels)
    methods = paper.get("methods", [])
    badge_items.extend((x, "expmethod" if x in EXPERIMENTAL_METHODS else "compmethod") for x in methods[:2])
    badge_items.extend((x, "property") for x in paper.get("exciton_properties", [])[:2])
    visible_badges = badge_items[:6]
    hidden_count = max(0, len(badge_items) - len(visible_badges))
    badges = "".join(f'<span class="tag {css}">{html.escape(tag)}</span>' for tag, css in visible_badges)
    if hidden_count:
        badges += f'<span class="tag relevance">+{hidden_count} more</span>'
    st.markdown(f"""
    <article class="paper {kind_class}">
      <h3><a href="{paper["arxiv_url"]}" target="_blank">{html.escape(title)}</a></h3>
      <div class="meta">{html.escape(authors)}</div>
      <div class="meta">Submitted {paper["submitted"][:10]} · arXiv:{paper["arxiv_id"]}</div>
      <div>{badges}</div><p class="preview">{html.escape(preview)}</p>
      <div class="links"><a href="{paper["arxiv_url"]}" target="_blank">arXiv page ↗</a>
      <a href="{paper["pdf_url"]}" target="_blank">PDF ↗</a></div>
    </article>
    """, unsafe_allow_html=True)
    with st.expander("Abstract, complete metadata and why classified"):
        st.write(abstract)
        st.caption(f'Updated {paper.get("updated", "")[:10]} · Categories: {", ".join(paper.get("categories", []))} · Versions: {", ".join(paper.get("versions_seen", [paper.get("version", "v1")]))}')
        if decision:
            st.markdown("**Full-metadata AI assessment**")
            st.markdown(f'- **Decision:** {"Include in final feed" if decision.get("include_in_feed") else "Exclude from final feed"}')
            st.markdown(f'- **Confidence:** {float(decision.get("confidence", 0)):.0%}')
            st.markdown(f'- **Reason:** {html.escape(decision.get("reason", ""))}')
            if decision.get("evidence"):
                st.markdown(f'- **Supporting abstract evidence:** {html.escape("; ".join(decision["evidence"][:5]))}')
            st.caption(f'Model: {decision.get("model", "unknown")} · Prompt: {decision.get("prompt_version", "unknown")} · Classified: {decision.get("classified_at", "unknown")}')
            return
        evidence = paper.get("classification_evidence", {})
        st.markdown("**Why classified**")
        rows = [
            ("Relevance", evidence.get("relevance", [])),
            ("Experimental evidence", evidence.get("experimental_actions", [])),
            ("Computational evidence", evidence.get("computational_actions", [])),
            ("Detected experimental methods", list(evidence.get("experimental_methods", {}).keys())),
            ("Detected computational methods", list(evidence.get("computational_methods", {}).keys())),
            ("Material evidence", [f'{name}: {", ".join(hits[:2])}' for name, hits in evidence.get("materials", {}).items()]),
            ("Property evidence", [f'{name}: {", ".join(hits[:2])}' for name, hits in evidence.get("properties", {}).items()]),
        ]
        for heading, values in rows:
            if values:
                st.markdown(f"- **{heading}:** {html.escape('; '.join(values[:5]))}")
        st.caption("Transparent abstract rules; these labels are discovery aids, not scientific judgments.")


archive = load_archive()
ai_store = load_json(AI_DATA, {"records": {}, "runs": []})
ai_records = ai_store.get("records", {})
ai_overrides = load_json(AI_OVERRIDES, {})
effective_decisions = {**ai_records, **ai_overrides}

def apply_ai_decision(paper: dict) -> dict:
    merged = dict(paper)
    decision = effective_decisions.get(paper.get("arxiv_id"))
    if not decision or decision.get("prompt_version") != PROMPT_VERSION:
        merged["ai_decision"] = None
        merged["relevance"] = "Pending AI review"
        merged["study_type"] = "Unclassified"
        merged["paper_nature"] = "Uncertain"
        merged["materials"] = []
        merged["material_families"] = []
        merged["methods"] = []
        merged["exciton_properties"] = []
        return merged
    merged["ai_decision"] = decision
    merged["relevance"] = decision.get("relevance", merged.get("relevance"))
    merged["study_type"] = decision.get("research_type", merged.get("study_type"))
    merged["paper_nature"] = decision.get("paper_nature", merged.get("paper_nature"))
    merged["materials"] = decision.get("materials") or merged.get("materials", [])
    merged["material_families"] = decision.get("material_families") or merged.get("material_families", [])
    merged["methods"] = list(dict.fromkeys(decision.get("experimental_methods", []) + decision.get("computational_methods", []))) or merged.get("methods", [])
    merged["exciton_properties"] = decision.get("exciton_properties") or merged.get("exciton_properties", [])
    return merged

all_papers = sorted((apply_ai_decision(p) for p in archive.get("papers", [])), key=lambda p: (p.get("submitted", ""), p.get("updated", "")), reverse=True)
last_scan = archive.get("last_scan")
latest_date = all_papers[0]["submitted"][:10] if all_papers else None
week_start = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d") if latest_date else None
raw_papers = [p for p in all_papers if week_start <= p.get("submitted", "")[:10] <= latest_date] if week_start else []
latest_count = sum(p.get("submitted", "")[:10] == latest_date for p in raw_papers) if latest_date else 0
last_scan_display = "—"
if last_scan:
    try:
        last_scan_display = datetime.fromisoformat(last_scan.replace("Z", "+00:00")).strftime("%d %b, %H:%M UTC")
    except ValueError:
        last_scan_display = last_scan

metrics = st.columns(4)
reviewed_count = sum(bool(p.get("ai_decision")) for p in raw_papers)
approved_count = sum((p.get("ai_decision") or {}).get("include_in_feed") is True for p in raw_papers)
metrics[0].metric("Papers this week", len(raw_papers))
metrics[1].metric("AI reviewed", reviewed_count)
metrics[2].metric("AI approved", approved_count)
metrics[3].metric("Pending review", len(raw_papers) - reviewed_count)
st.caption(f"Latest available arXiv week: {week_start or '—'} to {latest_date or '—'} · Last metadata scan: {last_scan_display}")

paper_natures_available = sorted({p.get("paper_nature", "Unclassified nature") for p in raw_papers})
family_options = sorted({x for p in raw_papers for x in p.get("material_families", [])})
specific_options = sorted({x for p in raw_papers for x in p.get("materials", [])})
material_options = [f"Family · {x}" for x in family_options] + [f"Material · {x}" for x in specific_options]
method_options = sorted({x for p in raw_papers for x in p.get("methods", [])})
property_options = sorted({x for p in raw_papers for x in p.get("exciton_properties", [])})
relevance_options = ["Core exciton paper", "Exciton-adjacent", "Uncertain"]
study_type_options = ["Experimental", "Computational", "Theory + Experiment", "Unclassified"]

def field_counts(field: str) -> Counter:
    return Counter(p.get(field, "Unclassified") for p in raw_papers)

study_counts = field_counts("study_type")
nature_counts = field_counts("paper_nature")
relevance_counts = field_counts("relevance")
material_counts = Counter(
    [f"Family · {x}" for p in raw_papers for x in p.get("material_families", [])]
    + [f"Material · {x}" for p in raw_papers for x in p.get("materials", [])]
)
method_counts = Counter(x for p in raw_papers for x in p.get("methods", []))
property_counts = Counter(x for p in raw_papers for x in p.get("exciton_properties", []))

FILTER_KEYS = ["search_filter", "feed_mode", "relevance_filter", "study_filter", "nature_filter", "material_filter", "method_filter", "property_filter"]
def clear_filters() -> None:
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)
    st.session_state.paper_page = 1

with st.sidebar:
    st.header("Explore the archive")
    st.caption("Filter the latest available arXiv week. Historical records remain stored for deduplication.")
    feed_mode = st.radio("Feed", ["All papers this week", "AI-approved final feed", "Pending AI review"], key="feed_mode")
    search_text = st.text_input(
        "Search",
        placeholder="Title, abstract, author, arXiv ID…",
        key="search_filter",
    )
    selected_relevance = st.multiselect("Exciton relevance", relevance_options, key="relevance_filter", format_func=lambda x: f"{x} — {relevance_counts.get(x, 0)}")
    study_types = st.multiselect(
        "Research type",
        study_type_options,
        key="study_filter",
        format_func=lambda x: f"{x} — {study_counts.get(x, 0)}",
    )
    paper_natures = st.multiselect("Paper nature", paper_natures_available, key="nature_filter", format_func=lambda x: f"{x} — {nature_counts.get(x, 0)}")
    selected_materials = st.multiselect("Material", material_options, key="material_filter", format_func=lambda x: f"{x} — {material_counts.get(x, 0)}")
    selected_methods = st.multiselect("Method", method_options, key="method_filter", format_func=lambda x: f"{x} — {method_counts.get(x, 0)}")
    selected_properties = st.multiselect("Exciton property", property_options, key="property_filter", format_func=lambda x: f"{x} — {property_counts.get(x, 0)}")
    st.button("Clear all filters", use_container_width=True, on_click=clear_filters)

def searchable_text(paper: dict) -> str:
    values = [
        paper.get("title", ""), paper.get("abstract", ""), paper.get("arxiv_id", ""),
        " ".join(paper.get("authors", [])), " ".join(paper.get("materials", [])),
        " ".join(paper.get("material_families", [])), " ".join(paper.get("methods", [])),
        " ".join(paper.get("exciton_properties", [])), paper.get("relevance", ""), paper.get("paper_nature", ""),
    ]
    return " ".join(values).lower()

def material_match(paper: dict) -> bool:
    if not selected_materials:
        return True
    available = {f"Family · {x}" for x in paper.get("material_families", [])}
    available.update(f"Material · {x}" for x in paper.get("materials", []))
    return bool(available.intersection(selected_materials))

query_terms = search_text.lower().split()
if feed_mode == "AI-approved final feed":
    source_papers = [p for p in raw_papers if (p.get("ai_decision") or {}).get("include_in_feed") is True]
elif feed_mode == "Pending AI review":
    source_papers = [p for p in raw_papers if not p.get("ai_decision")]
else:
    source_papers = raw_papers
papers = [
    paper for paper in source_papers
    if (not query_terms or all(term in searchable_text(paper) for term in query_terms))
    and (not study_types or paper.get("study_type", "Unclassified") in study_types)
    and (not selected_relevance or paper.get("relevance", "Uncertain") in selected_relevance)
    and (not paper_natures or paper.get("paper_nature", "Unclassified nature") in paper_natures)
    and material_match(paper)
    and (not selected_methods or bool(set(selected_methods).intersection(paper.get("methods", []))))
    and (not selected_properties or bool(set(selected_properties).intersection(paper.get("exciton_properties", []))))
]
active_count = bool(feed_mode != "All papers this week" or search_text or selected_relevance or study_types or paper_natures or selected_materials or selected_methods or selected_properties)
with st.sidebar:
    st.markdown(f"**{len(papers)} matching papers**")
    st.caption("Filters active" if active_count else "Showing the complete seven-day feed")
st.markdown(
    f'<div class="result-strip"><strong>{len(papers)} matching papers</strong><span>{"Filters active" if active_count else "Latest seven-day feed"}</span></div>',
    unsafe_allow_html=True,
)
st.caption(f"AI review progress: {reviewed_count} of {len(raw_papers)} papers · {approved_count} currently approved for the final feed · cached decisions are reused until metadata changes.")

selected_view = st.radio(
    "Choose view",
    ["Daily paper feed", "Time series & analysis"],
    horizontal=True,
    label_visibility="collapsed",
)


def polished(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure(background="#ffffff")
        .configure_view(fill="#ffffff", stroke="#dfe5e2", cornerRadius=10)
        .configure_axis(
            labelColor="#40534b", titleColor="#1e3c32", gridColor="#e7ece9",
            domainColor="#b8c5c0", tickColor="#b8c5c0",
        )
        .configure_legend(labelColor="#40534b", titleColor="#1e3c32")
        .configure_title(color="#173d31", fontSize=15, anchor="start")
    )

def set_page(page: int) -> None:
    st.session_state.paper_page = page

def page_window(current_page: int, total_pages: int) -> list[int]:
    window_start = max(1, min(current_page - 1, max(1, total_pages - 2)))
    return list(range(window_start, min(total_pages, window_start + 2) + 1))

def top_pagination(current_page: int, total_pages: int) -> None:
    if total_pages <= 1:
        return
    pages = page_window(current_page, total_pages)
    columns = st.columns([1, *([.55] * len(pages)), 1, 3])
    columns[0].button("←", disabled=current_page == 1, on_click=set_page, args=(current_page - 1,), key="top_previous", help="Previous page")
    for index, page in enumerate(pages, start=1):
        columns[index].button(str(page), on_click=set_page, args=(page,), key=f"top_page_{page}", type="primary" if page == current_page else "secondary")
    columns[len(pages) + 1].button("→", disabled=current_page == total_pages, on_click=set_page, args=(current_page + 1,), key="top_next", help="Next page")


if selected_view == "Daily paper feed":
    page_size = 20
    total_pages = max(1, (len(papers) + page_size - 1) // page_size)
    filter_signature = (search_text, tuple(selected_relevance), tuple(study_types), tuple(paper_natures), tuple(selected_materials), tuple(selected_methods), tuple(selected_properties))
    if st.session_state.get("filter_signature") != filter_signature:
        st.session_state.filter_signature = filter_signature
        st.session_state.paper_page = 1
    current_page = min(max(1, st.session_state.get("paper_page", 1)), total_pages)
    st.session_state.paper_page = current_page
    start = (current_page - 1) * page_size
    page_papers = papers[start:start + page_size]
    st.caption(f"Newest first · 20 papers per page · page {current_page} of {total_pages}")
    top_pagination(current_page, total_pages)
    grouped_dates = {}
    for paper in page_papers:
        grouped_dates.setdefault(paper["submitted"][:10], []).append(paper)

    for submission_date, day_papers in grouped_dates.items():
        display_date = datetime.strptime(submission_date, "%Y-%m-%d").strftime("%A, %d %B %Y")
        st.markdown(
            f'<div class="date-band"><h2>{display_date}</h2><span>{len(day_papers)} papers</span></div>',
            unsafe_allow_html=True,
        )
        for paper in day_papers:
            paper_card(paper)

    if total_pages > 1:
        pages = page_window(current_page, total_pages)
        nav_left, nav_pages, nav_right = st.columns([1, 3, 1])
        nav_left.button("← Previous", disabled=current_page == 1, use_container_width=True, on_click=set_page, args=(current_page - 1,), key="previous_page")
        selected_page = nav_pages.radio("Page", pages, index=pages.index(current_page), horizontal=True, label_visibility="collapsed", key=f"page_choice_{pages[0]}")
        if selected_page != current_page:
            st.session_state.paper_page = selected_page
            st.rerun()
        nav_right.button("Next →", disabled=current_page == total_pages, use_container_width=True, on_click=set_page, args=(current_page + 1,), key="next_page")

if selected_view == "Time series & analysis":
    st.markdown('<div class="section-head"><h2>Submission time series</h2><span>Daily and weekly activity</span></div>', unsafe_allow_html=True)
    if papers:
        daily = pd.DataFrame({"date": pd.to_datetime([p["submitted"][:10] for p in papers])})
        daily = daily.groupby("date", as_index=False).size().rename(columns={"size": "papers"})
        peak_daily = daily.loc[daily["papers"].idxmax()]
        category_counts = Counter(category for p in papers for category in p.get("categories", []))
        classification_counts = Counter(
            "General / unclassified" if p.get("study_type") == "Unclassified" else p.get("study_type")
            for p in papers
        )
        insight_cols = st.columns(4)
        insight_cols[0].metric("Peak day", int(peak_daily["papers"]))
        insight_cols[1].metric("Peak date", peak_daily["date"].strftime("%d %b"))
        largest_group = classification_counts.most_common(1)[0][0].replace("General / unclassified", "General")
        top_category = category_counts.most_common(1)[0][0].replace("cond-mat.", "")
        insight_cols[2].metric("Largest group", largest_group)
        insight_cols[3].metric("Top category", top_category)
        daily_chart = (
            alt.Chart(daily).mark_line(point=True, color="#17684f", strokeWidth=2.5).encode(
                x=alt.X("date:T", title="Submission date"),
                y=alt.Y("papers:Q", title="Papers per day"),
                tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("papers:Q", title="Papers")],
            ).properties(height=300)
        )
        st.altair_chart(polished(daily_chart), use_container_width=True, theme=None)

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
            color=alt.Color(
                "classification:N", title="Abstract classification",
                scale=alt.Scale(
                    domain=["General / unclassified", "Experimental", "Computational", "Theory + Experiment"],
                    range=["#96a09c", "#1d8a68", "#4169a1", "#d59f20"],
                ),
            ),
                tooltip=["week:T", "classification:N", "papers:Q"],
            ).properties(height=330)
        )
        st.altair_chart(polished(weekly_chart), use_container_width=True, theme=None)

        left, right = st.columns(2)
        composition = pd.DataFrame(
            [{"classification": key, "papers": value} for key, value in classification_counts.items()]
        )
        donut = (
            alt.Chart(composition).mark_arc(innerRadius=58, outerRadius=105).encode(
                theta=alt.Theta("papers:Q"),
                color=alt.Color(
                    "classification:N", title="Classification",
                    scale=alt.Scale(
                        domain=["General / unclassified", "Experimental", "Computational", "Theory + Experiment"],
                        range=["#96a09c", "#1d8a68", "#4169a1", "#d59f20"],
                    ),
                ),
                tooltip=["classification:N", "papers:Q"],
            ).properties(title="Classification composition", height=310)
        )
        left.altair_chart(polished(donut), use_container_width=True, theme=None)

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
        right.altair_chart(polished(category_chart), use_container_width=True, theme=None)

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
                color=alt.Color(
                    "metric:N", title="Metric",
                    scale=alt.Scale(
                        domain=["fetched", "new", "updated", "total"],
                        range=["#6f8f83", "#1d8a68", "#d59f20", "#4169a1"],
                    ),
                ),
                tooltip=["scanned_at:T", "metric:N", "papers:Q"],
            ).properties(height=290)
        )
        st.altair_chart(polished(scan_chart), use_container_width=True, theme=None)
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
st.markdown('<a class="back-top" href="#top">↑ Back to top</a>', unsafe_allow_html=True)
