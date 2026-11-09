"""System information and (permission-gated) screenshots."""
from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
from pathlib import Path

import psutil
from pydantic import BaseModel

from jarvis.security import paths as P
from jarvis.tools.base import Assessment, Risk, Tool, ToolResult


def gpu_stats() -> list[dict]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        out = subprocess.run(
            [exe, "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
    except Exception:
        return []
    gpus = []
    for line in out.strip().splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 5:
            gpus.append({"name": parts[0], "util_percent": _num(parts[1]), "mem_used_mb": _num(parts[2]),
                         "mem_total_mb": _num(parts[3]), "temp_c": _num(parts[4])})
    return gpus


def _num(s: str):
    try:
        return float(s)
    except ValueError:
        return None


def snapshot() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor))
    bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu_name": platform.processor(),
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / 1e9, 1),
        "ram_total_gb": round(vm.total / 1e9, 1),
        "disk_free_gb": round(disk.free / 1e9, 1),
        "battery_percent": bat.percent if bat else None,
        "plugged_in": bat.power_plugged if bat else None,
        "gpus": gpu_stats(),
    }


class NoArgs(BaseModel):
    pass


class SystemInfo(Tool):
    name = "system_info"
    description = "Get current CPU, RAM, GPU, disk and battery usage of this computer."
    Args = NoArgs
    risk = Risk.LOW

    async def run(self, args, ctx):
        s = await asyncio.to_thread(snapshot)
        g = "; ".join(f"{x['name']} {x['util_percent']}% util, {x['mem_used_mb']:.0f}/{x['mem_total_mb']:.0f} MB VRAM, {x['temp_c']}°C"
                      for x in s["gpus"]) or "no NVIDIA GPU data"
        text = (f"OS: {s['os']}\nCPU: {s['cpu_percent']}% ({s['cpu_cores']} cores/{s['cpu_threads']} threads)\n"
                f"RAM: {s['ram_used_gb']}/{s['ram_total_gb']} GB ({s['ram_percent']}%)\nGPU: {g}\n"
                f"Free disk on system drive: {s['disk_free_gb']} GB\n"
                f"Battery: {s['battery_percent']}%{' (charging)' if s['plugged_in'] else ''}" if s["battery_percent"] is not None
                else f"OS: {s['os']}\nCPU: {s['cpu_percent']}%\nRAM: {s['ram_used_gb']}/{s['ram_total_gb']} GB\nGPU: {g}")
        return ToolResult(True, text, s)


class TopProcesses(Tool):
    name = "top_processes"
    description = "List the processes using the most memory/CPU right now."
    Args = NoArgs
    risk = Risk.LOW

    async def run(self, args, ctx):
        def collect():
            procs = []
            for p in psutil.process_iter(["name", "memory_info", "cpu_percent"]):
                try:
                    procs.append((p.info["name"], p.info["memory_info"].rss / 1e6, p.info["cpu_percent"] or 0))
                except (psutil.Error, AttributeError):
                    pass
            agg: dict[str, list[float]] = {}
            for n, m, c in procs:
                a = agg.setdefault(n or "?", [0.0, 0.0])
                a[0] += m
                a[1] += c
            return sorted(agg.items(), key=lambda kv: -kv[1][0])[:12]
        top = await asyncio.to_thread(collect)
        return ToolResult(True, "\n".join(f"{n}: {m:.0f} MB RAM" for n, (m, c) in top), {"top": top})


class ScreenshotArgs(BaseModel):
    pass


class TakeScreenshot(Tool):
    name = "take_screenshot"
    description = "Take a screenshot of the primary screen and save it as PNG in the JARVIS workspace. Requires user permission."
    Args = ScreenshotArgs
    risk = Risk.MEDIUM  # privacy: always asks (not in auto-approve list by default)
    verifiable = True

    def assess(self, args, ctx):
        return Assessment(Risk.MEDIUM, False, "Capture the screen (may contain private information)")

    async def run(self, args, ctx):
        import mss
        import mss.tools
        from datetime import datetime
        ws = P.resolve(ctx.settings.security.approved_dirs[0]) / "screenshots"
        ws.mkdir(parents=True, exist_ok=True)
        path = ws / f"screenshot_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"

        def grab():
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                mss.tools.to_png(img.rgb, img.size, output=str(path))
                return img.size
        size = await asyncio.to_thread(grab)
        return ToolResult(True, f"Screenshot saved to {path} ({size[0]}x{size[1]}).",
                          {"path": str(path), "width": size[0], "height": size[1]}, artifacts=[str(path)])

    async def verify(self, args, result, ctx):
        ok = Path(result.data["path"]).stat().st_size > 1000
        return ok, f"png written: {ok}"


TOOLS = [SystemInfo(), TopProcesses(), TakeScreenshot()]
