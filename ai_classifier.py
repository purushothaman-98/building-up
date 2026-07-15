from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://models.github.ai/inference/chat/completions"
PROMPT_VERSION = "1.0"
DEFAULT_MODEL = "openai/gpt-4o-mini"
RELEVANCE = {"Core exciton paper", "Exciton-adjacent", "Not relevant"}
RESEARCH_TYPES = {"Experimental", "Computational", "Theory + Experiment", "Unclassified"}
PAPER_NATURES = {"Original research", "Review / perspective", "Methods / software", "Dataset / benchmark", "Uncertain"}

SYSTEM_PROMPT = """You are a careful condensed-matter and optical-materials literature curator.
Read the complete metadata supplied for one arXiv paper. Make a document-level scientific judgment; never decide from a lone keyword.

Include a paper in the final Exciton Research Scanner feed when excitons are a substantive subject, object of measurement, theoretical quantity, mechanism, quasiparticle, or central application. This includes experimental exciton spectroscopy/dynamics, DFT/GW/BSE/TDDFT exciton calculations, exciton-polaritons, excitonic energy transfer, excitons in 2D materials, organic/porous frameworks, photovoltaics, photocatalysis and photosynthesis.

Exclude papers where exciton/excitonic appears only casually, or where polariton means only phonon-polariton, plasmon-polariton or magnetic-polariton without substantive exciton physics. Do not exclude review papers when they are genuinely about excitons.

Classify research_type from the authors' own work. Discussion of prior experiments does not make a theory paper experimental. A paper is Theory + Experiment only when it reports both original measurements and original calculations/models. Read the full abstract before deciding.

Return only one valid JSON object with exactly the requested fields. Evidence must be short phrases copied or closely extracted from the supplied metadata, not invented claims."""


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
        "arxiv_id": paper.get("arxiv_id"),
        "version": paper.get("version"),
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "abstract": paper.get("abstract"),
        "submitted": paper.get("submitted"),
        "updated": paper.get("updated"),
        "categories": paper.get("categories", []),
    }
    schema = {
        "include_in_feed": "boolean",
        "relevance": sorted(RELEVANCE),
        "research_type": sorted(RESEARCH_TYPES),
        "paper_nature": sorted(PAPER_NATURES),
        "materials": ["specific materials actually stated or clearly identified"],
        "material_families": ["broad material families"],
        "experimental_methods": ["original experimental methods performed by the authors"],
        "computational_methods": ["original theoretical/computational methods performed by the authors"],
        "exciton_properties": ["exciton properties substantively studied"],
        "confidence": "number from 0 to 1",
        "reason": "one concise scientific sentence",
        "evidence": ["two to five short supporting phrases from the metadata"],
    }
    return "Classify this paper.\nOUTPUT SCHEMA:\n" + json.dumps(schema, ensure_ascii=False) + "\nPAPER METADATA:\n" + json.dumps(metadata, ensure_ascii=False)


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def validate(result: dict) -> dict:
    required = {"include_in_feed", "relevance", "research_type", "paper_nature", "materials", "material_families", "experimental_methods", "computational_methods", "exciton_properties", "confidence", "reason", "evidence"}
    missing = required.difference(result)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    if not isinstance(result["include_in_feed"], bool):
        raise ValueError("include_in_feed must be boolean")
    if result["relevance"] not in RELEVANCE or result["research_type"] not in RESEARCH_TYPES or result["paper_nature"] not in PAPER_NATURES:
        raise ValueError("Invalid classification enum")
    for field in ("materials", "material_families", "experimental_methods", "computational_methods", "exciton_properties", "evidence"):
        if not isinstance(result[field], list) or not all(isinstance(x, str) for x in result[field]):
            raise ValueError(f"{field} must be a string list")
    result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
    result["reason"] = str(result["reason"]).strip()
    return result


def call_model(paper: dict, token: str, model: str, attempts: int = 3) -> dict:
    body = json.dumps({
        "model": model,
        "temperature": 0.0,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, default=Path("data/papers.json"))
    parser.add_argument("--output", type=Path, default=Path("data/ai_classifications.json"))
    parser.add_argument("--overrides", type=Path, default=Path("data/ai_overrides.json"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--delay", type=float, default=7.0)
    parser.add_argument("--model", default=os.getenv("AI_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    archive = load_json(args.papers, {"papers": []})
    store = load_json(args.output, {"schema_version": 1, "records": {}, "runs": []})
    overrides = load_json(args.overrides, {})
    records = store.setdefault("records", {})
    queue = pending_papers(archive.get("papers", []), records, overrides)
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
