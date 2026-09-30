import crypto from 'crypto';
import { URL } from 'url';
import dns from 'dns/promises';
import Webhook from '../database/models/Webhook.js';
import Register from '../database/models/Register.js';
import { generateUniqueId } from './security.js';

// Blocos CIDR privados e loopback que não podem ser alvo de webhook
const BLOCKED_CIDRS = [
  [0x7f000000, 0xff000000],   // 127.0.0.0/8  loopback
  [0x0a000000, 0xff000000],   // 10.0.0.0/8
  [0xac100000, 0xfff00000],   // 172.16.0.0/12
  [0xc0a80000, 0xffff0000],   // 192.168.0.0/16
  [0xa9fe0000, 0xffff0000],   // 169.254.0.0/16 link-local (AWS IMDS)
  [0x64400000, 0xffc00000],   // 100.64.0.0/10 shared address space
  [0xe0000000, 0xf0000000],   // 224.0.0.0/4  multicast
];

/**
 * Converte IPv4 string para inteiro de 32 bits
 */
function ipToInt(ip) {
  return ip.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet, 10), 0) >>> 0;
}

/**
 * Retorna true se o IP for privado/loopback/reservado
 */
function isBlockedIP(ip) {
  // IPv6 loopback ou link-local
  if (ip === '::1' || ip.startsWith('fe80') || ip.startsWith('fc') || ip.startsWith('fd')) return true;
  // IPv4-mapped IPv6
  const v4mapped = ip.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
  const v4 = v4mapped ? v4mapped[1] : ip;
  if (!/^\d+\.\d+\.\d+\.\d+$/.test(v4)) return false; // IPv6 puro — não bloquear aqui
  const n = ipToInt(v4);
  return BLOCKED_CIDRS.some(([base, mask]) => (n & mask) === base);
}

/**
 * Valida URL de webhook contra SSRF
 * Lança Error se a URL for interna/inválida
 */
async function assertSafeWebhookUrl(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error('URL de webhook inválida');
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('Apenas protocolos http/https são permitidos para webhooks');
  }

  const hostname = parsed.hostname;

  // Bloquear hostnames obviamente internos
  if (hostname === 'localhost' || hostname.endsWith('.local') || hostname.endsWith('.internal')) {
    throw new Error('URL de webhook aponta para host interno');
  }

  // Resolver DNS e verificar IPs resultantes
  let addresses = [];
  try {
    const [v4s, v6s] = await Promise.allSettled([
      dns.resolve4(hostname),
      dns.resolve6(hostname),
    ]);
    if (v4s.status === 'fulfilled') addresses.push(...v4s.value);
    if (v6s.status === 'fulfilled') addresses.push(...v6s.value);
  } catch {
    throw new Error('Não foi possível resolver o hostname do webhook');
  }

  if (addresses.length === 0) throw new Error('Hostname do webhook não resolve');

  for (const addr of addresses) {
    if (isBlockedIP(addr)) {
      throw new Error('URL de webhook aponta para endereço IP privado/reservado');
    }
  }
}

export { assertSafeWebhookUrl };

/**
 * Gera assinatura HMAC-SHA256 do payload
 */
function generateSignature(payload, apiKey) {
  const payloadString = JSON.stringify(payload);
  const signature = crypto
    .createHmac('sha256', apiKey)
    .update(payloadString)
    .digest('hex');
  return `sha256=${signature}`;
}

/**
 * Envia um webhook para a URL configurada
 */
async function sendWebhook(webhookRecord) {
  try {
    const { url, payload, signature } = webhookRecord;
    const timestamp = Math.floor(Date.now() / 1000);

    // Validar URL contra SSRF antes de fazer a requisição
    try {
      await assertSafeWebhookUrl(url);
    } catch (ssrfErr) {
      console.error(`[Webhook] ❌ URL bloqueada (SSRF): ${ssrfErr.message}`);
      await Webhook.findByIdAndUpdate(webhookRecord._id, {
        $set: {
          status: 'failed',
          error: `SSRF bloqueado: ${ssrfErr.message}`,
          attempts: webhookRecord.attempts + 1,
          lastAttemptAt: new Date(),
        }
      });
      return { success: false, error: ssrfErr.message };
    }

    console.log(`[Webhook] Enviando HTTP POST para: ${url}`);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Amethys-Wallet-API/1.0',
        'X-Webhook-Timestamp': timestamp.toString(),
        'X-Webhook-Signature': signature,
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000), // 10 segundos timeout
    });

    console.log(`[Webhook] Resposta recebida: HTTP ${response.status}`);

    const responseText = await response.text();
    let responseBody = responseText;
    try {
      responseBody = JSON.parse(responseText);
    } catch (e) {
      // Manter como string se não for JSON
    }

    // Atualizar registro do webhook
    const update = {
      attempts: webhookRecord.attempts + 1,
      lastAttemptAt: new Date(),
      responseStatus: response.status,
      responseBody: typeof responseBody === 'string' ? responseBody.substring(0, 500) : JSON.stringify(responseBody).substring(0, 500),
    };

    // Se resposta 2xx, marcar como sucesso
    if (response.status >= 200 && response.status < 300) {
      update.status = 'success';
      update.error = null;
      console.log(`[Webhook] ✅ Webhook entregue com sucesso!`);
    } else if (response.status >= 400 && response.status < 500) {
      // Erros 4xx não são reenviados
      update.status = 'failed';
      update.error = `HTTP ${response.status}: ${typeof responseBody === 'string' ? responseBody : JSON.stringify(responseBody)}`;
      console.log(`[Webhook] ❌ Webhook falhou (4xx): ${update.error}`);
    } else {
      // Erros 5xx ou outros - agendar retentativa
      update.status = 'pending';
      update.error = `HTTP ${response.status}`;

      // Calcular próximo retry com backoff exponencial
      const attemptNumber = update.attempts;
      const baseDelay = 2000; // 2 segundos
      const delay = baseDelay * Math.pow(2, attemptNumber - 1);
      update.nextRetryAt = new Date(Date.now() + delay);
      console.log(`[Webhook] ⚠️ Webhook pendente (5xx), retry em ${delay / 1000}s`);
    }

    await Webhook.findByIdAndUpdate(webhookRecord._id, { $set: update });

    return {
      success: response.status >= 200 && response.status < 300,
      status: response.status,
      response: responseBody,
    };

  } catch (error) {
    console.error(`[Webhook] ❌ Erro de rede/timeout: ${error.message}`);

    // Erro de rede, timeout, etc - agendar retentativa
    const attemptNumber = webhookRecord.attempts + 1;
    const baseDelay = 2000;
    const delay = baseDelay * Math.pow(2, attemptNumber - 1);
    const nextRetryAt = new Date(Date.now() + delay);

    const update = {
      attempts: attemptNumber,
      lastAttemptAt: new Date(),
      status: attemptNumber >= (webhookRecord.maxAttempts || 5) ? 'failed' : 'pending',
      error: error.message || String(error),
      nextRetryAt: attemptNumber >= (webhookRecord.maxAttempts || 5) ? null : nextRetryAt,
    };

    await Webhook.findByIdAndUpdate(webhookRecord._id, { $set: update });

    return {
      success: false,
      error: error.message || String(error),
    };
  }
}

/**
 * Cria e envia um webhook
 * @param {string} userId - ID do usuário
 * @param {string} event - Nome do evento
 * @param {object} data - Dados do evento
 * @param {object} apiKeyInfo - Informações da API Key usada (opcional)
 */
export async function sendWebhookEvent(userId, event, data, apiKeyInfo = null) {
  try {
    console.log(`[Webhook] Iniciando envio de webhook para evento: ${event}`);

    // Buscar usuário para obter webhookUrl e apiKey
    const user = await Register.findOne({ id: userId });

    if (!user) {
      console.log(`[Webhook] Usuário não encontrado: ${userId}`);
      return { sent: false, reason: 'user_not_found' };
    }

    console.log(`[Webhook] Usuário encontrado: ${user.email}`);

    // Determinar qual webhookUrl e apiKey usar
    let webhookUrl = null;
    let apiKeyForSignature = null;

    // Se apiKeyInfo fornecido e é uma API key secundária com webhookUrl próprio
    if (apiKeyInfo && apiKeyInfo.type === 'secondary' && apiKeyInfo.index !== undefined) {
      const secondaryKey = user.apiKeys && user.apiKeys[apiKeyInfo.index];
      if (secondaryKey && secondaryKey.webhookUrl) {
        webhookUrl = secondaryKey.webhookUrl;
        apiKeyForSignature = secondaryKey.key;
        console.log(`[Webhook] Usando URL da API Key secundária`);
      }
    }

    // Se não encontrou webhookUrl específico, usar o principal
    if (!webhookUrl) {
      webhookUrl = user.webhookUrl;
      apiKeyForSignature = user.apiKey;
    }

    console.log(`[Webhook] URL configurada: ${webhookUrl || 'NENHUMA'}`);

    // Se ainda não tem webhookUrl, não enviar
    if (!webhookUrl) {
      console.log(`[Webhook] Sem webhookUrl configurada para usuário ${user.email}`);
      return { sent: false, reason: 'no_webhook_url' };
    }

    // Extrair o tipo do evento (e.g., 'payment.approved' -> 'payment')
    const type = event.split('.')[0];

    const payload = {
      type,
      event,
      data,
      timestamp: Date.now(),
    };

    console.log(`[Webhook] Payload: ${JSON.stringify(payload).substring(0, 200)}...`);

    // Gerar assinatura usando a API Key apropriada
    const signature = generateSignature(payload, apiKeyForSignature);

    // Criar registro do webhook
    const webhookId = generateUniqueId();
    const webhookRecord = await Webhook.create({
      id: webhookId,
      userId,
      event,
      url: webhookUrl,
      payload,
      signature,
      status: 'pending',
      attempts: 0,
      maxAttempts: 5,
      nextRetryAt: new Date(), // Tentar imediatamente
    });

    console.log(`[Webhook] Registro criado: ${webhookId}`);

    // Tentar enviar imediatamente
    const result = await sendWebhook(webhookRecord);

    console.log(`[Webhook] Resultado do envio: ${result.success ? 'SUCESSO' : 'FALHA'} - Status: ${result.status || result.error}`);

    return {
      sent: result.success,
      webhookId,
      result,
    };

  } catch (error) {
    console.error(`❌ Erro ao criar webhook para evento ${event}:`, error);
    return {
      sent: false,
      error: error.message,
    };
  }
}

/**
 * Processa webhooks pendentes (para retentativas)
 */
export async function processPendingWebhooks() {
  try {
    const pendingWebhooks = await Webhook.getPending();

    if (pendingWebhooks.length === 0) {
      return { processed: 0, succeeded: 0, failed: 0 };
    }

    console.log(`📤 Processando ${pendingWebhooks.length} webhook(s) pendente(s)...`);

    let succeeded = 0;
    let failed = 0;

    for (const webhook of pendingWebhooks) {
      const result = await sendWebhook(webhook);

      if (result.success) {
        succeeded++;
      } else {
        failed++;
      }

      // Pequeno delay entre requisições para não sobrecarregar
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    console.log(`✅ Webhooks processados: ${succeeded} sucesso(s), ${failed} falha(s)`);

    return {
      processed: pendingWebhooks.length,
      succeeded,
      failed,
    };

  } catch (error) {
    console.error('❌ Erro ao processar webhooks pendentes:', error);
    return { processed: 0, succeeded: 0, failed: 0 };
  }
}

/**
 * Inicia o scheduler de retentativas de webhooks
 */
export function startWebhookScheduler(intervalMs = 60000) {
  console.log(`📤 Iniciando scheduler de webhooks`);
  console.log(`   - Intervalo entre verificações: ${intervalMs / 1000}s`);
  console.log(`   - Retentativas com backoff exponencial (máx 5 tentativas)`);

  // Executar imediatamente
  processPendingWebhooks();

  // Executar periodicamente
  const interval = setInterval(async () => {
    await processPendingWebhooks();
  }, intervalMs);

  return interval;
}

/**
 * Verifica assinatura de webhook (para testes ou validação)
 */
export function verifyWebhookSignature(payload, signature, apiKey) {
  const expectedSignature = generateSignature(payload, apiKey);
  return signature === expectedSignature;
}
