"""Direct-mode tests for Claim Verifier."""

import json

from conftest import (
    LLM_PATTERN,
    LLM_RESPONSE_SUPPORTED,
    LLM_RESPONSE_FAIL_VALIDATION,
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
    assert v["cross_validation"] == "PASS"


def test_cross_validation_pass(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["cross_validation"] == "PASS"
    assert int(v["source_agreement"]) > 50


def test_cross_validation_fail(verifier):
    vm, c = verifier
    vm.clear_mocks()
    vm.mock_web(".*source-a.*", {"method": "GET", "status": 200, "body": "Bitcoin reached $60,000."})
    vm.mock_web(".*source-b.*", {"method": "GET", "status": 200, "body": "Bitcoin was $30,000."})
    vm.mock_llm(LLM_PATTERN, LLM_RESPONSE_FAIL_VALIDATION)
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin price claim", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["cross_validation"] == "FAIL"


def test_evidence_extraction(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["evidence"] != "{}"
    evidence = json.loads(v["evidence"])
    assert len(evidence) > 0


def test_source_reliability(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert int(v["source_reliability"]) > 0


def test_source_agreement_score(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert int(v["source_agreement"]) > 0


def test_claim_types(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("BTC will reach $100k", "PREDICTION", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["claim_type"] == "PREDICTION"


def test_requires_two_sources(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}])
    try:
        c.verify_claim("Test claim", "FACTUAL", sources)
        assert False, "Should have raised"
    except Exception:
        pass


def test_all_sources_failed(verifier):
    vm, c = verifier
    vm.clear_mocks()
    vm.mock_web(".*source-a.*", {"method": "GET", "status": 200, "body": ""})
    vm.mock_web(".*source-b.*", {"method": "GET", "status": 200, "body": ""})
    vm.mock_llm(LLM_PATTERN, json.dumps({
        "is_verifiable": "false",
        "verification_result": "UNVERIFIABLE",
        "confidence": "0",
        "evidence": {},
        "source_reliability": "0",
        "cross_validation": "FAIL",
        "source_agreement": "0",
        "reasoning": "No sources."
    }))
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Test claim", "FACTUAL", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["cross_validation"] == "FAIL"


def test_stats(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    c.verify_claim("Claim 1", "FACTUAL", sources)
    c.verify_claim("Claim 2", "PREDICTION", sources)
    s = c.get_stats()
    assert s["total"] == 2
    assert s["cross_validated"] == 2
