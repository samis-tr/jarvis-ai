import type { Jarvis } from "../useJarvis";
import { Card } from "./ui";

function Bar({ label, value, sub, invert }: { label: string; value: number | null | undefined; sub?: string; invert?: boolean }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const load = invert ? 100 - v : v;
  const color = load > 85 ? "bg-danger" : load > 65 ? "bg-amber" : "bg-cyan";
  return (
    <div>
      <div className="flex justify-between font-mono text-[11px]" dir="ltr">
        <span className="text-muted">{label}</span>
        <span>{value == null ? "–" : `${Math.round(v)}%`} {sub && <span className="text-muted">{sub}</span>}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-line" dir="ltr">
        <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

export default function SystemGauges({ j }: { j: Jarvis }) {
  const s = j.sys;
  const gpu = s?.gpus?.[0];
  return (
    <Card title={j.t("system")}>
      <div className="space-y-3">
        <Bar label="CPU" value={s?.cpu_percent} />
        <Bar label="RAM" value={s?.ram_percent} sub={s ? `${s.ram_used_gb}/${s.ram_total_gb} GB` : ""} />
        {gpu && <Bar label={`GPU · ${gpu.temp_c}°C`} value={gpu.util_percent} />}
        {gpu && <Bar label="VRAM" value={(gpu.mem_used_mb / gpu.mem_total_mb) * 100} sub={`${(gpu.mem_used_mb / 1024).toFixed(1)}/${(gpu.mem_total_mb / 1024).toFixed(0)} GB`} />}
        {s?.battery_percent != null && <Bar label={`BAT${s.plugged_in ? " ⚡" : ""}`} value={s.battery_percent} invert />}
      </div>
    </Card>
  );
}
