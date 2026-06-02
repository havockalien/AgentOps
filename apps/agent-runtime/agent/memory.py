"""
AgentOps — Memory Layer
========================
Two-tier memory system:
  Episodic (short-term)  : Redis — fast, TTL-bound, keyed by namespace
  Semantic  (long-term)  : Pinecone — vector similarity search

In dev/test environments the Pinecone client is replaced by an in-memory stub.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional, Protocol

log = logging.getLogger("agentops.memory")

# ── Pinecone Protocol (allows stubbing in tests) ───────────────────────────────


class VectorStoreProtocol(Protocol):
    """Minimal interface required from any vector store."""

    async def upsert(
        self,
        namespace: str,
        vector_id: str,
        values: list[float],
        metadata: dict[str, Any],
    ) -> None: ...

    async def query(
        self,
        namespace: str,
        query_vector: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]: ...


class InMemoryVectorStore:
    """In-process stub — used when PINECONE_API_KEY is absent."""

    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}

    async def upsert(
        self,
        namespace: str,
        vector_id: str,
        values: list[float],
        metadata: dict[str, Any],
    ) -> None:
        self._store.setdefault(namespace, []).append(
            {"id": vector_id, "values": values, "metadata": metadata}
        )

    async def query(
        self,
        namespace: str,
        query_vector: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        # No real similarity — just return latest entries for stub behaviour
        entries = self._store.get(namespace, [])
        return entries[-top_k:]


class MemoryClient:
    """
    Unified memory interface for AgentOps agents.

    Usage::

        client = MemoryClient(redis=redis_conn)
        await client.store("Search results for Q1", namespace="research-agent", metadata={...})
        context = await client.retrieve("Q1 revenue", namespace="research-agent", top_k=5)
    """

    EPISODIC_TTL = 3600 * 24  # 24 hours

    def __init__(
        self,
        redis: Any,  # redis.asyncio.Redis instance
        vector_store: Optional[VectorStoreProtocol] = None,
    ) -> None:
        self._redis = redis
        self._vector_store: VectorStoreProtocol = vector_store or InMemoryVectorStore()

    # ── Episodic (Redis) ──────────────────────────────────────────────────────

    async def store_episodic(
        self,
        key: str,
        content: str,
        namespace: str,
        ttl: int = EPISODIC_TTL,
    ) -> None:
        """Store a string value in Redis under `namespace:key`."""
        full_key = f"memory:{namespace}:{key}"
        await self._redis.setex(full_key, ttl, content)
        log.debug("Stored episodic memory: %s", full_key)

    async def get_episodic(self, key: str, namespace: str) -> Optional[str]:
        """Retrieve a single episodic memory by key."""
        full_key = f"memory:{namespace}:{key}"
        value = await self._redis.get(full_key)
        return value if isinstance(value, str) else (value.decode() if value else None)

    async def list_episodic(self, namespace: str, limit: int = 20) -> list[str]:
        """Return the most recent `limit` entries in the namespace."""
        pattern = f"memory:{namespace}:*"
        keys = await self._redis.keys(pattern)
        results: list[str] = []
        for key in keys[-limit:]:
            val = await self._redis.get(key)
            if val:
                results.append(val if isinstance(val, str) else val.decode())
        return results

    # ── Semantic (Vector Store) ───────────────────────────────────────────────

    async def store(
        self,
        content: str,
        namespace: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Store content in both Redis (episodic) and the vector store (semantic).
        Returns the vector ID.
        """
        vector_id = str(uuid.uuid4())
        meta = metadata or {}
        meta["content"] = content
        meta["namespace"] = namespace
        meta["timestamp"] = str(time.time())

        # Episodic store — keyed by vector_id
        await self.store_episodic(vector_id, content, namespace)

        # Semantic store — use a zero vector as placeholder (real embeddings added in Phase 3)
        placeholder_vector = [0.0] * 1536  # OpenAI embedding dimension
        await self._vector_store.upsert(namespace, vector_id, placeholder_vector, meta)

        log.debug("Stored semantic memory id=%s ns=%s", vector_id, namespace)
        return vector_id

    async def retrieve(
        self,
        query: str,
        namespace: str,
        top_k: int = 5,
    ) -> list[str]:
        """
        Retrieve semantically relevant memories.
        Falls back to recent episodic entries when vector store returns nothing.
        """
        query_vector = [0.0] * 1536  # Placeholder — real embeddings in Phase 3
        matches = await self._vector_store.query(namespace, query_vector, top_k)

        if matches:
            return [m.get("metadata", {}).get("content", json.dumps(m)) for m in matches]

        # Fallback to episodic
        return await self.list_episodic(namespace, limit=top_k)
