import express from "express";
import crypto from "node:crypto";
import getRedirectUri from "../../functions/getRedirectUri.js";

const router = express.Router();

router.get("/", (req, res) => {
  const clientId = process.env.DISCORD_CLIENT_ID;
  const scope = encodeURIComponent(
    process.env.DISCORD_SCOPES || "identify email guilds.join"
  );
  // Generate state and store in httpOnly cookie for CSRF protection
  const stateRaw = crypto.randomUUID();
  const state = encodeURIComponent(stateRaw);

  if (!clientId) {
    return res.status(500).json({ error: "DISCORD_CLIENT_ID não configurado" });
  }

  const redirectUriRaw = getRedirectUri(req);

  const authUrl =
    `https://discord.com/api/oauth2/authorize` +
    `?response_type=code` +
    `&client_id=${clientId}` +
    `&redirect_uri=${encodeURIComponent(redirectUriRaw)}` +
    `&scope=${scope}` +
    `&state=${state}`;

  // Set httpOnly cookie with state, short expiry
  const isProd = process.env.NODE_ENV === "production";
  res.cookie("oauth_state", stateRaw, {
    httpOnly: true,
    sameSite: isProd ? "none" : "lax",
    secure: isProd,
    path: "/",
    maxAge: 10 * 60 * 1000,
  });

  console.log("[/auth/login]", { redirectUriRaw });

  return res.json({ authUrl, redirectUri: redirectUriRaw });
});

export default router;
