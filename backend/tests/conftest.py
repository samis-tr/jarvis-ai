import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def services(tmp_path, monkeypatch):
    from jarvis.services import Services
    ws = tmp_path / "workspace"
    ws.mkdir()
    s = Services(data_dir=tmp_path / "data", headless_browser=True)
    s.store.update({"provider": {"active": "mock"},
                    "security": {"approved_dirs": [str(ws)], "approval_timeout_s": 5},
                    "voice": {"tts_enabled": False}})
    yield s
    s.memory.close()


def pytest_collection_modifyitems(config, items):
    if os.environ.get("JARVIS_INTEGRATION") != "1":
        skip = pytest.mark.skip(reason="set JARVIS_INTEGRATION=1 to run integration tests")
        for it in items:
            if "integration" in it.keywords:
                it.add_marker(skip)


@pytest.fixture
def outside_dir():
    """A writable folder outside the approved dirs and outside protected roots (temp lives in AppData = protected)."""
    import shutil
    import uuid
    d = Path.home() / f".jarvis_pytest_{uuid.uuid4().hex[:6]}"
    d.mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)
