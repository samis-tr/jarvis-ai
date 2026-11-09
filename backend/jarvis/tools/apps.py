"""Open / close applications via an allowlist and Start-Menu shortcuts. No shell strings are executed."""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import webbrowser
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import psutil
from pydantic import BaseModel, Field

from jarvis.tools.base import Assessment, Risk, Tool, ToolResult

# alias -> (argv for launching, process names for closing)
KNOWN_APPS: dict[str, tuple[list[str], list[str]]] = {
    "notepad": (["notepad.exe"], ["notepad.exe"]),
    "calculator": (["calc.exe"], ["calculatorapp.exe", "calculator.exe"]),
    "paint": (["mspaint.exe"], ["mspaint.exe"]),
    "explorer": (["explorer.exe"], []),  # never close the shell
    "edge": (["cmd:msedge"], ["msedge.exe"]),
    "chrome": (["cmd:chrome"], ["chrome.exe"]),
    "firefox": (["cmd:firefox"], ["firefox.exe"]),
    "vscode": (["cmd:code"], ["code.exe"]),
    "word": (["cmd:winword"], ["winword.exe"]),
    "excel": (["cmd:excel"], ["excel.exe"]),
    "powerpoint": (["cmd:powerpnt"], ["powerpnt.exe"]),
    "task manager": (["taskmgr.exe"], []),
    "settings": (["uri:ms-settings:"], ["systemsettings.exe"]),
    "spotify": (["uri:spotify:"], ["spotify.exe"]),
    "snipping tool": (["uri:ms-screenclip:"], ["snippingtool.exe"]),
}

ALIASES = {
    "المفكرة": "notepad", "مفكرة": "notepad", "نوتباد": "notepad", "editor": "notepad", "texteditor": "notepad",
    "الحاسبة": "calculator", "حاسبة": "calculator", "الآلة الحاسبة": "calculator", "rechner": "calculator", "calc": "calculator",
    "الرسام": "paint", "رسام": "paint",
    "مستكشف الملفات": "explorer", "الملفات": "explorer", "file explorer": "explorer", "datei-explorer": "explorer",
    "ايدج": "edge", "إيدج": "edge", "microsoft edge": "edge", "المتصفح": "edge", "browser": "edge",
    "كروم": "chrome", "google chrome": "chrome", "فايرفوكس": "firefox",
    "visual studio code": "vscode", "vs code": "vscode", "code": "vscode", "في اس كود": "vscode",
    "وورد": "word", "microsoft word": "word", "اكسل": "excel", "إكسل": "excel", "باوربوينت": "powerpoint",
    "مدير المهام": "task manager", "taskmanager": "task manager", "task-manager": "task manager",
    "الإعدادات": "settings", "الاعدادات": "settings", "einstellungen": "settings", "سبوتيفاي": "spotify",
    "notizblock": "notepad", "notebook": "notepad", "notes": "notepad", "text editor": "notepad",
    "calculatrice": "calculator", "taschenrechner": "calculator",
}


def normalize_app(name: str) -> str:
    n = name.strip().lower().removesuffix(".exe")
    return ALIASES.get(n, n)


def _start_menu_dirs() -> list[Path]:
    dirs = [Path(os.environ.get("ProgramData", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs"]
    return [d for d in dirs if d.exists()]


def find_shortcut(name: str) -> Path | None:
    target = name.lower()
    best: tuple[float, Path | None] = (0.0, None)
    for d in _start_menu_dirs():
        for lnk in d.rglob("*.lnk"):
            stem = lnk.stem.lower()
            if "uninstall" in stem or "deinstall" in stem:
                continue
            score = 1.0 if stem == target else (0.9 if target in stem else SequenceMatcher(None, target, stem).ratio())
            if score > best[0]:
                best = (score, lnk)
    return best[1] if best[0] >= 0.75 else None


def _close_windows_gracefully(pids: set[int]) -> int:
    """Post WM_CLOSE to the visible top-level windows of the given processes (same as clicking the X).
    Apps may then show their own 'save changes?' dialog - nothing is force-killed."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    hits: list[int] = []
    proc_t = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            hits.append(hwnd)
        return True
    user32.EnumWindows(proc_t(cb), 0)
    for h in hits:
        user32.PostMessageW(h, WM_CLOSE, 0, 0)
    return len(hits)


def _launch(spec: str) -> None:
    if spec.startswith("uri:"):
        os.startfile(spec[4:])  # type: ignore[attr-defined]
    elif spec.startswith("cmd:"):
        # 'start' resolves App Paths registry entries (msedge, chrome, winword ...) - argv list, no shell injection
        exe = spec[4:]
        if not re.fullmatch(r"[a-z0-9_.\-]+", exe):
            raise ValueError("invalid executable name")
        subprocess.Popen(["cmd", "/c", "start", "", exe], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen([spec], creationflags=0)


class OpenAppArgs(BaseModel):
    name: str = Field(..., description="Application name, e.g. 'notepad', 'calculator', 'chrome', 'word', or a Start-menu app name")


class OpenApplication(Tool):
    name = "open_application"
    description = ("Open/start/launch a desktop application by name (Arabic: افتح، شغّل; German: öffnen, starten). "
                   "Allowlisted apps or Start-menu shortcuts. "
                   "Cannot run arbitrary commands.")
    Args = OpenAppArgs
    risk = Risk.LOW
    verifiable = True

    def _resolve(self, raw: str) -> tuple[str, str | None, Path | None]:
        key = normalize_app(raw)
        if key in KNOWN_APPS:
            return key, KNOWN_APPS[key][0][0], None
        return key, None, find_shortcut(key)

    def assess(self, args, ctx):
        key, spec, lnk = self._resolve(args.name)
        if spec:
            return Assessment(Risk.LOW, True, f"Open application '{key}'")
        if lnk:
            return Assessment(Risk.LOW, True, f"Open Start-menu app '{lnk.stem}'")
        return Assessment(Risk.LOW, True, f"Open application '{args.name}' (not found)")

    async def run(self, args, ctx):
        key, spec, lnk = self._resolve(args.name)
        before = {p.pid for p in psutil.process_iter()}
        if spec:
            _launch(spec)
            label = key
        elif lnk:
            os.startfile(str(lnk))  # type: ignore[attr-defined]
            label = lnk.stem
        else:
            return ToolResult(False, f"No application named '{args.name}' was found in the allowlist or Start menu.")
        return ToolResult(True, f"Launched {label}.", {"app": label, "key": key, "pids_before": len(before)})

    async def verify(self, args, result, ctx):
        key = result.data.get("key", "")
        procs = KNOWN_APPS.get(key, ([], []))[1]
        if not procs:
            return True, "launch command issued (no process signature to check)"
        for _ in range(16):
            names = {(p.info.get("name") or "").lower() for p in psutil.process_iter(["name"])}
            if any(n in names for n in procs):
                return True, f"process running: {procs}"
            await asyncio.sleep(0.5)
        return False, f"process {procs} not detected after launch"


class CloseAppArgs(BaseModel):
    name: str = Field(..., description="Application name to close, e.g. 'notepad'")


class CloseApplication(Tool):
    name = "close_application"
    description = ("Close/quit/exit a running application (Arabic: أغلق، سكّر، سكر، طفّي; German: schließen, beenden). "
                   "Allowlisted apps only. Unsaved work could be lost, so it needs approval.")
    Args = CloseAppArgs
    risk = Risk.MEDIUM
    verifiable = True

    def assess(self, args, ctx):
        return Assessment(Risk.MEDIUM, True, f"Close application '{normalize_app(args.name)}' (unsaved work may be lost)")

    async def run(self, args, ctx):
        key = normalize_app(args.name)
        procs = KNOWN_APPS.get(key, ([], []))[1]
        if not procs:
            closable = ", ".join(k for k, v in KNOWN_APPS.items() if v[1])
            return ToolResult(False, f"'{args.name}' is not in the list of apps JARVIS may close. Allowed names: {closable}.")
        targets = [p for p in psutil.process_iter(["name"]) if (p.info.get("name") or "").lower() in procs]
        if not targets:
            return ToolResult(False, f"{key} is not running.", {"key": key})
        windows = await asyncio.to_thread(_close_windows_gracefully, {p.pid for p in targets})
        gone, alive = await asyncio.to_thread(psutil.wait_procs, targets, 5)
        if alive:
            return ToolResult(False, f"Asked {windows} {key} window(s) to close; {len(alive)} process(es) still running "
                                     f"(the app may be asking to save changes). Nothing was force-closed.", {"key": key})
        return ToolResult(True, f"Closed {key} ({len(gone)} process(es)).", {"key": key})

    async def verify(self, args, result, ctx):
        procs = KNOWN_APPS.get(result.data.get("key", ""), ([], []))[1]
        names = {(p.info.get("name") or "").lower() for p in psutil.process_iter(["name"])}
        ok = not any(n in names for n in procs)
        return ok, f"no longer running: {ok}"


class OpenUrlArgs(BaseModel):
    url: str = Field(..., description="http(s) URL, or plain search words")


class OpenWebsite(Tool):
    name = "open_website"
    description = "Open a website in the user's default browser. Plain words are opened as a web search."
    Args = OpenUrlArgs
    risk = Risk.LOW

    @staticmethod
    def normalize(url: str) -> str:
        u = url.strip()
        if not re.match(r"^https?://", u, re.I):
            if re.fullmatch(r"[\w\-]+(\.[\w\-]+)+(/\S*)?", u):
                u = "https://" + u
            else:
                u = "https://duckduckgo.com/?q=" + quote_plus(u)
        if urlparse(u).scheme not in ("http", "https"):
            raise ValueError("only http(s) URLs are allowed")
        return u

    def assess(self, args, ctx):
        return Assessment(Risk.LOW, True, f"Open {self.normalize(args.url)} in browser")

    async def run(self, args, ctx):
        u = self.normalize(args.url)
        webbrowser.open(u, new=2)
        return ToolResult(True, f"Opened {u}", {"url": u})


TOOLS = [OpenApplication(), CloseApplication(), OpenWebsite()]
