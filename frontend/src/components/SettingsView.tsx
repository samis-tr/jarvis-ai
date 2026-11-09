import { useEffect, useState } from "react";
import { api } from "../api";
import { playTTS } from "../audio";
import type { Jarvis } from "../useJarvis";
import { Btn, Card, Input, Select, Toggle } from "./ui";

const CLAUDE_MODELS: [string, string][] = [
  ["claude-opus-5-5", "Claude Opus 5.5 — $4 / $20 per 1M tokens"],
  ["claude-sonnet-5-5", "Claude Sonnet 5.5 — $2 / $10 per 1M tokens"],
  ["claude-haiku-5-5", "Claude Haiku 5.5 — $0.10 / $0.50 per 1M tokens"],
];
const VOICES = {
  ar: ["ar-LB-RamiNeural", "ar-LB-LaylaNeural", "ar-SY-LaithNeural", "ar-SY-AmanyNeural", "ar-JO-TaimNeural", "ar-JO-SanaNeural", "ar-SA-HamedNeural", "ar-EG-ShakirNeural"],
  de: ["de-DE-ConradNeural", "de-DE-KatjaNeural", "de-DE-FlorianMultilingualNeural", "de-AT-JonasNeural"],
  en: ["en-GB-RyanNeural", "en-GB-SoniaNeural", "en-US-GuyNeural", "en-US-AndrewMultilingualNeural"],
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block py-1.5"><span className="mb-1 block text-xs text-muted">{label}</span>{children}</label>;
}

function SecretField({ name, j }: { name: string; j: Jarvis }) {
  const [val, setVal] = useState("");
  const saved = j.boot?.secrets?.[name];
  const save = async () => {
    try { await api("/api/secrets", { body: { name, value: val } }); setVal(""); j.toast(j.t("key_saved")); j.reload(); }
    catch (e) { j.toast(String(e), "error"); }
  };
  return (
    <div>
      <div className="flex gap-2">
        <Input type="password" autoComplete="off" dir="ltr" value={val} onChange={(e) => setVal(e.target.value)} placeholder={saved ? "••••••••" : ""} />
        <Btn kind="primary" disabled={!val} onClick={save}>{j.t("save")}</Btn>
        {saved && <Btn kind="danger" onClick={async () => { await api(`/api/secrets/${name}`, { method: "DELETE" }); j.reload(); }}>✕</Btn>}
      </div>
      <p className={`mt-1 text-[11px] ${saved ? "text-ok" : "text-muted"}`}>{saved ? `✓ ${j.t("key_saved")}` : j.t("key_missing")}</p>
    </div>
  );
}

const CLOUD: Record<"gemini" | "deepseek", { label: string; field: "gemini_model" | "deepseek_model"; secret: string; keyUrl: string; note: string }> = {
  gemini: {
    label: "Google Gemini", field: "gemini_model", secret: "gemini_api_key", keyUrl: "aistudio.google.com/apikey",
    note: "Free tier with rate limits (Google may use free-tier prompts to improve its products); paid once billing is enabled on the key's Google Cloud project.",
  },
  deepseek: {
    label: "DeepSeek", field: "deepseek_model", secret: "deepseek_api_key", keyUrl: "platform.deepseek.com/api_keys",
    note: "Prepaid credit, billed per token (very low prices). Servers are in China — avoid sending private data.",
  },
};

function CloudModel({ provider, value, onChange, hasKey, j }: { provider: "gemini" | "deepseek"; value: string; onChange: (v: string) => void; hasKey: boolean; j: Jarvis }) {
  const [models, setModels] = useState<string[]>([]);
  const [err, setErr] = useState("");
  const load = async () => {
    setErr("");
    const r = await api<{ ok: boolean; error?: string; models: string[] }>(`/api/provider/models?provider=${provider}`);
    if (r.ok) setModels(r.models); else setErr(r.error || "error");
  };
  useEffect(() => { setModels([]); if (hasKey) load().catch((e) => setErr(String(e))); }, [provider, hasKey]); // eslint-disable-line
  return (
    <div>
      {models.length > 0
        ? <Select value={value} onChange={onChange} options={[...new Set([value, ...models])].map((m) => [m, m])} />
        : <Input dir="ltr" key={provider} defaultValue={value} onBlur={(e) => onChange(e.target.value.trim())} />}
      {err && <p className="mt-1 text-[11px] text-danger">{err}</p>}
      {!hasKey && <p className="mt-1 text-[11px] text-muted">{j.t("api_key")} → model list</p>}
    </div>
  );
}

export default function SettingsView({ j }: { j: Jarvis }) {
  const s = j.settings;
  const [health, setHealth] = useState<{ ok: boolean; error?: string; models?: string[] } | null>(null);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  useEffect(() => {
    api<{ models?: string[] }>("/api/ollama/models").then((r) => setOllamaModels(r.models || [])).catch(() => {});
    j.refreshVoice();
  }, []); // eslint-disable-line
  if (!s || !j.boot) return null;
  const p = s.provider, v = s.voice;
  const set = (patch: Record<string, unknown>) => j.patchSettings(patch).catch((e) => j.toast(String(e), "error"));
  const paid = p.active === "anthropic" || p.active === "gemini" || p.active === "deepseek"
    || (p.active === "openai_compat" && !/localhost|127\.0\.0\.1/.test(p.openai_base_url));
  const cloud = p.active === "gemini" || p.active === "deepseek" ? CLOUD[p.active] : null;
  const test = async () => { setHealth(null); setHealth(await api("/api/provider/health")); };

  return (
    <div className="scroll-thin grid h-full min-h-0 gap-4 overflow-y-auto lg:grid-cols-2">
      <div className="space-y-4">
        <Card title={j.t("ai_model")}>
          <Field label={j.t("provider")}>
            <Select value={p.active} onChange={(val) => { setHealth(null); set({ provider: { active: val } }); }} options={[
              ["ollama", "Ollama (local) — " + j.t("free_local")],
              ["anthropic", "Anthropic Claude API — paid"],
              ["gemini", "Google Gemini API — free tier / paid"],
              ["deepseek", "DeepSeek API — paid (cheap)"],
              ["openai_compat", "OpenAI-compatible endpoint"],
              ["mock", "Mock — " + j.t("mock_desc")],
            ]} />
          </Field>
          {p.active === "ollama" && <>
            <Field label={j.t("model")}>
              <Select value={p.ollama_model} onChange={(val) => set({ provider: { ollama_model: val } })}
                options={[...new Set([p.ollama_model, ...ollamaModels])].map((m) => [m, m])} />
            </Field>
            <p className="text-xs text-muted">qwen3.5:4b runs on your GTX 1060 (≈3 GB VRAM). Good for chat, Arabic and simple tool use; for long multi-step plans and best Arabic writing quality a cloud model (Claude) is stronger.</p>
          </>}
          {p.active === "anthropic" && <>
            <Field label={j.t("model")}><Select value={p.anthropic_model} onChange={(val) => set({ provider: { anthropic_model: val } })} options={CLAUDE_MODELS} /></Field>
            <Field label="Effort"><Select value={p.anthropic_effort} onChange={(val) => set({ provider: { anthropic_effort: val } })} options={[["low", "low"], ["medium", "medium"], ["high", "high"]]} /></Field>
            <Field label={`${j.t("api_key")} (console.anthropic.com)`}><SecretField name="anthropic_api_key" j={j} /></Field>
          </>}
          {cloud && (p.active === "gemini" || p.active === "deepseek") && <>
            <Field label={`${j.t("api_key")} (${cloud.keyUrl})`}><SecretField name={cloud.secret} j={j} /></Field>
            <Field label={j.t("model")}>
              <CloudModel provider={p.active} value={p[cloud.field]} hasKey={!!j.boot?.secrets?.[cloud.secret]} j={j}
                onChange={(val) => set({ provider: { [cloud.field]: val } })} />
            </Field>
            <p className="text-xs text-muted">{cloud.note}</p>
          </>}
          {p.active === "openai_compat" && <>
            <Field label="Base URL"><Input dir="ltr" defaultValue={p.openai_base_url} onBlur={(e) => set({ provider: { openai_base_url: e.target.value } })} /></Field>
            <Field label={j.t("model")}><Input dir="ltr" defaultValue={p.openai_model} onBlur={(e) => set({ provider: { openai_model: e.target.value } })} /></Field>
            <Field label={j.t("api_key")}><SecretField name="openai_api_key" j={j} /></Field>
          </>}
          {paid && !p.paid_acknowledged[p.active] && (
            <div className="glow-amber mt-3 rounded-xl border border-amber/60 bg-amber/5 p-3 text-sm">
              <p className="text-amber">{j.t("paid_warning")}</p>
              <Btn kind="amber" className="mt-2" onClick={() => set({ provider: { paid_acknowledged: { ...p.paid_acknowledged, [p.active]: true } } })}>{j.t("paid_ack")}</Btn>
            </div>
          )}
          {paid && p.paid_acknowledged[p.active] && (
            <p className="mt-2 text-xs text-amber">{j.t("cost")}: billed per token. <button className="underline" onClick={() => set({ provider: { paid_acknowledged: { ...p.paid_acknowledged, [p.active]: false } } })}>revoke</button></p>
          )}
          <div className="mt-3 flex items-center gap-3">
            <Btn onClick={test}>{j.t("test")}</Btn>
            {health && <span className={`text-xs ${health.ok ? "text-ok" : "text-danger"}`}>{health.ok ? "✓ OK" : health.error}</span>}
          </div>
        </Card>

        <Card title={j.t("language")}>
          <Field label={j.t("ui_language")}>
            <Select value={s.ui_language} onChange={(val) => set({ ui_language: val })} options={[["ar", "العربية"], ["de", "Deutsch"], ["en", "English"]]} />
          </Field>
          <Field label={j.t("your_name")}><Input dir="auto" defaultValue={s.user_name} onBlur={(e) => set({ user_name: e.target.value })} /></Field>
        </Card>
      </div>

      <div className="space-y-4">
        <Card title={j.t("voice")}>
          <Toggle checked={v.microphone_enabled} onChange={(val) => set({ voice: { microphone_enabled: val } })} label={v.microphone_enabled ? j.t("mic_on") : j.t("mic_off")} />
          <Field label={j.t("stt_model")}>
            <div className="flex gap-2">
              <Select value={v.stt_model} onChange={(val) => set({ voice: { stt_model: val } }).then(() => j.refreshVoice())}
                options={Object.entries(j.boot.stt_models).map(([k, mb]) => [k, `${k} (${mb} MB)`])} />
              {j.voice && !j.voice.downloaded && (
                <Btn kind="primary" disabled={j.voice.downloading} onClick={() => api("/api/voice/model/download", { body: {} }).then(() => j.refreshVoice())}>
                  {j.voice.downloading ? j.t("downloading") : `${j.t("download")} ${j.voice.size_mb ?? ""} MB`}
                </Btn>
              )}
            </div>
            {j.voice && <p className={`mt-1 text-[11px] ${j.voice.downloaded ? "text-ok" : "text-amber"}`} dir="ltr">
              {j.voice.downloaded ? `✓ ${j.t("downloaded")}` : j.t("not_downloaded")}{j.voice.device ? ` · ${j.voice.device}` : ""}{j.voice.error ? ` · ${j.voice.error}` : ""}
            </p>}
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={j.t("device")}><Select value={v.stt_device} onChange={(val) => set({ voice: { stt_device: val } })} options={[["auto", "auto (GPU→CPU)"], ["cuda", "GPU (CUDA)"], ["cpu", "CPU"]]} /></Field>
            <Field label={j.t("language")}><Select value={v.stt_language} onChange={(val) => set({ voice: { stt_language: val } })} options={[["auto", "auto"], ["ar", "العربية"], ["de", "Deutsch"], ["en", "English"]]} /></Field>
          </div>
          <Field label={j.t("mic_device")}>
            <Select value={String(v.input_device ?? "")} onChange={(val) => set({ voice: { input_device: val === "" ? null : Number(val) } })}
              options={[["", "Windows default"], ...(j.voice?.devices || []).map((d) => [String(d.index), d.name] as [string, string])]} />
          </Field>
          <Toggle checked={v.tts_enabled} onChange={(val) => set({ voice: { tts_enabled: val } })} label={j.t("tts_enabled")} desc="Microsoft Edge neural voices — free, but the spoken text is sent to Microsoft's online service." />
          <div className="grid grid-cols-3 gap-2">
            {(["ar", "de", "en"] as const).map((l) => (
              <Field key={l} label={j.t(`voice_${l}`)}>
                <Select value={v[`tts_voice_${l}`]} onChange={(val) => set({ voice: { [`tts_voice_${l}`]: val } })} options={VOICES[l].map((x) => [x, x.split("-").slice(1).join("-").replace("Neural", "")])} />
              </Field>
            ))}
          </div>
          <Btn className="mt-2 text-xs" onClick={async () => {
            const sample = { ar: "أهلاً، أنا جارفيس. كيف فيني ساعدك؟", de: "Hallo, ich bin Jarvis. Wie kann ich helfen?", en: "Hello, I'm Jarvis. How can I help?" }[s.ui_language];
            try { const r = await api<{ id: string }>("/api/tts", { body: { text: sample } }); playTTS(r.id); }
            catch (e) { j.toast(String(e), "error"); }
          }}>▶ {j.t("test")}</Btn>
        </Card>

        <Card title="Web">
          <Field label="Brave Search API key (free tier: api-dashboard.search.brave.com)"><SecretField name="brave_api_key" j={j} /></Field>
          <Field label="Wikipedia API contact (e-mail or URL, required by Wikimedia's API policy)">
            <Input dir="ltr" defaultValue={s.web.wikipedia_contact} onBlur={(e) => set({ web: { wikipedia_contact: e.target.value.trim() } })} />
          </Field>
          <Toggle checked={s.web.browser_visible} onChange={(val) => set({ web: { browser_visible: val } })} label="Visible automation browser"
            desc="Needs Playwright's Chromium: run `.venv\Scripts\playwright install chromium` once (~170 MB)." />
        </Card>
      </div>
    </div>
  );
}
