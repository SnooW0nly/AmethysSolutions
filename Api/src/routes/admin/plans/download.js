import express from "express";
import fs from "fs";
import path from "path";
import Plan from "../../../database/models/Plan.js";

const router = express.Router();
const zipDir = path.resolve(process.cwd(), "src", "database", "zip");

// ---- esta função garante que o bodyParser não interfira ----
function skipBodyParser(req, res, next) {
  req._body = false; // Express acha que não precisa fazer parse
  next();
}

router.get("/:id/zip", skipBodyParser, async (req, res) => {
  try {
    const { id } = req.params;
    const plan = await Plan.findOne({ id }).lean();
    if (!plan || !plan.zipFilename) {
      return res.status(404).json({ error: "Arquivo não encontrado" });
    }

    const filePath = path.join(zipDir, plan.zipFilename);
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: "Arquivo não encontrado" });
    }

    // 🔒 garante que nenhum middleware/proxy re-comprime
    res.setHeader("Content-Encoding", "identity");
    res.setHeader("Content-Type", "application/zip");
    res.setHeader(
      "Content-Disposition",
      `attachment; filename="${plan.zipFilename}"`
    );
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("Accept-Ranges", "bytes");

    // 📦 envia o arquivo direto
    return res.sendFile(filePath, (err) => {
      if (err && !res.headersSent) {
        console.error("Erro ao enviar arquivo:", err);
        res.status(500).json({ error: "Erro ao enviar arquivo" });
      }
    });
  } catch (err) {
    console.error("Erro na rota de download:", err);
    return res.status(400).json({ error: "Erro ao servir arquivo" });
  }
});

export default router;
