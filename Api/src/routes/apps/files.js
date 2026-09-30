import express from "express";
import discloudService from "../../services/discloudService.js";

const router = express.Router();

// GET /:id/files?path=.
router.get("/:id/files", async (req, res) => {
  const { id } = req.params;
  const filePath = req.query.path || ".";
  const result = await discloudService.listFiles(id, filePath);
  if (!result.success) return res.status(500).json(result);
  return res.status(200).json({ success: true, output: result.output });
});

// GET /:id/files/content?path=arquivo.js
router.get("/:id/files/content", async (req, res) => {
  const { id } = req.params;
  const { path } = req.query;
  if (!path) return res.status(400).json({ success: false, error: "path é obrigatório" });
  const result = await discloudService.readFile(id, path);
  if (!result.success) return res.status(500).json(result);
  return res.status(200).json({ success: true, content: result.content });
});

// PUT /:id/files/content — writeFile ainda requer commit
router.put("/:id/files/content", (req, res) => {
  return res.status(405).json({
    success: false,
    error: "Escrita de arquivo requer um novo commit/redeploy.",
  });
});

// POST /:id/files/mkdir
router.post("/:id/files/mkdir", async (req, res) => {
  const { id } = req.params;
  const { path } = req.body;
  if (!path) return res.status(400).json({ success: false, error: "path é obrigatório" });
  const result = await discloudService.createDirectory(id, path);
  if (!result.success) return res.status(500).json(result);
  return res.status(200).json({ success: true });
});

// PUT /:id/files/rename
router.put("/:id/files/rename", async (req, res) => {
  const { id } = req.params;
  const { oldPath, newPath } = req.body;
  if (!oldPath || !newPath) return res.status(400).json({ success: false, error: "oldPath e newPath são obrigatórios" });
  const result = await discloudService.renameFile(id, oldPath, newPath);
  if (!result.success) return res.status(500).json(result);
  return res.status(200).json({ success: true });
});

// POST /:id/files/delete
router.post("/:id/files/delete", async (req, res) => {
  const { id } = req.params;
  const { path, isDirectory } = req.body;
  if (!path) return res.status(400).json({ success: false, error: "path é obrigatório" });
  const result = isDirectory
    ? await discloudService.deleteDirectory(id, path)
    : await discloudService.deleteFile(id, path);
  if (!result.success) return res.status(500).json(result);
  return res.status(200).json({ success: true });
});

export default router;