from typing import Dict, List, Any


class AgentTemplates:
    """Pre-built agent templates."""

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """Get all available templates."""
        return [
            AgentTemplates.customer_service_agent(),
            AgentTemplates.research_agent(),
            AgentTemplates.data_analysis_agent(),
            AgentTemplates.workflow_agent(),
            AgentTemplates.qa_agent(),
        ]

    @staticmethod
    def customer_service_agent() -> Dict[str, Any]:
        """Customer Service Agent template."""
        return {
            "id": "customer_service",
            "name": "Customer Service Agent",
            "description": "Handles customer inquiries with FAQ retrieval, ticket routing, and sentiment analysis",
            "category": "Customer Support",
            "tags": ["support", "customer-service", "faq", "sentiment"],
            "config": {
                "nodes": [
                    {
                        "id": "input_1",
                        "type": "InputNode",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Customer Input",
                            "type": "INPUT",
                        },
                    },
                    {
                        "id": "rag_1",
                        "type": "RAGRetrieverNode",
                        "position": {"x": 300, "y": 100},
                        "data": {
                            "label": "Search FAQ",
                            "type": "RAG_RETRIEVER",
                            "config": {
                                "topK": 3,
                                "scoreThreshold": 0.8,
                            },
                        },
                    },
                    {
                        "id": "agent_1",
                        "type": "LLMAgentNode",
                        "position": {"x": 500, "y": 100},
                        "data": {
                            "label": "Customer Service Agent",
                            "type": "LLM_AGENT",
                            "config": {
                                "model": "gpt-3.5-turbo",
                                "temperature": 0.7,
                                "maxTokens": 500,
                                "systemPrompt": "You are a helpful customer service agent. Use the FAQ information provided to answer customer questions. Be polite, professional, and empathetic.",
                            },
                        },
                    },
                    {
                        "id": "decision_1",
                        "type": "DecisionNode",
                        "position": {"x": 700, "y": 100},
                        "data": {
                            "label": "Need Escalation?",
                            "type": "DECISION",
                            "config": {
                                "condition": "sentiment_negative or unresolved",
                            },
                        },
                    },
                    {
                        "id": "tool_1",
                        "type": "ToolNode",
                        "position": {"x": 900, "y": 50},
                        "data": {
                            "label": "Create Ticket",
                            "type": "TOOL",
                            "config": {
                                "toolId": "email_sender",
                            },
                        },
                    },
                    {
                        "id": "output_1",
                        "type": "OutputNode",
                        "position": {"x": 900, "y": 150},
                        "data": {
                            "label": "Response",
                            "type": "OUTPUT",
                        },
                    },
                ],
                "edges": [
                    {"source": "input_1", "target": "rag_1"},
                    {"source": "rag_1", "target": "agent_1"},
                    {"source": "agent_1", "target": "decision_1"},
                    {"source": "decision_1", "target": "tool_1"},
                    {"source": "decision_1", "target": "output_1"},
                    {"source": "tool_1", "target": "output_1"},
                ],
            },
        }

    @staticmethod
    def research_agent() -> Dict[str, Any]:
        """Research Agent template."""
        return {
            "id": "research",
            "name": "Research Agent",
            "description": "Analyzes documents, extracts facts, and generates summaries with citations",
            "category": "Research",
            "tags": ["research", "analysis", "citations", "documents"],
            "config": {
                "nodes": [
                    {
                        "id": "input_1",
                        "type": "InputNode",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Research Query",
                            "type": "INPUT",
                        },
                    },
                    {
                        "id": "tool_1",
                        "type": "ToolNode",
                        "position": {"x": 300, "y": 100},
                        "data": {
                            "label": "Web Search",
                            "type": "TOOL",
                            "config": {
                                "toolId": "web_search",
                            },
                        },
                    },
                    {
                        "id": "rag_1",
                        "type": "RAGRetrieverNode",
                        "position": {"x": 500, "y": 100},
                        "data": {
                            "label": "Document Search",
                            "type": "RAG_RETRIEVER",
                            "config": {
                                "topK": 5,
                                "scoreThreshold": 0.75,
                            },
                        },
                    },
                    {
                        "id": "agent_1",
                        "type": "LLMAgentNode",
                        "position": {"x": 700, "y": 100},
                        "data": {
                            "label": "Research Analyst",
                            "type": "LLM_AGENT",
                            "config": {
                                "model": "gpt-4",
                                "temperature": 0.3,
                                "maxTokens": 2000,
                                "systemPrompt": "You are a research analyst. Analyze the provided documents and web search results. Extract key facts, summarize findings, and always cite your sources.",
                            },
                        },
                    },
                    {
                        "id": "output_1",
                        "type": "OutputNode",
                        "position": {"x": 900, "y": 100},
                        "data": {
                            "label": "Research Report",
                            "type": "OUTPUT",
                        },
                    },
                ],
                "edges": [
                    {"source": "input_1", "target": "tool_1"},
                    {"source": "input_1", "target": "rag_1"},
                    {"source": "tool_1", "target": "agent_1"},
                    {"source": "rag_1", "target": "agent_1"},
                    {"source": "agent_1", "target": "output_1"},
                ],
            },
        }

    @staticmethod
    def data_analysis_agent() -> Dict[str, Any]:
        """Data Analysis Agent template."""
        return {
            "id": "data_analysis",
            "name": "Data Analysis Agent",
            "description": "Interprets queries, performs calculations, and generates insights",
            "category": "Analytics",
            "tags": ["analytics", "data", "insights", "calculations"],
            "config": {
                "nodes": [
                    {
                        "id": "input_1",
                        "type": "InputNode",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Analysis Query",
                            "type": "INPUT",
                        },
                    },
                    {
                        "id": "agent_1",
                        "type": "LLMAgentNode",
                        "position": {"x": 300, "y": 100},
                        "data": {
                            "label": "Query Interpreter",
                            "type": "LLM_AGENT",
                            "config": {
                                "model": "gpt-3.5-turbo",
                                "temperature": 0.2,
                                "maxTokens": 500,
                                "systemPrompt": "You are a data analyst. Interpret the user's query and determine what calculations or analysis are needed.",
                            },
                        },
                    },
                    {
                        "id": "tool_1",
                        "type": "ToolNode",
                        "position": {"x": 500, "y": 100},
                        "data": {
                            "label": "Calculator",
                            "type": "TOOL",
                            "config": {
                                "toolId": "calculator",
                            },
                        },
                    },
                    {
                        "id": "agent_2",
                        "type": "LLMAgentNode",
                        "position": {"x": 700, "y": 100},
                        "data": {
                            "label": "Insight Generator",
                            "type": "LLM_AGENT",
                            "config": {
                                "model": "gpt-4",
                                "temperature": 0.5,
                                "maxTokens": 1000,
                                "systemPrompt": "You are a data analyst. Given the calculation results, provide insights, trends, and recommendations.",
                            },
                        },
                    },
                    {
                        "id": "output_1",
                        "type": "OutputNode",
                        "position": {"x": 900, "y": 100},
                        "data": {
                            "label": "Analysis Report",
                            "type": "OUTPUT",
                        },
                    },
                ],
                "edges": [
                    {"source": "input_1", "target": "agent_1"},
                    {"source": "agent_1", "target": "tool_1"},
                    {"source": "tool_1", "target": "agent_2"},
                    {"source": "agent_2", "target": "output_1"},
                ],
            },
        }

    @staticmethod
    def workflow_agent() -> Dict[str, Any]:
        """Workflow Agent template."""
        return {
            "id": "workflow",
            "name": "Workflow Agent",
            "description": "Routes tasks, tracks status, and sends notifications across channels",
            "category": "Automation",
            "tags": ["automation", "workflow", "routing", "notifications"],
            "config": {
                "nodes": [
                    {
                        "id": "input_1",
                        "type": "InputNode",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Task Input",
                            "type": "INPUT",
                        },
                    },
                    {
                        "id": "decision_1",
                        "type": "DecisionNode",
                        "position": {"x": 300, "y": 100},
                        "data": {
                            "label": "Route Task",
                            "type": "DECISION",
                            "config": {
                                "condition": "task_type",
                            },
                        },
                    },
                    {
                        "id": "execute_workflow_1",
                        "type": "ExecuteWorkflowNode",
                        "position": {"x": 500, "y": 50},
                        "data": {
                            "label": "Process Task A",
                            "type": "EXECUTE_WORKFLOW",
                            "config": {
                                "workflowId": None,
                                "executionMode": "sync",
                                "timeout": 30000,
                                "inputMapping": [],
                                "outputMapping": [],
                                "onError": "stop",
                                "passFullState": False,
                                "inheritCredentials": True,
                            },
                        },
                    },
                    {
                        "id": "execute_workflow_2",
                        "type": "ExecuteWorkflowNode",
                        "position": {"x": 500, "y": 150},
                        "data": {
                            "label": "Process Task B",
                            "type": "EXECUTE_WORKFLOW",
                            "config": {
                                "workflowId": None,
                                "executionMode": "sync",
                                "timeout": 30000,
                                "inputMapping": [],
                                "outputMapping": [],
                                "onError": "stop",
                                "passFullState": False,
                                "inheritCredentials": True,
                            },
                        },
                    },
                    {
                        "id": "tool_1",
                        "type": "ToolNode",
                        "position": {"x": 700, "y": 100},
                        "data": {
                            "label": "Send Notification",
                            "type": "TOOL",
                            "config": {
                                "toolId": "slack_notification",
                            },
                        },
                    },
                    {
                        "id": "output_1",
                        "type": "OutputNode",
                        "position": {"x": 900, "y": 100},
                        "data": {
                            "label": "Status Update",
                            "type": "OUTPUT",
                        },
                    },
                ],
                "edges": [
                    {"source": "input_1", "target": "decision_1"},
                    {"source": "decision_1", "target": "execute_workflow_1"},
                    {"source": "decision_1", "target": "execute_workflow_2"},
                    {"source": "execute_workflow_1", "target": "tool_1"},
                    {"source": "execute_workflow_2", "target": "tool_1"},
                    {"source": "tool_1", "target": "output_1"},
                ],
            },
        }

    @staticmethod
    def qa_agent() -> Dict[str, Any]:
        """QA Agent template."""
        return {
            "id": "qa",
            "name": "QA Agent",
            "description": "Validates answers against knowledge base with source verification and confidence scoring",
            "category": "Quality Assurance",
            "tags": ["qa", "quality", "verification", "knowledge-base"],
            "config": {
                "nodes": [
                    {
                        "id": "input_1",
                        "type": "InputNode",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Question",
                            "type": "INPUT",
                        },
                    },
                    {
                        "id": "rag_1",
                        "type": "RAGRetrieverNode",
                        "position": {"x": 300, "y": 100},
                        "data": {
                            "label": "Knowledge Base Search",
                            "type": "RAG_RETRIEVER",
                            "config": {
                                "topK": 5,
                                "scoreThreshold": 0.85,
                            },
                        },
                    },
                    {
                        "id": "agent_1",
                        "type": "LLMAgentNode",
                        "position": {"x": 500, "y": 100},
                        "data": {
                            "label": "Answer Generator",
                            "type": "LLM_AGENT",
                            "config": {
                                "model": "gpt-4",
                                "temperature": 0.1,
                                "maxTokens": 1000,
                                "systemPrompt": "You are a QA specialist. Provide accurate answers based ONLY on the provided knowledge base. Include confidence scores and cite sources.",
                            },
                        },
                    },
                    {
                        "id": "decision_1",
                        "type": "DecisionNode",
                        "position": {"x": 700, "y": 100},
                        "data": {
                            "label": "High Confidence?",
                            "type": "DECISION",
                            "config": {
                                "condition": "confidence > 0.8",
                            },
                        },
                    },
                    {
                        "id": "tool_1",
                        "type": "ToolNode",
                        "position": {"x": 900, "y": 50},
                        "data": {
                            "label": "Web Verification",
                            "type": "TOOL",
                            "config": {
                                "toolId": "web_search",
                            },
                        },
                    },
                    {
                        "id": "output_1",
                        "type": "OutputNode",
                        "position": {"x": 900, "y": 150},
                        "data": {
                            "label": "Verified Answer",
                            "type": "OUTPUT",
                        },
                    },
                ],
                "edges": [
                    {"source": "input_1", "target": "rag_1"},
                    {"source": "rag_1", "target": "agent_1"},
                    {"source": "agent_1", "target": "decision_1"},
                    {"source": "decision_1", "target": "tool_1"},
                    {"source": "decision_1", "target": "output_1"},
                    {"source": "tool_1", "target": "output_1"},
                ],
            },
        }
