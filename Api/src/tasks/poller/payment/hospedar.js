import fs from "fs";
import path from "path";
import discloudService from "../../../services/discloudService.js";

function resolveZipPath(explicitPath) {
  if (explicitPath) return path.resolve(explicitPath);
  const zipDir = path.resolve(process.cwd(), "backend/src/database/zip");
  try {
    const files = fs.readdirSync(zipDir)
      .filter((f) => f.toLowerCase().endsWith(".zip"))
      .map((f) => ({ f, t: fs.statSync(path.join(zipDir, f)).mtimeMs }))
      .sort((a, b) => b.t - a.t);
    if (files.length === 0) return null;
    return path.join(zipDir, files[0].f);
  } catch {
    return null;
  }
}

/**
 * Hospeda uma aplicação na Discloud (fallback usado pelo processPayment)
 * @param {string} zipPathFromCaller - Caminho do ZIP
 * @param {object} options - { appName, language, command, memory, slug }
 */
export async function hospedarApp(zipPathFromCaller, options = {}) {
  const zipPath = resolveZipPath(zipPathFromCaller || process.env.DISCLOUD_ZIP_PATH);
  if (!zipPath) {
    console.error("[hospedarApp] Arquivo .zip não encontrado.");
    return null;
  }

  try {
    let stats;
    try {
      stats = fs.statSync(zipPath);
    } catch (e) {
      console.error("[hospedarApp] Caminho do .zip inválido ou inacessível:", zipPath);
      return null;
    }

    if (!stats.isFile() || stats.size <= 0) {
      console.error("[hospedarApp] .zip inexistente ou com tamanho inválido:", zipPath, "size=", stats.size);
      return null;
    }

    // A Discloud API no uploadApp recebe apenas o zipPath. 
    // Configurações como appName, ram, etc., devem estar no discloud.config dentro do ZIP.
    const result = await discloudService.uploadApp(zipPath);

    if (!result.success) {
      console.error("[hospedarApp] Erro da API Discloud:", result.error);
      return null;
    }

    console.log("[hospedarApp] Aplicação hospedada com sucesso na Discloud:", result.data);
    return result.data;
  } catch (err) {
    console.error("[hospedarApp] Erro ao hospedar aplicação:", err?.message || err);
    return null;
  }
}
