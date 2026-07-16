from __future__ import annotations
import argparse, json, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

API_URL = "https://export.arxiv.org/api/query"
CATEGORIES = ("cond-mat.mtrl-sci","cond-mat.mes-hall","physics.optics","physics.comp-ph","physics.app-ph","physics.chem-ph")
EXPERIMENTAL = {
 "Photoluminescence":("photoluminescence","pl spectra","pl spectrum"),
 "Absorption / reflectance":("absorption spectrum","absorption spectra","reflectance","reflectivity","reflectance contrast"),
 "Pump–probe spectroscopy":("pump-probe","pump–probe","transient absorption"),
 "Time-resolved spectroscopy":("time-resolved","time resolved","ultrafast spectroscopy"),
 "Magneto-optical measurements":("magneto-optical","magneto optical","magneto-photoluminescence"),
 "Raman spectroscopy":("raman spectroscopy","raman scattering"),
 "Photoemission / photocurrent":("arpes","photoemission spectroscopy","photocurrent spectroscopy"),
 "Coherent / THz spectroscopy":("two-dimensional coherent spectroscopy","2d coherent spectroscopy","terahertz spectroscopy","thz spectroscopy"),
 "Exciton lifetime / dynamics":("exciton lifetime","exciton dynamics","carrier dynamics","decay time","exciton diffusion"),
 "Linewidth / fine structure":("exciton linewidth","excitonic linewidth","linewidth","line width","fine-structure splitting","fine structure splitting"),
 "Exciton g-factor":("exciton g-factor","exciton g factor","excitonic g-factor","g-factor","g factor")}
COMPUTATIONAL = {
 "DFT":("density functional theory","first-principles","first principles","ab initio","dft"),
 "GW":("g0w0","gw calculation","gw calculations","gw approximation","gw-bse","gw+bse"),
 "Bethe–Salpeter equation":("bethe-salpeter","bethe–salpeter","bse calculation","bse calculations"),
 "TDDFT":("time-dependent density functional theory","time dependent density functional theory","tddft"),
 "Model Hamiltonian":("tight-binding","tight binding","effective-mass model","effective mass model","model hamiltonian"),
 "Quantum Monte Carlo":("quantum monte carlo","diffusion monte carlo"),
 "Exciton binding energy":("exciton binding energy","excitonic binding energy"),
 "Quasiparticle / optical gaps":("quasiparticle gap","optical gap","quasiparticle band gap"),
 "Oscillator strength":("oscillator strength","transition dipole")}
EXP_ACTIONS=("we measure","we measured","we observe","we observed","we use","we employ","we perform","we report","experimentally","experimental results","measurements reveal","spectroscopy reveals")
EXP_ACTIONS+=("we demonstrate experimentally","we fabricate and characterize","we fabricated","we characterize","we measured coherent","we acquire","we record")
COMP_ACTIONS=("we calculate","we calculated","we compute","we computed","we perform","we employ","we use","using","calculations show","simulations show","first-principles calculations","ab initio calculations","theoretical calculations","numerically investigate","we simulate","we model","we develop a theoretical framework","we present a theoretical framework","first-principles approach","first principles approach","numerical simulations","theoretical model")
MATERIALS={
 "MoS2":("mos2","molybdenum disulfide"),"WS2":("ws2","tungsten disulfide"),
 "MoSe2":("mose2","molybdenum diselenide"),"WSe2":("wse2","tungsten diselenide"),
 "hBN":("hbn","hexagonal boron nitride"),"black phosphorus":("black phosphorus","phosphorene"),
 "perovskites":("perovskite",),"transition-metal dichalcogenides":("transition metal dichalcogenide","transition-metal dichalcogenide","tmd monolayer","tmds"),
 "2D materials":("two-dimensional material","two dimensional material","2d material","van der waals heterostructure"),
 "quantum dots":("quantum dot",),"COFs":("covalent organic framework","covalent-organic framework","cof"),
 "MOFs":("metal-organic framework","metal organic framework","mof"),
 "organic semiconductors":("organic semiconductor","molecular crystal"),
}
MATERIAL_FAMILIES={
 "TMDs / 2D chalcogenides":("transition metal dichalcogenide","transition-metal dichalcogenide","tmds","mos2","ws2","mose2","wse2","molybdenum disulfide","tungsten disulfide","molybdenum diselenide","tungsten diselenide"),
 "Other 2D / van der Waals materials":("two-dimensional material","two dimensional material","2d material","van der waals","heterobilayer","monolayer","hbn","hexagonal boron nitride","black phosphorus","phosphorene"),
 "Perovskites / halide semiconductors":("perovskite","halide semiconductor","lead halide"),
 "Organic / molecular materials":("organic semiconductor","molecular crystal","molecular aggregate","j-aggregate"),
 "Porous frameworks (COFs / MOFs)":("covalent organic framework","covalent-organic framework","metal-organic framework","metal organic framework"," cof "," mof "),
 "Quantum-confined structures":("quantum dot","quantum well","nanocrystal"),
 "Biological / light-harvesting systems":("photosynthetic","photosynthesis","light-harvesting complex","chromophore"),
}
EXCITON_PROPERTIES={
 "Binding energy":("exciton binding energy","excitonic binding energy","binding energies"),
 "Lifetime / relaxation":("exciton lifetime","excitonic lifetime","radiative lifetime","nonradiative lifetime","relaxation dynamics","decay time"),
 "Linewidth / dephasing":("exciton linewidth","excitonic linewidth","line width","linewidth","dephasing","homogeneous broadening"),
 "g-factor / Zeeman splitting":("exciton g-factor","exciton g factor","g-factor","g factor","zeeman splitting","zeeman effect"),
 "Fine structure / bright-dark splitting":("fine-structure splitting","fine structure splitting","bright-dark","bright dark","dark exciton","bright exciton"),
 "Transport / diffusion":("exciton transport","exciton diffusion","diffusion length","energy transfer","exciton migration"),
 "Coherence":("exciton coherence","excitonic coherence","coherent exciton","coherence time"),
 "Valley / spin physics":("valley polarization","valley coherence","valley exciton","spin-valley","spin polarized","spin-polarised"),
 "Oscillator strength / optical activity":("oscillator strength","transition dipole","optical activity","radiative rate"),
 "Exciton-phonon coupling":("exciton-phonon","exciton phonon","electron-phonon coupling","phonon-assisted"),
 "Many-exciton interactions":("exciton-exciton","exciton exciton","biexciton","exciton annihilation","many-exciton"),
 "Strain response":("strain dependence","strained system","under strain","strain engineering","biaxial strain","uniaxial strain"),
 "Defects / trapping":("defect-bound exciton","defect bound exciton","exciton trapping","self-trapped exciton","self trapped exciton","trap state"),
 "Light-matter strong coupling":("exciton-polariton","exciton polariton","strong light-matter coupling","strong light–matter coupling","rabi splitting"),
}
APPLICATIONS={
 "Exciton polaritons":("exciton-polariton","exciton polariton","excitonic polariton"),
 "Light–matter coupling":("light-matter coupling","light–matter coupling","strong coupling","optical cavity","microcavity"),
 "Photosynthesis":("photosynthesis","photosynthetic","light-harvesting complex"),
 "Photovoltaics":("photovoltaic","solar cell","organic solar"),
 "Photocatalysis":("photocatalysis","photocatalytic","photoelectrochemical"),
}
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

def hit_terms(text, groups):
    return {label:[term for term in terms if term in text] for label,terms in groups.items() if any(term in text for term in terms)}

def action_hits(text, actions):
    return [action for action in actions if action in text]

def analyze(title, abstract):
    text=clean(f"{title}. {abstract}").lower()
    exp,exp_words=matches(text,EXPERIMENTAL); comp,comp_words=matches(text,COMPUTATIONAL)
    exp_terms=tuple(x for terms in EXPERIMENTAL.values() for x in terms)
    comp_terms=tuple(x for terms in COMPUTATIONAL.values() for x in terms)
    exp_ok=bool(exp) and near_action(text,exp_terms,EXP_ACTIONS)
    comp_ok=bool(comp) and near_action(text,comp_terms,COMP_ACTIONS)
    exp_ok |= bool(exp) and any(x in text for x in ("measurements show","spectra show","measured at"))
    comp_ok |= bool(comp) and any(x in text for x in ("calculated band","computed exciton","predicted binding"))
    # Strong theory signals are substantive even in review-style wording such as
    # “we highlight our GW-BSE calculations”. A lone DFT mention remains insufficient.
    strong_theory={"GW","Bethe–Salpeter equation","TDDFT"}
    comp_ok |= bool(strong_theory.intersection(comp))
    comp_ok |= bool(comp) and any(x in text for x in (
        "our calculations","our theoretical","theoretical framework",
        "theoretical insights","many-body calculations","we predict",
    ))
    # Explicit original-work language can classify theory even when the named
    # technique is domain-specific and not yet in the controlled method list.
    comp_ok |= any(x in text for x in ("numerically investigate","we simulate","we model","we develop a theoretical framework","we present a theoretical framework","first-principles approach","first principles approach"))
    exp_ok |= any(x in text for x in ("we measured","we demonstrate experimentally","we fabricate and characterize","we fabricated and measured","we record the spectra"))
    # Experimental methods mentioned only as prior literature do not make a paper
    # combined. Original measurement language is still required for exp_ok.
    if not exp_ok and exp and not comp:
        exp_ok=any(x in text for x in (
            "we report","we demonstrate","we investigate experimentally",
            "measured spectra","experimental study",
        ))
    kind="Theory + Experiment" if exp_ok and comp_ok else "Computational" if comp_ok else "Experimental" if exp_ok else "Unclassified"
    materials=[name for name,aliases in MATERIALS.items() if any(x in text for x in aliases)]
    material_families=[name for name,aliases in MATERIAL_FAMILIES.items() if any(x in f" {text} " for x in aliases)]
    properties=[name for name,aliases in EXCITON_PROPERTIES.items() if any(x in text for x in aliases)]
    applications=[name for name,aliases in APPLICATIONS.items() if any(x in text for x in aliases)]
    review_signals=("review article","this review","we review","we survey","perspective article","critical assessment","comprehensive review","status and outlook")
    method_signals=("new method","novel method","we develop a method","software package","code implementation","computational framework","workflow")
    benchmark_signals=("benchmark","dataset","database","high-throughput screening","high throughput screening")
    paper_nature="Review / perspective" if any(x in text for x in review_signals) else "Methods / software" if any(x in text for x in method_signals) else "Dataset / benchmark" if any(x in text for x in benchmark_signals) else "Original research"
    has_exciton=bool(re.search(r"\bexciton(?:s|ic|ically)?\b|exciton[-–]polariton",text))
    has_generic_polariton="polariton" in text
    relevance="Core exciton paper" if has_exciton else "Exciton-adjacent" if has_generic_polariton and any(x in text for x in ("light-matter","light–matter","semiconductor","optical","cavity")) else "Uncertain"
    classification_evidence={
      "experimental_actions":action_hits(text,EXP_ACTIONS),
      "computational_actions":action_hits(text,COMP_ACTIONS),
      "experimental_methods":hit_terms(text,EXPERIMENTAL),
      "computational_methods":hit_terms(text,COMPUTATIONAL),
      "materials":hit_terms(text,{**MATERIALS,**MATERIAL_FAMILIES}),
      "properties":hit_terms(text,EXCITON_PROPERTIES),
      "relevance":["exciton/excitonic stated in title or abstract"] if has_exciton else (["polariton context without an explicit exciton term"] if has_generic_polariton else []),
    }
    return {"study_type":kind,"relevance":relevance,"paper_nature":paper_nature,"materials":list(dict.fromkeys(materials)),"material_families":material_families,"exciton_properties":properties,"applications":applications,"methods":list(dict.fromkeys(exp+comp)),"matched_keywords":sorted(set(exp_words+comp_words+[x for x in ("exciton","excitonic","polariton") if x in text])),"classification_evidence":classification_evidence,"evidence":{"experimental":exp_ok,"computational":comp_ok}}

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

def fetch_since(since="2026-01-01", max_results=2000, page_size=200, until=None):
    cats=" OR ".join(f"cat:{x}" for x in CATEGORIES)
    start_stamp=date.fromisoformat(since).strftime("%Y%m%d0000")
    end_stamp=(date.fromisoformat(until).strftime("%Y%m%d2359") if until\n               else datetime.now(timezone.utc).strftime("%Y%m%d%H%M"))
    concepts='ti:exciton OR abs:exciton OR ti:excitonic OR abs:excitonic OR ti:"exciton polariton" OR abs:"exciton polariton"'
    query=f"({cats}) AND ({concepts}) AND submittedDate:[{start_stamp} TO {end_stamp}]"
    papers=[]
    for start in range(0,max_results,page_size):
        params=urllib.parse.urlencode({"search_query":query,"start":start,"max_results":min(page_size,max_results-start),"sortBy":"submittedDate","sortOrder":"descending"})
        request=urllib.request.Request(f"{API_URL}?{params}",headers={"User-Agent":"ExcitonResearchScanner/0.2 (arXiv metadata research scanner)"})
        with urllib.request.urlopen(request,timeout=60) as response:
            page=parse_feed(response.read())
        papers.extend(page)
        if len(page)<page_size:
            break
        time.sleep(3.1)
    return papers

def merge_archive(path,incoming,fetched_count=None,since=None):
    archive=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version":2,"papers":[],"scans":[]}
    existing={x["arxiv_id"]:x for x in archive.get("papers",[])}; new=updated=0
    for paper in incoming:
        old=existing.get(paper["arxiv_id"])
        if old is None: paper["versions_seen"]=[paper["version"]]; existing[paper["arxiv_id"]]=paper; new+=1
        else:
            versions=list(dict.fromkeys(old.get("versions_seen",[old.get("version","v1")])+[paper["version"]]))
            paper["versions_seen"]=versions
            # Re-run and persist current classification rules on every scan, even
            # when arXiv metadata itself has not changed.
            if paper["updated"]>old.get("updated",""): updated+=1
            existing[paper["arxiv_id"]]=paper
    scanned_at=datetime.now(timezone.utc).isoformat()
    scan={"scanned_at":scanned_at,"since":since,"fetched":fetched_count if fetched_count is not None else len(incoming),"classified":len(incoming),"new":new,"updated":updated,"total":len(existing)}
    scans=archive.get("scans",[])
    scans.append(scan)
    archive.update({"schema_version":2,"last_scan":scanned_at,"papers":sorted(existing.values(),key=lambda x:x.get("updated",""),reverse=True),"scans":scans[-500:],"counts":{"total":len(existing),"new_this_scan":new,"updated_this_scan":updated}})
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(archive,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return archive

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,default=Path("data/papers.json")); parser.add_argument("--since",default="2026-01-01"); parser.add_argument("--until"); parser.add_argument("--max-results",type=int,default=2000); parser.add_argument("--page-size",type=int,default=200); args=parser.parse_args()
    if args.until and date.fromisoformat(args.until) < date.fromisoformat(args.since):
        parser.error("--until must be on or after --since")
    for attempt in range(3):
        try:
            fetched=fetch_since(args.since,args.max_results,args.page_size,args.until)
            # Preserve every arXiv record returned by the scoped exciton query.
            # Classification is descriptive metadata, never an ingestion gate.
            papers=fetched
            result=merge_archive(args.output,papers,len(fetched),args.since)
            print(json.dumps({"scan":result["scans"][-1],"counts":result["counts"]})); return
        except Exception:
            if attempt==2: raise
            time.sleep(3*(attempt+1))
if __name__=="__main__": main()
