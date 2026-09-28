"""Shared fixtures and mocks for Claim Verifier tests."""

import json
import os
import pytest

CONTRACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "claim_verifier.py",
)

LLM_PATTERN = r".*claim.*verifier.*|.*verification_result.*|.*is_verifiable.*"

SOURCE_A = {"method": "GET", "status": 200, "body": "Bitcoin reached $60,000 in 2024."}
SOURCE_B = {"method": "GET", "status": 200, "body": "Bitcoin price analysis shows growth."}

LLM_RESPONSE_SUPPORTED = json.dumps({
    "is_verifiable": "true",
    "verification_result": "SUPPORTED",
    "confidence": "85",
    "evidence_found": "strong",
    "reasoning": "Multiple sources confirm the claim."
})

LLM_RESPONSE_REFUTED = json.dumps({
    "is_verifiable": "true",
    "verification_result": "REFUTED",
    "confidence": "75",
    "evidence_found": "strong",
    "reasoning": "Sources contradict the claim."
})

LLM_RESPONSE_UNVERIFIABLE = json.dumps({
    "is_verifiable": "false",
    "verification_result": "UNVERIFIABLE",
    "confidence": "0",
    "evidence_found": "none",
    "reasoning": "Claim cannot be verified with available sources."
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
