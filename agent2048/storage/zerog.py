"""0G Storage backend for Agent2048 memory.

This module provides integration with 0G Storage's KV Layer for storing
hierarchical memory onchain. It falls back to local SQLite when 0G SDK
is not installed or configured.

0G Storage KV Layer is designed for:
- Mutable, database-like Key-Value access
- Sub-second latency for vector embeddings
- Dynamic state updates without rewriting entire files
- Active memory layer for autonomous AI agents

Setup:
  1. Get testnet tokens from https://faucet.0g.ai
  2. Install SDK: pip install zerog-sdk (when available)
  3. Set in .env:
     ZEROG_RPC=https://evmrpc-testnet.0g.ai
     ZEROG_PRIVATE_KEY=your-testnet-key
     ZEROG_KV_CONTRACT=0x22E03a6A89B950F1c82ec5e74F8eCa321a105296
"""

import json
from typing import Any

from agent2048.logging_config import logger


_ZEROG_AVAILABLE = False

try:
    from zerog_sdk import ZeroGStorage
    _ZEROG_AVAILABLE = True
except ImportError:
    pass


class ZeroGMemoryBackend:
    """0G Storage KV Layer backend for memory items.

    Stores memory items as key-value pairs in 0G Storage.
    Falls back to local SQLite if SDK not available.
    """

    def __init__(
        self,
        rpc_url: str = "",
        private_key: str = "",
        kv_contract: str = "0x22E03a6A89B950F1c82ec5e74F8eCa321a105296",
    ):
        self.rpc_url = rpc_url
        self.private_key = private_key
        self.kv_contract = kv_contract
        self._client = None

        if _ZEROG_AVAILABLE and rpc_url and private_key:
            try:
                self._client = ZeroGStorage(
                    rpc_url=rpc_url,
                    private_key=private_key,
                    contract_address=kv_contract,
                )
                logger.info("0G Storage backend initialized")
            except Exception as e:
                logger.warning("Failed to init 0G Storage: %s", e)
        else:
            logger.info("0G SDK not available, using local SQLite fallback")

    @property
    def is_available(self) -> bool:
        """Check if 0G Storage backend is active."""
        return self._client is not None

    def store(self, key: str, value: dict[str, Any]) -> bool:
        """Store a memory item in 0G Storage KV Layer.

        Args:
            key: Memory item ID (UUID)
            value: Dict with content, level, embedding, tag, etc.

        Returns:
            True if stored successfully, False on failure or fallback.
        """
        if not self.is_available:
            return False

        try:
            serialized = json.dumps(value, default=str)
            self._client.kv_set(key, serialized)
            return True
        except Exception as e:
            logger.warning("0G Storage write failed: %s", e)
            return False

    def retrieve(self, key: str) -> dict[str, Any] | None:
        """Retrieve a memory item from 0G Storage.

        Args:
            key: Memory item ID

        Returns:
            Dict with memory data, or None if not found.
        """
        if not self.is_available:
            return None

        try:
            data = self._client.kv_get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("0G Storage read failed: %s", e)
            return None

    def delete(self, key: str) -> bool:
        """Delete a memory item from 0G Storage.

        Args:
            key: Memory item ID

        Returns:
            True if deleted, False on failure.
        """
        if not self.is_available:
            return False

        try:
            self._client.kv_delete(key)
            return True
        except Exception as e:
            logger.warning("0G Storage delete failed: %s", e)
            return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with a given prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of keys.
        """
        if not self.is_available:
            return []

        try:
            return self._client.kv_list(prefix)
        except Exception as e:
            logger.warning("0G Storage list failed: %s", e)
            return []
