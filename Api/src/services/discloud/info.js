import discloudService from "../discloudService.js";
import discloudCache from "./cache.js";

export default async function infoApp(appId) {
  if (!appId) {
    console.warn("[infoApp] appId ausente ao solicitar informações da aplicação.");
    return null;
  }

  const cached = discloudCache.get(appId);
  if (cached) return cached;

  try {
    const [appInfo, appStatus] = await Promise.all([
      discloudService.getAppInfo(appId),
      discloudService.getAppStatus(appId)
    ]);

    if (!appInfo.success) {
      console.warn(`[infoApp] Falha ao consultar Discloud Info para app ${appId}: ${appInfo.error}`);
      return null;
    }

    const app = appInfo.app;
    const status = appStatus.success ? appStatus.status : {
      running: false,
      container: "offline",
      ram: "0MB",
      cpu: "0%"
    };

    const normalizedApp = {
      ...app,
      status: {
        container: status.container,
        running: status.running,
        ram: status.ram,
        cpu: status.cpu,
        networkRx: null,
        networkTx: null,
      },
      ram: status.ram || null,
    };

    const result = { app: normalizedApp, status: normalizedApp.status };

    discloudCache.set(appId, result);

    return result;
  } catch (err) {
    console.warn(`[infoApp] Erro ao consultar Discloud para app ${appId}:`, err.message);
    return null;
  }
}
