import { useEffect, useState } from "react";
import { api } from "../api";
import type { Memory } from "../types";
import type { Jarvis } from "../useJarvis";
import { Btn, Card, Input, Select, Toggle } from "./ui";

const CATS = ["preference", "project", "fact", "workflow", "task"];

export default function MemoryView({ j }: { j: Jarvis }) {
  const [rows, setRows] = useState<Memory[]>([]);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [draft, setDraft] = useState({ category: "preference", content: "" });
  const [editing, setEditing] = useState<{ id: number; content: string; category: string } | null>(null);

  const load = async () => {
    const path = q ? `/api/memories?q=${encodeURIComponent(q)}` : `/api/memories${cat ? `?category=${cat}` : ""}`;
    try { setRows(await api<Memory[]>(path)); } catch (e) { j.toast(String(e), "error"); }
  };
  useEffect(() => { load(); }, [q, cat]); // eslint-disable-line

  const add = async () => {
    if (!draft.content.trim()) return;
    try { await api("/api/memories", { body: draft }); setDraft({ ...draft, content: "" }); load(); }
    catch (e) { j.toast(String(e), "error"); }
  };
  const save = async () => {
    if (!editing) return;
    try { await api(`/api/memories/${editing.id}`, { method: "PUT", body: { content: editing.content, category: editing.category } }); setEditing(null); load(); }
    catch (e) { j.toast(String(e), "error"); }
  };
  const del = async (id: number) => { await api(`/api/memories/${id}`, { method: "DELETE" }); load(); };
  const clear = async () => { if (confirm(j.t("confirm_clear"))) { await api("/api/memories", { method: "DELETE" }); load(); } };
  const mem = j.settings?.memory;

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className="space-y-4">
        <Card title={j.t("memory_title")}>
          {mem && <>
            <Toggle checked={mem.enabled} onChange={(v) => j.patchSettings({ memory: { enabled: v } })} label={j.t("memory_enabled")} />
            <Toggle checked={mem.save_conversations} onChange={(v) => j.patchSettings({ memory: { save_conversations: v } })} label={j.t("save_conv")} />
          </>}
          <p className="mt-2 text-xs text-muted">Passwords, card numbers, keys and similar secrets are refused automatically.</p>
          <Btn kind="danger" className="mt-3 w-full text-xs" onClick={clear}>{j.t("clear_all")}</Btn>
        </Card>
        <Card title={j.t("add")}>
          <div className="space-y-2">
            <Select value={draft.category} onChange={(v) => setDraft({ ...draft, category: v })} options={CATS.map((c) => [c, c])} />
            <textarea dir="auto" rows={3} value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })}
              className="w-full rounded-xl border border-line bg-panel-2/80 p-3 text-sm outline-none focus:border-cyan/60" />
            <Btn kind="primary" className="w-full" onClick={add}>{j.t("add")}</Btn>
          </div>
        </Card>
      </div>
      <Card title={`${rows.length}`} className="min-h-0 overflow-hidden" right={
        <div className="flex gap-2">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={j.t("search")} className="!py-1 w-48" />
          <Select value={cat} onChange={setCat} options={[["", j.t("all_categories")], ...CATS.map((c) => [c, c] as [string, string])]} />
        </div>}>
        <ul className="scroll-thin -m-4 max-h-[calc(100vh-170px)] space-y-2 overflow-y-auto p-4">
          {rows.length === 0 && <li className="text-sm text-muted">{j.t("empty")}</li>}
          {rows.map((r) => (
            <li key={r.id} className="rounded-xl border border-line bg-panel-2/40 p-3">
              {editing?.id === r.id ? (
                <div className="space-y-2">
                  <Select value={editing.category} onChange={(v) => setEditing({ ...editing, category: v })} options={CATS.map((c) => [c, c])} />
                  <textarea dir="auto" rows={3} value={editing.content} onChange={(e) => setEditing({ ...editing, content: e.target.value })}
                    className="w-full rounded-xl border border-line bg-panel-2/80 p-2 text-sm outline-none" />
                  <div className="flex gap-2"><Btn kind="primary" onClick={save}>{j.t("save")}</Btn><Btn onClick={() => setEditing(null)}>✕</Btn></div>
                </div>
              ) : (
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 rounded-md border border-violet/40 bg-violet/10 px-1.5 py-0.5 font-mono text-[10px] text-violet">{r.category}</span>
                  <p className="flex-1 text-sm" dir="auto">{r.content}</p>
                  <span className="font-mono text-[10px] text-muted">{r.source}</span>
                  <Btn className="!px-2 !py-1 text-xs" onClick={() => setEditing({ id: r.id, content: r.content, category: r.category })}>{j.t("edit")}</Btn>
                  <Btn kind="danger" className="!px-2 !py-1 text-xs" onClick={() => del(r.id)}>{j.t("delete")}</Btn>
                </div>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
