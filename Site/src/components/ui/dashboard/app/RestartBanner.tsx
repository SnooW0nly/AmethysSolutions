"use client";

import { useState } from "react";
import { Button, addToast } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRotate, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

interface RestartBannerProps {
  appId: string;
  onRestart?: () => void;
  serverConfigured?: boolean;
}

export function RestartBanner({ appId, onRestart, serverConfigured = true }: RestartBannerProps) {
  const [loading, setLoading] = useState(false);

  const handleRestart = async () => {
    if (!serverConfigured) {
      addToast({
        title: "Servidor não configurado",
        description: "Configure o ID do servidor antes de reiniciar",
        color: "warning",
      });
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/restart`, {
        method: "POST",
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao reiniciar bot");
      }

      addToast({
        title: "Bot reiniciando!",
        description: "Aguarde alguns segundos...",
        color: "success",
      });

      onRestart?.();
    } catch (err: any) {
      addToast({
        title: "Erro ao reiniciar",
        description: err.message || "Tente novamente",
        color: "danger",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg bg-warning/10 border border-warning/20 p-4 flex items-center justify-between gap-4">
      <div className="flex items-start gap-3">
        <FontAwesomeIcon icon={faExclamationTriangle} className="text-warning text-xl mt-0.5" />
        <div className="flex flex-col gap-1">
          <p className="font-semibold text-warning">Configurações alteradas</p>
          <p className="text-sm text-foreground/70">
            Seu bot precisa ser reiniciado para aplicar as novas configurações.
          </p>
        </div>
      </div>

      <Button
        color="warning"
        variant="flat"
        startContent={!loading && <FontAwesomeIcon icon={faRotate} />}
        onPress={handleRestart}
        isLoading={loading}
        className="shrink-0"
      >
        Reiniciar Agora
      </Button>
    </div>
  );
}
