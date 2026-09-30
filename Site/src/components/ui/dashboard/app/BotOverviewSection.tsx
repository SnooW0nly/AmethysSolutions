"use client";

import { CopyIconButton } from "@/components/ui/CopyIconButton";
import { formatBrazilianDate, formatSince } from "@/lib/utils/dates";
import type { AppInfo } from "@/types/app";
import { formatRemainingDays } from "@/lib/utils/dates";
import { calculateRemainingAndTotalDays, calculateRemainingProgressPercent } from "@/utils/apps";
import { Progress } from "@heroui/react";
import Link from "next/link";
import { getHostingStatusDisplay } from "@/lib/utils/status";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleExclamation, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { ActionButtons } from "./sidebar/ActionButtons";

interface BotOverviewSectionProps {
  app: AppInfo;
}

export function BotOverviewSection({ app }: BotOverviewSectionProps) {
    const { remainingDays } = calculateRemainingAndTotalDays(app?.expiresAt || undefined, app?.plan?.months || undefined);
    const utilizedRamMb = typeof app?.hosting?.utilizedRam === "number" ? app.hosting.utilizedRam : 0;
    const ramPercent = Math.max(0, Math.min(100, Math.round((utilizedRamMb / 200) * 100)));
    const statusDisplay = getHostingStatusDisplay(app?.hosting?.status);
    const normalizedStatus = (app?.hosting?.status || "").toString().trim().toLowerCase();
    const isRunning = ["running", "online", "on", "active"].includes(normalizedStatus);
    const uptime = isRunning && app?.hosting?.startedAt ? formatSince(app.hosting.startedAt) : "";
    return (
        <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full">
            <div className="flex flex-col lg:flex-row lg:justify-between items-center w-full">
                <div className="flex flex-col w-full">
                    <div className="flex flex-row items-center gap-2">
                        <h1 className="text-foreground font-bold text-xl">{app.name || "Amethys Pro"}</h1>
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
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                        <p className="text-foreground/60 text-[12px]">
                            {app.plan?.name || app.plan?.id}
                        </p>
                        <p className="text-foreground/60 text-[12px]">•</p>
                        <p className="text-foreground/60 text-[12px] select-all">{app._id || "N/A"}</p>
                        <CopyIconButton
                            value={app._id || ""}
                            className="text-foreground/60 text-[10px] cursor-pointer hover:text-foreground/80 transition-all duration-100"
                        />
                    </div>
                </div>
                <div className="flex flex-col lg:flex-row lg:flex-wrap gap-2 lg:gap-2 mt-3 lg:mt-0 w-full lg:justify-end">
                    <div className="bg-foreground/1 border border-foreground/2 rounded-lg p-2 h-fit w-full lg:flex-1 lg:min-w-[240px] lg:max-w-[300px]">
                        <div className="flex flex-col gap-1">
                            {app.expiresAt && (
                                <div className="flex flex-row gap-10 items-center justify-between text-xs text-foreground/70">
                                    <span>Expira: {formatBrazilianDate(app.expiresAt)}</span>
                                    <span>{formatRemainingDays(remainingDays)}</span>
                                </div>
                            )}
                            <Progress value={calculateRemainingProgressPercent(app.expiresAt || undefined, app?.plan?.months)} size="sm" />
                        </div>
                    </div>
                    <div className="bg-foreground/1 border border-foreground/2 rounded-lg p-2 h-fit w-full lg:flex-1 lg:min-w-[240px] lg:max-w-[300px]">
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-row gap-10 items-center justify-between text-xs text-foreground/70">
                                <span>RAM:</span>
                                <span>{utilizedRamMb}/200MB</span>
                            </div>
                            <Progress value={ramPercent} size="sm" />
                        </div>
                    </div>
                </div>
            </div>
            <hr className="my-2 border-foreground/4" />
            <div className="flex flex-row items-center w-full gap-2">
                <div className="flex flex-row items-center gap-2">
                    <div className="flex items-center gap-1 text-[12px] bg-foreground/5 border border-foreground/10 rounded-lg px-3 py-1">
                        <span
                            className={`inline-block w-2 h-2 rounded-full ${statusDisplay.dotClass} ${statusDisplay.animated ? 'animate-pulse' : ''}`}
                            aria-hidden="true"
                        />
                        <span className="text-foreground">
                            {statusDisplay.label}
                        </span>
                    </div>
                </div>
                <div className="flex w-full justify-end">
                    {isRunning && uptime ? (
                        <p className="text-foreground/60 text-[12px]">
                            {`Online há ${uptime}`}
                        </p>
                    ) : (
                        <Link href={`/tutorials`} className="text-foreground/60 text-[12px] flex flex-row items-center gap-1 w-fit">Veja como configurar o bot <FontAwesomeIcon className="text-[10px]" icon={faExternalLinkAlt} /></Link>
                    )}
                </div>
            </div>
        </div>
    )
}
