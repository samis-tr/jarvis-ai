import { useEffect, useRef } from "react";
import { currentLevel } from "../audio";
import type { Phase } from "../types";

// Colors per real assistant phase (driven by backend status + actual audio levels).
const PALETTE: Record<Phase, [number, number, number][]> = {
  idle: [[34, 227, 255], [80, 120, 255]],
  listening: [[34, 227, 255], [140, 255, 240]],
  transcribing: [[120, 200, 255], [155, 123, 255]],
  thinking: [[155, 123, 255], [34, 227, 255]],
  executing: [[34, 227, 255], [155, 123, 255]],
  waiting_approval: [[255, 181, 71], [255, 120, 80]],
  speaking: [[34, 227, 255], [200, 160, 255]],
};

export default function Orb({ phase, size = 360 }: { phase: Phase; size?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  useEffect(() => {
    const cv = ref.current!;
    const g = cv.getContext("2d")!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = size * dpr; cv.height = size * dpr;
    g.scale(dpr, dpr);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0, t = 0, level = 0;
    const cx = size / 2, cy = size / 2, R = size * 0.27;
    const N = 160;
    const draw = () => {
      const ph = phaseRef.current;
      const [c1, c2] = PALETTE[ph];
      const target = currentLevel();
      level += (target - level) * 0.25;
      const speed = ph === "thinking" || ph === "executing" ? 2.2 : ph === "idle" ? 0.5 : 1.2;
      t += (reduce ? 0.2 : 1) * 0.012 * speed;
      g.clearRect(0, 0, size, size);

      // ambient glow
      const pulse = ph === "waiting_approval" ? 0.5 + 0.5 * Math.sin(t * 4) : 0.6 + level * 0.8;
      const glow = g.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 1.9);
      glow.addColorStop(0, `rgba(${c1},${0.28 * pulse})`);
      glow.addColorStop(0.5, `rgba(${c2},${0.10 * pulse})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = glow;
      g.fillRect(0, 0, size, size);

      // core sphere
      const core = g.createRadialGradient(cx - R * 0.3, cy - R * 0.35, R * 0.05, cx, cy, R);
      core.addColorStop(0, `rgba(${c1},0.55)`);
      core.addColorStop(0.55, `rgba(${c2},0.18)`);
      core.addColorStop(1, "rgba(8,14,30,0.9)");
      g.beginPath(); g.arc(cx, cy, R * (0.92 + level * 0.08), 0, Math.PI * 2); g.fillStyle = core; g.fill();

      // audio-reactive waveform ring
      for (let ring = 0; ring < 3; ring++) {
        g.beginPath();
        for (let i = 0; i <= N; i++) {
          const a = (i / N) * Math.PI * 2;
          const wob = Math.sin(a * (3 + ring) + t * (2 + ring)) * 0.5 + Math.sin(a * 7 - t * 3) * 0.5;
          const amp = (ph === "idle" ? 2 : 4) + level * (ph === "listening" || ph === "speaking" ? 34 : 14);
          const r = R * (1.08 + ring * 0.1) + wob * amp * (1 - ring * 0.25);
          const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
          i ? g.lineTo(x, y) : g.moveTo(x, y);
        }
        const col = ring === 1 ? c2 : c1;
        g.strokeStyle = `rgba(${col},${0.55 - ring * 0.14})`;
        g.lineWidth = 1.6 - ring * 0.4;
        g.shadowColor = `rgba(${col},0.8)`; g.shadowBlur = 12;
        g.stroke();
      }
      g.shadowBlur = 0;

      // orbiting arcs (spin faster while thinking / executing)
      for (let k = 0; k < 3; k++) {
        const rr = R * (1.55 + k * 0.13);
        const start = t * (k % 2 ? -1 : 1) * (1 + k * 0.4) + k;
        g.beginPath();
        g.arc(cx, cy, rr, start, start + (ph === "thinking" || ph === "executing" ? 1.6 : 0.7));
        g.strokeStyle = `rgba(${k === 1 ? c2 : c1},${0.35 - k * 0.07})`;
        g.lineWidth = 2; g.lineCap = "round"; g.stroke();
      }

      // tick marks
      g.save(); g.translate(cx, cy); g.rotate(t * 0.15);
      for (let i = 0; i < 72; i++) {
        g.rotate((Math.PI * 2) / 72);
        g.fillStyle = `rgba(${c1},${i % 6 ? 0.12 : 0.4})`;
        g.fillRect(R * 1.95, -0.5, i % 6 ? 4 : 8, 1);
      }
      g.restore();
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [size]);

  return <canvas ref={ref} style={{ width: size, height: size }} aria-hidden className="pointer-events-none select-none" />;
}
