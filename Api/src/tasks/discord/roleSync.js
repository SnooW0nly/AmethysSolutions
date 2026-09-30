/**
 * src/tasks/discord/roleSync.js
 *
 * Task de sincronização de cargo de cliente no Discord.
 *
 * O que faz:
 *  - Busca todos os usuários com pelo menos uma aplicação ativa no banco
 *    (não deletada, não bloqueada) e que tenham discordId cadastrado.
 *  - Para cada um, verifica se está no servidor e se já possui o cargo
 *    configurado em `discord_default_role_id` (GlobalConfig / .env).
 *  - Se estiver no servidor mas SEM o cargo → atribui automaticamente.
 *  - Se NÃO tiver nenhuma aplicação ativa e TIVER o cargo → remove.
 *  - Respeita rate-limit do Discord (requisições sequenciais com delay).
 *  - Registra tudo via console com prefixo [ROLE SYNC].
 *
 * Uso:
 *   import { startRoleSync } from "./tasks/discord/roleSync.js";
 *   startRoleSync(); // chame uma vez ao subir o servidor
 */

import Application from "../../database/models/Application.js";
import User from "../../database/models/User.js";
import GlobalConfig from "../../database/models/GlobalConfig.js";
import { DISCORD_API, getBotAuthHeader } from "../../services/discord/puxarDiscord.js";

// ─── Configurações ────────────────────────────────────────────────────────────

/** Intervalo entre cada ciclo completo (padrão: 10 minutos) */
const CYCLE_INTERVAL_MS = 10 * 60 * 1000;

/** Delay entre cada requisição ao Discord para não estourar rate-limit */
const REQUEST_DELAY_MS = 500;

/** Timeout por requisição HTTP ao Discord */
const FETCH_TIMEOUT_MS = 10_000;

// ─── Estado interno ───────────────────────────────────────────────────────────

let _intervalId = null;
let _isRunning = false;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

/**
 * Resolve o roleId e guildId a partir do GlobalConfig, com fallback para .env.
 */
async function resolveDiscordConfig() {
  try {
    const { getDiscordConfig } = await import(
      "../../routes/admin/discord/discord-config.js"
    );
    const [roleId, guildId] = await Promise.all([
      getDiscordConfig("discord_default_role_id"),
      getDiscordConfig("discord_guild_id"),
    ]);
    return { roleId, guildId };
  } catch {
    return {
      roleId: process.env.DISCORD_DEFAULT_ROLE_ID || null,
      guildId: process.env.DISCORD_GUILD_ID || null,
    };
  }
}

/**
 * Busca o membro na guild via API do Discord.
 * Retorna o objeto do membro ou null se não estiver no servidor / erro.
 *
 * @param {string} userId
 * @param {string} guildId
 * @returns {Promise<{roles: string[]}|null>}
 */
async function fetchGuildMember(userId, guildId) {
  try {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    const res = await fetch(
      `${DISCORD_API}/v10/guilds/${guildId}/members/${userId}`,
      { headers: getBotAuthHeader(), signal: controller.signal }
    );
    clearTimeout(tid);

    if (res.status === 404) return null; // não está no servidor
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Adiciona o cargo ao membro.
 */
async function addRole(userId, guildId, roleId) {
  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  const res = await fetch(
    `${DISCORD_API}/v10/guilds/${guildId}/members/${userId}/roles/${roleId}`,
    { method: "PUT", headers: getBotAuthHeader(), signal: controller.signal }
  );
  clearTimeout(tid);
  if (!res.ok && res.status !== 204) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
}

/**
 * Remove o cargo do membro.
 */
async function removeRole(userId, guildId, roleId) {
  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  const res = await fetch(
    `${DISCORD_API}/v10/guilds/${guildId}/members/${userId}/roles/${roleId}`,
    { method: "DELETE", headers: getBotAuthHeader(), signal: controller.signal }
  );
  clearTimeout(tid);
  if (!res.ok && res.status !== 204) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
}

// ─── Ciclo principal ──────────────────────────────────────────────────────────

async function runRoleSyncCycle() {
  const cycleStart = Date.now();
  console.log("[ROLE SYNC] ▶ Iniciando ciclo de sincronização de cargos...");

  // 1. Resolve configuração
  const { roleId, guildId } = await resolveDiscordConfig();

  if (!roleId) {
    console.warn("[ROLE SYNC] ⚠ discord_default_role_id não configurado — abortando ciclo");
    return;
  }
  if (!guildId) {
    console.warn("[ROLE SYNC] ⚠ discord_guild_id não configurado — abortando ciclo");
    return;
  }

  // 2. Busca todos os usuários que têm pelo menos uma app ativa
  //    (não deletada, não bloqueada, não expirada)
  const now = new Date();

  const activeApps = await Application.find({
    isDeleted: false,
    isBlocked: false,
    $or: [{ expiresAt: null }, { expiresAt: { $gt: now } }],
  })
    .select("userId")
    .lean();

  // Conjunto de userIds (ObjectId → string) com app ativa
  const userIdsWithApp = new Set(activeApps.map((a) => String(a.userId)));

  // 3. Busca os usuários completos para pegar os discordIds
  const users = await User.find({
    _id: { $in: [...userIdsWithApp] },
    discordId: { $exists: true, $ne: null, $ne: "" },
    blocked: { $ne: true },
  })
    .select("_id discordId username")
    .lean();

  // 4. Busca usuários que NÃO têm app ativa (para possível remoção de cargo)
  //    Só buscamos quem estava ativo em algum momento (tem discordId)
  const usersWithoutApp = await User.find({
    _id: { $nin: [...userIdsWithApp] },
    discordId: { $exists: true, $ne: null, $ne: "" },
    blocked: { $ne: true },
  })
    .select("_id discordId username")
    .lean();

  const stats = {
    checked: 0,
    roleAdded: 0,
    roleRemoved: 0,
    notInServer: 0,
    alreadyCorrect: 0,
    errors: 0,
  };

  console.log(
    `[ROLE SYNC] 📋 Usuários com app ativa: ${users.length} | Sem app ativa: ${usersWithoutApp.length}`
  );

  // ── PARTE A: garantir que quem tem app tem o cargo ────────────────────────

  for (const user of users) {
    stats.checked++;
    try {
      const member = await fetchGuildMember(user.discordId, guildId);

      if (!member) {
        stats.notInServer++;
        continue; // não está no servidor, nada a fazer
      }

      const hasRole = Array.isArray(member.roles) && member.roles.includes(roleId);

      if (!hasRole) {
        await addRole(user.discordId, guildId, roleId);
        stats.roleAdded++;
        console.log(
          `[ROLE SYNC] ✅ Cargo adicionado → ${user.username ?? user.discordId} (${user.discordId})`
        );
      } else {
        stats.alreadyCorrect++;
      }
    } catch (err) {
      stats.errors++;
      console.error(
        `[ROLE SYNC] ✗ Erro ao processar ${user.discordId}:`,
        err.message
      );
    }

    await sleep(REQUEST_DELAY_MS);
  }

  // ── PARTE B: remover cargo de quem não tem mais app ativa ─────────────────

  for (const user of usersWithoutApp) {
    stats.checked++;
    try {
      const member = await fetchGuildMember(user.discordId, guildId);

      if (!member) {
        stats.notInServer++;
        continue;
      }

      const hasRole = Array.isArray(member.roles) && member.roles.includes(roleId);

      if (hasRole) {
        await removeRole(user.discordId, guildId, roleId);
        stats.roleRemoved++;
        console.log(
          `[ROLE SYNC] 🗑 Cargo removido → ${user.username ?? user.discordId} (${user.discordId}) — sem app ativa`
        );
      }
    } catch (err) {
      stats.errors++;
      console.error(
        `[ROLE SYNC] ✗ Erro ao processar remoção ${user.discordId}:`,
        err.message
      );
    }

    await sleep(REQUEST_DELAY_MS);
  }

  const elapsed = ((Date.now() - cycleStart) / 1000).toFixed(1);

  console.log(
    `[ROLE SYNC] ✔ Ciclo concluído em ${elapsed}s — ` +
    `verificados: ${stats.checked} | adicionados: ${stats.roleAdded} | ` +
    `removidos: ${stats.roleRemoved} | fora do servidor: ${stats.notInServer} | ` +
    `já corretos: ${stats.alreadyCorrect} | erros: ${stats.errors}`
  );
}

// ─── API pública ──────────────────────────────────────────────────────────────

/**
 * Inicia a task de sincronização de cargos.
 * Roda imediatamente e depois a cada CYCLE_INTERVAL_MS.
 */
export async function startRoleSync() {
  if (_intervalId) {
    console.warn("[ROLE SYNC] Serviço já está rodando");
    return;
  }

  console.log(
    `[ROLE SYNC] 🚀 Serviço iniciado — ciclo a cada ${CYCLE_INTERVAL_MS / 60_000} minutos`
  );

  // Primeiro ciclo imediato (com tratamento de erro para não travar o boot)
  runRoleSyncCycle().catch((err) =>
    console.error("[ROLE SYNC] Erro no ciclo inicial:", err.message)
  );

  _intervalId = setInterval(async () => {
    if (_isRunning) {
      console.warn("[ROLE SYNC] Ciclo anterior ainda em execução — pulando");
      return;
    }
    _isRunning = true;
    try {
      await runRoleSyncCycle();
    } catch (err) {
      console.error("[ROLE SYNC] Erro no ciclo:", err.message);
    } finally {
      _isRunning = false;
    }
  }, CYCLE_INTERVAL_MS);
}

/**
 * Para o serviço de sincronização de cargos.
 */
export function stopRoleSync() {
  if (_intervalId) {
    clearInterval(_intervalId);
    _intervalId = null;
  }
  _isRunning = false;
  console.log("[ROLE SYNC] Serviço parado");
}

/**
 * Força execução imediata de um ciclo (útil para testes / acionamento manual).
 */
export async function forceRoleSync() {
  console.log("[ROLE SYNC] 🔁 Execução forçada solicitada");
  await runRoleSyncCycle();
}