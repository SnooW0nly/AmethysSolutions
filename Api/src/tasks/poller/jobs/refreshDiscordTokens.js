import User from "../../../database/models/User.js";

const DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token";

// Renova tokens que expiram nas próximas REFRESH_WINDOW_HOURS horas
const REFRESH_WINDOW_HOURS = 48;

/**
 * Renova um único token OAuth2 do Discord.
 * @param {string} refreshToken
 * @returns {Promise<object>} Novo payload OAuth ou lança erro
 */
async function refreshDiscordToken(refreshToken) {
  const clientId     = process.env.DISCORD_CLIENT_ID;
  const clientSecret = process.env.DISCORD_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    throw new Error("DISCORD_CLIENT_ID / DISCORD_CLIENT_SECRET não configurados");
  }

  const params = new URLSearchParams({
    client_id:     clientId,
    client_secret: clientSecret,
    grant_type:    "refresh_token",
    refresh_token: refreshToken,
  });

  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), 10_000);

  const resp = await fetch(DISCORD_TOKEN_URL, {
    method:  "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body:    params.toString(),
    signal:  controller.signal,
  });
  clearTimeout(tid);

  const json = await resp.json();

  if (!resp.ok || json.error) {
    throw new Error(json.error_description || json.error || `HTTP ${resp.status}`);
  }

  return json; // { access_token, refresh_token, token_type, scope, expires_in }
}

/**
 * Job principal: busca usuários com token prestes a expirar e renova.
 */
export async function refreshExpiringTokens() {
  const now        = new Date();
  const windowEnd  = new Date(now.getTime() + REFRESH_WINDOW_HOURS * 60 * 60 * 1000);

  // Usuários cujo token expira dentro da janela OU já expirou, e que têm refresh_token
  const users = await User.find({
    "oauth.refreshToken": { $exists: true, $ne: null },
    $or: [
      { "oauth.expiresAt": { $lte: windowEnd } }, // expira em breve
      { "oauth.expiresAt": { $exists: false } },   // sem data (legado)
    ],
  }).select("_id discordId username oauth").lean();

  if (!users.length) return;

  console.log(`[refreshTokens] ${users.length} usuário(s) com token para renovar`);

  let renewed  = 0;
  let failed   = 0;
  let revoked  = 0;

  for (const user of users) {
    const refreshToken = user.oauth?.refreshToken;
    if (!refreshToken) continue;

    try {
      const tokenJson = await refreshDiscordToken(refreshToken);

      const { access_token, refresh_token, token_type, scope, expires_in } = tokenJson;

      await User.findByIdAndUpdate(user._id, {
        $set: {
          "oauth.accessToken":  access_token,
          "oauth.refreshToken": refresh_token,   // Discord rotaciona o refresh_token
          "oauth.tokenType":    token_type,
          "oauth.scope":        scope,
          "oauth.obtainedAt":   now,
          "oauth.expiresAt":    expires_in
            ? new Date(now.getTime() + Number(expires_in) * 1000)
            : undefined,
        },
      });

      renewed++;
    } catch (err) {
      const msg = err.message || String(err);

      // Token foi revogado pelo usuário (desconectou o app no Discord)
      const isRevoked = msg.includes("invalid_grant") || msg.includes("Invalid refresh token");

      if (isRevoked) {
        // Limpa os tokens inválidos para não tentar renovar sempre
        await User.findByIdAndUpdate(user._id, {
          $unset: {
            "oauth.accessToken":  "",
            "oauth.refreshToken": "",
            "oauth.expiresAt":    "",
          },
        });
        console.warn(`[refreshTokens] Token revogado — user ${user.discordId} (${user.username}). OAuth limpo.`);
        revoked++;
      } else {
        console.error(`[refreshTokens] Falha ao renovar user ${user.discordId}: ${msg}`);
        failed++;
      }
    }
  }

  if (renewed || failed || revoked) {
    console.log(
      `[refreshTokens] ✅ renovados: ${renewed} | ❌ falhas: ${failed} | 🚫 revogados: ${revoked}`
    );
  }
}