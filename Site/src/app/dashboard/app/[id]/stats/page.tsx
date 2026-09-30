"use client";

import { useParams } from "next/navigation";
import { useAppInfo } from "@/hooks/useApp";
import { Loading } from "@/components/Loading";

export default function StatsPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id as string | undefined;
  const { app, loading } = useAppInfo(id);

  if (loading) return <Loading />;
  if (!app) return null;

  return (
    <main className="p-4 md:p-6 flex flex-col gap-4">
      <section className="bg-foreground/5 border border-foreground/10 rounded-xl p-4">
        <h2 className="text-base font-semibold">Estatísticas</h2>
        <p className="text-sm text-foreground/70 mt-1">Exemplo de estatísticas para a aplicação {app.name || app._id}.</p>
      </section>
    </main>
  );
}


