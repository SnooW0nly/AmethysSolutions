"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { motion, AnimatePresence, useScroll, useSpring } from "framer-motion";

// ── Types ─────────────────────────────────────────────────────────────────────
interface NotebookModule {
  id: string;
  badge: string;
  title: string;
  description: string;
  features: string[];
}

interface Notebook3DProps {
  modules: NotebookModule[];
}

// ── Accent colors ─────────────────────────────────────────────────────────────
const ACCENT: Record<string, string> = {
  automations:  "#8b5cf6",
  cloud:        "#38bdf8",
  customization:"#f472b6",
  giveaways:    "#fbbf24",
  loja:         "#34d399",
  messages:     "#60a5fa",
  protection:   "#f87171",
  rendimentos:  "#2dd4bf",
  settings:     "#fb923c",
  tickets:      "#818cf8",
  economia:     "#fde047",
};

// ── Canvas drawing helpers ────────────────────────────────────────────────────

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string, x: number, y: number,
  maxW: number, lineH: number
): number {
  const words = text.split(" ");
  let line = "";
  let cy = y;
  for (const w of words) {
    const test = line + w + " ";
    if (line && ctx.measureText(test).width > maxW) {
      ctx.fillText(line.trim(), x, cy);
      line = w + " ";
      cy += lineH;
    } else { line = test; }
  }
  if (line.trim()) ctx.fillText(line.trim(), x, cy);
  return cy + lineH;
}

function paperBase(ctx: CanvasRenderingContext2D, W: number, H: number) {
  // Gradiente de papel com leve variação de tom
  const bg = ctx.createLinearGradient(0, 0, W * 0.4, H);
  bg.addColorStop(0,    "#fefdf9");
  bg.addColorStop(0.35, "#faf6ee");
  bg.addColorStop(1,    "#f0e9dc");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Grain de papel — ruído sutil
  const imageData = ctx.getImageData(0, 0, W, H);
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    const noise = (Math.random() - 0.5) * 9;
    data[i]   = Math.max(0, Math.min(255, data[i]   + noise));
    data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise * 0.9));
    data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise * 0.7));
  }
  ctx.putImageData(imageData, 0, 0);

  // Vinheta lateral suave (a página recebe menos luz perto das bordas)
  const vigL = ctx.createLinearGradient(0, 0, 90, 0);
  vigL.addColorStop(0, "rgba(0,0,0,0.09)");
  vigL.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = vigL; ctx.fillRect(0, 0, 90, H);

  const vigR = ctx.createLinearGradient(W, 0, W - 90, 0);
  vigR.addColorStop(0, "rgba(0,0,0,0.07)");
  vigR.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = vigR; ctx.fillRect(W - 90, 0, 90, H);

  const vigT = ctx.createLinearGradient(0, 0, 0, 70);
  vigT.addColorStop(0, "rgba(0,0,0,0.08)"); vigT.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = vigT; ctx.fillRect(0, 0, W, 70);

  const vigB = ctx.createLinearGradient(0, H, 0, H - 70);
  vigB.addColorStop(0, "rgba(0,0,0,0.06)"); vigB.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = vigB; ctx.fillRect(0, H - 70, W, 70);

  // Linhas pautadas — mais sutis, com leve variação de opacidade
  for (let y = 144; y < H - 60; y += 42) {
    const alpha = 0.28 + Math.random() * 0.06;
    ctx.strokeStyle = `rgba(140,175,220,${alpha})`;
    ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(60, y); ctx.lineTo(W - 60, y); ctx.stroke();
  }
}

function spiralHoles(
  ctx: CanvasRenderingContext2D, W: number, H: number, side: "L" | "R"
) {
  const x = side === "L" ? 42 : W - 42;
  for (let y = 84; y < H - 60; y += 76) {
    ctx.fillStyle = "#cdc4b8";
    ctx.beginPath(); ctx.arc(x, y, 13, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#f2ece3";
    ctx.beginPath(); ctx.arc(x, y, 7.5, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "#aaa098";
    ctx.lineWidth = 1.3;
    ctx.beginPath(); ctx.arc(x, y, 10, -0.6, 0.6); ctx.stroke();
  }
}

function marginLine(
  ctx: CanvasRenderingContext2D, W: number, H: number, side: "L" | "R"
) {
  const x = side === "L" ? 152 : W - 152;
  ctx.strokeStyle = "#ffb3b855";
  ctx.lineWidth = 1.8;
  ctx.beginPath(); ctx.moveTo(x, 56); ctx.lineTo(x, H - 56); ctx.stroke();
}

// Cover texture — couro escuro premium com embossing e reflexo sutil
function makeCoverTex(): THREE.CanvasTexture {
  const W = 1024, H = 1408; // resolução maior = mais nitidez
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d")!;

  // Base: gradiente de couro escuro com profundidade
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0,    "#1e1838");
  bg.addColorStop(0.28, "#160e2c");
  bg.addColorStop(0.65, "#0f0b20");
  bg.addColorStop(1,    "#09071a");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

  // Grain de couro — ruído fino para simular textura
  const imageData = ctx.getImageData(0, 0, W, H);
  const d = imageData.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = (Math.random() - 0.5) * 14;
    d[i]   = Math.max(0, Math.min(255, d[i]   + n));
    d[i+1] = Math.max(0, Math.min(255, d[i+1] + n * 0.8));
    d[i+2] = Math.max(0, Math.min(255, d[i+2] + n * 1.1));
  }
  ctx.putImageData(imageData, 0, 0);

  // Grid sutil — linhas muito finas de "diário"
  ctx.strokeStyle = "rgba(139,92,246,0.06)"; ctx.lineWidth = 0.8;
  for (let x = 0; x < W; x += 48) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y < H; y += 48) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // Glow central — aura roxa dramática
  const g1 = ctx.createRadialGradient(W/2, H*0.48, 0, W/2, H*0.48, 420);
  g1.addColorStop(0,   "rgba(124,58,237,0.38)");
  g1.addColorStop(0.5, "rgba(109,40,217,0.14)");
  g1.addColorStop(1,   "rgba(0,0,0,0)");
  ctx.fillStyle = g1; ctx.fillRect(0, 0, W, H);

  // Highlight de "reflexo de couro" — diagonal sutil no canto superior esquerdo
  const hl = ctx.createLinearGradient(0, 0, W*0.55, H*0.3);
  hl.addColorStop(0,    "rgba(255,255,255,0.07)");
  hl.addColorStop(0.4,  "rgba(255,255,255,0.025)");
  hl.addColorStop(1,    "rgba(255,255,255,0)");
  ctx.fillStyle = hl; ctx.fillRect(0, 0, W, H);

  // Vinheta perimetral — profundidade / queimado nas bordas
  const vg = ctx.createRadialGradient(W/2, H/2, H*0.22, W/2, H/2, H*0.7);
  vg.addColorStop(0, "rgba(0,0,0,0)");
  vg.addColorStop(1, "rgba(0,0,0,0.68)");
  ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);

  // Borda interna dourada fina (estilo livro encadernado)
  const pad = 38;
  ctx.strokeStyle = "rgba(139,92,246,0.30)"; ctx.lineWidth = 1.5;
  ctx.strokeRect(pad, pad, W - pad*2, H - pad*2);
  ctx.strokeStyle = "rgba(139,92,246,0.12)"; ctx.lineWidth = 0.8;
  ctx.strokeRect(pad+6, pad+6, W - (pad+6)*2, H - (pad+6)*2);

  // Regras horizontais decorativas
  const rule = ctx.createLinearGradient(0, 0, W, 0);
  rule.addColorStop(0,   "rgba(0,0,0,0)");
  rule.addColorStop(0.18,"rgba(139,92,246,0.70)");
  rule.addColorStop(0.5, "rgba(167,139,250,0.90)");
  rule.addColorStop(0.82,"rgba(139,92,246,0.70)");
  rule.addColorStop(1,   "rgba(0,0,0,0)");
  ctx.strokeStyle = rule; ctx.lineWidth = 1.8;
  ctx.beginPath(); ctx.moveTo(0, H*0.44); ctx.lineTo(W, H*0.44); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, H*0.58); ctx.lineTo(W, H*0.58); ctx.stroke();

  // Letra decorativa de fundo — watermark
  ctx.save();
  ctx.globalAlpha = 0.04;
  ctx.fillStyle = "#a78bfa";
  ctx.font = `bold ${Math.round(H*0.32)}px 'Times New Roman', Georgia, serif`;
  ctx.textAlign = "center";
  ctx.fillText("A", W/2, H*0.62);
  ctx.restore();

  // Título principal — embossed effect (sombra + texto)
  ctx.textAlign = "center";
  ctx.shadowColor = "rgba(0,0,0,0.9)"; ctx.shadowBlur = 18; ctx.shadowOffsetY = 4;
  ctx.fillStyle = "#c4b5fd";
  ctx.font = `bold ${Math.round(W*0.092)}px 'Times New Roman', Georgia, serif`;
  // Simula letter-spacing manualmente
  const title = "AMETHYS";
  const spacing = W * 0.016;
  const totalW = title.length * (ctx.measureText("M").width + spacing) - spacing;
  let tx = W/2 - totalW/2;
  for (const ch of title) {
    const cw = ctx.measureText(ch).width;
    ctx.fillText(ch, tx + cw/2, H*0.495);
    tx += cw + spacing;
  }
  ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;

  // Subtítulo
  ctx.fillStyle = "rgba(167,139,250,0.75)";
  ctx.font = `italic ${Math.round(W*0.038)}px 'Times New Roman', Georgia, serif`;
  ctx.fillText("módulos & funcionalidades", W/2, H*0.538);

  // Dica de scroll
  ctx.fillStyle = "rgba(255,255,255,0.12)";
  ctx.font = `${Math.round(W*0.022)}px 'Courier New', monospace`;
  ctx.fillText("↓  ROLE PARA EXPLORAR  ↓", W/2, H*0.60);

  return new THREE.CanvasTexture(c);
}

// Right page: module content
function makeRightPageTex(mod: NotebookModule, idx: number, total: number): THREE.CanvasTexture {
  const W = 768, H = 1056;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d")!;

  paperBase(ctx, W, H);
  marginLine(ctx, W, H, "L");
  spiralHoles(ctx, W, H, "L");

  const accent = ACCENT[mod.id] ?? "#8b5cf6";
  const ML = 182;

  // Page counter
  ctx.fillStyle = "#8878a8";
  ctx.font = "bold 18px 'Courier New', monospace";
  ctx.textAlign = "right";
  ctx.letterSpacing = "1px";
  ctx.fillText(`${String(idx + 1).padStart(2, "0")} / ${String(total).padStart(2, "0")}`, W - 72, 60);
  ctx.letterSpacing = "0px";

  // Badge pill
  ctx.textAlign = "left";
  ctx.font = "bold 22px 'Courier New', monospace";
  ctx.letterSpacing = "2px";
  const bw = ctx.measureText(mod.badge.toUpperCase()).width + 52;
  ctx.fillStyle = accent + "33";
  ctx.beginPath();
  const br = 24;
  ctx.moveTo(ML + br, 74); ctx.lineTo(ML + bw - br, 74);
  ctx.arcTo(ML + bw, 74, ML + bw, 74 + br, br);
  ctx.lineTo(ML + bw, 74 + 48 - br);
  ctx.arcTo(ML + bw, 74 + 48, ML + bw - br, 74 + 48, br);
  ctx.lineTo(ML + br, 74 + 48);
  ctx.arcTo(ML, 74 + 48, ML, 74 + 48 - br, br);
  ctx.lineTo(ML, 74 + br);
  ctx.arcTo(ML, 74, ML + br, 74, br);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = accent + "88"; ctx.lineWidth = 1.8;
  ctx.stroke();
  ctx.fillStyle = accent;
  ctx.fillText(mod.badge.toUpperCase(), ML + 20, 108);
  ctx.letterSpacing = "0px";

  // Title
  ctx.fillStyle = "#0f0c1e";
  ctx.font = "bold 62px 'Times New Roman', Georgia, serif";
  let ny = wrapText(ctx, mod.title, ML, 208, W - ML - 78, 72);

  // Accent divider
  const grad = ctx.createLinearGradient(ML, 0, ML + 260, 0);
  grad.addColorStop(0, accent); grad.addColorStop(1, accent + "00");
  ctx.strokeStyle = grad; ctx.lineWidth = 4; ctx.lineCap = "round";
  ctx.beginPath(); ctx.moveTo(ML, ny + 4); ctx.lineTo(ML + 260, ny + 4); ctx.stroke();
  ny += 48;

  // Description
  ctx.fillStyle = "#3a2e58";
  ctx.font = "24px Georgia, serif";
  ny = wrapText(ctx, mod.description, ML, ny, W - ML - 88, 38);
  ny += 26;

  // Features heading
  ctx.fillStyle = "#7060a0";
  ctx.font = "bold 17px 'Courier New', monospace";
  ctx.letterSpacing = "3px";
  ctx.fillText("DESTAQUES", ML, ny);
  ctx.letterSpacing = "0px";
  ny += 38;

  // Feature items
  for (const feat of mod.features) {
    ctx.fillStyle = accent;
    ctx.beginPath(); ctx.arc(ML + 8, ny - 9, 5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#1a1030";
    ctx.font = "bold 22px Georgia, serif";
    ctx.fillText(feat, ML + 26, ny);
    ny += 40;
  }

  // Footer id
  ctx.fillStyle = "#8070aa";
  ctx.font = "bold 15px 'Courier New', monospace";
  ctx.letterSpacing = "2px";
  ctx.fillText(mod.id.toUpperCase(), ML, H - 48);
  ctx.letterSpacing = "0px";

  return new THREE.CanvasTexture(c);
}

// Left page: notes / decorative
function makeLeftPageTex(idx: number, total: number, prevMod: NotebookModule | null): THREE.CanvasTexture {
  const W = 768, H = 1056;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d")!;

  paperBase(ctx, W, H);
  marginLine(ctx, W, H, "R");
  spiralHoles(ctx, W, H, "R");

  const ML2 = 90;
  const MR2 = W - 182;

  // Page counter
  ctx.fillStyle = "#8878a8";
  ctx.font = "bold 18px 'Courier New', monospace";
  ctx.textAlign = "left";
  ctx.letterSpacing = "1px";
  ctx.fillText(`${String(idx).padStart(2, "0")} / ${String(total).padStart(2, "0")}`, 72, 60);
  ctx.letterSpacing = "0px";

  // "NOTAS" heading
  ctx.fillStyle = "#7060a0";
  ctx.font = "bold 17px 'Courier New', monospace";
  ctx.textAlign = "right";
  ctx.letterSpacing = "4px";
  ctx.fillText("NOTAS", MR2, 112);
  ctx.letterSpacing = "0px";

  if (prevMod) {
    const acc = ACCENT[prevMod.id] ?? "#8b5cf6";

    // Continuation label
    ctx.fillStyle = acc + "cc";
    ctx.font = "bold 14px 'Courier New', monospace";
    ctx.textAlign = "left";
    ctx.letterSpacing = "2px";
    ctx.fillText("↳  CONTINUAÇÃO", ML2, 148);
    ctx.letterSpacing = "0px";

    // Prev module title
    ctx.fillStyle = acc;
    ctx.font = "italic bold 30px 'Times New Roman', Georgia, serif";
    ctx.fillText(prevMod.title, ML2, 198);

    // Divider
    const dg = ctx.createLinearGradient(ML2, 0, ML2 + 240, 0);
    dg.addColorStop(0, acc); dg.addColorStop(1, acc + "00");
    ctx.strokeStyle = dg; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(ML2, 214); ctx.lineTo(ML2 + 240, 214); ctx.stroke();

    // Continuation of description (truncated for space)
    const descWords = prevMod.description.split(" ");
    const descShort = descWords.slice(0, 18).join(" ") + (descWords.length > 18 ? "..." : "");
    let cy = 256;
    ctx.font = "italic 21px Georgia, serif";
    ctx.fillStyle = "#3a2e58";
    cy = wrapText(ctx, descShort, ML2, cy, MR2 - ML2, 34);
    cy += 10;

    // Note continuation line
    ctx.fillStyle = "#4a3870";
    ctx.font = "italic 20px Georgia, serif";
    ctx.fillText("— ver módulo anterior para detalhes.", ML2, cy);
    cy += 44;

    // Feature bullets
    ctx.fillStyle = "#7060a0";
    ctx.font = "bold 16px 'Courier New', monospace";
    ctx.letterSpacing = "2px";
    ctx.fillText("PONTOS-CHAVE:", ML2, cy);
    ctx.letterSpacing = "0px";
    cy += 36;

    ctx.font = "bold 21px Georgia, serif";
    for (const feat of prevMod.features) {
      if (cy > H - 160) break;
      ctx.fillStyle = acc;
      ctx.beginPath(); ctx.arc(ML2 + 8, cy - 8, 4.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#1a1030";
      ctx.fillText(feat, ML2 + 26, cy);
      cy += 40;
    }

    // Handwritten note lines
    cy += 16;
    ctx.strokeStyle = acc + "55";
    ctx.lineWidth = 1.5;
    const noteWidths = [220, 160, 200];
    for (const lw of noteWidths) {
      if (cy > H - 130) break;
      ctx.beginPath(); ctx.moveTo(ML2, cy); ctx.lineTo(ML2 + lw, cy); ctx.stroke();
      cy += 42;
    }

    // Bottom badge
    ctx.fillStyle = acc + "30";
    ctx.font = "44px serif"; ctx.textAlign = "center";
    ctx.fillText("✦", W / 2, H - 110);
    ctx.fillStyle = acc;
    ctx.font = "bold 16px 'Courier New', monospace";
    ctx.letterSpacing = "3px";
    ctx.fillText(prevMod.badge.toUpperCase(), W / 2, H - 64);
    ctx.letterSpacing = "0px";
  } else {
    // First page blank notes
    ctx.fillStyle = "#604080aa";
    ctx.font = "italic 22px Georgia, serif";
    ctx.textAlign = "left";
    ctx.fillText("Anote suas observações...", ML2, 184);

    ctx.strokeStyle = "#8b5cf635";
    ctx.lineWidth = 1.5;
    const lineGroups = [
      { y: 240, widths: [360, 280, 320, 190] },
      { y: 440, widths: [250, 300] },
      { y: 560, widths: [320, 260, 290] },
      { y: 720, widths: [190, 340] },
    ];
    for (const grp of lineGroups) {
      let gy = grp.y;
      for (const lw of grp.widths) {
        ctx.beginPath(); ctx.moveTo(ML2, gy); ctx.lineTo(ML2 + lw, gy); ctx.stroke();
        gy += 42;
      }
    }
  }

  return new THREE.CanvasTexture(c);
}

// Blank paper (for flip back-face mid-animation)
function makePaperTex(): THREE.CanvasTexture {
  const W = 512, H = 720;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  paperBase(c.getContext("2d")!, W, H);
  return new THREE.CanvasTexture(c);
}

// ── Geometry: PlaneGeometry already in XZ plane ───────────────────────────────
function flatPlane(w: number, h: number): THREE.BufferGeometry {
  const geo = new THREE.PlaneGeometry(w, h);
  geo.applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
  return geo;
}

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
function easeInOutQuart(t: number) { return t < 0.5 ? 8*t*t*t*t : 1-Math.pow(-2*t+2,4)/2; }
// Flip ease: cinematic — slow lift, quick sweep, soft landing
function easeFlip(t: number): number {
  if (t < 0.15) return (t / 0.15) * (t / 0.15) * 0.07;             // slow start
  if (t < 0.75) return 0.07 + ((t - 0.15) / 0.60) * 0.86;         // fast sweep
  const e = (t - 0.75) / 0.25;
  return 0.93 + e * e * (3 - 2 * e) * 0.07;                        // slow graceful land
}

// ════════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ════════════════════════════════════════════════════════════════════════════════
export function Notebook3D({ modules }: Notebook3DProps) {
  // ── Refs ──────────────────────────────────────────────────────────────────────
  const scrollRef   = useRef<HTMLDivElement>(null); // tall scroll container
  const canvasRef   = useRef<HTMLDivElement>(null); // sticky canvas host
  const [uiPage, setUiPage] = useState(0);

  // ── Scroll progress (0 → 1 over the whole tall container) ────────────────────
  const { scrollYProgress } = useScroll({ target: scrollRef, offset: ["start start", "end end"] });
  // Tighter spring so animation tracks scroll position closely
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 120, damping: 28, restDelta: 0.0001 });

  // ── Three.js state lives here — read each frame, never causes re-render ───────
  const S = useRef({
    time: 0,
    // cover
    coverAngle: 0, coverTarget: 0,
    // book X
    bookWorldX: 0, bookWorldXTarget: 0,
    // camera
    camPhase: 0 as 0|1|2, camT: 0,
    isOpen: false,
    // current rendered page (integer) and flip animation
    page: 0,
    flipActive: false, flipForward: true,
    flipT: 0, flipFromPage: 0, flipHalf: false,
    // scroll-driven target
    scrollProgress: 0,
  });

  // ── useEffect: build Three.js scene ──────────────────────────────────────────
  useEffect(() => {
    if (!canvasRef.current) return;
    const el = canvasRef.current;
    let W = el.clientWidth, H = el.clientHeight;

    // ── Renderer — configuração cinematográfica ───────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0, 0);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    // Tone mapping físico — muito mais profundidade e contraste realista
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    el.appendChild(renderer.domElement);

    const scene  = new THREE.Scene();
    // Fog sutil — dá profundidade aérea ao fundo
    scene.fog = new THREE.FogExp2(0x0a0818, 0.038);

    const camera = new THREE.PerspectiveCamera(34, W / H, 0.1, 100);

    // ── Camera positions — ângulos cinematográficos ──────────────────────────
    // Fechado: leve 3/4 view para mostrar profundidade do livro
    const CAM_CLOSED = { pos: new THREE.Vector3(1.8, 5.2, 7.5), tgt: new THREE.Vector3(0.3, 0, 0) };
    // Aberto: vista levemente de cima e frente, mostrando ambas as páginas
    const CAM_OPEN   = { pos: new THREE.Vector3(0,   7.6, 5.2), tgt: new THREE.Vector3(0, -0.2, -0.3) };
    camera.position.copy(CAM_CLOSED.pos);
    camera.lookAt(CAM_CLOSED.tgt);
    const camPos = CAM_CLOSED.pos.clone();
    const camTgt = CAM_CLOSED.tgt.clone();

    // ── Lights — setup cinematográfico de 4 pontos ───────────────────────────
    // Ambient bem baixo — deixa sombras profundas e dramáticas
    scene.add(new THREE.AmbientLight(0x1a1025, 0.55));

    // Key light — sol quente vindo da direita e cima (estúdio fotográfico)
    const sun = new THREE.DirectionalLight(0xffe8c0, 2.4);
    sun.position.set(5, 16, 9);
    sun.castShadow = true;
    sun.shadow.mapSize.set(4096, 4096);
    sun.shadow.bias = -0.0002;
    sun.shadow.normalBias = 0.02;
    Object.assign(sun.shadow.camera, { left:-12, right:12, top:12, bottom:-12, far:50 });
    scene.add(sun);

    // Fill light — luz fria e difusa da esquerda (céu / reflector)
    const fill = new THREE.DirectionalLight(0x8ab4d8, 0.55);
    fill.position.set(-8, 6, 4);
    scene.add(fill);

    // Rim light — contorno atrás do livro (separa do fundo)
    const rim = new THREE.DirectionalLight(0x6040ff, 0.35);
    rim.position.set(-2, 3, -12);
    scene.add(rim);

    // Accent point — luz roxa sutil embaixo/frente para realçar a lombada
    const accent = new THREE.PointLight(0x7c3aed, 1.1, 14);
    accent.position.set(0, -1.5, 4.5);
    scene.add(accent);

    // Warm glow — pontual quente na diagonal superior direita
    const warm = new THREE.PointLight(0xff9944, 0.45, 20);
    warm.position.set(6, 10, 3);
    scene.add(warm);

    // ── Geometry constants ────────────────────────────────────────────────────
    const PW = 2.6, PD = 4.0, PT = 0.30, CT = 0.088;
    const TY = PT / 2 + CT / 2;

    // ── Textures ──────────────────────────────────────────────────────────────
    const coverTex  = makeCoverTex();
    const rightTexs = modules.map((m, i) => makeRightPageTex(m, i, modules.length));
    const leftTexs  = modules.map((_, i) => makeLeftPageTex(i + 1, modules.length, i > 0 ? modules[i - 1] : null));

    // ── Materials — PBR físico com roughness/metalness calibrados ─────────────
    // Capa escura: couro sintético
    const darkMat  = new THREE.MeshStandardMaterial({
      color: "#110d1e", roughness: 0.78, metalness: 0.08,
      envMapIntensity: 0.6,
    });
    // Miolo das páginas: papel levemente amarelado
    const edgeMat  = new THREE.MeshStandardMaterial({
      color: "#e8e0d0", roughness: 0.98, metalness: 0.0,
    });
    // Páginas abertas: papel com roughness alto (sem reflexo)
    const leftMat  = new THREE.MeshStandardMaterial({
      map: leftTexs[0],  roughness: 0.96, metalness: 0.0,
      envMapIntensity: 0.1,
    });
    const rightMat = new THREE.MeshStandardMaterial({
      map: rightTexs[0], roughness: 0.96, metalness: 0.0,
      envMapIntensity: 0.1,
    });
    const flipMat  = new THREE.MeshStandardMaterial({
      map: rightTexs[0], roughness: 0.96, metalness: 0.0,
      side: THREE.DoubleSide, envMapIntensity: 0.1,
    });

    // ── Book group ─────────────────────────────────────────────────────────────
    const bookGroup = new THREE.Group();
    bookGroup.position.set(-PW / 2, 0, 0);
    bookGroup.rotation.y = 0.42;
    scene.add(bookGroup);
    S.current.bookWorldX        = -PW / 2;
    S.current.bookWorldXTarget  = -PW / 2;

    // Back cover — full width beneath both page halves
    const backCover = new THREE.Mesh(new THREE.BoxGeometry(PW * 2 + 0.14, CT, PD), darkMat);
    backCover.position.set(0, -(PT / 2 + CT / 2), 0); backCover.receiveShadow = true;
    bookGroup.add(backCover);

    // Page stacks
    const rightStack = new THREE.Mesh(new THREE.BoxGeometry(PW - 0.05, PT, PD - 0.05), edgeMat);
    rightStack.position.x = PW / 2; rightStack.receiveShadow = true;
    bookGroup.add(rightStack);

    const leftStack = new THREE.Mesh(new THREE.BoxGeometry(PW - 0.05, 0.01, PD - 0.05), edgeMat);
    leftStack.position.x = -PW / 2; leftStack.visible = false;
    bookGroup.add(leftStack);

    // Spine
    // Lombada levemente mais larga e material brilhante para separar as páginas
    const spineMesh = new THREE.Mesh(new THREE.BoxGeometry(0.16, PT + CT * 2 + 0.04, PD), new THREE.MeshStandardMaterial({
      color: "#0d0a18", roughness: 0.60, metalness: 0.18, envMapIntensity: 1.0,
    }));
    bookGroup.add(spineMesh);

    // ── Cover — geometria com curl igual à página, pivotando no spine (x=0) ────
    // Usa PlaneGeometry deformada pelo mesmo sistema de curl das páginas.
    // Quando aberta (t=1) ela repousa do lado esquerdo, abaixo das páginas.
    const COVER_SEGS = 20;
    const coverGeo = new THREE.PlaneGeometry(PW, PD, COVER_SEGS, 1);
    coverGeo.applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
    // Pivô no spine (x=0), capa se estende para +x
    coverGeo.applyMatrix4(new THREE.Matrix4().makeTranslation(PW / 2, 0, 0));

    // Capa: material com textura e reflexo sutil de couro envernizado
    const coverTopMat = new THREE.MeshStandardMaterial({
      map: coverTex, roughness: 0.58, metalness: 0.12,
      side: THREE.DoubleSide, envMapIntensity: 0.8,
    });
    const coverMesh   = new THREE.Mesh(coverGeo, coverTopMat);
    coverMesh.castShadow  = true;
    coverMesh.renderOrder = 5; // abaixo das páginas (renderOrder 10)

    const coverPivot = new THREE.Group();
    // Ligeiramente abaixo do topo do miolo para não sobrepor páginas quando aberta
    coverPivot.position.set(0, TY - CT * 0.1, 0);
    bookGroup.add(coverPivot);
    coverPivot.add(coverMesh);

    const coverPosAttr = coverGeo.attributes.position as THREE.BufferAttribute;
    const coverOrigX   = new Float32Array(coverPosAttr.count);
    for (let i = 0; i < coverPosAttr.count; i++) coverOrigX[i] = coverPosAttr.getX(i);

    // Anima a capa com o mesmo sistema de curl das páginas
    // t=0: fechada (plana sobre o miolo), t=1: aberta (virada para a esquerda)
    function applyCoverCurl(t: number) {
      const baseAngle = t * Math.PI;
      const maxLag    = 0.22; // capa é mais rígida → menos curl
      const curlLag   = Math.sin(t * Math.PI) * maxLag;
      for (let i = 0; i < coverPosAttr.count; i++) {
        const ox    = coverOrigX[i];
        const rel   = ox / PW;
        const lag   = curlLag * rel * rel;
        const angle = baseAngle - lag;
        coverPosAttr.setX(i,  ox * Math.cos(angle));
        coverPosAttr.setY(i,  ox * Math.sin(angle)); // sobe durante a virada
      }
      coverPosAttr.needsUpdate = true;
      coverGeo.computeVertexNormals();
    }
    applyCoverCurl(0); // estado inicial: fechada

    // ── Static pages ───────────────────────────────────────────────────────────
    const leftPage  = new THREE.Mesh(flatPlane(PW, PD), leftMat);
    leftPage.position.set(-PW / 2, TY + 0.001, 0); leftPage.receiveShadow = true;
    leftPage.visible = false; bookGroup.add(leftPage);

    const rightPage = new THREE.Mesh(flatPlane(PW, PD), rightMat);
    rightPage.position.set(PW / 2, TY + 0.001, 0); rightPage.receiveShadow = true;
    rightPage.visible = false; bookGroup.add(rightPage);

    const divider = new THREE.Mesh(new THREE.BoxGeometry(0.05, CT * 0.6, PD), darkMat);
    divider.position.set(0, TY + 0.001, 0); divider.visible = false;
    bookGroup.add(divider);

    // ── Flip page ──────────────────────────────────────────────────────────────
    const FLIP_SEGS = 20;
    const flipGeo = new THREE.PlaneGeometry(PW, PD, FLIP_SEGS, 1);
    flipGeo.applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
    flipGeo.applyMatrix4(new THREE.Matrix4().makeTranslation(PW / 2, 0, 0));

    const flipMesh  = new THREE.Mesh(flipGeo, flipMat);
    flipMesh.castShadow = true;
    flipMesh.renderOrder = 10;

    const flipPivot = new THREE.Group();
    flipPivot.position.set(0, TY + 0.003, 0);
    flipPivot.visible = false;
    bookGroup.add(flipPivot);
    flipPivot.add(flipMesh);

    const posAttr = flipGeo.attributes.position as THREE.BufferAttribute;
    const origX   = new Float32Array(posAttr.count);
    for (let i = 0; i < posAttr.count; i++) origX[i] = posAttr.getX(i);

    // Shadow catcher — sombra projetada no chão
    const shadowPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(32, 32),
      new THREE.ShadowMaterial({ opacity: 0.42, color: 0x000000 })
    );
    shadowPlane.rotation.x = -Math.PI / 2;
    shadowPlane.position.y = -(PT / 2 + CT + 0.04);
    shadowPlane.receiveShadow = true;
    scene.add(shadowPlane);

    // ── Sombra de lombada (spine gutter) — plano com gradiente escuro no centro ─
    // Cria a ilusão de profundidade/dobra entre as duas páginas abertas
    const gutterGeo = new THREE.PlaneGeometry(0.22, PD);
    gutterGeo.applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
    const gutterCanvas = document.createElement("canvas");
    gutterCanvas.width = 64; gutterCanvas.height = 4;
    const gutterCtx = gutterCanvas.getContext("2d")!;
    const gutterGrad = gutterCtx.createLinearGradient(0, 0, 64, 0);
    gutterGrad.addColorStop(0,    "rgba(0,0,0,0.0)");
    gutterGrad.addColorStop(0.18, "rgba(0,0,0,0.55)");
    gutterGrad.addColorStop(0.5,  "rgba(0,0,0,0.80)");
    gutterGrad.addColorStop(0.82, "rgba(0,0,0,0.55)");
    gutterGrad.addColorStop(1,    "rgba(0,0,0,0.0)");
    gutterCtx.fillStyle = gutterGrad;
    gutterCtx.fillRect(0, 0, 64, 4);
    const gutterTex = new THREE.CanvasTexture(gutterCanvas);
    const gutterMesh = new THREE.Mesh(
      gutterGeo,
      new THREE.MeshBasicMaterial({ map: gutterTex, transparent: true, depthWrite: false, renderOrder: 15 })
    );
    gutterMesh.position.set(0, TY + 0.004, 0);
    gutterMesh.visible = false;
    bookGroup.add(gutterMesh);

    // ── Curl deformation ──────────────────────────────────────────────────────
    // fwd=true:  página gira da direita para a esquerda (avançar)
    // fwd=false: página gira da esquerda para a direita (voltar)
    function applyPageCurl(t: number, fwd: boolean) {
      const baseAngle = t * Math.PI;
      const maxLag    = 0.36;
      const curlLag   = Math.sin(t * Math.PI) * maxLag;

      for (let i = 0; i < posAttr.count; i++) {
        const ox  = origX[i];           // 0..PW (borda da esquerda ao pivô)
        const rel = ox / PW;            // 0..1
        const lag = curlLag * rel * rel;
        const angle = fwd ? (baseAngle - lag) : -(baseAngle - lag);
        // Rotaciona em torno do pivô (x=0)
        const newX = ox * Math.cos(angle);
        const newY = ox * Math.sin(Math.abs(angle)); // sempre levanta para cima
        posAttr.setX(i, newX);
        posAttr.setY(i, newY);
      }
      posAttr.needsUpdate = true;
      flipGeo.computeVertexNormals();
    }

    // ── Flip helpers ──────────────────────────────────────────────────────────
    function endFlip() {
      const s  = S.current;
      const to = s.flipForward ? s.flipFromPage + 1 : s.flipFromPage - 1;
      s.page       = to;
      s.flipActive = false;
      s.flipHalf   = false;
      // Define texturas da página destino
      leftMat.map  = leftTexs[to];  leftMat.needsUpdate  = true;
      rightMat.map = rightTexs[to]; rightMat.needsUpdate = true;
      leftPage.visible  = true;
      rightPage.visible = true;
      flipPivot.visible = false;
      flipMesh.scale.x  = 1;
      flipPivot.rotation.set(0, 0, 0);
      applyPageCurl(0, true);
      setUiPage(to);
    }

    // ── Open/Close book — driven by scroll ────────────────────────────────────
    // coverAngle: 0 = fechado (capa sobre as páginas), -PI = aberto (capa virada)
    // Isso é aplicado suavemente no loop de animação via S.current.coverTarget

    function openBook() {
      const s = S.current;
      if (s.isOpen) return;
      s.isOpen    = true;
      s.camPhase  = 1;
      s.camT      = 0;
      s.coverTarget      = 1; // 1 = completamente aberta via applyCoverCurl
      s.bookWorldXTarget = 0;
      setTimeout(() => { leftStack.visible = true; }, 550);
      // Esconde capa após abertura — ela fica sob o leftStack, pages não passam por ela
      setTimeout(() => { coverMesh.visible = false; }, 1400);
      setTimeout(() => { leftPage.visible = true; rightPage.visible = true; divider.visible = true; gutterMesh.visible = true; }, 850);
      setTimeout(() => { s.camPhase = 2; }, 1800);
    }

    function closeBook() {
      const s = S.current;
      if (!s.isOpen) return;
      s.isOpen    = false;
      s.camPhase  = 0;
      s.page      = 0;
      s.flipActive = false;
      s.coverTarget      = 0; // 0 = fechada
      s.bookWorldXTarget = -PW / 2;
      // Captura posição atual da câmera para suavizar o retorno
      camPos.copy(camera.position);
      camTgt.copy(CAM_OPEN.tgt); // mantém target aproximado
      // Restaura estado visual
      leftPage.visible  = false;
      rightPage.visible = false;
      divider.visible   = false;
      gutterMesh.visible = false;
      leftStack.visible = false;
      coverMesh.visible = true;
      flipPivot.visible = false;
      leftMat.map  = leftTexs[0];  leftMat.needsUpdate  = true;
      rightMat.map = rightTexs[0]; rightMat.needsUpdate = true;
      setUiPage(0);
    }

    // ── Scroll-driven logic ────────────────────────────────────────────────────
    // scrollProgress 0→1: [0, OPEN_ZONE] = abertura, resto = virada de páginas
    const OPEN_ZONE = 0.03; // menor = começa a abrir mais rápido
    const PAGE_ZONE = (1 - OPEN_ZONE) / modules.length;

    // Inicia flip scroll-driven — textura correta na face visível desde o início
    function beginScrollFlip(fwd: boolean, fromPage: number) {
      const s = S.current;
      s.flipActive   = true;
      s.flipForward  = fwd;
      s.flipFromPage = fromPage;
      s.flipHalf     = false;
      s.flipT        = 0;
      flipPivot.rotation.set(0, 0, 0);
      flipPivot.position.y = TY + 0.003;
      flipMesh.scale.x = 1;
      flipPivot.visible = true;

      if (fwd) {
        // Página direita gira para esquerda — a página que VIRA é a direita atual
        flipMesh.position.x = 0;
        flipMesh.scale.x = 1;
        flipMat.map = rightTexs[fromPage];
        flipMat.needsUpdate = true;
        rightPage.visible = false;

        // Mostra IMEDIATAMENTE a esquerda+direita da próxima página por baixo
        const nextPage = Math.min(fromPage + 1, modules.length - 1);
        leftMat.map  = leftTexs[nextPage];  leftMat.needsUpdate  = true;
        rightMat.map = rightTexs[nextPage]; rightMat.needsUpdate = true;
        leftPage.visible  = true;
        rightPage.visible = true; // página direita da PRÓXIMA visível por baixo desde o início
      } else {
        // Página esquerda gira para direita (volta)
        flipMesh.position.x = 0;
        flipMesh.scale.x = -1;
        flipMat.map = leftTexs[fromPage];
        flipMat.needsUpdate = true;
        leftPage.visible = false;

        // Mostra IMEDIATAMENTE a direita+esquerda da página anterior por baixo
        const prevPage = Math.max(fromPage - 1, 0);
        rightMat.map = rightTexs[prevPage]; rightMat.needsUpdate = true;
        leftMat.map  = leftTexs[prevPage];  leftMat.needsUpdate  = true;
        rightPage.visible = true;
        leftPage.visible  = true;
      }
      applyPageCurl(0, fwd);
    }

    // Cancela flip sem completar (ex: scroll voltou)
    function cancelFlip() {
      const s = S.current;
      s.flipActive  = false;
      s.flipHalf    = false;
      flipPivot.visible = false;
      flipMesh.scale.x  = 1;
      // Restaura texturas e visibilidade da página atual
      leftMat.map  = leftTexs[s.page];  leftMat.needsUpdate  = true;
      rightMat.map = rightTexs[s.page]; rightMat.needsUpdate = true;
      leftPage.visible  = true;
      rightPage.visible = true;
      applyPageCurl(0, true);
    }

    function driveScroll(raw: number) {
      const s = S.current;
      s.scrollProgress = raw;

      // ── Fechar caderno se voltou ao topo ──────────────────────────────────
      if (raw < OPEN_ZONE * 0.3 && s.isOpen) {
        closeBook();
        return;
      }

      // ── Abrir caderno ─────────────────────────────────────────────────────
      if (raw >= OPEN_ZONE && !s.isOpen) {
        openBook();
      }

      if (!s.isOpen || s.camPhase < 2) return;

      // Posição contínua em "páginas": 0.0 = pag 0, 1.0 = pag 1, etc.
      const pagePos = Math.max(0, (raw - OPEN_ZONE) / PAGE_ZONE);
      const clampedPagePos = Math.min(pagePos, modules.length - 1 + 0.999);

      // Atualiza indicador de UI (página inteira mais próxima do destino)
      const uiIdx = Math.min(Math.floor(clampedPagePos), modules.length - 1);
      setUiPage(uiIdx);

      if (s.flipActive) {
        // Range scroll da transição em andamento
        const fromScrollPos = s.flipFromPage;
        const toScrollPos   = s.flipForward ? s.flipFromPage + 1 : s.flipFromPage - 1;
        // flipT = onde estamos no range [fromPage → toPage]
        const rawT = (clampedPagePos - fromScrollPos) / (toScrollPos - fromScrollPos);
        s.flipT = Math.max(0, Math.min(1, rawT));

        if (s.flipT >= 0.99) {
          endFlip();
          // Se ainda há páginas para virar, processa na próxima chamada
          if (Math.abs(clampedPagePos - s.page) > 0.01) driveScroll(raw);
        } else if (s.flipT <= 0.01) {
          cancelFlip();
        }
        return;
      }

      // ── Sem flip ativo — checar se precisa começar um ─────────────────────
      const currentPage = s.page;
      const diff = clampedPagePos - currentPage;

      if (Math.abs(diff) > 0.005) {
        const fwd = diff > 0;
        // Só inicia se ainda há páginas nessa direção
        if (fwd && currentPage < modules.length - 1) {
          beginScrollFlip(true, currentPage);
          const rawT = clampedPagePos - currentPage; // 0..1
          s.flipT = Math.max(0, Math.min(1, rawT));
          if (s.flipT >= 0.99) endFlip();
        } else if (!fwd && currentPage > 0) {
          beginScrollFlip(false, currentPage);
          const rawT = currentPage - clampedPagePos; // 0..1
          s.flipT = Math.max(0, Math.min(1, rawT));
          if (s.flipT >= 0.99) endFlip();
        }
      }
    }

    // Subscribe ao smooth scroll
    const unsub = smoothProgress.on("change", (v) => driveScroll(v));

    // ── Animation loop ─────────────────────────────────────────────────────────
    let animId: number;
    let lastTime = performance.now();

    function animate() {
      animId = requestAnimationFrame(animate);
      const now = performance.now();
      const dt  = Math.min((now - lastTime) / 1000, 0.05);
      lastTime  = now;
      const s   = S.current;
      s.time   += dt;
      const decay = (k: number) => 1 - Math.pow(k, dt);

      // Cover rotation — gira em Y: 0=fechada/aberta via curl (0=fechada, 1=aberta)
      const coverDecay = s.isOpen ? decay(0.008) : decay(0.016);
      s.coverAngle = lerp(s.coverAngle, s.coverTarget, coverDecay);
      applyCoverCurl(Math.max(0, Math.min(1, s.coverAngle)));

      // Book X centering
      s.bookWorldX = lerp(s.bookWorldX, s.bookWorldXTarget, decay(0.022));
      bookGroup.position.x = s.bookWorldX;

      // Idle motion — movimento de "respiração" do livro
      if (!s.isOpen) {
        // Fechado: levita suavemente + leve rotação oscilante
        bookGroup.position.y = Math.sin(s.time * 0.48) * 0.07 + Math.sin(s.time * 0.27) * 0.025;
        bookGroup.rotation.y = 0.44 + Math.sin(s.time * 0.31) * 0.028;
        bookGroup.rotation.z = Math.sin(s.time * 0.39) * 0.010;
        bookGroup.rotation.x = Math.sin(s.time * 0.23) * 0.008;
      } else if (s.camPhase === 2 && !s.flipActive) {
        // Aberto em repouso: respiração mínima — como um livro em cima de mesa
        bookGroup.rotation.y = Math.sin(s.time * 0.18) * 0.012;
        bookGroup.position.y = Math.sin(s.time * 0.29) * 0.016;
        bookGroup.rotation.z = 0;
        bookGroup.rotation.x = 0;
      } else {
        bookGroup.rotation.y = lerp(bookGroup.rotation.y, 0, decay(0.008));
        bookGroup.rotation.z = lerp(bookGroup.rotation.z, 0, decay(0.008));
        bookGroup.rotation.x = lerp(bookGroup.rotation.x, 0, decay(0.008));
        bookGroup.position.y = lerp(bookGroup.position.y, 0, decay(0.01));
      }

      // Camera swoop — arco cinematográfico de fechado → aberto
      if (s.camPhase === 1) {
        s.camT = Math.min(s.camT + dt / 2.4, 1);
        const t = easeInOutQuart(s.camT);
        // Arco: câmera passa levemente pela lateral antes de pousar na posição aberta
        const arc = Math.sin(t * Math.PI) * 0.28;
        const arcPos = CAM_CLOSED.pos.clone().lerp(CAM_OPEN.pos, t);
        arcPos.x += arc * 0.5;
        arcPos.z -= arc * 0.2;
        camPos.copy(arcPos);
        camTgt.lerpVectors(CAM_CLOSED.tgt, CAM_OPEN.tgt, t);
        camera.position.copy(camPos); camera.lookAt(camTgt);
      } else if (s.camPhase === 2) {
        // Aberto: paralax sutil sincronizado com a respiração do livro
        const sw = Math.sin(s.time * 0.14) * 0.14;
        const sh = Math.sin(s.time * 0.19) * 0.07;
        camera.position.set(CAM_OPEN.pos.x + sw, CAM_OPEN.pos.y + sh, CAM_OPEN.pos.z);
        camera.lookAt(CAM_OPEN.tgt.x + sw * 0.06, CAM_OPEN.tgt.y, CAM_OPEN.tgt.z);
      } else {
        // camPhase === 0: retorno suave para posição fechada
        camPos.lerp(CAM_CLOSED.pos, decay(0.014));
        camTgt.lerp(CAM_CLOSED.tgt, decay(0.014));
        camera.position.copy(camPos); camera.lookAt(camTgt);
      }

      // Page flip — flipT é controlado pelo scroll, só aplicamos curl e detectamos mid-swap
      if (s.flipActive) {
        const t = easeFlip(Math.min(s.flipT, 1));
        applyPageCurl(t, s.flipForward);

        // Troca de textura no meio da virada (back-face da página virando)
        // Quando t>=0.5 a página já passou do meio: mostra o verso (blank paper ou página oposta)
        if (!s.flipHalf && t >= 0.5) {
          s.flipHalf = true;
          if (s.flipForward) {
            // Verso da página direita que virou: mostra página esquerda da próxima (já aparece por baixo)
            // Usamos paper branco para o verso da página virando (mais realista)
            const nextPage = Math.min(s.flipFromPage + 1, modules.length - 1);
            flipMat.map = leftTexs[nextPage];
            // Oculta a página esquerda estática (agora a flip mesh a representa)
            leftPage.visible = false;
          } else {
            // Verso da página esquerda que virou para direita
            const prevPage = Math.max(s.flipFromPage - 1, 0);
            flipMat.map = rightTexs[prevPage];
            rightPage.visible = false;
          }
          flipMat.needsUpdate = true;
        }
        // Se flipHalf e voltou abaixo de 0.5, desfaz troca (scroll voltou)
        if (s.flipHalf && t < 0.5) {
          s.flipHalf = false;
          if (s.flipForward) {
            flipMat.map = rightTexs[s.flipFromPage];
            leftPage.visible = true;
          } else {
            flipMat.map = leftTexs[s.flipFromPage];
            rightPage.visible = true;
          }
          flipMat.needsUpdate = true;
        }
      }

      renderer.render(scene, camera);
    }
    animate();

    // ── Resize ────────────────────────────────────────────────────────────────
    const ro = new ResizeObserver(() => {
      W = el.clientWidth; H = el.clientHeight;
      camera.aspect = W / H; camera.updateProjectionMatrix();
      renderer.setSize(W, H);
    });
    ro.observe(el);

    return () => {
      unsub();
      cancelAnimationFrame(animId);
      ro.disconnect();
      renderer.dispose();
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modules]);

  const mod = modules[uiPage];

  // ── JSX ──────────────────────────────────────────────────────────────────────
  // Outer div is TALL (scroll container) — canvas is sticky inside it
  const totalPages  = modules.length;
  // Height: viewport * (1 intro screen + 1 open screen + 1 per page + 1 outro)
  const scrollH     = `${(totalPages + 3) * 100}vh`;

  return (
    <div ref={scrollRef} style={{ height: scrollH }} className="relative w-full select-none">
      {/* Sticky viewport — stays fixed while outer div scrolls */}
      <div className="sticky top-0 w-full" style={{ height: "clamp(480px, 70vw, 860px)" }}>
        {/* Three.js canvas */}
        <div ref={canvasRef} className="absolute inset-0" />

        {/* Scroll hint — fades out once open */}
        <AnimatePresence>
          {uiPage === 0 && (
            <motion.div
              key="hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.4 } }}
              transition={{ delay: 0.6, duration: 0.5 }}
              className="absolute bottom-5 left-1/2 -translate-x-1/2 pointer-events-none flex flex-col items-center gap-2"
            >
              <motion.div
                animate={{ y: [0, 6, 0] }}
                transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                className="flex flex-col items-center gap-1.5"
              >
                <div className="w-px h-8 bg-gradient-to-b from-primary/40 to-transparent" />
                <span className="text-[10px] font-mono text-primary/40 uppercase tracking-widest">
                  role para explorar
                </span>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Module name + dot indicator — shown once open */}
        <AnimatePresence>
          {uiPage >= 0 && mod && (
            <motion.div
              key="indicators"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2.5 pointer-events-none"
            >
              <AnimatePresence mode="wait">
                <motion.span
                  key={uiPage}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.2 }}
                  className="text-[10px] font-mono text-primary/50 uppercase tracking-widest"
                >
                  {mod.badge}
                </motion.span>
              </AnimatePresence>

              <div className="flex items-center gap-1.5">
                {modules.map((_, i) => (
                  <motion.div
                    key={i}
                    animate={{ width: i === uiPage ? 18 : 5, opacity: i === uiPage ? 1 : 0.28 }}
                    transition={{ duration: 0.25 }}
                    className="h-[5px] rounded-full bg-primary"
                    style={{ minWidth: 5 }}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
