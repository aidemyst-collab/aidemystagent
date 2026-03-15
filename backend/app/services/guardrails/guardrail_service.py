"""
Guardrail Service

Orchestrates all guardrail checks and handles org/workflow configuration merging.
"""

import time
import copy
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .base import (
    GuardrailResult,
    GuardrailCheckResult,
    BaseGuardrail,
)
from .input_guardrails import (
    QueryLengthGuardrail,
    PIIDetectionGuardrail,
    PromptInjectionGuardrail,
    ToxicityGuardrail,
    QuerySanitizationGuardrail,
)
from .retrieval_guardrails import (
    ScoreThresholdGuardrail,
    TokenLimitGuardrail,
    ChunkDeduplicationGuardrail,
    SourceDiversityGuardrail,
)
from .output_guardrails import (
    HallucinationDetectionGuardrail,
    FactualGroundingGuardrail,
    PIILeakageGuardrail,
    CitationVerificationGuardrail,
)


class GuardrailService:
    """
    Orchestrates guardrail checks for RAG workflows.

    Handles:
    - Merging organization-enforced guardrails with workflow-level config
    - Running input, retrieval, and output guardrails
    - Aggregating results and tracking execution time
    """

    def __init__(
        self,
        org_config: Optional[Dict[str, Any]] = None,
        workflow_config: Optional[Dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize the guardrail service.

        Args:
            org_config: Organization-level guardrails config (enforced)
            workflow_config: Workflow-level guardrails config (additional)
            llm_client: LLM client for hybrid/LLM guardrails
        """
        self.org_config = org_config or {}
        self.workflow_config = workflow_config or {}
        self.llm_client = llm_client
        self.merged_config = self._merge_configs()

        # Initialize guardrails
        self._init_guardrails()

    def _merge_configs(self) -> Dict[str, Any]:
        """
        Merge org-enforced guardrails with workflow additions.

        Org guardrails CANNOT be disabled at workflow level.
        Workflow can ADD more guardrails or strengthen thresholds.
        """
        merged = {
            "input": {},
            "retrieval": {},
            "output": {},
            "global": {},
        }

        # Start with org-enforced config
        org_enforced = self.org_config.get("enforced", {})
        for category in ["input", "retrieval", "output"]:
            if category in org_enforced:
                for guardrail, config in (org_enforced[category] or {}).items():
                    if config and config.get("enabled"):
                        merged[category][guardrail] = {
                            **config,
                            "source": "org_enforced",
                        }

        # Add workflow config (cannot override org-enforced)
        for category in ["input", "retrieval", "output"]:
            workflow_category = self.workflow_config.get(category, {})
            for guardrail, config in (workflow_category or {}).items():
                if config and config.get("enabled"):
                    if guardrail not in merged[category]:
                        # New guardrail from workflow
                        merged[category][guardrail] = {
                            **config,
                            "source": "workflow",
                        }
                    else:
                        # Org-enforced exists - can only strengthen
                        org_threshold = merged[category][guardrail].get("threshold", 0)
                        workflow_threshold = config.get("threshold", 0)
                        if workflow_threshold > org_threshold:
                            merged[category][guardrail]["threshold"] = workflow_threshold

        # Global settings (org defaults, workflow can override some)
        org_global = self.org_config.get("global", {})
        workflow_global = self.workflow_config.get("global", {})

        merged["global"] = {
            "failAction": workflow_global.get("failAction") or org_global.get("failAction", "warn"),
            "llmValidationThreshold": org_global.get("llmValidationThreshold", 0.7),
            "llmCredentialId": workflow_global.get("llmCredentialId") or org_global.get("llmCredentialId"),
        }

        return merged

    def _init_guardrails(self) -> None:
        """Initialize guardrail instances based on merged config."""
        self.input_guardrails: List[BaseGuardrail] = []
        self.retrieval_guardrails: List[BaseGuardrail] = []
        self.output_guardrails: List[BaseGuardrail] = []

        # Input guardrails
        input_config = self.merged_config.get("input", {})

        if "queryLength" in input_config:
            self.input_guardrails.append(
                QueryLengthGuardrail(
                    enabled=True,
                    source=input_config["queryLength"].get("source", "workflow"),
                    config=input_config["queryLength"],
                )
            )

        if "piiDetection" in input_config:
            self.input_guardrails.append(
                PIIDetectionGuardrail(
                    enabled=True,
                    source=input_config["piiDetection"].get("source", "workflow"),
                    config=input_config["piiDetection"],
                )
            )

        if "promptInjection" in input_config:
            self.input_guardrails.append(
                PromptInjectionGuardrail(
                    llm_client=self.llm_client,
                    enabled=True,
                    source=input_config["promptInjection"].get("source", "workflow"),
                    config=input_config["promptInjection"],
                )
            )

        if "toxicity" in input_config:
            self.input_guardrails.append(
                ToxicityGuardrail(
                    llm_client=self.llm_client,
                    enabled=True,
                    source=input_config["toxicity"].get("source", "workflow"),
                    config=input_config["toxicity"],
                )
            )

        # Always add sanitization if any input guardrails are enabled
        if input_config:
            self.input_guardrails.append(
                QuerySanitizationGuardrail(enabled=True, source="system")
            )

        # Retrieval guardrails
        retrieval_config = self.merged_config.get("retrieval", {})

        if "scoreThreshold" in retrieval_config:
            self.retrieval_guardrails.append(
                ScoreThresholdGuardrail(
                    enabled=True,
                    source=retrieval_config["scoreThreshold"].get("source", "workflow"),
                    config=retrieval_config["scoreThreshold"],
                )
            )

        if "tokenLimit" in retrieval_config:
            self.retrieval_guardrails.append(
                TokenLimitGuardrail(
                    enabled=True,
                    source=retrieval_config["tokenLimit"].get("source", "workflow"),
                    config=retrieval_config["tokenLimit"],
                )
            )

        if "deduplication" in retrieval_config:
            self.retrieval_guardrails.append(
                ChunkDeduplicationGuardrail(
                    enabled=True,
                    source=retrieval_config["deduplication"].get("source", "workflow"),
                    config=retrieval_config["deduplication"],
                )
            )

        if "sourceDiversity" in retrieval_config:
            self.retrieval_guardrails.append(
                SourceDiversityGuardrail(
                    enabled=True,
                    source=retrieval_config["sourceDiversity"].get("source", "workflow"),
                    config=retrieval_config["sourceDiversity"],
                )
            )

        # Output guardrails
        output_config = self.merged_config.get("output", {})

        if "hallucinationDetection" in output_config:
            self.output_guardrails.append(
                HallucinationDetectionGuardrail(
                    llm_client=self.llm_client,
                    enabled=True,
                    source=output_config["hallucinationDetection"].get("source", "workflow"),
                    config=output_config["hallucinationDetection"],
                )
            )

        if "factualGrounding" in output_config:
            self.output_guardrails.append(
                FactualGroundingGuardrail(
                    llm_client=self.llm_client,
                    enabled=True,
                    source=output_config["factualGrounding"].get("source", "workflow"),
                    config=output_config["factualGrounding"],
                )
            )

        if "piiLeakage" in output_config:
            self.output_guardrails.append(
                PIILeakageGuardrail(
                    enabled=True,
                    source=output_config["piiLeakage"].get("source", "workflow"),
                    config=output_config["piiLeakage"],
                )
            )

        if "citationVerification" in output_config:
            self.output_guardrails.append(
                CitationVerificationGuardrail(
                    llm_client=self.llm_client,
                    enabled=True,
                    source=output_config["citationVerification"].get("source", "workflow"),
                    config=output_config["citationVerification"],
                )
            )

    async def validate_input(self, query: str) -> GuardrailResult:
        """
        Run all enabled input guardrails.

        Args:
            query: The user query to validate

        Returns:
            GuardrailResult with aggregated results
        """
        start_time = time.time()
        result = GuardrailResult(passed=True, confidence=1.0)

        for guardrail in self.input_guardrails:
            check_result = await guardrail.execute(query)
            result.add_check(check_result)

            # Handle violations
            if not check_result.passed:
                if check_result.details.get("violation"):
                    result.add_violation(
                        violation_type=check_result.details["violation"],
                        severity=check_result.details.get("max_severity", "medium"),
                        message=check_result.details.get("message", f"{guardrail.name} failed"),
                        details=check_result.details,
                    )

        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result

    async def validate_retrieval(
        self,
        chunks: List[Dict[str, Any]],
    ) -> GuardrailResult:
        """
        Run all enabled retrieval guardrails.

        Args:
            chunks: Retrieved chunks to validate

        Returns:
            GuardrailResult with aggregated results and filtered chunks
        """
        start_time = time.time()
        result = GuardrailResult(passed=True, confidence=1.0)
        current_chunks = chunks

        for guardrail in self.retrieval_guardrails:
            check_result = await guardrail.execute(current_chunks)
            result.add_check(check_result)

            # Update chunks if filtered
            if "filtered_chunks" in check_result.details:
                current_chunks = check_result.details["filtered_chunks"]

            # Handle violations
            if not check_result.passed:
                if check_result.details.get("violation"):
                    result.add_violation(
                        violation_type=check_result.details["violation"],
                        severity="medium",
                        message=check_result.details.get("message", f"{guardrail.name} failed"),
                        details=check_result.details,
                    )

        result.metadata["filtered_chunks"] = current_chunks
        result.metadata["original_count"] = len(chunks)
        result.metadata["final_count"] = len(current_chunks)
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result

    async def validate_output(
        self,
        response: str,
        context: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> GuardrailResult:
        """
        Run all enabled output guardrails.

        Args:
            response: The LLM response to validate
            context: The context provided to the LLM
            sources: Optional list of source documents

        Returns:
            GuardrailResult with aggregated results
        """
        start_time = time.time()
        result = GuardrailResult(passed=True, confidence=1.0)

        data = {
            "response": response,
            "context": context,
            "sources": sources or [],
        }

        for guardrail in self.output_guardrails:
            check_result = await guardrail.execute(data)
            result.add_check(check_result)

            # Handle violations
            if not check_result.passed:
                if check_result.details.get("violation"):
                    result.add_violation(
                        violation_type=check_result.details["violation"],
                        severity=check_result.details.get("max_severity", "medium"),
                        message=check_result.details.get("message", f"{guardrail.name} failed"),
                        details=check_result.details,
                    )

        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result

    def get_config_summary(self) -> Dict[str, Any]:
        """Return a summary of the current guardrail configuration."""
        return {
            "org_enforced": {
                "input": list((self.org_config.get("enforced", {}).get("input") or {}).keys()),
                "retrieval": list((self.org_config.get("enforced", {}).get("retrieval") or {}).keys()),
                "output": list((self.org_config.get("enforced", {}).get("output") or {}).keys()),
            },
            "workflow_additional": {
                "input": [g.name for g in self.input_guardrails if g.source == "workflow"],
                "retrieval": [g.name for g in self.retrieval_guardrails if g.source == "workflow"],
                "output": [g.name for g in self.output_guardrails if g.source == "workflow"],
            },
            "global": self.merged_config.get("global", {}),
        }

    @staticmethod
    async def create_with_org_merge(
        org_id: Optional[str],
        workflow_config: Dict[str, Any],
        db: Optional[AsyncSession],
        llm_client: Optional[Any] = None,
    ) -> "GuardrailService":
        """
        Factory method that fetches org settings and merges with workflow config.

        Args:
            org_id: Organization ID
            workflow_config: Workflow-level guardrail configuration
            db: Database session
            llm_client: LLM client for hybrid guardrails

        Returns:
            Configured GuardrailService instance
        """
        org_guardrails = {}

        if org_id and db:
            try:
                from app.models.user import Organization
                from sqlalchemy import select
                from uuid import UUID

                result = await db.execute(
                    select(Organization).where(Organization.id == UUID(org_id))
                )
                org = result.scalar_one_or_none()

                if org and org.settings:
                    org_guardrails = org.settings.get("guardrails", {})
            except Exception:
                # If we can't fetch org settings, proceed without them
                pass

        return GuardrailService(
            org_config=org_guardrails,
            workflow_config=workflow_config,
            llm_client=llm_client,
        )
