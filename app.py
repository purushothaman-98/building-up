from __future__ import annotations
import html, json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import streamlit as st

DATA=Path("data/papers.json")
st.set_page_config(page_title="Exciton Research Scanner",page_icon="◌",layout="wide")
st.markdown("""<style>
.stApp{background:#f4f1e9;color:#17201d}.block-container{max-width:1420px;padding-top:1.7rem}
.hero{background:#12372d;color:white;border-radius:26px;padding:42px 46px;margin-bottom:22px;background-image:radial-gradient(circle at 88% 15%,#d8a838 0,transparent 29%)}
.hero h1{font-size:3.25rem;letter-spacing:-.05em;margin:.2rem 0}.hero p{max-width:760px;color:#dce9e3;font-size:1.08rem}
.paper{background:white;border:1px solid #ded9ce;border-radius:18px;padding:22px 24px;margin:12px 0;box-shadow:0 5px 18px #192d250c}
.paper h3{margin:0 0 7px;font-size:1.18rem}.meta{color:#68736e;font-size:.86rem}.abstract{color:#35413c;line-height:1.55}
.tag{display:inline-block;border-radius:999px;background:#e8eee9;padding:4px 9px;margin:3px 4px 3px 0;font-size:.76rem}.type{background:#d8a838;font-weight:700}
.links a{color:#11614b;font-weight:700;margin-right:14px}[data-testid="stMetric"]{background:white;border:1px solid #ded9ce;padding:13px;border-radius:14px}
</style><div class="hero"><small>ARXIV DISCOVERY · RULE-BASED CLASSIFICATION</small><h1>Exciton Research Scanner</h1>
<p>A living index of recent experimental, computational and combined exciton studies across materials science, condensed matter and optics.</p></div>""",unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load():
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"papers":[]}
archive=load(); papers=archive.get("papers",[])
kinds=("Experimental","Computational","Theory + Experiment")
cols=st.columns(4); cols[0].metric("Indexed papers",len(papers))
for col,kind in zip(cols[1:],kinds): col.metric(kind,sum(x.get("study_type")==kind for x in papers))
with st.sidebar:
    st.header("Filter the archive")
    query=st.text_input("Search",placeholder="exciton, material, author…").strip().lower()
    materials=sorted({x for p in papers for x in p.get("materials",[])})
    methods=sorted({x for p in papers for x in p.get("methods",[])})
    material=st.selectbox("Material",["All materials",*materials]); method=st.selectbox("Method",["All methods",*methods])
    date_mode=st.selectbox("Date",["Any date","Last 7 days","Last 30 days","Last 90 days","This year"])
    st.divider()
    if archive.get("last_scan"):
        stamp=datetime.fromisoformat(archive["last_scan"].replace("Z","+00:00")); st.caption(f"Last scan: {stamp:%d %b %Y, %H:%M} UTC")
    st.caption("Metadata and abstracts only. Classification is transparent and keyword-based.")

def is_visible(p,kind):
    haystack=" ".join([p.get("title",""),p.get("abstract",""),*p.get("authors",[]),*p.get("materials",[]),*p.get("methods",[])]).lower()
    submitted=date.fromisoformat(p["submitted"][:10]); today=datetime.now(timezone.utc).date()
    cutoffs={"Last 7 days":today-timedelta(7),"Last 30 days":today-timedelta(30),"Last 90 days":today-timedelta(90),"This year":date(today.year,1,1)}
    return (kind is None or p.get("study_type")==kind) and (not query or query in haystack) and (material=="All materials" or material in p.get("materials",[])) and (method=="All methods" or method in p.get("methods",[])) and (date_mode=="Any date" or submitted>=cutoffs[date_mode])

def card(p):
    authors=", ".join(p.get("authors",[])); authors=authors if len(authors)<180 else authors[:177]+"…"
    abstract=p.get("abstract",""); preview=abstract[:520]+("…" if len(abstract)>520 else "")
    tags=[p["study_type"],*p.get("materials",[]),*p.get("methods",[])]
    badges="".join(f'<span class="tag {"type" if i==0 else ""}">{html.escape(x)}</span>' for i,x in enumerate(tags))
    st.markdown(f"""<article class="paper"><h3>{html.escape(p["title"])}</h3><div class="meta">{html.escape(authors)}</div>
    <div class="meta">Submitted {p["submitted"][:10]} · updated {p["updated"][:10]} · {p["arxiv_id"]} · versions {", ".join(p.get("versions_seen",[p.get("version","v1")]))}</div>
    <p>{badges}</p><p class="abstract">{html.escape(preview)}</p><div class="links"><a href="{p["arxiv_url"]}" target="_blank">Abstract ↗</a><a href="{p["pdf_url"]}" target="_blank">PDF ↗</a></div></article>""",unsafe_allow_html=True)

tabs=st.tabs(["Latest Papers",*kinds])
for tab,kind in zip(tabs,(None,*kinds)):
    with tab:
        subset=[p for p in papers if is_visible(p,kind)]; st.caption(f"{len(subset):,} matching papers")
        if not subset: st.info("No papers match these filters yet. Run the scanner to seed or update the archive.")
        for paper in subset: card(paper)
st.caption("Uses the official arXiv API. Independent project; not affiliated with or endorsed by arXiv.")
