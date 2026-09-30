"use client";

import { useEffect, useState } from "react";

type Feedback = {
  id: string;
  content: string;
  username: string;
  avatar: string;
  timestamp: string;
};

const STARS = [1, 2, 3, 4, 5];

function FeedbackCard({ feedback }: { feedback: Feedback }) {
  return (
    <div className="flex items-start gap-3 border border-white/[0.06] bg-white/[0.04] hover:bg-white/[0.07] transition-colors duration-200 rounded-xl px-3 py-2.5 shrink-0">
      {/* Avatar */}
      <div className="relative shrink-0 mt-0.5">
        <div className="w-7 h-7 rounded-full overflow-hidden border border-white/10 bg-foreground/10">
          <img
            src={feedback.avatar}
            alt={feedback.username}
            width={28}
            height={28}
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src =
                "https://cdn.discordapp.com/embed/avatars/0.png";
            }}
          />
        </div>
        {/* Discord badge */}
        <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#5865F2] border border-black flex items-center justify-center">
          <svg width="7" height="7" viewBox="0 0 24 24" fill="white">
            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
          </svg>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-col flex-1 min-w-0 gap-0.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[12px] font-semibold text-foreground/90 truncate">
            {feedback.username}
          </span>
          {/* Stars */}
          <div className="flex items-center gap-0.5 shrink-0">
            {STARS.map((s) => (
              <svg key={s} width="8" height="8" viewBox="0 0 24 24" fill="currentColor" className="text-yellow-400/80">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
            ))}
          </div>
        </div>
        <p className="text-[11.5px] text-foreground/60 leading-relaxed line-clamp-2">
          {feedback.content}
        </p>
      </div>
    </div>
  );
}

const FALLBACK: Feedback[] = [
  { id: "1", content: "Automatizei minha loja inteira em menos de 15 minutos. Nunca foi tão fácil vender no Discord.", username: "lucasdev_", avatar: "https://cdn.discordapp.com/embed/avatars/0.png", timestamp: "" },
  { id: "2", content: "Sistema de pagamentos perfeito. Pix cai na hora e o bot entrega automático. Recomendo demais!", username: "Maria_Store", avatar: "https://cdn.discordapp.com/embed/avatars/1.png", timestamp: "" },
  { id: "3", content: "Uso há 4 meses, já faturei muito mais do que esperava. A automação de pedidos me economiza horas.", username: "xablau.gg", avatar: "https://cdn.discordapp.com/embed/avatars/2.png", timestamp: "" },
  { id: "4", content: "Melhor bot de loja do Discord sem dúvida. Interface clean, suporte rápido e atualizações frequentes.", username: "pedro_gamer", avatar: "https://cdn.discordapp.com/embed/avatars/3.png", timestamp: "" },
  { id: "5", content: "Comecei do zero e hoje tenho uma loja estruturada. O Amethys foi essencial nessa jornada.", username: "ana.shop", avatar: "https://cdn.discordapp.com/embed/avatars/4.png", timestamp: "" },
  { id: "6", content: "O sistema de cupons é perfeito pra fidelizar clientes. Vale muito cada centavo investido.", username: "rafael_drops", avatar: "https://cdn.discordapp.com/embed/avatars/5.png", timestamp: "" },
  { id: "7", content: "Configurei em minutos e já tava vendendo. Nunca imaginei que seria tão simples.", username: "thiag0.dev", avatar: "https://cdn.discordapp.com/embed/avatars/0.png", timestamp: "" },
  { id: "8", content: "Suporte incrível e o bot nunca cai. Minha loja funciona 24h sem precisar de mim.", username: "gabi_store", avatar: "https://cdn.discordapp.com/embed/avatars/3.png", timestamp: "" },
];

export function FeedbacksMarquee() {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>(FALLBACK);

  useEffect(() => {
    fetch("/api/info/feedbacks")
      .then((r) => r.json())
      .then((json) => {
        if (Array.isArray(json?.data) && json.data.length >= 4) {
          setFeedbacks(json.data);
        }
      })
      .catch(() => {});
  }, []);

  // Triplica para garantir loop suave e sem salto
  const items = [...feedbacks, ...feedbacks, ...feedbacks];

  return (
    <>
      <style>{`
        @keyframes feedback-scroll {
          0%   { transform: translateY(0); }
          100% { transform: translateY(calc(-100% / 3)); }
        }
        .feedback-track {
          animation: feedback-scroll 24s linear infinite;
          will-change: transform;
        }
        .feedback-track:hover {
          animation-play-state: paused;
        }
      `}</style>

      <div
        className="relative w-full rounded-2xl border border-white/5 bg-white/[0.03] shadow-[0_0_40px_-10px_rgba(0,0,0,0.4)] p-5 backdrop-blur-xl overflow-hidden"
        style={{ height: "315px" }}
      >
        {/* Header — espelho exato do card "Últimas vendas" */}
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold">
            O que dizem sobre nós
          </p>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] text-foreground/30 font-medium">Discord</span>
          </div>
        </div>

        {/* Scroll area */}
        <div className="relative overflow-hidden" style={{ height: "calc(315px - 52px)" }}>
          {/* Fade top */}
          <div
            className="pointer-events-none absolute top-0 left-0 right-0 z-10"
            style={{
              height: "28px",
              background: "linear-gradient(to bottom, rgba(10,10,10,0.85) 0%, transparent 100%)",
            }}
          />
          {/* Fade bottom */}
          <div
            className="pointer-events-none absolute bottom-0 left-0 right-0 z-10"
            style={{
              height: "36px",
              background: "linear-gradient(to top, rgba(10,10,10,0.95) 0%, transparent 100%)",
            }}
          />

          <div className="feedback-track flex flex-col gap-1.5">
            {items.map((f, i) => (
              <FeedbackCard key={`${f.id}-${i}`} feedback={f} />
            ))}
          </div>
        </div>
      </div>
    </>
  );
}