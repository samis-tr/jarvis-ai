"""API keys stored in Windows Credential Manager (via `keyring`). Never in files or logs."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)
SERVICE = "JARVIS-AI"

try:
    import keyring  # type: ignore
except Exception:  # pragma: no cover
    keyring = None


def set_secret(name: str, value: str) -> None:
    if keyring is None:
        raise RuntimeError("keyring not available")
    keyring.set_password(SERVICE, name, value)
    log.info("Stored secret %s in Windows Credential Manager", name)


def get_secret(name: str) -> str | None:
    if keyring is None:
        return None
    try:
        return keyring.get_password(SERVICE, name)
    except Exception as e:  # pragma: no cover
        log.warning("Could not read secret %s: %s", name, e)
        return None


def delete_secret(name: str) -> None:
    if keyring is None:
        return
    try:
        keyring.delete_password(SERVICE, name)
    except Exception:
        pass


def has_secret(name: str) -> bool:
    return bool(get_secret(name))
