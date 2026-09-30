"use client";

import { Loading } from "@/components/Loading";
import { DashboardHeader, DashboardMissing } from "@/components/ui/dashboard/DashboardHeader";
import { useRequireAuth } from "@/hooks/useAuth";
import { useEffect, useState } from "react";
import { AppCard } from "@/components/ui/dashboard/AppCard";

export default function DashboardPage() {
  const { user, loading } = useRequireAuth();
  const [apps, setApps] = useState<any[] | null>(null);
  const [appsLoading, setAppsLoading] = useState(false);

  const fetchApps = async () => {
    try {
      setAppsLoading(true);
      const res = await fetch("/api/apps", { cache: "no-store" });
      const json = await res.json();
      setApps(json.applications || []);
    } catch {
      setApps([]);
    } finally {
      setAppsLoading(false);
    }
  };

  useEffect(() => {
    if (user) fetchApps();
  }, [user]);

  // Exibe loading global até que usuário e apps estejam carregados
  if (loading || appsLoading || apps === null) return <Loading />;

  return (
    <main>
      {user && <DashboardHeader user={user} />}
      {(apps?.length ?? 0) === 0 ? (
        <DashboardMissing />
      ) : (
        <>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-foreground/90">Suas aplicações</h2>
          </div>
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {apps.map((app) => (
              <AppCard key={app._id} app={app} onRefresh={fetchApps} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
