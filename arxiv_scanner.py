from __future__ import annotations
import argparse, json, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://export.arxiv.org/api/query"
CATEGORIES = ("cond-mat.mtrl-sci","cond-mat.mes-hall","physics.optics","physics.comp-ph","physics.app-ph","physics.chem-ph")
EXPERIMENTAL = {
 "Photoluminescence":("photoluminescence","pl spectra","pl spectrum"),
 "Absorption / reflectance":("absorption spectrum","absorption spectra","reflectance","reflectivity"),
 "Pump–probe spectroscopy":("pump-probe","pump–probe","transient absorption"),
 "Time-resolved spectroscopy":("time-resolved","time resolved","ultrafast spectroscopy"),
 "Magneto-optical measurements":("magneto-optical","magneto optical","magneto-photoluminescence"),
 "Exciton lifetime / dynamics":("exciton lifetime","exciton dynamics","carrier dynamics","decay time")}
COMPUTATIONAL = {
 "DFT":("density functional theory","first-principles","first principles","ab initio","dft"),
 "GW":("g0w0","gw calculation","gw calculations","gw approximation","gw-bse","gw+bse"),
 "Bethe–Salpeter equation":("bethe-salpeter","bethe–salpeter","bse calculation","bse calculations"),
 "TDDFT":("time-dependent density functional theory","time dependent density functional theory","tddft"),
 "Exciton binding energy":("exciton binding energy","excitonic binding energy"),
 "Quasiparticle / optical gaps":("quasiparticle gap","optical gap","quasiparticle band gap")}
EXP_ACTIONS=("we measure","we measured","we observe","we observed","experimentally","experimental results","measurements reveal","spectroscopy reveals")
COMP_ACTIONS=("we calculate","we calculated","we compute","we computed","we perform","we employ","we use","using","calculations show","simulations show","first-principles calculations","ab initio calculations","theoretical calculations")
MATERIALS={"MoS2":("mos2","molybdenum disulfide"),"WS2":("ws2","tungsten disulfide"),"MoSe2":("mose2","molybdenum diselenide"),"WSe2":("wse2","tungsten diselenide"),"hBN":("hbn","hexagonal boron nitride"),"perovskites":("perovskite",),"transition-metal dichalcogenides":("transition metal dichalcogenide","tmd monolayer"),"2D materials":("two-dimensional material","2d material","van der waals heterostructure"),"quantum dots":("quantum dot",)}
NS={"atom":"http://www.w3.org/2005/Atom"}
ID_RE=re.compile(r"(?:abs/)?((?:[a-z-]+/)?\d{4}\.\d{4,5})(v\d+)?$",re.I)
FORMULA_RE=re.compile(r"\b(?:[A-Z][a-z]?\d*){2,5}\b")

def clean(value): return re.sub(r"\s+"," ",value or "").strip()

def matches(text, groups):
    labels, words=[],[]
    for label,terms in groups.items():
        hits=[term for term in terms if term in text]
        if hits: labels.append(label); words.extend(hits)
    return labels,words

def near_action(text, terms, actions, radius=180):
    for term in terms:
        for match in re.finditer(re.escape(term),text):
            window=text[max(0,match.start()-radius):match.end()+radius]
            if any(action in window for action in actions): return True
    return False

def analyze(title, abstract):
    text=clean(f"{title}. {abstract}").lower()
    exp,exp_words=matches(text,EXPERIMENTAL); comp,comp_words=matches(text,COMPUTATIONAL)
    exp_terms=tuple(x for terms in EXPERIMENTAL.values() for x in terms)
    comp_terms=tuple(x for terms in COMPUTATIONAL.values() for x in terms)
    exp_ok=bool(exp) and near_action(text,exp_terms,EXP_ACTIONS)
    comp_ok=bool(comp) and near_action(text,comp_terms,COMP_ACTIONS)
    exp_ok |= bool(exp) and any(x in text for x in ("measurements show","spectra show","measured at"))
    comp_ok |= bool(comp) and any(x in text for x in ("calculated band","computed exciton","predicted binding"))
    kind="Theory + Experiment" if exp_ok and comp_ok else "Computational" if comp_ok else "Experimental" if exp_ok else "Unclassified"
    materials=[name for name,aliases in MATERIALS.items() if any(x in text for x in aliases)]
    formulas=[x for x in FORMULA_RE.findall(f"{title} {abstract}") if x not in {"DFT","GW","BSE","TDDFT","PL"}]
    return {"study_type":kind,"materials":list(dict.fromkeys(materials+formulas[:8])),"methods":list(dict.fromkeys(exp+comp)),"matched_keywords":sorted(set(exp_words+comp_words+[x for x in ("exciton","excitonic") if x in text])),"evidence":{"experimental":exp_ok,"computational":comp_ok}}

def parse_feed(xml):
    papers=[]
    for entry in ET.fromstring(xml).findall("atom:entry",NS):
        raw=clean(entry.findtext("atom:id",namespaces=NS)).rstrip("/"); match=ID_RE.search(raw)
        if not match: continue
        base,version=match.group(1),match.group(2) or "v1"
        title=clean(entry.findtext("atom:title",namespaces=NS)); abstract=clean(entry.findtext("atom:summary",namespaces=NS))
        links={x.attrib.get("type",""):x.attrib.get("href","") for x in entry.findall("atom:link",NS)}
        papers.append({"arxiv_id":base,"version":version,"versioned_id":base+version,"title":title,
          "authors":[clean(x.findtext("atom:name",namespaces=NS)) for x in entry.findall("atom:author",NS)],
          "abstract":abstract,"submitted":clean(entry.findtext("atom:published",namespaces=NS)),
          "updated":clean(entry.findtext("atom:updated",namespaces=NS)),
          "categories":[x.attrib["term"] for x in entry.findall("atom:category",NS)],
          "pdf_url":links.get("application/pdf",f"https://arxiv.org/pdf/{base}"),"arxiv_url":f"https://arxiv.org/abs/{base}",**analyze(title,abstract)})
    return papers

def fetch_recent(max_results=300):
    cats=" OR ".join(f"cat:{x}" for x in CATEGORIES)
    params=urllib.parse.urlencode({"search_query":f"({cats}) AND (all:exciton OR all:excitonic)","start":0,"max_results":max_results,"sortBy":"submittedDate","sortOrder":"descending"})
    request=urllib.request.Request(f"{API_URL}?{params}",headers={"User-Agent":"ExcitonResearchScanner/0.1 (arXiv metadata research scanner)"})
    with urllib.request.urlopen(request,timeout=45) as response: return parse_feed(response.read())

def merge_archive(path,incoming):
    archive=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version":1,"papers":[]}
    existing={x["arxiv_id"]:x for x in archive.get("papers",[])}; new=updated=0
    for paper in incoming:
        old=existing.get(paper["arxiv_id"])
        if old is None: paper["versions_seen"]=[paper["version"]]; existing[paper["arxiv_id"]]=paper; new+=1
        else:
            versions=list(dict.fromkeys(old.get("versions_seen",[old.get("version","v1")])+[paper["version"]]))
            if paper["updated"]>old.get("updated",""): paper["versions_seen"]=versions; existing[paper["arxiv_id"]]=paper; updated+=1
            else: old["versions_seen"]=versions
    archive.update({"last_scan":datetime.now(timezone.utc).isoformat(),"papers":sorted(existing.values(),key=lambda x:x.get("updated",""),reverse=True),"counts":{"total":len(existing),"new_this_scan":new,"updated_this_scan":updated}})
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(archive,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return archive

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,default=Path("data/papers.json")); parser.add_argument("--max-results",type=int,default=300); args=parser.parse_args()
    for attempt in range(3):
        try:
            papers=[x for x in fetch_recent(args.max_results) if x["study_type"]!="Unclassified"]
            print(json.dumps(merge_archive(args.output,papers)["counts"])); return
        except Exception:
            if attempt==2: raise
            time.sleep(3*(attempt+1))
if __name__=="__main__": main()
