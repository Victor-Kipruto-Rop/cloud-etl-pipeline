"""Utilities to expose deployment metadata for the service.

This module reads a `deploy_info.json` file if present (written by CI/CD during
deploys) and provides helpers to surface the data in endpoints and logs.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEPLOY_INFO_PATH_ENV = "DEPLOY_INFO_PATH"
DEFAULT_DEPLOY_INFO = Path("deploy_info.json")


def _load_from_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            with path.open() as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to load deploy info from {path}: {e}")
    return None


def get_deploy_info() -> Dict[str, Any]:
    """Return deploy metadata.

    Expected keys produced by CI/CD:
      - version
      - commit
      - deployed_by
      - timestamp
      - status: success|failed
      - notes
      - last_successful_deploy
      - last_failed_deploy
    Falls back to environment variables: `RELEASE_VERSION`, `GIT_COMMIT`.
    """
    path = Path(os.getenv(DEPLOY_INFO_PATH_ENV, DEFAULT_DEPLOY_INFO))

    info = _load_from_file(path) or {}

    # Env fallbacks
    if not info.get("version"):
        info["version"] = os.getenv("RELEASE_VERSION")
    if not info.get("commit"):
        info["commit"] = os.getenv("GIT_COMMIT")

    # Ensure minimal keys
    info.setdefault("version", "unknown")
    info.setdefault("commit", "unknown")
    info.setdefault("deployed_by", "ci")
    info.setdefault("timestamp", None)
    info.setdefault("status", None)

    # Last deploys
    info.setdefault("last_successful_deploy", None)
    info.setdefault("last_failed_deploy", None)

    return info


def write_deploy_info(data: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Write deploy metadata to the configured path (used by CI/CD)."""
    path = path or Path(os.getenv(DEPLOY_INFO_PATH_ENV, DEFAULT_DEPLOY_INFO))
    try:
        with path.open("w") as f:
            json.dump(data, f)
    except Exception:
        logger.exception("Failed to write deploy info file")
