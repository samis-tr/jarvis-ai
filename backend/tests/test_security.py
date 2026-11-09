import os
from pathlib import Path

import pytest

from jarvis.config import Settings
from jarvis.security import paths as P
from jarvis.security.permissions import Decision, TaskGrants, decide
from jarvis.security.redact import looks_sensitive, redact, redact_obj
from jarvis.tools.base import Assessment, Risk
from jarvis.tools.filesystem import CreateFile, DeletePath, ReadFile


def test_redaction_of_keys_and_passwords():
    s = "key sk-ant-api03-abcdefghijklmnop1234 and password: hunter2 and كلمة السر: سر123"
    out = redact(s)
    assert "abcdefghijklmnop" not in out and "hunter2" not in out and "سر123" not in out
    assert redact_obj({"api_key": "x", "nested": ["Bearer abcdefghijklmnopqrstuvwxyz"]}) == \
        {"api_key": "[REDACTED]", "nested": ["Bearer [REDACTED]"]}
    assert looks_sensitive("my passwort ist geheim")
    assert not looks_sensitive("I prefer short answers in Arabic")


def test_path_scope(tmp_path, outside_dir):
    ws = tmp_path / "ws"
    ws.mkdir()
    ok = P.check_path(str(ws / "a.txt"), [str(ws)])
    assert ok == (ws / "a.txt").resolve()
    with pytest.raises(P.ScopeError):
        P.check_path(str(tmp_path / "outside.txt"), [str(ws)])
    with pytest.raises(P.ScopeError):  # traversal
        P.check_path(str(ws / ".." / "outside.txt"), [str(ws)])
    with pytest.raises(P.ScopeError):  # sensitive file even inside scope
        P.check_path(str(ws / ".env"), [str(ws)])
    with pytest.raises(P.ScopeError):  # protected system dir, even if user approved
        P.check_path(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "x.txt"), [str(ws)], user_approved=True)
    # outside approved but explicitly approved by the user -> allowed
    assert P.check_path(str(outside_dir / "outside.txt"), [str(ws)], user_approved=True)
    # temp folders live in AppData, which is protected
    with pytest.raises(P.ScopeError):
        P.check_path(str(tmp_path / "outside.txt"), [str(ws)], user_approved=True)


def _settings(**sec):
    s = Settings()
    for k, v in sec.items():
        setattr(s.security, k, v)
    return s


def test_permission_matrix():
    g = TaskGrants(tools=set())
    st = _settings()
    assert decide(ReadFile(), Assessment(Risk.LOW), st, g).decision is Decision.ALLOW
    assert decide(CreateFile(), Assessment(Risk.MEDIUM, True), st, g).decision is Decision.ALLOW  # pre-authorized
    assert decide(CreateFile(), Assessment(Risk.MEDIUM, False), st, g).decision is Decision.ASK   # out of scope
    assert decide(DeletePath(), Assessment(Risk.HIGH), st, g).decision is Decision.ASK
    # tainted by web content -> medium needs approval again
    assert decide(CreateFile(), Assessment(Risk.MEDIUM, True), st, TaskGrants(set(), tainted=True)).decision is Decision.ASK
    # safe mode
    safe = _settings(safe_mode=True)
    assert decide(CreateFile(), Assessment(Risk.MEDIUM, True), safe, g).decision is Decision.ASK
    assert decide(DeletePath(), Assessment(Risk.HIGH), safe, g).decision is Decision.DENY
    # disabled tool
    assert decide(ReadFile(), Assessment(Risk.LOW), _settings(disabled_tools=["read_file"]), g).decision is Decision.DENY
    # high risk is never covered by a task grant
    assert decide(DeletePath(), Assessment(Risk.HIGH), st, TaskGrants({"delete_to_recycle_bin"})).decision is Decision.ASK
