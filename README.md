# Exciton Research Scanner

A version-aware Streamlit research dashboard that queries the official arXiv API for recent exciton papers and classifies abstract-level evidence as experimental, computational, or combined theory and experiment.

## First-version scope

- Official arXiv Atom API metadata and abstracts only.
- Searches materials science, mesoscopic physics, optics, computational physics, applied physics and chemical physics.
- Evidence-aware rules do not treat a casual DFT citation as a computational study.
- Full-text, material, method and date filters.
- Base arXiv ID deduplication with tracked v1/v2/v3 updates.
- Durable, Git-tracked `data/papers.json` archive.
- Twice-daily GitHub Actions scan plus manual dispatch.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python arxiv_scanner.py
streamlit run app.py
```

## Test

```bash
pytest -q
```

## Deploy on Streamlit Community Cloud

Select `purushothaman-98/building-up`, branch `master`, and entrypoint `app.py`. No secrets are required. Run the “Scan arXiv for exciton papers” workflow manually once to seed the archive.

## Classification

Method keywords are recorded whenever present, but a study type is assigned only when a method occurs near action or result language such as “we measured,” “using GW-BSE,” or “calculations show.” A paper with experimental evidence and only an introductory DFT reference therefore remains experimental.
