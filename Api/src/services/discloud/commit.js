import discloudService from "../discloudService.js";

/**
 * Realiza commit de uma app na Discloud via SDK oficial.
 * Toda lógica de retry e backoff está em discloudService.commitApp().
 *
 * @param {string}        appId
 * @param {Buffer|string} fileBuffer  Buffer do ZIP ou caminho do arquivo
 */
export async function commitApp(appId, fileBuffer) {
  try {
    const result = await discloudService.commitApp(appId, fileBuffer);

    if (!result.success) {
      const msg = result.error || "Erro ao realizar commit na Discloud";

      // 404 → app não existe na Discloud
      if (
        msg.includes("404") ||
        msg.toLowerCase().includes("not found") ||
        msg.toLowerCase().includes("não encontrad")
      ) {
        throw new Error("Aplicação não encontrada na Discloud");
      }

      throw new Error(msg);
    }

    return {
      success: true,
      data: result.data,
      warning: result.data?.message || null,
    };
  } catch (error) {
    // HTML de erro ou timeout que escapou do retry
    if (
      error instanceof SyntaxError ||
      error.message?.includes("<!DOCTYPE") ||
      error.message?.includes("Unexpected token")
    ) {
      const wrapped = new Error("Discloud retornou resposta inválida (timeout ou erro de servidor)");
      console.error("[DISCLOUD COMMIT] Erro HTML/parse:", error.message);
      throw wrapped;
    }

    console.error(`[DISCLOUD COMMIT] Erro no commit de ${appId}:`, error.message);
    throw error;
  }
}

export async function restartApp(appId) {
  try {
    const result = await discloudService.restartApp(appId);

    if (!result.success) {
      if (
        result.error &&
        (result.error.includes("404") || result.error.toLowerCase().includes("not found"))
      ) {
        throw new Error("Aplicação não encontrada na Discloud");
      }
      console.warn(`[DISCLOUD RESTART] Aviso para ${appId}: ${result.error || "App pode estar desligado"}`);
      return { success: false, error: result.error, warning: "App pode estar desligado" };
    }

    return { success: true, data: result.data };
  } catch (error) {
    if (
      error instanceof SyntaxError ||
      error.message?.includes("<!DOCTYPE") ||
      error.message?.includes("Unexpected token")
    ) {
      throw new Error("Discloud retornou resposta inválida (timeout ou erro de servidor)");
    }
    console.error(`[DISCLOUD RESTART] Erro no restart de ${appId}:`, error.message);
    throw error;
  }
}