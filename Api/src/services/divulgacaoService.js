import Divulgacao from "../database/models/Divulgacao.js";

const DISCORD_API = "https://discord.com/api/v9"; // v9 recomendada para user accounts

let _isRunning = false;
let _loopHandle = null;
const _logs = [];

function addLog(level, tokenLabel, channelId, msg) {
  const entry = {
    ts: new Date().toISOString(),
    level,
    token: tokenLabel,
    channel: channelId,
    msg,
  };
  _logs.unshift(entry);
  if (_logs.length > 200) _logs.length = 200;
}

export function getLogs() {
  return [..._logs];
}

export function isRunning() {
  return _isRunning;
}

// ─── Discord API helpers (User token) ────────────────────────────────────────

async function discordGet(path, token) {
  const res = await fetch(`${DISCORD_API}${path}`, {
    headers: { Authorization: token },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error(err.message || `HTTP ${res.status}`), { status: res.status });
  }
  return res.json();
}

async function discordPost(path, token, body) {
  const res = await fetch(`${DISCORD_API}${path}`, {
    method: "POST",
    headers: {
      Authorization: token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error(err.message || `HTTP ${res.status}`), {
      status: res.status,
      retryAfter: err.retry_after ?? null,
      discordCode: err.code ?? null,
    });
  }
  return res.json();
}

/** Valida token de usuário e retorna informações da conta */
export async function validateToken(token) {
  try {
    const user = await discordGet("/users/@me", token);
    return {
      valid: true,
      userId: user.id,
      username: user.username,
      discriminator: user.discriminator,
      avatar: user.avatar
        ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
        : null,
    };
  } catch {
    return { valid: false };
  }
}

export async function fetchChannel(token, channelId) {
  return discordGet(`/channels/${channelId}`, token);
}

async function fetchLastMessage(token, channelId) {
  try {
    const msgs = await discordGet(`/channels/${channelId}/messages?limit=1`, token);
    return msgs?.[0] ?? null;
  } catch {
    return null;
  }
}

async function sendMessage(token, channelId, content) {
  if (!content?.trim()) return;
  return discordPost(`/channels/${channelId}/messages`, token, { content: content.trim() });
}

// ─── Estado individual por conta+canal (bloqueios, permissões) ───────────────

/**
 * Chave: `tokenId:channelId`
 * Guarda estado de saúde de cada conta em cada canal.
 * Não controla "quando enviar" — isso é responsabilidade do estado compartilhado.
 */
const _tokenChannelHealth = new Map();

function getTokenHealth(tokenId, channelId) {
  const key = `${tokenId}:${channelId}`;
  if (!_tokenChannelHealth.has(key)) {
    _tokenChannelHealth.set(key, {
      blockedUntil: null,      // rate-limit / mute / timeout
      noPermission: false,     // 403 permanente
      noPermissionRetryAt: 0,
    });
  }
  return _tokenChannelHealth.get(key);
}

function isTokenHealthy(health, now) {
  if (health.noPermission && now < health.noPermissionRetryAt) return false;
  if (health.blockedUntil && now < health.blockedUntil) return false;
  return true;
}

// ─── Estado compartilhado por canal (coordenação inteligente) ─────────────────

/**
 * Chave: channelId
 *
 * Armazena o estado GLOBAL do canal, compartilhado entre todas as contas.
 * Isso garante que apenas UMA conta envie por vez e que o rodízio seja coordenado.
 *
 * {
 *   lastSentMsgId:   string | null  — ID da última mensagem enviada por qualquer conta
 *   lastExternalId:  string | null  — ID da última mensagem vista de terceiros
 *   nextSendAt:      number         — timestamp ms: quando o próximo envio está liberado
 *   assignedIndex:   number         — índice do token "da vez" na lista de tokens do canal
 *   waitingForReply: boolean        — slowmode 0: aguardando nova mensagem de terceiro
 * }
 */
const _channelShared = new Map();

function getChannelShared(channelId) {
  if (!_channelShared.has(channelId)) {
    _channelShared.set(channelId, {
      lastSentMsgId: null,
      lastExternalId: null,
      nextSendAt: 0,
      assignedIndex: 0,
      waitingForReply: false,
    });
  }
  return _channelShared.get(channelId);
}

// ─── Seleção inteligente do próximo token disponível ─────────────────────────

/**
 * Retorna o próximo tokenCfg saudável para um canal, fazendo rodízio circular.
 * Se nenhum estiver disponível, retorna null.
 *
 * @param {Array}  candidates  — lista de { tokenCfg, ch } que têm esse canal ativo
 * @param {object} shared      — estado compartilhado do canal
 * @param {number} now
 */
function pickNextToken(candidates, shared, now) {
  const total = candidates.length;
  if (total === 0) return null;

  // tenta a partir do assignedIndex, dando uma volta completa
  for (let i = 0; i < total; i++) {
    const idx = (shared.assignedIndex + i) % total;
    const { tokenCfg, ch } = candidates[idx];
    const health = getTokenHealth(tokenCfg.id, ch.channelId);

    // recupera noPermission expirada
    if (health.noPermission && now >= health.noPermissionRetryAt) {
      health.noPermission = false;
    }

    if (isTokenHealthy(health, now)) {
      shared.assignedIndex = idx; // fixa o escolhido
      return { tokenCfg, ch, health, idx };
    }
  }

  return null; // todos bloqueados
}

// ─── Tick principal ───────────────────────────────────────────────────────────

async function tick() {
  if (!_isRunning) return;

  let config;
  try {
    config = await Divulgacao.findOne().lean();
  } catch {
    return;
  }

  if (!config || !config.isRunning) {
    await stopService();
    return;
  }

  const now = Date.now();

  // ── 1. Agrupa tokens ativos por canal ──────────────────────────────────────
  //
  // Monta um mapa: channelId → [ { tokenCfg, ch } ]
  // Isso é o coração da coordenação: sabemos quantos tokens disputam cada canal.

  /** @type {Map<string, Array<{tokenCfg: object, ch: object}>>} */
  const channelCandidates = new Map();

  for (const tokenCfg of config.tokens) {
    if (!tokenCfg.isActive || !tokenCfg.isValid) continue;

    for (const ch of tokenCfg.channels) {
      if (!ch.enabled) continue;

      if (!channelCandidates.has(ch.channelId)) {
        channelCandidates.set(ch.channelId, []);
      }
      channelCandidates.get(ch.channelId).push({ tokenCfg, ch });
    }
  }

  // ── 2. Processa cada canal de forma coordenada ─────────────────────────────

  for (const [channelId, candidates] of channelCandidates) {
    const shared = getChannelShared(channelId);

    // Precisamos de pelo menos 1 token para monitorar o canal
    // Usamos o primeiro saudável disponível para leitura (não necessariamente o da vez)
    const readerCandidate = candidates.find(({ tokenCfg, ch }) =>
      isTokenHealthy(getTokenHealth(tokenCfg.id, ch.channelId), now)
    );
    if (!readerCandidate) continue;

    const readerToken = readerCandidate.tokenCfg.token;

    // ── Detecta slowmode do canal (usa configuração do primeiro candidate) ──
    const slowmode = readerCandidate.ch.slowmode ?? 0;

    if (slowmode === 0) {
      // ── MODO SEM SLOWMODE: envia uma vez, depois monitora respostas de terceiros ──

      if (shared.waitingForReply) {
        // Monitora se alguém além das nossas contas enviou mensagem
        const lastMsg = await fetchLastMessage(readerToken, channelId).catch(() => null);
        if (!lastMsg) continue;

        const isOurMessage = candidates.some(
          ({ tokenCfg }) => tokenCfg.userId && lastMsg.author?.id === tokenCfg.userId
        );

        if (!isOurMessage && lastMsg.id !== shared.lastExternalId) {
          // Nova mensagem de terceiro detectada → acorda o próximo token da fila
          shared.lastExternalId = lastMsg.id;
          shared.waitingForReply = false;
          shared.nextSendAt = now;

          // avança o rodízio para que a PRÓXIMA conta envie
          shared.assignedIndex = (shared.assignedIndex + 1) % candidates.length;

          const label = readerCandidate.tokenCfg.label || readerCandidate.tokenCfg.username;
          addLog("info", label, channelId, `Nova mensagem de terceiro detectada — escalando próximo token`);
        }
        continue;
      }

      // Ainda não enviou neste ciclo (ou está esperando o tempo certo)
      if (now < shared.nextSendAt) continue;

      const picked = pickNextToken(candidates, shared, now);
      if (!picked) continue; // todos bloqueados

      const { tokenCfg, ch, health } = picked;
      const label = tokenCfg.label || tokenCfg.username;

      try {
        await sendMessage(tokenCfg.token, channelId, config.message);

        // Lê o ID da mensagem que acabou de ser enviada
        const lastMsg = await fetchLastMessage(tokenCfg.token, channelId).catch(() => null);
        shared.lastSentMsgId = lastMsg?.id ?? null;
        shared.lastExternalId = lastMsg?.id ?? null;
        shared.waitingForReply = true; // aguarda próxima mensagem de terceiro
        health.blockedUntil = null;
        health.noPermission = false;

        addLog("success", label, channelId,
          `[${picked.idx + 1}/${candidates.length}] Enviado (sem slowmode) — aguardando resposta de terceiro`);
        await Divulgacao.updateOne({}, { $inc: { totalSent: 1 } });

      } catch (err) {
        handleSendError({ err, health, shared, label, channelId, candidates, now, slowmode: 0 });
        if (err.status !== 403 && err.status !== 429 && !err.retryAfter) {
          await Divulgacao.updateOne({}, { $inc: { totalErrors: 1 } });
        }
      }

    } else {
      // ── MODO SLOWMODE: apenas UM token envia por rodada, respeitando o intervalo ──

      if (now < shared.nextSendAt) continue;

      const picked = pickNextToken(candidates, shared, now);
      if (!picked) continue;

      const { tokenCfg, ch, health, idx } = picked;
      const label = tokenCfg.label || tokenCfg.username;

      try {
        await sendMessage(tokenCfg.token, channelId, config.message);

        // Próximo envio: respeita o slowmode + avança o rodízio para a próxima conta
        shared.nextSendAt = now + slowmode * 1000;
        shared.assignedIndex = (idx + 1) % candidates.length;
        health.blockedUntil = null;
        health.noPermission = false;

        addLog("success", label, channelId,
          `[${idx + 1}/${candidates.length}] Enviado — próximo em ${slowmode}s` +
          (candidates.length > 1 ? ` (próxima conta: ${candidates[shared.assignedIndex]?.tokenCfg?.label || "?"})` : "")
        );

        await Divulgacao.updateOne({}, { $inc: { totalSent: 1 } });
        await Divulgacao.updateOne(
          { "tokens.id": tokenCfg.id, "tokens.channels.channelId": channelId },
          { $set: { "tokens.$[t].channels.$[c].lastSentAt": new Date() } },
          { arrayFilters: [{ "t.id": tokenCfg.id }, { "c.channelId": channelId }] }
        );

      } catch (err) {
        handleSendError({ err, health, shared, label, channelId, candidates, now, slowmode, idx });
        if (err.status !== 403 && err.status !== 429 && !err.retryAfter) {
          await Divulgacao.updateOne({}, { $inc: { totalErrors: 1 } });
          shared.nextSendAt = now + 10_000; // pequeno backoff em erro genérico
        }
      }
    }
  }
}

// ─── Tratamento de erros de envio ─────────────────────────────────────────────

/**
 * Centraliza o tratamento de erros de sendMessage para ambos os modos.
 * Atualiza o estado de saúde do token e o estado compartilhado do canal.
 */
function handleSendError({ err, health, shared, label, channelId, candidates, now, slowmode, idx }) {
  if (err.status === 403) {
    health.noPermission = true;
    health.noPermissionRetryAt = now + 10 * 60 * 1000;

    if (slowmode > 0) {
      // tenta avançar para a próxima conta imediatamente
      shared.assignedIndex = ((idx ?? shared.assignedIndex) + 1) % candidates.length;
      shared.nextSendAt = now; // tenta de novo agora com outro token
    }

    addLog("warn", label, channelId,
      `Sem permissão (${err.discordCode ?? 403}) — pausado 10 min` +
      (candidates.length > 1 ? `, tentando próxima conta` : "")
    );

  } else if (err.status === 429 || err.retryAfter) {
    const waitMs = err.retryAfter ? Math.ceil(err.retryAfter * 1000) : 60_000;
    health.blockedUntil = now + waitMs;

    if (slowmode > 0) {
      // tenta avançar para a próxima conta enquanto essa espera
      shared.assignedIndex = ((idx ?? shared.assignedIndex) + 1) % candidates.length;
      shared.nextSendAt = now; // tenta outra conta já
    }

    addLog("warn", label, channelId,
      `Rate-limit — aguardando ${Math.ceil(waitMs / 1000)}s (${err.discordCode ?? 429})` +
      (candidates.length > 1 ? `, tentando próxima conta` : "")
    );

  } else {
    addLog("error", label, channelId, `Erro: ${err.message}`);
  }
}

// ─── Ciclo de vida do serviço ─────────────────────────────────────────────────

export async function startService() {
  if (_isRunning) return;
  _isRunning = true;
  _channelShared.clear();
  _tokenChannelHealth.clear();
  await Divulgacao.updateOne({}, { $set: { isRunning: true, startedAt: new Date() } }, { upsert: true });
  addLog("info", "sistema", "", "Serviço iniciado");
  _loopHandle = setInterval(tick, 3000);
}

export async function stopService() {
  if (!_isRunning) return;
  _isRunning = false;
  if (_loopHandle) clearInterval(_loopHandle);
  _loopHandle = null;
  _channelShared.clear();
  _tokenChannelHealth.clear();
  await Divulgacao.updateOne({}, { $set: { isRunning: false, stoppedAt: new Date() } });
  addLog("info", "sistema", "", "Serviço parado");
}

export async function initService() {
  try {
    const cfg = await Divulgacao.findOne().lean();
    if (cfg?.isRunning) {
      await startService();
      console.log("[Divulgacao] Serviço retomado após restart");
    }
  } catch {}
}