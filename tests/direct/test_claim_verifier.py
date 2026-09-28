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
    vid = c.verify_claim("Bitcoin reached $60,000", sources)
    assert c.get_verification_count() == 1
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["verification_result"] == "SUPPORTED"
    assert v["is_verifiable"] == "true"


def test_verify_claim_refuted(verifier):
    vm, c = verifier
    vm.clear_mocks()
    vm.mock_web(".*source-a.*", {"method": "GET", "status": 200, "body": "Bitcoin price was $30,000."})
    vm.mock_llm(LLM_PATTERN, LLM_RESPONSE_REFUTED)
    sources = json.dumps([{"url": "https://source-a.com"}])
    vid = c.verify_claim("Bitcoin reached $60,000", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["verification_result"] == "REFUTED"


def test_verify_claim_unverifiable(verifier):
    vm, c = verifier
    vm.clear_mocks()
    vm.mock_web(".*source-a.*", {"method": "GET", "status": 200, "body": "No relevant data."})
    vm.mock_llm(LLM_PATTERN, LLM_RESPONSE_UNVERIFIABLE)
    sources = json.dumps([{"url": "https://source-a.com"}])
    vid = c.verify_claim("Aliens exist", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["verification_result"] == "UNVERIFIABLE"
    assert v["is_verifiable"] == "false"


def test_requires_claim(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}])
    try:
        c.verify_claim("", sources)
        assert False, "Should have raised"
    except Exception:
        pass


def test_requires_sources(verifier):
    vm, c = verifier
    try:
        c.verify_claim("Test claim", "[]")
        assert False, "Should have raised"
    except Exception:
        pass


def test_requires_valid_json(verifier):
    vm, c = verifier
    try:
        c.verify_claim("Test claim", "invalid")
        assert False, "Should have raised"
    except Exception:
        pass


def test_requires_url_field(verifier):
    vm, c = verifier
    sources = json.dumps([{"data": "test"}])
    try:
        c.verify_claim("Test claim", sources)
        assert False, "Should have raised"
    except Exception:
        pass


def test_requires_http_url(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "ftp://test.com"}])
    try:
        c.verify_claim("Test claim", sources)
        assert False, "Should have raised"
    except Exception:
        pass


def test_multiple_verifications(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}])
    vid1 = c.verify_claim("Claim 1", sources)
    vid2 = c.verify_claim("Claim 2", sources)
    assert vid1 != vid2
    assert c.get_verification_count() == 2


def test_source_agreement(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Test claim", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert int(v["sources_checked"]) == 2
    assert int(v["sources_agreed"]) == 2


def test_all_sources_failed(verifier):
    vm, c = verifier
    vm.clear_mocks()
    vm.mock_web(".*source-a.*", {"method": "GET", "status": 200, "body": ""})
    vm.mock_web(".*source-b.*", {"method": "GET", "status": 200, "body": ""})
    vm.mock_llm(LLM_PATTERN, LLM_RESPONSE_UNVERIFIABLE)
    sources = json.dumps([{"url": "https://source-a.com"}, {"url": "https://source-b.com"}])
    vid = c.verify_claim("Test claim", sources)
    raw = c.get_verification(vid)
    v = json.loads(raw)
    assert v["verification_result"] == "UNVERIFIABLE"


def test_stats(verifier):
    vm, c = verifier
    sources = json.dumps([{"url": "https://source-a.com"}])
    c.verify_claim("Claim 1", sources)
    s = c.get_stats()
    assert s["total"] == 1
    assert s["supported"] == 1


def test_get_verification_not_found(verifier):
    vm, c = verifier
    assert c.get_verification("999") == "{}"
