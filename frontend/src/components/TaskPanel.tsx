import { useState } from "react";
import { api } from "../api";
import type { Jarvis } from "../useJarvis";
import type { Step, Task } from "../types";
import { Btn, Card, RiskBadge } from "./ui";

const STATES = ["PLANNING", "WAITING_FOR_APPROVAL", "EXECUTING", "VERIFYING"] as const;

function StatusDot({ s }: { s: string }) {
  const c: Record<string, string> = {
    done: "bg-ok", failed: "bg-danger", denied: "bg-danger/70", running: "bg-cyan animate-pulse",
    awaiting_approval: "bg-amber animate-pulse", approved: "bg-cyan", skipped: "bg-muted", pending: "bg-muted",
  };
  return <span className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${c[s] ?? "bg-muted"}`} />;
}

function ApprovalCard({ task, step, j }: { task: Task; step: Step; j: Jarvis }) {
  const [busy, setBusy] = useState(false);
  const decide = async (decision: string) => {
    setBusy(true);
    try { await api(`/api/tasks/${task.id}/approval`, { body: { step_id: step.id, decision } }); }
    catch (e) { j.toast(String(e), "error"); }
    finally { setBusy(false); }
  };
  return (
    <div className={`rise rounded-xl border p-3 ${step.risk === "high" ? "border-danger/60 bg-danger/5" : "glow-amber border-amber/60 bg-amber/5"}`}>
      <div className="mb-1 flex items-center gap-2">
        <span className="text-xs font-semibold text-amber">{j.t("approval_needed")}</span>
        <RiskBadge risk={step.risk} t={j.t} />
      </div>
      <p className="text-sm" dir="auto">{step.summary}</p>
      <p className="mt-1 font-mono text-[11px] text-muted" dir="ltr">{step.tool} · {step.reason}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Btn kind="primary" disabled={busy} onClick={() => decide("approve")}>{j.t("approve")}</Btn>
        {step.risk !== "high" && <Btn disabled={busy} onClick={() => decide("approve_for_task")}>{j.t("approve_task")}</Btn>}
        <Btn kind="danger" disabled={busy} onClick={() => decide("deny")}>{j.t("deny")}</Btn>
      </div>
    </div>
  );
}

export default function TaskPanel({ j }: { j: Jarvis }) {
  const task = j.activeTask;
  if (!task || !task.plan.length) {
    return <Card title={j.t("current_task")}><p className="text-sm text-muted">{j.t("no_task")}</p></Card>;
  }
  const live = !["COMPLETED", "FAILED", "CANCELLED"].includes(task.state);
  const doneCount = task.plan.filter((s) => ["done", "failed", "denied", "skipped"].includes(s.status)).length;
  const pct = Math.round((doneCount / task.plan.length) * 100);
  const stateColor = task.state === "COMPLETED" ? "text-ok" : task.state === "FAILED" ? "text-danger" : task.state === "CANCELLED" ? "text-muted" : task.state === "WAITING_FOR_APPROVAL" ? "text-amber" : "text-cyan";
  return (
    <Card title={j.t("current_task")} right={live && <Btn kind="danger" className="!px-2 !py-1 text-xs" onClick={() => api(`/api/tasks/${task.id}/cancel`, { body: {} })}>{j.t("cancel_task")}</Btn>}>
      <p className="line-clamp-2 text-sm" dir="auto">{task.request}</p>
      <div className="mt-3 flex items-center gap-1.5" dir="ltr">
        {STATES.map((s) => {
          const idx = STATES.indexOf(s), cur = STATES.indexOf(task.state as any);
          const on = !live || idx <= cur;
          return <div key={s} title={s} className={`h-1 flex-1 rounded-full ${on ? (task.state === "FAILED" ? "bg-danger" : "bg-cyan") : "bg-line"}`} />;
        })}
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[11px]" dir="ltr">
        <span className={stateColor}>{task.state}</span>
        <span className="text-muted">{doneCount}/{task.plan.length} · {pct}%</span>
      </div>
      <ol className="mt-3 space-y-2">
        {task.plan.map((s) => (
          <li key={s.id} className="space-y-2">
            {s.status === "awaiting_approval" ? <ApprovalCard task={task} step={s} j={j} /> : (
              <div className="flex gap-2.5 rounded-lg border border-line/70 bg-panel-2/40 p-2.5">
                <StatusDot s={s.status} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm" dir="auto">{s.summary || s.tool}</span>
                    <RiskBadge risk={s.risk} t={j.t} />
                  </div>
                  <div className="font-mono text-[11px] text-muted" dir="ltr">
                    {s.tool} · {s.status}{s.duration_ms ? ` · ${s.duration_ms} ms` : ""}
                    {s.verified === true && <span className="text-ok"> · ✓ {j.t("verified")}</span>}
                    {s.verified === false && <span className="text-danger"> · ✗ {j.t("unverified")}</span>}
                  </div>
                  {s.output && <pre className="mt-1 max-h-28 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-ink/70 scroll-thin" dir="auto">{s.output}</pre>}
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
      {task.usage?.cost_usd !== undefined && <p className="mt-2 font-mono text-[11px] text-amber" dir="ltr">≈ ${task.usage.cost_usd.toFixed(4)} · {task.usage.input_tokens}+{task.usage.output_tokens} {j.t("tokens")}</p>}
    </Card>
  );
}
