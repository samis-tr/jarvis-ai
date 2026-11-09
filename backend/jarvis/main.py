"""Entry point: starts the local API server and opens the desktop window.

    python -m jarvis.main            # desktop window (pywebview / WebView2)
    python -m jarvis.main --server   # API + UI only, open the printed URL in a browser
"""
from __future__ import annotations

import argparse
import os
import logging
import logging.handlers
import secrets
import socket
import sys
import threading
import time

import uvicorn

from jarvis.config import DATA_DIR
from jarvis.security.redact import RedactingFilter


def setup_logging() -> None:
    (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.handlers.RotatingFileHandler(DATA_DIR / "logs" / "jarvis.log", maxBytes=2_000_000, backupCount=3,
                                              encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in (fh, sh):
        h.setFormatter(fmt)
        h.addFilter(RedactingFilter())
        root.addHandler(h)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def free_port(preferred: int = 8765) -> int:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", action="store_true", help="run without desktop window")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    setup_logging()
    log = logging.getLogger("jarvis")

    from jarvis.server import create_app
    token = os.environ.get("JARVIS_DEV_TOKEN") or secrets.token_urlsafe(24)
    port = free_port(args.port)
    app = create_app(token=token)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    url = f"http://127.0.0.1:{port}/?token={token}"

    if args.server:
        print(f"\nJARVIS running: {url}\n", flush=True)
        server.run()
        return

    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    log.info("API ready on port %s", port)

    import webview
    window = webview.create_window("JARVIS AI", url, width=1440, height=900, min_size=(1000, 680),
                                   background_color="#05070d")
    opened = time.time()
    try:
        webview.start(private_mode=False, storage_path=str(DATA_DIR / "webview"))
    except Exception:
        log.exception("desktop window failed")
    alive = time.time() - opened
    if alive < 5:
        log.warning("desktop window closed after %.1f s - WebView2 may have failed to start "
                    "(another JARVIS window still closing?). Try again, or use start-jarvis.ps1 -Server.", alive)
    else:
        log.info("desktop window closed after %.0f s", alive)
    server.should_exit = True
    th.join(timeout=8)


if __name__ == "__main__":
    main()
