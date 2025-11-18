from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import operator


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    agent_config: dict
    current_node: str
    execution_path: list
    tool_results: dict
    final_output: str | None


class LangGraphEngine:
    """LangGraph-based agent execution engine."""

    def __init__(self):
        self.graphs = {}

    def build_graph_from_config(self, agent_config: dict) -> StateGraph:
        """Build a LangGraph workflow from agent configuration."""

        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes from config
        nodes = agent_config.get("nodes", [])
        edges = agent_config.get("edges", [])

        # Register node handlers
        for node in nodes:
            node_type = node.get("data", {}).get("type")
            node_id = node.get("id")

            if node_type == "INPUT":
                workflow.add_node(node_id, self._handle_input_node)
            elif node_type == "LLM_AGENT":
                workflow.add_node(node_id, self._handle_llm_agent_node)
            elif node_type == "RAG_RETRIEVER":
                workflow.add_node(node_id, self._handle_rag_retriever_node)
            elif node_type == "DECISION":
                workflow.add_node(node_id, self._handle_decision_node)
            elif node_type == "TOOL":
                workflow.add_node(node_id, self._handle_tool_node)
            elif node_type == "OUTPUT":
                workflow.add_node(node_id, self._handle_output_node)
            elif node_type == "SUBGRAPH":
                workflow.add_node(node_id, self._handle_subgraph_node)

        # Add edges
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            workflow.add_edge(source, target)

        # Set entry point (find INPUT node)
        input_node = next((n for n in nodes if n.get("data", {}).get("type") == "INPUT"), None)
        if input_node:
            workflow.set_entry_point(input_node["id"])

        # Find output node and connect to END
        output_node = next((n for n in nodes if n.get("data", {}).get("type") == "OUTPUT"), None)
        if output_node:
            workflow.add_edge(output_node["id"], END)

        return workflow.compile()

    def _handle_input_node(self, state: AgentState) -> AgentState:
        """Handle INPUT node - initialize agent state."""
        state["execution_path"].append("INPUT")
        return state

    def _handle_llm_agent_node(self, state: AgentState) -> AgentState:
        """Handle LLM_AGENT node - process with language model."""
        state["execution_path"].append("LLM_AGENT")

        # Get LLM configuration from agent config
        # In production, this would call the actual LLM
        messages = state["messages"]

        # Mock LLM response for now
        response = AIMessage(content="Agent response placeholder")
        state["messages"].append(response)

        return state

    def _handle_rag_retriever_node(self, state: AgentState) -> AgentState:
        """Handle RAG_RETRIEVER node - retrieve from knowledge base."""
        state["execution_path"].append("RAG_RETRIEVER")

        # In production, this would query the RAG system
        # For now, return mock retrieval
        state["tool_results"]["rag_retrieval"] = {
            "documents": [],
            "scores": [],
        }

        return state

    def _handle_decision_node(self, state: AgentState) -> AgentState:
        """Handle DECISION node - conditional routing."""
        state["execution_path"].append("DECISION")

        # Evaluate decision condition
        # In production, this would evaluate the condition logic

        return state

    def _handle_tool_node(self, state: AgentState) -> AgentState:
        """Handle TOOL node - execute tool."""
        state["execution_path"].append("TOOL")

        # In production, this would execute the actual tool
        # For now, return mock result

        return state

    def _handle_output_node(self, state: AgentState) -> AgentState:
        """Handle OUTPUT node - format final response."""
        state["execution_path"].append("OUTPUT")

        # Format final output
        if state["messages"]:
            last_message = state["messages"][-1]
            state["final_output"] = last_message.content

        return state

    def _handle_subgraph_node(self, state: AgentState) -> AgentState:
        """Handle SUBGRAPH node - nested workflow."""
        state["execution_path"].append("SUBGRAPH")
        return state

    async def execute_agent(self, agent_config: dict, user_input: str) -> dict:
        """Execute an agent with given input."""

        # Build graph from config
        graph = self.build_graph_from_config(agent_config)

        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "agent_config": agent_config,
            "current_node": "",
            "execution_path": [],
            "tool_results": {},
            "final_output": None,
        }

        # Execute graph
        result = await graph.ainvoke(initial_state)

        return {
            "output": result.get("final_output"),
            "execution_path": result.get("execution_path"),
            "messages": [{"role": m.type, "content": m.content} for m in result.get("messages", [])],
            "tool_results": result.get("tool_results"),
        }
