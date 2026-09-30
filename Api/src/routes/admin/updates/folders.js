import express from "express";
import JSZip from "jszip";
import fs from "fs";
import discloudService from "../../../services/discloudService.js";

const router = express.Router();

const EXCLUDED_FOLDERS = ["database", "configs"];

/**
 * POST /admin/updates/folders
 * Recebe o ZIP do plano e retorna a estrutura de pastas (excluindo 'database' e 'configs')
 */
router.post("/", async (req, res) => {
  // Expect zipPath in body (already uploaded via /start flow, or a temp path)
  const { zipPath } = req.body;

  if (!zipPath || !fs.existsSync(zipPath)) {
    return res.status(400).json({
      success: false,
      message: "zipPath inválido ou não encontrado",
    });
  }

  try {
    const buffer = fs.readFileSync(zipPath);
    const zip = await JSZip.loadAsync(buffer);

    const fileList = Object.keys(zip.files);
    const rootPrefix = detectRootPrefix(fileList);

    // Collect top-level folders only
    const folders = new Set();
    for (const filePath of fileList) {
      const relative = rootPrefix ? filePath.replace(rootPrefix, "") : filePath;
      if (!relative) continue;
      const parts = relative.split("/");
      if (parts.length >= 2 && parts[0]) {
        const folder = parts[0];
        if (!EXCLUDED_FOLDERS.includes(folder.toLowerCase())) {
          folders.add(folder);
        }
      }
    }

    return res.status(200).json({
      success: true,
      data: {
        folders: Array.from(folders).sort(),
        rootPrefix,
      },
    });
  } catch (error) {
    console.error("[ADMIN UPDATES FOLDERS] Erro ao ler ZIP:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao ler estrutura do ZIP",
      error: error.message,
    });
  }
});

/**
 * POST /admin/updates/folders/delete-on-app
 * Deleta pastas específicas em um app da Discloud
 */
router.post("/delete-on-app", async (req, res) => {
  const { appId, folders } = req.body;

  if (!appId || !Array.isArray(folders) || folders.length === 0) {
    return res.status(400).json({
      success: false,
      message: "appId e folders[] são obrigatórios",
    });
  }

  const results = [];

  for (const folder of folders) {
    const result = await discloudService.deleteDirectory(appId, folder);
    results.push({
      folder,
      success: result.success,
      message: result.success ? "Pasta deletada com sucesso" : result.error,
    });
  }

  const allOk = results.every((r) => r.success);

  return res.status(200).json({
    success: allOk,
    data: results,
  });
});

function detectRootPrefix(fileList) {
  const nonDirFiles = fileList.filter((f) => !f.endsWith("/"));
  if (nonDirFiles.length === 0) return "";
  const firstSegments = nonDirFiles.map((f) => f.split("/")[0]);
  const unique = [...new Set(firstSegments)];
  if (unique.length === 1 && nonDirFiles.some((f) => f.includes("/"))) {
    return `${unique[0]}/`;
  }
  return "";
}

export default router;