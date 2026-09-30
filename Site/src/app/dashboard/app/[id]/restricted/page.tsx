"use client";

import { useParams, useRouter } from "next/navigation";
import { useAppInfo } from "@/hooks/useApp";
import { Loading } from "@/components/Loading";
import { BotTokenSection } from "@/components/ui/dashboard/app/BotTokenSection";
import { BotOwnerSection } from "@/components/ui/dashboard/app/BotOwnerSection";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft, faLock } from "@fortawesome/free-solid-svg-icons";
import Link from "next/link";
import { ConfigCardSkeleton } from "@/components/ui/dashboard/app/skeletons/ConfigCardSkeleton";

export default function RestrictedPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id as string | undefined;
  const { app, loading, refetch } = useAppInfo(id);

  const handleUpdate = () => {
    refetch();
  };

  if (loading) {
    return (
      <main className="p-6 md:p-12 flex flex-col gap-8 min-h-screen">
        {/* Header */}
        <div className="flex flex-col gap-3">
          <div className="h-4 bg-foreground/10 rounded w-40 animate-pulse" />
          <div className="flex flex-col gap-2">
            <div className="h-8 bg-foreground/10 rounded w-64 animate-pulse" />
            <div className="h-4 bg-foreground/10 rounded w-96 animate-pulse" />
          </div>
          <hr className="border-foreground/10 mt-2" />
        </div>

        {/* Skeleton Cards */}
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
      <main className="p-6 md:p-12 flex flex-col gap-8 min-h-screen">
        {/* Header */}
        <div className="flex flex-col gap-3">
          <div className="h-4 bg-foreground/10 rounded w-40 animate-pulse" />
          <div className="flex flex-col gap-2">
            <div className="h-8 bg-foreground/10 rounded w-64 animate-pulse" />
            <div className="h-4 bg-foreground/10 rounded w-96 animate-pulse" />
          </div>
          <div className="rounded-xl bg-danger/5 border border-danger/20 p-6">
            <div className="flex items-start gap-3">
              <FontAwesomeIcon icon={faLock} className="text-danger mt-1" />
              <div className="flex-1">
                <p className="font-semibold text-danger mb-1">Área Restrita</p>
                <p className="text-sm text-foreground/70">
                  As configurações nesta página são sensíveis e podem afetar o funcionamento do bot. 
                  Tenha cuidado ao fazer alterações.
                </p>
              </div>
            </div>
          </div>
          <hr className="border-foreground/10 mt-2" />
        </div>

        {/* Skeleton Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ConfigCardSkeleton />
          <ConfigCardSkeleton />
        </div>
      </main>
    );
  }
  
  if (app?.permissions && app.permissions.canAccessRestricted === false) {
    router.push(`/dashboard/app/${app._id}/overview`);
    return null;
  }

  return (
    <main className="p-6 md:p-12 flex flex-col gap-8 min-h-screen">
      {/* Header */}
      <div className="flex flex-col gap-3">
        <Link className="text-foreground/60 text-[12px] flex flex-row items-center gap-1 w-fit" href={`/dashboard/app/${app._id}/overview`}><FontAwesomeIcon className="text-[11px]" icon={faArrowLeft} /> Voltar para a visão geral</Link>
        <div className="flex flex-col">
          <p className="text-2xl font-bold">Configurações Restritas</p>
          <p className="text-foreground/60 text-sm">
            Gerencie informações sensíveis da aplicação
          </p>
        </div>
      {/* Warning */}
      <div className="rounded-xl bg-danger/5 border border-danger/20 p-6">
        <div className="flex items-start gap-3">
          <FontAwesomeIcon icon={faLock} className="text-danger mt-1" />
          <div>
            <p className="font-semibold text-danger mb-1">Área Restrita</p>
            <p className="text-sm text-foreground/70">
              As configurações nesta página são sensíveis e podem afetar o funcionamento do bot. 
              Tenha cuidado ao fazer alterações.
            </p>
          </div>
        </div>
      </div>
        <hr className="border-foreground/10 mt-2" />
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Token do Bot */}
        <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full">
          <BotTokenSection 
            appId={app._id} 
            botId={app.bot?.id || null} 
            onUpdate={handleUpdate} 
          />
        </div>

        {/* Owner do Bot */}
        <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full">
          <BotOwnerSection 
            appId={app._id} 
            currentOwner={app.bot?.owner || null} 
            onUpdate={handleUpdate} 
          />
        </div>
      </div>
    </main>
  );
}
