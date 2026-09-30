"use client";

import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrochip, faCircleExclamation, faEllipsisV, faPlay, faRotateRight, faPowerOff, faChartLine, faLock, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { Progress, Tooltip, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button, addToast, DropdownSection } from "@heroui/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppActions } from "@/features/dashboard/hooks/useAppActions";
import {
  calculateRemainingAndTotalDays,
  calculateRemainingProgressPercent,
} from "@/utils/apps";
import { getHostingStatusDisplay } from "@/lib/utils/status";
import { formatBrazilianDate, formatRemainingDays } from "@/lib/utils/dates";
import { CopyIconButton } from "@/components/ui/CopyIconButton";

type App = any;

interface AppCardProps {
  app: App;
}

export function AppCard({ app, onRefresh }: AppCardProps & { onRefresh?: () => void }) {
  const [actionLoading, setActionLoading] = useState<"start" | "stop" | "restart" | null>(null);
  const router = useRouter();

  const { remainingDays, totalDays } = calculateRemainingAndTotalDays(
    app?.expiresAt,
    app?.plan?.months
  );
  const statusDisplay = getHostingStatusDisplay(app?.hosting?.status);
  const normalizedStatus = (app?.hosting?.status || "").toString().trim().toLowerCase();
  const isRunning = ["running", "online", "on", "active"].includes(normalizedStatus);
  const isOffline = [
    "stopped",
    "offline",
    "off",
    "shutdown",
    "stopping",
    "erro",
    "error",
  ].includes(normalizedStatus);
  const botConfigured = app?.bot?.configured !== false;
  const serverConfigured = Boolean(app?.bot?.server);
  const canStartOrRestart = botConfigured && serverConfigured;
  const startDisabled = isRunning || actionLoading !== null || !canStartOrRestart;
  const restartDisabled = actionLoading !== null || !canStartOrRestart || isOffline;
  const stopDisabled = isOffline || actionLoading !== null;
  const { doAction } = useAppActions();

  // Use centralized action handler to avoid duplicated fetch/handling.
  async function handleAction(action: "start" | "stop" | "restart") {
    if (!app?._id) return;
    try {
      setActionLoading(action);
      const success = await doAction(app._id, action);
      
      // Se sucesso, inicia polling inteligente
      if (success && onRefresh) {
        // Polling inteligente: continua atualizando até status mudar
        let attempts = 0;
        const maxAttempts = 12; // 12 tentativas = ~60 segundos
        
        const pollInterval = setInterval(() => {
          attempts++;
          
          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            return;
          }
          
          onRefresh();
        }, 5000); // A cada 5 segundos
      }
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <Link
      key={app._id}
      href={`/dashboard/app/${app._id}`}
      className="cursor-pointer rounded-lg border border-foreground/10 bg-foreground/1 p-4 hover:border-foreground/15 transition-all duration-100"
    >
      <div className="flex flex-row justify-between items-start">
        <div className="flex flex-col items-start">
          <p className="text-sm font-medium leading-tight flex flex-row items-center gap-1">
            {app.name || app.appId || "Aplicação"}
            {app._id && (
              <CopyIconButton
                value={app._id}
                stopPropagation
                ariaLabel="Copiar ID"
                title="Copiar ID da aplicação"
                className="cursor-pointer rounded p-1 hover:bg-foreground/5 text-foreground/60 hover:text-foreground/90 flex items-center justify-center"
                iconClassName="text-[10px]"
              />
            )}
          </p>
          {app._id && (
            <span className="text-[10px] text-foreground/40 font-medium mt-0.5 select-all">
              {app._id}
            </span>
          )}
        </div>
        <div className="h-fit text-[11px] flex flex-row gap-1 items-center text-foreground/70 py-1 px-2 rounded-sm border border-foreground/10">
          {app.plan?.name || app.plan?.id}
        </div>
      </div>
      <hr className="my-2 border-foreground/10" />
      <div className="flex flex-col gap-1">
        {app.expiresAt && (
          <div className="flex flex-row gap-1 items-center justify-between text-xs text-foreground/70">
            <span>Expira: {formatBrazilianDate(app.expiresAt)}</span>
            <span>{formatRemainingDays(remainingDays)}</span>
          </div>
        )}
        <Progress value={calculateRemainingProgressPercent(app.expiresAt, app?.plan?.months)} size="sm" />
      </div>
      <div className="flex flex-row gap-1 mt-3">
        <div className="py-1 px-3 rounded-full border border-foreground/5 text-[11px] text-foreground/70 flex items-center justify-center gap-1.5">
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${statusDisplay.dotClass} ${statusDisplay.animated ? 'animate-pulse' : ''}`} />
          <span>{statusDisplay.label}</span>
        </div>
        {app?.bot?.configured === true && (
        <div className="py-1 px-3 rounded-full border border-foreground/5 text-[11px] text-foreground/70 flex items-center justify-center gap-1">
          <FontAwesomeIcon icon={faMicrochip} className="text-[10px] text-foreground/40" />
          <span>RAM: {app?.hosting?.utilizedRam ?? 0}MB</span>
        </div>
        )}
        {app?.bot?.configured === false && (
          <div
            className="py-1 px-3 rounded-full border border-red-500/20 bg-red-500/5 text-[11px] text-red-500 flex items-center justify-center gap-1"
            title="Bot não configurado"
            aria-label="Bot não configurado"
          >
            <FontAwesomeIcon icon={faCircleExclamation} className="text-[10px]" />
            <span>Não configurado</span>
          </div>
        )}
        {/* Quick actions dropdown - stop propagation to avoid Link navigation */}
        <div
          className="ml-auto"
          onClick={(e) => {
            e.stopPropagation();
          }}
          onMouseDown={(e) => {
            e.stopPropagation();
          }}
          onPointerDown={(e) => {
            e.stopPropagation();
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.stopPropagation();
            }
          }}
        >
          <Dropdown className="min-w-[220px] bg-background border border-foreground/10">
            <DropdownTrigger>
              <Button
                isIconOnly
                size="sm"
                variant="light"
                className="text-foreground/60"
                aria-label="Ações rápidas"
                // Prevent Link navigation when pressing the trigger inside a Link-wrapped card.
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onMouseDown={(e) => {
                  e.stopPropagation();
                }}
                onPointerDown={(e) => {
                  e.stopPropagation();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    e.stopPropagation();
                  }
                }}
              >
                <FontAwesomeIcon icon={faEllipsisV} />
              </Button>
            </DropdownTrigger>
            <DropdownMenu aria-label="Ações rápidas">
              <DropdownSection title="Navegar">
                <DropdownItem startContent={<FontAwesomeIcon icon={faExternalLinkAlt} className="text-[10px]" />} key="open" onPress={() => router.push(`/dashboard/app/${app._id}`)}>
                  Ir para a aplicação
                </DropdownItem>
                <DropdownItem startContent={<FontAwesomeIcon icon={faChartLine} className="text-[10px]" />} key="overview" onPress={() => router.push(`/dashboard/app/${app._id}/overview`)}>
                  Visão geral
                </DropdownItem>
                <DropdownItem startContent={<FontAwesomeIcon icon={faLock} className="text-[10px]" />} key="restricted" onPress={() => router.push(`/dashboard/app/${app._id}/restricted`)}>
                  Restrito
                </DropdownItem>
              </DropdownSection>
              <DropdownSection title="Ações">
                <DropdownItem
                  key="start"
                  startContent={<FontAwesomeIcon icon={faPlay} className="text-[10px]" />}
                  isDisabled={startDisabled}
                  onPress={() => handleAction("start")}
                  className="data-[disabled=true]:opacity-60"
                  title="Ligar"
                >
                  Ligar
                </DropdownItem>
                <DropdownItem
                  key="restart"
                  startContent={<FontAwesomeIcon icon={faRotateRight} className={`text-[10px] ${actionLoading === "restart" ? "animate-spin" : ""}`} />}
                  isDisabled={restartDisabled}
                  onPress={() => handleAction("restart")}
                  className="data-[disabled=true]:opacity-60"
                  title="Reiniciar"
                >
                  Reiniciar
                </DropdownItem>
                <DropdownItem
                  key="stop"
                  startContent={<FontAwesomeIcon icon={faPowerOff} className="text-[10px]" />}
                  isDisabled={stopDisabled}
                  onPress={() => handleAction("stop")}
                  className="text-danger data-[disabled=true]:opacity-60"
                  title="Desligar"
                >
                  Desligar
                </DropdownItem>
              </DropdownSection>
            </DropdownMenu>
          </Dropdown>
        </div>
      </div>
    </Link>
  );
}


