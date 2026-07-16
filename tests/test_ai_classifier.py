import json

import pytest

from ai_classifier import (
    COMPUTATIONAL_METHODS, EXCITON_OBSERVABLES, EXPERIMENTAL_METHODS, MATERIAL_FAMILIES,
    OUTPUT_SCHEMA, SYSTEM_PROMPT, fingerprint, latest_window, parse_json_response,
    pending_papers, user_prompt, validate,
)


def paper(version="v1", abstract="We calculate excitons with GW-BSE."):
    return {
        "arxiv_id": "2601.00001", "version": version, "title": "Excitons in a monolayer",
        "abstract": abstract, "authors": ["A. Author"], "submitted": "2026-07-14T00:00:00Z",
        "categories": ["cond-mat.mtrl-sci"],
    }


def valid_decision():
    return {
        "include_in_feed": True, "relevance": "Core exciton paper",
        "research_type": "Computational", "paper_nature": "Original research",
        "materials": ["MoS₂ monolayer"], "material_families": ["TMDs"],
        "experimental_methods": [], "computational_methods": ["DFT + GW/BSE"],
        "exciton_properties": ["Binding energy"], "confidence": 0.93,
        "reason": "Original GW-BSE exciton calculations are reported.",
        "evidence": ["calculate excitons with GW-BSE"],
    }


def test_fingerprint_changes_with_version_or_abstract():
    assert fingerprint(paper()) != fingerprint(paper(version="v2"))
    assert fingerprint(paper()) != fingerprint(paper(abstract="A changed abstract"))


def test_pending_queue_uses_fingerprint_and_respects_override():
    item = paper()
    records = {item["arxiv_id"]: {"fingerprint": fingerprint(item)}}
    assert pending_papers([item], records, {}) == []
    assert pending_papers([paper(version="v2")], records, {})
    assert pending_papers([paper(version="v2")], records, {item["arxiv_id"]: {"include_in_feed": True}}) == []


def test_response_validation_and_fenced_json():
    decision = valid_decision()
    parsed = parse_json_response("```json\n" + json.dumps(decision) + "\n```")
    assert validate(parsed)["confidence"] == 0.93


def test_invalid_enum_is_rejected():
    decision = valid_decision()
    decision["relevance"] = "maybe"
    with pytest.raises(ValueError):
        validate(decision)


def test_common_model_scalar_deviations_are_normalized():
    decision = valid_decision()
    decision.update({"include_in_feed": "true", "relevance": ["Core exciton paper"], "research_type": ["Computational"]})
    normalized = validate(decision)
    assert normalized["include_in_feed"] is True
    assert normalized["research_type"] == "Computational"


def test_only_title_authors_and_abstract_are_sent_to_model():
    prompt = user_prompt(paper())
    metadata = json.loads(prompt.split("PAPER METADATA:\n", 1)[1])
    assert set(metadata) == {"title", "authors", "abstract"}


def test_latest_window_uses_latest_available_submission_date():
    papers = [paper(), {**paper(), "arxiv_id": "old", "submitted": "2026-07-07T00:00:00Z"}]
    selected, start, end = latest_window(papers, 7)
    assert [item["arxiv_id"] for item in selected] == ["2601.00001"]
    assert start.isoformat() == "2026-07-08"
    assert end.isoformat() == "2026-07-14"


def test_prompt_encodes_scientific_scope_and_conservative_screening():
    required_guidance = [
        "A keyword hit is never sufficient",
        "ground-state DFT",
        "phonon-polaritons",
        "AUTHORS' ORIGINAL WORK ONLY",
        "separate evidence for both",
        "At title/abstract screening, preserve uncertain records",
        "COFs",
        "g-factors",
        "PL or absorption peak position",
        "exactly one broad class",
    ]
    assert all(phrase in SYSTEM_PROMPT for phrase in required_guidance)


def test_uncertain_relevance_is_retained_for_human_review():
    decision = valid_decision()
    decision.update({"include_in_feed": True, "relevance": "Uncertain", "confidence": 0.45})
    assert validate(decision)["relevance"] == "Uncertain"


def test_feed_decision_must_agree_with_relevance():
    decision = valid_decision()
    decision.update({"include_in_feed": False, "relevance": "Core exciton paper"})
    with pytest.raises(ValueError, match="contradicts"):
        validate(decision)


def test_grouped_fields_are_constrained_to_canonical_vocabularies():
    properties = OUTPUT_SCHEMA["schema"]["properties"]
    assert set(properties["material_families"]["items"]["enum"]) == MATERIAL_FAMILIES
    assert set(properties["experimental_methods"]["items"]["enum"]) == EXPERIMENTAL_METHODS
    assert set(properties["computational_methods"]["items"]["enum"]) == COMPUTATIONAL_METHODS
    assert set(properties["exciton_properties"]["items"]["enum"]) == EXCITON_OBSERVABLES


def test_free_form_keyword_fragments_are_rejected_from_grouped_fields():
    decision = valid_decision()
    decision["experimental_methods"] = ["we measured a beautiful spectrum"]
    with pytest.raises(ValueError, match="Non-canonical experimental_methods"):
        validate(decision)


def test_exactly_one_primary_material_class_is_required():
    decision = valid_decision()
    decision["material_families"] = ["TMDs", "Other 2D materials"]
    with pytest.raises(ValueError, match="exactly one"):
        validate(decision)
