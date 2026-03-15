"""
Retrieval Guardrails

Context quality guardrails that run after RAG retrieval:
- ScoreThresholdGuardrail: Filter low-relevance chunks
- TokenLimitGuardrail: Truncate context to fit token limits
- ChunkDeduplicationGuardrail: Remove duplicate/similar chunks
- SourceDiversityGuardrail: Ensure diverse sources
"""

from typing import Any, Dict, List, Optional, Set
from difflib import SequenceMatcher
from .base import (
    RuleBasedGuardrail,
    HybridGuardrail,
    GuardrailCheckResult,
    ViolationSeverity,
    ViolationType,
)


class ScoreThresholdGuardrail(RuleBasedGuardrail):
    """Filters chunks below a minimum relevance score."""

    def __init__(
        self,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        min_score: float = 0.5,
        score_field: str = "score",
    ):
        super().__init__(
            name="scoreThreshold",
            enabled=enabled,
            source=source,
            config=config,
        )
        self.min_score = config.get("minScore", min_score) if config else min_score
        self.score_field = score_field

    async def check(self, data: List[Dict[str, Any]]) -> GuardrailCheckResult:
        """Filter chunks below the score threshold."""
        if not data:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={"original_count": 0, "filtered_count": 0},
            )

        original_count = len(data)
        filtered_chunks = []
        removed_chunks = []

        for chunk in data:
            score = chunk.get(self.score_field, chunk.get("similarity", 0))
            if score >= self.min_score:
                filtered_chunks.append(chunk)
            else:
                removed_chunks.append({
                    "id": chunk.get("id", "unknown"),
                    "score": score,
                })

        filtered_count = len(filtered_chunks)
        removed_count = len(removed_chunks)

        # Determine if this is a problem
        passed = filtered_count > 0 or original_count == 0

        return GuardrailCheckResult(
            name=self.name,
            passed=passed,
            confidence=1.0,
            details={
                "original_count": original_count,
                "filtered_count": filtered_count,
                "removed_count": removed_count,
                "min_score": self.min_score,
                "filtered_chunks": filtered_chunks,  # Include for downstream use
                "removed_chunks": removed_chunks[:5],  # Sample of removed
                "violation": ViolationType.LOW_RELEVANCE_SCORE if not passed else None,
                "message": f"All chunks below threshold ({self.min_score})" if not passed else None,
            },
        )


class TokenLimitGuardrail(RuleBasedGuardrail):
    """Truncates context to fit within token limits."""

    def __init__(
        self,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        max_tokens: int = 4000,
        chars_per_token: float = 4.0,  # Approximate
        content_field: str = "content",
    ):
        super().__init__(
            name="tokenLimit",
            enabled=enabled,
            source=source,
            config=config,
        )
        self.max_tokens = config.get("maxTokens", max_tokens) if config else max_tokens
        self.chars_per_token = chars_per_token
        self.content_field = content_field

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length."""
        return int(len(text) / self.chars_per_token)

    async def check(self, data: List[Dict[str, Any]]) -> GuardrailCheckResult:
        """Truncate chunks to fit token limit."""
        if not data:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={"original_tokens": 0, "truncated": False},
            )

        # Calculate total tokens
        total_chars = sum(
            len(chunk.get(self.content_field, ""))
            for chunk in data
        )
        total_tokens = self._estimate_tokens(total_chars)

        if total_tokens <= self.max_tokens:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={
                    "original_tokens": total_tokens,
                    "max_tokens": self.max_tokens,
                    "truncated": False,
                    "filtered_chunks": data,
                },
            )

        # Need to truncate - keep chunks in order until we hit limit
        filtered_chunks = []
        current_tokens = 0

        for chunk in data:
            chunk_content = chunk.get(self.content_field, "")
            chunk_tokens = self._estimate_tokens(len(chunk_content))

            if current_tokens + chunk_tokens <= self.max_tokens:
                filtered_chunks.append(chunk)
                current_tokens += chunk_tokens
            else:
                # Try to include partial chunk
                remaining_tokens = self.max_tokens - current_tokens
                if remaining_tokens > 100:  # Only include if meaningful
                    remaining_chars = int(remaining_tokens * self.chars_per_token)
                    truncated_chunk = chunk.copy()
                    truncated_chunk[self.content_field] = chunk_content[:remaining_chars] + "..."
                    filtered_chunks.append(truncated_chunk)
                break

        return GuardrailCheckResult(
            name=self.name,
            passed=True,  # Truncation is a fix, not a failure
            confidence=1.0,
            details={
                "original_tokens": total_tokens,
                "final_tokens": current_tokens,
                "max_tokens": self.max_tokens,
                "truncated": True,
                "original_chunks": len(data),
                "final_chunks": len(filtered_chunks),
                "filtered_chunks": filtered_chunks,
                "violation": ViolationType.TOKEN_LIMIT_EXCEEDED,
                "message": f"Truncated from {total_tokens} to {current_tokens} tokens",
            },
        )


class ChunkDeduplicationGuardrail(RuleBasedGuardrail):
    """Removes duplicate or highly similar chunks."""

    def __init__(
        self,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.9,
        content_field: str = "content",
    ):
        super().__init__(
            name="deduplication",
            enabled=enabled,
            source=source,
            config=config,
        )
        self.similarity_threshold = (
            config.get("threshold", similarity_threshold) if config else similarity_threshold
        )
        self.content_field = content_field

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    async def check(self, data: List[Dict[str, Any]]) -> GuardrailCheckResult:
        """Remove duplicate chunks based on content similarity."""
        if not data or len(data) <= 1:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={
                    "original_count": len(data) if data else 0,
                    "deduplicated": False,
                    "filtered_chunks": data or [],
                },
            )

        unique_chunks: List[Dict[str, Any]] = []
        duplicate_pairs: List[Dict[str, Any]] = []

        for chunk in data:
            chunk_content = chunk.get(self.content_field, "")
            is_duplicate = False

            for existing in unique_chunks:
                existing_content = existing.get(self.content_field, "")
                similarity = self._similarity(chunk_content, existing_content)

                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    duplicate_pairs.append({
                        "removed": chunk.get("id", "unknown"),
                        "similar_to": existing.get("id", "unknown"),
                        "similarity": round(similarity, 3),
                    })
                    break

            if not is_duplicate:
                unique_chunks.append(chunk)

        removed_count = len(data) - len(unique_chunks)

        return GuardrailCheckResult(
            name=self.name,
            passed=True,
            confidence=1.0,
            details={
                "original_count": len(data),
                "unique_count": len(unique_chunks),
                "removed_count": removed_count,
                "similarity_threshold": self.similarity_threshold,
                "duplicate_pairs": duplicate_pairs[:5],  # Sample
                "filtered_chunks": unique_chunks,
                "violation": ViolationType.DUPLICATE_CONTENT if removed_count > 0 else None,
                "message": f"Removed {removed_count} duplicate chunks" if removed_count > 0 else None,
            },
        )


class SourceDiversityGuardrail(RuleBasedGuardrail):
    """Ensures chunks come from diverse sources."""

    def __init__(
        self,
        enabled: bool = True,
        source: str = "workflow",
        config: Optional[Dict[str, Any]] = None,
        min_sources: int = 2,
        source_field: str = "source",
        max_per_source: Optional[int] = None,
    ):
        super().__init__(
            name="sourceDiversity",
            enabled=enabled,
            source=source,
            config=config,
        )
        self.min_sources = config.get("minSources", min_sources) if config else min_sources
        self.source_field = source_field
        self.max_per_source = max_per_source

    async def check(self, data: List[Dict[str, Any]]) -> GuardrailCheckResult:
        """Check source diversity and optionally balance sources."""
        if not data:
            return GuardrailCheckResult(
                name=self.name,
                passed=True,
                confidence=1.0,
                details={"source_count": 0, "diverse": True},
            )

        # Count chunks per source
        source_counts: Dict[str, int] = {}
        for chunk in data:
            src = chunk.get(self.source_field, chunk.get("metadata", {}).get("source", "unknown"))
            source_counts[src] = source_counts.get(src, 0) + 1

        unique_sources = len(source_counts)
        diverse_enough = unique_sources >= self.min_sources or len(data) < self.min_sources

        # Optionally balance sources
        filtered_chunks = data
        if self.max_per_source and unique_sources > 1:
            source_counts_remaining = {src: 0 for src in source_counts}
            filtered_chunks = []

            for chunk in data:
                src = chunk.get(self.source_field, chunk.get("metadata", {}).get("source", "unknown"))
                if source_counts_remaining[src] < self.max_per_source:
                    filtered_chunks.append(chunk)
                    source_counts_remaining[src] += 1

        return GuardrailCheckResult(
            name=self.name,
            passed=diverse_enough,
            confidence=1.0 if diverse_enough else 0.5,
            details={
                "source_count": unique_sources,
                "min_sources": self.min_sources,
                "source_distribution": source_counts,
                "diverse": diverse_enough,
                "filtered_chunks": filtered_chunks,
                "violation": ViolationType.INSUFFICIENT_SOURCES if not diverse_enough else None,
                "message": f"Only {unique_sources} source(s) (min: {self.min_sources})" if not diverse_enough else None,
            },
        )
