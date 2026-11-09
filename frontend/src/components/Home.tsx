import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { stopSpeech } from "../audio";
import type { Jarvis } from "../useJarvis";
import Markdown from "./Markdown";
import Orb from "./Orb";
import SystemGauges from "./SystemGauges";
import TaskPanel from "./TaskPanel";
import { Btn, Icon, Svg } from "./ui";

function useVoiceControls(j: Jarvis) {
  const holding = useRef(false);
  const start = async (mode: "ptt" | "vad") => {
    stopSpeech();
    if (!j.voice?.downloaded) { j.toast(`${j.t("stt_model")}: ${j.t("not_downloaded")} → ${j.t("nav_settings")}`, "error"); return; }
    try { await api("/api/voice/start", { body: { mode, conversation_id: j.conversationId } }); }
    catch (e) { j.toast(String(e), "error"); }
  };
  const stop = () => api("/api/voice/stop", { body: {} }).catch(() => {});
  const down = () => { if (!holding.current) { holding.current = true; start("ptt"); } };
  const up = () => { if (holding.current) { holding.current = false; stop(); } };
  useEffect(() => {
    const kd = (e: KeyboardEvent) => { if (e.ctrlKey && e.code === "Space") { e.preventDefault(); down(); } };
    const ku = (e: KeyboardEvent) => { if (e.code === "Space" || e.key === "Control") up(); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") stopSpeech(); };
    window.addEventListener("keydown", kd); window.addEventListener("keyup", ku); window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("keydown", kd); window.removeEventListener("keyup", ku); window.removeEventListener("keydown", esc); };
  });
  return { down, up, once: () => start("vad") };
}

export default function Home({ j }: { j: Jarvis }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const v = useVoiceControls(j);
  const micEnabled = j.settings?.voice.microphone_enabled ?? false;
  const recording = j.phase === "listening";

  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" }); }, [j.messages.length]);

  const submit = async (msg?: string) => {
    const m = (msg ?? text).trim();
    if (!m || sending) return;
    setSending(true);
    try { await j.send(m); setText(""); } catch (e) { j.toast(String(e), "error"); } finally { setSending(false); }
  };

  const toggleMic = () => j.patchSettings({ voice: { microphone_enabled: !micEnabled } });
  const examples = [j.t("ex1"), j.t("ex2"), j.t("ex3"), j.t("ex4")];

  return (
    <div className="grid h-full min-h-0 grid-cols-1 grid-rows-[minmax(0,1fr)_auto] gap-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:grid-rows-1">
      {/* center */}
      <div className="flex min-h-0 flex-col">
        <div className="relative flex shrink-0 flex-col items-center pt-2">
          <div className="grid-bg pointer-events-none absolute inset-0" />
          <Orb phase={j.phase} size={300} />
          <div className="-mt-3 text-center">
            <div className={`text-sm font-medium tracking-wide ${j.phase === "waiting_approval" ? "text-amber" : "text-cyan"}`} aria-live="polite">
              {j.t(`phase_${j.phase}` as any)}
            </div>
            {j.phaseDetail && <div className="mt-0.5 max-w-md truncate text-xs text-muted" dir="auto">{j.phaseDetail}</div>}
          </div>
        </div>

        <div ref={scroller} className="scroll-thin mt-3 min-h-0 flex-1 space-y-3 overflow-y-auto px-1 pb-2">
          {j.messages.length === 0 && (
            <div className="mx-auto mt-4 max-w-xl text-center">
              <p className="text-ink/80">{j.t("welcome")}</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {examples.map((ex) => <Btn key={ex} onClick={() => submit(ex)} className="text-xs">{ex}</Btn>)}
              </div>
            </div>
          )}
          {j.messages.map((m, i) => (
            <div key={i} className={`rise flex ${m.role === "user" ? "justify-start" : "justify-end"}`}>
              <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-[15px] ${m.role === "user"
                ? "rounded-ss-sm border border-line bg-panel-2/80" : "rounded-se-sm border border-cyan/25 bg-cyan/[0.06]"}`} dir="auto">
                {m.role === "assistant" ? <Markdown text={m.content} /> : <span className="whitespace-pre-wrap">{m.content}</span>}
                {m.state && m.state !== "COMPLETED" && <div className="mt-1 font-mono text-[10px] text-muted" dir="ltr">{m.state}</div>}
              </div>
            </div>
          ))}
        </div>

        {/* composer */}
        <form className="glass mt-2 flex shrink-0 items-end gap-2 rounded-2xl p-2" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <button type="button" onClick={toggleMic} title={micEnabled ? j.t("mic_on") : j.t("mic_off")}
            className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border ${micEnabled ? "border-line text-muted hover:text-cyan" : "border-danger/50 text-danger"}`}>
            <Svg d={micEnabled ? Icon.mic : Icon.micOff} />
          </button>
          <button type="button" disabled={!micEnabled}
            onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); v.down(); }} onPointerUp={v.up} onPointerCancel={v.up}
            title={j.t("hold_to_talk")}
            className={`relative grid h-11 shrink-0 select-none place-items-center rounded-xl border px-4 text-sm font-medium transition disabled:opacity-30
              ${recording ? "glow-cyan border-cyan bg-cyan/25 text-cyan" : "border-cyan/40 bg-cyan/10 text-cyan hover:bg-cyan/20"}`}>
            <span className="flex items-center gap-2"><Svg d={Icon.mic} className="h-4 w-4" />{recording ? j.t("phase_listening") : "PTT"}</span>
          </button>
          <Btn disabled={!micEnabled || recording} onClick={v.once} className="h-11 shrink-0 text-xs" title={j.t("talk_once")}>{j.t("talk_once")}</Btn>
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={1} dir="auto"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder={j.t("placeholder")}
            className="max-h-36 min-h-11 flex-1 resize-none rounded-xl border border-line bg-panel-2/70 px-3 py-2.5 text-[15px] outline-none placeholder:text-muted/60 focus:border-cyan/50" />
          {j.speaking && <Btn onClick={stopSpeech} className="h-11" title="Esc"><Svg d={Icon.speaker} className="h-4 w-4" />■</Btn>}
          <Btn kind="primary" type="submit" disabled={!text.trim() || sending} className="h-11 w-11 !px-0" title={j.t("send")}>
            <Svg d={Icon.send} className="h-5 w-5 rtl:-scale-x-100" />
          </Btn>
        </form>
      </div>

      {/* right column */}
      <aside className="scroll-thin flex max-h-[40vh] min-h-0 flex-col gap-4 overflow-y-auto lg:max-h-none">
        <TaskPanel j={j} />
        <SystemGauges j={j} />
      </aside>
    </div>
  );
}
