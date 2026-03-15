"""
Guardrails Service Module

Provides hybrid guardrails (rule-based + LLM) for RAG workflows:
- Input guardrails: Query validation before RAG
- Retrieval guardrails: Context quality validation after RAG
- Output guardrails: Response validation after LLM

Usage:
    from app.services.guardrails import GuardrailService

    service = await GuardrailService.create_with_org_merge(
        org_id="org-123",
        workflow_config=workflow_guardrails,
        db=db_session,
        llm_client=llm_client
    )

    input_result = await service.validate_input(query)
    retrieval_result = await service.validate_retrieval(chunks)
    output_result = await service.validate_output(response, context)
"""

from .base import (
    GuardrailResult,
    GuardrailViolation,
    GuardrailCheckResult,
    BaseGuardrail,
    RuleBasedGuardrail,
    LLMBasedGuardrail,
    HybridGuardrail,
)
from .guardrail_service import GuardrailService

__all__ = [
    "GuardrailResult",
    "GuardrailViolation",
    "GuardrailCheckResult",
    "BaseGuardrail",
    "RuleBasedGuardrail",
    "LLMBasedGuardrail",
    "HybridGuardrail",
    "GuardrailService",
]
