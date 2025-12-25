"""LLM Client service for unified multi-provider LLM interactions."""

from typing import Optional, Dict, Any, List, AsyncIterator, Union
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

from app.models.credential import Credential


class LLMResponse(BaseModel):
    """Standardized LLM response."""
    content: str
    role: str = "assistant"
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None


class LLMClient:
    """Unified LLM client for all providers."""

    @staticmethod
    def create_client(
        credential: Credential,
        model_config: Dict[str, Any]
    ) -> BaseChatModel:
        """Create appropriate LLM client based on credential provider.

        Args:
            credential: Credential object with provider and API key
            model_config: Model configuration including model name, temperature, etc.

        Returns:
            BaseChatModel: LangChain chat model instance

        Raises:
            ValueError: If provider is not supported
        """
        provider = credential.provider
        api_key = credential.api_key

        # Extract model configuration
        model = model_config.get("model", "gpt-4")
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("maxTokens", 2048)
        top_p = model_config.get("topP")

        # Build credential config from Credential model fields
        credential_config = {
            "api_base": credential.api_base,
            "api_version": credential.api_version,
            "organization_key": credential.organization_key,
        }

        # Provider-specific initialization
        if provider == "openai":
            return LLMClient._create_openai_client(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                credential_config=credential_config
            )

        elif provider == "anthropic":
            return LLMClient._create_anthropic_client(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                credential_config=credential_config
            )

        elif provider == "google":
            return LLMClient._create_google_client(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                credential_config=credential_config
            )

        elif provider == "azure_openai":
            return LLMClient._create_azure_client(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                credential_config=credential_config
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def _create_openai_client(
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float],
        credential_config: Dict[str, Any]
    ) -> ChatOpenAI:
        """Create OpenAI chat client."""
        params = {
            "api_key": api_key,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add optional parameters
        if top_p is not None:
            params["top_p"] = top_p

        # Add base URL if provided (for OpenAI-compatible APIs)
        if base_url := credential_config.get("base_url"):
            params["base_url"] = base_url

        # Add organization if provided
        if organization := credential_config.get("organization"):
            params["organization"] = organization

        return ChatOpenAI(**params)

    @staticmethod
    def _create_anthropic_client(
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float],
        credential_config: Dict[str, Any]
    ) -> ChatAnthropic:
        """Create Anthropic chat client."""
        params = {
            "api_key": api_key,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add optional parameters
        if top_p is not None:
            params["top_p"] = top_p

        # Add base URL if provided
        if base_url := credential_config.get("base_url"):
            params["base_url"] = base_url

        return ChatAnthropic(**params)

    @staticmethod
    def _create_google_client(
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        credential_config: Dict[str, Any]
    ) -> BaseChatModel:
        """Create Google AI chat client."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            params = {
                "google_api_key": api_key,
                "model": model,
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            return ChatGoogleGenerativeAI(**params)
        except ImportError:
            raise ImportError(
                "langchain-google-genai is not installed. "
                "Install it with: pip install langchain-google-genai"
            )

    @staticmethod
    def _create_azure_client(
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        credential_config: Dict[str, Any]
    ) -> ChatOpenAI:
        """Create Azure OpenAI chat client."""
        azure_endpoint = credential_config.get("azure_endpoint")
        api_version = credential_config.get("api_version", "2024-02-01")
        deployment_name = credential_config.get("deployment_name", model)

        if not azure_endpoint:
            raise ValueError("Azure endpoint is required for Azure OpenAI")

        return ChatOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            azure_deployment=deployment_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    async def invoke(
        client: BaseChatModel,
        messages: List[BaseMessage],
        tools: Optional[List[Any]] = None,
        **kwargs
    ) -> AIMessage:
        """Invoke LLM with optional tool binding.

        Args:
            client: LangChain chat model instance
            messages: List of messages to send
            tools: Optional list of tools to bind to the model
            **kwargs: Additional arguments to pass to the model

        Returns:
            AIMessage: Response from the LLM
        """
        # Bind tools if provided
        if tools:
            client = client.bind_tools(tools)

        # Invoke the model
        response = await client.ainvoke(messages, **kwargs)

        return response

    @staticmethod
    async def stream(
        client: BaseChatModel,
        messages: List[BaseMessage],
        tools: Optional[List[Any]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream LLM response.

        Args:
            client: LangChain chat model instance
            messages: List of messages to send
            tools: Optional list of tools to bind to the model
            **kwargs: Additional arguments to pass to the model

        Yields:
            str: Chunks of the response content
        """
        # Bind tools if provided
        if tools:
            client = client.bind_tools(tools)

        # Stream the response
        async for chunk in client.astream(messages, **kwargs):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content

    @staticmethod
    def extract_usage(response: AIMessage) -> Dict[str, int]:
        """Extract token usage from LLM response.

        Args:
            response: AIMessage from LLM

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens
        """
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

        # Try to extract from response metadata
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata

            # OpenAI format
            if "token_usage" in metadata:
                token_usage = metadata["token_usage"]
                usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
                usage["completion_tokens"] = token_usage.get("completion_tokens", 0)
                usage["total_tokens"] = token_usage.get("total_tokens", 0)

            # Anthropic format
            elif "usage" in metadata:
                anthropic_usage = metadata["usage"]
                usage["prompt_tokens"] = anthropic_usage.get("input_tokens", 0)
                usage["completion_tokens"] = anthropic_usage.get("output_tokens", 0)
                usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

        return usage

    @staticmethod
    def calculate_cost(
        usage: Dict[str, int],
        model: str,
        provider: str
    ) -> float:
        """Calculate approximate cost in USD.

        Args:
            usage: Token usage dict
            model: Model name
            provider: Provider name

        Returns:
            float: Cost in USD (cents)
        """
        # Pricing as of 2024 (per 1M tokens)
        PRICING = {
            "openai": {
                "gpt-4": {"input": 30.0, "output": 60.0},
                "gpt-4-turbo": {"input": 10.0, "output": 30.0},
                "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            },
            "anthropic": {
                "claude-3-opus": {"input": 15.0, "output": 75.0},
                "claude-3-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3-haiku": {"input": 0.25, "output": 1.25},
            },
        }

        pricing = PRICING.get(provider, {}).get(model)
        if not pricing:
            return 0.0

        input_cost = (usage["prompt_tokens"] / 1_000_000) * pricing["input"]
        output_cost = (usage["completion_tokens"] / 1_000_000) * pricing["output"]

        return input_cost + output_cost
