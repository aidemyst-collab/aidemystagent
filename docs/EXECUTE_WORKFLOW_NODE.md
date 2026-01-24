# Execute Workflow Node - Design Document

## Overview

The **Execute Workflow** node enables modular, reusable workflow design by allowing one workflow to call and execute another workflow. This follows the hybrid approach inspired by n8n's workflow execution patterns.

---

## Problem Statement

Currently, the **Subgraph** node provides basic nested agent functionality, but lacks:
- Easy workflow selection from existing workflows
- Input/output data mapping
- Execution mode options (sync/async)
- Error handling strategies
- Visibility into child workflow execution

---

## Solution: Execute Workflow Node

Replace the Subgraph node with a more powerful **Execute Workflow** node that provides:

1. **Workflow Selection** - Browse and select from saved workflows
2. **Data Mapping** - Map parent state to child inputs and vice versa
3. **Execution Control** - Sync, async, and timeout options
4. **Error Handling** - Configurable error strategies

---

## Architecture

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Parent Workflow                                                │
│                                                                 │
│  ┌───────┐    ┌───────────┐    ┌──────────────────┐    ┌─────┐ │
│  │ INPUT │───▶│ LLM_AGENT │───▶│ EXECUTE_WORKFLOW │───▶│ OUT │ │
│  └───────┘    └───────────┘    └────────┬─────────┘    └─────┘ │
│                                         │                       │
│                                         ▼                       │
│                               ┌─────────────────┐               │
│                               │ Child Workflow  │               │
│                               │                 │               │
│                               │ INPUT → LLM → OUT               │
│                               └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Parent State                    Child Workflow                 Parent State
─────────────                   ──────────────                 ─────────────
{                               {                              {
  user_query: "..."    ──────▶    input: "..."                   user_query: "...",
  context: {...}       ──────▶    context: {...}                 context: {...},
  user_id: "123"                  ...                            workflow_result: "...", ◀──
}                               }                                tokens_used: 150        ◀──
                                         │                     }
                                         ▼
                                {
                                  result: "..."       ──────▶
                                  tokens_used: 150    ──────▶
                                }
```

---

## Node Configuration

### Node Type Definition

```typescript
interface ExecuteWorkflowNodeData {
  label: string;
  workflowId: string | null;          // Selected workflow ID
  workflowName?: string;              // Display name (cached)

  // Execution Settings
  executionMode: 'sync' | 'async' | 'async_callback';
  timeout: number;                     // Timeout in ms (for sync mode)

  // Input Mapping
  inputMapping: InputMapping[];

  // Output Mapping
  outputMapping: OutputMapping[];

  // Error Handling
  onError: 'stop' | 'continue' | 'fallback';
  fallbackValue?: any;

  // Advanced
  passFullState: boolean;              // Pass entire parent state
  inheritCredentials: boolean;         // Use parent's credentials
}

interface InputMapping {
  id: string;
  sourceField: string;      // Field from parent state
  targetField: string;      // Field in child workflow input
  transform?: string;       // Optional JSONPath or expression
}

interface OutputMapping {
  id: string;
  sourceField: string;      // Field from child output
  targetField: string;      // Field to set in parent state
  transform?: string;       // Optional transformation
}
```

### Node Schema

```typescript
// Add to nodeSchemas.ts
export const executeWorkflowSchema = z.object({
  label: z.string().default('Execute Workflow'),
  workflowId: z.string().nullable().default(null),
  workflowName: z.string().optional(),

  executionMode: z.enum(['sync', 'async', 'async_callback']).default('sync'),
  timeout: z.number().min(1000).max(300000).default(30000),

  inputMapping: z.array(z.object({
    id: z.string(),
    sourceField: z.string(),
    targetField: z.string(),
    transform: z.string().optional(),
  })).default([]),

  outputMapping: z.array(z.object({
    id: z.string(),
    sourceField: z.string(),
    targetField: z.string(),
    transform: z.string().optional(),
  })).default([]),

  onError: z.enum(['stop', 'continue', 'fallback']).default('stop'),
  fallbackValue: z.any().optional(),

  passFullState: z.boolean().default(false),
  inheritCredentials: z.boolean().default(true),
});
```

---

## UI Components

### Property Panel Configuration

```
┌─────────────────────────────────────────┐
│ Execute Workflow Properties             │
├─────────────────────────────────────────┤
│                                         │
│ Workflow *                              │
│ ┌─────────────────────────────────────┐ │
│ │ 🔍 Select a workflow...           ▼ │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ─────────────────────────────────────── │
│ EXECUTION SETTINGS                      │
│ ─────────────────────────────────────── │
│                                         │
│ Execution Mode                          │
│ ○ Wait for completion (Sync)            │
│ ○ Run in background (Async)             │
│ ○ Async with callback                   │
│                                         │
│ Timeout (ms)         [30000        ]    │
│                                         │
│ ─────────────────────────────────────── │
│ INPUT MAPPING                           │
│ ─────────────────────────────────────── │
│                                         │
│ ┌─────────────┬─────────────┬────────┐  │
│ │ Parent Field│ Child Input │ Action │  │
│ ├─────────────┼─────────────┼────────┤  │
│ │ user_query  │ input       │   🗑   │  │
│ │ context     │ context     │   🗑   │  │
│ └─────────────┴─────────────┴────────┘  │
│ [+ Add Input Mapping]                   │
│                                         │
│ ─────────────────────────────────────── │
│ OUTPUT MAPPING                          │
│ ─────────────────────────────────────── │
│                                         │
│ ┌─────────────┬─────────────┬────────┐  │
│ │ Child Output│ Parent Field│ Action │  │
│ ├─────────────┼─────────────┼────────┤  │
│ │ result      │ wf_result   │   🗑   │  │
│ │ tokens      │ wf_tokens   │   🗑   │  │
│ └─────────────┴─────────────┴────────┘  │
│ [+ Add Output Mapping]                  │
│                                         │
│ ─────────────────────────────────────── │
│ ERROR HANDLING                          │
│ ─────────────────────────────────────── │
│                                         │
│ On Error                                │
│ ○ Stop parent workflow                  │
│ ○ Continue with error in state          │
│ ○ Use fallback value                    │
│                                         │
│ ─────────────────────────────────────── │
│ ADVANCED                                │
│ ─────────────────────────────────────── │
│                                         │
│ ☐ Pass full parent state                │
│ ☑ Inherit parent credentials            │
│                                         │
└─────────────────────────────────────────┘
```

### Node Visual (Canvas)

```
┌────────────────────────────┐
│  ⚡ Execute Workflow       │
├────────────────────────────┤
│  📋 Customer Support Bot   │
│  Mode: Sync | Timeout: 30s │
│  Inputs: 2 | Outputs: 1    │
└────────────────────────────┘
```

---

## Backend Implementation

### LangGraph Engine Handler

```python
# In langgraph_engine.py

async def execute_workflow_node(state: AgentState, config: dict) -> AgentState:
    """
    Execute another workflow and merge results into current state.
    """
    node_config = config.get('node_config', {})

    workflow_id = node_config.get('workflowId')
    execution_mode = node_config.get('executionMode', 'sync')
    timeout = node_config.get('timeout', 30000)
    input_mapping = node_config.get('inputMapping', [])
    output_mapping = node_config.get('outputMapping', [])
    on_error = node_config.get('onError', 'stop')
    pass_full_state = node_config.get('passFullState', False)

    if not workflow_id:
        raise ValueError("No workflow selected for Execute Workflow node")

    # Build child workflow input
    if pass_full_state:
        child_input = dict(state)
    else:
        child_input = {}
        for mapping in input_mapping:
            source_value = get_nested_value(state, mapping['sourceField'])
            if mapping.get('transform'):
                source_value = apply_transform(source_value, mapping['transform'])
            set_nested_value(child_input, mapping['targetField'], source_value)

    try:
        # Execute child workflow
        if execution_mode == 'sync':
            result = await execute_workflow_sync(
                workflow_id=workflow_id,
                input_data=child_input,
                timeout=timeout,
                inherit_credentials=node_config.get('inheritCredentials', True)
            )
        elif execution_mode == 'async':
            # Fire and forget
            asyncio.create_task(execute_workflow_async(
                workflow_id=workflow_id,
                input_data=child_input
            ))
            result = {'status': 'started', 'workflow_id': workflow_id}
        else:
            # Async with callback - store execution ID for later retrieval
            execution_id = await start_workflow_execution(
                workflow_id=workflow_id,
                input_data=child_input
            )
            result = {'execution_id': execution_id, 'status': 'running'}

        # Map outputs back to parent state
        new_state = dict(state)
        for mapping in output_mapping:
            source_value = get_nested_value(result, mapping['sourceField'])
            if mapping.get('transform'):
                source_value = apply_transform(source_value, mapping['transform'])
            set_nested_value(new_state, mapping['targetField'], source_value)

        return AgentState(**new_state)

    except Exception as e:
        if on_error == 'stop':
            raise
        elif on_error == 'continue':
            new_state = dict(state)
            new_state['workflow_error'] = str(e)
            return AgentState(**new_state)
        else:  # fallback
            new_state = dict(state)
            fallback = node_config.get('fallbackValue', {})
            for mapping in output_mapping:
                set_nested_value(new_state, mapping['targetField'], fallback)
            return AgentState(**new_state)
```

### API Endpoint for Workflow List

```python
# In api/v1/workflows.py

@router.get("/workflows/list", response_model=WorkflowListResponse)
async def list_workflows_for_selector(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    search: str = Query(None),
    exclude_id: str = Query(None),  # Exclude current workflow to prevent recursion
):
    """
    Get list of workflows for the Execute Workflow node selector.
    Returns minimal data needed for selection.
    """
    query = select(Workflow).where(
        Workflow.organization_id == current_user.organization_id,
        Workflow.status.in_(['draft', 'deployed'])
    )

    if search:
        query = query.where(Workflow.name.ilike(f'%{search}%'))

    if exclude_id:
        query = query.where(Workflow.id != exclude_id)

    query = query.order_by(Workflow.updated_at.desc())

    result = await db.execute(query)
    workflows = result.scalars().all()

    return {
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "status": w.status,
                "nodeCount": len(w.config.get('nodes', [])) if w.config else 0,
                "updatedAt": w.updated_at.isoformat()
            }
            for w in workflows
        ]
    }
```

---

## File Changes Required

### Frontend

| File | Changes |
|------|---------|
| `types/nodeSchemas.ts` | Add `EXECUTE_WORKFLOW` type and schema |
| `types/workflow.ts` | Add ExecuteWorkflowNodeData interface |
| `components/AgentBuilder/nodes/ExecuteWorkflowNode.tsx` | New node component |
| `components/AgentBuilder/nodes/index.ts` | Export new node |
| `components/AgentBuilder/NodeLibrary.tsx` | Add to node palette |
| `components/AgentBuilder/PropertyPanel.tsx` | Add configuration UI |
| `features/workflows/workflowService.ts` | Add workflow list API |
| `features/workflows/workflowHooks.ts` | Add useWorkflowList hook |

### Backend

| File | Changes |
|------|---------|
| `services/langgraph_engine.py` | Add `execute_workflow_node` handler |
| `api/v1/workflows.py` | Add `/workflows/list` endpoint |
| `schemas/workflow.py` | Add WorkflowListResponse schema |

---

## Use Cases

### 1. Modular Customer Support

```
Main Support Workflow
├── INPUT
├── LLM_AGENT (Intent Classification)
├── DECISION (Route by intent)
│   ├── billing → EXECUTE_WORKFLOW (Billing Handler)
│   ├── technical → EXECUTE_WORKFLOW (Tech Support)
│   └── general → EXECUTE_WORKFLOW (FAQ Handler)
└── OUTPUT
```

### 2. Data Processing Pipeline

```
Document Processing Workflow
├── INPUT (File upload)
├── EXECUTE_WORKFLOW (PDF Extractor)
├── EXECUTE_WORKFLOW (Text Chunker)
├── EXECUTE_WORKFLOW (Embedding Generator)
├── EXECUTE_WORKFLOW (Vector Store Writer)
└── OUTPUT (Success/Failure)
```

### 3. Multi-Agent Collaboration

```
Research Assistant Workflow
├── INPUT (Research query)
├── EXECUTE_WORKFLOW (Web Search Agent) → search_results
├── EXECUTE_WORKFLOW (Summarizer Agent) → summaries
├── EXECUTE_WORKFLOW (Fact Checker Agent) → verified_facts
├── LLM_AGENT (Compile final report)
└── OUTPUT
```

---

## Testing Plan

### Unit Tests

1. Input mapping correctly extracts values
2. Output mapping correctly sets values
3. Timeout handling works
4. Error handling modes work correctly
5. Async execution starts properly

### Integration Tests

1. Parent workflow can call child workflow
2. Nested workflows (child calls grandchild)
3. Circular reference detection
4. Credential inheritance
5. Large state passing

### E2E Tests

1. Create workflow with Execute Workflow node
2. Select child workflow from dropdown
3. Configure mappings
4. Execute and verify results
5. Test error scenarios

---

## Security Considerations

1. **Circular Reference Prevention**: Detect and prevent workflows calling themselves
2. **Depth Limit**: Maximum nesting depth (e.g., 10 levels)
3. **Permission Check**: Verify user has access to child workflow
4. **Credential Isolation**: Option to not inherit parent credentials
5. **Timeout Enforcement**: Prevent runaway executions

---

## Future Enhancements

1. **Workflow Versioning**: Execute specific version of workflow
2. **Parallel Execution**: Execute multiple workflows in parallel
3. **Conditional Execution**: Skip based on conditions
4. **Retry Logic**: Auto-retry failed workflow executions
5. **Execution History**: View child workflow execution details
6. **Visual Debugging**: Step into child workflow during testing

---

*Document Version: 1.0*
*Created: January 2026*
*Author: AgentStudio Team*
