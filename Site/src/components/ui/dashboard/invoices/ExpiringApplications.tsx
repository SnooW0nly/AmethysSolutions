"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, RefreshCw, Clock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@heroui/react";

interface Application {
  _id: string;
  name: string;
  plan: {
    name: string;
  };
  expiresAt: string;
  daysLeft: number;
}

export default function ExpiringApplications() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    loadExpiringApps();
  }, []);

  const loadExpiringApps = async () => {
    try {
      const response = await fetch("/api/applications/expiring", {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setApplications(data.data || []);
        }
      }
    } catch (error) {
      console.error("Erro ao carregar apps expirando:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return null;
  }

  if (applications.length === 0) {
    return null;
  }

  return (
    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-6">
      <div className="flex flex-col items-start gap-4 w-full">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <h3 className="text-xl font-bold text-yellow-500">
              Vencimento de aplicações
            </h3>
            <p className="text-sm text-foreground/60">
              Você tem {applications.length} {applications.length === 1 ? "aplicação" : "aplicações"} que {applications.length === 1 ? "vence" : "vencem"} nos próximos 7 dias.
              Renove agora para evitar o bloqueio dela{applications.length > 1 ? "s" : ""}.
            </p>
          </div>
        </div>
        <hr className="w-full border-foreground/10" />
        <div className="w-full">
            {applications.map((app) => (
              <div
                key={app._id}
                className="bg-background/50 border border-foreground/10 rounded-lg p-4"
              >
                <div className="flex md:flex-row flex-col md:items-center justify-between gap-3">
                  <div className="flex-1">
                    <h4 className="font-semibold text-lg mb-1">{app.name}</h4>
                    <div className="flex items-center gap-2 text-sm text-foreground/60">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        Expira em {app.daysLeft} {app.daysLeft === 1 ? "dia" : "dias"}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-foreground/30"></span>
                      <span>{new Date(app.expiresAt).toLocaleDateString("pt-BR")}</span>
                    </div>
                  </div>

                  <Button
                    onPress={() => router.push(`/dashboard/invoices?renew=${app._id}`)}
                    color="primary"
                    startContent={<RefreshCw className="w-4 h-4" />}
                    className="font-normal text-sm rounded-lg"
                  >
                    Renovar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
  );
}
