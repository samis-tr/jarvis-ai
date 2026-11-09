import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, connectEvents, type JarvisEvent } from "./api";
import { onSpeaking, playTTS, setMicLevel, stopSpeech } from "./audio";
import { makeT } from "./i18n";
import type { Bootstrap, ChatMsg, Phase, Settings, SystemSnap, Task, VoiceStatus } from "./types";

export interface Toast { id: number; kind: "info" | "error"; text: string }

export function useJarvis() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [connected, setConnected] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [phaseDetail, setPhaseDetail] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [tasks, setTasks] = useState<Record<string, Task>>({});
  const [voice, setVoice] = useState<VoiceStatus | null>(null);
  const [sys, setSys] = useState<SystemSnap | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const convRef = useRef<string | null>(null);
  convRef.current = conversationId;

  const lang = settings?.ui_language ?? "ar";
  const t = useMemo(() => makeT(lang), [lang]);

  const toast = useCallback((text: string, kind: Toast["kind"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((x) => [...x, { id, kind, text }]);
    setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), kind === "error" ? 7000 : 4000);
  }, []);

  const refreshVoice = useCallback(async () => {
    try { setVoice(await api<VoiceStatus>("/api/voice/status")); } catch { /* ignore */ }
  }, []);

  const load = useCallback(async () => {
    const b = await api<Bootstrap>("/api/bootstrap");
    setBoot(b);
    setSettings(b.settings);
    setVoice(b.voice);
    setPhase(b.status.phase);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  useEffect(() => onSpeaking(setSpeaking), []);

  useEffect(() => {
    load().catch((e) => toast(String(e), "error"));
    const handle = (e: JarvisEvent) => {
      switch (e.type) {
        case "status": setPhase(e.phase); setPhaseDetail(e.detail || ""); break;
        case "message": {
          if (convRef.current && e.conversation_id !== convRef.current) break;
          if (!convRef.current) setConversationId(e.conversation_id);
          setMessages((m) => [...m, { role: e.role, content: e.content, task_id: e.task_id, state: e.state, ts: e.ts, usage: e.usage }]);
          break;
        }
        case "task": setTasks((x) => ({ ...x, [e.task.id]: e.task })); break;
        case "audio_level": setMicLevel(e.level); break;
        case "voice": if (e.state !== "listening") refreshVoice(); else setVoice((v) => v && { ...v, recording: true }); break;
        case "transcript":
          if (e.error === "too_short" || (!e.error && !e.text)) toast(makeT(lang)("heard_nothing"));
          else if (e.error) toast(e.error, "error");
          refreshVoice();
          break;
        case "voice_submitted": if (!convRef.current) setConversationId(e.conversation_id); break;
        case "speak": playTTS(e.id).catch((err) => toast(`Audio: ${err}`, "error")); break;
        case "speak_error": toast(`TTS: ${e.error}`, "error"); break;
        case "stop_audio": stopSpeech(); break;
        case "voice_model": refreshVoice(); if (e.state === "error") toast(e.error, "error"); break;
        case "settings": setSettings(e.settings); break;
        case "emergency_stop": toast(`STOP — ${e.cancelled} task(s) cancelled`, "error"); break;
      }
    };
    return connectEvents(handle, setConnected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // live system gauges (real psutil / nvidia-smi values)
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try { const s = await api<SystemSnap>("/api/system"); if (!stop) setSys(s); } catch { /* ignore */ }
    };
    tick();
    const h = setInterval(tick, 4000);
    return () => { stop = true; clearInterval(h); };
  }, []);

  const send = useCallback(async (text: string, speak = false) => {
    const r = await api<{ task_id: string; conversation_id: string }>("/api/chat", {
      body: { text, conversation_id: convRef.current, speak },
    });
    if (!convRef.current) setConversationId(r.conversation_id);
    return r;
  }, []);

  const patchSettings = useCallback(async (patch: Record<string, unknown>) => {
    const s = await api<Settings>("/api/settings", { method: "PATCH", body: patch });
    setSettings(s);
    return s;
  }, []);

  const openConversation = useCallback(async (id: string | null) => {
    setConversationId(id);
    if (!id) { setMessages([]); return; }
    const rows = await api<{ role: "user" | "assistant"; content: string; created: number }[]>(`/api/conversations/${id}`);
    setMessages(rows.map((r) => ({ role: r.role, content: r.content, ts: r.created })));
  }, []);

  const emergencyStop = useCallback(async () => {
    stopSpeech();
    await api("/api/stop", { body: {} });
  }, []);

  const displayPhase: Phase = speaking && phase === "idle" ? "speaking" : phase;
  const activeTask = useMemo(() => {
    const list = Object.values(tasks).filter((x) => x.conversation_id === conversationId || !conversationId);
    return list.sort((a, b) => b.created - a.created)[0] ?? null;
  }, [tasks, conversationId]);

  return {
    boot, settings, connected, phase: displayPhase, phaseDetail, speaking, conversationId, messages, tasks, activeTask,
    voice, sys, toasts, t, lang, toast, send, patchSettings, openConversation, emergencyStop, refreshVoice, reload: load,
  };
}

export type Jarvis = ReturnType<typeof useJarvis>;
