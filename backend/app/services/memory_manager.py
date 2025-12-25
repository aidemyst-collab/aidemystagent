"""Memory Manager service for conversation history management."""

from typing import List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
)
import redis.asyncio as aioredis
import json
from datetime import datetime, timedelta


class MemoryManager:
    """Manages conversation memory for agents."""

    def __init__(self, redis_client: aioredis.Redis):
        """Initialize memory manager with Redis client.

        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client

    async def load_session_memory(
        self,
        session_id: str,
        config: Dict[str, Any]
    ) -> List[BaseMessage]:
        """Load conversation history from persistent storage.

        Args:
            session_id: Unique session identifier
            config: Memory configuration

        Returns:
            List[BaseMessage]: Conversation history
        """
        if not config.get("persistence", {}).get("enabled"):
            return []

        backend = config.get("persistence", {}).get("backend", "redis")

        if backend == "redis":
            key = f"memory:session:{session_id}"
            data = await self.redis.get(key)
            if data:
                messages_data = json.loads(data)
                return self._deserialize_messages(messages_data)

        # Add support for postgres, mongodb backends here...

        return []

    async def save_session_memory(
        self,
        session_id: str,
        messages: List[BaseMessage],
        config: Dict[str, Any]
    ):
        """Save conversation history to persistent storage.

        Args:
            session_id: Unique session identifier
            messages: List of messages to save
            config: Memory configuration
        """
        if not config.get("persistence", {}).get("enabled"):
            return

        backend = config.get("persistence", {}).get("backend", "redis")

        if backend == "redis":
            key = f"memory:session:{session_id}"
            messages_data = self._serialize_messages(messages)

            # Set TTL (default 7 days)
            ttl_days = config.get("persistence", {}).get("ttlDays", 7)
            ttl_seconds = ttl_days * 86400

            await self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(messages_data)
            )

        # Add support for postgres, mongodb backends here...

    async def apply_window(
        self,
        messages: List[BaseMessage],
        window_size: int
    ) -> List[BaseMessage]:
        """Apply window size to conversation history.

        Args:
            messages: Full conversation history
            window_size: Maximum number of messages to keep

        Returns:
            List[BaseMessage]: Windowed messages
        """
        if window_size <= 0:
            return messages

        # Keep system messages + last N user/assistant messages
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        conversation_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        # Apply window to conversation messages
        windowed_conversation = conversation_messages[-window_size:]

        return system_messages + windowed_conversation

    async def get_memory_context(
        self,
        session_id: Optional[str],
        config: Dict[str, Any],
        current_input: str
    ) -> Dict[str, Any]:
        """Get memory context to inject into LLM.

        Args:
            session_id: Optional session identifier
            config: Memory configuration
            current_input: Current user input

        Returns:
            Dict with chat_history and other memory context
        """
        memory_type = config.get("type", "buffer-window")
        window_size = config.get("windowSize", 10)

        # Load conversation history if session exists
        if session_id and config.get("persistence", {}).get("enabled"):
            history = await self.load_session_memory(session_id, config)
        else:
            history = []

        # Apply window if configured
        if memory_type == "buffer-window":
            history = await self.apply_window(history, window_size)

        return {
            "chat_history": history,
            "session_id": session_id,
            "memory_type": memory_type
        }

    async def update_memory(
        self,
        session_id: Optional[str],
        user_message: BaseMessage,
        ai_message: BaseMessage,
        existing_history: List[BaseMessage],
        config: Dict[str, Any]
    ):
        """Update memory with new messages.

        Args:
            session_id: Optional session identifier
            user_message: User's message
            ai_message: AI's response
            existing_history: Existing conversation history
            config: Memory configuration
        """
        # Add new messages to history
        updated_history = existing_history + [user_message, ai_message]

        # Apply window if configured
        memory_type = config.get("type", "buffer-window")
        if memory_type == "buffer-window":
            window_size = config.get("windowSize", 10)
            updated_history = await self.apply_window(updated_history, window_size)

        # Save to persistent storage if configured
        if session_id and config.get("persistence", {}).get("enabled"):
            await self.save_session_memory(session_id, updated_history, config)

    def _serialize_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Serialize messages to JSON-compatible format.

        Args:
            messages: List of messages

        Returns:
            List of serialized message dicts
        """
        serialized = []
        for msg in messages:
            msg_dict = {
                "content": msg.content,
                "type": msg.__class__.__name__,
            }

            # Include additional fields if present
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                msg_dict["additional_kwargs"] = msg.additional_kwargs

            serialized.append(msg_dict)

        return serialized

    def _deserialize_messages(self, messages_data: List[Dict[str, Any]]) -> List[BaseMessage]:
        """Deserialize messages from JSON format.

        Args:
            messages_data: List of serialized message dicts

        Returns:
            List[BaseMessage]: Deserialized messages
        """
        messages = []
        for msg_data in messages_data:
            msg_type = msg_data.get("type", "HumanMessage")
            content = msg_data.get("content", "")
            additional_kwargs = msg_data.get("additional_kwargs", {})

            if msg_type == "HumanMessage":
                msg = HumanMessage(content=content, additional_kwargs=additional_kwargs)
            elif msg_type == "AIMessage":
                msg = AIMessage(content=content, additional_kwargs=additional_kwargs)
            elif msg_type == "SystemMessage":
                msg = SystemMessage(content=content, additional_kwargs=additional_kwargs)
            else:
                # Default to HumanMessage
                msg = HumanMessage(content=content, additional_kwargs=additional_kwargs)

            messages.append(msg)

        return messages

    async def clear_session(self, session_id: str):
        """Clear session memory.

        Args:
            session_id: Session identifier to clear
        """
        key = f"memory:session:{session_id}"
        await self.redis.delete(key)

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with session info or None if not found
        """
        key = f"memory:session:{session_id}"
        data = await self.redis.get(key)

        if not data:
            return None

        messages_data = json.loads(data)
        ttl = await self.redis.ttl(key)

        return {
            "session_id": session_id,
            "message_count": len(messages_data),
            "ttl_seconds": ttl,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
        }
