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
PROMPT_VERSION = "3.0"
DEFAULT_MODEL = "openai/gpt-4o-mini"
RELEVANCE = {"Core exciton paper", "Exciton-adjacent", "Uncertain", "Not relevant"}
RESEARCH_TYPES = {"Experimental", "Computational", "Theory + Experiment", "Unclassified"}
PAPER_NATURES = {"Original research", "Review / perspective", "Methods / software", "Dataset / benchmark", "Uncertain"}
MATERIAL_FAMILIES = {
    "TMDs / 2D chalcogenides", "Other layered chalcogenides", "2D elemental materials / Xenes",
    "hBN / 2D wide-gap insulators", "2D heterostructures", "Moiré / twisted systems",
    "2D magnets", "2D oxides / nitrides", "MXenes", "2D perovskites",
    "3D / bulk perovskites", "Organic semiconductors / molecular crystals",
    "COFs / MOFs / porous frameworks", "Polymers / molecular aggregates",
    "Quantum dots / nanocrystals", "Carbon nanotubes / carbon nanostructures",
    "Conventional semiconductors / quantum wells", "Other low-dimensional materials",
}
EXPERIMENTAL_METHODS = {
    "Steady-state photoluminescence", "Time-resolved photoluminescence",
    "Absorption / reflectance / transmission", "Photoluminescence excitation / two-photon spectroscopy",
    "Ultrafast pump–probe / transient absorption", "Coherent multidimensional / four-wave mixing",
    "Raman / resonant Raman", "THz / microwave spectroscopy", "Magneto-optical spectroscopy",
    "Polarization / valley-resolved optical spectroscopy", "Photoemission / momentum microscopy",
    "Scanning probe / tunneling spectroscopy", "Photocurrent / electrical transport",
    "Near-field / single-particle optical microscopy", "Cathodoluminescence / EELS",
    "Cavity / angle-resolved polariton spectroscopy", "Other experimental exciton probe",
}
COMPUTATIONAL_METHODS = {
    "Ground-state DFT / electronic structure", "GW quasiparticle calculations",
    "Bethe–Salpeter equation", "TDDFT / real-time TDDFT",
    "Semiconductor Bloch / density-matrix equations", "Effective-mass / Wannier / Rytova–Keldysh model",
    "Tight-binding / model Hamiltonian", "Quantum Monte Carlo",
    "Configuration interaction / wavefunction method", "Nonadiabatic molecular dynamics",
    "Real-time GW/BSE / nonequilibrium Green functions", "Exciton-phonon / electron-phonon calculation",
    "Classical electrodynamics / transfer matrix / FDTD", "Kinetic / rate-equation / diffusion model",
    "Machine learning / surrogate model", "Other computational exciton method",
}
EXCITON_OBSERVABLES = {
    "Exciton resonance / transition energy", "Binding energy / Rydberg series",
    "Optical / quasiparticle gap", "Population lifetime / decay", "Coherence / dephasing time",
    "Homogeneous linewidth", "Inhomogeneous broadening / spectral disorder",
    "Diffusion / transport length", "Formation / thermalization / relaxation",
    "Energy transfer", "Charge transfer / exciton dissociation", "Radiative / nonradiative recombination",
    "Oscillator strength / absorption strength", "Bright-dark splitting / fine structure",
    "g-factor / Zeeman splitting", "Valley / spin polarization or coherence",
    "Exciton-phonon coupling", "Exciton-exciton interaction / annihilation",
    "Trion / biexciton / charged complexes", "Interlayer / intralayer character",
    "Wavefunction / radius / spatial extent", "Momentum dispersion / exciton band structure",
    "Rabi splitting / strong-coupling strength", "Condensation / many-body exciton phase",
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

MATERIALS AND MATERIAL FAMILIES
- materials contains specific studied systems as concise normalized names (for example MoS2 -> MoS₂, WSe2/MoSe2 heterobilayer -> WSe₂/MoSe₂ heterobilayer). Do not include abbreviations, techniques, functionals, substrates or generic words such as “monolayer” as materials.
- material_families is multi-label and hierarchical. A twisted WSe₂/MoSe₂ heterobilayer should receive “TMDs / 2D chalcogenides”, “2D heterostructures”, and “Moiré / twisted systems” when each is supported. A specific compound remains in materials.
- Map graphene, phosphorene/black phosphorus, silicene, germanene, borophene and related elemental sheets to “2D elemental materials / Xenes”. Map MoS₂, WS₂, MoSe₂, WSe₂ and related MX₂ semiconductors to “TMDs / 2D chalcogenides”. Use “Other layered chalcogenides” for group-IV/III-VI chalcogenides and related layered chalcogenides that are not TMDs.
- Keep 2D and bulk perovskites distinct. Group covalent and metal-organic frameworks together only under “COFs / MOFs / porous frameworks”. MXenes are transition-metal carbides/nitrides/carbonitrides, not generic TMDs.

METHOD GROUPS
- experimental_methods describes instruments/protocols actually used by the authors. Map synonyms to one canonical group: PL/micro-PL -> “Steady-state photoluminescence”; TRPL/streak-camera PL -> “Time-resolved photoluminescence”; differential transmission/transient reflectance/transient absorption -> “Ultrafast pump–probe / transient absorption” when time resolved; MOKE/Faraday/field-dependent PL -> “Magneto-optical spectroscopy”; trARPES/photoemission electron microscopy -> “Photoemission / momentum microscopy”.
- Add multiple experimental groups when genuinely performed, but do not turn measured quantities into methods. “Lifetime”, “linewidth”, “binding energy”, “g-factor” and “polarization” are observables. Polarization-resolved PL may receive both the PL group and “Polarization / valley-resolved optical spectroscopy”.
- computational_methods describes calculations actually performed by the authors. Map G0W0/evGW/scGW to “GW quasiparticle calculations”; BSE/GW-BSE to “Bethe–Salpeter equation” plus GW only when GW is actually performed; real-time BSE/NEGF to the corresponding nonequilibrium group; NAMD/surface hopping to “Nonadiabatic molecular dynamics”.
- Ground-state DFT is supporting electronic-structure work, not by itself an exciton calculation. Include “Ground-state DFT / electronic structure” only when the authors perform it, and never infer it from a named functional such as PBE/HSE alone in background text.
- Classical cavity simulations (FDTD, transfer matrix, coupled oscillators) count only when used to analyze substantive exciton light-matter coupling.

EXCITON OBSERVABLES / PROPERTIES
- exciton_properties contains canonical physical outputs actually measured, extracted, calculated or quantitatively analyzed—not every phenomenon mentioned in motivation.
- Keep population lifetime distinct from coherence/dephasing; homogeneous linewidth distinct from inhomogeneous broadening; energy transfer distinct from charge transfer/dissociation; binding energy distinct from optical/quasiparticle gap.
- A fitted decay constant supports “Population lifetime / decay”; spatially resolved propagation supports “Diffusion / transport length”; magnetic-field splitting supports “g-factor / Zeeman splitting”; polarization/helicity contrast supports “Valley / spin polarization or coherence”; anticrossing supports “Rabi splitting / strong-coupling strength”.
- PL or absorption peak position supports “Exciton resonance / transition energy”, but does not alone prove binding energy. Binding energy requires an explicit value/extraction or evidence relating an exciton level/Rydberg series to a quasiparticle or continuum gap.

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
            "material_families": {"type": "array", "items": {"type": "string", "enum": sorted(MATERIAL_FAMILIES)}},
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
