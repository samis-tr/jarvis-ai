import { useState } from "react";
import type { Jarvis } from "../useJarvis";
import { Btn, Card, Input, RiskBadge, Toggle } from "./ui";

export default function PermissionsView({ j }: { j: Jarvis }) {
  const sec = j.settings?.security;
  const [dir, setDir] = useState("");
  if (!sec || !j.boot) return null;
  const set = (patch: Partial<typeof sec>) => j.patchSettings({ security: patch }).catch((e) => j.toast(String(e), "error"));
  const toggleIn = (list: string[], item: string, on: boolean) => on ? [...new Set([...list, item])] : list.filter((x) => x !== item);

  return (
    <div className="scroll-thin grid h-full min-h-0 gap-4 overflow-y-auto lg:grid-cols-2">
      <div className="space-y-4">
        <Card title={j.t("perms_title")}>
          <Toggle checked={sec.safe_mode} onChange={(v) => set({ safe_mode: v })} label={j.t("safe_mode")} desc={j.t("safe_mode_desc")} />
          <div className="mt-3 rounded-xl border border-line bg-panel-2/40 p-3 text-xs leading-relaxed text-muted">
            <p><RiskBadge risk="low" t={j.t} /> reading approved files, web search, opening apps — runs directly.</p>
            <p className="mt-1.5"><RiskBadge risk="medium" t={j.t} /> creating/editing files, closing apps, screenshots, saving memories — asks unless pre-authorized inside approved folders.</p>
            <p className="mt-1.5"><RiskBadge risk="high" t={j.t} /> deleting (Recycle Bin), overwriting files — always asks. Blocked in safe mode.</p>
            <p className="mt-1.5">After JARVIS reads a web page or file, every further change in that task requires your approval (prompt-injection protection). There is no arbitrary shell, install, payment or messaging tool.</p>
          </div>
        </Card>
        <Card title={j.t("approved_dirs")}>
          <ul className="space-y-1.5">
            {sec.approved_dirs.map((d, i) => (
              <li key={d} className="flex items-center gap-2 rounded-lg border border-line bg-panel-2/40 px-3 py-1.5">
                <span className="flex-1 truncate font-mono text-xs" dir="ltr">{d}</span>
                {i === 0 && <span className="text-[10px] text-cyan">workspace</span>}
                <Btn kind="danger" className="!px-2 !py-0.5 text-xs" disabled={sec.approved_dirs.length === 1}
                  onClick={() => set({ approved_dirs: sec.approved_dirs.filter((x) => x !== d) })}>✕</Btn>
              </li>
            ))}
          </ul>
          <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (dir.trim()) { set({ approved_dirs: [...sec.approved_dirs, dir.trim()] }); setDir(""); } }}>
            <Input dir="ltr" value={dir} onChange={(e) => setDir(e.target.value)} placeholder={j.t("add_dir")} />
            <Btn kind="primary" type="submit">{j.t("add")}</Btn>
          </form>
          <p className="mt-2 text-xs text-muted">Windows, Program Files, AppData and .ssh are always protected; files like .env, keys and password databases are never read.</p>
        </Card>
      </div>
      <Card title={j.t("tools")}>
        <ul className="divide-y divide-line">
          {j.boot.tools.map((tool) => {
            const enabled = !sec.disabled_tools.includes(tool.name);
            const auto = sec.auto_approve_medium.includes(tool.name);
            return (
              <li key={tool.name} className="py-2.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm" dir="ltr">{tool.name}</span>
                  <RiskBadge risk={tool.risk} t={j.t} />
                  <span className="flex-1" />
                  <Toggle checked={enabled} onChange={(v) => set({ disabled_tools: toggleIn(sec.disabled_tools, tool.name, !v) })} label="" />
                </div>
                <p className="text-xs text-muted" dir="ltr">{tool.description}</p>
                {tool.risk === "medium" && enabled && (
                  <label className="mt-1 flex items-center gap-2 text-xs text-ink/80">
                    <input type="checkbox" checked={auto} className="accent-cyan"
                      onChange={(e) => set({ auto_approve_medium: toggleIn(sec.auto_approve_medium, tool.name, e.target.checked) })} />
                    {j.t("auto_medium")}
                  </label>
                )}
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
