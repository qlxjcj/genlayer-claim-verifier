# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Verification:
    verification_id: str
    claim: str
    is_verifiable: str
    verification_result: str
    confidence: str
    sources_checked: str
    sources_agreed: str
    evidence_found: str
    reasoning: str
    fetched_at: str


class ClaimVerifier(gl.Contract):
    verifications: TreeMap[str, str]
    verification_count: u256

    def __init__(self):
        self.verification_count = 0

    def _decode_body(self, content) -> str:
        body = getattr(content, "body", None)
        if body is None:
            return str(content)
        if isinstance(body, bytes):
            return body.decode("utf-8", errors="replace")
        return str(body)

    def _verify_claim(self, claim: str, sources: list) -> dict:
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
                    "evidence_found": "none",
                    "sources_checked": len(sources),
                    "sources_agreed": 0,
                    "reasoning": "No sources could be retrieved.",
                }

            parts = []
            for i, r in enumerate(retrieved):
                parts.append("[Source " + str(i+1) + "] " + r["url"] + ":\n" + r["data"][:500])
            sources_text = "\n".join(parts)

            json_format = chr(123) + chr(34) + "is_verifiable" + chr(34) + ": " + chr(34) + "true" + chr(34) + "|" + chr(34) + "false" + chr(34) + ", " + chr(34) + "verification_result" + chr(34) + ": " + chr(34) + "SUPPORTED" + chr(34) + "|" + chr(34) + "REFUTED" + chr(34) + "|" + chr(34) + "UNVERIFIABLE" + chr(34) + ", " + chr(34) + "confidence" + chr(34) + ": " + chr(34) + "<0-100>" + chr(34) + ", " + chr(34) + "evidence_found" + chr(34) + ": " + chr(34) + "strong" + chr(34) + "|" + chr(34) + "weak" + chr(34) + "|" + chr(34) + "none" + chr(34) + ", " + chr(34) + "reasoning" + chr(34) + ": " + chr(34) + "<text>" + chr(34) + chr(125)

            task = (
                "You are a claim verifier. Verify the following claim using the provided sources.\n"
                "CLAIM: " + claim + "\n"
                "SOURCES (" + str(len(retrieved)) + " retrieved):\n" + sources_text + "\n\n"
                "Verify: Is the claim verifiable? Is it supported or refuted by the evidence?\n"
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
            "verification_result matches exactly, confidence differs by at most 5 points, "
            "evidence_found matches exactly, sources_checked matches exactly, "
            "and sources_agreed matches exactly. "
            "reasoning wording may differ."
        )
        return gl.eq_principle.prompt_comparative(gather_and_verify, principle)

    @gl.public.write
    def verify_claim(self, claim: str, sources_json: str) -> str:
        if not claim or not claim.strip():
            raise gl.vm.UserError("Claim is required")

        try:
            sources = json.loads(sources_json)
        except (json.JSONDecodeError, TypeError):
            raise gl.vm.UserError("Invalid sources JSON")

        if not isinstance(sources, list) or len(sources) < 1:
            raise gl.vm.UserError("At least 1 source required")

        for s in sources:
            if not isinstance(s, dict) or "url" not in s:
                raise gl.vm.UserError("Each source must have a url field")
            url = s["url"]
            if not url.startswith("http://") and not url.startswith("https://"):
                raise gl.vm.UserError("Invalid URL: " + url)

        result = self._verify_claim(claim.strip(), sources)

        from datetime import datetime, timezone
        self.verification_count += 1
        verification_id = str(self.verification_count)

        verification = Verification(
            verification_id=verification_id,
            claim=claim.strip(),
            is_verifiable=str(result.get("is_verifiable", "false")).lower(),
            verification_result=str(result.get("verification_result", "UNVERIFIABLE")),
            confidence=str(result.get("confidence", "0")),
            sources_checked=str(result.get("sources_checked", 0)),
            sources_agreed=str(result.get("sources_agreed", 0)),
            evidence_found=str(result.get("evidence_found", "none")),
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
    def get_stats(self) -> dict:
        total = 0
        supported = 0
        refuted = 0
        unverifiable = 0
        by_result = {}
        for v in self.verifications.values():
            r = json.loads(v)
            total += 1
            result = r.get("verification_result", "UNVERIFIABLE")
            by_result[result] = by_result.get(result, 0) + 1
            if result == "SUPPORTED":
                supported += 1
            elif result == "REFUTED":
                refuted += 1
            else:
                unverifiable += 1
        return {
            "total": total,
            "supported": supported,
            "refuted": refuted,
            "unverifiable": unverifiable,
            "by_result": by_result,
        }