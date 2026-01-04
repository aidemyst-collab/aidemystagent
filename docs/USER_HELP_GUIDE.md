# AgentStudio User Help Guide

Welcome to **AgentStudio** - Your AI Agent Creation & Management Platform. This guide will help you understand and use all the features of AgentStudio to build, test, deploy, and manage AI agents.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Workflow Builder](#3-workflow-builder)
4. [Node Types Reference](#4-node-types-reference)
5. [Credentials Management](#5-credentials-management)
6. [Templates](#6-templates)
7. [Tools](#7-tools)
8. [Testing & Playground](#8-testing--playground)
9. [Deployments](#9-deployments)
10. [Analytics](#10-analytics)
11. [User & Organization Management](#11-user--organization-management)
12. [Voice Integration](#12-voice-integration)
13. [WhatsApp Integration](#13-whatsapp-integration)
14. [Troubleshooting & FAQ](#14-troubleshooting--faq)

---

## 1. Getting Started

### What is AgentStudio?

AgentStudio is a visual platform for creating AI agents without writing code. You can:

- **Design** workflows using drag-and-drop nodes
- **Connect** to LLMs (OpenAI, Anthropic, Google, Azure)
- **Integrate** with knowledge bases (RAG systems)
- **Deploy** agents to production with API endpoints
- **Monitor** performance with analytics

### First Steps

1. **Register/Login**: Create an account or log in at the login page
2. **Add Credentials**: Navigate to **Credentials** to add your LLM API keys
3. **Explore Templates**: Check out **Templates** for pre-built agent workflows
4. **Build Your First Agent**: Go to **Workflow Builder** to create a custom agent

### Navigation

The main menu provides access to all sections:

| Menu Item | Description |
|-----------|-------------|
| Dashboard | Overview of your agents and activity |
| Agents | List and manage all your agents |
| Workflow Builder | Visual editor for creating workflows |
| Templates | Pre-built agent templates |
| Tools | Built-in and custom tools |
| Credentials | API keys and provider credentials |
| Deployments | Production deployments |
| Analytics | Usage statistics and metrics |

---

## 2. Dashboard

The Dashboard provides a quick overview of your AgentStudio workspace.

### Key Metrics

- **Total Agents**: Number of agents you've created
- **Active Deployments**: Agents currently deployed to production
- **Total Executions**: How many times your agents have been run
- **Success Rate**: Percentage of successful executions

### Recent Activity

View your most recent:
- Created/modified agents
- Deployment changes
- Execution logs

### Quick Actions

- **Create New Agent**: Start building a new workflow
- **View All Agents**: Navigate to the full agents list
- **Create Deployment**: Deploy an agent to production

---

## 3. Workflow Builder

The Workflow Builder is the heart of AgentStudio - a visual canvas for designing AI agent workflows.

### Canvas Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Node Library  │              Canvas                │ Props  │
│                │                                    │        │
│  [Input]       │    ┌─────┐    ┌─────┐    ┌─────┐  │ Config │
│  [LLM Agent]   │    │Input│───▶│ LLM │───▶│Output│  │ Panel  │
│  [RAG]         │    └─────┘    └─────┘    └─────┘  │        │
│  [Tool]        │                                    │        │
│  [Output]      │                                    │        │
│  ...           │                                    │        │
└──────────────────────────────────────────────────────────────┘
```

### How to Build a Workflow

1. **Drag Nodes**: Drag nodes from the Node Library onto the canvas
2. **Connect Nodes**: Click and drag from one node's output handle to another node's input handle
3. **Configure Nodes**: Click a node to open its configuration in the Properties Panel
4. **Save**: Click "Save" to save your workflow
5. **Test**: Use the Test button to try your workflow

### Basic Workflow Pattern

Most agents follow this pattern:

```
INPUT → LLM_AGENT → OUTPUT
```

For more complex agents:

```
INPUT → MEMORY → LLM_AGENT → RAG_RETRIEVER → LLM_AGENT → OUTPUT
              ↓
            TOOL
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Delete` / `Backspace` | Delete selected node |
| `Ctrl/Cmd + S` | Save workflow |
| `Ctrl/Cmd + Z` | Undo |
| `Ctrl/Cmd + Y` | Redo |
| Mouse Wheel | Zoom in/out |
| Click + Drag | Pan canvas |

---

## 4. Node Types Reference

AgentStudio provides 17 node types for building workflows:

### Core Nodes

#### Input Node
**Purpose**: Entry point for user requests

**Configuration**:
- **Mode**: Chat, JSON, Form, or Audio
- **Schema**: Optional input validation

**Example Use**: Receive user messages, accept form data, process audio input

---

#### LLM Agent Node
**Purpose**: Core language model agent that processes text

**Configuration**:
- **Credential**: Select your LLM provider credential
- **Model**: Choose the model (GPT-4, Claude-3, etc.)
- **Temperature**: Control creativity (0.0 = focused, 1.0 = creative)
- **Max Tokens**: Limit response length
- **System Prompt**: Define the agent's behavior and personality
- **Tools**: Select tools the agent can use

**Example Use**: Process user queries, generate responses, make decisions

---

#### Output Node
**Purpose**: Format and deliver final responses

**Configuration**:
- **Format**: Text, JSON, or Markdown
- **Template**: Optional response template

**Example Use**: Send formatted responses to users

---

#### Memory Node
**Purpose**: Store and retrieve conversation history

**Configuration**:
- **Type**: Buffer, Buffer-Window, Summary, Vector, or Entity
- **Window Size**: How many messages to remember (for buffer-window)
- **Persistence**: Enable Redis/PostgreSQL storage for long-term memory

**Example Use**: Maintain context across conversations

---

#### RAG Retriever Node
**Purpose**: Retrieve knowledge from external databases

**Configuration**:
- **RAG Source**: Internal or External
- **Endpoint**: RAG system URL
- **Search Method**: Semantic, Hybrid, or Keyword search
- **Top K**: Number of results to retrieve
- **Score Threshold**: Minimum relevance score

**Example Use**: Fetch relevant documents before LLM processing

---

#### Decision Node
**Purpose**: Conditional logic and routing

**Configuration**:
- **Conditions**: Define rules (field, operator, value)
- **Target Nodes**: Where to route based on conditions
- **Default Route**: Fallback path

**Example Use**: Route conversations based on intent, user type, or content

---

#### Tool Node
**Purpose**: Execute specific tools

**Configuration**:
- **Tool Selection**: Choose from built-in or custom tools
- **Parameters**: Configure tool inputs

**Example Use**: Perform calculations, search the web, call APIs

---

#### Subgraph Node
**Purpose**: Embed nested workflows

**Configuration**:
- **Agent ID**: Select an existing agent to embed
- **Input Mapping**: Map parent data to subgraph inputs

**Example Use**: Reuse common workflows, create modular agents

---

### Processing Nodes

#### File Reader Node
**Purpose**: Read and process files

**Configuration**:
- **File Type**: PDF, TXT, CSV, JSON, etc.
- **Source**: Upload, URL, or Path

**Example Use**: Process uploaded documents

---

#### Structured Output Parser Node
**Purpose**: Parse LLM output into structured JSON

**Configuration**:
- **Schema**: Define expected JSON structure
- **Validation**: Enable/disable strict validation

**Example Use**: Extract structured data from LLM responses

---

#### Code Node
**Purpose**: Execute custom JavaScript or Python code

**Configuration**:
- **Language**: JavaScript or Python
- **Code**: Your custom code
- **Inputs**: Variables passed to the code

**Example Use**: Custom data transformations, complex logic

---

### Audio Nodes

#### Audio to Text Node
**Purpose**: Transcribe audio to text

**Configuration**:
- **Provider**: OpenAI Whisper, Azure, etc.
- **Language**: Source audio language

**Example Use**: Transcribe voice messages or calls

---

#### Text to Audio Node
**Purpose**: Convert text to speech

**Configuration**:
- **Provider**: OpenAI TTS, Azure, ElevenLabs
- **Voice**: Select voice type
- **Speed**: Playback speed

**Example Use**: Generate voice responses

---

### Voice Nodes

#### Voice Input Node
**Purpose**: Receive incoming voice calls

**Configuration**:
- **Provider**: Twilio or Etisalat
- **Credential**: Select voice provider credential
- **Welcome Message**: Initial greeting
- **Language**: Expected language

**Example Use**: Build voice-based AI assistants

---

#### Voice Output Node
**Purpose**: Play audio responses to callers

**Configuration**:
- **Response Type**: Text-to-Speech or Audio URL
- **Voice**: Select TTS voice
- **End Call**: Optionally end call after response

**Example Use**: Respond to voice callers

---

### Messaging Nodes

#### WhatsApp Input Node
**Purpose**: Receive WhatsApp messages

**Configuration**:
- **Credential**: WhatsApp Meta credential
- **Message Types**: Text, Image, Video, etc.
- **Welcome Message**: Auto-reply for new conversations

**Example Use**: Build WhatsApp chatbots

---

#### WhatsApp Output Node
**Purpose**: Send WhatsApp responses

**Configuration**:
- **Response Type**: Text, Template, Media, or Interactive
- **Template Name**: For template messages
- **Buttons**: For interactive messages (max 3)

**Example Use**: Reply to WhatsApp users with rich content

---

## 5. Credentials Management

Credentials store your API keys securely for use in workflows.

### Supported Providers

| Category | Providers |
|----------|-----------|
| **LLM** | OpenAI, Anthropic, Google AI, Azure OpenAI, Custom |
| **Database** | Redis, PostgreSQL, MongoDB |
| **Voice** | Twilio, Etisalat |
| **Messaging** | WhatsApp (Meta) |

### Adding a Credential

1. Navigate to **Credentials**
2. Click **Add Credential**
3. Select the **Provider Type**
4. Enter your **API Key** and other required fields
5. Give it a **Name** for easy reference
6. Click **Save**

### Credential Fields by Provider

**OpenAI**:
- API Key (required)
- Organization ID (optional)

**Anthropic**:
- API Key (required)

**Azure OpenAI**:
- API Key (required)
- API Base URL (required)
- API Version (required)

**WhatsApp Meta**:
- Phone Number ID (required)
- Access Token (required)
- Business Account ID (optional)
- App Secret (recommended for webhook security)

### Security

- API keys are encrypted at rest
- Keys are never exposed in the UI (shown as masked previews)
- Credentials are scoped to your organization

---

## 6. Templates

Templates are pre-built agent workflows you can clone and customize.

### Available Template Categories

- **Customer Support**: FAQ bots, ticket handlers
- **Data Processing**: Document analyzers, data extractors
- **Conversational**: Chatbots, virtual assistants
- **Integration**: API connectors, workflow automation

### Using a Template

1. Navigate to **Templates**
2. Browse or search for a template
3. Click **Preview** to see the workflow
4. Click **Use Template** to clone it
5. Customize the cloned workflow as needed

### Template Features

Each template includes:
- Pre-configured nodes and connections
- Default prompts and settings
- Documentation on use cases
- Suggested customizations

---

## 7. Tools

Tools extend agent capabilities with specific functions.

### Built-in Tools

| Tool | Description | Example Use |
|------|-------------|-------------|
| **Calculator** | Math operations | "What's 15% of 250?" |
| **DateTime** | Date/time operations | "What day is it next Friday?" |
| **JSON Parser** | Parse/extract JSON | Extract data from API responses |
| **Web Search** | Search the internet | Find current information |
| **API Integration** | Call external APIs | Connect to third-party services |

### Using Tools in Workflows

1. Add an **LLM Agent** node
2. In the configuration, under **Tools**, select the tools to enable
3. The LLM will automatically use tools when appropriate

### Creating Custom Tools

1. Navigate to **Tools**
2. Click **Create Tool**
3. Define:
   - **Name**: Tool identifier
   - **Description**: What the tool does (LLMs read this)
   - **Input Schema**: Expected parameters
   - **API Endpoint**: External API to call
   - **Authentication**: API key or OAuth

---

## 8. Testing & Playground

Test your agents before deploying them.

### Agent Playground

The Playground provides an interactive testing environment:

1. Open an agent in the Workflow Builder
2. Click **Test** or navigate to **Agent Test**
3. Enter a test message
4. View the response and execution details

### Playground Features

- **Real-time Responses**: See agent responses immediately
- **Execution Trace**: View which nodes were executed
- **Token Usage**: Monitor token consumption
- **Error Details**: Debug issues with detailed error messages

### Testing Tips

- Start with simple inputs and gradually add complexity
- Test edge cases (empty inputs, long messages, special characters)
- Verify tool usage by asking questions that require tools
- Check memory by having multi-turn conversations

---

## 9. Deployments

Deploy agents to production with API endpoints.

### Environments

| Environment | Purpose |
|-------------|---------|
| **Development** | For testing and iteration |
| **Staging** | Pre-production testing |
| **Production** | Live, customer-facing |

### Creating a Deployment

1. Navigate to **Deployments**
2. Click **Create Deployment**
3. Select the **Agent** to deploy
4. Choose the **Environment**
5. Configure settings:
   - Rate limits
   - API key requirements
   - CORS settings
6. Click **Deploy**

### Deployment Details

Each deployment provides:
- **Endpoint URL**: `https://api.yourdomain.com/v1/execute/{deployment_id}`
- **API Key**: For authentication
- **Status**: Active, Inactive, or Failed

### Using Deployed Agents

```bash
curl -X POST "https://api.yourdomain.com/v1/execute/{deployment_id}" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how can you help me?"}'
```

### Managing Deployments

- **Stop**: Temporarily disable without deleting
- **Restart**: Restart a stopped deployment
- **Delete**: Permanently remove deployment
- **View Logs**: See execution history

---

## 10. Analytics

Monitor agent performance and usage.

### Dashboard Metrics

- **Total Executions**: Number of times agents were run
- **Success Rate**: Percentage of successful executions
- **Average Response Time**: How fast agents respond
- **Token Usage**: LLM tokens consumed

### Agent-Specific Analytics

For each agent, view:
- Execution history over time
- Error rates and types
- Most common user inputs
- Token consumption breakdown

### Filtering & Export

- Filter by date range, agent, or environment
- Export data to CSV for external analysis

---

## 11. User & Organization Management

Manage team members and access control.

### Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access, user management |
| **Creator** | Create/edit agents, deploy |
| **Viewer** | Read-only access, test agents |

### Inviting Team Members

1. Navigate to **Users** (Admin only)
2. Click **Invite User**
3. Enter email address
4. Select role
5. Click **Send Invitation**

### Organization Settings

- **Name**: Your organization name
- **Members**: List of all team members
- **Usage Limits**: Set execution limits per user

---

## 12. Voice Integration

Build voice-enabled AI agents using Twilio or Etisalat.

### Setup Overview

1. **Add Voice Credential**: Add your Twilio/Etisalat credentials
2. **Configure Webhook**: Point your phone number to AgentStudio
3. **Build Workflow**: Use Voice Input/Output nodes

### Voice Workflow Example

```
VOICE_INPUT → AUDIO_TO_TEXT → LLM_AGENT → TEXT_TO_AUDIO → VOICE_OUTPUT
```

### Voice Node Configuration

**Voice Input**:
- Select provider (Twilio/Etisalat)
- Set welcome message
- Configure language

**Voice Output**:
- Choose response type (TTS or audio file)
- Select voice
- Configure end-call behavior

### Webhook Setup

For **Twilio**:
1. In Twilio Console, go to Phone Numbers
2. Set Voice webhook URL to: `https://your-domain/api/v1/voice/twilio/webhook`

For **Etisalat**:
1. Configure callback URL in Etisalat portal
2. Set URL to: `https://your-domain/api/v1/voice/etisalat/webhook`

---

## 13. WhatsApp Integration

Build WhatsApp chatbots using Meta's Cloud API.

### Setup Overview

1. **Create Meta App**: Set up a WhatsApp Business app in Meta Developer Portal
2. **Add Credential**: Add your WhatsApp credentials to AgentStudio
3. **Configure Webhook**: Point Meta to your AgentStudio webhook
4. **Build Workflow**: Use WhatsApp Input/Output nodes

### WhatsApp Workflow Example

```
WHATSAPP_INPUT → MEMORY → LLM_AGENT → WHATSAPP_OUTPUT
```

### Message Types Supported

**Incoming**:
- Text messages
- Images, videos, audio, documents
- Location sharing
- Interactive button replies
- List selections

**Outgoing**:
- Text messages
- Media (image, video, audio, document)
- Template messages (required outside 24-hour window)
- Interactive buttons and lists

### Template Messages

Templates are required for initiating conversations or messaging outside the 24-hour customer service window:

1. Create templates in Meta Business Manager
2. Wait for Meta approval (usually 24 hours)
3. Use templates in WhatsApp Output node

### Webhook Setup

1. In Meta Developer Portal, go to WhatsApp > Configuration
2. Set Webhook URL: `https://your-domain/api/v1/whatsapp/webhook`
3. Enter your Verify Token (from AgentStudio credentials)
4. Subscribe to: `messages`

---

## 14. Troubleshooting & FAQ

### Common Issues

#### "Agent execution failed"

**Causes**:
- Invalid credentials
- LLM API rate limits
- Network issues

**Solutions**:
1. Check credential validity in Credentials page
2. Wait and retry for rate limits
3. Check error details in execution logs

---

#### "Credential test failed"

**Causes**:
- Invalid API key
- Wrong API base URL (Azure)
- Missing required fields

**Solutions**:
1. Verify API key is correct
2. Check provider-specific fields
3. Ensure credential is marked as "active"

---

#### "RAG retrieval returned no results"

**Causes**:
- Empty knowledge base
- High score threshold
- Incorrect collection ID

**Solutions**:
1. Verify data exists in your RAG system
2. Lower the score threshold (e.g., from 0.8 to 0.5)
3. Check collection ID is correct

---

#### "WhatsApp webhook verification failed"

**Causes**:
- Verify token mismatch
- Incorrect webhook URL
- Server not reachable

**Solutions**:
1. Ensure verify token matches in both Meta and AgentStudio
2. Check URL is publicly accessible
3. Verify HTTPS is properly configured

---

#### "Voice call drops immediately"

**Causes**:
- TwiML/response error
- Credential issues
- Webhook timeout

**Solutions**:
1. Check voice credential is valid
2. Review webhook logs for errors
3. Ensure response is generated within timeout

---

### FAQ

**Q: Can I use multiple LLM providers in one workflow?**

A: Yes! Each LLM Agent node can use a different credential. This allows you to use GPT-4 for complex reasoning and GPT-3.5 for simple tasks.

---

**Q: How do I handle long conversations?**

A: Use a Memory node with "buffer-window" or "summary" type. Buffer-window keeps the last N messages, while summary creates condensed history.

---

**Q: What's the difference between Development and Production deployments?**

A: Development deployments are for testing and may have less strict rate limits. Production deployments are for live usage and should have proper monitoring and rate limiting.

---

**Q: Can I call external APIs from my agent?**

A: Yes! Use the API Integration tool or create a custom tool with your API endpoint.

---

**Q: How do I debug a failing workflow?**

A:
1. Use the Playground to test with sample inputs
2. Check the execution trace to see which node failed
3. Review error messages in the details panel
4. Check Analytics for patterns in failures

---

**Q: Is my data secure?**

A: Yes. AgentStudio uses:
- Encrypted credential storage
- HTTPS for all communications
- Role-based access control
- Audit logging for sensitive operations

---

### Getting Help

If you need additional assistance:

1. **Documentation**: Review this guide and other docs
2. **API Docs**: Visit `/docs` on your backend for API reference
3. **Support**: Contact your administrator
4. **Issues**: Report bugs on the GitHub repository

---

## Quick Reference

### Node Connection Rules

| Node Type | Can Connect To |
|-----------|----------------|
| INPUT | Any node |
| MEMORY | LLM_AGENT, OUTPUT |
| LLM_AGENT | Any node |
| RAG_RETRIEVER | LLM_AGENT |
| DECISION | Any node (via conditions) |
| TOOL | LLM_AGENT, OUTPUT |
| OUTPUT | (End node) |
| VOICE_INPUT | AUDIO_TO_TEXT, LLM_AGENT |
| VOICE_OUTPUT | (End node) |
| WHATSAPP_INPUT | LLM_AGENT, MEMORY |
| WHATSAPP_OUTPUT | (End node) |

### Model Recommendations

| Use Case | Recommended Model |
|----------|-------------------|
| Complex reasoning | GPT-4, Claude-3-Opus |
| General chat | GPT-3.5-Turbo, Claude-3-Sonnet |
| Fast responses | GPT-3.5-Turbo, Claude-3-Haiku |
| Code generation | GPT-4, Claude-3-Opus |
| Cost-sensitive | GPT-3.5-Turbo, Claude-3-Haiku |

---

*Last Updated: January 2026*
*AgentStudio Version: 1.0.0-beta*
