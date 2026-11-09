import { useState } from "react";
import { TOKEN } from "./api";
import HistoryView from "./components/HistoryView";
import Home from "./components/Home";
import MemoryView from "./components/MemoryView";
import PermissionsView from "./components/PermissionsView";
import SettingsView from "./components/SettingsView";
import { Icon, Svg } from "./components/ui";
import { useJarvis } from "./useJarvis";

type View = "home" | "tasks" | "memory" | "perms" | "settings";

export default function App() {
  const j = useJarvis();
  const [view, setView] = useState<View>("home");

  if (!TOKEN) {
    return <div className="grid h-full place-items-center p-8 text-center text-muted">Start JARVIS with <code className="mx-1 text-cyan">start-jarvis.ps1</code> — the session token is missing.</div>;
  }

  const nav: [View, keyof typeof Icon, Parameters<typeof j.t>[0]][] = [
    ["home", "home", "nav_home"], ["tasks", "tasks", "nav_tasks"], ["memory", "memory", "nav_memory"],
    ["perms", "shield", "nav_perms"], ["settings", "gear", "nav_settings"],
  ];
  const providerLabel = j.settings ? ({ ollama: `Ollama · ${j.settings.provider.ollama_model}`, anthropic: `Claude · ${j.settings.provider.anthropic_model}`,
    openai_compat: `API · ${j.settings.provider.openai_model}`, gemini: `Gemini · ${j.settings.provider.gemini_model}`,
    deepseek: `DeepSeek · ${j.settings.provider.deepseek_model}`, mock: "Mock" } as const)[j.settings.provider.active] : "";
  const paid = j.settings && ["anthropic", "openai_compat", "gemini", "deepseek"].includes(j.settings.provider.active);

  return (
    <div className="flex h-full">
      {/* nav rail */}
      <nav className="glass flex w-[72px] shrink-0 flex-col items-center gap-2 border-y-0 border-s-0 py-4">
        <div className="mb-4 grid h-10 w-10 place-items-center rounded-xl border border-cyan/40 bg-cyan/10 font-mono text-sm font-bold text-cyan">J</div>
        {nav.map(([id, icon, label]) => (
          <button key={id} onClick={() => setView(id)} title={j.t(label)} aria-label={j.t(label)}
            className={`grid h-11 w-11 place-items-center rounded-xl border transition ${view === id ? "border-cyan/50 bg-cyan/10 text-cyan" : "border-transparent text-muted hover:text-ink"}`}>
            <Svg d={Icon[icon]} />
          </button>
        ))}
        <div className="flex-1" />
        <button onClick={() => { j.openConversation(null); setView("home"); }} title={j.t("new_chat")} aria-label={j.t("new_chat")}
          className="grid h-11 w-11 place-items-center rounded-xl border border-line text-muted hover:text-cyan"><Svg d={Icon.plus} /></button>
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="flex h-14 shrink-0 items-center gap-3 px-5">
          <h1 className="font-mono text-sm tracking-[0.35em] text-ink">J·A·R·V·I·S</h1>
          <span className={`h-2 w-2 rounded-full ${j.connected ? "bg-ok" : "bg-danger animate-pulse"}`} title={j.connected ? "connected" : "offline"} />
          <span className={`rounded-lg border px-2 py-0.5 font-mono text-[11px] ${paid ? "border-amber/50 text-amber" : "border-line text-muted"}`} dir="ltr">{providerLabel}{paid ? " · $" : ""}</span>
          {j.settings?.security.safe_mode && <span className="rounded-lg border border-ok/50 px-2 py-0.5 text-[11px] text-ok">{j.t("safe_mode")}</span>}
          <span className={`flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-[11px] ${j.phase === "listening" ? "border-cyan text-cyan" : j.settings?.voice.microphone_enabled ? "border-line text-muted" : "border-danger/50 text-danger"}`}>
            <Svg d={j.settings?.voice.microphone_enabled ? Icon.mic : Icon.micOff} className="h-3.5 w-3.5" />
            {j.phase === "listening" ? "REC" : j.settings?.voice.microphone_enabled ? j.t("mic_on") : j.t("mic_off")}
          </span>
          <div className="flex-1" />
          <button onClick={() => j.emergencyStop()}
            className="flex items-center gap-2 rounded-xl border border-danger/70 bg-danger/15 px-4 py-2 text-sm font-semibold text-danger shadow-[0_0_24px_-6px_rgba(255,77,109,0.7)] hover:bg-danger/30">
            <Svg d={Icon.stop} className="h-4 w-4" /> {j.t("stop")}
          </button>
        </header>
        {!j.connected && <div className="mx-5 mb-2 rounded-lg border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs text-danger">{j.t("connection_lost")}</div>}

        <main className="min-h-0 flex-1 px-5 pb-5">
          {view === "home" && <Home j={j} />}
          {view === "tasks" && <HistoryView j={j} />}
          {view === "memory" && <MemoryView j={j} />}
          {view === "perms" && <PermissionsView j={j} />}
          {view === "settings" && <SettingsView j={j} />}
        </main>
      </div>

      {/* toasts */}
      <div className="pointer-events-none fixed bottom-5 start-1/2 z-50 flex -translate-x-1/2 flex-col gap-2 rtl:translate-x-1/2" aria-live="polite">
        {j.toasts.map((x) => (
          <div key={x.id} className={`rise glass pointer-events-auto max-w-lg rounded-xl px-4 py-2 text-sm ${x.kind === "error" ? "border-danger/60 text-danger" : "text-ink"}`} dir="auto">{x.text}</div>
        ))}
      </div>
    </div>
  );
}
