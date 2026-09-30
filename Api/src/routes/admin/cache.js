import express from "express";
import discloudCache from "../../services/discloud/cache.js";

const router = express.Router();

router.get("/stats", (req, res) => {
  try {
    const stats = discloudCache.getStats();
    res.json({ success: true, cache: stats });
  } catch (err) {
    console.error("[CACHE STATS]", err);
    res.status(500).json({ error: "Erro ao obter estatísticas do cache" });
  }
});

router.delete("/clear", (req, res) => {
  try {
    discloudCache.clear();
    res.json({ success: true, message: "Cache limpo com sucesso" });
  } catch (err) {
    console.error("[CACHE CLEAR]", err);
    res.status(500).json({ error: "Erro ao limpar cache" });
  }
});

router.delete("/:appId", (req, res) => {
  try {
    const { appId } = req.params;
    discloudCache.invalidate(appId);
    res.json({ success: true, message: `Cache invalidado para app ${appId}` });
  } catch (err) {
    console.error("[CACHE INVALIDATE]", err);
    res.status(500).json({ error: "Erro ao invalidar cache" });
  }
});

export default router;
