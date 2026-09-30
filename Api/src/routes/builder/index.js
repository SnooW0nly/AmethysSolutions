import { Router } from "express";
import mongoose from "mongoose";

const router = Router();

// ─── Schema com TTL automático ───────────────────────────────────────────────
const builderSchema = new mongoose.Schema(
  {
    json: {
      type: String,
      required: true,
    },
    expiresAt: {
      type: Date,
      required: true,
      index: { expires: 0 }, // TTL index — MongoDB deleta quando expiresAt < agora
    },
  },
  { timestamps: true }
);

// Modelo (singleton seguro para hot-reload)
const BuilderSnippet =
  mongoose.models.BuilderSnippet ||
  mongoose.model("BuilderSnippet", builderSchema);

// ─── POST /builder ────────────────────────────────────────────────────────────
// Cria um snippet JSON com TTL
router.post("/", async (req, res) => {
  try {
    const { json, ttlDays = 7 } = req.body;

    if (!json || typeof json !== "string") {
      return res.status(400).json({ error: "Campo 'json' obrigatório" });
    }

    // Valida JSON
    try {
      JSON.parse(json);
    } catch {
      return res.status(400).json({ error: "JSON mal-formado" });
    }

    const days = Math.min(Math.max(Number(ttlDays) || 7, 1), 30); // 1–30 dias
    const expiresAt = new Date(Date.now() + days * 24 * 60 * 60 * 1000);

    const snippet = await BuilderSnippet.create({ json, expiresAt });

    return res.status(201).json({
      id: snippet._id,
      expiresAt: snippet.expiresAt,
    });
  } catch (err) {
    console.error("[BUILDER POST]", err);
    return res.status(500).json({ error: "Erro interno" });
  }
});

// ─── GET /builder/:id ─────────────────────────────────────────────────────────
// Busca snippet pelo ID
router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;

    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const snippet = await BuilderSnippet.findById(id).lean();

    if (!snippet) {
      return res.status(404).json({ error: "Não encontrado ou expirado" });
    }

    // Checa expiração manualmente (TTL pode ter até 60s de delay)
    if (snippet.expiresAt < new Date()) {
      await BuilderSnippet.deleteOne({ _id: id });
      return res.status(404).json({ error: "Link expirado" });
    }

    return res.json({
      id: snippet._id,
      json: snippet.json,
      expiresAt: snippet.expiresAt,
      createdAt: snippet.createdAt,
    });
  } catch (err) {
    console.error("[BUILDER GET]", err);
    return res.status(500).json({ error: "Erro interno" });
  }
});

export default router;