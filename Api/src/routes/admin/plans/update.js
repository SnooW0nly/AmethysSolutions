import express from "express";
import Plan from "../../../database/models/Plan.js";
import fs from "fs";
import path from "path";

const router = express.Router();

const zipDir = path.resolve(process.cwd(), "src", "database", "zip");

router.put("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const payload = req.body;
    // Preserve existing zipFilename unless payload explicitly clears it
    const existing = await Plan.findOne({ id }).lean();
    const updated = await Plan.findOneAndUpdate(
      { id },
      { ...payload, zipFilename: payload.zipFilename ?? existing?.zipFilename },
      { new: true }
    );
    if (!updated) return res.status(404).json({ error: "Plano não encontrado" });
    return res.json({ plan: updated });
  } catch (err) {
    return res.status(400).json({ error: "Erro ao atualizar plano" });
  }
});

export default router;


