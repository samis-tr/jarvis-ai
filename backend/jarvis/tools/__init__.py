from jarvis.tools.base import ToolRegistry


def build_registry() -> ToolRegistry:
    from jarvis.tools import apps, browser, filesystem, memory_tools, system
    return ToolRegistry([*apps.TOOLS, *filesystem.TOOLS, *system.TOOLS, *browser.TOOLS, *memory_tools.TOOLS])
