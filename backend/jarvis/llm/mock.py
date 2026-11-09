"""Deterministic offline 'mock AI' for testing without any model or API.

It recognizes a handful of commands in Arabic / German / English and maps them to
real tool calls, so the tool, permission and task machinery can be exercised for
free. Its answers are clearly labeled as mock output.
"""
from __future__ import annotations

import re
import uuid

from jarvis.llm.base import ChatMessage, LLMResponse, Provider, ToolCall

OPEN = r"(?:افتح(?:لي)?|إفتح|شغّ?ل(?:لي)?|open|start|launch|öffne|starte)"
CREATE_FILE = r"(?:(?:أنشئ|انشئ|اعمل(?:لي)?|اكتب(?:لي)?|سوي(?:لي)?|create|make|write|erstelle|schreibe?)\s+(?:(?:a|an|ein(?:e|en)?)\s+)?(?:test\s*)?(?:ملف|مستند|وثيقة|file|document|note|datei|dokument|notiz))"
CREATE_FOLDER = r"(?:(?:أنشئ|انشئ|اعمل(?:لي)?|سوي(?:لي)?|create|make|erstelle)\s+(?:(?:a|an|ein(?:e|en)?)\s+)?(?:مجلد|فولدر|folder|directory|ordner))"
RESEARCH = r"(?:ابحث(?:\s+عن)?|دوّ?ر(?:\s+على)?|research|search(?:\s+for)?|recherchiere|suche(?:\s+nach)?)"
SYSTEM = r"(?:النظام|الجهاز|المعالج|الرام|الذاكرة|كرت الشاشة|system|cpu|ram|gpu|memory usage|systeminfo|speicher|prozessor)"


def _first_sentence(s: str) -> str:
    return re.split(r"(?<=[.!?؟])\s", s.strip())[0]


def _call(tool_name: str, **args) -> ToolCall:
    return ToolCall(uuid.uuid4().hex[:10], tool_name, args)


def _name_after(pattern: str, text: str) -> str:
    m = re.search(pattern + r"\s*[:\-]?\s*[\"'«]?(.+?)[\"'»]?\s*$", text, re.I)
    return m.group(1).strip(" .؟?!") if m else ""


class MockProvider(Provider):
    name = "mock"
    paid = False

    async def chat(self, system, messages, tools):
        last = messages[-1]
        if last.role == "tool":
            return self._after_tools(messages)
        text = last.content.strip()
        low = text.lower()
        tool_names = {t["name"] for t in tools}

        if re.search(CREATE_FOLDER, low) and "create_folder" in tool_names:
            name = _name_after(CREATE_FOLDER + r"(?:\s+(?:باسم|اسمه|named|called|namens))?", text) or "New Folder"
            return LLMResponse("", [_call("create_folder", path=name)])
        if re.search(CREATE_FILE, low) and "create_file" in tool_names:
            name = _name_after(CREATE_FILE + r"(?:\s+(?:باسم|اسمه|named|called|namens))?", text) or "jarvis-test"
            if not re.search(r"\.\w{2,4}$", name):
                name += ".md"
            content = f"# {name.rsplit('.', 1)[0]}\n\nCreated by JARVIS (mock mode).\n"
            return LLMResponse("", [_call("create_file", path=name, content=content)])
        if re.search(RESEARCH, low) and "research_topic" in tool_names:
            topic = _name_after(RESEARCH, text) or text
            return LLMResponse("", [_call("research_topic", topic=topic, pages=2)])
        if re.search(OPEN, low):
            target = _name_after(OPEN, text)
            if re.search(r"(https?://|www\.|\.\w{2,3}(/|$))", target) and "open_website" in tool_names:
                return LLMResponse("", [_call("open_website", url=target)])
            if target and "open_application" in tool_names:
                return LLMResponse("", [_call("open_application", name=target)])
        if re.search(SYSTEM, low) and "system_info" in tool_names:
            return LLMResponse("", [_call("system_info")])

        if re.search(r"[؀-ۿ]", text):
            reply = f"[وضع تجريبي] وصلتني رسالتك: «{text}». هذا رد تجريبي بدون ذكاء اصطناعي. اختر Ollama أو Claude من الإعدادات للحصول على إجابات حقيقية."
        elif re.search(r"\b(der|die|das|ist|und|ich|bitte|wie|was)\b", low):
            reply = f"[Mock-Modus] Nachricht erhalten: „{text}“. Dies ist eine Testantwort ohne KI."
        else:
            reply = f"[Mock mode] I received: \"{text}\". This is a test reply without an AI model."
        return LLMResponse(reply)

    def _after_tools(self, messages: list[ChatMessage]) -> LLMResponse:
        results = []
        for m in reversed(messages):
            if m.role != "tool":
                break
            results.append(m)
        results.reverse()
        parts = []
        for r in results:
            status = "✗" if r.is_error else "✓"
            body = r.content
            if "<untrusted_content>" in body:
                body = body.split("\n", 2)[-1].replace("</untrusted_content>", "")
                # mock "summary": first sentence of each source
                srcs = re.findall(r"SOURCE \[(\d+)\] (.+?) — (\S+)\n(.{0,300})", body, re.S)
                if srcs:
                    body = "\n".join(f"[{n}] {t}: {_first_sentence(s)} ({u})" for n, t, u, s in srcs)
                else:
                    body = body[:400]
            parts.append(f"{status} {r.tool_name}: {body[:600]}")
        return LLMResponse("[Mock] " + "\n".join(parts))
