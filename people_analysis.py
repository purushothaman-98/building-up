from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations


def mapped_papers(papers: list[dict]) -> list[dict]:
    """Return AI-approved papers when decisions exist, otherwise the full archive."""
    reviewed = [p for p in papers if p.get("ai_decision")]
    if not reviewed:
        return papers
    return [p for p in reviewed if (p.get("ai_decision") or {}).get("include_in_feed") is True]


def build_people_analysis(papers: list[dict]) -> dict:
    author_papers: dict[str, list[dict]] = defaultdict(list)
    coauthors: Counter[tuple[str, str]] = Counter()
    years: Counter[str] = Counter()

    for paper in papers:
        authors = list(dict.fromkeys(a.strip() for a in paper.get("authors", []) if a.strip()))
        year = (paper.get("submitted") or "Unknown")[:4]
        years[year] += 1
        for author in authors:
            author_papers[author].append(paper)
        for left, right in combinations(sorted(authors), 2):
            coauthors[(left, right)] += 1

    author_rows = []
    for author, authored in author_papers.items():
        active_years = sorted({(p.get("submitted") or "")[:4] for p in authored if p.get("submitted")})
        materials = Counter(
            item for paper in authored
            for item in (paper.get("material_families", []) or paper.get("materials", []))
        )
        methods = Counter(item for paper in authored for item in paper.get("methods", []))
        author_rows.append({
            "author": author,
            "papers": len(authored),
            "first_year": active_years[0] if active_years else "—",
            "last_year": active_years[-1] if active_years else "—",
            "materials": [name for name, _ in materials.most_common(3)],
            "methods": [name for name, _ in methods.most_common(3)],
        })

    author_rows.sort(key=lambda row: (-row["papers"], row["author"]))
    connection_rows = [
        {"author_a": pair[0], "author_b": pair[1], "shared_papers": count}
        for pair, count in coauthors.most_common()
    ]
    return {
        "authors": author_rows,
        "author_papers": dict(author_papers),
        "connections": connection_rows,
        "years": dict(sorted(years.items())),
    }


def build_institution_analysis(papers: list[dict], registry: dict) -> dict:
    authors = registry.get("authors", {})
    institutions = registry.get("institutions", {})
    author_names = {author for paper in papers for author in paper.get("authors", [])}
    mapped_authors = author_names.intersection(authors)
    activity = Counter()
    institution_papers: dict[str, set[str]] = defaultdict(set)
    years: dict[str, set[str]] = defaultdict(set)
    links: Counter[tuple[str, str]] = Counter()

    for paper in papers:
        paper_institutions = set()
        paper_id = paper.get("arxiv_id") or paper.get("title") or str(id(paper))
        year = (paper.get("submitted") or "")[:4]
        for author in paper.get("authors", []):
            institution_id = authors.get(author, {}).get("institution_id")
            if institution_id in institutions:
                institution_papers[institution_id].add(paper_id)
                if year:
                    years[institution_id].add(year)
                paper_institutions.add(institution_id)
        for institution_id in paper_institutions:
            activity[institution_id] += 1
        for left, right in combinations(sorted(paper_institutions), 2):
            links[(left, right)] += 1

    markers = []
    for institution_id, count in activity.items():
        institution = institutions[institution_id]
        institution_authors = sorted(
            author for author in mapped_authors
            if authors[author].get("institution_id") == institution_id
        )
        author_records = [authors[author] for author in institution_authors]
        markers.append({
            "id": institution_id,
            **institution,
            "papers": len(institution_papers[institution_id]),
            "authors": institution_authors,
            "roles": sorted({record.get("role", "research") for record in author_records}),
            "contributions": [
                record.get("contribution")
                for record in author_records
                if record.get("contribution")
            ],
            "years": sorted(years[institution_id]),
        })
    markers.sort(key=lambda row: (-row["papers"], row["name"]))
    return {
        "markers": markers,
        "links": [
            {"source": left, "target": right, "papers": count}
            for (left, right), count in links.most_common()
        ],
        "mapped_authors": len(mapped_authors),
        "total_authors": len(author_names),
    }
