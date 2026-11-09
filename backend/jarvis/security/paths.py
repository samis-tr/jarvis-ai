"""Filesystem scope enforcement: approved directories and protected locations."""
from __future__ import annotations

import os
from pathlib import Path

SENSITIVE_NAMES = {
    ".env", ".npmrc", ".pypirc", ".netrc", "id_rsa", "id_ed25519", "credentials", "credentials.json",
    "known_hosts", "login data", "cookies", "web data", "key4.db", "logins.json", "wallet.dat",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".pfx", ".p12", ".kdbx", ".ppk", ".gpg", ".asc", ".ovpn", ".rdp"}
SENSITIVE_DIR_PARTS = {".ssh", ".gnupg", ".aws", ".azure", ".kube", ".docker", "microsoft\\credentials",
                       "microsoft\\protect"}


def protected_roots() -> list[Path]:
    env = os.environ
    roots = [
        env.get("SystemRoot", r"C:\Windows"),
        env.get("ProgramFiles", r"C:\Program Files"),
        env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        env.get("ProgramData", r"C:\ProgramData"),
        env.get("APPDATA", ""),
        env.get("LOCALAPPDATA", ""),
        str(Path.home() / ".ssh"),
    ]
    return [Path(r).resolve() for r in roots if r]


class ScopeError(PermissionError):
    pass


def resolve(path: str | os.PathLike) -> Path:
    p = Path(os.path.expandvars(os.path.expanduser(str(path))))
    return p.resolve(strict=False)


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def is_protected(path: Path) -> bool:
    return any(is_within(path, root) for root in protected_roots())


def is_sensitive_file(path: Path) -> bool:
    name = path.name.lower()
    if name in SENSITIVE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    low = str(path).lower()
    return any(part in low for part in SENSITIVE_DIR_PARTS)


def in_approved(path: Path, approved_dirs: list[str]) -> bool:
    return any(is_within(path, resolve(d)) for d in approved_dirs)


def check_path(path: str, approved_dirs: list[str], *, allow_sensitive: bool = False,
               user_approved: bool = False) -> Path:
    """Resolve a user/AI-supplied path and enforce scope. Raises ScopeError.

    Outside the approved directories a path is only usable when the user explicitly
    approved this specific call; protected system locations are never usable.
    """
    p = resolve(path)
    inside = in_approved(p, approved_dirs)
    if is_protected(p) and not inside:
        raise ScopeError(f"Path is in a protected system location: {p}")
    if not inside and not user_approved:
        raise ScopeError(f"Path is outside the approved directories: {p}")
    if not allow_sensitive and is_sensitive_file(p):
        raise ScopeError(f"Access to sensitive file is blocked: {p.name}")
    return p
