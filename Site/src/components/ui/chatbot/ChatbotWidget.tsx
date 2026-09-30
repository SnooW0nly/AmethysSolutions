"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faXmark, faPaperPlane, faArrowRight } from "@fortawesome/free-solid-svg-icons";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  navPath?: string;
};

type FlyState = {
  active: boolean;
  from: { x: number; y: number };
  to: { x: number; y: number };
  path: string;
};

const SYSTEM_PROMPT = `Você é o Robozinho da Amethys — assistente virtual da Amethys Solutions.

SOBRE A AMETHYS:
- Empresa especializada em bots para Discord
- 11 módulos: Loja, Tickets, Sorteios, Proteção, Automações, Cloud, Customização, Rendimentos, Configurações, Mensagens e Economia

PLANOS:
• Amethys Pro: R$ 15/mês | R$ 39,99/trimestre | R$ 119,99/ano
• Amethys Cloud: R$ 6/mês | R$ 15,99/trimestre | R$ 48,24/ano

REGRAS DE RESPOSTA:
- Sempre em português brasileiro
- Respostas CURTAS (máximo 2-3 linhas)
- Tom animado e amigável
- Máximo 1-2 emojis por resposta

NAVEGAÇÃO — Quando o usuário precisar ir a uma página, adicione [NAV:/caminho] NO FINAL da sua resposta.
Páginas disponíveis:
- [NAV:/pricing] → planos, preços, valores, comprar, assinar, contratar, adquirir
- [NAV:/about] → sobre, o que é, empresa, história, informações
- [NAV:/modules] → módulos, funcionalidades, recursos, o que o bot faz, features
- [NAV:/login] → login, entrar, acessar conta, cadastrar
- [NAV:/dashboard] → painel, configurar, gerenciar, dashboard, meu bot
- [NAV:/terms] → termos, política, privacidade, regras

EXEMPLOS:
P: "Como compro um bot?"
R: "Para adquirir seu bot, acesse nossos planos — temos opções mensais, trimestrais e anuais com ótimos preços! 🚀 [NAV:/pricing]"

P: "Quais são as funcionalidades?"
R: "Temos 11 módulos poderosos: loja, tickets, sorteios, automações e muito mais! Dá uma olhada 💜 [NAV:/modules]"

P: "Como faço login?"
R: "Clica aqui para entrar na sua conta! [NAV:/login]"`;

const NAV_LABELS: Record<string, string> = {
  "/pricing":   "Ver Planos e Preços",
  "/about":     "Saiba Mais sobre a Amethys",
  "/modules":   "Explorar os Módulos",
  "/login":     "Fazer Login",
  "/dashboard": "Abrir o Dashboard",
  "/terms":     "Ver Termos de Serviço",
};

const NAV_SELECTORS: Record<string, string> = {
  "/pricing":   'a[href="/pricing"]',
  "/about":     'a[href="/about"]',
  "/modules":   'a[href="/modules"]',
  "/login":     'a[href="/login"]',
  "/dashboard": 'a[href="/dashboard"]',
};

function stripThink(text: string): string {
  return text
    .replace(/<think[^>]*>[\s\S]*?<\/think>/gi, "") // tag com fechamento
    .replace(/<think[^>]*>[\s\S]*/gi, "")            // tag sem fechamento (truncada)
    .trim();
}

function parseResponse(content: string): { text: string; navPath?: string } {
  const clean = stripThink(content);
  const match = clean.match(/\[NAV:(\/[^\]]+)\]/);
  if (match) return { text: clean.replace(match[0], "").trim(), navPath: match[1] };
  return { text: clean };
}

function RobotSVG({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 44" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="18" y1="6" x2="18" y2="1" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <circle cx="18" cy="0" r="2.5" fill="currentColor" fillOpacity="0.8"/>
      <rect x="6" y="6" width="24" height="18" rx="6" fill="currentColor"/>
      <circle cx="12.5" cy="14" r="3.5" fill="white" fillOpacity="0.95"/>
      <circle cx="23.5" cy="14" r="3.5" fill="white" fillOpacity="0.95"/>
      <circle cx="12.5" cy="14" r="2" fill="currentColor" fillOpacity="0.9"/>
      <circle cx="23.5" cy="14" r="2" fill="currentColor" fillOpacity="0.9"/>
      <circle cx="13.5" cy="13" r="0.7" fill="white"/>
      <circle cx="24.5" cy="13" r="0.7" fill="white"/>
      <rect x="11" y="20" width="14" height="2.5" rx="1.25" fill="white" fillOpacity="0.55"/>
      <rect x="4" y="27" width="28" height="16" rx="5" fill="currentColor" fillOpacity="0.88"/>
      <rect x="13" y="31" width="10" height="5" rx="2" fill="white" fillOpacity="0.25"/>
      <rect x="-2" y="28" width="8" height="6" rx="3" fill="currentColor" fillOpacity="0.7"/>
      <rect x="30" y="28" width="8" height="6" rx="3" fill="currentColor" fillOpacity="0.7"/>
    </svg>
  );
}

export default function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "init", role: "assistant", content: "Olá! Sou o Robozinho da Amethys 🤖 Como posso te ajudar hoje?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [flyState, setFlyState] = useState<FlyState>({
    active: false, from: { x: 0, y: 0 }, to: { x: 0, y: 0 }, path: "",
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const robotIframeRef = useRef<HTMLIFrameElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const handler = () => setIsOpen((prev) => !prev);
    window.addEventListener("toggle-chatbot", handler);
    return () => window.removeEventListener("toggle-chatbot", handler);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    // Sincroniza mensagens com a tela do computador no iframe
    robotIframeRef.current?.contentWindow?.postMessage(
      { type: 'updateMessages', messages: messages.map(m => ({ role: m.role, content: m.content })) },
      '*'
    );
  }, [messages, loading]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 380);
      // Reseta o robô (caso tenha saído com animação de navegação)
      setTimeout(() => {
        robotIframeRef.current?.contentWindow?.postMessage({ type: 'resetRobot' }, '*');
      }, 100);
    }
  }, [isOpen]);

  const robotAnim = useCallback((name: string) => {
    robotIframeRef.current?.contentWindow?.postMessage({ type: "playAnimation", name }, "*");
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    robotAnim("Yes");

    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const res = await fetch("/api/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            ...nextMessages.map((m) => ({ role: m.role, content: m.content })),
          ],
        }),
      });
      const data = await res.json();
      const rawReply = data.reply || "Hmm, não consegui responder agora. Tente de novo!";
      const { text: cleanText, navPath } = parseResponse(rawReply);
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: cleanText, navPath }]);
      robotAnim(navPath ? "Wave" : "Idle");
    } catch {
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: "Ops! Deu um errinho aqui. Pode tentar de novo? 😅" }]);
      robotAnim("Idle");
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, robotAnim]);

  const handleNavigate = useCallback((path: string) => {
    robotAnim("Running");
    const panelRect = panelRef.current?.getBoundingClientRect();
    const fromX = panelRect ? panelRect.left + panelRect.width / 2 : window.innerWidth - 220;
    const fromY = panelRect ? panelRect.top + 80 : window.innerHeight - 320;
    const selector = NAV_SELECTORS[path];
    let toX = window.innerWidth / 2, toY = 42;
    if (selector) {
      const el = document.querySelector(selector) as HTMLElement | null;
      if (el) {
        const rect = el.getBoundingClientRect();
        toX = rect.left + rect.width / 2;
        toY = rect.top + rect.height / 2;
        el.classList.add("chatbot-highlight");
        setTimeout(() => el.classList.remove("chatbot-highlight"), 2600);
      }
    }
    setFlyState({ active: true, from: { x: fromX, y: fromY }, to: { x: toX, y: toY }, path });
    setIsOpen(false);
    setTimeout(() => { setFlyState((s) => ({ ...s, active: false })); router.push(path); }, 1350);
  }, [router, robotAnim]);

  return (
    <>
      {/* Flying Robot */}
      <AnimatePresence>
        {flyState.active && (
          <motion.div
            initial={{ x: flyState.from.x - 36, y: flyState.from.y - 36, opacity: 0, scale: 0.4, rotate: 0 }}
            animate={{ x: flyState.to.x - 36, y: flyState.to.y - 36, opacity: [0, 1, 1, 0.7], scale: [0.4, 1.3, 1.1, 0.9], rotate: [0, -15, 12, -8, 0] }}
            exit={{ opacity: 0, scale: 0, rotate: 20 }}
            transition={{ duration: 1.25, ease: [0.22, 1, 0.36, 1] }}
            style={{ position: "fixed", top: 0, left: 0, zIndex: 9999, pointerEvents: "none" }}
          >
            <div className="w-[72px] h-[72px] rounded-2xl bg-gradient-to-br from-primary to-purple-800 border border-primary/50 shadow-2xl shadow-primary/60 flex items-center justify-center text-white">
              <RobotSVG size={40} />
            </div>
            <p className="mt-1.5 text-center text-[10px] font-bold text-primary bg-background/90 backdrop-blur-sm border border-primary/20 rounded-full px-2.5 py-0.5 whitespace-nowrap mx-auto w-fit">
              {NAV_LABELS[flyState.path] || "Indo..."}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, y: 24, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.94 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: "fixed",
              bottom: "1.25rem",
              right: "1.25rem",
              zIndex: 200,
              width: "min(360px, calc(100vw - 2.5rem))",
              maxHeight: "min(600px, calc(100vh - 2.5rem))",
              boxShadow: "0 32px 64px -16px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.05), 0 0 80px -24px rgba(139,92,246,0.3)",
            }}
            className="rounded-2xl border border-white/[0.08] overflow-hidden flex flex-col"
          >
            {/* ── Robô como fundo total ── */}
            <div
              className="absolute inset-0 rounded-2xl overflow-hidden"
              style={{ zIndex: 0 }}
            >
              {/* iframe ocupa tudo */}
              <iframe
                ref={robotIframeRef}
                src="/robot.html"
                title="Robô 3D Amethys"
                scrolling="no"
                style={{
                  border: "none",
                  background: "transparent",
                  width: "100%",
                  height: "100%",
                  display: "block",
                  pointerEvents: "none",
                }}
              />
              {/* Overlay escuro gradiente — garante legibilidade do chat sobre o robô */}
              <div
                className="absolute inset-0"
                style={{
                  background: `
                    linear-gradient(
                      to bottom,
                      rgba(9,9,11,0.55) 0%,
                      rgba(9,9,11,0.30) 35%,
                      rgba(9,9,11,0.72) 65%,
                      rgba(9,9,11,0.96) 100%
                    )
                  `,
                }}
              />
            </div>

            {/* ── Conteúdo sobre o fundo ── */}
            <div className="relative flex flex-col flex-1 min-h-0" style={{ zIndex: 1 }}>
              {/* Top accent */}
              <div className="h-px w-full bg-gradient-to-r from-transparent via-primary/70 to-transparent flex-shrink-0" />

              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="relative w-9 h-9 rounded-xl bg-primary/20 border border-primary/30 backdrop-blur-sm flex items-center justify-center text-primary">
                    <RobotSVG size={20} />
                    <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-green-400 border-2 border-background" />
                  </div>
                  <div>
                    <p className="text-[13px] font-bold text-white/90 leading-tight drop-shadow-sm">Robozinho Amethys</p>
                    <p className="text-[10px] text-white/40">Assistente Virtual</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors text-white/40 hover:text-white/70"
                >
                  <FontAwesomeIcon icon={faXmark} className="text-sm" />
                </button>
              </div>

              {/* Espaço para o robô "respirar" no topo — empurra mensagens para baixo */}
              <div className="flex-shrink-0" style={{ height: 148 }} />

              {/* Messages */}
              <div
                className="flex-1 overflow-y-auto px-3 py-2 flex flex-col gap-2 min-h-0"
                style={{ scrollbarWidth: "thin", scrollbarColor: "rgba(139,92,246,0.3) transparent" }}
              >
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[84%] text-xs leading-relaxed backdrop-blur-md ${
                        msg.role === "user"
                          ? "bg-primary/85 text-white rounded-2xl rounded-br-md px-3 py-2 shadow-lg shadow-primary/20"
                          : "bg-black/40 border border-white/10 text-white/85 rounded-2xl rounded-bl-md px-3 py-2"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.navPath && (
                        <button
                          onClick={() => handleNavigate(msg.navPath!)}
                          className="mt-2 flex items-center gap-2 w-full px-3 py-2 bg-primary/30 hover:bg-primary/50 active:bg-primary/60 border border-primary/40 rounded-xl text-primary font-semibold transition-all duration-150 text-[11px] group backdrop-blur-sm"
                        >
                          <span className="flex-1 text-left leading-tight">{NAV_LABELS[msg.navPath] ?? "Ir para a página"}</span>
                          <FontAwesomeIcon icon={faArrowRight} className="text-[9px] flex-shrink-0 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-black/40 border border-white/10 backdrop-blur-md rounded-2xl rounded-bl-md px-3.5 py-2.5">
                      <div className="flex gap-1 items-center">
                        {[0, 1, 2].map((i) => (
                          <motion.div
                            key={i}
                            className="w-1.5 h-1.5 rounded-full bg-primary/70"
                            animate={{ y: ["0%", "-55%", "0%"] }}
                            transition={{ duration: 0.65, delay: i * 0.14, repeat: Infinity, ease: "easeInOut" }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="px-3 pb-3 pt-2 flex-shrink-0">
                <div className="flex items-center gap-2 bg-black/50 hover:bg-black/60 focus-within:bg-black/60 rounded-xl border border-white/10 focus-within:border-primary/40 transition-all px-3 py-2.5 backdrop-blur-md">
                  <input
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                    placeholder="Pergunte sobre a Amethys..."
                    className="flex-1 bg-transparent text-xs text-white/85 outline-none placeholder:text-white/25"
                    disabled={loading}
                    autoComplete="off"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!input.trim() || loading}
                    className="w-7 h-7 rounded-lg bg-primary hover:bg-primary/85 active:bg-primary/70 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-all active:scale-95 text-white flex-shrink-0"
                  >
                    <FontAwesomeIcon icon={faPaperPlane} className="text-[11px]" />
                  </button>
                </div>
                <p className="text-center text-[9px] text-white/20 mt-1.5 select-none">Powered by Amethys AI</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}