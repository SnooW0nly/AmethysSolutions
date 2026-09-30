// src/routes/admin/discord/index.js
import express from "express";
import discordConfigRoute from "./discord-config.js";

const router = express.Router();

router.use("/", discordConfigRoute);

export default router;