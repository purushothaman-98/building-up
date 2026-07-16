from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://models.github.ai/inference/chat/completions"
PROMPT_VERSION = "4.0"
# A prompt-version fingerprint ensures stale classifications are re-queued safely.
DEFAULT_MODEL = "openai/gpt-4o-mini"
RELEVANCE = {"Core exciton paper", "Exciton-adjacent", "Uncertain", "Not relevant"}
RESEARCH_TYPES = {"Experimental", "Computational", "Theory + Experiment", "Unclassified"}
PAPER_NATURES = {"Original research", "Review / perspective", "Methods / software", "Dataset / benchmark", "Uncertain"}
MATERIAL_FAMILIES = {
    "TMDs", "Perovskites", "Graphene / carbon materials", "Other 2D materials",
    "Organic / molecular materials", "COFs / MOFs / porous materials",
    "Quantum dots / nanocrystals", "Conventional semiconductors", "Other materials",
}
EXPERIMENTAL_METHODS = {
    "Photoluminescence", "Absorption / reflectance", "Pump–probe / transient absorption",
    "Time-resolved spectroscopy", "Magneto-optical spectroscopy", "Polarization-resolved spectroscopy",
    "Raman spectroscopy", "Photoemission spectroscopy", "Electrical / photocurrent measurements",
    "Optical microscopy", "Cavity / polariton spectroscopy", "Other experimental method",
}
COMPUTATIONAL_METHODS = {
    "DFT", "DFT + GW", "DFT + GW/BSE", "BSE / exciton equation", "TDDFT",
    "Model / analytical theory", "Semiconductor Bloch / density-matrix theory",
    "Quantum / nonadiabatic dynamics", "Kinetic / rate-equation model",
    "Quantum Monte Carlo / wavefunction method", "Electromagnetic / cavity simulation",
    "Machine learning", "Other computational method",
}
EXCITON_OBSERVABLES = {
    "Exciton energy / optical spectrum", "Binding energy", "Optical / quasiparticle gap",
    "Lifetime / recombination", "Ultrafast dynamics / relaxation", "Linewidth / coherence",
    "Diffusion / transport", "Fine structure / bright-dark states", "g-factor / Zeeman splitting",
    "Valley / spin polarization", "Interlayer / charge-transfer excitons", "Exciton complexes",
    "Exciton-phonon coupling", "Strong coupling / polaritons", "Energy / charge transfer",
    "Many-body exciton physics",
}

SYSTEM_PROMPT = """You are the scientific abstract-screening curator for an Exciton Research Scanner used by researchers in condensed-matter physics, materials science, physical chemistry and optics.

INPUT LIMIT: You receive only a paper title, author list and complete author-written abstract. Judge only what these fields support. Do not invent information, infer a method merely from an author name, or treat missing abstract detail as proof that something was done.

SCIENTIFIC SCOPE
The feed covers excitons as electron-hole quasiparticles and exciton-mediated phenomena, especially:
- 2D materials and heterostructures: TMDs/TMDCs, moire systems, perovskites, hBN, phosphorene, layered semiconductors and related low-dimensional materials;
- organic, molecular and porous materials: COFs, MOFs, polymers, molecular crystals, aggregates and quantum-confined systems;
- original spectroscopy and measurements: photoluminescence, absorption/reflectance, pump-probe, transient absorption, time-resolved, multidimensional/coherent, THz, magneto-optical, photocurrent and related optical measurements;
- original theory/computation: DFT only when used for the reported work, GW, GW-BSE/BSE, TDDFT, many-body or model-Hamiltonian calculations, nonadiabatic/exciton dynamics and quantitative theory-experiment comparison;
- exciton quantities and physics: binding energy, optical/quasiparticle gap, lifetime, relaxation, diffusion/transport, linewidth/dephasing, fine structure, bright/dark states, interlayer/intralayer excitons, trions/biexcitons, g-factors, valley/spin polarization, oscillator strength and radiative/nonradiative processes;
- substantive exciton light-matter coupling: exciton-polaritons, strong/ultrastrong coupling, cavities, plexcitons and polariton condensation;
- exciton roles in photovoltaics, photocatalysis, artificial/natural photosynthesis, charge/energy transfer and exciton dissociation.

STEP 1 — DOCUMENT-LEVEL RELEVANCE
Read the title and full abstract together. A keyword hit is never sufficient.
- Core exciton paper: excitons or an excitonic state/process are a principal object, reported result, calculated quantity, measured signal, controlling mechanism or central application.
- Exciton-adjacent: excitons are scientifically substantive and necessary to understand part of the reported work, but are not the main object.
- Uncertain: the abstract plausibly falls in scope but does not provide enough evidence for a reliable inclusion/exclusion judgment. At title/abstract screening, preserve uncertain records for human review.
- Not relevant: exciton language is incidental/background-only, metaphorical, or does not describe substantive exciton science in the authors' work.
Set include_in_feed=true for Core, Exciton-adjacent and Uncertain; set it false only for Not relevant.

Important exclusions unless an actual excitonic component is substantive: phonon-polaritons, plasmon/surface-plasmon polaritons, magnon/magnetic polaritons, generic cavity modes, ordinary photonics, band-structure-only or ground-state DFT studies, and photovoltaic/photocatalytic/photosynthetic studies that never analyze excitons, electron-hole attraction, exciton transfer/dissociation or an equivalent excitonic mechanism.

STEP 2 — RESEARCH TYPE (AUTHORS' ORIGINAL WORK ONLY)
- Experimental: the authors report original measurements, sample/device fabrication plus characterization, or measured spectra/dynamics. Prior experimental literature and comparison to published data do not count.
- Computational: the authors perform original calculations, simulations, analytical theory or numerical modelling. A casual statement that DFT/GW/BSE was used in earlier work does not count.
- Theory + Experiment: the same paper reports both original experimental measurements and original theoretical/computational analysis. Require separate evidence for both; fitting alone is not automatically a full theoretical study.
- Unclassified: reviews/perspectives without a new study, or insufficient evidence.
Use author-action language such as “we measure”, “we calculate”, “we simulate”, “we fabricate”, “we derive” and the described results. Do not classify from method nouns in introductory sentences.

STEP 3 — PAPER NATURE
- Original research requires a new result or analysis reported by the authors.
- Review / perspective requires explicit synthesis, assessment, survey, outlook or perspective intent. Words such as “landscape”, “overview”, “recent advances” or “we discuss” alone are insufficient when the abstract also reports new results.
- Methods / software requires the method, code or workflow itself to be a primary contribution.
- Dataset / benchmark requires a dataset or systematic benchmark to be a primary contribution.
- Uncertain when the abstract cannot distinguish these reliably.

STEP 4 — SCIENTIFIC EXTRACTION
Extract only entities supported by the title/abstract. Use the canonical labels supplied in the output schema; do not create synonyms or copy arbitrary noun phrases into grouped fields.

MATERIALS AND ONE PRIMARY MATERIAL CLASS
- materials contains specific studied systems as concise normalized names (for example MoS2 -> MoS₂, WSe2/MoSe2 heterobilayer -> WSe₂/MoSe₂ heterobilayer). Do not include abbreviations, techniques, functionals, substrates or generic words such as “monolayer” as materials.
- material_families must contain exactly one broad class chosen for useful filtering. Classify by the active excitonic material, not by substrate, encapsulation, geometry or device architecture.
- MoS₂, WS₂, MoSe₂, WSe₂ and related transition-metal dichalcogenides -> “TMDs”, including their heterobilayers and moiré structures. Do not add separate heterostructure or moiré family labels.
- Lead-halide, hybrid, inorganic, layered/Ruddlesden–Popper and related perovskites -> “Perovskites”.
- Graphene, graphene nanoribbons, carbon nanotubes, fullerenes and related carbon systems -> “Graphene / carbon materials”.
- hBN, black phosphorus/phosphorene, Xenes, MXenes, 2D magnets, layered oxides and non-TMD layered chalcogenides -> “Other 2D materials” when the studied system is genuinely low dimensional.
- Molecular crystals, small molecules, polymers, aggregates and organic semiconductors -> “Organic / molecular materials”; COFs, MOFs and porous frameworks -> “COFs / MOFs / porous materials”.
- III–V/II–VI semiconductors, silicon, bulk crystals and quantum wells -> “Conventional semiconductors”; colloidal or epitaxial dots/nanocrystals -> “Quantum dots / nanocrystals”. Use “Other materials” only when no scientific class above fits.

METHOD GROUPS
- experimental_methods describes broad techniques actually used by the authors. Map PL/micro-PL/PL excitation -> “Photoluminescence”; TRPL/streak-camera PL/fluorescence upconversion -> “Time-resolved spectroscopy”; differential transmission/transient reflectance/transient absorption -> “Pump–probe / transient absorption”; MOKE/Faraday/field-dependent PL -> “Magneto-optical spectroscopy”; ARPES/trARPES/photoemission microscopy -> “Photoemission spectroscopy”.
- Add multiple experimental groups when genuinely performed, but do not turn measured quantities into methods. “Lifetime”, “linewidth”, “binding energy”, “g-factor” and “polarization” are observables. Polarization-resolved PL may receive both the PL group and “Polarization / valley-resolved optical spectroscopy”.
- computational_methods describes the main workflow, not every technical ingredient. Prefer one workflow label; add a second only for a genuinely separate calculation.
- DFT only -> “DFT”. DFT followed by GW quasiparticle corrections but no BSE -> “DFT + GW”. The standard ground-state DFT -> GW -> BSE optical/exciton chain, including phrases such as first-principles GW-BSE, -> “DFT + GW/BSE”. Do not also output DFT, DFT + GW, or BSE separately for that same chain.
- A direct/effective BSE, Wannier or exciton Schrödinger calculation without a reported GW chain -> “BSE / exciton equation”. Gross–Pitaevskii, tight-binding, coupled-oscillator and other reduced Hamiltonians -> “Model / analytical theory”. NAMD, surface hopping, real-time propagation and explicitly simulated exciton dynamics -> “Quantum / nonadiabatic dynamics”.
- Ground-state DFT is supporting electronic-structure work, not by itself an exciton calculation. Include “DFT” only when the authors perform it, and never infer it from PBE/HSE or a prior-work statement.
- Classical cavity simulations (FDTD, transfer matrix, coupled oscillators) count only when used to analyze substantive exciton light-matter coupling.

EXCITON OBSERVABLES / PROPERTIES
- exciton_properties contains canonical physical outputs actually measured, extracted, calculated or quantitatively analyzed—not every phenomenon mentioned in motivation.
- Use broad researcher-facing observables. A fitted decay supports “Lifetime / recombination”; femtosecond formation/cooling/transfer kinetics supports “Ultrafast dynamics / relaxation”; linewidth, dephasing and coherence time -> “Linewidth / coherence”; spatial propagation -> “Diffusion / transport”; magnetic splitting -> “g-factor / Zeeman splitting”; helicity/polarization contrast -> “Valley / spin polarization”; anticrossing/Rabi splitting -> “Strong coupling / polaritons”.
- PL or absorption peak position supports “Exciton energy / optical spectrum”, but does not alone prove “Binding energy”. Binding energy requires an explicit value/extraction or evidence relating an exciton level/Rydberg series to a quasiparticle or continuum gap.

STEP 5 — AUDITABLE EVIDENCE AND CONSISTENCY
Give 2–5 short evidence phrases copied exactly or nearly exactly from the title/abstract. Evidence should cover relevance and, when applicable, separate experimental and computational actions. The reason must state what the paper actually contributes and why that supports the decision, without hype.
Before returning, verify: relevance agrees with include_in_feed; research_type is supported by author actions; extracted methods/properties are supported by evidence; and no output depends on knowledge outside the supplied metadata.

Return only one JSON object matching the supplied schema. No Markdown, commentary or extra keys."""


def fingerprint(paper: dict) -> str:
    payload = {
        "arxiv_id": paper.get("arxiv_id"),
        "version": paper.get("version"),
        "title": paper.get("title"),
        "abstract": paper.get("abstract"),
        "categories": paper.get("categories", []),
        "prompt_version": PROMPT_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def user_prompt(paper: dict) -> str:
    metadata = {
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "abstract": paper.get("abstract"),
    }
    schema = {
        "include_in_feed": "one boolean",
        "relevance": "one string: " + " | ".join(sorted(RELEVANCE)),
        "research_type": "one string: " + " | ".join(sorted(RESEARCH_TYPES)),
        "paper_nature": "one string: " + " | ".join(sorted(PAPER_NATURES)),
        "materials": ["specific materials actually stated or clearly identified"],
        "material_families": ["zero or more canonical material-family labels from the JSON schema"],
        "experimental_methods": ["zero or more canonical experimental-method labels from the JSON schema"],
        "computational_methods": ["zero or more canonical computational-method labels from the JSON schema"],
        "exciton_properties": ["zero or more canonical observable/property labels from the JSON schema"],
        "confidence": "number from 0 to 1",
        "reason": "one concise scientific sentence",
        "evidence": ["two to five short supporting phrases from the metadata"],
    }
    return "Classify this paper.\nOUTPUT SCHEMA:\n" + json.dumps(schema, ensure_ascii=False) + "\nPAPER METADATA:\n" + json.dumps(metadata, ensure_ascii=False)


OUTPUT_SCHEMA = {
    "name": "exciton_paper_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "include_in_feed": {"type": "boolean"},
            "relevance": {"type": "string", "enum": sorted(RELEVANCE)},
            "research_type": {"type": "string", "enum": sorted(RESEARCH_TYPES)},
            "paper_nature": {"type": "string", "enum": sorted(PAPER_NATURES)},
            "materials": {"type": "array", "items": {"type": "string"}},
            "material_families": {"type": "array", "minItems": 1, "maxItems": 1, "items": {"type": "string", "enum": sorted(MATERIAL_FAMILIES)}},
            "experimental_methods": {"type": "array", "items": {"type": "string", "enum": sorted(EXPERIMENTAL_METHODS)}},
            "computational_methods": {"type": "array", "items": {"type": "string", "enum": sorted(COMPUTATIONAL_METHODS)}},
            "exciton_properties": {"type": "array", "items": {"type": "string", "enum": sorted(EXCITON_OBSERVABLES)}},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
        "required": [
            "include_in_feed", "relevance", "research_type", "paper_nature",
            "materials", "material_families", "experimental_methods",
            "computational_methods", "exciton_properties", "confidence", "reason", "evidence",
        ],
    },
}


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def normalize_result(result: dict) -> dict:
    """Normalize common model deviations before applying the strict validator."""
    result = dict(result)
    for field in ("relevance", "research_type", "paper_nature"):
        value = result.get(field)
        if isinstance(value, list) and value:
            result[field] = value[0]
    value = result.get("include_in_feed")
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "include", "included"}:
            result["include_in_feed"] = True
        elif lowered in {"false", "no", "exclude", "excluded"}:
            result["include_in_feed"] = False
    for field in ("materials", "material_families", "experimental_methods", "computational_methods", "exciton_properties", "evidence"):
        if isinstance(result.get(field), str):
            result[field] = [result[field]] if result[field].strip() else []
    return result


def validate(result: dict) -> dict:
    result = normalize_result(result)
    required = {"include_in_feed", "relevance", "research_type", "paper_nature", "materials", "material_families", "experimental_methods", "computational_methods", "exciton_properties", "confidence", "reason", "evidence"}
    missing = required.difference(result)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    if not isinstance(result["include_in_feed"], bool):
        raise ValueError("include_in_feed must be boolean")
    if result["relevance"] not in RELEVANCE or result["research_type"] not in RESEARCH_TYPES or result["paper_nature"] not in PAPER_NATURES:
        raise ValueError("Invalid classification enum")
    expected_inclusion = result["relevance"] != "Not relevant"
    if result["include_in_feed"] is not expected_inclusion:
        raise ValueError("include_in_feed contradicts relevance")
    for field in ("materials", "material_families", "experimental_methods", "computational_methods", "exciton_properties", "evidence"):
        if not isinstance(result[field], list) or not all(isinstance(x, str) for x in result[field]):
            raise ValueError(f"{field} must be a string list")
    controlled_fields = {
        "material_families": MATERIAL_FAMILIES,
        "experimental_methods": EXPERIMENTAL_METHODS,
        "computational_methods": COMPUTATIONAL_METHODS,
        "exciton_properties": EXCITON_OBSERVABLES,
    }
    for field, vocabulary in controlled_fields.items():
        invalid = set(result[field]).difference(vocabulary)
        if invalid:
            raise ValueError(f"Non-canonical {field}: {sorted(invalid)}")
    if len(result["material_families"]) != 1:
        raise ValueError("material_families must contain exactly one broad class")
    result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
    result["reason"] = str(result["reason"]).strip()
    return result


def call_model(paper: dict, token: str, model: str, attempts: int = 3) -> dict:
    body = json.dumps({
        "model": model,
        "temperature": 0.0,
        "max_tokens": 900,
        "response_format": {"type": "json_schema", "json_schema": OUTPUT_SCHEMA},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(paper)},
        ],
    }).encode()
    for attempt in range(attempts):
        request = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ExcitonResearchScanner/ai-classifier",
        })
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.load(response)
            return validate(parse_json_response(payload["choices"][0]["message"]["content"]))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else (15, 45, 120)[attempt]
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
            if attempt == attempts - 1:
                raise
            delay = (15, 45, 120)[attempt]
        time.sleep(delay + random.random() * 2)
    raise RuntimeError("Model request exhausted retries")


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def pending_papers(papers: list[dict], records: dict, overrides: dict) -> list[dict]:
    pending = []
    for paper in papers:
        paper_id = paper["arxiv_id"]
        if paper_id in overrides:
            continue
        record = records.get(paper_id)
        if not record or record.get("fingerprint") != fingerprint(paper):
            pending.append(paper)
    return pending


def latest_window(papers: list[dict], days: int = 7) -> tuple[list[dict], date | None, date | None]:
    dated = []
    for paper in papers:
        try:
            dated.append((date.fromisoformat(paper.get("submitted", "")[:10]), paper))
        except ValueError:
            continue
    if not dated:
        return [], None, None
    end = max(item[0] for item in dated)
    start = end - timedelta(days=max(1, days) - 1)
    return [paper for submitted, paper in dated if start <= submitted <= end], start, end


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, default=Path("data/papers.json"))
    parser.add_argument("--output", type=Path, default=Path("data/ai_classifications.json"))
    parser.add_argument("--overrides", type=Path, default=Path("data/ai_overrides.json"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--delay", type=float, default=7.0)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--model", default=os.getenv("AI_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    archive = load_json(args.papers, {"papers": []})
    store = load_json(args.output, {"schema_version": 1, "records": {}, "runs": []})
    overrides = load_json(args.overrides, {})
    records = store.setdefault("records", {})
    eligible, window_start, window_end = latest_window(archive.get("papers", []), args.days)
    queue = pending_papers(eligible, records, overrides)
    selected = queue[: max(0, args.limit)]
    succeeded = failed = 0

    for index, paper in enumerate(selected):
        paper_id = paper["arxiv_id"]
        try:
            decision = call_model(paper, token, args.model)
            records[paper_id] = {
                **decision,
                "arxiv_id": paper_id,
                "version": paper.get("version"),
                "fingerprint": fingerprint(paper),
                "model": args.model,
                "prompt_version": PROMPT_VERSION,
                "classified_at": datetime.now(timezone.utc).isoformat(),
            }
            succeeded += 1
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as exc:
            failed += 1
            print(json.dumps({"arxiv_id": paper_id, "error": str(exc)}))
        if index < len(selected) - 1:
            time.sleep(args.delay)

    run = {
        "run_at": datetime.now(timezone.utc).isoformat(), "model": args.model,
        "prompt_version": PROMPT_VERSION, "attempted": len(selected),
        "succeeded": succeeded, "failed": failed,
        "remaining": max(0, len(queue) - succeeded), "total_records": len(records),
        "eligible": len(eligible),
        "window_start": window_start.isoformat() if window_start else None,
        "window_end": window_end.isoformat() if window_end else None,
    }
    store.setdefault("runs", []).append(run)
    store["runs"] = store["runs"][-200:]
    store["last_run"] = run["run_at"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run))
    if failed and not succeeded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
