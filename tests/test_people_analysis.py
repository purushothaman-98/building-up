from people_analysis import (
    build_institution_analysis,
    build_people_analysis,
    mapped_papers,
)


def sample_paper(identifier, authors, year="2026", approved=True):
    return {
        "arxiv_id": identifier,
        "authors": authors,
        "submitted": f"{year}-01-01T00:00:00Z",
        "title": identifier,
        "materials": ["WSe2"],
        "material_families": ["TMDs / 2D chalcogenides"],
        "methods": ["Photoluminescence"],
        "ai_decision": {"include_in_feed": approved},
    }


def test_people_analysis_counts_real_coauthorship_and_years():
    papers = [
        sample_paper("one", ["Ada", "Bo"], "2025"),
        sample_paper("two", ["Ada", "Bo", "Cy"], "2026"),
    ]
    result = build_people_analysis(papers)

    ada = next(row for row in result["authors"] if row["author"] == "Ada")
    assert ada["papers"] == 2
    assert ada["first_year"] == "2025"
    assert ada["last_year"] == "2026"
    assert result["connections"][0] == {
        "author_a": "Ada",
        "author_b": "Bo",
        "shared_papers": 2,
    }
    assert result["years"] == {"2025": 1, "2026": 1}


def test_unverified_author_is_never_geographically_guessed():
    papers = [sample_paper("one", ["Verified", "Unknown"])]
    registry = {
        "institutions": {
            "lab": {
                "name": "Verified Lab",
                "latitude": 1.0,
                "longitude": 2.0,
            }
        },
        "authors": {"Verified": {"institution_id": "lab"}},
    }
    result = build_institution_analysis(papers, registry)

    assert result["mapped_authors"] == 1
    assert result["total_authors"] == 2
    assert result["markers"][0]["authors"] == ["Verified"]
    assert "Unknown" not in result["markers"][0]["authors"]


def test_institution_link_requires_a_shared_paper():
    registry = {
        "institutions": {
            "a": {"name": "A", "latitude": 1, "longitude": 2},
            "b": {"name": "B", "latitude": 3, "longitude": 4},
        },
        "authors": {
            "Ada": {"institution_id": "a"},
            "Bo": {"institution_id": "b"},
        },
    }
    separate = [sample_paper("one", ["Ada"]), sample_paper("two", ["Bo"])]
    together = separate + [sample_paper("three", ["Ada", "Bo"])]

    assert build_institution_analysis(separate, registry)["links"] == []
    assert build_institution_analysis(together, registry)["links"] == [
        {"source": "a", "target": "b", "papers": 1}
    ]


def test_mapped_papers_uses_approved_feed_when_reviewed():
    approved = sample_paper("yes", ["Ada"], approved=True)
    rejected = sample_paper("no", ["Bo"], approved=False)
    assert mapped_papers([approved, rejected]) == [approved]
