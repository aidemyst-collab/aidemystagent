# Guardrails Integration Implementation

## Status: COMPLETE

---

## Overview

Hybrid guardrails system for RAG workflows with 3 validation phases:
- **Input**: Before RAG retrieval
- **Retrieval**: After RAG, before LLM
- **Output**: After LLM response

---

## Backend Guardrails (13 Total)

| Phase | Guardrail | Type | Status |
|-------|-----------|------|--------|
| **Input** | QueryLength | Rule | Done |
| **Input** | PIIDetection | Rule | Done |
| **Input** | PromptInjection | Hybrid | Done |
| **Input** | Toxicity | LLM | Done |
| **Input** | QuerySanitization | Rule | Done (system) |
| **Retrieval** | ScoreThreshold | Rule | Done |
| **Retrieval** | TokenLimit | Rule | Done |
| **Retrieval** | ChunkDeduplication | Rule | Done |
| **Retrieval** | SourceDiversity | Rule | Done |
| **Output** | HallucinationDetection | LLM | Done |
| **Output** | FactualGrounding | LLM | Done |
| **Output** | PIILeakage | Rule | Done |
| **Output** | CitationVerification | Hybrid | Done |

---

## Files Created (Complete)

```
backend/app/services/guardrails/
├── __init__.py              # Module exports
├── base.py                  # Base classes, ViolationType, ViolationSeverity
├── guardrail_service.py     # Orchestration, org/workflow merge
├── input_guardrails.py      # 5 input guardrails
├── retrieval_guardrails.py  # 4 retrieval guardrails
└── output_guardrails.py     # 4 output guardrails

backend/app/api/v1/organization_settings.py    # API endpoints
backend/app/schemas/organization_settings.py   # Pydantic schemas

frontend/src/pages/OrganizationSettings.tsx           # Settings page (4 tabs)
frontend/src/types/organizationSettings.ts            # TypeScript types
frontend/src/features/organization/organizationSettingsService.ts  # API service
frontend/src/features/organization/useOrganizationSettings.ts      # React hooks
```

---

## UI Coverage

| Phase | Guardrail | In UI? |
|-------|-----------|--------|
| Input | PII Detection | Yes |
| Input | Prompt Injection | Yes |
| Input | Toxicity | Yes |
| Input | Query Length | Yes |
| Retrieval | Score Threshold | Yes |
| Retrieval | Token Limit | Yes |
| Retrieval | Deduplication | Yes |
| Retrieval | Source Diversity | Yes |
| Output | Hallucination Detection | Yes |
| Output | PII Leakage | Yes |
| Output | Factual Grounding | Yes |
| Output | Citation Verification | Yes |

---

## Completed Tasks

### 1. LangGraph Engine Integration (DONE)

**File:** `backend/app/services/langgraph_engine.py`

#### 1.1 Completed:
- Added imports: `from app.services.guardrails import GuardrailService, GuardrailResult`
- Added state fields: `guardrails_config`, `guardrails_results`

#### 1.2 Add _initialize_guardrails method (after __init__ ~line 263):
```python
async def _initialize_guardrails(
    self,
    organization_id: Optional[str],
    workflow_guardrails: Optional[Dict[str, Any]] = None
) -> Optional[GuardrailService]:
    """Initialize GuardrailService with org + workflow config merge."""
    if not organization_id:
        return None
    try:
        return await GuardrailService.create_with_org_merge(
            org_id=organization_id,
            workflow_config=workflow_guardrails or {},
            db=self.db,
            llm_client=None
        )
    except Exception as e:
        logger.warning(f"Failed to initialize guardrails: {e}")
        return None
```

#### 1.3 Add input guardrails in _handle_input_node (~line 492, after messages set):
```python
# Run input guardrails if configured
guardrail_service = state.get("_guardrail_service")
if guardrail_service and mode != "audio":
    try:
        input_result = await guardrail_service.validate_input(message_content)
        if "guardrails_results" not in state or state["guardrails_results"] is None:
            state["guardrails_results"] = {}
        state["guardrails_results"]["input"] = input_result.model_dump()

        # Check if should block
        fail_action = state.get("guardrails_config", {}).get("global", {}).get("failAction", "warn")
        if not input_result.passed and fail_action == "block":
            error_msg = f"Input blocked: {[v.message for v in input_result.violations]}"
            state["final_output"] = error_msg
            raise ValueError(error_msg)
    except ValueError:
        raise
    except Exception as e:
        logger.warning(f"Input guardrails error: {e}")
```

#### 1.4 Add retrieval guardrails in _handle_llm_agent_node (~line 1118, after rag_chunks):
```python
# Run retrieval guardrails
guardrail_service = state.get("_guardrail_service")
if guardrail_service and rag_chunks:
    try:
        retrieval_result = await guardrail_service.validate_retrieval(rag_chunks)
        if "guardrails_results" not in state or state["guardrails_results"] is None:
            state["guardrails_results"] = {}
        state["guardrails_results"]["retrieval"] = retrieval_result.model_dump()

        # Use filtered chunks from guardrails
        if "filtered_chunks" in retrieval_result.metadata:
            rag_chunks = retrieval_result.metadata["filtered_chunks"]
            logger.info(f"Retrieval guardrails: {retrieval_result.metadata.get('original_count')} -> {len(rag_chunks)} chunks")
    except Exception as e:
        logger.warning(f"Retrieval guardrails error: {e}")
```

#### 1.5 Add output guardrails in _handle_llm_agent_node (~line 1287, after response):
```python
# Run output guardrails
guardrail_service = state.get("_guardrail_service")
if guardrail_service:
    try:
        response_text = response.content if hasattr(response, 'content') else str(response)
        output_result = await guardrail_service.validate_output(
            response=response_text,
            context=rag_context or "",
            sources=rag_chunks if rag_chunks else []
        )
        if "guardrails_results" not in state or state["guardrails_results"] is None:
            state["guardrails_results"] = {}
        state["guardrails_results"]["output"] = output_result.model_dump()

        # Log violations but don't block (output already generated)
        if not output_result.passed:
            logger.warning(f"Output guardrails violations: {[v.message for v in output_result.violations]}")
    except Exception as e:
        logger.warning(f"Output guardrails error: {e}")
```

#### 1.6 Update execute_agent method (~line 3151):

Add to initial_state dict:
```python
"guardrails_config": agent_config.get("guardrails"),
"guardrails_results": {},
"_guardrail_service": None,  # Will be set below
```

Before graph execution (after initial_state):
```python
# Initialize guardrails service
guardrail_service = await self._initialize_guardrails(
    organization_id=organization_id,
    workflow_guardrails=agent_config.get("guardrails")
)
if guardrail_service:
    initial_state["_guardrail_service"] = guardrail_service
```

Add to return dict:
```python
"guardrails_results": result.get("guardrails_results", {}),
```

---

### 2. Add Missing UI Elements (DONE)

**File:** `frontend/src/pages/OrganizationSettings.tsx`

#### 2.1 Add to Retrieval Panel (~line 256, after Token Limit card):

```tsx
<Card size="small" title="Deduplication">
  <Form.Item name="enforcedDeduplication" valuePropName="checked" className="mb-2">
    <Switch /> <Text className="ml-2">Enforce Chunk Deduplication</Text>
  </Form.Item>
  <Form.Item name="enforcedDeduplicationThreshold" label="Similarity Threshold" className="mb-0">
    <InputNumber min={0.5} max={1} step={0.05} style={{ width: '100%' }} />
  </Form.Item>
</Card>

<Card size="small" title="Source Diversity">
  <Form.Item name="enforcedSourceDiversity" valuePropName="checked" className="mb-2">
    <Switch /> <Text className="ml-2">Enforce Source Diversity</Text>
  </Form.Item>
  <Form.Item name="enforcedMinSources" label="Min Sources" className="mb-0">
    <InputNumber min={1} max={10} style={{ width: '100%' }} />
  </Form.Item>
</Card>
```

#### 2.2 Add to Output Panel (~line 286, after PII Leakage card):

```tsx
<Card size="small" title="Factual Grounding">
  <Form.Item name="enforcedFactualGrounding" valuePropName="checked" className="mb-2">
    <Switch /> <Text className="ml-2">Enforce Factual Grounding</Text>
  </Form.Item>
  <Form.Item name="enforcedFactualMinScore" label="Min Score" className="mb-0">
    <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
  </Form.Item>
</Card>

<Card size="small" title="Citation Verification">
  <Form.Item name="enforcedCitationVerification" valuePropName="checked" className="mb-0">
    <Switch /> <Text className="ml-2">Enforce Citation Verification</Text>
  </Form.Item>
  <Text type="secondary" className="text-xs">
    Verifies citations in responses match sources
  </Text>
</Card>
```

#### 2.3 Update useEffect form values (~line 79):
Add:
```tsx
// Retrieval
enforcedDeduplication: settings.guardrails.enforced?.retrieval?.deduplication?.enabled ?? false,
enforcedDeduplicationThreshold: settings.guardrails.enforced?.retrieval?.deduplication?.threshold ?? 0.9,
enforcedSourceDiversity: settings.guardrails.enforced?.retrieval?.sourceDiversity?.enabled ?? false,
enforcedMinSources: settings.guardrails.enforced?.retrieval?.sourceDiversity?.minSources ?? 2,

// Output
enforcedFactualGrounding: settings.guardrails.enforced?.output?.factualGrounding?.enabled ?? false,
enforcedFactualMinScore: settings.guardrails.enforced?.output?.factualGrounding?.minScore ?? 0.8,
enforcedCitationVerification: settings.guardrails.enforced?.output?.citationVerification?.enabled ?? false,
```

#### 2.4 Update handleSave update object (~line 129):
Add to retrieval:
```tsx
deduplication: values.enforcedDeduplication
  ? { enabled: true, threshold: values.enforcedDeduplicationThreshold }
  : undefined,
sourceDiversity: values.enforcedSourceDiversity
  ? { enabled: true, minSources: values.enforcedMinSources }
  : undefined,
```

Add to output:
```tsx
factualGrounding: values.enforcedFactualGrounding
  ? { enabled: true, minScore: values.enforcedFactualMinScore }
  : undefined,
citationVerification: values.enforcedCitationVerification
  ? { enabled: true }
  : undefined,
```

---

## Testing Checklist (Manual Testing Required)

- [ ] Organization Settings page loads at `/settings`
- [ ] Guardrails tab shows all 12 configurable guardrails
- [ ] Save button persists settings to database
- [ ] Workflow execution applies input guardrails
- [ ] Workflow execution applies retrieval guardrails (filters chunks)
- [ ] Workflow execution applies output guardrails
- [ ] Guardrails results returned in execution response
- [ ] Block action stops execution on violation
- [ ] Warn action logs but continues

## Implementation Summary

| Component | Changes Made |
|-----------|--------------|
| `langgraph_engine.py` | Added imports, state fields, `_initialize_guardrails()`, input/retrieval/output validation |
| `OrganizationSettings.tsx` | Added 4 missing guardrail cards + form fields + save handler |
| `GUARDRAILS_INTEGRATION.md` | Documentation updated |

---

## Git Status (Untracked Files)

```
backend/app/api/v1/organization_settings.py
backend/app/schemas/organization_settings.py
backend/app/services/guardrails/
frontend/src/features/organization/
frontend/src/pages/OrganizationSettings.tsx
frontend/src/types/organizationSettings.ts
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LangGraphEngine                               │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ INPUT Node   │───▶│  LLM_AGENT   │───▶│ OUTPUT Node  │          │
│  │              │    │    Node      │    │              │          │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘          │
│         │                   │                                       │
│         ▼                   ▼                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │    INPUT     │    │  RETRIEVAL   │    │   OUTPUT     │          │
│  │  Guardrails  │    │  Guardrails  │    │  Guardrails  │          │
│  │  (validate)  │    │  (filter)    │    │  (verify)    │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GuardrailService                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Config Merge: Org Enforced + Workflow = Final Config       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  validate_input() ──▶ validate_retrieval() ──▶ validate_output()    │
└─────────────────────────────────────────────────────────────────────┘
```
