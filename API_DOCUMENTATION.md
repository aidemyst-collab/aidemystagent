# AgentStudio API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_token>
```

### Endpoints

#### POST /auth/register
Register a new user.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "organization_name": "My Organization"
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "creator"
  }
}
```

#### POST /auth/login
Authenticate a user.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

## Agents

#### GET /agents
List all agents.

**Query Parameters:**
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 100)

**Response:** `200 OK`
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "Customer Service Bot",
      "description": "Handles customer inquiries",
      "status": "deployed",
      "version": 1,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### POST /agents
Create a new agent.

**Request Body:**
```json
{
  "name": "My Agent",
  "description": "Agent description",
  "config": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response:** `201 Created`

#### GET /agents/{agent_id}
Get a specific agent.

**Response:** `200 OK`

#### PATCH /agents/{agent_id}
Update an agent.

**Response:** `200 OK`

#### DELETE /agents/{agent_id}
Delete an agent.

**Response:** `204 No Content`

## Templates

#### GET /templates
List all available agent templates.

**Response:** `200 OK`
```json
{
  "templates": [
    {
      "id": "customer_service",
      "name": "Customer Service Agent",
      "description": "...",
      "category": "support",
      "tags": ["support", "faq"]
    }
  ]
}
```

#### POST /templates/{template_id}/clone
Clone a template to create a new agent.

**Response:** `200 OK`

## Deployments

#### GET /deployments
List all deployments.

**Query Parameters:**
- `agent_id` (uuid): Filter by agent
- `environment` (string): Filter by environment (development, staging, production)
- `status_filter` (string): Filter by status (pending, active, stopped, failed)

**Response:** `200 OK`

#### POST /deployments
Create a new deployment.

**Request Body:**
```json
{
  "agent_id": "uuid",
  "version": "1.0.0",
  "environment": "production",
  "config": {
    "auto_scale": true,
    "max_concurrent": 10,
    "timeout": 300
  }
}
```

**Response:** `201 Created`

#### POST /deployments/{deployment_id}/stop
Stop a running deployment.

**Response:** `200 OK`

#### POST /deployments/{deployment_id}/restart
Restart a stopped deployment.

**Response:** `200 OK`

## Version Control

#### GET /agents/{agent_id}/versions
List all versions of an agent.

**Response:** `200 OK`

#### POST /agents/{agent_id}/versions
Create a new version.

**Request Body:**
```json
{
  "version_tag": "v1.0.0",
  "config": {...},
  "description": "Added new features",
  "changelog": "- Added RAG integration\n- Fixed bugs"
}
```

**Response:** `201 Created`

#### POST /agents/{agent_id}/versions/{version_number}/restore
Restore an agent to a previous version.

**Response:** `200 OK`

#### GET /agents/{agent_id}/versions/compare/{version1}/{version2}
Compare two versions.

**Response:** `200 OK`

## Tools

#### GET /tools/built-in
List all built-in tools.

**Response:** `200 OK`
```json
{
  "tools": [
    {
      "name": "calculator",
      "description": "Performs mathematical calculations",
      "category": "utility",
      "parameters": {
        "expression": "string"
      }
    }
  ]
}
```

#### POST /tools/built-in/{tool_name}/execute
Execute a tool.

**Request Body:**
```json
{
  "input_data": {
    "expression": "2 + 2 * 3"
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "result": 8,
  "metadata": {
    "execution_time_ms": 5
  }
}
```

## Agent Execution

#### POST /execute/{agent_id}
Execute an agent.

**Request Body:**
```json
{
  "input": {
    "query": "What is the weather today?"
  }
}
```

**Response:** `200 OK`
```json
{
  "output": "I don't have access to real-time weather data...",
  "execution_path": [...],
  "tokens_used": 150,
  "execution_time_ms": 2500
}
```

#### POST /execute/{agent_id}/stream
Execute an agent with streaming response (Server-Sent Events).

**Response:** `text/event-stream`

## Analytics

#### GET /analytics
Get analytics data.

**Query Parameters:**
- `agent_id` (uuid): Filter by agent
- `start_date` (datetime): Start date for filtering
- `end_date` (datetime): End date for filtering

**Response:** `200 OK`
```json
{
  "total_agents": 10,
  "total_executions": 1500,
  "avg_execution_time": 2345.67,
  "success_rate": 98.5,
  "executions_by_agent": [...],
  "executions_over_time": [...]
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": {
    "message": "Invalid request",
    "status_code": 400,
    "path": "/api/v1/agents",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

### 401 Unauthorized
```json
{
  "error": {
    "message": "Not authenticated",
    "status_code": 401
  }
}
```

### 403 Forbidden
```json
{
  "error": {
    "message": "Insufficient permissions",
    "status_code": 403
  }
}
```

### 404 Not Found
```json
{
  "error": {
    "message": "Resource not found",
    "status_code": 404
  }
}
```

### 422 Unprocessable Entity
```json
{
  "error": {
    "message": "Validation error",
    "details": [...],
    "status_code": 422
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "message": "Internal server error",
    "status_code": 500,
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

## Rate Limiting

Currently, there are no rate limits applied. In production, consider implementing rate limiting based on user tiers.

## Pagination

List endpoints support pagination using `skip` and `limit` query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100, max: 1000)

## Versioning

The API is versioned via the URL path (`/api/v1`). Breaking changes will result in a new version (`/api/v2`).
