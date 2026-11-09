export type Phase = "idle" | "listening" | "transcribing" | "thinking" | "executing" | "waiting_approval" | "speaking";
export type Lang = "ar" | "de" | "en";
export type TaskState = "PLANNING" | "WAITING_FOR_APPROVAL" | "EXECUTING" | "VERIFYING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface Step {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  summary: string;
  risk: "low" | "medium" | "high";
  decision: string;
  reason: string;
  status: string;
  output: string;
  verified: boolean | null;
  verify_note: string;
  duration_ms: number;
}

export interface Task {
  id: string;
  conversation_id: string;
  request: string;
  state: TaskState;
  plan: Step[];
  result: string;
  error: string;
  created: number;
  usage: Record<string, number>;
}

export interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  task_id?: string;
  state?: TaskState;
  ts: number;
  usage?: Record<string, number>;
}

export interface Settings {
  ui_language: Lang;
  assistant_name: string;
  user_name: string;
  provider: {
    active: "mock" | "ollama" | "anthropic" | "openai_compat" | "gemini" | "deepseek";
    ollama_url: string;
    ollama_model: string;
    anthropic_model: string;
    anthropic_effort: "low" | "medium" | "high";
    openai_base_url: string;
    openai_model: string;
    gemini_model: string;
    deepseek_model: string;
    paid_acknowledged: Record<string, boolean>;
    request_timeout_s: number;
  };
  voice: {
    microphone_enabled: boolean;
    stt_model: string;
    stt_device: "auto" | "cuda" | "cpu";
    stt_language: "auto" | Lang;
    tts_enabled: boolean;
    tts_voice_ar: string;
    tts_voice_de: string;
    tts_voice_en: string;
    vad_silence_ms: number;
    max_record_s: number;
    input_device: number | null;
  };
  security: {
    safe_mode: boolean;
    approved_dirs: string[];
    auto_approve_medium: string[];
    disabled_tools: string[];
    approval_timeout_s: number;
    tool_timeout_s: number;
  };
  memory: { enabled: boolean; save_conversations: boolean };
  web: { browser_visible: boolean; wikipedia_contact: string };
}

export interface ToolInfo { name: string; description: string; risk: "low" | "medium" | "high"; enabled: boolean }

export interface VoiceStatus {
  model: string; downloaded: boolean; loaded: boolean; device: string | null; downloading: boolean;
  size_mb: number | null; recording: boolean; mic_enabled: boolean; error: string;
  devices?: { index: number; name: string; default: boolean }[];
}

export interface Bootstrap {
  version: string;
  settings: Settings;
  status: { phase: Phase; detail: string };
  tools: ToolInfo[];
  secrets: Record<string, boolean>;
  voice: VoiceStatus;
  stt_models: Record<string, number>;
  memory_categories: string[];
  conversations: { id: string; title: string; created: number; updated: number }[];
}

export interface Memory { id: number; category: string; content: string; source: string; created: number; updated: number }

export interface SystemSnap {
  cpu_percent: number; ram_percent: number; ram_used_gb: number; ram_total_gb: number; disk_free_gb: number;
  battery_percent: number | null; plugged_in: boolean | null;
  gpus: { name: string; util_percent: number; mem_used_mb: number; mem_total_mb: number; temp_c: number }[];
}
