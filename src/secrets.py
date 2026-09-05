"""Production-grade secret resolution helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class SecretManager:
    """Resolve secrets from environment variables and AWS Secrets Manager."""

    def __init__(self, region_name: Optional[str] = None):
        self.region_name = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

    def get_secret(self, name: str, default: Any = None, *, secret_id: Optional[str] = None) -> Any:
        """Get a secret by name, preferring environment variables and then AWS Secrets Manager."""
        env_value = os.getenv(name)
        if env_value is not None and env_value.strip():
            return env_value

        if secret_id is not None:
            secret_value = self._load_from_secrets_manager(secret_id)
            if secret_value is not None:
                return secret_value

        secret_name = secret_id or self._resolve_secret_name(name)
        secret_value = self._load_from_secrets_manager(secret_name)
        if secret_value is not None:
            return secret_value

        return default

    def get_required_secret(self, name: str, *, secret_id: Optional[str] = None) -> str:
        """Return a required secret or raise a clear ValueError."""
        value = self.get_secret(name, secret_id=secret_id)
        if value is None:
            raise ValueError(f"Secret '{name}' is not configured")
        return str(value)

    def _resolve_secret_name(self, name: str) -> Optional[str]:
        """Infer secret names from commonly used naming conventions."""
        candidates = []
        normalized = name.strip()
        candidates.append(normalized)
        candidates.append(f"{normalized}_SECRET")
        candidates.append(f"{normalized.lower()}_secret")
        candidates.append(f"etl/{normalized.lower()}")
        candidates.append(f"/prod/{normalized.lower()}")

        for candidate in candidates:
            env_candidate = os.getenv(candidate)
            if env_candidate:
                return env_candidate
        return name

    def _load_from_secrets_manager(self, secret_name: str) -> Any:
        """Resolve a secret via AWS Secrets Manager when available."""
        if not secret_name:
            return None
        try:
            client = boto3.client("secretsmanager", region_name=self.region_name)
            response = client.get_secret_value(SecretId=secret_name)
        except (BotoCoreError, ClientError, Exception):
            return None

        if "SecretString" in response:
            value = response["SecretString"]
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        if "SecretBinary" in response:
            return response["SecretBinary"]

        return None


def get_secret_manager() -> SecretManager:
    """Convenience accessor for the shared secret manager."""
    return SecretManager()
