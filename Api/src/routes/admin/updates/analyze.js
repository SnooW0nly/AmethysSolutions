import express from "express";
import multer from "multer";
import path from "path";
import fs from "fs";
import JSZip from "jszip";

const router = express.Router();

const EXCLUDED_FOLDERS = ["database", "configs"];

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.resolve(process.cwd(), "src/temp/updates");
    if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `update-${Date.now()}-${file.originalname}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 100 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === "application/zip" || file.originalname.endsWith(".zip")) {
      cb(null, true);
    } else {
      cb(new Error("Apenas arquivos ZIP são permitidos"));
    }
  },
});

/**
 * POST /admin/updates/analyze
 * Recebe um ZIP, salva temporariamente e retorna a lista de pastas de primeiro nível
 * (excluindo 'database' e 'configs')
 */
router.post("/", upload.single("file"), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ success: false, message: "Arquivo ZIP é obrigatório" });
  }

  try {
    const buffer = fs.readFileSync(req.file.path);
    const zip = await JSZip.loadAsync(buffer);

    const fileList = Object.keys(zip.files);
    const rootPrefix = detectRootPrefix(fileList);

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
        zipPath: req.file.path,
        folders: Array.from(folders).sort(),
        rootPrefix,
      },
    });
  } catch (error) {
    console.error("[ADMIN UPDATES ANALYZE] Erro:", error);
    // Clean up on error
    try { fs.unlinkSync(req.file.path); } catch {}
    return res.status(500).json({
      success: false,
      message: "Erro ao analisar ZIP",
      error: error.message,
    });
  }
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