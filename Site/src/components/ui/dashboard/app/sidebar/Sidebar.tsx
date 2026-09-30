"use client";

import { useEffect, useState } from "react";
import { addToast } from "@heroui/react";
import { useRouter } from "next/navigation";
import { getHostingStatusDisplay } from "@/lib/utils/status";
import { DesktopPanel } from "./DesktopPanel";
import { MobileDrawer } from "./MobileDrawer";
import { useAppActions } from "@/features/dashboard/hooks/useAppActions";
import { actionBus } from "@/lib/events/actionBus";

type SidebarProps = {
  isOpen?: boolean;
  onClose?: () => void;
  app?: any;
  onRefresh?: () => void | Promise<void>;
};

export function Sidebar({ isOpen = false, onClose, app, onRefresh }: SidebarProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<"start" | "stop" | "restart" | null>(null);
  const [apps, setApps] = useState<any[] | null>(null);
  const [appsLoading, setAppsLoading] = useState(false);
  const router = useRouter();
  const { doAction } = useAppActions();

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

  async function handleAction(action: "start" | "stop" | "restart") {
    if (!app?._id) return;
    actionBus.emitActionStart(app._id, action);
    setActionLoading(action);
    try {
      const ok = await doAction(app._id, action);
      if (ok && typeof onRefresh === "function") {
        await onRefresh();
        actionBus.emitRefetch(app._id);
        
        // Polling inteligente: continua atualizando até status mudar
        let attempts = 0;
        const maxAttempts = 12; // 12 tentativas = ~60 segundos
        
        const pollInterval = setInterval(async () => {
          attempts++;
          
          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            return;
          }
          
          if (typeof onRefresh === "function") {
            await onRefresh();
          }
        }, 5000); // A cada 5 segundos
      }
    } finally {
      setActionLoading(null);
      actionBus.emitActionEnd(app._id, action);
    }
  }

  const handleCopyId = () => {
    if (!app?._id) return;
    navigator.clipboard.writeText(app._id);
    setCopiedId(app._id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  useEffect(() => {
    let aborted = false;
    (async () => {
      try {
        setAppsLoading(true);
        const res = await fetch("/api/apps", { cache: "no-store" });
        const json = await res.json();
        if (!aborted) setApps(json.applications || []);
      } catch {
        if (!aborted) setApps([]);
      } finally {
        if (!aborted) setAppsLoading(false);
      }
    })();
    return () => {
      aborted = true;
    };
  }, []);

  // Listen to global action events to sync button disabled state
  useEffect(() => {
    if (!app?._id) return;
    const id = app._id;
    const onStart = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === id) {
        setActionLoading(detail.action || "restart");
      }
    };
    const onEnd = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === id) {
        setActionLoading(null);
      }
    };
    actionBus.addEventListener("app-action-start", onStart);
    actionBus.addEventListener("app-action-end", onEnd);
    return () => {
      actionBus.removeEventListener("app-action-start", onStart);
      actionBus.removeEventListener("app-action-end", onEnd);
    };
  }, [app?._id]);

  const handleSelectApp = (id: string) => {
    router.push(`/dashboard/app/${id}`);
  };

  return (
    <>
      <DesktopPanel
        name={app?.name}
        fallbackName={app?.appId}
        appId={app?._id}
        copied={copiedId === app?._id}
        onCopy={handleCopyId}
        apps={apps}
        appsLoading={appsLoading}
        onSelectApp={handleSelectApp}
        statusDisplay={statusDisplay}
        utilizedRam={app?.hosting?.utilizedRam}
        isRunning={isRunning}
        isOffline={isOffline}
        actionLoading={actionLoading}
        onAction={handleAction}
        botConfigured={app?.bot?.configured}
        serverConfigured={Boolean(app?.bot?.server)}
        expiresAt={app?.expiresAt}
        planMonths={app?.plan?.months}
      />

      <MobileDrawer
        isOpen={!!isOpen}
        onClose={onClose}
        name={app?.name}
        fallbackName={app?.appId}
        appId={app?._id}
        copied={copiedId === app?._id}
        onCopy={handleCopyId}
        apps={apps}
        appsLoading={appsLoading}
        onSelectApp={handleSelectApp}
        statusDisplay={statusDisplay}
        utilizedRam={app?.hosting?.utilizedRam}
        isRunning={isRunning}
        isOffline={isOffline}
        actionLoading={actionLoading}
        onAction={handleAction}
        botConfigured={app?.bot?.configured}
        serverConfigured={Boolean(app?.bot?.server)}
        expiresAt={app?.expiresAt}
        planMonths={app?.plan?.months}
      />
    </>
  );
}


