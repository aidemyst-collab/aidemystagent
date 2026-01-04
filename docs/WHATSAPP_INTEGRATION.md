# WhatsApp Business API Integration Guide

This document provides a comprehensive guide for integrating WhatsApp Business API (Meta Cloud API) into AgentStudio.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Implementation Plan](#implementation-plan)
5. [Backend Components](#backend-components)
6. [Frontend Components](#frontend-components)
7. [Webhook Security](#webhook-security)
8. [Message Types](#message-types)
9. [Session Management](#session-management)
10. [Testing](#testing)
11. [Production Checklist](#production-checklist)

---

## Overview

### Why WhatsApp Cloud API?

- **Meta-hosted**: No server infrastructure to manage
- **Future-proof**: On-Premises API sunsets October 23, 2025
- **Scalable**: Automatic scaling by Meta
- **Feature-rich**: Text, media, templates, interactive messages

### Comparison with Voice Integration

| Aspect | Voice (Twilio/Etisalat) | WhatsApp (Meta Cloud API) |
|--------|-------------------------|---------------------------|
| Message Type | Audio streams | Text, Media, Templates, Interactive |
| Webhook Verification | Signature-based | Token-based challenge/response |
| Session | Call duration | 24-hour customer service window |
| Outbound | Direct calling | Templates required outside 24h |
| Media | Audio only | Images, Videos, Documents, Audio |

---

## Architecture

### Message Flow

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  WhatsApp User  │────────▶│  Meta Cloud API  │────────▶│  AgentStudio    │
│  (Mobile App)   │         │  (Meta Servers)  │  webhook │  Backend        │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        ▲                                                        │
        │                                                        ▼
        │                                                ┌───────────────┐
        │                                                │ WHATSAPP_INPUT│
        │                                                └───────┬───────┘
        │                                                        ▼
        │                                                ┌───────────────┐
        │                                                │   LLM_AGENT   │
        │                                                └───────┬───────┘
        │                                                        ▼
        │                                                ┌───────────────┐
        │                                                │WHATSAPP_OUTPUT│
        │         ┌──────────────────┐                  └───────┬───────┘
        └─────────│  Meta Cloud API  │◀─────────────────────────┘
                  └──────────────────┘
```

### Directory Structure

```
backend/
├── app/
│   ├── api/v1/
│   │   └── whatsapp.py              # Webhook endpoints
│   ├── services/
│   │   └── whatsapp_provider/       # WhatsApp provider module
│   │       ├── __init__.py
│   │       ├── client.py            # Meta Graph API client
│   │       ├── message_types.py     # Message type definitions
│   │       └── security.py          # Webhook verification
│   ├── models/
│   │   └── credential.py            # Add WHATSAPP_META provider
│   └── schemas/
│       └── credential.py            # WhatsApp credential validation

frontend/
├── src/
│   ├── components/
│   │   ├── AgentBuilder/nodes/
│   │   │   ├── WhatsAppInputNode.tsx
│   │   │   └── WhatsAppOutputNode.tsx
│   │   └── Credentials/
│   │       └── CredentialModal.tsx  # WhatsApp credential form
│   └── types/
│       └── workflow.ts              # Node type definitions
```

---

## Prerequisites

### Meta Business Requirements

1. **Meta Business Account**: [business.facebook.com](https://business.facebook.com)
2. **Meta Developer Account**: [developers.facebook.com](https://developers.facebook.com)
3. **WhatsApp Business Account (WABA)**
4. **Verified Business** (for production)
5. **Dedicated Phone Number**

### Technical Requirements

- Python 3.11+
- HTTPS endpoint with valid SSL certificate
- Redis for session management

### Required Credentials

| Field | Description | Where to Find |
|-------|-------------|---------------|
| Phone Number ID | WhatsApp phone identifier | WhatsApp > Getting Started |
| Access Token | Graph API access token | System User > Generate Token |
| Business Account ID | WABA identifier | WhatsApp > Getting Started |
| App Secret | For webhook signature | App Settings > Basic |
| Verify Token | Custom webhook token | You create this |

---

## Implementation Plan

### Phase 1: Basic Text Messaging
- WhatsApp provider client
- Webhook endpoints (verification + messages)
- WhatsAppInputNode and WhatsAppOutputNode
- Credential support

### Phase 2: Media Support
- Image, video, audio, document handling
- Media upload/download
- Caption support

### Phase 3: Template Messages
- Template listing
- Template message sending
- Variable substitution

### Phase 4: Interactive Messages
- Quick reply buttons (max 3)
- List messages (max 10 items)
- Button/list response handling

---

## Backend Components

### 1. Credential Provider

Add to `backend/app/models/credential.py`:

```python
class CredentialProvider(str, enum.Enum):
    # ... existing providers
    WHATSAPP_META = "whatsapp_meta"
```

### 2. Credential Schema Validation

Add to `backend/app/schemas/credential.py`:

```python
elif provider == CredentialProvider.WHATSAPP_META:
    required_fields = ["phone_number_id", "access_token"]
    optional_fields = ["business_account_id", "app_secret", "verify_token"]
```

### 3. WhatsApp Client (`client.py`)

```python
class WhatsAppClient:
    """Meta Graph API client for WhatsApp Cloud API."""

    GRAPH_API_VERSION = "v19.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, phone_number_id: str, access_token: str, business_account_id: str = None):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.business_account_id = business_account_id

    async def send_text_message(self, to: str, text: str) -> dict:
        """Send text message (max 4096 chars)."""

    async def send_media_message(self, to: str, media_type: str, media_url: str, caption: str = None) -> dict:
        """Send image/video/audio/document."""

    async def send_template_message(self, to: str, template_name: str, language: str, components: list = None) -> dict:
        """Send pre-approved template message."""

    async def send_interactive_message(self, to: str, body: str, buttons: list = None, sections: list = None) -> dict:
        """Send interactive buttons or list."""

    async def mark_as_read(self, message_id: str) -> dict:
        """Mark message as read (blue ticks)."""
```

### 4. Webhook Endpoints (`whatsapp.py`)

```python
router = APIRouter()

@router.get("/webhook/{deployment_id}")
async def verify_webhook(
    deployment_id: str,
    api_key: str,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta webhook verification challenge."""
    # Return hub.challenge if verify_token matches

@router.post("/webhook/{deployment_id}")
async def handle_webhook(deployment_id: str, api_key: str, request: Request):
    """Process incoming WhatsApp messages."""
    # 1. Validate signature (X-Hub-Signature-256)
    # 2. Parse message from webhook payload
    # 3. Execute agent workflow
    # 4. Send response back via WhatsApp

@router.post("/send/{deployment_id}")
async def send_message(deployment_id: str, api_key: str, request: Request):
    """Send outbound message (for templates/proactive)."""

@router.get("/templates/{deployment_id}")
async def get_templates(deployment_id: str, api_key: str):
    """List approved message templates."""
```

### 5. Webhook Security (`security.py`)

```python
def verify_webhook_challenge(mode: str, token: str, challenge: str, expected_token: str) -> int:
    """Verify Meta's webhook setup challenge."""
    if mode == "subscribe" and token == expected_token:
        return int(challenge)
    raise HTTPException(403, "Verification failed")

def validate_webhook_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Validate X-Hub-Signature-256 header."""
    expected = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Frontend Components

### 1. WhatsAppInputNode

```tsx
// Shows: credential status, verify token, accepted message types
export const WhatsAppInputNode = memo(({ data, selected }: NodeProps) => {
  const config = data.config || {};
  return (
    <Card title={<><WhatsAppOutlined /> WhatsApp Input</>}>
      <div>Credential: {config.credentialId ? '✓ Connected' : '✗ Not configured'}</div>
      <div>Verify Token: {config.verifyToken ? '✓ Set' : '⚠ Not set'}</div>
      <div>Accept: {(config.messageTypes || ['text']).join(', ')}</div>
      <Handle type="source" position={Position.Right} />
    </Card>
  );
});
```

### 2. WhatsAppOutputNode

```tsx
// Shows: response type, template name (if template), buttons (if interactive)
export const WhatsAppOutputNode = memo(({ data, selected }: NodeProps) => {
  const config = data.config || {};
  return (
    <Card title={<><WhatsAppOutlined /> WhatsApp Output</>}>
      <Handle type="target" position={Position.Left} />
      <div>Type: {config.responseType || 'text'}</div>
      {config.responseType === 'template' && <div>Template: {config.templateName}</div>}
      {config.responseType === 'interactive' && <div>Buttons: {config.buttons?.length || 0}</div>}
    </Card>
  );
});
```

### 3. PropertyPanel Configuration

**WHATSAPP_INPUT config:**
- Credential selector (filter by whatsapp_meta)
- Verify token input
- Message types multi-select (text, image, video, audio, document, location, interactive)
- Error message textarea

**WHATSAPP_OUTPUT config:**
- Response type select (text, template, media, interactive)
- Template name input (if template)
- Media type select (if media)
- Button configuration (if interactive, max 3)

### 4. CredentialModal WhatsApp Fields

```tsx
{credentialType === 'whatsapp' && (
  <>
    <Form.Item name={['connection_config', 'phone_number_id']} label="Phone Number ID" required>
      <Input placeholder="1234567890123456" />
    </Form.Item>
    <Form.Item name={['connection_config', 'access_token']} label="Access Token" required>
      <Input.Password placeholder="EAAxxxxxxx..." />
    </Form.Item>
    <Form.Item name={['connection_config', 'business_account_id']} label="Business Account ID">
      <Input placeholder="1234567890123456" />
    </Form.Item>
    <Form.Item name={['connection_config', 'app_secret']} label="App Secret">
      <Input.Password placeholder="For webhook signature validation" />
    </Form.Item>
  </>
)}
```

---

## Webhook Security

### Verification Challenge (GET)

When setting up webhooks in Meta dashboard, Meta sends:
```
GET /webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=123456
```

Your server must return the `hub.challenge` value if `hub.verify_token` matches.

### Signature Validation (POST)

Meta signs payloads with your app secret:
```
X-Hub-Signature-256: sha256=<signature>
```

Always validate in production:
```python
expected = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
is_valid = hmac.compare_digest(expected, received_signature)
```

---

## Message Types

### Text (within 24h window)
```python
await client.send_text_message(to="1234567890", text="Hello!")
```

### Media
```python
await client.send_media_message(
    to="1234567890",
    media_type="image",  # image, video, audio, document
    media_url="https://example.com/image.jpg",
    caption="Check this out!"
)
```

### Template (outside 24h window)
```python
await client.send_template_message(
    to="1234567890",
    template_name="order_update",
    language="en",
    components=[{"type": "body", "parameters": [{"type": "text", "text": "ORD-123"}]}]
)
```

### Interactive Buttons (max 3)
```python
await client.send_interactive_message(
    to="1234567890",
    body="How can I help?",
    buttons=[
        {"id": "sales", "title": "Sales"},
        {"id": "support", "title": "Support"},
        {"id": "other", "title": "Other"}
    ]
)
```

---

## Session Management

### 24-Hour Window

- **Within 24h of last user message**: Send any message type (free)
- **Outside 24h**: Only template messages allowed (paid)

### Redis Session Storage

```python
session_key = f"whatsapp_session:{deployment_id}:{phone_number}"
session_data = {
    "phone_number": "+1234567890",
    "sender_name": "John Doe",
    "last_message_at": "2025-01-02T10:30:00Z",
    "message_count": 5,
    "context": {}  # Conversation history
}
# TTL: 24 hours (86400 seconds)
```

---

## Testing

### 1. Get Test Credentials

1. Go to Meta Developer Dashboard
2. WhatsApp > Getting Started
3. Use provided test phone number
4. Add your number to recipient list

### 2. Expose Local Webhook

```bash
ngrok http 8000
# Use: https://abc123.ngrok.io/api/v1/whatsapp/webhook/{deployment_id}?api_key={key}
```

### 3. Configure Webhook in Meta

1. WhatsApp > Configuration > Webhooks
2. Enter your ngrok URL + verify token
3. Subscribe to `messages` field

### 4. Send Test Message

Send a WhatsApp message to the test number and verify:
- Webhook receives the message
- Agent processes it
- Response sent back

---

## Production Checklist

- [ ] Business verification completed
- [ ] Production phone number verified
- [ ] Display name approved by Meta
- [ ] Message templates created and approved
- [ ] HTTPS webhook with valid SSL
- [ ] App secret configured for signature validation
- [ ] Rate limits implemented
- [ ] Error handling and logging
- [ ] Monitoring and alerting

### Rate Limits

| Tier | Messages/24h | Requirements |
|------|--------------|--------------|
| Unverified | 250 | Default |
| Tier 1 | 1,000 | Business verified |
| Tier 2 | 10,000 | Quality history |
| Tier 3 | 100,000 | High quality |
| Tier 4 | Unlimited | Enterprise |

---

## Environment Variables

```env
# Add to backend/.env
WHATSAPP_GRAPH_API_VERSION=v19.0
WHATSAPP_SIGNATURE_VALIDATION=true
```

---

## References

- [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Webhook Setup](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/message-templates)
- [Interactive Messages](https://developers.facebook.com/docs/whatsapp/cloud-api/messages/interactive)

---

**Last Updated**: 2025-01-02
