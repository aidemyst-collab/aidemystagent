# Voice Provider Integration Guide

AgentStudio Voice Integration Documentation

## Supported Providers

Only two providers are supported:

1. Twilio - Global coverage
2. Etisalat CPaaS (e&) - UAE/MENA coverage

---

## 1. Twilio

### Overview

- Website: https://www.twilio.com
- Docs: https://www.twilio.com/docs/voice
- Coverage: Global (190+ countries)
- Format: TwiML (XML)

### Credentials

```json
{
  "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "auth_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "phone_number": "+1234567890"
}
```

### Setup Steps

1. Create Twilio account at console.twilio.com
2. Get Account SID and Auth Token
3. Buy a phone number
4. Configure webhook URL in Phone Numbers settings
5. Add credential in AgentStudio Credentials page

### Webhook Configuration

In Twilio Console:
- Go to Phone Numbers > Manage > Active Numbers
- Select your number
- Set "A Call Comes In" to Webhook
- URL: https://your-domain.com/api/v1/voice/webhook/incoming/{deployment_id}?api_key={api_key}
- Method: POST

### TwiML Responses

Greeting with Record:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! How can I help you?</Say>
    <Record maxLength="60" action="/webhook/recording" playBeep="true"/>
</Response>
```

Play Audio:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>https://example.com/audio/response.mp3</Play>
</Response>
```

Hangup:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Goodbye!</Say>
    <Hangup/>
</Response>
```

### Provider Implementation

```python
class TwilioProvider(VoiceProvider):
    provider_name = "twilio"

    def __init__(self, credentials):
        self.account_sid = credentials["account_sid"]
        self.auth_token = credentials["auth_token"]

    def get_content_type(self):
        return "application/xml"

    async def fetch_recording(self, url):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{url}.mp3",
                auth=(self.account_sid, self.auth_token)
            )
            return response.content
```

---

## 2. Etisalat CPaaS (e&)

### Overview

- Platform: engageX Nexus
- Website: https://www.eand.com
- Coverage: UAE, MENA region
- Format: JSON
- TRA Compliance: Built-in

### Benefits for UAE

- Native carrier integration
- TRA compliant out of the box
- Local data residency
- Better delivery rates
- Native Arabic support
- Local technical support

### Credentials

```json
{
  "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "api_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "account_id": "xxxxxxxxxx",
  "sender_id": "COMPANY_NAME",
  "webhook_secret": "xxxxxxxxxxxxxxxx"
}
```

### How to Get Access

1. Contact e& Enterprise: https://www.eand.com/en/business.html
2. Sign enterprise agreement
3. Get access to engageX Nexus
4. Receive API credentials
5. Register Sender ID with TRA

### Webhook Configuration

In engageX Nexus:
- Navigate to Voice > Webhooks
- URL: https://your-domain.com/api/v1/voice/webhook/incoming/{deployment_id}?api_key={api_key}
- Method: POST
- Events: call.received, recording.completed

### JSON Responses

Greeting with Record:

```json
{
  "actions": [
    {
      "action": "say",
      "text": "Hello! How can I help you?",
      "language": "en-US"
    },
    {
      "action": "record",
      "max_duration": 60,
      "beep": true,
      "callback_url": "https://example.com/webhook/recording"
    }
  ]
}
```

Play Audio:

```json
{
  "actions": [
    {
      "action": "play",
      "url": "https://example.com/audio/response.mp3"
    }
  ]
}
```

Hangup:

```json
{
  "actions": [
    {"action": "say", "text": "Goodbye!"},
    {"action": "hangup"}
  ]
}
```

Arabic Support:

```json
{
  "actions": [
    {
      "action": "say",
      "text": "مرحبا! كيف يمكنني مساعدتك؟",
      "language": "ar-AE"
    }
  ]
}
```

### Provider Implementation

```python
class EtisalatProvider(VoiceProvider):
    provider_name = "etisalat"

    def __init__(self, credentials):
        self.api_key = credentials["api_key"]
        self.account_id = credentials["account_id"]

    def get_content_type(self):
        return "application/json"

    async def fetch_recording(self, url):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.content
```

---

## Voice Nodes

### VOICE_INPUT Node

#### Configuration Schema

```typescript
interface VoiceInputConfig {
  provider: 'twilio' | 'etisalat';
  credentialId: string;
  greeting: string;
  language: string;
  maxDuration: number;
  silenceTimeout: number;
  playBeep: boolean;
  trimSilence: boolean;
  audioFormat: 'wav' | 'mp3' | 'mulaw';
}
```

#### Output Schema

```typescript
interface VoiceInputOutput {
  audio_data: string;    // Base64 encoded
  audio_format: string;
  audio_duration: number;
  caller_id: string;
  call_sid: string;
  provider: string;
  session_id: string;
}
```

#### Frontend Component

File: `frontend/src/components/AgentBuilder/nodes/VoiceInputNode.tsx`

```tsx
import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Form, Select, Input, InputNumber, Switch, Collapse } from 'antd';
import { PhoneOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';

const PROVIDERS = [
  { value: 'twilio', label: 'Twilio' },
  { value: 'etisalat', label: 'Etisalat CPaaS (e&)' },
];

const LANGUAGES = [
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'ar-AE', label: 'Arabic (UAE)' },
  { value: 'ar-SA', label: 'Arabic (Saudi)' },
  { value: 'hi-IN', label: 'Hindi' },
];

interface VoiceInputNodeData {
  provider?: string;
  credentialId?: string;
  greeting?: string;
  language?: string;
  maxDuration?: number;
  silenceTimeout?: number;
  playBeep?: boolean;
  trimSilence?: boolean;
  onChange?: (field: string, value: any) => void;
}

export const VoiceInputNode: React.FC<NodeProps<VoiceInputNodeData>> = ({
  data,
  selected
}) => {
  const handleChange = (field: string, value: any) => {
    data.onChange?.(field, value);
  };

  return (
    <BaseNode
      title="Voice Input"
      icon={<PhoneOutlined />}
      selected={selected}
      color="#52c41a"
      nodeType="VOICE_INPUT"
    >
      <Form layout="vertical" size="small">
        <Form.Item label="Provider" required>
          <Select
            value={data.provider || 'twilio'}
            options={PROVIDERS}
            onChange={(v) => handleChange('provider', v)}
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item label="Credential" required>
          <Select
            value={data.credentialId}
            placeholder="Select voice credential"
            onChange={(v) => handleChange('credentialId', v)}
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item label="Greeting Message">
          <Input.TextArea
            value={data.greeting}
            placeholder="Hello! How can I help you today?"
            rows={2}
            onChange={(e) => handleChange('greeting', e.target.value)}
          />
        </Form.Item>

        <Form.Item label="Language">
          <Select
            value={data.language || 'en-US'}
            options={LANGUAGES}
            onChange={(v) => handleChange('language', v)}
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Collapse ghost size="small">
          <Collapse.Panel header="Recording Settings" key="recording">
            <Form.Item label="Max Duration (seconds)">
              <InputNumber
                value={data.maxDuration || 60}
                min={5}
                max={300}
                onChange={(v) => handleChange('maxDuration', v)}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item label="Silence Timeout (seconds)">
              <InputNumber
                value={data.silenceTimeout || 3}
                min={1}
                max={10}
                onChange={(v) => handleChange('silenceTimeout', v)}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item label="Play Beep">
              <Switch
                checked={data.playBeep ?? true}
                onChange={(v) => handleChange('playBeep', v)}
              />
            </Form.Item>

            <Form.Item label="Trim Silence">
              <Switch
                checked={data.trimSilence ?? true}
                onChange={(v) => handleChange('trimSilence', v)}
              />
            </Form.Item>
          </Collapse.Panel>
        </Collapse>
      </Form>

      <Handle
        type="source"
        position={Position.Right}
        id="audio_data"
        style={{ background: '#52c41a' }}
      />
    </BaseNode>
  );
};

export default VoiceInputNode;
```

#### Zod Validation Schema

File: `frontend/src/types/nodeSchemas.ts`

```typescript
import { z } from 'zod';

export const VoiceInputSchema = z.object({
  provider: z.enum(['twilio', 'etisalat']),
  credentialId: z.string().uuid('Select a valid credential'),
  greeting: z.string().min(1, 'Greeting is required').max(500),
  language: z.string().default('en-US'),
  maxDuration: z.number().min(5).max(300).default(60),
  silenceTimeout: z.number().min(1).max(10).default(3),
  playBeep: z.boolean().default(true),
  trimSilence: z.boolean().default(true),
  audioFormat: z.enum(['wav', 'mp3', 'mulaw']).default('mp3'),
});

export type VoiceInputConfig = z.infer<typeof VoiceInputSchema>;
```

---

### VOICE_OUTPUT Node

#### Configuration Schema

```typescript
interface VoiceOutputConfig {
  inputField: string;
  audioFormat: 'mp3' | 'wav' | 'mulaw';
  afterResponse: 'hangup' | 'continue' | 'transfer';
  transferTo?: string;
  fallbackMessage?: string;
  fallbackVoice?: string;
  loop: number;
}
```

#### Input Schema

```typescript
interface VoiceOutputInput {
  audio_data: string;    // Base64 encoded audio
  audio_format: string;
  text_fallback?: string;
  session_id: string;
}
```

#### Frontend Component

File: `frontend/src/components/AgentBuilder/nodes/VoiceOutputNode.tsx`

```tsx
import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Form, Select, Input, Radio, InputNumber } from 'antd';
import { SoundOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';

const AUDIO_FORMATS = [
  { value: 'mp3', label: 'MP3' },
  { value: 'wav', label: 'WAV' },
  { value: 'mulaw', label: 'mulaw (Twilio)' },
];

interface VoiceOutputNodeData {
  inputField?: string;
  audioFormat?: string;
  afterResponse?: string;
  transferTo?: string;
  fallbackMessage?: string;
  loop?: number;
  onChange?: (field: string, value: any) => void;
}

export const VoiceOutputNode: React.FC<NodeProps<VoiceOutputNodeData>> = ({
  data,
  selected
}) => {
  const handleChange = (field: string, value: any) => {
    data.onChange?.(field, value);
  };

  return (
    <BaseNode
      title="Voice Output"
      icon={<SoundOutlined />}
      selected={selected}
      color="#1890ff"
      nodeType="VOICE_OUTPUT"
    >
      <Handle
        type="target"
        position={Position.Left}
        id="audio_data"
        style={{ background: '#1890ff' }}
      />

      <Form layout="vertical" size="small">
        <Form.Item label="Audio Input Field">
          <Select
            value={data.inputField || 'audio_data'}
            onChange={(v) => handleChange('inputField', v)}
            style={{ width: '100%' }}
          >
            <Select.Option value="audio_data">audio_data</Select.Option>
            <Select.Option value="output_audio">output_audio</Select.Option>
            <Select.Option value="tts_audio">tts_audio</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item label="Audio Format">
          <Select
            value={data.audioFormat || 'mp3'}
            options={AUDIO_FORMATS}
            onChange={(v) => handleChange('audioFormat', v)}
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item label="After Playing Response">
          <Radio.Group
            value={data.afterResponse || 'continue'}
            onChange={(e) => handleChange('afterResponse', e.target.value)}
          >
            <Radio value="hangup" style={{ display: 'block' }}>
              Hangup call
            </Radio>
            <Radio value="continue" style={{ display: 'block' }}>
              Continue conversation
            </Radio>
            <Radio value="transfer" style={{ display: 'block' }}>
              Transfer call
            </Radio>
          </Radio.Group>
        </Form.Item>

        {data.afterResponse === 'transfer' && (
          <Form.Item label="Transfer To">
            <Input
              value={data.transferTo}
              placeholder="+1234567890"
              onChange={(e) => handleChange('transferTo', e.target.value)}
            />
          </Form.Item>
        )}

        <Form.Item label="Fallback Message">
          <Input.TextArea
            value={data.fallbackMessage}
            placeholder="Sorry, I couldn't process that."
            rows={2}
            onChange={(e) => handleChange('fallbackMessage', e.target.value)}
          />
        </Form.Item>

        <Form.Item label="Loop Count">
          <InputNumber
            value={data.loop || 1}
            min={1}
            max={5}
            onChange={(v) => handleChange('loop', v)}
            style={{ width: '100%' }}
          />
        </Form.Item>
      </Form>
    </BaseNode>
  );
};

export default VoiceOutputNode;
```

#### Zod Validation Schema

```typescript
export const VoiceOutputSchema = z.object({
  inputField: z.string().default('audio_data'),
  audioFormat: z.enum(['wav', 'mp3', 'mulaw']).default('mp3'),
  afterResponse: z.enum(['hangup', 'continue', 'transfer']).default('continue'),
  transferTo: z.string().optional(),
  fallbackMessage: z.string().optional(),
  fallbackVoice: z.string().optional(),
  loop: z.number().min(1).max(5).default(1),
});

export type VoiceOutputConfig = z.infer<typeof VoiceOutputSchema>;
```

---

### Register Nodes

File: `frontend/src/components/AgentBuilder/nodes/index.ts`

```typescript
import { VoiceInputNode } from './VoiceInputNode';
import { VoiceOutputNode } from './VoiceOutputNode';
// ... other imports

export const nodeTypes = {
  // ... existing nodes
  VOICE_INPUT: VoiceInputNode,
  VOICE_OUTPUT: VoiceOutputNode,
};

export { VoiceInputNode, VoiceOutputNode };
```

---

### Add to Node Library

File: `frontend/src/components/AgentBuilder/NodeLibrary.tsx`

Add to the nodes array:

```typescript
const nodeCategories = [
  // ... existing categories
  {
    name: 'Voice',
    icon: <PhoneOutlined />,
    nodes: [
      {
        type: 'VOICE_INPUT',
        label: 'Voice Input',
        description: 'Receive incoming voice calls',
        icon: <PhoneOutlined />,
        color: '#52c41a',
      },
      {
        type: 'VOICE_OUTPUT',
        label: 'Voice Output',
        description: 'Play audio response to caller',
        icon: <SoundOutlined />,
        color: '#1890ff',
      },
    ],
  },
];
```

---

### Backend Node Handlers

File: `backend/app/services/langgraph_engine.py`

Add handlers for voice nodes:

```python
async def handle_voice_input(self, state: dict, node_config: dict) -> dict:
    """
    VOICE_INPUT node handler.
    This node is triggered by the webhook, not during normal execution.
    It receives audio from the voice provider webhook.
    """
    # Audio data comes from webhook, stored in state
    audio_data = state.get("audio_data")
    caller_id = state.get("caller_id")
    session_id = state.get("session_id")

    return {
        **state,
        "voice_input": {
            "audio_data": audio_data,
            "caller_id": caller_id,
            "session_id": session_id,
            "provider": node_config.get("provider", "twilio"),
        }
    }


async def handle_voice_output(self, state: dict, node_config: dict) -> dict:
    """
    VOICE_OUTPUT node handler.
    Prepares audio response to be played back to caller.
    """
    input_field = node_config.get("inputField", "audio_data")
    audio_data = state.get(input_field)

    if not audio_data:
        # Use fallback message if no audio
        fallback = node_config.get("fallbackMessage", "Sorry, no response available.")
        return {
            **state,
            "voice_output": {
                "type": "text",
                "text": fallback,
                "action": node_config.get("afterResponse", "hangup"),
            }
        }

    return {
        **state,
        "voice_output": {
            "type": "audio",
            "audio_data": audio_data,
            "audio_format": node_config.get("audioFormat", "mp3"),
            "action": node_config.get("afterResponse", "hangup"),
            "transfer_to": node_config.get("transferTo"),
            "loop": node_config.get("loop", 1),
        }
    }
```

Add to node type handlers:

```python
NODE_HANDLERS = {
    # ... existing handlers
    "VOICE_INPUT": handle_voice_input,
    "VOICE_OUTPUT": handle_voice_output,
}
```

---

### Example Workflow

A complete voice workflow:

```
VOICE_INPUT -> AUDIO_TO_TEXT -> LLM_AGENT -> TEXT_TO_AUDIO -> VOICE_OUTPUT
     |                                                              |
     |                                                              |
     +--- Incoming call audio                    Response audio ----+
```

Workflow JSON:

```json
{
  "nodes": [
    {
      "id": "voice_in_1",
      "type": "VOICE_INPUT",
      "data": {
        "provider": "twilio",
        "credentialId": "cred-uuid",
        "greeting": "Hello! How can I help you?",
        "language": "en-US",
        "maxDuration": 60
      }
    },
    {
      "id": "stt_1",
      "type": "AUDIO_TO_TEXT",
      "data": {
        "provider": "openai_whisper",
        "language": "en"
      }
    },
    {
      "id": "llm_1",
      "type": "LLM_AGENT",
      "data": {
        "model": "gpt-4",
        "systemPrompt": "You are a helpful voice assistant."
      }
    },
    {
      "id": "tts_1",
      "type": "TEXT_TO_AUDIO",
      "data": {
        "provider": "openai_tts",
        "voice": "alloy"
      }
    },
    {
      "id": "voice_out_1",
      "type": "VOICE_OUTPUT",
      "data": {
        "inputField": "audio_data",
        "afterResponse": "continue",
        "fallbackMessage": "Sorry, I didn't understand."
      }
    }
  ],
  "edges": [
    {"source": "voice_in_1", "target": "stt_1"},
    {"source": "stt_1", "target": "llm_1"},
    {"source": "llm_1", "target": "tts_1"},
    {"source": "tts_1", "target": "voice_out_1"}
  ]
}
```

---

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| POST /api/v1/voice/webhook/incoming/{id} | Handle incoming calls |
| POST /api/v1/voice/webhook/recording/{id} | Handle recording complete |
| GET /api/v1/voice/audio/{audio_id} | Serve response audio |

---

## Database Schema

```sql
CREATE TABLE voice_sessions (
    id UUID PRIMARY KEY,
    deployment_id UUID NOT NULL,
    call_id VARCHAR(255) NOT NULL,
    caller_id VARCHAR(50),
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('twilio', 'etisalat')),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE voice_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    audio_url VARCHAR(500),
    transcription TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## File Structure

```
backend/app/services/voice_providers/
├── __init__.py
├── base.py
├── twilio_provider.py
└── etisalat_provider.py

frontend/src/components/AgentBuilder/nodes/
├── VoiceInputNode.tsx
└── VoiceOutputNode.tsx
```

---

## Provider Factory

```python
PROVIDERS = {
    "twilio": TwilioProvider,
    "etisalat": EtisalatProvider,
}

def get_voice_provider(name, credentials):
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Use: twilio, etisalat")
    return PROVIDERS[name](credentials)
```

---

## Security

1. Always use HTTPS for webhooks
2. Validate Twilio signatures
3. Validate Etisalat webhook secrets
4. Store audio temporarily (5-10 min TTL)
5. Encrypt credentials at rest

---

## UAE Compliance

| Requirement | Details |
|-------------|---------|
| Sender ID | Must be TRA approved |
| Content | No political/religious/gambling |
| Consent | Opt-in required for marketing |
| Data | Store in UAE for local apps |
| Penalty | Up to 400,000 AED per violation |

### Provider Comparison for UAE

| Aspect | Twilio | Etisalat |
|--------|--------|----------|
| TRA Compliance | Manual | Built-in |
| Data Residency | International | UAE |
| Arabic Support | Limited | Native |
| Recommended | Global apps | UAE apps |

---

## Testing

Twilio test:

```bash
curl -X POST "http://localhost:8000/api/v1/voice/webhook/incoming/{id}?api_key={key}" \
  -d "CallSid=CA123&From=+1234567890&To=+0987654321"
```

Etisalat test:

```bash
curl -X POST "http://localhost:8000/api/v1/voice/webhook/incoming/{id}?api_key={key}" \
  -H "Content-Type: application/json" \
  -d '{"event":"call.received","call_id":"abc-123","from":"+971501234567"}'
```

---

## Roadmap

Phase 1:
- Twilio provider
- Etisalat provider
- Voice nodes UI
- Webhook endpoints

Phase 2:
- Multi-turn conversations
- Session analytics
- DTMF handling

Phase 3:
- SMS nodes
- WhatsApp integration
- Call transfer

---

Document Version: 1.0
Supported Providers: Twilio, Etisalat CPaaS
