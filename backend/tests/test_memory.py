import pytest

from jarvis.memory import MemoryStore, SensitiveContentError


def test_memory_crud_and_search(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    a = m.add_memory("preference", "User prefers answers in Arabic")
    m.add_memory("project", "YouTube channel about AI tools")
    assert [r["id"] for r in m.search_memories("Arabic answers")] == [a]
    m.update_memory(a, "User prefers answers in German")
    assert m.search_memories("German")[0]["id"] == a
    assert not m.search_memories("Arabic")
    m.delete_memory(a)
    assert len(m.list_memories()) == 1
    # Arabic full-text search
    m.add_memory("fact", "اسم القناة جارفيس للتقنية")
    assert m.search_memories("القناة")
    with pytest.raises(SensitiveContentError):
        m.add_memory("fact", "my password: hunter2")
    with pytest.raises(ValueError):
        m.add_memory("bogus", "x")


def test_conversation_and_action_log_redacted(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    cid = m.new_conversation("t")
    m.add_message(cid, "user", "my key is sk-ant-api03-SECRETSECRETSECRET")
    assert "SECRET" not in m.messages(cid)[0]["content"]
    m.log_action("t1", "create_file", {"path": "a", "token": "abc"}, "medium", "allow", "done", "ok")
    assert m.actions("t1")[0]["args"]["token"] == "[REDACTED]"
