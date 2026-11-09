// Minimal, safe Markdown renderer (no raw HTML is ever injected - content may originate from web pages).
import { Fragment, type ReactNode } from "react";
import { api } from "../api";

function openExternal(url: string) {
  api("/api/open_url", { body: { url } }).catch(() => {});
}

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\((https?:\/\/[^)\s]+)\)|https?:\/\/[^\s)]+)/g;
  let last = 0, m: RegExpExecArray | null, i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const k = `${key}-${i++}`;
    if (tok.startsWith("**")) out.push(<strong key={k}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={k}>{tok.slice(1, -1)}</code>);
    else if (tok.startsWith("[")) {
      const label = tok.slice(1, tok.indexOf("]"));
      out.push(<a key={k} href={m[2]} onClick={(e) => { e.preventDefault(); openExternal(m![2]); }}>{label}</a>);
    } else out.push(<a key={k} href={tok} dir="ltr" onClick={(e) => { e.preventDefault(); openExternal(tok); }}>{tok}</a>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let code: string[] | null = null;
  const flush = () => {
    if (list) {
      const L = list.ordered ? "ol" : "ul";
      blocks.push(<L key={`l${blocks.length}`}>{list.items.map((it, j) => <li key={j}>{inline(it, `li${j}`)}</li>)}</L>);
      list = null;
    }
  };
  lines.forEach((ln, idx) => {
    if (ln.trim().startsWith("```")) {
      if (code) { blocks.push(<pre key={`c${idx}`} className="overflow-x-auto rounded-lg bg-[#0b1322] p-3 text-xs" dir="ltr"><code>{code.join("\n")}</code></pre>); code = null; }
      else { flush(); code = []; }
      return;
    }
    if (code) { code.push(ln); return; }
    const h = ln.match(/^(#{1,3})\s+(.*)/);
    const ul = ln.match(/^\s*[-*•]\s+(.*)/);
    const ol = ln.match(/^\s*\d+[.)]\s+(.*)/);
    if (h) { flush(); const H = (`h${h[1].length}`) as "h1"; blocks.push(<H key={idx}>{inline(h[2], `h${idx}`)}</H>); }
    else if (ul || ol) {
      const ordered = !!ol;
      if (!list || list.ordered !== ordered) { flush(); list = { ordered, items: [] }; }
      list.items.push((ul || ol)![1]);
    } else if (!ln.trim()) flush();
    else { flush(); blocks.push(<p key={idx}>{inline(ln, `p${idx}`)}</p>); }
  });
  flush();
  return <div className="md leading-relaxed">{blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>)}</div>;
}
