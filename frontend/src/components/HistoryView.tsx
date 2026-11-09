import { useEffect, useState } from "react";
import { api } from "../api";
import type { Jarvis } from "../useJarvis";
import { Btn, Card, RiskBadge } from "./ui";

interface StoredTask {
  id: string; conversation_id: string; request: string; state: string; result: string; error: string; created: number;
  actions: { id: number; tool: string; args: Record<string, unknown>; risk: string; decision: string; status: string; output: string; verified: number | null; created: number; duration_ms: number }[];
}

export default function HistoryView({ j }: { j: Jarvis }) {
  const [tasks, setTasks] = useState<StoredTask[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const load = () => api<StoredTask[]>("/api/tasks?limit=100").then(setTasks).catch((e) => j.toast(String(e), "error"));
  useEffect(() => { load(); }, [Object.keys(j.tasks).length]); // eslint-disable-line

  const color = (s: string) => s === "COMPLETED" ? "text-ok" : s === "FAILED" ? "text-danger" : s === "CANCELLED" ? "text-muted" : "text-cyan";
  return (
    <Card title={j.t("tasks_title")} className="h-full overflow-hidden" right={<Btn className="!py-1 text-xs" onClick={load}>↻</Btn>}>
      <div className="scroll-thin -m-4 max-h-[calc(100vh-150px)] overflow-y-auto p-4">
        {tasks.length === 0 && <p className="text-sm text-muted">{j.t("empty")}</p>}
        <ul className="space-y-2">
          {tasks.map((t) => (
            <li key={t.id} className="rounded-xl border border-line bg-panel-2/40">
              <button className="flex w-full items-center gap-3 p-3 text-start" onClick={() => setOpen(open === t.id ? null : t.id)}>
                <span className={`w-28 shrink-0 font-mono text-[11px] ${color(t.state)}`} dir="ltr">{t.state}</span>
                <span className="flex-1 truncate text-sm" dir="auto">{t.request}</span>
                <span className="shrink-0 font-mono text-[11px] text-muted" dir="ltr">{new Date(t.created * 1000).toLocaleString()}</span>
              </button>
              {open === t.id && (
                <div className="space-y-2 border-t border-line p-3">
                  {t.result && <p className="whitespace-pre-wrap text-sm text-ink/80" dir="auto">{t.result.slice(0, 1200)}</p>}
                  {t.error && <p className="text-xs text-danger">{t.error}</p>}
                  <table className="w-full text-start font-mono text-[11px]" dir="ltr">
                    <thead className="text-muted"><tr><th className="text-left">tool</th><th className="text-left">risk</th><th className="text-left">decision</th><th className="text-left">status</th><th className="text-left">verified</th><th className="text-left">ms</th></tr></thead>
                    <tbody>
                      {t.actions.map((a) => (
                        <tr key={a.id} className="border-t border-line/50 align-top" title={a.output}>
                          <td className="py-1 pe-2">{a.tool}<div className="max-w-xs truncate text-muted">{JSON.stringify(a.args)}</div></td>
                          <td><RiskBadge risk={a.risk} t={j.t} /></td>
                          <td>{a.decision}</td><td>{a.status}</td>
                          <td>{a.verified === null ? "–" : a.verified ? "✓" : "✗"}</td><td>{a.duration_ms}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <Btn className="text-xs" onClick={() => j.openConversation(t.conversation_id)}>{j.t("open")} →</Btn>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
