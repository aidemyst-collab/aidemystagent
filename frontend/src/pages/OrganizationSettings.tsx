/**
 * Organization Settings Page
 *
 * Comprehensive settings management for organizations including:
 * - Guardrails (enforced and defaults)
 * - LLM Defaults
 * - Security
 * - General preferences
 */

import { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Switch,
  InputNumber,
  Select,
  Input,
  Button,
  Space,
  Typography,
  Divider,
  Spin,
  Alert,
  Collapse,
  Tag,
  Tooltip,
} from 'antd';
import {
  SafetyCertificateOutlined,
  RobotOutlined,
  LockOutlined,
  SettingOutlined,
  SaveOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  useCurrentOrganizationSettings,
  useUpdateCurrentSettings,
} from '../features/organization/useOrganizationSettings';
import { credentialService } from '../features/credentials/credentialService';
import type {
  OrganizationSettings,
  OrganizationSettingsUpdate,
  InputGuardrailConfig,
  RetrievalGuardrailConfig,
  OutputGuardrailConfig,
  LLMDefaultsConfig,
  SecurityConfig,
  GeneralConfig,
  DEFAULT_ORGANIZATION_SETTINGS,
} from '../types/organizationSettings';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

// ============================================================================
// Guardrails Tab
// ============================================================================

interface GuardrailsTabProps {
  settings: OrganizationSettings;
  onUpdate: (updates: OrganizationSettingsUpdate) => void;
  isUpdating: boolean;
  credentials: Array<{ id: string; name: string; type: string }>;
}

const GuardrailsTab: React.FC<GuardrailsTabProps> = ({
  settings,
  onUpdate,
  isUpdating,
  credentials,
}) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (settings?.guardrails) {
      form.setFieldsValue({
        // Enforced Input
        enforcedPiiDetection: settings.guardrails.enforced?.input?.piiDetection?.enabled ?? false,
        enforcedPiiAction: settings.guardrails.enforced?.input?.piiDetection?.action ?? 'warn',
        enforcedPromptInjection: settings.guardrails.enforced?.input?.promptInjection?.enabled ?? false,
        enforcedToxicity: settings.guardrails.enforced?.input?.toxicity?.enabled ?? false,
        enforcedToxicityThreshold: settings.guardrails.enforced?.input?.toxicity?.threshold ?? 0.8,
        enforcedQueryLength: settings.guardrails.enforced?.input?.queryLength?.enabled ?? false,
        enforcedQueryLengthMax: settings.guardrails.enforced?.input?.queryLength?.maxLength ?? 4096,

        // Enforced Retrieval
        enforcedScoreThreshold: settings.guardrails.enforced?.retrieval?.scoreThreshold?.enabled ?? false,
        enforcedScoreMin: settings.guardrails.enforced?.retrieval?.scoreThreshold?.minScore ?? 0.5,
        enforcedTokenLimit: settings.guardrails.enforced?.retrieval?.tokenLimit?.enabled ?? false,
        enforcedTokenMax: settings.guardrails.enforced?.retrieval?.tokenLimit?.maxTokens ?? 4000,
        enforcedDeduplication: settings.guardrails.enforced?.retrieval?.deduplication?.enabled ?? false,
        enforcedDeduplicationThreshold: settings.guardrails.enforced?.retrieval?.deduplication?.threshold ?? 0.9,
        enforcedSourceDiversity: settings.guardrails.enforced?.retrieval?.sourceDiversity?.enabled ?? false,
        enforcedMinSources: settings.guardrails.enforced?.retrieval?.sourceDiversity?.minSources ?? 2,

        // Enforced Output
        enforcedHallucination: settings.guardrails.enforced?.output?.hallucinationDetection?.enabled ?? false,
        enforcedHallucinationThreshold: settings.guardrails.enforced?.output?.hallucinationDetection?.threshold ?? 0.7,
        enforcedPiiLeakage: settings.guardrails.enforced?.output?.piiLeakage?.enabled ?? false,
        enforcedFactualGrounding: settings.guardrails.enforced?.output?.factualGrounding?.enabled ?? false,
        enforcedFactualMinScore: settings.guardrails.enforced?.output?.factualGrounding?.minScore ?? 0.8,
        enforcedCitationVerification: settings.guardrails.enforced?.output?.citationVerification?.enabled ?? false,

        // Global
        failAction: settings.guardrails.global?.failAction ?? 'warn',
        llmValidationThreshold: settings.guardrails.global?.llmValidationThreshold ?? 0.7,
        llmCredentialId: settings.guardrails.global?.llmCredentialId ?? null,
      });
    }
  }, [settings, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      const update: OrganizationSettingsUpdate = {
        guardrails: {
          enforced: {
            input: {
              piiDetection: values.enforcedPiiDetection
                ? { enabled: true, action: values.enforcedPiiAction }
                : undefined,
              promptInjection: values.enforcedPromptInjection
                ? { enabled: true }
                : undefined,
              toxicity: values.enforcedToxicity
                ? { enabled: true, threshold: values.enforcedToxicityThreshold }
                : undefined,
              queryLength: values.enforcedQueryLength
                ? { enabled: true, maxLength: values.enforcedQueryLengthMax }
                : undefined,
            },
            retrieval: {
              scoreThreshold: values.enforcedScoreThreshold
                ? { enabled: true, minScore: values.enforcedScoreMin }
                : undefined,
              tokenLimit: values.enforcedTokenLimit
                ? { enabled: true, maxTokens: values.enforcedTokenMax }
                : undefined,
              deduplication: values.enforcedDeduplication
                ? { enabled: true, threshold: values.enforcedDeduplicationThreshold }
                : undefined,
              sourceDiversity: values.enforcedSourceDiversity
                ? { enabled: true, minSources: values.enforcedMinSources }
                : undefined,
            },
            output: {
              hallucinationDetection: values.enforcedHallucination
                ? { enabled: true, threshold: values.enforcedHallucinationThreshold }
                : undefined,
              piiLeakage: values.enforcedPiiLeakage
                ? { enabled: true }
                : undefined,
              factualGrounding: values.enforcedFactualGrounding
                ? { enabled: true, minScore: values.enforcedFactualMinScore }
                : undefined,
              citationVerification: values.enforcedCitationVerification
                ? { enabled: true }
                : undefined,
            },
          },
          defaults: settings.guardrails.defaults,
          global: {
            failAction: values.failAction,
            llmValidationThreshold: values.llmValidationThreshold,
            llmCredentialId: values.llmCredentialId,
          },
        },
      };
      onUpdate(update);
    });
  };

  const llmCredentialOptions = credentials
    .filter((c) => ['openai', 'anthropic', 'azure_openai'].includes(c.type))
    .map((c) => ({ value: c.id, label: c.name }));

  return (
    <Form form={form} layout="vertical">
      <Alert
        message="Enforced Guardrails"
        description="Guardrails enabled here CANNOT be disabled at the workflow level. Use this for organization-wide compliance requirements."
        type="info"
        showIcon
        icon={<ExclamationCircleOutlined />}
        className="mb-4"
      />

      <Collapse defaultActiveKey={['input', 'global']} ghost>
        <Panel
          header={
            <Space>
              <SafetyCertificateOutlined />
              <Text strong>Input Guardrails</Text>
              <Tag color="blue">Before RAG</Tag>
            </Space>
          }
          key="input"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card size="small" title="PII Detection">
              <Form.Item name="enforcedPiiDetection" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce PII Detection</Text>
              </Form.Item>
              <Form.Item name="enforcedPiiAction" label="Action" className="mb-0">
                <Select
                  options={[
                    { value: 'block', label: 'Block Request' },
                    { value: 'redact', label: 'Redact PII' },
                    { value: 'warn', label: 'Warn Only' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Prompt Injection">
              <Form.Item name="enforcedPromptInjection" valuePropName="checked" className="mb-0">
                <Switch /> <Text className="ml-2">Enforce Injection Detection</Text>
              </Form.Item>
              <Text type="secondary" className="text-xs">
                Detects attempts to override system instructions
              </Text>
            </Card>

            <Card size="small" title="Toxicity Filter">
              <Form.Item name="enforcedToxicity" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Toxicity Filter</Text>
              </Form.Item>
              <Form.Item name="enforcedToxicityThreshold" label="Threshold" className="mb-0">
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Card>

            <Card size="small" title="Query Length">
              <Form.Item name="enforcedQueryLength" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Query Length Limit</Text>
              </Form.Item>
              <Form.Item name="enforcedQueryLengthMax" label="Max Characters" className="mb-0">
                <InputNumber min={100} max={100000} style={{ width: '100%' }} />
              </Form.Item>
            </Card>
          </div>
        </Panel>

        <Panel
          header={
            <Space>
              <SafetyCertificateOutlined />
              <Text strong>Retrieval Guardrails</Text>
              <Tag color="purple">After RAG</Tag>
            </Space>
          }
          key="retrieval"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card size="small" title="Score Threshold">
              <Form.Item name="enforcedScoreThreshold" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Minimum Score</Text>
              </Form.Item>
              <Form.Item name="enforcedScoreMin" label="Min Score" className="mb-0">
                <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
              </Form.Item>
            </Card>

            <Card size="small" title="Token Limit">
              <Form.Item name="enforcedTokenLimit" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Token Limit</Text>
              </Form.Item>
              <Form.Item name="enforcedTokenMax" label="Max Tokens" className="mb-0">
                <InputNumber min={100} max={128000} style={{ width: '100%' }} />
              </Form.Item>
            </Card>

            <Card size="small" title="Chunk Deduplication">
              <Form.Item name="enforcedDeduplication" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Deduplication</Text>
              </Form.Item>
              <Form.Item name="enforcedDeduplicationThreshold" label="Similarity Threshold" className="mb-0">
                <InputNumber min={0.5} max={1} step={0.05} style={{ width: '100%' }} />
              </Form.Item>
              <Text type="secondary" className="text-xs">
                Removes duplicate chunks above similarity threshold
              </Text>
            </Card>

            <Card size="small" title="Source Diversity">
              <Form.Item name="enforcedSourceDiversity" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Source Diversity</Text>
              </Form.Item>
              <Form.Item name="enforcedMinSources" label="Min Sources" className="mb-0">
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
              <Text type="secondary" className="text-xs">
                Ensures chunks from multiple sources
              </Text>
            </Card>
          </div>
        </Panel>

        <Panel
          header={
            <Space>
              <SafetyCertificateOutlined />
              <Text strong>Output Guardrails</Text>
              <Tag color="green">After LLM</Tag>
            </Space>
          }
          key="output"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card size="small" title="Hallucination Detection">
              <Form.Item name="enforcedHallucination" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Hallucination Check</Text>
              </Form.Item>
              <Form.Item name="enforcedHallucinationThreshold" label="Threshold" className="mb-0">
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Card>

            <Card size="small" title="PII Leakage Prevention">
              <Form.Item name="enforcedPiiLeakage" valuePropName="checked" className="mb-0">
                <Switch /> <Text className="ml-2">Enforce PII Leakage Check</Text>
              </Form.Item>
              <Text type="secondary" className="text-xs">
                Prevents PII from appearing in responses
              </Text>
            </Card>

            <Card size="small" title="Factual Grounding">
              <Form.Item name="enforcedFactualGrounding" valuePropName="checked" className="mb-2">
                <Switch /> <Text className="ml-2">Enforce Factual Grounding</Text>
              </Form.Item>
              <Form.Item name="enforcedFactualMinScore" label="Min Score" className="mb-0">
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
              <Text type="secondary" className="text-xs">
                Verifies claims are grounded in context
              </Text>
            </Card>

            <Card size="small" title="Citation Verification">
              <Form.Item name="enforcedCitationVerification" valuePropName="checked" className="mb-0">
                <Switch /> <Text className="ml-2">Enforce Citation Verification</Text>
              </Form.Item>
              <Text type="secondary" className="text-xs">
                Validates citations match source documents
              </Text>
            </Card>
          </div>
        </Panel>

        <Panel
          header={
            <Space>
              <SettingOutlined />
              <Text strong>Global Settings</Text>
            </Space>
          }
          key="global"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Form.Item name="failAction" label="Fail Action">
              <Select
                options={[
                  { value: 'block', label: 'Block - Stop execution' },
                  { value: 'warn', label: 'Warn - Continue with warning' },
                  { value: 'log_only', label: 'Log Only - Silent logging' },
                ]}
              />
            </Form.Item>

            <Form.Item name="llmValidationThreshold" label="LLM Validation Threshold">
              <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="llmCredentialId" label="LLM Credential">
              <Select
                allowClear
                placeholder="Select credential for LLM validation"
                options={llmCredentialOptions}
              />
            </Form.Item>
          </div>
        </Panel>
      </Collapse>

      <Divider />

      <Button
        type="primary"
        icon={<SaveOutlined />}
        onClick={handleSave}
        loading={isUpdating}
      >
        Save Guardrails Settings
      </Button>
    </Form>
  );
};

// ============================================================================
// LLM Defaults Tab
// ============================================================================

interface LLMDefaultsTabProps {
  settings: OrganizationSettings;
  onUpdate: (updates: OrganizationSettingsUpdate) => void;
  isUpdating: boolean;
  credentials: Array<{ id: string; name: string; type: string }>;
}

const LLMDefaultsTab: React.FC<LLMDefaultsTabProps> = ({
  settings,
  onUpdate,
  isUpdating,
  credentials,
}) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (settings?.llmDefaults) {
      form.setFieldsValue(settings.llmDefaults);
    }
  }, [settings, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      onUpdate({ llmDefaults: values });
    });
  };

  const llmCredentialOptions = credentials
    .filter((c) => ['openai', 'anthropic', 'azure_openai'].includes(c.type))
    .map((c) => ({ value: c.id, label: c.name }));

  const modelOptions: Record<string, Array<{ value: string; label: string }>> = {
    openai: [
      { value: 'gpt-4', label: 'GPT-4' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    ],
    anthropic: [
      { value: 'claude-3-opus', label: 'Claude 3 Opus' },
      { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
      { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
      { value: 'claude-opus-4', label: 'Claude 4 Opus' },
    ],
    azure: [
      { value: 'gpt-4', label: 'Azure GPT-4' },
      { value: 'gpt-4-turbo', label: 'Azure GPT-4 Turbo' },
    ],
    google: [
      { value: 'gemini-pro', label: 'Gemini Pro' },
      { value: 'gemini-ultra', label: 'Gemini Ultra' },
    ],
  };

  const selectedProvider = Form.useWatch('defaultProvider', form);

  return (
    <Form form={form} layout="vertical">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Form.Item name="defaultProvider" label="Default Provider">
          <Select
            options={[
              { value: 'openai', label: 'OpenAI' },
              { value: 'anthropic', label: 'Anthropic' },
              { value: 'azure', label: 'Azure OpenAI' },
              { value: 'google', label: 'Google AI' },
            ]}
          />
        </Form.Item>

        <Form.Item name="defaultModel" label="Default Model">
          <Select options={modelOptions[selectedProvider] || modelOptions.openai} />
        </Form.Item>

        <Form.Item name="defaultTemperature" label="Default Temperature">
          <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="maxTokensLimit" label="Max Tokens Limit">
          <InputNumber min={100} max={128000} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="credentialId" label="Default Credential">
          <Select
            allowClear
            placeholder="Select default credential"
            options={llmCredentialOptions}
          />
        </Form.Item>

        <Form.Item
          name="allowedProviders"
          label={
            <Space>
              Allowed Providers
              <Tooltip title="Restrict which providers can be used in workflows">
                <InfoCircleOutlined />
              </Tooltip>
            </Space>
          }
        >
          <Select
            mode="multiple"
            options={[
              { value: 'openai', label: 'OpenAI' },
              { value: 'anthropic', label: 'Anthropic' },
              { value: 'azure', label: 'Azure OpenAI' },
              { value: 'google', label: 'Google AI' },
            ]}
          />
        </Form.Item>
      </div>

      <Divider />

      <Button
        type="primary"
        icon={<SaveOutlined />}
        onClick={handleSave}
        loading={isUpdating}
      >
        Save LLM Defaults
      </Button>
    </Form>
  );
};

// ============================================================================
// Security Tab
// ============================================================================

interface SecurityTabProps {
  settings: OrganizationSettings;
  onUpdate: (updates: OrganizationSettingsUpdate) => void;
  isUpdating: boolean;
}

const SecurityTab: React.FC<SecurityTabProps> = ({ settings, onUpdate, isUpdating }) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (settings?.security) {
      form.setFieldsValue(settings.security);
    }
  }, [settings, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      onUpdate({ security: values });
    });
  };

  return (
    <Form form={form} layout="vertical">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card size="small" title="Authentication">
          <Form.Item name="require2FA" valuePropName="checked" className="mb-2">
            <Switch /> <Text className="ml-2">Require Two-Factor Authentication</Text>
          </Form.Item>

          <Form.Item name="sessionTimeoutMinutes" label="Session Timeout (minutes)">
            <InputNumber min={5} max={1440} style={{ width: '100%' }} />
          </Form.Item>
        </Card>

        <Card size="small" title="Password Policy">
          <Form.Item name="enforcePasswordPolicy" valuePropName="checked" className="mb-2">
            <Switch /> <Text className="ml-2">Enforce Password Policy</Text>
          </Form.Item>

          <Form.Item name="minPasswordLength" label="Minimum Password Length">
            <InputNumber min={6} max={32} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="requirePasswordSpecialChars" valuePropName="checked" className="mb-0">
            <Switch /> <Text className="ml-2">Require Special Characters</Text>
          </Form.Item>
        </Card>

        <Card size="small" title="Email Restrictions">
          <Form.Item
            name="allowedEmailDomains"
            label="Allowed Email Domains"
            help="Leave empty to allow all domains"
          >
            <Select
              mode="tags"
              placeholder="e.g., company.com, partner.com"
              tokenSeparators={[',', ' ']}
            />
          </Form.Item>
        </Card>

        <Card size="small" title="IP Restrictions">
          <Form.Item
            name="ipWhitelist"
            label="IP Whitelist"
            help="Leave empty to allow all IPs"
          >
            <Select
              mode="tags"
              placeholder="e.g., 192.168.1.0/24"
              tokenSeparators={[',', ' ']}
            />
          </Form.Item>
        </Card>
      </div>

      <Divider />

      <Button
        type="primary"
        icon={<SaveOutlined />}
        onClick={handleSave}
        loading={isUpdating}
      >
        Save Security Settings
      </Button>
    </Form>
  );
};

// ============================================================================
// General Tab
// ============================================================================

interface GeneralTabProps {
  settings: OrganizationSettings;
  onUpdate: (updates: OrganizationSettingsUpdate) => void;
  isUpdating: boolean;
}

const GeneralTab: React.FC<GeneralTabProps> = ({ settings, onUpdate, isUpdating }) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (settings?.general) {
      form.setFieldsValue(settings.general);
    }
  }, [settings, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      onUpdate({ general: values });
    });
  };

  const timezones = [
    'UTC',
    'America/New_York',
    'America/Los_Angeles',
    'America/Chicago',
    'Europe/London',
    'Europe/Paris',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Asia/Dubai',
    'Australia/Sydney',
  ];

  return (
    <Form form={form} layout="vertical">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Form.Item name="timezone" label="Timezone">
          <Select
            showSearch
            options={timezones.map((tz) => ({ value: tz, label: tz }))}
          />
        </Form.Item>

        <Form.Item name="dateFormat" label="Date Format">
          <Select
            options={[
              { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2024-03-14)' },
              { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (03/14/2024)' },
              { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (14/03/2024)' },
              { value: 'DD MMM YYYY', label: 'DD MMM YYYY (14 Mar 2024)' },
            ]}
          />
        </Form.Item>

        <Form.Item name="defaultLanguage" label="Default Language">
          <Select
            options={[
              { value: 'en', label: 'English' },
              { value: 'es', label: 'Spanish' },
              { value: 'fr', label: 'French' },
              { value: 'de', label: 'German' },
              { value: 'ar', label: 'Arabic' },
              { value: 'zh', label: 'Chinese' },
              { value: 'ja', label: 'Japanese' },
            ]}
          />
        </Form.Item>

        <Form.Item name="logoUrl" label="Custom Logo URL">
          <Input placeholder="https://example.com/logo.png" />
        </Form.Item>

        <Form.Item name="primaryColor" label="Primary Brand Color">
          <Input type="color" style={{ width: 100, height: 40 }} />
        </Form.Item>
      </div>

      <Divider />

      <Button
        type="primary"
        icon={<SaveOutlined />}
        onClick={handleSave}
        loading={isUpdating}
      >
        Save General Settings
      </Button>
    </Form>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const OrganizationSettingsPage: React.FC = () => {
  const { data, isLoading, error } = useCurrentOrganizationSettings();
  const updateMutation = useUpdateCurrentSettings();
  const { data: credentialsData } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => credentialService.getCredentials(),
    staleTime: 5 * 60 * 1000,
  });

  const credentials = (credentialsData?.credentials || []).map((c) => ({
    id: c.id,
    name: c.name,
    type: c.provider,
  }));

  const handleUpdate = (updates: OrganizationSettingsUpdate) => {
    updateMutation.mutate(updates);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="Failed to load settings"
        description={error.message}
        showIcon
      />
    );
  }

  const settings = data?.settings;

  if (!settings) {
    return (
      <Alert
        type="warning"
        message="No settings found"
        description="Organization settings could not be loaded."
        showIcon
      />
    );
  }

  const tabItems = [
    {
      key: 'guardrails',
      label: (
        <Space>
          <SafetyCertificateOutlined />
          Guardrails
        </Space>
      ),
      children: (
        <GuardrailsTab
          settings={settings}
          onUpdate={handleUpdate}
          isUpdating={updateMutation.isPending}
          credentials={credentials}
        />
      ),
    },
    {
      key: 'llm',
      label: (
        <Space>
          <RobotOutlined />
          LLM Defaults
        </Space>
      ),
      children: (
        <LLMDefaultsTab
          settings={settings}
          onUpdate={handleUpdate}
          isUpdating={updateMutation.isPending}
          credentials={credentials}
        />
      ),
    },
    {
      key: 'security',
      label: (
        <Space>
          <LockOutlined />
          Security
        </Space>
      ),
      children: (
        <SecurityTab
          settings={settings}
          onUpdate={handleUpdate}
          isUpdating={updateMutation.isPending}
        />
      ),
    },
    {
      key: 'general',
      label: (
        <Space>
          <SettingOutlined />
          General
        </Space>
      ),
      children: (
        <GeneralTab
          settings={settings}
          onUpdate={handleUpdate}
          isUpdating={updateMutation.isPending}
        />
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <Title level={2}>Organization Settings</Title>
        <Paragraph type="secondary">
          Configure organization-wide settings including enforced guardrails, LLM defaults,
          security policies, and general preferences.
        </Paragraph>
        {data?.organizationName && (
          <Tag color="blue" className="mt-2">
            {data.organizationName}
          </Tag>
        )}
      </div>

      <Card>
        <Tabs items={tabItems} defaultActiveKey="guardrails" />
      </Card>
    </div>
  );
};

export default OrganizationSettingsPage;
