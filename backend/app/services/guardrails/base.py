"""
Base Classes for Guardrails

Provides abstract base classes and result types for all guardrail implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time


class ViolationSeverity(str, Enum):
    """Severity levels for guardrail violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """Types of guardrail violations."""
    # Input violations
    PII_DETECTED = "pii_detected"
    INJECTION_ATTEMPT = "injection_attempt"
    TOXICITY = "toxicity"
    QUERY_TOO_LONG = "query_too_long"
    QUERY_TOO_SHORT = "query_too_short"
    MALFORMED_INPUT = "malformed_input"

    # Retrieval violations
    LOW_RELEVANCE_SCORE = "low_relevance_score"
    TOKEN_LIMIT_EXCEEDED = "token_limit_exceeded"
    DUPLICATE_CONTENT = "duplicate_content"
    INSUFFICIENT_SOURCES = "insufficient_sources"

    # Output violations
    HALLUCINATION = "hallucination"
    UNGROUNDED_CLAIM = "ungrounded_claim"
    PII_LEAKAGE = "pii_leakage"
    INVALID_CITATION = "invalid_citation"
    FACTUAL_ERROR = "factual_error"


class GuardrailViolation(BaseModel):
    """Represents a single guardrail violation."""
    type: str
    severity: ViolationSeverity
    message: str
    location: Optional[str] = None  # Where in the input/output the violation occurred
    remediation: Optional[str] = None  # Suggested fix
    details: Dict[str, Any] = Field(default_factory=dict)


class GuardrailCheckResult(BaseModel):
    """Result of a single guardrail check."""
    name: str
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source: str = "workflow"  # "org_enforced" or "workflow"
    execution_time_ms: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)


class GuardrailResult(BaseModel):
    """Aggregate result of all guardrail checks for a phase."""
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    violations: List[GuardrailViolation] = Field(default_factory=list)
    checks: Dict[str, GuardrailCheckResult] = Field(default_factory=dict)
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_violation(
        self,
        violation_type: str,
        severity: ViolationSeverity,
        message: str,
        location: Optional[str] = None,
        remediation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a violation to the result."""
        self.violations.append(
            GuardrailViolation(
                type=violation_type,
                severity=severity,
                message=message,
                location=location,
                remediation=remediation,
                details=details or {},
            )
        )
        self.passed = False

    def add_check(self, check: GuardrailCheckResult) -> None:
        """Add a check result."""
        self.checks[check.name] = check
        if not check.passed:
            self.passed = False
        # Update overall confidence as minimum of all checks
        if self.checks:
            self.confidence = min(c.confidence for c in self.checks.values())

    @classmethod
    def success(cls, execution_time_ms: int = 0) -> "GuardrailResult":
        """Create a successful result."""
        return cls(
            passed=True,
            confidence=1.0,
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def failure(
        cls,
        violations: List[GuardrailViolation],
        execution_time_ms: int = 0,
    ) -> "GuardrailResult":
        """Create a failed result with violations."""
        return cls(
            passed=False,
            confidence=0.0,
            violations=violations,
            execution_time_ms=execution_time_ms,
        )


class BaseGuardrail(ABC):
    """Abstract base class for all guardrails."""

    def __init__(
        self,
        name: str,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.enabled = enabled
        self.source = source
        self.config = config or {}

    @abstractmethod
    async def check(self, data: Any) -> GuardrailCheckResult:
        """
        Perform the guardrail check.

        Args:
            data: The data to check (query, chunks, response, etc.)

        Returns:
            GuardrailCheckResult with pass/fail status and details
        """
        pass

    async def execute(self, data: Any) -> GuardrailCheckResult:
        """
        Execute the guardrail check with timing.

        Args:
            data: The data to check

        Returns:
            GuardrailCheckResult with timing information
        """
        if not self.enabled:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                source=self.source,
                execution_time_ms=0,
                details={"skipped": True, "reason": "disabled"},
            )

        start_time = time.time()
        try:
            result = await self.check(data)
            result.source = self.source
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result
        except Exception as e:
            return GuardrailCheckResult(
                name=self.name,
                passed=False,
                confidence=0.0,
                source=self.source,
                execution_time_ms=int((time.time() - start_time) * 1000),
                details={"error": str(e)},
            )


class RuleBasedGuardrail(BaseGuardrail):
    """
    Base class for rule-based guardrails.

    Rule-based guardrails use patterns, thresholds, or deterministic logic
    and execute very fast (<1ms typically).
    """

    guardrail_type = "rule"


class LLMBasedGuardrail(BaseGuardrail):
    """
    Base class for LLM-based guardrails.

    LLM-based guardrails use language models to evaluate content
    and are more accurate but slower.
    """

    guardrail_type = "llm"

    def __init__(
        self,
        name: str,
        llm_client: Any,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, enabled, source, config)
        self.llm_client = llm_client


class HybridGuardrail(BaseGuardrail):
    """
    Base class for hybrid guardrails.

    Hybrid guardrails first use fast rule-based checks, and only
    invoke the LLM when confidence is below a threshold.
    """

    guardrail_type = "hybrid"

    def __init__(
        self,
        name: str,
        llm_client: Optional[Any] = None,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        llm_threshold: float = 0.7,
    ):
        super().__init__(name, enabled, source, config)
        self.llm_client = llm_client
        self.llm_threshold = llm_threshold

    @abstractmethod
    async def rule_check(self, data: Any) -> GuardrailCheckResult:
        """Fast rule-based check."""
        pass

    @abstractmethod
    async def llm_check(self, data: Any) -> GuardrailCheckResult:
        """LLM-based check for uncertain cases."""
        pass

    async def check(self, data: Any) -> GuardrailCheckResult:
        """
        Execute hybrid check: rule first, LLM if uncertain.
        """
        # First, try rule-based check
        rule_result = await self.rule_check(data)

        # If rule check is confident (high or low), return it
        if rule_result.confidence >= self.llm_threshold or rule_result.confidence <= (1 - self.llm_threshold):
            return rule_result

        # If uncertain and LLM is available, use LLM
        if self.llm_client is not None:
            llm_result = await self.llm_check(data)
            # Merge results, preferring LLM for uncertain cases
            llm_result.details["rule_result"] = rule_result.model_dump()
            return llm_result

        # No LLM available, return rule result
        return rule_result
