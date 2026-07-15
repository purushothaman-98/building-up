from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

DATA = Path("data/papers.json")
KINDS = ("Experimental", "Computational", "Theory + Experiment")
SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

st.set_page_config(page_title="Exciton Research Scanner", page_icon="◌", layout="wide")
st.markdown("""
<style>
.stApp{background:#f6f4ee;color:#17201d}.block-container{max-width:1380px;padding-top:1.45rem}
.hero{background:#103f34;color:white;border-radius:24px;padding:36px 42px;margin-bottom:18px;
background-image:radial-gradient(circle at 90% 8%,#e0ad2d 0,transparent 30%)}
.hero h1{font-size:3rem;letter-spacing:-.05em;margin:.18rem 0}.hero p{max-width:790px;color:#dce9e3;font-size:1.04rem}
.eyebrow{font-size:.76rem;font-weight:800;letter-spacing:.08em}.paper{background:white;border:1px solid #ded9ce;
border-radius:17px;padding:21px 24px 18px;margin:12px 0 5px;box-shadow:0 5px 18px #192d250c}
.paper h3{margin:0 0 7px;font-size:1.22rem;line-height:1.35}.meta{color:#66726c;font-size:.84rem;line-height:1.55}
.signal{border-left:3px solid #d8a838;padding-left:11px;color:#294139;margin:13px 0 8px;font-size:.9rem}
.abstract{color:#35413c;line-height:1.58}.tag{display:inline-block;border-radius:999px;background:#e9efeb;
padding:4px 9px;margin:3px 4px 3px 0;font-size:.75rem}.type{background:#e2b43b;color:#18231e;font-weight:750}
.new{background:#d9eee6;color:#125943;font-weight:750}.links a{color:#11614b;font-weight:750;margin-right:16px;text-decoration:none}
[data-testid="stMetric"]{background:white;border:1px solid #ded9ce;padding:13px;border-radius:14px}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:#17352c!important}
[data-testid="stSidebar"]{background:#17231f}.small-note{color:#68736e;font-size:.82rem}
</style>
<div class="hero"><div class="eyebrow">EXCITON DISCOVERY · UPDATED TWICE DAILY</div>
<h1>Exciton Research Scanner</h1>
<p>Find recent exciton experiments, first-principles calculations, and studies that connect both—classified from the authors’ own abstracts.</p></div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_archive() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"papers": []}


def pretty_text(value: str) -> str:
    """Make common arXiv TeX fragments readable without pretending to be a TeX renderer."""
    value = re.sub(r"\$_(\d+)\$", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = re.sub(r"\$_\{(\d+)\}\$", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = re.sub(r"\$\^\{?([+-])\}?\$", lambda m: m.group(1), value)
    value = re.sub(r"_\{(\d+)\}", lambda m: m.group(1).translate(SUBSCRIPTS), value)
    value = value.replace("\\textendash", "–").replace("~", " ")
    return re.sub(r"\s+", " ", value).strip()


def research_signal(paper: dict) -> str:
    methods = paper.get("methods", [])
    materials = paper.get("materials", [])
    method_text = ", ".join(methods[:3]) if methods else "abstract-level exciton evidence"
    material_text = ", ".join(materials[:2]) if materials else "the reported material system"
    prefix = {
        "Experimental": "Experimental signal",
        "Computational": "Computational signal",
        "Theory + Experiment": "Cross-validation signal",
    }.get(paper.get("study_type"), "Research signal")
    return f"{prefix}: {method_text} applied to {material_text}."


def bibtex(paper: dict) -> str:
    first_author = paper.get("authors", ["unknown"])[0].split()[-1].lower()
    key = re.sub(r"\W+", "", f"{first_author}{paper['submitted'][:4]}{paper['arxiv_id'].split('.')[-1]}")
    authors = " and ".join(paper.get("authors", []))
    return (
        f"@misc{{{key},\n"
        f"  title = {{{pretty_text(paper['title'])}}},\n"
        f"  author = {{{authors}}},\n"
        f"  year = {{{paper['submitted'][:4]}}},\n"
        f"  eprint = {{{paper['arxiv_id']}}},\n"
        f"  archivePrefix = {{arXiv}},\n"
        f"  primaryClass = {{{paper.get('categories', [''])[0]}}}\n"
        f"}}"
    )


archive = load_archive()
papers = archive.get("papers", [])
st.session_state.setdefault("reading_list", set())

search_query = st.text_input(
    "Search the exciton archive",
    placeholder="Try: WSe2 GW-BSE, pump-probe lifetime, perovskite photoluminescence…",
    label_visibility="collapsed",
)

metrics = st.columns(4)
metrics[0].metric("Indexed papers", len(papers))
for column, kind in zip(metrics[1:], KINDS):
    column.metric(kind, sum(p.get("study_type") == kind for p in papers))

with st.sidebar:
    st.header("Refine results")
    materials = sorted({x for p in papers for x in p.get("materials", [])})
    methods = sorted({x for p in papers for x in p.get("methods", [])})
    material = st.selectbox("Material", ["All materials", *materials])
    method = st.selectbox("Method", ["All methods", *methods])
    date_mode = st.selectbox("Date", ["Any date", "Last 7 days", "Last 30 days", "Last 90 days", "This year"])
    sort_mode = st.selectbox("Sort", ["Newest submitted", "Recently updated", "Title A–Z"])
    page_size = st.select_slider("Papers per section", [10, 20, 30, 50], value=20)
    reading_only = st.toggle(f"Reading list ({len(st.session_state.reading_list)})")
    st.divider()
    material_counts = Counter(x for p in papers for x in p.get("materials", []))
    if material_counts:
        st.markdown("##### Active material topics")
        st.caption(" · ".join(f"{name} ({count})" for name, count in material_counts.most_common(6)))
    if archive.get("last_scan"):
        stamp = datetime.fromisoformat(archive["last_scan"].replace("Z", "+00:00"))
        st.caption(f"Last scan: {stamp:%d %b %Y, %H:%M} UTC")
    st.caption("Uses arXiv metadata and author abstracts only.")


def is_visible(paper: dict, kind: str | None) -> bool:
    query = search_query.strip().lower()
    haystack = " ".join([
        paper.get("title", ""), paper.get("abstract", ""), *paper.get("authors", []),
        *paper.get("materials", []), *paper.get("methods", []), *paper.get("matched_keywords", []),
    ]).lower()
    submitted = date.fromisoformat(paper["submitted"][:10])
    today = datetime.now(timezone.utc).date()
    cutoffs = {
        "Last 7 days": today - timedelta(days=7), "Last 30 days": today - timedelta(days=30),
        "Last 90 days": today - timedelta(days=90), "This year": date(today.year, 1, 1),
    }
    return (
        (kind is None or paper.get("study_type") == kind)
        and (not query or all(term in haystack for term in query.split()))
        and (material == "All materials" or material in paper.get("materials", []))
        and (method == "All methods" or method in paper.get("methods", []))
        and (date_mode == "Any date" or submitted >= cutoffs[date_mode])
        and (not reading_only or paper["arxiv_id"] in st.session_state.reading_list)
    )


def sorted_papers(items: list[dict]) -> list[dict]:
    if sort_mode == "Title A–Z":
        return sorted(items, key=lambda p: p["title"].lower())
    field = "updated" if sort_mode == "Recently updated" else "submitted"
    return sorted(items, key=lambda p: p.get(field, ""), reverse=True)


def paper_card(paper: dict, section_key: str) -> None:
    title = pretty_text(paper["title"])
    authors = ", ".join(paper.get("authors", []))
    if len(authors) > 190:
        authors = authors[:187] + "…"
    abstract = pretty_text(paper.get("abstract", ""))
    preview = abstract[:430].rsplit(" ", 1)[0] + ("…" if len(abstract) > 430 else "")
    tags = [paper["study_type"], *paper.get("materials", [])[:4], *paper.get("methods", [])[:5]]
    age = (datetime.now(timezone.utc).date() - date.fromisoformat(paper["submitted"][:10])).days
    badges = "".join(
        f'<span class="tag {"type" if i == 0 else ""}">{html.escape(tag)}</span>' for i, tag in enumerate(tags)
    )
    if age <= 7:
        badges = '<span class="tag new">NEW</span>' + badges
    versions = ", ".join(paper.get("versions_seen", [paper.get("version", "v1")]))
    st.markdown(f"""
    <article class="paper">
      <h3>{html.escape(title)}</h3>
      <div class="meta">{html.escape(authors)}</div>
      <div class="meta">Submitted {paper["submitted"][:10]} · updated {paper["updated"][:10]}
      · {paper["arxiv_id"]} · versions {versions}</div>
      <p>{badges}</p>
      <div class="signal">{html.escape(research_signal(paper))}</div>
      <p class="abstract">{html.escape(preview)}</p>
      <div class="links"><a href="{paper["arxiv_url"]}" target="_blank">arXiv page ↗</a>
      <a href="{paper["pdf_url"]}" target="_blank">Open PDF ↗</a></div>
    </article>
    """, unsafe_allow_html=True)
    actions = st.columns([1.1, 1.1, 5])
    saved = paper["arxiv_id"] in st.session_state.reading_list
    if actions[0].button(
        "★ Saved" if saved else "☆ Save",
        key=f"save-{section_key}-{paper['arxiv_id']}",
        use_container_width=True,
    ):
        if saved:
            st.session_state.reading_list.remove(paper["arxiv_id"])
        else:
            st.session_state.reading_list.add(paper["arxiv_id"])
        st.rerun()
    actions[1].download_button(
        "Cite", bibtex(paper), file_name=f"{paper['arxiv_id'].replace('/', '-')}.bib",
        mime="application/x-bibtex",
        key=f"cite-{section_key}-{paper['arxiv_id']}",
        use_container_width=True,
    )
    with st.expander("Paper details · full abstract · classification evidence"):
        st.markdown(f"**Full abstract**\n\n{abstract}")
        st.markdown("**Why it was classified this way**")
        evidence = paper.get("evidence", {})
        st.write(
            f"Experimental evidence: {'detected' if evidence.get('experimental') else 'not detected'} · "
            f"Computational evidence: {'detected' if evidence.get('computational') else 'not detected'}"
        )
        st.write("Matched terms:", ", ".join(paper.get("matched_keywords", [])) or "None recorded")
        st.write("arXiv categories:", ", ".join(paper.get("categories", [])))


tabs = st.tabs(["Explore", "Experimental", "Computational", "Theory + Experiment"])
for tab, kind in zip(tabs, (None, *KINDS)):
    with tab:
        subset = sorted_papers([p for p in papers if is_visible(p, kind)])
        shown = subset[:page_size]
        st.caption(f"Showing {len(shown):,} of {len(subset):,} matching papers")
        if not shown:
            st.info("No papers match these filters. Broaden the query or clear one of the filters.")
        section_key = (kind or "explore").lower().replace(" ", "-").replace("+", "plus")
        for paper in shown:
            paper_card(paper, section_key)

st.caption("Inspired by modern research-discovery tools such as alphaXiv. Independent project; not affiliated with alphaXiv or arXiv.")
