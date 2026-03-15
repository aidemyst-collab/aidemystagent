/**
 * Organization Settings Types
 * Defines the structure for organization-level configuration including
 * enforced guardrails, LLM defaults, security settings, and general preferences.
 */

// ============================================================================
// Guardrails Configuration
// ============================================================================

export interface InputGuardrailConfig {
  piiDetection: {
    enabled: boolean;
    action: 'block' | 'redact' | 'warn';
  };
  promptInjection: {
    enabled: boolean;
    llmThreshold?: number;
  };
  toxicity: {
    enabled: boolean;
    threshold: number;
  };
  queryLength: {
    enabled: boolean;
    maxLength: number;
  };
}

export interface RetrievalGuardrailConfig {
  scoreThreshold: {
    enabled: boolean;
    minScore: number;
  };
  tokenLimit: {
    enabled: boolean;
    maxTokens: number;
  };
  deduplication: {
    enabled: boolean;
    threshold: number;
  };
  sourceDiversity: {
    enabled: boolean;
    minSources: number;
  };
}

export interface OutputGuardrailConfig {
  hallucinationDetection: {
    enabled: boolean;
    threshold: number;
  };
  factualGrounding: {
    enabled: boolean;
    minScore: number;
  };
  piiLeakage: {
    enabled: boolean;
  };
  citationVerification: {
    enabled: boolean;
  };
}

export interface GlobalGuardrailSettings {
  failAction: 'block' | 'warn' | 'log_only';
  llmValidationThreshold: number;
  llmCredentialId: string | null;
}

export interface OrganizationGuardrailsConfig {
  // Enforced guardrails - CANNOT be disabled at workflow level
  enforced: {
    input: Partial<InputGuardrailConfig>;
    retrieval: Partial<RetrievalGuardrailConfig>;
    output: Partial<OutputGuardrailConfig>;
  };
  // Default values for workflow-level settings (can be overridden)
  defaults: {
    input: Partial<InputGuardrailConfig>;
    retrieval: Partial<RetrievalGuardrailConfig>;
    output: Partial<OutputGuardrailConfig>;
  };
  // Global settings
  global: GlobalGuardrailSettings;
}

// ============================================================================
// LLM Defaults Configuration
// ============================================================================

export type LLMProvider = 'openai' | 'anthropic' | 'azure' | 'google';

export interface LLMDefaultsConfig {
  defaultProvider: LLMProvider;
  defaultModel: string;
  defaultTemperature: number;
  maxTokensLimit: number;
  credentialId: string | null;
  allowedProviders: LLMProvider[];
  allowedModels: string[];
}

// ============================================================================
// Security Configuration
// ============================================================================

export interface SecurityConfig {
  require2FA: boolean;
  allowedEmailDomains: string[];
  sessionTimeoutMinutes: number;
  ipWhitelist: string[];
  enforcePasswordPolicy: boolean;
  minPasswordLength: number;
  requirePasswordSpecialChars: boolean;
}

// ============================================================================
// General Configuration
// ============================================================================

export interface GeneralConfig {
  timezone: string;
  dateFormat: string;
  defaultLanguage: string;
  logoUrl: string | null;
  primaryColor: string | null;
}

// ============================================================================
// Complete Organization Settings
// ============================================================================

export interface OrganizationSettings {
  guardrails: OrganizationGuardrailsConfig;
  llmDefaults: LLMDefaultsConfig;
  security: SecurityConfig;
  general: GeneralConfig;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface OrganizationSettingsResponse {
  organizationId: string;
  organizationName: string;
  settings: OrganizationSettings;
  updatedAt: string;
  updatedBy: string | null;
}

export interface OrganizationSettingsUpdate {
  guardrails?: Partial<OrganizationGuardrailsConfig>;
  llmDefaults?: Partial<LLMDefaultsConfig>;
  security?: Partial<SecurityConfig>;
  general?: Partial<GeneralConfig>;
}

// ============================================================================
// Default Values
// ============================================================================

export const DEFAULT_GUARDRAILS_CONFIG: OrganizationGuardrailsConfig = {
  enforced: {
    input: {},
    retrieval: {},
    output: {},
  },
  defaults: {
    input: {
      piiDetection: { enabled: false, action: 'warn' },
      promptInjection: { enabled: false, llmThreshold: 0.7 },
      toxicity: { enabled: false, threshold: 0.8 },
      queryLength: { enabled: false, maxLength: 4096 },
    },
    retrieval: {
      scoreThreshold: { enabled: false, minScore: 0.5 },
      tokenLimit: { enabled: false, maxTokens: 4000 },
      deduplication: { enabled: false, threshold: 0.9 },
      sourceDiversity: { enabled: false, minSources: 2 },
    },
    output: {
      hallucinationDetection: { enabled: false, threshold: 0.7 },
      factualGrounding: { enabled: false, minScore: 0.8 },
      piiLeakage: { enabled: false },
      citationVerification: { enabled: false },
    },
  },
  global: {
    failAction: 'warn',
    llmValidationThreshold: 0.7,
    llmCredentialId: null,
  },
};

export const DEFAULT_LLM_DEFAULTS_CONFIG: LLMDefaultsConfig = {
  defaultProvider: 'openai',
  defaultModel: 'gpt-4',
  defaultTemperature: 0.7,
  maxTokensLimit: 4096,
  credentialId: null,
  allowedProviders: ['openai', 'anthropic', 'azure', 'google'],
  allowedModels: [],
};

export const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  require2FA: false,
  allowedEmailDomains: [],
  sessionTimeoutMinutes: 480, // 8 hours
  ipWhitelist: [],
  enforcePasswordPolicy: true,
  minPasswordLength: 8,
  requirePasswordSpecialChars: true,
};

export const DEFAULT_GENERAL_CONFIG: GeneralConfig = {
  timezone: 'UTC',
  dateFormat: 'YYYY-MM-DD',
  defaultLanguage: 'en',
  logoUrl: null,
  primaryColor: null,
};

export const DEFAULT_ORGANIZATION_SETTINGS: OrganizationSettings = {
  guardrails: DEFAULT_GUARDRAILS_CONFIG,
  llmDefaults: DEFAULT_LLM_DEFAULTS_CONFIG,
  security: DEFAULT_SECURITY_CONFIG,
  general: DEFAULT_GENERAL_CONFIG,
};

// ============================================================================
// Type Guards
// ============================================================================

export function isOrganizationSettings(obj: unknown): obj is OrganizationSettings {
  if (typeof obj !== 'object' || obj === null) return false;
  const settings = obj as OrganizationSettings;
  return (
    typeof settings.guardrails === 'object' &&
    typeof settings.llmDefaults === 'object' &&
    typeof settings.security === 'object' &&
    typeof settings.general === 'object'
  );
}
