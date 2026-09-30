"use client";

import { Accordion, AccordionItem } from "@heroui/react";
import { useState, useEffect } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Feedback = {
  id: string;
  content: string;
  username: string;
  avatar: string;
  timestamp: string;
};

// ─── Fallback feedbacks (mesmo do FeedbacksMarquee) ──────────────────────────

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

const STARS = [1, 2, 3, 4, 5];

// ─── Card de feedback horizontal ─────────────────────────────────────────────

function FeedbackCard({ feedback }: { feedback: Feedback }) {
  return (
    <div
      className="shrink-0 flex flex-col gap-2 border border-white/[0.06] bg-white/[0.04] hover:bg-white/[0.07] transition-colors duration-200 rounded-xl p-3"
      style={{ width: "220px" }}
    >
      <div className="flex items-center gap-2">
        {/* Avatar */}
        <div className="relative shrink-0">
          <div className="w-7 h-7 rounded-full overflow-hidden border border-white/10 bg-foreground/10">
            <img
              src={feedback.avatar}
              alt={feedback.username}
              width={28}
              height={28}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).src = "https://cdn.discordapp.com/embed/avatars/0.png";
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

        <div className="flex flex-col min-w-0">
          <span className="text-[12px] font-semibold text-foreground/90 truncate">{feedback.username}</span>
          <div className="flex items-center gap-0.5">
            {STARS.map((s) => (
              <svg key={s} width="8" height="8" viewBox="0 0 24 24" fill="currentColor" className="text-yellow-400/80">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
            ))}
          </div>
        </div>
      </div>

      <p className="text-[11.5px] text-foreground/60 leading-relaxed line-clamp-3">
        {feedback.content}
      </p>
    </div>
  );
}

// ─── Carrossel horizontal de feedbacks ───────────────────────────────────────

function FeedbacksCarousel() {
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

  const items = [...feedbacks, ...feedbacks, ...feedbacks];

  return (
    <>
      <style>{`
        @keyframes feedbacks-h-scroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(calc(-100% / 3)); }
        }
        .feedbacks-h-track {
          animation: feedbacks-h-scroll 32s linear infinite;
          will-change: transform;
        }
        .feedbacks-h-track:hover {
          animation-play-state: paused;
        }
      `}</style>

      <div className="relative w-full overflow-hidden rounded-xl mt-3" style={{ padding: "4px 0" }}>
        {/* Fade left */}
        <div
          className="pointer-events-none absolute top-0 left-0 bottom-0 z-10"
          style={{
            width: "40px",
            background: "linear-gradient(to right, rgba(10,10,10,0.95) 0%, transparent 100%)",
          }}
        />
        {/* Fade right */}
        <div
          className="pointer-events-none absolute top-0 right-0 bottom-0 z-10"
          style={{
            width: "40px",
            background: "linear-gradient(to left, rgba(10,10,10,0.95) 0%, transparent 100%)",
          }}
        />

        <div className="feedbacks-h-track flex flex-row gap-3 w-max">
          {items.map((f, i) => (
            <FeedbackCard key={`${f.id}-${i}`} feedback={f} />
          ))}
        </div>
      </div>
    </>
  );
}

// ─── FAQ ──────────────────────────────────────────────────────────────────────

export function FAQ() {
  return (
    <section className="mt-10">
      <div className="flex flex-col gap-4">
        <p className="text-2xl font-bold">Perguntas Frequentes</p>
        <Accordion
          className="bg-foreground/2 p-5 rounded-lg border border-foreground/10 border-dashed focus:outline-none"
          itemClasses={{ title: "text-foreground/90 cursor-pointer" }}
        >
          <AccordionItem key="1" aria-label="Accordion 1" title="Como faço para comprar o plano?" className="focus:outline-none text-sm text-foreground">
            <p>
              Após selecionar o plano desejado, clique no botão "Escolher plano" e siga as instruções para finalizar a compra. Um PIX no valor do plano será gerado e você poderá pagar com o QR Code ou copiando o código de pagamento.
            </p>
          </AccordionItem>
          <AccordionItem key="2" aria-label="Accordion 2" title="Como faço para configurar o bot após a compra?" className="focus:outline-none text-sm text-foreground">
            <p>
              Automáticamente após a compra, o serviço ficará disponível para a configuração na Dashboard. Antes de poder configurar o restante, você precisará informar o token do seu bot.
            </p>
          </AccordionItem>
          <AccordionItem key="3" aria-label="Accordion 3" title="Como faço para renovar o plano?" className="focus:outline-none text-sm text-foreground">
            <p>
              No painel de controle do seu serviço, você irá ver um botão de faturas. Lá, você poderá ver todas as faturas e renovações.
            </p>
          </AccordionItem>
          <AccordionItem key="4" aria-label="Accordion 4" title="É possível cancelar o plano?" className="focus:outline-none text-sm text-foreground">
            <p>
              Não, infelizmente não é possível cancelar o plano. Você poderá pedir reembolso caso tenha problemas com o serviço.
            </p>
          </AccordionItem>
          <AccordionItem
            key="5"
            aria-label="Accordion 5"
            title="O que os clientes acham do produto?"
            className="focus:outline-none text-sm text-foreground"
          >
            <FeedbacksCarousel />
          </AccordionItem>
        </Accordion>
      </div>
    </section>
  );
}
