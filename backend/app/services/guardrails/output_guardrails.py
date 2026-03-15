"""
Output Guardrails

Response validation guardrails that run after LLM generation:
- HallucinationDetectionGuardrail: Verify response against context
- FactualGroundingGuardrail: Check claims are grounded in sources
- PIILeakageGuardrail: Prevent PII from appearing in responses
- CitationVerificationGuardrail: Verify citations match sources
"""

import re
import json
from typing import Any, Dict, List, Optional
from .base import (
    RuleBasedGuardrail,
    LLMBasedGuardrail,
    HybridGuardrail,
    GuardrailCheckResult,
    ViolationSeverity,
    ViolationType,
)
from .input_guardrails import PII_PATTERNS


class HallucinationDetectionGuardrail(LLMBasedGuardrail):
    """Detects hallucinations by comparing response to provided context."""

    def __init__(
        self,
        llm_client: Any,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7,
    ):
        super().__init__(
            name="hallucinationDetection",
            llm_client=llm_client,
            enabled=enabled,
            source=source,
            config=config,
        )
        self.threshold = config.get("threshold", threshold) if config else threshold

    async def check(self, data: Dict[str, Any]) -> GuardrailCheckResult:
        """
        Check if response is grounded in the provided context.

        Args:
            data: Dict with "response" and "context" keys
        """
        response = data.get("response", "")
        context = data.get("context", "")

        if not response:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={"skipped": True, "reason": "empty_response"},
            )

        if not context:
            # No context to verify against
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"skipped": True, "reason": "no_context"},
            )

        if not self.llm_client:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"skipped": True, "reason": "no_llm_client"},
            )

        try:
            prompt = f"""Analyze whether the response is factually grounded in the provided context.
Identify any claims in the response that are NOT supported by the context.

Context:
{context[:4000]}

Response:
{response[:2000]}

Respond with JSON:
{{
    "grounding_score": 0.0-1.0,
    "is_grounded": true/false,
    "ungrounded_claims": ["list of claims not in context"],
    "explanation": "brief explanation"
}}"""

            llm_response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0,
            )

            result = json.loads(
                llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            )

            grounding_score = result.get("grounding_score", 0.5)
            is_grounded = result.get("is_grounded", True) and grounding_score >= self.threshold
            ungrounded_claims = result.get("ungrounded_claims", [])

            return GuardrailCheckResult(
                name=self.name,
                passed=is_grounded,
                confidence=grounding_score,
                details={
                    "grounding_score": grounding_score,
                    "threshold": self.threshold,
                    "ungrounded_claims": ungrounded_claims,
                    "explanation": result.get("explanation", ""),
                    "violation": ViolationType.HALLUCINATION if not is_grounded else None,
                    "message": f"Response contains ungrounded claims" if not is_grounded else None,
                },
            )
        except Exception as e:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"error": str(e)},
            )


class FactualGroundingGuardrail(LLMBasedGuardrail):
    """Extracts factual claims and verifies them against sources."""

    def __init__(
        self,
        llm_client: Any,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        min_score: float = 0.8,
    ):
        super().__init__(
            name="factualGrounding",
            llm_client=llm_client,
            enabled=enabled,
            source=source,
            config=config,
        )
        self.min_score = config.get("minScore", min_score) if config else min_score

    async def check(self, data: Dict[str, Any]) -> GuardrailCheckResult:
        """
        Extract and verify factual claims.

        Args:
            data: Dict with "response" and "sources" (list of source documents)
        """
        response = data.get("response", "")
        sources = data.get("sources", [])

        if not response:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={"skipped": True, "reason": "empty_response"},
            )

        if not self.llm_client:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"skipped": True, "reason": "no_llm_client"},
            )

        # Format sources for verification
        sources_text = "\n\n".join([
            f"Source {i+1}: {s.get('content', s) if isinstance(s, dict) else s}"
            for i, s in enumerate(sources[:5])
        ])

        try:
            prompt = f"""Extract factual claims from the response and verify each against the sources.

Sources:
{sources_text[:3000]}

Response:
{response[:2000]}

Respond with JSON:
{{
    "claims": [
        {{"claim": "...", "verified": true/false, "source_index": 1 or null}}
    ],
    "verification_score": 0.0-1.0,
    "summary": "brief summary"
}}"""

            llm_response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0,
            )

            result = json.loads(
                llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            )

            claims = result.get("claims", [])
            verification_score = result.get("verification_score", 0.5)
            passed = verification_score >= self.min_score

            unverified_claims = [c["claim"] for c in claims if not c.get("verified", True)]

            return GuardrailCheckResult(
                name=self.name,
                passed=passed,
                confidence=verification_score,
                details={
                    "verification_score": verification_score,
                    "min_score": self.min_score,
                    "total_claims": len(claims),
                    "verified_claims": len(claims) - len(unverified_claims),
                    "unverified_claims": unverified_claims,
                    "summary": result.get("summary", ""),
                    "violation": ViolationType.UNGROUNDED_CLAIM if not passed else None,
                },
            )
        except Exception as e:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"error": str(e)},
            )


class PIILeakageGuardrail(RuleBasedGuardrail):
    """Detects PII leakage in LLM responses."""

    def __init__(
        self,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        patterns_to_check: Optional[List[str]] = None,
    ):
        super().__init__(
            name="piiLeakage",
            enabled=enabled,
            source=source,
            config=config,
        )
        self.patterns_to_check = patterns_to_check or list(PII_PATTERNS.keys())

    async def check(self, data: Dict[str, Any]) -> GuardrailCheckResult:
        """Check for PII in the response."""
        response = data.get("response", "")

        if not response:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
            )

        detected_pii: List[Dict[str, Any]] = []

        for pii_type in self.patterns_to_check:
            if pii_type not in PII_PATTERNS:
                continue

            pii_info = PII_PATTERNS[pii_type]
            pattern = re.compile(pii_info["pattern"], re.IGNORECASE)
            matches = pattern.findall(response)

            if matches:
                detected_pii.append({
                    "type": pii_type,
                    "description": pii_info["description"],
                    "count": len(matches),
                    "severity": pii_info["severity"],
                })

        if detected_pii:
            max_severity = max(
                (d["severity"] for d in detected_pii),
                key=lambda s: ["low", "medium", "high", "critical"].index(s)
            )
            return GuardrailCheckResult(
                name=self.name,
                passed=False,
                confidence=0.95,
                details={
                    "detected_pii": detected_pii,
                    "max_severity": max_severity,
                    "violation": ViolationType.PII_LEAKAGE,
                    "message": f"PII detected in response: {', '.join(d['description'] for d in detected_pii)}",
                },
            )

        return GuardrailCheckResult(
            name=self.name,
            passed=True,
            confidence=1.0,
            details={"pii_found": False},
        )


class CitationVerificationGuardrail(HybridGuardrail):
    """Verifies that citations in the response match the sources."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        llm_threshold: float = 0.7,
    ):
        super().__init__(
            name="citationVerification",
            llm_client=llm_client,
            enabled=enabled,
            source=source,
            config=config,
            llm_threshold=llm_threshold,
        )

    # Citation patterns
    CITATION_PATTERNS = [
        r"\[(\d+)\]",  # [1], [2]
        r"\[source\s*(\d+)\]",  # [source 1]
        r"(?:according to|per|from)\s+source\s*(\d+)",  # according to source 1
        r"\(source\s*(\d+)\)",  # (source 1)
    ]

    def _extract_citations(self, text: str) -> List[int]:
        """Extract citation numbers from text."""
        citations = set()
        for pattern in self.CITATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    citations.add(int(match))
                except ValueError:
                    pass
        return sorted(citations)

    async def rule_check(self, data: Dict[str, Any]) -> GuardrailCheckResult:
        """Pattern-based citation extraction and basic verification."""
        response = data.get("response", "")
        sources = data.get("sources", [])

        if not response:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={"skipped": True, "reason": "empty_response"},
            )

        citations = self._extract_citations(response)

        if not citations:
            # No citations found - may or may not be an issue
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.6,  # Uncertain without LLM
                details={
                    "citations_found": False,
                    "needs_review": True,
                },
            )

        # Check if citations are within valid range
        max_source = len(sources)
        invalid_citations = [c for c in citations if c < 1 or c > max_source]

        if invalid_citations:
            return GuardrailCheckResult(
                name=self.name,
                passed=False,
                confidence=0.9,
                details={
                    "citations": citations,
                    "invalid_citations": invalid_citations,
                    "source_count": max_source,
                    "violation": ViolationType.INVALID_CITATION,
                    "message": f"Invalid citations: {invalid_citations} (max: {max_source})",
                },
            )

        # Citations are valid numbers - but content matching needs LLM
        return GuardrailCheckResult(
            name=self.name,
            passed=True,
            confidence=0.7,  # Needs LLM to verify content matches
            details={
                "citations": citations,
                "all_valid": True,
            },
        )

    async def llm_check(self, data: Dict[str, Any]) -> GuardrailCheckResult:
        """LLM-based citation content verification."""
        response = data.get("response", "")
        sources = data.get("sources", [])

        if not self.llm_client:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"skipped": True, "reason": "no_llm_client"},
            )

        try:
            sources_text = "\n\n".join([
                f"Source {i+1}: {s.get('content', s) if isinstance(s, dict) else s}"
                for i, s in enumerate(sources[:5])
            ])

            prompt = f"""Verify that citations in the response accurately reference the sources.
Check if the cited information actually appears in the referenced source.

Sources:
{sources_text[:3000]}

Response with citations:
{response[:2000]}

Respond with JSON:
{{
    "citations_valid": true/false,
    "verification_score": 0.0-1.0,
    "issues": ["list of citation issues"],
    "summary": "brief summary"
}}"""

            llm_response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=400,
                temperature=0,
            )

            result = json.loads(
                llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            )

            return GuardrailCheckResult(
                name=self.name,
                passed=result.get("citations_valid", True),
                confidence=result.get("verification_score", 0.5),
                details={
                    "llm_verified": True,
                    "issues": result.get("issues", []),
                    "summary": result.get("summary", ""),
                    "violation": ViolationType.INVALID_CITATION if not result.get("citations_valid", True) else None,
                },
            )
        except Exception as e:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=0.5,
                details={"error": str(e)},
            )
