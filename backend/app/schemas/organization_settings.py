"""
Organization Settings Schemas

Pydantic models for organization-level configuration including
enforced guardrails, LLM defaults, security settings, and general preferences.
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Guardrails Configuration
# ============================================================================

class PIIDetectionConfig(BaseModel):
    enabled: bool = False
    action: Literal["block", "redact", "warn"] = "warn"


class PromptInjectionConfig(BaseModel):
    enabled: bool = False
    llm_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0, alias="llmThreshold")

    class Config:
        populate_by_name = True


class ToxicityConfig(BaseModel):
    enabled: bool = False
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class QueryLengthConfig(BaseModel):
    enabled: bool = False
    max_length: int = Field(default=4096, ge=1, alias="maxLength")

    class Config:
        populate_by_name = True


class ScoreThresholdConfig(BaseModel):
    enabled: bool = False
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, alias="minScore")

    class Config:
        populate_by_name = True


class TokenLimitConfig(BaseModel):
    enabled: bool = False
    max_tokens: int = Field(default=4000, ge=1, alias="maxTokens")

    class Config:
        populate_by_name = True


class DeduplicationConfig(BaseModel):
    enabled: bool = False
    threshold: float = Field(default=0.9, ge=0.0, le=1.0)


class SourceDiversityConfig(BaseModel):
    enabled: bool = False
    min_sources: int = Field(default=2, ge=1, alias="minSources")

    class Config:
        populate_by_name = True


class HallucinationDetectionConfig(BaseModel):
    enabled: bool = False
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class FactualGroundingConfig(BaseModel):
    enabled: bool = False
    min_score: float = Field(default=0.8, ge=0.0, le=1.0, alias="minScore")

    class Config:
        populate_by_name = True


class PIILeakageConfig(BaseModel):
    enabled: bool = False


class CitationVerificationConfig(BaseModel):
    enabled: bool = False


class InputGuardrailsConfig(BaseModel):
    pii_detection: Optional[PIIDetectionConfig] = Field(default=None, alias="piiDetection")
    prompt_injection: Optional[PromptInjectionConfig] = Field(default=None, alias="promptInjection")
    toxicity: Optional[ToxicityConfig] = None
    query_length: Optional[QueryLengthConfig] = Field(default=None, alias="queryLength")

    class Config:
        populate_by_name = True


class RetrievalGuardrailsConfig(BaseModel):
    score_threshold: Optional[ScoreThresholdConfig] = Field(default=None, alias="scoreThreshold")
    token_limit: Optional[TokenLimitConfig] = Field(default=None, alias="tokenLimit")
    deduplication: Optional[DeduplicationConfig] = None
    source_diversity: Optional[SourceDiversityConfig] = Field(default=None, alias="sourceDiversity")

    class Config:
        populate_by_name = True


class OutputGuardrailsConfig(BaseModel):
    hallucination_detection: Optional[HallucinationDetectionConfig] = Field(default=None, alias="hallucinationDetection")
    factual_grounding: Optional[FactualGroundingConfig] = Field(default=None, alias="factualGrounding")
    pii_leakage: Optional[PIILeakageConfig] = Field(default=None, alias="piiLeakage")
    citation_verification: Optional[CitationVerificationConfig] = Field(default=None, alias="citationVerification")

    class Config:
        populate_by_name = True


class GlobalGuardrailSettings(BaseModel):
    fail_action: Literal["block", "warn", "log_only"] = Field(default="warn", alias="failAction")
    llm_validation_threshold: float = Field(default=0.7, ge=0.0, le=1.0, alias="llmValidationThreshold")
    llm_credential_id: Optional[str] = Field(default=None, alias="llmCredentialId")

    class Config:
        populate_by_name = True


class EnforcedGuardrails(BaseModel):
    """Guardrails that CANNOT be disabled at workflow level"""
    input: Optional[InputGuardrailsConfig] = None
    retrieval: Optional[RetrievalGuardrailsConfig] = None
    output: Optional[OutputGuardrailsConfig] = None


class DefaultGuardrails(BaseModel):
    """Default values for workflow-level settings (can be overridden)"""
    input: Optional[InputGuardrailsConfig] = None
    retrieval: Optional[RetrievalGuardrailsConfig] = None
    output: Optional[OutputGuardrailsConfig] = None


class OrganizationGuardrailsConfig(BaseModel):
    enforced: EnforcedGuardrails = Field(default_factory=EnforcedGuardrails)
    defaults: DefaultGuardrails = Field(default_factory=DefaultGuardrails)
    global_settings: GlobalGuardrailSettings = Field(default_factory=GlobalGuardrailSettings, alias="global")

    class Config:
        populate_by_name = True


# ============================================================================
# LLM Defaults Configuration
# ============================================================================

class LLMDefaultsConfig(BaseModel):
    default_provider: Literal["openai", "anthropic", "azure", "google"] = Field(default="openai", alias="defaultProvider")
    default_model: str = Field(default="gpt-4", alias="defaultModel")
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0, alias="defaultTemperature")
    max_tokens_limit: int = Field(default=4096, ge=1, alias="maxTokensLimit")
    credential_id: Optional[str] = Field(default=None, alias="credentialId")
    allowed_providers: List[str] = Field(default_factory=lambda: ["openai", "anthropic", "azure", "google"], alias="allowedProviders")
    allowed_models: List[str] = Field(default_factory=list, alias="allowedModels")

    class Config:
        populate_by_name = True


# ============================================================================
# Security Configuration
# ============================================================================

class SecurityConfig(BaseModel):
    require_2fa: bool = Field(default=False, alias="require2FA")
    allowed_email_domains: List[str] = Field(default_factory=list, alias="allowedEmailDomains")
    session_timeout_minutes: int = Field(default=480, ge=5, alias="sessionTimeoutMinutes")
    ip_whitelist: List[str] = Field(default_factory=list, alias="ipWhitelist")
    enforce_password_policy: bool = Field(default=True, alias="enforcePasswordPolicy")
    min_password_length: int = Field(default=8, ge=6, alias="minPasswordLength")
    require_password_special_chars: bool = Field(default=True, alias="requirePasswordSpecialChars")

    class Config:
        populate_by_name = True


# ============================================================================
# General Configuration
# ============================================================================

class GeneralConfig(BaseModel):
    timezone: str = "UTC"
    date_format: str = Field(default="YYYY-MM-DD", alias="dateFormat")
    default_language: str = Field(default="en", alias="defaultLanguage")
    logo_url: Optional[str] = Field(default=None, alias="logoUrl")
    primary_color: Optional[str] = Field(default=None, alias="primaryColor")

    class Config:
        populate_by_name = True


# ============================================================================
# Complete Organization Settings
# ============================================================================

class OrganizationSettings(BaseModel):
    guardrails: OrganizationGuardrailsConfig = Field(default_factory=OrganizationGuardrailsConfig)
    llm_defaults: LLMDefaultsConfig = Field(default_factory=LLMDefaultsConfig, alias="llmDefaults")
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    general: GeneralConfig = Field(default_factory=GeneralConfig)

    class Config:
        populate_by_name = True


# ============================================================================
# API Request/Response Schemas
# ============================================================================

class OrganizationSettingsResponse(BaseModel):
    organization_id: str = Field(alias="organizationId")
    organization_name: str = Field(alias="organizationName")
    settings: OrganizationSettings
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    updated_by: Optional[str] = Field(default=None, alias="updatedBy")

    class Config:
        populate_by_name = True
        from_attributes = True


class OrganizationSettingsUpdate(BaseModel):
    guardrails: Optional[OrganizationGuardrailsConfig] = None
    llm_defaults: Optional[LLMDefaultsConfig] = Field(default=None, alias="llmDefaults")
    security: Optional[SecurityConfig] = None
    general: Optional[GeneralConfig] = None

    class Config:
        populate_by_name = True


class GuardrailsOnlyResponse(BaseModel):
    organization_id: str = Field(alias="organizationId")
    guardrails: OrganizationGuardrailsConfig
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class GuardrailsOnlyUpdate(BaseModel):
    enforced: Optional[EnforcedGuardrails] = None
    defaults: Optional[DefaultGuardrails] = None
    global_settings: Optional[GlobalGuardrailSettings] = Field(default=None, alias="global")

    class Config:
        populate_by_name = True


# ============================================================================
# Helper Functions
# ============================================================================

def merge_settings(existing: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge settings, preserving existing values not in updates.
    """
    result = existing.copy() if existing else {}

    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_settings(result[key], value)
        else:
            result[key] = value

    return result


def get_default_settings() -> Dict[str, Any]:
    """Return default organization settings as a dictionary."""
    return OrganizationSettings().model_dump(by_alias=True)
