# AgentStudio User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Creating Your First Agent](#creating-your-first-agent)
3. [Using Templates](#using-templates)
4. [Testing Agents](#testing-agents)
5. [Deploying Agents](#deploying-agents)
6. [Managing Tools](#managing-tools)
7. [Version Control](#version-control)
8. [Analytics](#analytics)
9. [User Management](#user-management)

## Getting Started

### Registration
1. Navigate to the registration page
2. Enter your email and password
3. Provide your organization name
4. Click "Register"

### Login
1. Go to the login page
2. Enter your credentials
3. Click "Login"

You'll be redirected to the dashboard upon successful authentication.

## Creating Your First Agent

### Using the Visual Builder

1. **Navigate to Agents**
   - Click "Agents" in the sidebar
   - Click "Create New Agent"

2. **Add Nodes**
   - Drag nodes from the Node Library panel
   - Available node types:
     - **INPUT**: Entry point for user queries
     - **LLM_AGENT**: AI-powered language model processing
     - **RAG_RETRIEVER**: Retrieve documents from RAG systems
     - **DECISION**: Conditional logic and routing
     - **TOOL**: Execute external tools
     - **OUTPUT**: Final response to user
     - **SUBGRAPH**: Nested workflows

3. **Connect Nodes**
   - Click and drag from one node's output to another's input
   - Connections define the execution flow

4. **Configure Nodes**
   - Click a node to open the Property Panel
   - Set node-specific parameters:
     - LLM prompts
     - RAG endpoints
     - Tool parameters
     - Decision conditions

5. **Save Your Agent**
   - Click "Save" in the toolbar
   - Your agent is automatically versioned

### Agent Configuration Example

```
INPUT → LLM_AGENT → RAG_RETRIEVER → LLM_AGENT → OUTPUT
```

This creates a simple Q&A agent that:
1. Receives user input
2. Processes with LLM
3. Retrieves relevant documents
4. Generates final response
5. Returns to user

## Using Templates

Templates provide pre-built agent workflows for common use cases.

1. **Browse Templates**
   - Click "Templates" in the sidebar
   - Use search and filters to find templates

2. **Preview Template**
   - Click "Preview" on any template
   - View the workflow structure and configuration

3. **Clone Template**
   - Click "Use Template"
   - A new agent is created from the template
   - Customize as needed

### Available Templates

- **Customer Service Agent**: FAQ answering and ticket routing
- **Research Agent**: Web search and document analysis
- **Data Analysis Agent**: Query interpretation and calculations
- **Workflow Agent**: Task routing and notifications
- **QA Agent**: Answer validation and verification

## Testing Agents

### Interactive Testing Playground

1. **Open Test Interface**
   - Navigate to your agent
   - Click "Test" button

2. **Standard Mode**
   - Enter test input in the message box
   - Click "Send"
   - View complete response

3. **Streaming Mode**
   - Switch to "Streaming" tab
   - Responses stream in real-time
   - See token-by-token generation

4. **Review Execution Path**
   - View which nodes were executed
   - Check execution times
   - Analyze token usage

## Deploying Agents

### Creating a Deployment

1. **Navigate to Deployments**
   - Click "Deployments" in sidebar
   - Select agent to deploy

2. **Configure Deployment**
   - **Version**: Semantic version (e.g., 1.0.0)
   - **Environment**: Development, Staging, or Production
   - **Auto-scaling**: Enable/disable
   - **Max Concurrent**: Maximum simultaneous requests
   - **Timeout**: Request timeout in seconds

3. **Deploy**
   - Click "Deploy"
   - Deployment status updates automatically

### Managing Deployments

- **Stop**: Temporarily halt a deployment
- **Restart**: Resume a stopped deployment
- **Delete**: Remove a deployment permanently

### Deployment Endpoints

Each deployment provides:
- **Endpoint URL**: API endpoint for invoking the agent
- **API Key**: Authentication key for requests

Copy these values to integrate your agent into applications.

## Managing Tools

Tools extend agent capabilities with external functions.

### Built-in Tools

1. **Calculator**
   - Performs mathematical calculations
   - Input: `expression` (string)
   - Example: `"2 + 2 * 3"` → `8`

2. **DateTime**
   - Current time and timezone conversion
   - Operations: `current`, `convert_timezone`

3. **JSON Parser**
   - Parse and extract JSON data
   - Operations: `parse`, `extract`

4. **Web Search**
   - Search the web (mock implementation)
   - Input: `query` (string)

### Testing Tools

1. Go to "Tools" page
2. Select a tool
3. Click "Test"
4. Enter test parameters
5. View results

## Version Control

AgentStudio tracks all changes to your agents.

### Creating Versions

Versions are created automatically when you:
- Save changes to an agent
- Deploy an agent
- Restore from a previous version

### Manual Versioning

1. Edit your agent
2. Click "Create Version"
3. Add version tag (e.g., "v1.2.0")
4. Provide description and changelog
5. Save

### Viewing History

1. Navigate to your agent
2. Click "Versions" tab
3. View all versions with:
   - Version number
   - Tag
   - Description
   - Created date

### Restoring Versions

1. Find the version to restore
2. Click "Restore"
3. Confirm restoration
4. A new version is created with old configuration

### Comparing Versions

1. Select two versions
2. Click "Compare"
3. View differences:
   - Nodes added/removed
   - Edges added/removed
   - Configuration changes

## Analytics

Monitor agent performance and usage.

### Dashboard Metrics

- **Total Agents**: Number of agents in your organization
- **Total Executions**: All-time execution count
- **Avg Execution Time**: Average response time
- **Success Rate**: Percentage of successful executions

### Filtering Analytics

- **By Agent**: View metrics for specific agent
- **Date Range**: Filter by time period
- **Environment**: Filter by deployment environment

### Charts

- **Executions by Agent**: Top performing agents
- **Executions Over Time**: Usage trends

## User Management

*Admin users only*

### Adding Users

1. Go to "Users" page
2. Click "Add User"
3. Enter:
   - Email
   - Password
   - Role (Admin, Creator, Viewer)
4. Click "Create"

### User Roles

- **Admin**: Full access, user management
- **Creator**: Create and manage agents
- **Viewer**: Read-only access

### Editing Users

1. Find user in list
2. Click "Edit"
3. Update role or details
4. Save changes

### Removing Users

1. Find user in list
2. Click "Delete"
3. Confirm deletion

## Best Practices

### Agent Design

1. **Start Simple**: Begin with basic workflows
2. **Test Frequently**: Use the playground extensively
3. **Version Often**: Create versions before major changes
4. **Document**: Use descriptions and changelogs

### Performance

1. **Optimize Prompts**: Keep LLM prompts focused
2. **Cache RAG Results**: Configure caching for frequently accessed data
3. **Set Timeouts**: Prevent long-running executions
4. **Monitor Analytics**: Track and optimize slow agents

### Security

1. **Rotate API Keys**: Update deployment keys regularly
2. **Least Privilege**: Assign minimal necessary permissions
3. **Review Logs**: Check error logs for security issues
4. **Validate Input**: Sanitize user input in agent configurations

## Troubleshooting

### Agent Not Executing

- Check all nodes are connected
- Verify INPUT and OUTPUT nodes exist
- Review error logs in Analytics

### Deployment Failed

- Ensure agent is saved
- Check deployment configuration
- Verify environment settings

### RAG Connection Issues

- Test RAG endpoint connectivity
- Verify authentication credentials
- Check firewall/network settings

## Support

For additional help:
- Check API documentation at `/docs`
- Review error logs in `logs/` directory
- Contact your organization admin
