"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import GridLines from "@/components/GridLines";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Partnership {
  _id: string;
  name: string;
  shortDescription?: string;
  description?: string;
  logoUrl?: string;
  bannerUrl?: string;
  websiteUrl?: string;
  active: boolean;
}

// ─── Side Banner ──────────────────────────────────────────────────────────────
// Shown on desktop only (≥1024px). Each side cycles through partners independently.
// Left side shows even-indexed partners, right shows odd-indexed.
// If only 1 partner, both sides show the same one.

function SideBanner({
  partner,
  side,
}: {
  partner: Partnership;
  side: "left" | "right";
}) {
  return (
    <a
      href={partner.websiteUrl ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        position: "fixed",
        top: "50%",
        transform: "translateY(-50%)",
        [side]: "10px",
        width: "88px",
        zIndex: 30,
        textDecoration: "none",
      }}
      className="max-lg:hidden"
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={partner._id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "8px",
            borderRadius: "14px",
            border: "1px solid rgba(255,255,255,0.07)",
            background: "rgba(255,255,255,0.03)",
            backdropFilter: "blur(8px)",
            padding: "12px 8px",
            cursor: "pointer",
            transition: "border-color 0.2s, background 0.2s",
          }}
          whileHover={{
            borderColor: "rgba(255,255,255,0.18)",
            background: "rgba(255,255,255,0.07)",
          }}
        >
          {/* Logo */}
          {partner.logoUrl ? (
            <img
              src={partner.logoUrl}
              alt={partner.name}
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "12px",
                objectFit: "cover",
                flexShrink: 0,
              }}
            />
          ) : (
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "12px",
                background: "rgba(255,255,255,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <span style={{ fontSize: "14px", fontWeight: 700, color: "rgba(255,255,255,0.3)" }}>
                {partner.name.slice(0, 2).toUpperCase()}
              </span>
            </div>
          )}

          {/* Divider */}
          <div style={{ width: "40px", height: "1px", background: "rgba(255,255,255,0.08)" }} />

          {/* Name — rotated vertically */}
          <div
            style={{
              writingMode: "vertical-rl",
              textOrientation: "mixed",
              transform: side === "left" ? "rotate(180deg)" : "none",
              fontSize: "9px",
              fontWeight: 600,
              color: "rgba(255,255,255,0.35)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              maxHeight: "96px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              lineHeight: 1,
            }}
          >
            {partner.name}
          </div>

          {/* "Parceiro" label */}
          <div
            style={{
              fontSize: "7px",
              color: "rgba(255,255,255,0.2)",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              fontWeight: 500,
            }}
          >
            parceiro
          </div>
        </motion.div>
      </AnimatePresence>
    </a>
  );
}

// ─── Side Banner Controller ────────────────────────────────────────────────────

function SideBanners({ partners }: { partners: Partnership[] }) {
  const [leftIdx, setLeftIdx] = useState(0);
  const [rightIdx, setRightIdx] = useState(partners.length > 1 ? 1 : 0);

  useEffect(() => {
    if (partners.length <= 1) return; // nothing to cycle

    const interval = setInterval(() => {
      setLeftIdx((i) => (i + 2) % partners.length);
      setRightIdx((i) => (i + 2) % partners.length);
    }, 4000);

    return () => clearInterval(interval);
  }, [partners.length]);

  return (
    <>
      <SideBanner partner={partners[leftIdx]} side="left" />
      <SideBanner partner={partners[rightIdx]} side="right" />
    </>
  );
}

// ─── Mobile Bottom Strip ──────────────────────────────────────────────────────

function MobilePartnerStrip({ partners }: { partners: Partnership[] }) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (partners.length <= 1) return;
    const interval = setInterval(() => setIdx((i) => (i + 1) % partners.length), 3500);
    return () => clearInterval(interval);
  }, [partners.length]);

  const p = partners[idx];

  return (
    <div className="lg:hidden mt-4 w-full flex justify-center">
      <AnimatePresence mode="wait">
        <motion.a
          key={p._id + idx}
          href={p.websiteUrl ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.4 }}
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-foreground/[0.08] bg-foreground/[0.04] hover:bg-foreground/[0.08] transition-colors"
          style={{ maxWidth: "320px", width: "100%", textDecoration: "none" }}
        >
          {p.logoUrl ? (
            <img src={p.logoUrl} alt={p.name} className="w-8 h-8 rounded-lg object-cover flex-shrink-0" />
          ) : (
            <div className="w-8 h-8 rounded-lg bg-foreground/10 flex items-center justify-center flex-shrink-0">
              <span className="text-[10px] font-bold text-foreground/40">{p.name.slice(0, 2).toUpperCase()}</span>
            </div>
          )}
          <div className="flex flex-col min-w-0">
            <span className="text-[10px] text-foreground/30 uppercase tracking-widest font-medium">parceiro</span>
            <span className="text-xs font-semibold text-foreground/70 truncate">{p.name}</span>
            {(p.shortDescription || p.description) && (
              <span className="text-[10px] text-foreground/40 truncate">{p.shortDescription || p.description}</span>
            )}
          </div>
        </motion.a>
      </AnimatePresence>
    </div>
  );
}

const COMMAND = "/painel";
const TYPE_DELAY = 90;

/* cursor start (bottom-right area) → target (slightly lower than before) */
const CURSOR_START = { x: 80, y: 78 };
const CURSOR_TARGET = { x: 38, y: 72 };

function Cursor({ click }: { click: boolean }) {
  return (
    <motion.svg
      width="18"
      height="22"
      viewBox="0 0 20 24"
      animate={{ scale: click ? 0.8 : 1 }}
      transition={{ duration: 0.1 }}
      style={{ filter: "drop-shadow(0 2px 6px rgba(0,0,0,.8))" }}
    >
      <path
        d="M1.5 1.5V20L6 15L9.5 22.5L12 21.4L8.3 13.7H15L1.5 1.5Z"
        fill="white"
        stroke="#000"
        strokeWidth="1.4"
      />
    </motion.svg>
  );
}

function PauseIcon() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ duration: 0.2 }}
      className="flex gap-2 items-center justify-center"
    >
      <div className="w-3 h-9 md:w-4 md:h-12 bg-white/90 rounded-sm shadow-lg" />
      <div className="w-3 h-9 md:w-4 md:h-12 bg-white/90 rounded-sm shadow-lg" />
    </motion.div>
  );
}

export function Preview() {
  const [typed, setTyped] = useState("");
  const [showUserMsg, setShowUserMsg] = useState(false);
  const [showEmbed, setShowEmbed] = useState(false);

  const [cursorVisible, setCursorVisible] = useState(false);
  const [cursorPos, setCursorPos] = useState(CURSOR_START);
  const [cursorClick, setCursorClick] = useState(false);

  const [phase, setPhase] = useState<"idle" | "paused" | "split">("idle");

  /* partnerships */
  const [partners, setPartners] = useState<Partnership[]>([]);

  useEffect(() => {
    fetch("/api/info/partnerships", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((json: any) => {
        const list: Partnership[] = json?.partnerships ?? [];
        const active = list.filter((p) => p.active);
        if (active.length) setPartners(active);
      })
      .catch(() => {});
  }, []);

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  useEffect(() => {
    const run = async () => {
      while (true) {
        /* typing */
        for (let i = 1; i <= COMMAND.length; i++) {
          await sleep(TYPE_DELAY);
          setTyped(COMMAND.slice(0, i));
        }
        await sleep(400);

        /* send */
        setTyped("");
        setShowUserMsg(true);
        await sleep(500);

        /* bot response */
        setShowEmbed(true);
        await sleep(1200);

        /* cursor moves */
        setCursorVisible(true);
        setCursorPos(CURSOR_START);
        await sleep(150);
        setCursorPos(CURSOR_TARGET);
        await sleep(700);

        /* click */
        setCursorClick(true);
        await sleep(120);
        setCursorClick(false);

        /* pause phase → everything dims, pause icon */
        setPhase("paused");
        await sleep(1000);

        /* split phase → embed thrown left, plan card slides in */
        setPhase("split");
        await sleep(3000);

        /* reset */
        setPhase("idle");
        setCursorVisible(false);
        setShowEmbed(false);
        setShowUserMsg(false);
        await sleep(700);
      }
    };
    run();
  }, []);

  const now = new Date().toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <>
      {/* Side banners — desktop only, fixed to viewport edges */}
      {partners.length > 0 && <SideBanners partners={partners} />}

      <section className="flex flex-col items-center w-full px-4 md:px-0">
        {/* perspective wrapper — disabled on mobile */}
        <div
          className="w-full max-w-2xl"
          style={{ transform: "perspective(900px) rotateX(6deg)" }}
        >
        {/* window shell — uses site bg + grid */}
        <div
          className="relative rounded-xl overflow-hidden border border-foreground/10 shadow-[0_32px_80px_rgba(0,0,0,0.55)]"
          style={{ fontFamily: '"gg sans","Noto Sans",Whitney,"Helvetica Neue",Arial,sans-serif' }}
        >
          {/* site grid as background */}
          <div className="absolute inset-0 z-0 bg-background" />
          <GridLines
            className="absolute inset-0 z-0 opacity-[0.07] pointer-events-none"
            style={{
              WebkitMaskImage:
                "radial-gradient(80% 80% at 50% 40%, #000 40%, transparent 100%)",
              maskImage:
                "radial-gradient(80% 80% at 50% 40%, #000 40%, transparent 100%)",
            }}
          />

          {/* channel header */}
          <div className="relative z-10 bg-foreground/[0.04] px-4 py-2.5 border-b border-foreground/[0.06] text-foreground/80 font-semibold text-sm select-none">
            # geral
          </div>

          {/* messages area */}
          <div
            className="relative z-10 px-4 pt-5 pb-2 flex flex-col justify-end gap-4"
            style={{ minHeight: "clamp(260px, 45vw, 400px)" }}
          >
            {/* user message */}
            <AnimatePresence>
              {showUserMsg && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex gap-3 items-start"
                >
                  <div className="w-8 h-8 md:w-9 md:h-9 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                    7
                  </div>
                  <div>
                    <div className="text-foreground/80 font-semibold text-xs md:text-sm">
                      7gsw
                      <span className="text-foreground/30 text-[10px] ml-1.5">
                        Hoje às {now}
                      </span>
                    </div>
                    <div className="text-foreground/60 text-sm">/painel</div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* bot message */}
            <AnimatePresence>
              {showEmbed && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex gap-3 items-start"
                >
                  {/* bot avatar */}
                  <img
                    src="/logo.png"
                    className="w-8 h-8 md:w-9 md:h-9 rounded-full flex-shrink-0"
                    alt="Amethys"
                  />

                  <div className="flex-1 min-w-0">
                    {/* bot name */}
                    <div className="text-foreground font-semibold text-xs md:text-sm mb-1.5">
                      Amethys
                      <span className="bg-primary/80 text-white text-[8px] px-1 py-0.5 rounded ml-1.5 align-middle">
                        APP
                      </span>
                      <span className="text-foreground/30 text-[10px] ml-1.5">
                        Hoje às {now}
                      </span>
                    </div>

                    {/* embed + overlay container */}
                    <div className="relative" style={{ maxWidth: "clamp(200px, 60vw, 420px)" }}>
                      {/* embed image — slides left in split phase */}
                      <motion.div
                        animate={
                          phase === "split"
                            ? { x: "-8%", opacity: 0.25, scale: 0.97 }
                            : phase === "paused"
                            ? { x: 0, opacity: 0.45 }
                            : { x: 0, opacity: 1 }
                        }
                        transition={
                          phase === "split"
                            ? { type: "spring", stiffness: 320, damping: 28 }
                            : { duration: 0.35 }
                        }
                        className="relative rounded-md overflow-hidden"
                      >
                        <img
                          src="/embed.png"
                          className="w-full rounded-md block"
                          alt="embed"
                          draggable={false}
                        />
                      </motion.div>

                      {/* pause icon overlay */}
                      <AnimatePresence>
                        {(phase === "paused" || phase === "split") && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: phase === "split" ? 0 : 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="absolute inset-0 flex items-center justify-center pointer-events-none"
                          >
                            <PauseIcon />
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* plan card slides in from right */}
                      <AnimatePresence>
                        {phase === "split" && (
                          <motion.div
                            initial={{ opacity: 0, x: 24 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 16 }}
                            transition={{ type: "spring", stiffness: 280, damping: 26, delay: 0.1 }}
                            className="absolute top-0 right-0 bottom-0 flex items-center justify-end"
                            style={{ width: "58%" }}
                          >
                            <div className="bg-background/95 border border-primary/25 backdrop-blur-md rounded-lg p-3 md:p-4 shadow-xl w-full">
                              <p className="text-foreground/40 text-[9px] uppercase tracking-widest font-mono mb-1">
                                Acesso restrito
                              </p>
                              <p className="text-foreground text-xs md:text-sm font-semibold leading-snug">
                                Para ver mais, adquira um plano.
                              </p>
                              <p className="text-foreground/50 text-[10px] mt-1 leading-snug">
                                Desbloqueie todos os recursos com o Amethys Pro.
                              </p>
                              <div className="mt-2.5 px-2.5 py-1 bg-primary/15 border border-primary/20 rounded-md text-primary text-[10px] font-semibold w-fit cursor-pointer hover:bg-primary/25 transition-colors">
                                Ver planos →
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* cursor */}
            <AnimatePresence>
              {cursorVisible && (
                <motion.div
                  animate={{
                    left: `${cursorPos.x}%`,
                    top: `${cursorPos.y}%`,
                  }}
                  transition={{ duration: 0.65, ease: "easeInOut" }}
                  className="absolute z-50 pointer-events-none"
                >
                  <Cursor click={cursorClick} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* input bar */}
          <div className="relative z-10 px-4 pb-4">
            <div className="bg-foreground/[0.05] border border-foreground/[0.07] rounded-lg px-3.5 py-2.5 text-xs md:text-sm text-foreground/35 select-none">
              {typed ? (
                <span className="text-foreground/70">{typed}</span>
              ) : (
                "Enviar mensagem para #geral"
              )}
            </div>
          </div>
        </div>
      </div>

        {/* Mobile partner strip — below card, mobile only */}
        {partners.length > 0 && <MobilePartnerStrip partners={partners} />}
      </section>
    </>
  );
}
