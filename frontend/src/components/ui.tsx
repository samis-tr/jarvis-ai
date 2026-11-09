import type { ReactNode } from "react";

export function Card({ title, children, className = "", right }: { title?: ReactNode; children: ReactNode; className?: string; right?: ReactNode }) {
  return (
    <section className={`glass rounded-2xl ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">{title}</h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Btn({ children, onClick, kind = "ghost", disabled, title, className = "", type = "button" }: {
  children: ReactNode; onClick?: () => void; kind?: "ghost" | "primary" | "danger" | "amber"; disabled?: boolean;
  title?: string; className?: string; type?: "button" | "submit";
}) {
  const styles = {
    ghost: "border-line bg-panel-2/60 text-ink hover:border-cyan/50 hover:text-cyan",
    primary: "border-cyan/60 bg-cyan/15 text-cyan hover:bg-cyan/25",
    danger: "border-danger/60 bg-danger/15 text-danger hover:bg-danger/25",
    amber: "border-amber/60 bg-amber/15 text-amber hover:bg-amber/25",
  }[kind];
  return (
    <button type={type} title={title} disabled={disabled} onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition
        disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-cyan ${styles} ${className}`}>
      {children}
    </button>
  );
}

export function Toggle({ checked, onChange, label, desc }: { checked: boolean; onChange: (v: boolean) => void; label: ReactNode; desc?: ReactNode }) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-2">
      <span>
        <span className="block text-sm">{label}</span>
        {desc && <span className="block text-xs text-muted">{desc}</span>}
      </span>
      <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
        className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full border transition ${checked ? "border-cyan/70 bg-cyan/30" : "border-line bg-panel-2"}`}>
        <span className={`absolute top-0.5 h-4.5 w-4.5 rounded-full transition-all ${checked ? "bg-cyan start-[22px]" : "bg-muted start-0.5"}`} />
      </button>
    </label>
  );
}

export function RiskBadge({ risk, t }: { risk: string; t: (k: any) => string }) {
  const c = risk === "high" ? "text-danger border-danger/50 bg-danger/10" : risk === "medium" ? "text-amber border-amber/50 bg-amber/10" : "text-ok border-ok/40 bg-ok/10";
  return <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${c}`}>{t(`risk_${risk}`)}</span>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`w-full rounded-xl border border-line bg-panel-2/80 px-3 py-2 text-sm outline-none placeholder:text-muted/70 focus:border-cyan/60 ${props.className ?? ""}`} />;
}

export function Select({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-line bg-panel-2/80 px-3 py-2 text-sm outline-none focus:border-cyan/60">
      {options.map(([v, l]) => <option key={v} value={v} className="bg-panel">{l}</option>)}
    </select>
  );
}

export const Icon = {
  home: <path d="M3 11l9-7 9 7v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z" />,
  tasks: <path d="M9 6h11M9 12h11M9 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2" />,
  memory: <path d="M12 3a5 5 0 00-5 5v1a4 4 0 00-2 7 4 4 0 007 3 4 4 0 007-3 4 4 0 00-2-7V8a5 5 0 00-5-5zM12 3v18" />,
  shield: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z M9 12l2 2 4-4" />,
  gear: <path d="M12 9a3 3 0 100 6 3 3 0 000-6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z" />,
  mic: <path d="M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3zM5 11a7 7 0 0014 0M12 18v3" />,
  micOff: <path d="M3 3l18 18M9 9v3a3 3 0 005 2.2M15 9.3V6a3 3 0 00-5.7-1.3M5 11a7 7 0 0011.2 5.6M19 11a7 7 0 01-.6 2.8M12 18v3" />,
  send: <path d="M4 12l16-8-6 16-2-7z" />,
  stop: <path d="M7 7h10v10H7z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  speaker: <path d="M4 9h4l5-4v14l-5-4H4zM16 9a4 4 0 010 6M18.5 6.5a8 8 0 010 11" />,
};

export function Svg({ d, className = "h-5 w-5" }: { d: ReactNode; className?: string }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>{d}</svg>;
}
