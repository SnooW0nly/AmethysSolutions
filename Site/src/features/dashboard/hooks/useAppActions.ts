// Shared hook for app start/stop/restart actions.
// Centralizes HTTP calls and consistent toast messages.
import { addToast } from "@heroui/react";
import { restartApp, startApp, stopApp } from "@/lib/api/apps";

type Action = "start" | "stop" | "restart";

// Rate limit: armazena último timestamp de ação por app
const lastActionTime = new Map<string, number>();
const RATE_LIMIT_MS = 5000; // 5 segundos entre ações

export function useAppActions() {
  async function doAction(appId: string, action: Action): Promise<boolean> {
    try {
      if (!appId) return false;

      // Verifica rate limit
      const now = Date.now();
      const lastTime = lastActionTime.get(appId) || 0;
      const timeSinceLastAction = now - lastTime;

      if (timeSinceLastAction < RATE_LIMIT_MS) {
        const remainingSeconds = Math.ceil((RATE_LIMIT_MS - timeSinceLastAction) / 1000);
        addToast({
          title: "Vá com calma",
          description: `Aguarde ${remainingSeconds}s antes de executar outra ação`,
          color: "warning",
        });
        return false;
      }

      // Atualiza timestamp
      lastActionTime.set(appId, now);

      // Executa ação
      if (action === "start") await startApp(appId);
      else if (action === "stop") await stopApp(appId);
      else await restartApp(appId);

      // Toast de sucesso
      const actionText = action === "start" ? "ligado" : action === "stop" ? "desligado" : "reiniciado";
      addToast({
        title: `Bot ${actionText}`,
        description: "Aguarde alguns segundos para ver o novo status",
        color: "success",
      });

      return true;
    } catch (e: any) {
      const code = e?.code || e?.data?.errorCode;
      if (code === "BOT_NOT_CONFIGURED") {
        addToast({
          title: "Bot não configurado",
          description: "Configure o token do bot antes de ligar ou reiniciar.",
          color: "warning",
        });
        return false;
      }
      if (code === "SERVER_NOT_CONFIGURED") {
        addToast({
          title: "Servidor não configurado",
          description: "Configure o ID do servidor antes de ligar ou reiniciar.",
          color: "warning",
        });
        return false;
      }
      addToast({
        title: "Erro",
        description: e?.message || "Falha ao executar ação",
        color: "danger",
      });
      return false;
    }
  }

  return { doAction } as const;
}


