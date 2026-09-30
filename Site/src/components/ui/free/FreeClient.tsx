"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Chip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faGift,
  faRobot,
  faShieldHalved,
  faCircleCheck,
  faTriangleExclamation,
  faCircleXmark,
  faArrowRight,
  faClock,
  faCalendarDays,
  faSpinner,
  faBoxOpen,
} from "@fortawesome/free-solid-svg-icons";

// ─── Tipos ────────────────────────────────────────────────────────────────────

type CheckData = {
  canCreate: boolean;
  existingCount: number;
  accountAge: { ok: boolean; ageDays: number; required: number; createdAt: string };
  risk: { score: number; blocked: boolean; reasons: string[] };
  config: { durationDays: number; sourcePlanId: string } | null;
};

type RedeemResult = {
  applicationId: string;
  name: string;
  plan: { name: string };
  hosting: { status: string };
  expiresAt: string | null;
};

type Phase =
  | { type: "loading-check" }
  | { type: "error-check"; message: string }
  | { type: "blocked"; reason: "already-redeemed" | "account-too-new" | "risk" | "unavailable"; detail: string }
  | { type: "confirm"; check: CheckData }
  | { type: "redeeming" }
  | { type: "success"; result: RedeemResult; durationDays: number | null }
  | { type: "error-redeem"; message: string };

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
}

// ─── Sub-componentes ──────────────────────────────────────────────────────────

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-[70vh] flex items-center justify-center py-10 px-4">
      <div className="w-full max-w-lg">{children}</div>
    </main>
  );
}

function LoadingCheck() {
  return (
    <Shell>
      <div className="flex flex-col items-center gap-4 py-16 text-foreground/40">
        <FontAwesomeIcon icon={faSpinner} className="text-3xl animate-spin" />
        <p className="text-sm">Verificando elegibilidade…</p>
      </div>
    </Shell>
  );
}

function BlockedView({ phase }: { phase: Extract<Phase, { type: "blocked" }> }) {
  const router = useRouter();

  const icons = {
    "already-redeemed": faBoxOpen,
    "account-too-new": faCalendarDays,
    "risk": faShieldHalved,
    "unavailable": faCircleXmark,
  };

  const colors = {
    "already-redeemed": "text-primary",
    "account-too-new": "text-warning-500",
    "risk": "text-danger-500",
    "unavailable": "text-foreground/40",
  };

  return (
    <Shell>
      <div className="rounded-2xl border border-foreground/10 bg-foreground/2 p-8 flex flex-col items-center gap-5 text-center">
        <div className={`text-4xl ${colors[phase.reason]}`}>
          <FontAwesomeIcon icon={icons[phase.reason]} />
        </div>
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-bold">
            {phase.reason === "already-redeemed" && "Plano já resgatado"}
            {phase.reason === "account-too-new" && "Conta muito recente"}
            {phase.reason === "risk" && "Verificação não passou"}
            {phase.reason === "unavailable" && "Indisponível no momento"}
          </h2>
          <p className="text-sm text-foreground/60 leading-relaxed">{phase.detail}</p>
        </div>
        <div className="flex flex-col gap-2 w-full">
          {phase.reason === "already-redeemed" && (
            <Button color="primary" onPress={() => router.push("/dashboard")}>
              Ir para a Dashboard
            </Button>
          )}
          <Button variant="bordered" onPress={() => router.push("/pricing")}>
            Ver planos pagos
          </Button>
        </div>
      </div>
    </Shell>
  );
}

function ConfirmView({
  phase,
  onConfirm,
  loading,
}: {
  phase: Extract<Phase, { type: "confirm" }>;
  onConfirm: () => void;
  loading: boolean;
}) {
  const { check } = phase;
  const days = check.config?.durationDays ?? null;

  return (
    <Shell>
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-success-500 mb-1">
            <FontAwesomeIcon icon={faGift} className="text-lg" />
            <span className="text-xs uppercase tracking-widest font-semibold">Teste gratuito</span>
          </div>
          <h1 className="text-3xl font-bold leading-tight">
            Seu bot grátis,<br />sem cartão.
          </h1>
          <p className="text-foreground/60 text-sm mt-1">
            Resgate uma vez e experimente a plataforma completa.
            {days ? ` Válido por ${days} dias.` : " Sem expiração."}
          </p>
        </div>

        {/* Card do que vem incluso */}
        <div className="rounded-2xl border border-foreground/10 bg-foreground/2 p-5 flex flex-col gap-4">
          <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold">O que está incluso</p>
          <div className="flex flex-col gap-3">
            {[
              { icon: faRobot, text: "Bot Discord completo com todas as funcionalidades" },
              { icon: faClock, text: days ? `Acesso por ${days} dias sem cobrança` : "Acesso sem expiração" },
              { icon: faCircleCheck, text: "Deploy automático — já sobe pronto após resgatar" },
              { icon: faShieldHalved, text: "Suporte incluído durante o período" },
            ].map(({ icon, text }, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-success/10 flex items-center justify-center shrink-0">
                  <FontAwesomeIcon icon={icon} className="text-success-500 text-xs" />
                </div>
                <p className="text-sm text-foreground/80">{text}</p>
              </div>
            ))}
          </div>

          <hr className="border-foreground/10" />

          {/* Status da conta */}
          <div className="flex flex-col gap-2">
            <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold">Sua conta</p>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground/70">Idade da conta Discord</span>
              <Chip
                size="sm"
                color={check.accountAge.ok ? "success" : "warning"}
                variant="flat"
                className="text-[11px]"
              >
                {check.accountAge.ageDays} dias
              </Chip>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground/70">Verificação de segurança</span>
              <Chip
                size="sm"
                color={check.risk.blocked ? "danger" : "success"}
                variant="flat"
                className="text-[11px]"
              >
                {check.risk.blocked ? "Atenção" : "Aprovada"}
              </Chip>
            </div>
          </div>
        </div>

        {/* Aviso de limite */}
        <div className="rounded-xl border border-warning/20 bg-warning/5 p-3 flex items-start gap-2">
          <FontAwesomeIcon icon={faTriangleExclamation} className="text-warning-500 text-sm mt-0.5 shrink-0" />
          <p className="text-xs text-foreground/60 leading-relaxed">
            O teste gratuito é permitido <span className="font-semibold text-foreground/80">uma única vez por conta</span>.
            Após resgatar não é possível desfazer.
          </p>
        </div>

        {/* CTA */}
        <Button
          color="success"
          size="lg"
          className="w-full font-semibold text-white"
          isLoading={loading}
          endContent={!loading && <FontAwesomeIcon icon={faArrowRight} className="text-sm" />}
          onPress={onConfirm}
        >
          Resgatar bot gratuito
        </Button>

        <p className="text-center text-xs text-foreground/30">
          Sem renovação automática · Sem cobrança
        </p>
      </div>
    </Shell>
  );
}

function RedeemingView() {
  return (
    <Shell>
      <div className="flex flex-col items-center gap-6 py-16 text-center">
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-success/10 flex items-center justify-center">
            <FontAwesomeIcon icon={faRobot} className="text-success-500 text-2xl" />
          </div>
          <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-success/20 flex items-center justify-center">
            <FontAwesomeIcon icon={faSpinner} className="text-success-500 text-[10px] animate-spin" />
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-bold">Criando seu bot…</h2>
          <p className="text-sm text-foreground/50">Fazendo deploy, pode levar alguns segundos.</p>
        </div>
        <div className="flex flex-col gap-1.5 w-full max-w-xs text-xs text-foreground/30">
          {["Verificando conta", "Alocando servidor", "Fazendo deploy"].map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-success/40" />
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}

function SuccessView({ phase }: { phase: Extract<Phase, { type: "success" }> }) {
  const router = useRouter();
  const { result, durationDays } = phase;

  return (
    <Shell>
      <div className="flex flex-col gap-5">
        {/* Header animado */}
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <div className="relative">
            <div className="w-20 h-20 rounded-3xl bg-success/10 border border-success/20 flex items-center justify-center">
              <FontAwesomeIcon icon={faRobot} className="text-success-400 text-3xl" />
            </div>
            <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-success flex items-center justify-center border-2 border-background">
              <FontAwesomeIcon icon={faCircleCheck} className="text-white text-sm" />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold">Bot criado com sucesso!</h1>
            <p className="text-sm text-foreground/50">
              {result.hosting.status === "deploying"
                ? "Seu bot está sendo implantado. Estará pronto em instantes."
                : "Seu bot já está online e pronto para configurar."}
            </p>
          </div>
        </div>

        {/* Detalhes */}
        <div className="rounded-2xl border border-foreground/10 bg-foreground/2 overflow-hidden">
          <div className="p-4 border-b border-foreground/10">
            <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold">Detalhes do plano</p>
          </div>
          <div className="flex flex-col divide-y divide-foreground/5">
            <Row label="Nome" value={result.name} />
            <Row label="Plano" value={result.plan.name} />
            <Row
              label="Status"
              value={
                <Chip
                  size="sm"
                  color={result.hosting.status === "online" ? "success" : "warning"}
                  variant="flat"
                  className="text-[11px]"
                >
                  {result.hosting.status === "online" ? "Online" : "Implantando"}
                </Chip>
              }
            />
            {result.expiresAt && (
              <Row label="Expira em" value={formatDate(result.expiresAt)} />
            )}
            {!result.expiresAt && (
              <Row label="Validade" value="Sem expiração" />
            )}
            {durationDays && (
              <Row label="Duração" value={`${durationDays} dias`} />
            )}
          </div>
        </div>

        {/* Próximo passo */}
        <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex gap-3">
          <FontAwesomeIcon icon={faCircleCheck} className="text-primary text-sm mt-0.5 shrink-0" />
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-semibold text-foreground/90">Próximo passo</p>
            <p className="text-xs text-foreground/55 leading-relaxed">
              Acesse a Dashboard, selecione seu bot e adicione o token para começar a usar.
            </p>
          </div>
        </div>

        <Button
          color="primary"
          size="lg"
          className="w-full font-semibold"
          endContent={<FontAwesomeIcon icon={faArrowRight} />}
          onPress={() => router.push("/dashboard")}
        >
          Ir para a Dashboard
        </Button>
      </div>
    </Shell>
  );
}

function RedeemErrorView({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  const router = useRouter();
  return (
    <Shell>
      <div className="rounded-2xl border border-danger/20 bg-danger/5 p-8 flex flex-col items-center gap-5 text-center">
        <FontAwesomeIcon icon={faCircleXmark} className="text-danger-400 text-4xl" />
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-bold">Erro ao resgatar</h2>
          <p className="text-sm text-foreground/60 leading-relaxed">{message}</p>
        </div>
        <div className="flex gap-2 w-full">
          <Button variant="bordered" className="flex-1" onPress={() => router.push("/pricing")}>
            Ver planos
          </Button>
          <Button color="primary" className="flex-1" onPress={onRetry}>
            Tentar novamente
          </Button>
        </div>
      </div>
    </Shell>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-sm text-foreground/50">{label}</span>
      <span className="text-sm font-medium text-foreground/90">{value}</span>
    </div>
  );
}

// ─── FreeClient principal ─────────────────────────────────────────────────────

export function FreeClient() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ type: "loading-check" });

  async function runCheck() {
    setPhase({ type: "loading-check" });
    try {
      const res = await fetch("/api/apps/free/check", { credentials: "include" });
      if (res.status === 401) {
        router.push("/login?redirect=/free");
        return;
      }
      const data: CheckData & { success: boolean; error?: string } = await res.json();

      if (!data.success) {
        setPhase({ type: "error-check", message: data.error || "Erro ao verificar elegibilidade." });
        return;
      }

      // Já resgatou
      if (!data.canCreate || data.existingCount > 0) {
        setPhase({
          type: "blocked",
          reason: "already-redeemed",
          detail: "Você já resgatou seu bot gratuito. Cada conta tem direito a apenas 1 resgate.",
        });
        return;
      }

      // Conta muito nova
      if (!data.accountAge.ok) {
        setPhase({
          type: "blocked",
          reason: "account-too-new",
          detail: `Sua conta Discord tem ${data.accountAge.ageDays} dia(s), mas precisa ter pelo menos ${data.accountAge.required} dias para resgatar.`,
        });
        return;
      }

      // Risco bloqueado
      if (data.risk.blocked) {
        setPhase({
          type: "blocked",
          reason: "risk",
          detail: "Detectamos o uso de VPN, proxy ou múltiplas contas no mesmo IP. Desative e tente novamente.",
        });
        return;
      }

      // Config inativa / indisponível
      if (!data.config) {
        setPhase({
          type: "blocked",
          reason: "unavailable",
          detail: "O plano gratuito não está disponível no momento. Tente mais tarde.",
        });
        return;
      }

      setPhase({ type: "confirm", check: data });
    } catch {
      setPhase({ type: "error-check", message: "Não foi possível verificar sua conta. Tente novamente." });
    }
  }

  async function handleRedeem() {
    if (phase.type !== "confirm") return;
    const durationDays = phase.check.config?.durationDays ?? null;

    setPhase({ type: "redeeming" });
    try {
      const res = await fetch("/api/apps/free", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        const msg = data.message || data.error || "Erro ao criar bot gratuito.";

        // Erros específicos com tela de bloqueio
        if (
          msg.includes("já resgatou") ||
          msg.includes("Limite") ||
          msg.includes("já possui")
        ) {
          setPhase({ type: "blocked", reason: "already-redeemed", detail: msg });
          return;
        }
        if (msg.includes("Conta muito nova") || msg.includes("Discord precisa ter")) {
          setPhase({ type: "blocked", reason: "account-too-new", detail: msg });
          return;
        }
        if (msg.includes("VPN") || msg.includes("segurança")) {
          setPhase({ type: "blocked", reason: "risk", detail: msg });
          return;
        }

        setPhase({ type: "error-redeem", message: msg });
        return;
      }

      setPhase({ type: "success", result: data.data, durationDays });
    } catch {
      setPhase({ type: "error-redeem", message: "Erro de conexão. Verifique sua internet e tente novamente." });
    }
  }

  // Executa o check ao montar
  useEffect(() => {
    runCheck();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (phase.type === "loading-check") return <LoadingCheck />;
  if (phase.type === "error-check")
    return (
      <Shell>
        <div className="rounded-2xl border border-danger/20 bg-danger/5 p-8 flex flex-col items-center gap-5 text-center">
          <FontAwesomeIcon icon={faCircleXmark} className="text-danger-400 text-4xl" />
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-bold">Não foi possível verificar</h2>
            <p className="text-sm text-foreground/60">{phase.message}</p>
          </div>
          <Button color="primary" onPress={runCheck}>Tentar novamente</Button>
        </div>
      </Shell>
    );
  if (phase.type === "blocked") return <BlockedView phase={phase} />;
  if (phase.type === "confirm")
    return (
      <ConfirmView
        phase={phase}
        onConfirm={handleRedeem}
        loading={false}
      />
    );
  if (phase.type === "redeeming") return <RedeemingView />;
  if (phase.type === "success") return <SuccessView phase={phase} />;
  if (phase.type === "error-redeem")
    return <RedeemErrorView message={phase.message} onRetry={runCheck} />;

  return null;
}