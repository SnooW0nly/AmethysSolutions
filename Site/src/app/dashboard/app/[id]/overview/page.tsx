"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAppInfo } from "@/hooks/useApp";
import { Loading } from "@/components/Loading";
import { BotServerSection } from "@/components/ui/dashboard/app/BotServerSection";
import { BotPermsSection } from "@/components/ui/dashboard/app/BotPermsSection";
import { BotOverviewSection } from "@/components/ui/dashboard/app/BotOverviewSection";
import ExpirationAlert from "@/components/ui/dashboard/app/ExpirationAlert";
import { useAppActions } from "@/features/dashboard/hooks/useAppActions";
import { actionBus } from "@/lib/events/actionBus";
import { BotOverviewSkeleton } from "@/components/ui/dashboard/app/skeletons/BotOverviewSkeleton";
import { ConfigCardSkeleton } from "@/components/ui/dashboard/app/skeletons/ConfigCardSkeleton";
import { BotCustomizationSection } from "@/components/ui/dashboard/app/BotCustomizationSection";
import { BotAuditLog } from "@/components/ui/dashboard/app/BotAuditLog";

export default function Overview() {
  const params = useParams<{ id: string }>();
  const id = params?.id as string | undefined;
  const { app, loading, refetch } = useAppInfo(id);
  const [actionLoading, setActionLoading] = useState<"start" | "stop" | "restart" | null>(null);
  const { doAction } = useAppActions();

  const handleUpdate = () => {
    if (!app?._id) return;
    const appId = app._id; // Captura appId
    
    // Atualiza imediatamente
    refetch();
    actionBus.emitRefetch(appId);
    
    // Atualiza novamente após 2s para pegar o status "restarting"
    setTimeout(() => {
      refetch();
      actionBus.emitRefetch(appId);
    }, 2000);
  };

  // Handle actions from overview (if any in the future) and emit to bus
  async function handleAction(action: "start" | "stop" | "restart") {
    if (!app?._id) return;
    const appId = app._id; // Captura appId antes do polling
    actionBus.emitActionStart(appId, action);
    setActionLoading(action);
    try {
      const ok = await doAction(appId, action);
      if (ok) {
        await refetch();
        actionBus.emitRefetch(appId);
        
        // Polling inteligente: continua atualizando até status mudar
        let attempts = 0;
        const maxAttempts = 12; // 12 tentativas = ~60 segundos
        
        const pollInterval = setInterval(() => {
          attempts++;
          
          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            return;
          }
          
          refetch();
          // Emite evento para sincronizar com layout/sidebar
          console.log('[Overview] Emitindo evento de refetch no polling...');
          actionBus.emitRefetch(appId);
        }, 5000); // A cada 5 segundos
      }
    } finally {
      setActionLoading(null);
      actionBus.emitActionEnd(appId, action);
    }
  }

  // Listen to global action events to keep labels and buttons in sync
  useEffect(() => {
    if (!app?._id) return;
    const appId = app._id;
    const onStart = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === appId) {
        setActionLoading(detail.action || "restart");
      }
    };
    const onEnd = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === appId) {
        setActionLoading(null);
      }
    };
    const onRefetch = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.appId === appId) {
        refetch();
      }
    };
    actionBus.addEventListener("app-action-start", onStart);
    actionBus.addEventListener("app-action-end", onEnd);
    actionBus.addEventListener("app-refetch", onRefetch);
    return () => {
      actionBus.removeEventListener("app-action-start", onStart);
      actionBus.removeEventListener("app-action-end", onEnd);
      actionBus.removeEventListener("app-refetch", onRefetch);
    };
  }, [app?._id, refetch]);

  if (loading) {
    return (
      <main className="p-6 md:px-12 flex flex-col gap-5 min-h-screen">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <div className="h-8 bg-foreground/10 rounded w-64 animate-pulse" />
            <div className="h-4 bg-foreground/10 rounded w-96 animate-pulse" />
          </div>
          <hr className="border-foreground/10 mt-2" />
        </div>
        
        {/* Skeleton Loading */}
        <BotOverviewSkeleton />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ConfigCardSkeleton />
          <ConfigCardSkeleton />
        </div>
      </main>
    );
  }
  
  // Verifica se app tem dados mínimos necessários
  if (!app || !app._id || app.bot === undefined) {
    return (
      <main className="p-6 md:px-12 flex flex-col gap-5 min-h-screen">
        <div className="flex flex-col">
          <p className="text-2xl font-bold">Visão Geral</p>
          <p className="text-foreground/60 text-sm">
            Gerencie as configurações da aplicação e usuários autorizados
          </p>
          <hr className="border-foreground/10 mt-4" />
        </div>
        
        {/* Skeleton Loading */}
        <BotOverviewSkeleton />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ConfigCardSkeleton />
          <ConfigCardSkeleton />
        </div>
      </main>
    );
  }

  return (
    <main className="p-6 md:px-12 flex flex-col gap-5 min-h-screen">
      <div className="flex flex-col">
        <p className="text-2xl font-bold">Visão Geral</p>
        <p className="text-foreground/60 text-sm">
          Gerencie as configurações da aplicação e usuários autorizados
        </p>
        <hr className="border-foreground/10 mt-4" />
      </div>
      {/* Alerta de expiração/bloqueio */}
      <ExpirationAlert app={app as any} />

      <BotOverviewSection app={app} />
      
      {/* Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Servidor Principal */}
        <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full">
          <BotServerSection 
            appId={app._id}
            botId={app.bot?.id || null}
            currentServer={app.bot?.server || null}
            tokenConfigured={app.bot?.configured || false}
            onUpdate={handleUpdate} 
          />
        </div>

        {/* Permissões */}
        <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full">
          <BotPermsSection 
            appId={app._id} 
            currentPerms={app.bot?.perms || []} 
            currentOwner={app.bot?.owner || null}
            serverConfigured={Boolean(app.bot?.server)}
            tokenConfigured={app.bot?.configured || false}
            onUpdate={handleUpdate} 
          />
        </div>
      </div>

      <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full">
        <BotAuditLog />
      </div>
    </main>
  );
}

