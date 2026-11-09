// Plays JARVIS's TTS audio and exposes live levels (TTS output + microphone) for the visualizer.
import { audioUrl } from "./api";

let ctx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let el: HTMLAudioElement | null = null;
const buf = new Uint8Array(256);
let micLevel = 0;
let micTs = 0;
const listeners = new Set<(speaking: boolean) => void>();

function ensure() {
  if (el) return;
  el = new Audio();
  el.crossOrigin = "anonymous";
  ctx = new AudioContext();
  const src = ctx.createMediaElementSource(el);
  analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  src.connect(analyser);
  analyser.connect(ctx.destination);
  el.onplay = () => listeners.forEach((l) => l(true));
  el.onended = el.onpause = () => listeners.forEach((l) => l(false));
}

export async function playTTS(id: string) {
  ensure();
  if (ctx!.state === "suspended") await ctx!.resume();
  el!.src = audioUrl(id);
  await el!.play();
}

export function stopSpeech() {
  if (el && !el.paused) { el.pause(); el.currentTime = 0; }
}

export const isSpeaking = () => !!el && !el.paused;
export function onSpeaking(fn: (s: boolean) => void) { listeners.add(fn); return () => { listeners.delete(fn); }; }

export function setMicLevel(level: number) { micLevel = level; micTs = performance.now(); }

/** 0..1 combined level: TTS output while speaking, otherwise the most recent mic level. */
export function currentLevel(): number {
  if (analyser && el && !el.paused) {
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
    return Math.min(1, Math.sqrt(sum / buf.length) * 4);
  }
  return performance.now() - micTs < 250 ? micLevel : 0;
}
