import express from "express";
import getStatusWebsite from "../../functions/getStatusWebsite.js";

const router = express.Router();

router.get("/", async (req, res) => {
  const stats = getStatusWebsite(req);
  return res.json(stats);
});

export default router;