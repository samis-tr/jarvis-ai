import type { Lang } from "./types";

const ar = {
  nav_home: "الرئيسية", nav_tasks: "سجل المهام", nav_memory: "الذاكرة", nav_perms: "الصلاحيات", nav_settings: "الإعدادات",
  phase_idle: "جاهز", phase_listening: "عم إسمعك…", phase_transcribing: "عم إفهم كلامك…", phase_thinking: "عم فكّر…",
  phase_executing: "عم نفّذ…", phase_waiting_approval: "بانتظار موافقتك", phase_speaking: "عم إحكي…",
  placeholder: "اكتب لجارفيس…", send: "إرسال", hold_to_talk: "اضغط مطوّلاً للتكلم (أو Ctrl+Space)",
  talk_once: "استمع مرة", mic_off: "الميكروفون مقفول", mic_on: "الميكروفون مفعّل", stop: "إيقاف طارئ",
  new_chat: "محادثة جديدة", current_task: "المهمة الحالية", no_task: "ما في مهمة شغّالة هلّق.",
  approve: "موافق", deny: "رفض", approve_task: "اسمح لهالأداة بهالمهمة", cancel_task: "إلغاء المهمة",
  approval_needed: "جارفيس بدّه موافقتك", risk_low: "منخفض", risk_medium: "متوسط", risk_high: "عالي",
  system: "النظام", connection_lost: "انقطع الاتصال بالخادم المحلي — عم حاول من جديد…",
  welcome: "أهلاً! أنا جارفيس. اكتبلي أو احكيلي شو بدك.", examples: "جرّب:",
  ex1: "افتح المفكرة", ex2: "أنشئ ملف باسم ملاحظات اليوم", ex3: "ابحث عن أفضل ميكروفون لليوتيوب ولخّصلي", ex4: "شو وضع الجهاز؟",
  tasks_title: "سجل المهام والإجراءات", empty: "فاضي", memory_title: "الذاكرة الدائمة", add: "إضافة", save: "حفظ",
  delete: "حذف", edit: "تعديل", search: "بحث…", memory_enabled: "تفعيل الذاكرة", save_conv: "حفظ المحادثات",
  clear_all: "مسح كل الذكريات", confirm_clear: "متأكد بدك تمسح كل الذكريات؟ ما في رجعة.",
  perms_title: "الصلاحيات والأمان", safe_mode: "الوضع الآمن", safe_mode_desc: "كل تعديل بيحتاج موافقة، والإجراءات عالية الخطورة ممنوعة.",
  approved_dirs: "المجلدات المسموحة", add_dir: "إضافة مجلد (مسار كامل)", auto_medium: "مسموح تلقائياً داخل المجلدات المسموحة",
  tools: "الأدوات", enabled: "مفعّلة", disabled: "معطّلة",
  settings_title: "الإعدادات", ai_model: "نموذج الذكاء الاصطناعي", provider: "المزوّد", model: "النموذج", test: "اختبار",
  paid_warning: "هاد مزوّد سحابي ممكن يكلّف مصاري: الرسائل بتنحسب على حساب الـ API تبعك (منفصل عن أي اشتراك متل Claude أو Gemini). ورسائلك بتنبعت لسيرفراتهم. بتوافق؟",
  paid_ack: "فهمت إنو مدفوع وبوافق", api_key: "مفتاح API", key_saved: "محفوظ في Windows Credential Manager",
  key_missing: "مش محفوظ", voice: "الصوت", stt_model: "نموذج التعرّف على الكلام", download: "تنزيل",
  downloading: "عم ينزّل…", downloaded: "منزّل", not_downloaded: "مش منزّل", language: "اللغة", ui_language: "لغة الواجهة",
  tts_enabled: "الرد بالصوت", mic_device: "الميكروفون", voice_ar: "الصوت العربي", voice_de: "الصوت الألماني", voice_en: "الصوت الإنجليزي",
  your_name: "اسمك", cost: "التكلفة", free_local: "مجاني — شغّال على جهازك", mock_desc: "وضع تجريبي بدون ذكاء اصطناعي (للاختبار)",
  verified: "تم التحقق", unverified: "فشل التحقق", tokens: "رموز", transcript: "سمعت:", heard_nothing: "ما سمعت شي واضح.",
  open: "فتح", all_categories: "كل الفئات", device: "الجهاز", ok: "تمام", error: "خطأ",
};

type Dict = typeof ar;

const en: Dict = {
  nav_home: "Home", nav_tasks: "Task history", nav_memory: "Memory", nav_perms: "Permissions", nav_settings: "Settings",
  phase_idle: "Ready", phase_listening: "Listening…", phase_transcribing: "Transcribing…", phase_thinking: "Thinking…",
  phase_executing: "Executing…", phase_waiting_approval: "Waiting for your approval", phase_speaking: "Speaking…",
  placeholder: "Message JARVIS… (Enter to send)", send: "Send", hold_to_talk: "Hold to talk (or Ctrl+Space)",
  talk_once: "Listen once", mic_off: "Microphone off", mic_on: "Microphone on", stop: "Emergency stop",
  new_chat: "New chat", current_task: "Current task", no_task: "No task running.",
  approve: "Approve", deny: "Deny", approve_task: "Allow this tool for this task", cancel_task: "Cancel task",
  approval_needed: "JARVIS needs your approval", risk_low: "Low", risk_medium: "Medium", risk_high: "High",
  system: "System", connection_lost: "Lost connection to the local backend — retrying…",
  welcome: "Hi! I'm JARVIS. Type or talk to me.", examples: "Try:",
  ex1: "Open notepad", ex2: "Create a file called today-notes", ex3: "Research the best YouTube microphone and summarize", ex4: "How is my PC doing?",
  tasks_title: "Task & action history", empty: "Empty", memory_title: "Persistent memory", add: "Add", save: "Save",
  delete: "Delete", edit: "Edit", search: "Search…", memory_enabled: "Enable memory", save_conv: "Save conversations",
  clear_all: "Clear all memories", confirm_clear: "Really delete all memories? This cannot be undone.",
  perms_title: "Permissions & security", safe_mode: "Safe mode", safe_mode_desc: "Every change needs approval; high-risk actions are blocked.",
  approved_dirs: "Approved folders", add_dir: "Add folder (full path)", auto_medium: "Auto-allowed inside approved folders",
  tools: "Tools", enabled: "Enabled", disabled: "Disabled",
  settings_title: "Settings", ai_model: "AI model", provider: "Provider", model: "Model", test: "Test",
  paid_warning: "This is a cloud provider that can cost money: messages are billed to your API account (separate from any Claude/Gemini subscription) and sent to their servers. Continue?",
  paid_ack: "I understand it is paid", api_key: "API key", key_saved: "Saved in Windows Credential Manager",
  key_missing: "Not saved", voice: "Voice", stt_model: "Speech recognition model", download: "Download",
  downloading: "Downloading…", downloaded: "Downloaded", not_downloaded: "Not downloaded", language: "Language", ui_language: "Interface language",
  tts_enabled: "Spoken replies", mic_device: "Microphone", voice_ar: "Arabic voice", voice_de: "German voice", voice_en: "English voice",
  your_name: "Your name", cost: "Cost", free_local: "Free — runs on your PC", mock_desc: "Test mode without AI",
  verified: "Verified", unverified: "Verification failed", tokens: "tokens", transcript: "Heard:", heard_nothing: "Didn't catch that.",
  open: "Open", all_categories: "All categories", device: "Device", ok: "OK", error: "Error",
};

const de: Dict = {
  ...en,
  nav_home: "Start", nav_tasks: "Aufgabenverlauf", nav_memory: "Gedächtnis", nav_perms: "Berechtigungen", nav_settings: "Einstellungen",
  phase_idle: "Bereit", phase_listening: "Ich höre zu…", phase_transcribing: "Verstehe…", phase_thinking: "Denke nach…",
  phase_executing: "Führe aus…", phase_waiting_approval: "Wartet auf deine Freigabe", phase_speaking: "Spreche…",
  placeholder: "Nachricht an JARVIS… (Enter zum Senden)", send: "Senden", hold_to_talk: "Gedrückt halten zum Sprechen (oder Strg+Leertaste)",
  talk_once: "Einmal zuhören", mic_off: "Mikrofon aus", mic_on: "Mikrofon an", stop: "Not-Stopp",
  new_chat: "Neuer Chat", current_task: "Aktuelle Aufgabe", no_task: "Keine laufende Aufgabe.",
  approve: "Erlauben", deny: "Ablehnen", approve_task: "Werkzeug für diese Aufgabe erlauben", cancel_task: "Aufgabe abbrechen",
  approval_needed: "JARVIS braucht deine Freigabe", risk_low: "Niedrig", risk_medium: "Mittel", risk_high: "Hoch",
  welcome: "Hallo! Ich bin JARVIS. Schreib oder sprich mit mir.", examples: "Probier:",
  ex1: "Öffne den Editor", ex2: "Erstelle eine Datei namens notizen", ex3: "Recherchiere das beste YouTube-Mikrofon", ex4: "Wie geht es meinem PC?",
  settings_title: "Einstellungen", ai_model: "KI-Modell", provider: "Anbieter", model: "Modell", test: "Testen",
  safe_mode: "Sicherer Modus", approved_dirs: "Freigegebene Ordner", tools: "Werkzeuge", voice: "Stimme",
  download: "Herunterladen", language: "Sprache", ui_language: "Oberflächensprache", save: "Speichern", delete: "Löschen",
};

export const DICTS: Record<Lang, Dict> = { ar, en, de };
export type TKey = keyof Dict;
export const makeT = (lang: Lang) => (k: TKey) => DICTS[lang][k] ?? DICTS.en[k] ?? k;
