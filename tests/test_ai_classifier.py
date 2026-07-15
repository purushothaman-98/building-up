import json

import pytest

from ai_classifier import fingerprint, parse_json_response, pending_papers, validate


def paper(version="v1", abstract="We calculate excitons with GW-BSE."):
    return {
        "arxiv_id": "2601.00001", "version": version, "title": "Excitons in a monolayer",
        "abstract": abstract, "categories": ["cond-mat.mtrl-sci"],
    }


def valid_decision():
    return {
        "include_in_feed": True, "relevance": "Core exciton paper",
        "research_type": "Computational", "paper_nature": "Original research",
        "materials": ["monolayer"], "material_families": ["2D materials"],
        "experimental_methods": [], "computational_methods": ["GW", "BSE"],
        "exciton_properties": ["binding energy"], "confidence": 0.93,
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
