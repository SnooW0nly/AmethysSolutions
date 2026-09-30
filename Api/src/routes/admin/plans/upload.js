import express from "express";
import multer from "multer";
import fs from "fs";
import path from "path";
import Plan from "../../../database/models/Plan.js";
import unzipper from "unzipper";

const router = express.Router();

const zipDir = path.resolve(process.cwd(), "src", "database", "zip");
if (!fs.existsSync(zipDir)) {
  fs.mkdirSync(zipDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, zipDir),
  filename: (req, file, cb) => {
    const planId = req.params.id || "generic";
    const ts = Date.now();
    const safe = String(planId).replace(/[^a-zA-Z0-9-_]/g, "");
    cb(null, `${safe}-${ts}.zip`);
  },
});

const upload = multer({
  storage,
  fileFilter: (_req, file, cb) => {
    if (file.mimetype === "application/zip" || file.originalname.endsWith(".zip")) {
      return cb(null, true);
    }
    return cb(new Error("Arquivo deve ser .zip"));
  },
  limits: { fileSize: 200 * 1024 * 1024 }, // 200MB para suportar pastas grandes como modules
});

router.post("/:id/zip", upload.single("file"), async (req, res) => {
  try {
    const { id } = req.params;
    const plan = await Plan.findOne({ id });
    if (!plan) return res.status(404).json({ error: "Plano não encontrado" });

    // Remove old file if exists
    if (plan.zipFilename) {
      const oldPath = path.join(zipDir, plan.zipFilename);
      if (fs.existsSync(oldPath)) {
        try { fs.unlinkSync(oldPath); } catch { }
      }
    }

    const filename = path.basename(req.file.filename);
    const filePath = path.join(zipDir, filename);

    // Verifica tamanho do arquivo
    const fileStats = fs.statSync(filePath);
    console.log(`[UPLOAD] Arquivo recebido: ${filename} (${(fileStats.size / 1024 / 1024).toFixed(2)} MB)`);

    // Try to extract for basic validation into a temp dir and then remove it
    const tempExtractDir = path.join(zipDir, `__tmp_extract_${Date.now()}`);
    fs.mkdirSync(tempExtractDir, { recursive: true });

    try {
      // Usa Promise com timeout para ZIPs grandes
      await new Promise((resolve, reject) => {
        const stream = fs.createReadStream(filePath)
          .pipe(unzipper.Extract({
            path: tempExtractDir,
            concurrency: 5 // Permite 5 arquivos extraídos em paralelo
          }));

        stream.on('close', resolve);
        stream.on('error', reject);

        // Timeout de 5 minutos para ZIPs muito grandes
        const timeout = setTimeout(() => {
          stream.destroy();
          reject(new Error('Timeout ao validar ZIP (5 min)'));
        }, 5 * 60 * 1000);

        stream.on('close', () => clearTimeout(timeout));
      });

      // Aguarda um momento para garantir que todos os arquivos foram escritos
      await new Promise(resolve => setTimeout(resolve, 500));

      // Verifica se extraiu algo
      const extractedFiles = countFilesRecursive(tempExtractDir);
      console.log(`[UPLOAD] ZIP válido - ${extractedFiles} arquivos extraídos`);

      if (extractedFiles === 0) {
        throw new Error("ZIP vazio ou corrompido");
      }

      // Salva no banco
      plan.zipFilename = filename;
      await plan.save();

      return res.json({
        ok: true,
        filename,
        filesCount: extractedFiles,
        sizeBytes: fileStats.size
      });

    } catch (e) {
      console.error(`[UPLOAD] Erro ao validar ZIP:`, e.message);

      // mark as invalid by removing stored file and temp dir
      try { fs.unlinkSync(filePath); } catch { }
      try { fs.rmSync(tempExtractDir, { recursive: true, force: true }); } catch { }

      plan.zipFilename = undefined;
      await plan.save();

      return res.status(400).json({
        error: "Arquivo .zip corrompido ou inválido",
        details: e.message
      });
    } finally {
      try { fs.rmSync(tempExtractDir, { recursive: true, force: true }); } catch { }
    }
  } catch (err) {
    console.error(`[UPLOAD] Erro geral:`, err);
    return res.status(400).json({ error: "Erro no upload", details: err.message });
  }
});

/**
 * Conta arquivos recursivamente sem usar recursão (evita stack overflow)
 */
function countFilesRecursive(dirPath) {
  let count = 0;
  const stack = [dirPath];

  while (stack.length > 0) {
    const currentDir = stack.pop();

    let entries;
    try {
      entries = fs.readdirSync(currentDir, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);

      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile()) {
        count++;
      }
    }
  }

  return count;
}

export default router;
