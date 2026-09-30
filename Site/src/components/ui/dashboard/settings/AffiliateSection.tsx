"use client";

import { useState } from "react";
import {
  Copy,
  Check,
  Users,
  MousePointerClick,
  Gift,
  TrendingUp,
  ExternalLink,
  Clock,
  ChevronDown,
  ChevronUp,
  Zap,
} from "lucide-react";
import { useAffiliate } from "@/hooks/useAffiliate";

export default function AffiliateSection() {
  const { stats, loading, error } = useAffiliate();
  const [copied, setCopied] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const copyLink = async () => {
    if (!stats?.link) return;
    await navigator.clipboard.writeText(stats.link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-2 mt-2 md:w-full">
        <div className="flex flex-col gap-1">
          <span className="text-foreground/70 text-sm font-medium">Programa de Afiliados</span>
          <div className="bg-foreground/5 rounded-lg p-4 animate-pulse">
            <div className="h-4 w-48 bg-foreground/10 rounded mb-3" />
            <div className="h-10 w-full bg-foreground/10 rounded mb-3" />
            <div className="grid grid-cols-2 gap-2">
              <div className="h-16 bg-foreground/10 rounded" />
              <div className="h-16 bg-foreground/10 rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="flex flex-col gap-2 mt-2 md:w-full">
        <span className="text-foreground/70 text-sm font-medium">Programa de Afiliados</span>
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <p className="text-red-500 text-sm">Erro ao carregar dados de afiliado.</p>
        </div>
      </div>
    );
  }

  const conversionRate =
    stats.clicks > 0 ? ((stats.conversions / stats.clicks) * 100).toFixed(1) : "0.0";

  return (
    <div className="flex flex-col gap-2 mt-2 md:w-full">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-foreground/70 text-sm font-medium">Programa de Afiliados</span>
          <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
            BETA
          </span>
        </div>

        <div className="bg-foreground/5 border border-foreground/10 rounded-lg p-4 flex flex-col gap-4">
          {/* Explicação */}
          <div className="flex flex-col gap-1">
            <p className="text-foreground/80 text-sm font-medium">Como funciona?</p>
            <p className="text-foreground/60 text-xs leading-relaxed">
              Compartilhe seu link de convite. Quando alguém comprar um plano pelo seu link,
              você ganha <strong className="text-foreground/80">+1 dia</strong> de bot gratuito.
              Cada nova compra adiciona mais 1 dia — acumulando automaticamente!
            </p>
          </div>

          {/* Link de convite */}
          <div className="flex flex-col gap-1.5">
            <span className="text-foreground/70 text-xs font-medium">Seu link de convite</span>
            <div className="flex items-center gap-2">
              <div className="flex-1 flex items-center gap-2 bg-foreground/5 border border-foreground/10 rounded-lg px-3 py-2 min-w-0">
                <ExternalLink className="w-3.5 h-3.5 text-foreground/40 flex-shrink-0" />
                <span className="text-xs font-mono text-foreground/70 truncate">
                  {stats.link}
                </span>
              </div>
              <button
                onClick={copyLink}
                className="flex items-center gap-1.5 px-3 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-xs font-medium transition-colors flex-shrink-0"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    Copiado
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copiar
                  </>
                )}
              </button>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-foreground/40 text-[11px]">Código:</span>
              <span className="text-[11px] font-mono bg-foreground/10 px-2 py-0.5 rounded text-foreground/70 tracking-widest">
                {stats.code}
              </span>
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <StatCard
              icon={<MousePointerClick className="w-4 h-4" />}
              label="Acessos"
              value={stats.clicks.toLocaleString("pt-BR")}
              color="text-blue-400"
              bg="bg-blue-500/10"
              border="border-blue-500/20"
            />
            <StatCard
              icon={<Users className="w-4 h-4" />}
              label="Conversões"
              value={stats.conversions.toLocaleString("pt-BR")}
              color="text-green-400"
              bg="bg-green-500/10"
              border="border-green-500/20"
            />
            <StatCard
              icon={<TrendingUp className="w-4 h-4" />}
              label="Taxa"
              value={`${conversionRate}%`}
              color="text-purple-400"
              bg="bg-purple-500/10"
              border="border-purple-500/20"
            />
            <StatCard
              icon={<Gift className="w-4 h-4" />}
              label="Dias ganhos"
              value={stats.rewardDays.toLocaleString("pt-BR")}
              color="text-yellow-400"
              bg="bg-yellow-500/10"
              border="border-yellow-500/20"
            />
          </div>

          {/* Recompensa pendente */}
          {stats.pendingDays > 0 && (
            <div className="flex items-center gap-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
              <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                <Zap className="w-4 h-4 text-yellow-400" />
              </div>
              <div>
                <p className="text-yellow-400 text-sm font-semibold">
                  {stats.pendingDays} dia{stats.pendingDays !== 1 ? "s" : ""} de recompensa!
                </p>
                <p className="text-foreground/60 text-xs">
                  Um bot gratuito foi (ou será em breve) criado na sua conta.
                </p>
              </div>
            </div>
          )}

          {/* Bots de recompensa */}
          {stats.rewardApps.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="text-foreground/60 text-xs font-medium">Bots gerados como recompensa</span>
              <div className="flex flex-col gap-1">
                {stats.rewardApps.map((app, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-xs bg-foreground/5 border border-foreground/10 rounded-md px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <Gift className="w-3.5 h-3.5 text-yellow-400" />
                      <span className="text-foreground/70">Bot de Recompensa #{i + 1}</span>
                    </div>
                    <span className="text-foreground/50">
                      {app.days} dia{app.days !== 1 ? "s" : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Histórico de conversões */}
          {stats.conversionHistory.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-1 text-foreground/60 text-xs font-medium hover:text-foreground/80 transition-colors w-fit"
              >
                <Clock className="w-3.5 h-3.5" />
                Histórico de conversões ({stats.conversionHistory.length})
                {showHistory ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>

              {showHistory && (
                <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                  {stats.conversionHistory.map((c, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-xs bg-foreground/5 border border-foreground/10 rounded-md px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                        <span className="text-foreground/70">Compra realizada</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-green-400 font-medium">+{c.rewardDays} dia</span>
                        <span className="text-foreground/40">
                          {new Date(c.createdAt).toLocaleDateString("pt-BR")}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty state histórico */}
          {stats.conversions === 0 && (
            <div className="text-center py-2">
              <p className="text-foreground/40 text-xs">
                Nenhuma conversão ainda. Compartilhe seu link para começar!
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
  bg,
  border,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
  bg: string;
  border: string;
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${bg} border ${border} rounded-lg p-3`}>
      <div className={`${color}`}>{icon}</div>
      <div>
        <p className="text-foreground/90 text-base font-bold leading-none">{value}</p>
        <p className="text-foreground/50 text-[11px] mt-0.5">{label}</p>
      </div>
    </div>
  );
}