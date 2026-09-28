"""Shared fixtures and mocks for Claim Verifier tests."""

import json
import os
import pytest

CONTRACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "claim_verifier.py",
)

LLM_PATTERN = r".*claim.*verifier.*|.*cross_validation.*|.*verification_result.*"

SOURCE_A = {"method": "GET", "status": 200, "body": "Bitcoin reached $60,000 in 2024."}
SOURCE_B = {"method": "GET", "status": 200, "body": "Bitcoin price analysis shows growth."}

LLM_RESPONSE_SUPPORTED = json.dumps({
    "is_verifiable": "true",
    "verification_result": "SUPPORTED",
    "confidence": "85",
    "evidence": {"https://source-a.com": "Bitcoin reached $60,000 in 2024."},
    "source_reliability": "80",
    "cross_validation": "PASS",
    "source_agreement": "90",
    "reasoning": "Multiple sources confirm the claim."
})

LLM_RESPONSE_FAIL_VALIDATION = json.dumps({
    "is_verifiable": "true",
    "verification_result": "UNVERIFIABLE",
    "confidence": "30",
    "evidence": {"https://source-a.com": "Bitcoin reached $60,000.", "https://source-b.com": "Bitcoin was $30,000."},
    "source_reliability": "50",
    "cross_validation": "FAIL",
    "source_agreement": "30",
    "reasoning": "Sources contradict each other."
})


def with_claim_data(vm):
    vm.mock_web(".*source-a.*", SOURCE_A)
    vm.mock_web(".*source-b.*", SOURCE_B)
    vm.mock_llm(LLM_PATTERN, LLM_RESPONSE_SUPPORTED)


@pytest.fixture
def verifier(direct_vm, direct_deploy):
    vm = direct_vm
    c = direct_deploy(CONTRACT)
    with_claim_data(vm)
    return vm, c
