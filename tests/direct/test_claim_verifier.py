"""Direct-mode tests for Claim Verifier."""

import json

from conftest import (
    LLM_PATTERN,
    LLM_RESPONSE_SUPPORTED,
    LLM_RESPONSE_REFUTED,
    LLM_RESPONSE_UNVERIFIABLE,
    with_claim_data,
)


def test_verify_claim_supported(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    assert c.get_verification_count() == 1
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["verification_result"] == "SUPPORTED"
    assert v["is_verifiable"] == "true"
    assert v["claim_type"] == "FACTUAL"


def test_claim_types(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("BTC will reach $100k", "PREDICTION", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["claim_type"] == "PREDICTION"


def test_invalid_claim_type_defaults(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Test claim", "INVALID_TYPE", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["claim_type"] == "FACTUAL"


def test_evidence_extraction(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["evidence"] != "{}"


def test_source_reliability(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert int(v["source_reliability"]) > 0


def test_cross_reference_score(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert int(v["cross_reference_score"]) > 0


def test_requires_two_sources(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}])
    try:
        c.verify_claim("Test claim", "FACTUAL", sources)
        assert False, "Should have raised"
    except Exception:
        pass


def test_requires_claim(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    try:
        c.verify_claim("", "FACTUAL", sources)
        assert False, "Should have raised"
    except Exception:
        pass


def test_multiple_verifications(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid1 = c.verify_claim("Claim 1", "FACTUAL", sources)
    vid2 = c.verify_claim("Claim 2", "PREDICTION", sources)
    assert vid1 != vid2
    assert c.get_verification_count() == 2


def test_get_claim_types(verifier):
    vm, c = verifier
    types = c.get_claim_types()
    assert "FACTUAL" in types
    assert "PREDICTION" in types
    assert "OPINION" in types
    assert "STATISTICAL" in types


def test_stats(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    c.verify_claim("Claim 1", "FACTUAL", sources)
    c.verify_claim("Claim 2", "PREDICTION", sources)
    s = c.get_stats()
    assert s["total"] == 2
    assert "FACTUAL" in s["by_type"]
    assert "PREDICTION" in s["by_type"]


def test_all_sources_failed(verifier):
    vm, c = verifier
    vm.clear_mocks()
    vm.mock_web(".*source-a.*", {"method": "GET", "status": 200, "body": ""})
    vm.mock_web(".*source-b.*", {"method": "GET", "status": 200, "body": ""})
    vm.mock_llm(LLM_PATTERN, LLM_RESPONSE_UNVERIFIABLE)
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Test claim", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["verification_result"] == "UNVERIFIABLE"
