/**
 * src/services/revision/index.js
 *
 * Integração com a RevisionSMM via cookie de sessão.
 * Cookie é armazenado no MongoDB (RevisionConfig) e pode ser
 * atualizado pelo admin sem precisar reiniciar o servidor.
 */

import axios from "axios";
import * as cheerio from "cheerio";
import RevisionConfig from "../../database/models/RevisionConfig.js";

const BASE_URL = "https://revisionsmm.com";
const UA =
  "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36";

// ─── Helpers de config ────────────────────────────────────────────────────────

async function getConfig(key) {
  const doc = await RevisionConfig.findOne({ key }).lean();
  return doc?.value || null;
}

async function getCookie() {
  const cookie = await getConfig("revision_cookie");
  if (!cookie) throw new Error("Cookie da RevisionSMM não configurado. Acesse o painel admin.");
  return cookie;
}

async function getCpf() {
  return (await getConfig("revision_cpf")) || "000.000.000-00";
}

// ─── Headers padrão ───────────────────────────────────────────────────────────

function buildHeaders(cookie, extra = {}) {
  return {
    Cookie: cookie,
    "User-Agent": UA,
    Accept:
      "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    Host: "revisionsmm.com",
    Connection: "keep-alive",
    ...extra,
  };
}

// ─── Valida cookie ────────────────────────────────────────────────────────────

/**
 * Verifica se o cookie ainda é válido tentando acessar /addfunds.
 * Retorna { valid, balance, redirectedTo }
 */
export async function validateCookie(cookieOverride = null) {
  const cookie = cookieOverride || (await getCookie());

  try {
    const res = await axios.get(`${BASE_URL}/addfunds`, {
      headers: buildHeaders(cookie),
      maxRedirects: 0,
      validateStatus: (s) => s < 400,
    });

    const finalUrl = res.request?.res?.responseUrl || res.config?.url || "";
    const isLogin = finalUrl.includes("login") || res.status === 302;

    if (isLogin) {
      return { valid: false, balance: null, redirectedTo: finalUrl };
    }

    // Extrai saldo do HTML
    const $ = cheerio.load(res.data);
    let balance = null;

    // Tenta diferentes seletores comuns no RevisionSMM
    const selectors = [
      ".balance",
      "[class*='balance']",
      "[class*='saldo']",
      ".user-balance",
      ".navbar .amount",
    ];

    for (const sel of selectors) {
      const text = $(sel).first().text().trim();
      if (text && /[\d.,]+/.test(text)) {
        balance = text;
        break;
      }
    }

    // Fallback: regex no HTML bruto
    if (!balance) {
      const match = res.data.match(/(?:Saldo|Balance|R\$)\s*([\d.,]+)/i);
      if (match) balance = `R$ ${match[1]}`;
    }

    return { valid: true, balance, redirectedTo: null };
  } catch (err) {
    if (err.response?.status === 302 || err.response?.status === 301) {
      return {
        valid: false,
        balance: null,
        redirectedTo: err.response.headers?.location || "login",
      };
    }
    throw err;
  }
}

// ─── Extrai CSRF ──────────────────────────────────────────────────────────────

async function fetchCsrf(cookie) {
  const res = await axios.get(`${BASE_URL}/addfunds`, {
    headers: buildHeaders(cookie),
    maxRedirects: 5,
  });

  const finalUrl = res.request?.res?.responseUrl || "";
  if (finalUrl.includes("login")) {
    throw new Error("Cookie inválido ou expirado — redirecionou para o login");
  }

  // Captura cookies adicionais que o servidor possa ter setado
  const setCookies = res.headers["set-cookie"] || [];
  const extraCookies = setCookies.map((c) => c.split(";")[0]).join("; ");
  const updatedCookie = extraCookies ? `${cookie}; ${extraCookies}` : cookie;

  const $ = cheerio.load(res.data);
  const csrf =
    $('input[name="_csrf"]').val() ||
    $('meta[name="csrf-token"]').attr("content");

  if (!csrf) throw new Error("Token CSRF não encontrado na página");

  return { csrf, updatedCookie };
}

// ─── Adicionar saldo ──────────────────────────────────────────────────────────

/**
 * Adiciona saldo via PIX na RevisionSMM.
 * @param {number} amount  — valor em reais (ex: 13.00)
 * @param {string} cpf     — CPF do pagador (opcional, usa o do config)
 * @returns {Promise<{ success, data, raw }>}
 */
export async function addFunds(amount, cpfOverride = null) {
  const cookie = await getCookie();
  const cpf = cpfOverride || (await getCpf());

  const { csrf, updatedCookie } = await fetchCsrf(cookie);

  const payload = new URLSearchParams({
    "AddFoundsForm[type]": "150002",     // PIX
    "AddFoundsForm[amount]": String(Math.round(amount)), // Revision usa inteiro (centavos? não — parece R$ inteiro)
    "AddFoundsForm[fields][cpf_cnpj]": cpf,
    _csrf: csrf,
    save: "1",
  });

  try {
    const res = await axios.post(`${BASE_URL}/addfunds`, payload.toString(), {
      headers: buildHeaders(updatedCookie, {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json, text/javascript, */*; q=0.01",
        Origin: BASE_URL,
        Referer: `${BASE_URL}/addfunds`,
      }),
      maxRedirects: 0,
      validateStatus: () => true,
    });

    let data = res.data;
    if (typeof data === "string") {
      try {
        data = JSON.parse(data);
      } catch {
        data = { raw: data };
      }
    }

    // Sucesso esperado: resposta JSON com status/data
    const success =
      res.status === 200 &&
      !String(res.data).includes("Error 404") &&
      !String(res.data).includes("Error 403");

    return { success, data, status: res.status };
  } catch (err) {
    const status = err.response?.status;
    const data = err.response?.data;
    return { success: false, data, status, error: err.message };
  }
}

// ─── Listar serviços ──────────────────────────────────────────────────────────

/**
 * Busca a lista de serviços disponíveis na RevisionSMM via API pública.
 * RevisionSMM tem endpoint /api/v2 igual a SMM panels padrão.
 */
export async function listServices() {
  const cookie = await getCookie();

  // Tenta API v2 (padrão SMM panel)
  try {
    const res = await axios.get(`${BASE_URL}/api/v2`, {
      params: { action: "services" },
      headers: buildHeaders(cookie, {
        Accept: "application/json",
      }),
      timeout: 15000,
    });

    if (Array.isArray(res.data)) {
      // Filtra apenas serviços de membros Discord
      const discordServices = res.data.filter(
        (s) =>
          /discord/i.test(s.name || s.category || "") &&
          /member/i.test(s.name || "")
      );
      return { success: true, services: res.data, discordMemberServices: discordServices };
    }
  } catch {
    // fallback: tenta scraping da página de pedido
  }

  // Fallback: scraping da página /neworder
  try {
    const res = await axios.get(`${BASE_URL}/neworder`, {
      headers: buildHeaders(cookie),
      timeout: 15000,
    });
    const $ = cheerio.load(res.data);
    const services = [];
    $("option[value]").each((_, el) => {
      const val = $(el).val();
      const text = $(el).text().trim();
      if (val && /^\d+$/.test(val)) {
        services.push({ service: val, name: text });
      }
    });
    return { success: true, services, discordMemberServices: services };
  } catch (err) {
    return { success: false, services: [], error: err.message };
  }
}

// ─── Verificar saldo atual ────────────────────────────────────────────────────

export async function getBalance() {
  const { valid, balance } = await validateCookie();
  return { valid, balance };
}

// ─── Fazer pedido ─────────────────────────────────────────────────────────────

/**
 * Cria um pedido na RevisionSMM via API v2.
 * @param {object} params
 * @param {string} params.serviceId   — ID do serviço
 * @param {string} params.link        — Link do servidor Discord
 * @param {number} params.quantity    — Quantidade de membros
 */
export async function placeOrder({ serviceId, link, quantity }) {
  const cookie = await getCookie();

  // Tenta via API v2 primeiro
  try {
    const res = await axios.post(
      `${BASE_URL}/api/v2`,
      new URLSearchParams({
        action: "add",
        service: String(serviceId),
        link,
        quantity: String(quantity),
      }).toString(),
      {
        headers: buildHeaders(cookie, {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        }),
        timeout: 20000,
      }
    );

    const data = res.data;
    if (data?.order) {
      return { success: true, orderId: String(data.order), raw: data };
    }
    if (data?.error) {
      return { success: false, error: data.error, raw: data };
    }
    return { success: false, error: "Resposta inesperada da API", raw: data };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// ─── Verificar status do pedido ───────────────────────────────────────────────

export async function checkOrderStatus(orderId) {
  const cookie = await getCookie();

  try {
    const res = await axios.post(
      `${BASE_URL}/api/v2`,
      new URLSearchParams({
        action: "status",
        order: String(orderId),
      }).toString(),
      {
        headers: buildHeaders(cookie, {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        }),
        timeout: 15000,
      }
    );

    return { success: true, data: res.data };
  } catch (err) {
    return { success: false, error: err.message };
  }
}