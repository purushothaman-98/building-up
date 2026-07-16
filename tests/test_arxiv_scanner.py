from pathlib import Path
from unittest.mock import patch
from arxiv_scanner import analyze, fetch_since, merge_archive, parse_feed

def test_casual_dft_mention_is_not_computational():
    result=analyze("Photoluminescence of excitons in MoS2","We measured photoluminescence spectra and observe an exciton. Earlier DFT work is discussed.")
    assert result["study_type"]=="Experimental"

def test_combined_requires_both_evidence_types():
    result=analyze("Excitons in WSe2","We measured reflectance spectra. Using GW-BSE calculations, we calculate the exciton binding energy.")
    assert result["study_type"]=="Theory + Experiment"
    assert "WSe2" in result["materials"]

def test_review_with_own_gw_bse_is_computational_not_combined():
    result=analyze(
        "Excitonic Landscape of Monolayer Transition-Metal Dichalcogenides",
        "We present a comprehensive and critical assessment and integrate prior photoluminescence measurements with theoretical insights. "
        "We highlight our state-of-the-art GW-BSE calculations for strained systems.",
    )
    assert result["study_type"]=="Computational"
    assert result["paper_nature"]=="Review / perspective"

def test_specific_material_maps_to_broad_family_and_property():
    result=analyze(
        "Strain-dependent exciton binding energy in monolayer MoS2",
        "Using GW-BSE calculations, we compute the exciton binding energy under biaxial strain.",
    )
    assert "MoS2" in result["materials"]
    assert "TMDs / 2D chalcogenides" in result["material_families"]
    assert {"Binding energy", "Strain response"}.issubset(result["exciton_properties"])

def test_explicit_numerical_language_is_computational():
    result=analyze("Excitonic enhancement", "Here, we numerically investigate the optical response of an excitonic monolayer.")
    assert result["study_type"]=="Computational"
    assert "numerically investigate" in result["classification_evidence"]["computational_actions"]

def test_generic_polariton_is_not_core_exciton_relevance():
    result=analyze("Magnetic polariton resonance", "We model an optical cavity supporting magnetic polaritons.")
    assert result["relevance"]=="Exciton-adjacent"

def test_landscape_alone_does_not_imply_review():
    result=analyze("Exciton landscape in a monolayer", "We calculate the exciton spectrum using GW-BSE calculations.")
    assert result["paper_nature"]=="Original research"

def test_instrument_acronyms_are_not_materials():
    result=analyze(
        "Exciton imaging",
        "We use ARPES, AFM, MEMS and LiDAR to discuss an exciton.",
    )
    assert not {"ARPES","AFM","MEMS","LiDAR"}.intersection(result["materials"])

def test_feed_and_version_merge(tmp_path: Path):
    xml=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2607.12345v2</id>
    <updated>2026-07-15T12:00:00Z</updated><published>2026-07-14T12:00:00Z</published>
    <title>Calculated exciton in MoS2</title><summary>Using GW-BSE calculations, we compute the exciton binding energy.</summary>
    <author><name>A. Researcher</name></author><category term="cond-mat.mtrl-sci"/>
    <link href="https://arxiv.org/pdf/2607.12345v2" type="application/pdf"/></entry></feed>'''
    papers=parse_feed(xml); assert papers[0]["arxiv_id"]=="2607.12345"; assert papers[0]["version"]=="v2"
    archive=merge_archive(tmp_path/"papers.json",papers)
    assert archive["counts"]["new_this_scan"]==1
    assert archive["papers"][0]["versions_seen"]==["v2"]


def test_bounded_fetch_uses_end_of_until_day():
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self): return b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    with patch("arxiv_scanner.urllib.request.urlopen",return_value=Response()) as opened:
        fetch_since("2026-06-01",max_results=100,page_size=100,until="2026-06-07")
    url=opened.call_args.args[0].full_url
    assert "202606010000" in url
    assert "202606072359" in url
