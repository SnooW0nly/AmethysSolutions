"use client";

import { Sidebar } from "@/components/ui/dashboard/app/sidebar/Sidebar";
import { Topbar } from "@/components/ui/dashboard/app/Topbar";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useAppInfo } from "@/hooks/useApp";
import NotFound from "@/app/not-found";
import { actionBus } from "@/lib/events/actionBus";
import { ActionOverlay } from "@/components/ui/dashboard/app/ActionOverlay";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const params = useParams<{ id: string }>();
  const id = params?.id as string | undefined;
  const { app, loading, refetch } = useAppInfo(id);
  const [overlayVisible, setOverlayVisible] = useState(false);
  const [overlayAction, setOverlayAction] = useState<"start" | "stop" | "restart" | null>(null);
  const [overlayTimer, setOverlayTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  // Sincroniza com eventos globais de refetch
  useEffect(() => {
    if (!app?._id) return;
    const appId = app._id;
    
    const onRefetch = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === appId) {
        console.log('[Layout] Recebeu evento de refetch, atualizando sidebar...');
        refetch();
      }
    };
    
    actionBus.addEventListener("app-refetch", onRefetch);
    return () => {
      actionBus.removeEventListener("app-refetch", onRefetch);
    };
  }, [app?._id, refetch]);

  // Ouve início de ações globais (start/stop/restart) para exibir overlay por 5s
  useEffect(() => {
    if (!app?._id) return;
    const appId = app._id;

    const onActionStart = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === appId) {
        const act = (detail.action || "restart") as "start" | "stop" | "restart";
        setOverlayAction(act);
        setOverlayVisible(true);
        // Limpa timers anteriores
        if (overlayTimer) clearTimeout(overlayTimer);
        // Exibe por 5 segundos e então fecha
        const timer = setTimeout(() => {
          setOverlayVisible(false);
          setOverlayAction(null);
          refetch();
        }, 5000);
        setOverlayTimer(timer);
      }
    };

    actionBus.addEventListener("app-action-start", onActionStart);
    return () => {
      actionBus.removeEventListener("app-action-start", onActionStart);
      if (overlayTimer) clearTimeout(overlayTimer);
    };
  }, [app?._id, refetch, overlayTimer]);

  if (loading) {
    return (
      <div className="h-screen overflow-hidden flex flex-col items-center justify-center">
        <img src="/amethys.png" width={80} height={80} className="animate-pulse [animation-duration:3s]" />
        <p className="text-foreground/50 text-sm">Carregando informações</p>
      </div>
    );
  }

  if (!app) {
    return <NotFound />;
  }

  return (
    <div className="flex h-screen overflow-hidden flex-col">
      <Topbar onOpenSidebar={() => setIsSidebarOpen(true)} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} app={app} onRefresh={refetch} />
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
        <ActionOverlay
          visible={overlayVisible}
          action={overlayAction}
        />
      </div>
    </div>
  );
}


