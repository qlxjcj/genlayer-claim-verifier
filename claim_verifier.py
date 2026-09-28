# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Verification:
    verification_id: str
    claim: str
    claim_type: str
    is_verifiable: str
    verification_result: str
    confidence: str
    evidence: str
    source_reliability: str
    cross_validation: str
    source_agreement: str
    sources_checked: str
    sources_agreed: str
    reasoning: str
    fetched_at: str


class ClaimVerifier(gl.Contract):
    verifications: TreeMap[str, str]
    verification_count: u256

    CLAIM_TYPES = ("FACTUAL", "PREDICTION", "OPINION", "STATISTICAL")

    def __init__(self):
        self.verification_count = 0

    def _decode_body(self, content) -> str:
        body = getattr(content, "body", None)
        if body is None:
            return str(content)
        if isinstance(body, bytes):
            return body.decode("utf-8", errors="replace")
        return str(body)

    def _verify_claim(self, claim: str, claim_type: str, sources: list) -> dict:
        def gather_and_verify() -> dict:
            fetched = []
            for source in sources:
                try:
                    content = gl.nondet.web.render(source["url"])
                    body = self._decode_body(content)[:1500]
                    fetched.append({"url": source["url"], "data": body, "retrieved": True})
                except Exception:
                    fetched.append({"url": source["url"], "data": "", "retrieved": False})

            retrieved = [f for f in fetched if f["retrieved"]]
            if not retrieved:
                return {
                    "is_verifiable": "false",
                    "verification_result": "UNVERIFIABLE",
                    "confidence": "0",
                    "evidence": "{}",
                    "source_reliability": "0",
                    "cross_validation": "FAIL",
                    "source_agreement": "0",
                    "sources_checked": len(sources),
                    "sources_agreed": 0,
                    "reasoning": "No sources could be retrieved.",
                }

            parts = []
            for i, r in enumerate(retrieved):
                parts.append("[Source " + str(i+1) + "] " + r["url"] + ":\n" + r["data"][:500])
            sources_text = "\n".join(parts)

            json_format = chr(123) + chr(34) + "is_verifiable" + chr(34) + ": " + chr(34) + "true" + chr(34) + "|" + chr(34) + "false" + chr(34) + ", " + chr(34) + "verification_result" + chr(34) + ": " + chr(34) + "SUPPORTED" + chr(34) + "|" + chr(34) + "REFUTED" + chr(34) + "|" + chr(34) + "UNVERIFIABLE" + chr(34) + ", " + chr(34) + "confidence" + chr(34) + ": " + chr(34) + "<0-100>" + chr(34) + ", " + chr(34) + "evidence" + chr(34) + ": " + chr(123) + chr(34) + "<source>" + chr(34) + ": " + chr(34) + "<quote>" + chr(34) + chr(125) + ", " + chr(34) + "source_reliability" + chr(34) + ": " + chr(34) + "<0-100>" + chr(34) + ", " + chr(34) + "cross_validation" + chr(34) + ": " + chr(34) + "PASS" + chr(34) + "|" + chr(34) + "FAIL" + chr(34) + "|" + chr(34) + "PARTIAL" + chr(34) + ", " + chr(34) + "source_agreement" + chr(34) + ": " + chr(34) + "<0-100>" + chr(34) + ", " + chr(34) + "reasoning" + chr(34) + ": " + chr(34) + "<text>" + chr(34) + chr(125)

            task = (
                "You are a claim verifier with cross-validation capabilities.\n"
                "CLAIM TYPE: " + claim_type + "\n"
                "CLAIM: " + claim + "\n"
                "SOURCES (" + str(len(retrieved)) + " retrieved):\n" + sources_text + "\n\n"
                "INSTRUCTIONS:\n"
                "1. is_verifiable: Can this claim be verified with factual evidence?\n"
                "2. verification_result: SUPPORTED, REFUTED, or UNVERIFIABLE\n"
                "3. evidence: Extract specific quotes from each source that support/refute the claim\n"
                "4. source_reliability: Rate source authority (0-100)\n"
                "5. cross_validation: Compare evidence between sources - PASS if agree, FAIL if contradict, PARTIAL if partial\n"
                "6. source_agreement: percentage of sources that agree (0-100)\n\n"
                "Respond ONLY in JSON: " + json_format
            )
            result = gl.nondet.exec_prompt(task)
            if isinstance(result, str):
                result = json.loads(result.replace("```json", "").replace("```", ""))
            if not isinstance(result, dict):
                raise gl.vm.UserError("[LLM_ERROR] LLM returned non-dict result")
            result["sources_checked"] = len(sources)
            result["sources_agreed"] = len(retrieved)
            return result

        principle = (
            "Two results are equivalent if is_verifiable matches exactly, "
            "verification_result matches exactly, claim_type matches exactly, "
            "cross_validation matches exactly, "
            "confidence differs by at most 5 points, "
            "source_reliability differs by at most 10 points, "
            "source_agreement differs by at most 10 points, "
            "evidence quotes may differ slightly, "
            "sources_checked and sources_agreed match exactly. "
            "reasoning wording may differ."
        )
        return gl.eq_principle.prompt_comparative(gather_and_verify, principle)

    @gl.public.write
    def verify_claim(self, claim: str, claim_type: str, sources_json: str) -> str:
        if not claim or not claim.strip():
            raise gl.vm.UserError("Claim is required")

        claim_type = (claim_type or "FACTUAL").upper()
        if claim_type not in self.CLAIM_TYPES:
            claim_type = "FACTUAL"

        try:
            sources = json.loads(sources_json)
        except (json.JSONDecodeError, TypeError):
            raise gl.vm.UserError("Invalid sources JSON")

        if not isinstance(sources, list) or len(sources) < 2:
            raise gl.vm.UserError("At least 2 sources required for cross-validation")

        for s in sources:
            if not isinstance(s, dict) or "url" not in s:
                raise gl.vm.UserError("Each source must have a url field")
            url = s["url"]
            if not url.startswith("http://") and not url.startswith("https://"):
                raise gl.vm.UserError("Invalid URL: " + url)

        result = self._verify_claim(claim.strip(), claim_type, sources)

        from datetime import datetime, timezone
        self.verification_count += 1
        verification_id = str(self.verification_count)

        verification = Verification(
            verification_id=verification_id,
            claim=claim.strip(),
            claim_type=claim_type,
            is_verifiable=str(result.get("is_verifiable", "false")).lower(),
            verification_result=str(result.get("verification_result", "UNVERIFIABLE")),
            confidence=str(result.get("confidence", "0")),
            evidence=json.dumps(result.get("evidence", {})),
            source_reliability=str(result.get("source_reliability", "0")),
            cross_validation=str(result.get("cross_validation", "FAIL")),
            source_agreement=str(result.get("source_agreement", "0")),
            sources_checked=str(result.get("sources_checked", 0)),
            sources_agreed=str(result.get("sources_agreed", 0)),
            reasoning=str(result.get("reasoning", "")),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        self.verifications[verification_id] = json.dumps(verification.__dict__)
        return verification_id

    @gl.public.view
    def get_verification(self, verification_id: str) -> str:
        return self.verifications.get(str(verification_id), "{}")

    @gl.public.view
    def get_verification_count(self) -> int:
        return self.verification_count

    @gl.public.view
    def get_claim_types(self) -> list:
        return list(self.CLAIM_TYPES)

    @gl.public.view
    def get_stats(self) -> dict:
        total = 0
        supported = 0
        refuted = 0
        unverifiable = 0
        cross_valid = 0
        by_type = {}
        by_result = {}
        for v in self.verifications.values():
            r = json.loads(v)
            total += 1
            ct = r.get("claim_type", "FACTUAL")
            by_type[ct] = by_type.get(ct, 0) + 1
            result = r.get("verification_result", "UNVERIFIABLE")
            by_result[result] = by_result.get(result, 0) + 1
            if result == "SUPPORTED":
                supported += 1
            elif result == "REFUTED":
                refuted += 1
            else:
                unverifiable += 1
            if r.get("cross_validation") == "PASS":
                cross_valid += 1
        return {
            "total": total,
            "supported": supported,
            "refuted": refuted,
            "unverifiable": unverifiable,
            "cross_validated": cross_valid,
            "by_type": by_type,
            "by_result": by_result,
        }