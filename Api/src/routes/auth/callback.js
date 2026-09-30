import express from "express";
import User from "../../database/models/User.js";
import { generateToken } from "../../database/auth.js";
import getRedirectUri from "../../functions/getRedirectUri.js";
import getClientIp from "../../functions/getClientIp.js";

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    console.log("[callback] Iniciando callback do Discord");
    const { code, error, state } = req.query;

    if (error) {
      console.error("[callback] Erro no OAuth:", error);
      return res.status(400).send(String(error));
    }

    if (!code) {
      console.error("[callback] Code ausente");
      return res.status(400).json({ error: "Code ausente" });
    }

    console.log("[callback] Code recebido, state:", state);

    const clientId = process.env.DISCORD_CLIENT_ID;
    const clientSecret = process.env.DISCORD_CLIENT_SECRET;
    if (!clientId || !clientSecret) {
      return res
        .status(500)
        .json({ error: "Discord CLIENT_ID/SECRET não configurados" });
    }

    const redirectUri = getRedirectUri(req);

    const params = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: "authorization_code",
      code: String(code),
      redirect_uri: redirectUri,
    });

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    const tokenResp = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params.toString(),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!tokenResp.ok) {
      const t = await tokenResp.text();
      console.error("[callback] token exchange failed:", tokenResp.status, t);
      return res.status(400).json({ error: "Falha ao obter token", detail: t });
    }

    const tokenJson = await tokenResp.json();
    if (tokenJson.error) {
      console.error("[callback] token exchange error:", tokenJson);
      return res
        .status(400)
        .json({ error: "Falha ao obter token", detail: tokenJson });
    }

    const { access_token, token_type, refresh_token, scope, expires_in } =
      tokenJson;

    const controller2 = new AbortController();
    const timeoutId2 = setTimeout(() => controller2.abort(), 10000);
    const userResp = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `${token_type} ${access_token}` },
      signal: controller2.signal,
    });
    clearTimeout(timeoutId2);

    if (!userResp.ok) {
      const t = await userResp.text();
      console.error("[callback] user fetch failed:", userResp.status, t);
      return res
        .status(400)
        .json({ error: "Falha ao obter usuário", detail: t });
    }

    const dUser = await userResp.json();
    if (dUser.error) {
      console.error("[callback] user fetch error:", dUser);
      return res
        .status(400)
        .json({ error: "Falha ao obter usuário", detail: dUser });
    }

    const payload = {
      discordId: dUser.id,
      username: dUser.username,
      globalName: dUser.global_name || dUser.username,
      email: dUser.email || undefined,
      avatar: dUser.avatar
        ? `https://cdn.discordapp.com/avatars/${dUser.id}/${dUser.avatar}.webp?size=256`
        : undefined,
    };

    const clientIp = getClientIp(req);
    const now = new Date();

    const user = await User.findOneAndUpdate(
      { discordId: payload.discordId },
      {
        $set: {
          username: payload.username,
          globalName: payload.globalName,
          email: payload.email,
          avatar: payload.avatar,
          oauth: {
            accessToken: access_token,
            refreshToken: refresh_token,
            tokenType: token_type,
            scope,
            obtainedAt: now,
            expiresAt: expires_in
              ? new Date(Date.now() + Number(expires_in) * 1000)
              : undefined,
          },
        },
        $setOnInsert: {
          admin: false,
          tokenVersion: 0,
          ipHistory: [],
        },
      },
      { new: true, upsert: true }
    );

    // Salva IP no histórico
    if (user && clientIp) {
      const history = Array.isArray(user.ipHistory) ? user.ipHistory : [];
      const existing = history.find((h) => h.ip === clientIp);
      if (existing) {
        existing.dates.push(now);
      } else {
        history.push({ ip: clientIp, dates: [now] });
      }
      user.ipHistory = history;
      try {
        await user.save();
        console.log(`[callback] IP salvo: ${clientIp} → user ${user._id}`);
      } catch (saveErr) {
        console.error("[callback] Falha ao salvar IP:", saveErr);
      }
    }

    // Tenta adicionar ao servidor Discord (best-effort)
    try {
      const { addUserToGuild } = await import(
        "../../services/discord/puxarDiscord.js"
      );
      await addUserToGuild({
        userId: payload.discordId,
        accessToken: access_token,
        guildId: process.env.DISCORD_GUILD_ID,
        nickname: payload.globalName,
      });
    } catch (e) {
      console.warn("[callback] guild join falhou:", e?.message || e);
    }

    console.log("[callback] Gerando token JWT para user:", user._id);
    const jwtToken = generateToken({
      id: user._id,
      discordId: user.discordId,
      tokenVersion: user.tokenVersion || 0,
    });

    const isProd = process.env.NODE_ENV === "production";

    console.log("[callback] Configurando cookie (isProd:", isProd, ")");
    res.cookie("token", jwtToken, {
      httpOnly: true,
      sameSite: isProd ? "none" : "lax",
      secure: isProd,
      path: "/",
      maxAge: 7 * 24 * 60 * 60 * 1000,
      domain: isProd ? process.env.COOKIE_DOMAIN : undefined,
    });

    const frontendUrl = process.env.FRONTEND_URL || "http://localhost:3000";
    const dashboardUrl = `${frontendUrl}/dashboard`;

    console.log("[callback] Login bem-sucedido, redirecionando para:", dashboardUrl);
    return res.redirect(dashboardUrl);
  } catch (err) {
    console.error("Erro no callback:", err);
    return res.status(500).json({ error: "Erro no servidor" });
  }
});

export default router;