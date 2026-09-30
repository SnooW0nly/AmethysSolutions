import express from "express";
import Plan from "../../../database/models/Plan.js";
import fs from "fs";
import path from "path";

const router = express.Router();

const zipDir = path.resolve(process.cwd(), "src", "database", "zip");

router.delete("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const deleted = await Plan.findOneAndDelete({ id });
    if (deleted?.zipFilename) {
      const zipPath = path.join(zipDir, deleted.zipFilename);
      if (fs.existsSync(zipPath)) {
        try { fs.unlinkSync(zipPath); } catch {}
      }
    }
    if (!deleted) return res.status(404).json({ error: "Plano não encontrado" });
    return res.json({ ok: true });
  } catch (err) {
    return res.status(400).json({ error: "Erro ao deletar plano" });
  }
});

export default router;


