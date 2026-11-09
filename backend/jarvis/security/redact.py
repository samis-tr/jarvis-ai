"""Secret redaction for logs, action history and memory."""
from __future__ import annotations

import logging
import re

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"), "Bearer [REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)((?:password|passwort|kennwort|passwd|pwd|secret|token|api[_-]?key|كلمة\s*(?:ال)?سر|كلمة\s*المرور)\s*[:=]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[REDACTED_NUMBER]"),  # card-like numbers
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}\b"), "[REDACTED_IBAN]"),
]

_SENSITIVE_HINTS = re.compile(
    r"(?i)(password|passwort|kennwort|passwd|secret|api[_-]?key|private key|iban|credit card|kreditkarte|"
    r"كلمة\s*(?:ال)?سر|كلمة\s*المرور|رقم\s*البطاقة|-----BEGIN)"
)


def redact(text: str) -> str:
    if not text:
        return text
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


def redact_obj(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if _is_secret_key(k) else redact_obj(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_obj(v) for v in obj]
    return obj


def _is_secret_key(key: str) -> bool:
    return bool(re.search(r"(?i)(password|secret|api_?key|token)", str(key)))


def looks_sensitive(text: str) -> bool:
    """True if text appears to contain credentials or financial identifiers."""
    return bool(_SENSITIVE_HINTS.search(text)) or redact(text) != text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        record.msg = redact(msg)
        record.args = ()
        return True
