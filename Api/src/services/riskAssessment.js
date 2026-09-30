/**
 * riskAssessment.js
 * Sistema de avaliação de risco para detectar alt-accounts, VPN, proxy, bots, etc.
 * Retorna um score de 0 (confiável) a 100 (suspeito).
 */

import fetch from "node-fetch";
import User from "../database/models/User.js";

// ─── Constantes de peso ────────────────────────────────────────────────────────
const WEIGHTS = {
  ACCOUNT_TOO_YOUNG: 35,        // Conta criada recentemente
  KNOWN_VPN_IP: 25,             // IP em lista de VPN/proxy/datacenter
  MULTIPLE_ACCOUNTS_SAME_IP: 20, // Vários usuários no mesmo IP
  DISCORD_NEW_ACCOUNT: 15,      // Discord ID recente (Snowflake jovem)
  NO_EMAIL: 5,                  // Sem e-mail verificado
  DISPOSABLE_EMAIL: 10,         // E-mail descartável
  RAPID_LOGIN: 10,              // Login muito rápido (< 30s após registro)
};

/**
 * Extrai o timestamp de criação de um Discord Snowflake ID
 * Discord Epoch: 1420070400000 (Jan 1, 2015)
 */
function snowflakeToDate(snowflake) {
  try {
    const id = BigInt(snowflake);
    const timestamp = Number(id >> 22n) + 1420070400000;
    return new Date(timestamp);
  } catch {
    return null;
  }
}

/**
 * Verifica se um IP é VPN/proxy/datacenter usando ipinfo.io ou proxycheck.io
 * Usa duas fontes para melhor cobertura.
 */
async function checkIPReputation(ip) {
  if (!ip || ip === "unknown" || ip === "::1" || ip === "127.0.0.1") {
    return { isVpn: false, isProxy: false, isDatacenter: false, org: null, country: null };
  }

  const results = { isVpn: false, isProxy: false, isDatacenter: false, org: null, country: null };

  // Fonte 1: ipinfo.io (gratuito sem key para uso limitado)
  try {
    const res = await fetch(`https://ipinfo.io/${ip}/json`, {
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      results.org = data.org || null;
      results.country = data.country || null;

      // Datacenter/VPN por ASN/org conhecidos
      const org = (data.org || "").toLowerCase();
      const DATACENTER_ORGS = [
        "digitalocean", "linode", "vultr", "amazon", "google", "microsoft",
        "cloudflare", "ovh", "hetzner", "contabo", "hostinger", "leaseweb",
        "choopa", "quadranet", "psychz", "m247", "mullvad", "nordvpn",
        "expressvpn", "surfshark", "protonvpn", "ipvanish", "cyberghost",
        "torguard", "hidemyass", "privateinternetaccess", "windscribe",
        "tunnelbear", "hotspot shield", "hide.me", "perfect privacy",
      ];
      if (DATACENTER_ORGS.some((d) => org.includes(d))) {
        results.isDatacenter = true;
        results.isVpn = true;
      }
    }
  } catch {
    // falha silenciosa
  }

  // Fonte 2: proxycheck.io (gratuito, 1000/dia)
  try {
    const res = await fetch(
      `https://proxycheck.io/v2/${ip}?vpn=1&asn=1&risk=1&port=1&seen=1`,
      { signal: AbortSignal.timeout(3000) }
    );
    if (res.ok) {
      const data = await res.json();
      const ipData = data[ip];
      if (ipData) {
        if (ipData.proxy === "yes" || ipData.type === "VPN" || ipData.type === "TOR") {
          results.isVpn = true;
          results.isProxy = true;
        }
        if (ipData.risk && Number(ipData.risk) > 66) {
          results.isProxy = true;
        }
      }
    }
  } catch {
    // falha silenciosa
  }

  return results;
}

/**
 * Verifica domínios de e-mail descartáveis
 */
function isDisposableEmail(email) {
  if (!email) return false;
  const domain = email.split("@")[1]?.toLowerCase() || "";
  const DISPOSABLE = [
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "temp-mail.org",
    "throwam.com", "trashmail.com", "fakeinbox.com", "yopmail.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la", "guerrillamail.info",
    "spam4.me", "dispostable.com", "maildrop.cc", "discard.email",
    "spamgourmet.com", "anonaddy.com", "simplelogin.io", "duck.com",
  ];
  return DISPOSABLE.some((d) => domain === d || domain.endsWith(`.${d}`));
}

/**
 * Verifica quantas contas usaram o mesmo IP nas últimas 72h
 */
async function countAccountsFromIP(ip) {
  if (!ip || ip === "unknown") return 0;
  const since = new Date(Date.now() - 72 * 60 * 60 * 1000);
  try {
    const count = await User.countDocuments({
      "ipHistory.ip": ip,
      "ipHistory.dates": { $elemMatch: { $gte: since } },
    });
    return count;
  } catch {
    return 0;
  }
}

/**
 * Avalia o risco de um usuário para resgatar o bot gratuito
 * @param {object} params
 * @param {object} params.user - Documento do usuário (MongoDB)
 * @param {string} params.ip - IP da requisição
 * @param {number} params.minAccountAgeDays - Mínimo de dias da conta Discord
 * @returns {Promise<{score: number, reasons: string[], blocked: boolean, details: object}>}
 */
export async function assessRisk({ user, ip, minAccountAgeDays = 15 }) {
  let score = 0;
  const reasons = [];
  const details = {};

  // ─── 1. Idade da conta Discord (Snowflake) ─────────────────────────────────
  const discordCreatedAt = snowflakeToDate(user.discordId);
  details.discordCreatedAt = discordCreatedAt;

  if (discordCreatedAt) {
    const discordAgeDays = (Date.now() - discordCreatedAt.getTime()) / (1000 * 60 * 60 * 24);
    details.discordAgeDays = Math.floor(discordAgeDays);

    if (discordAgeDays < minAccountAgeDays) {
      score += WEIGHTS.ACCOUNT_TOO_YOUNG;
      reasons.push(
        `Conta Discord com apenas ${Math.floor(discordAgeDays)} dia(s) (mínimo: ${minAccountAgeDays})`
      );
    } else if (discordAgeDays < minAccountAgeDays * 2) {
      // Conta nova mas dentro do limite: adiciona score parcial
      score += Math.round(WEIGHTS.DISCORD_NEW_ACCOUNT * (1 - discordAgeDays / (minAccountAgeDays * 2)));
    }
  }

  // ─── 2. Verificação de IP (VPN, proxy, datacenter) ────────────────────────
  const ipReputation = await checkIPReputation(ip);
  details.ipReputation = ipReputation;

  if (ipReputation.isVpn || ipReputation.isProxy || ipReputation.isDatacenter) {
    score += WEIGHTS.KNOWN_VPN_IP;
    reasons.push(`IP suspeito detectado (VPN/Proxy/Datacenter: ${ipReputation.org || ip})`);
  }

  // ─── 3. Múltiplas contas no mesmo IP ──────────────────────────────────────
  const accountsFromIP = await countAccountsFromIP(ip);
  details.accountsFromIP = accountsFromIP;

  if (accountsFromIP > 3) {
    const extra = Math.min(accountsFromIP - 3, 5); // máximo de 5 contas extras
    const partialScore = Math.round((extra / 5) * WEIGHTS.MULTIPLE_ACCOUNTS_SAME_IP);
    score += partialScore;
    if (partialScore > 0) {
      reasons.push(`${accountsFromIP} contas detectadas no mesmo IP nas últimas 72h`);
    }
  }

  // ─── 4. E-mail descartável ────────────────────────────────────────────────
  if (!user.email) {
    score += WEIGHTS.NO_EMAIL;
    details.hasEmail = false;
  } else {
    details.hasEmail = true;
    if (isDisposableEmail(user.email)) {
      score += WEIGHTS.DISPOSABLE_EMAIL;
      reasons.push("E-mail descartável detectado");
      details.disposableEmail = true;
    }
  }

  // ─── 5. Conta criada no sistema muito recentemente ────────────────────────
  if (user.createdAt) {
    const sysAgeDays = (Date.now() - new Date(user.createdAt).getTime()) / (1000 * 60 * 60 * 24);
    details.sysAgeDays = Math.floor(sysAgeDays);
    if (sysAgeDays < 0.02) {
      // criado há menos de ~30 minutos
      score += WEIGHTS.RAPID_LOGIN;
      reasons.push("Conta no sistema criada há menos de 30 minutos");
    }
  }

  score = Math.min(score, 100);

  return {
    score,
    reasons,
    blocked: false, // quem decide bloquear é o caller
    details,
  };
}

/**
 * Verifica se a conta Discord tem idade mínima obrigatória.
 * Retorna { ok, ageDays, required }
 */
export function checkDiscordAccountAge(discordId, minDays) {
  const createdAt = snowflakeToDate(discordId);
  if (!createdAt) return { ok: false, ageDays: 0, required: minDays, createdAt: null };
  const ageDays = (Date.now() - createdAt.getTime()) / (1000 * 60 * 60 * 24);
  return {
    ok: ageDays >= minDays,
    ageDays: Math.floor(ageDays),
    required: minDays,
    createdAt,
  };
}