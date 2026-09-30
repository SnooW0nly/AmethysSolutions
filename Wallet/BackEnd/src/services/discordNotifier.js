/**
 * Serviço de notificações via Discord Webhook
 */

const DISCORD_WEBHOOKS = {
    RATE_LIMIT: process.env.DISCORD_WEBHOOK_RATE_LIMIT,
    PAYMENTS: process.env.DISCORD_WEBHOOK_PAYMENTS,
    TRANSFERS: process.env.DISCORD_WEBHOOK_TRANSFERS,
    REGISTERS: process.env.DISCORD_WEBHOOK_REGISTERS,
    LOGINS: process.env.DISCORD_WEBHOOK_LOGINS,
    REQUESTS: process.env.DISCORD_WEBHOOK_REQUESTS,
};

// Nomes de bot por tipo de webhook
const WEBHOOK_NAMES = {
    RATE_LIMIT: 'Rate Limiter',
    PAYMENTS: 'Pagamentos',
    TRANSFERS: 'Transferências',
    REGISTERS: 'Registros',
    LOGINS: 'Logins',
    REQUESTS: 'API Requests'
};

/**
 * Retorna timestamp em horário de Brasília formatado
 */
function getBrasiliaTime() {
    return new Date().toLocaleString('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        dateStyle: 'short',
        timeStyle: 'medium'
    });
}

// ========== Sistema de Queue e Retry ==========

// Filas por webhook para rate limiting
const queues = {
    RATE_LIMIT: [],
    PAYMENTS: [],
    TRANSFERS: [],
    REGISTERS: [],
    LOGINS: [],
    REQUESTS: []
};

// Flags de processamento
const processing = {
    RATE_LIMIT: false,
    PAYMENTS: false,
    TRANSFERS: false,
    REGISTERS: false,
    LOGINS: false,
    REQUESTS: false
};

// Delay entre mensagens (Discord rate limit: 30 req/min por webhook)
const MESSAGE_DELAY = 2100; // 2.1 segundos (safe margin)

/**
 * Envia notificação com retry automático
 * @param {string} webhookUrl - URL do webhook
 * @param {object} payload - Payload completo (com username e embeds)
 * @param {number} retries - Número de tentativas restantes
 */
async function sendWithRetry(webhookUrl, payload, retries = 3) {
    try {
        const response = await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            return true;
        }

        // Rate limited - esperar e tentar novamente
        if (response.status === 429) {
            const retryAfter = parseInt(response.headers.get('retry-after') || '5') * 1000;
            console.warn(`[DISCORD] Rate limited, aguardando ${retryAfter}ms...`);
            await sleep(retryAfter);
            if (retries > 0) {
                return sendWithRetry(webhookUrl, embed, retries - 1);
            }
        }

        // Outros erros - retry com backoff
        if (retries > 0) {
            const backoff = (4 - retries) * 2000; // 2s, 4s, 6s
            console.warn(`[DISCORD] Erro ${response.status}, retry em ${backoff}ms...`);
            await sleep(backoff);
            return sendWithRetry(webhookUrl, embed, retries - 1);
        }

        console.error(`[DISCORD] Falha após retries: ${response.status}`);
        return false;
    } catch (error) {
        if (retries > 0) {
            const backoff = (4 - retries) * 2000;
            console.warn(`[DISCORD] Erro de rede, retry em ${backoff}ms: ${error.message}`);
            await sleep(backoff);
            return sendWithRetry(webhookUrl, embed, retries - 1);
        }
        console.error('[DISCORD] Falha após retries:', error.message);
        return false;
    }
}

/**
 * Sleep helper
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Processa a fila de um webhook específico
 */
async function processQueue(queueName) {
    if (processing[queueName] || queues[queueName].length === 0) {
        return;
    }

    processing[queueName] = true;

    while (queues[queueName].length > 0) {
        const { webhookUrl, embed } = queues[queueName].shift();
        await sendWithRetry(webhookUrl, embed);

        // Delay entre mensagens para evitar rate limit
        if (queues[queueName].length > 0) {
            await sleep(MESSAGE_DELAY);
        }
    }

    processing[queueName] = false;
}

/**
 * Adiciona notificação à fila e inicia processamento
 */
function queueNotification(queueName, webhookUrl, embed) {
    queues[queueName].push({ webhookUrl, embed });

    // Iniciar processamento se não estiver rodando
    if (!processing[queueName]) {
        processQueue(queueName);
    }
}

/**
 * Envia notificação para webhook Discord (com queue e retry)
 */
function sendDiscordNotification(webhookUrl, embed, queueName = 'PAYMENTS') {
    // Adicionar horário de Brasília no footer
    embed.footer = { text: `${embed.footer?.text || 'Amethys Wallet'} • ${getBrasiliaTime()}` };

    // Criar payload com nome do bot
    const payload = {
        username: WEBHOOK_NAMES[queueName] || 'Amethys Wallet',
        embeds: [embed]
    };

    queueNotification(queueName, webhookUrl, payload);
}

/**
 * Notifica rate limit atingido
 */
export async function notifyRateLimit({ apiKey, email, endpoint, limit, windowMs, ip }) {
    const embed = {
        title: 'Rate Limit Atingido',
        color: 0xFF0000,
        fields: [
            { name: 'Email', value: email || 'N/A', inline: true },
            { name: 'API Key', value: `\`${apiKey || 'N/A'}\``, inline: false },
            { name: 'Endpoint', value: endpoint || 'N/A', inline: true },
            { name: 'Limite', value: `${limit} req/${Math.round(windowMs / 1000)}s`, inline: true },
            { name: 'IP', value: ip || 'N/A', inline: true }
        ],
        footer: { text: 'Rate Limiter' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.RATE_LIMIT, embed, 'RATE_LIMIT');
}

/**
 * Notifica novo registro
 */
export async function notifyRegister({ email, name, taxID, category, tier, businessProfile, ip, userAgent }) {
    const fields = [
        { name: 'Email', value: email || 'N/A', inline: true },
        { name: 'Nome', value: name || 'N/A', inline: true },
        { name: 'CPF/CNPJ', value: taxID ? `${taxID.slice(0, 3)}***` : 'N/A', inline: true },
        { name: 'Categoria', value: category === 'BLACK' ? '⚫ BLACK' : `⚪ WHITE ${tier || 1}`, inline: true },
        { name: 'IP', value: ip || 'N/A', inline: true },
    ];

    // Adicionar dados do perfil de negócio se disponível
    if (businessProfile) {
        fields.push(
            { name: '📋 Nome do Negócio', value: businessProfile.businessName || 'N/A', inline: false },
            { name: '🌐 Site', value: businessProfile.website || 'Não informado', inline: true },
            { name: '📝 Descrição', value: businessProfile.description ? businessProfile.description.slice(0, 200) : 'N/A', inline: false },
            {
                name: '⚠️ Frequência MEDs', value: {
                    'NEVER': '✅ Nunca',
                    'RARELY': '🟡 Raramente',
                    'FREQUENTLY': '🔴 Frequentemente',
                    'ALWAYS': '🔴 Sempre'
                }[businessProfile.medFrequency] || 'N/A', inline: true
            }
        );
    }

    fields.push({ name: 'User Agent', value: userAgent ? userAgent.slice(0, 50) : 'N/A', inline: false });

    const embed = {
        title: 'Novo Registro',
        color: category === 'BLACK' ? 0x000000 : 0x9B59B6,
        fields,
        footer: { text: 'Registros' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.REGISTERS, embed, 'REGISTERS');
}

/**
 * Notifica login
 */
export async function notifyLogin({ email, name, ip, userAgent, method, success }) {
    const embed = {
        title: success ? 'Login Bem-sucedido' : 'Login Falhou',
        color: success ? 0x2ECC71 : 0xE74C3C,
        fields: [
            { name: 'Email', value: email || 'N/A', inline: true },
            { name: 'Nome', value: name || 'N/A', inline: true },
            { name: 'Método', value: method || 'Password', inline: true },
            { name: 'IP', value: ip || 'N/A', inline: true },
            { name: 'User Agent', value: userAgent ? userAgent.slice(0, 50) : 'N/A', inline: false }
        ],
        footer: { text: 'Logins' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.LOGINS, embed, 'LOGINS');
}

/**
 * Notifica request de API
 */
export async function notifyRequest({ email, endpoint, method, statusCode, responseTime, ip, apiKey }) {
    const embed = {
        title: `${method} ${endpoint}`,
        color: statusCode >= 200 && statusCode < 300 ? 0x3498DB : 0xE74C3C,
        fields: [
            { name: 'Email', value: email || 'N/A', inline: true },
            { name: 'Status', value: `${statusCode}`, inline: true },
            { name: 'Tempo', value: `${responseTime}ms`, inline: true },
            { name: 'IP', value: ip || 'N/A', inline: true },
            { name: 'API Key', value: apiKey ? `${apiKey.slice(0, 10)}...` : 'N/A', inline: true }
        ],
        footer: { text: 'API Requests' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.REQUESTS, embed, 'REQUESTS');
}

/**
 * Notifica pagamento aprovado
 */
export async function notifyPaymentApproved({ paymentId, email, value, fee, netValue, status, pixKey, plan, ip }) {
    const valueInReais = (value / 100).toFixed(2);
    const feeInReais = (fee / 100).toFixed(2);
    const netValueInReais = ((netValue || (value - fee)) / 100).toFixed(2);

    const embed = {
        title: 'Pagamento Aprovado',
        color: 0x00FF00,
        fields: [
            { name: 'Email', value: email || 'N/A', inline: true },
            { name: 'ID', value: `\`${paymentId}\``, inline: true },
            { name: 'Valor Bruto', value: `R$ ${valueInReais}`, inline: true },
            { name: 'Taxa', value: `R$ ${feeInReais}`, inline: true },
            { name: 'Valor Líquido', value: `R$ ${netValueInReais}`, inline: true },
            { name: 'Status', value: status || 'PAID', inline: true },
            { name: 'Plano', value: plan || 'N/A', inline: true },
            { name: 'IP', value: ip || 'N/A', inline: true },
            { name: 'PIX', value: pixKey ? `${pixKey.slice(0, 10)}...` : 'N/A', inline: true }
        ],
        footer: { text: 'Pagamentos' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.PAYMENTS, embed, 'PAYMENTS');
}

/**
 * Notifica saque realizado
 */
export async function notifyWithdraw({ withdrawId, email, value, fee, sent, status, pixKey, pixKeyType, plan, ip }) {
    const valueInReais = (value / 100).toFixed(2);
    const feeInReais = (fee / 100).toFixed(2);
    const sentInReais = ((sent || (value - fee)) / 100).toFixed(2);

    const embed = {
        title: 'Saque Realizado',
        color: 0xFFA500,
        fields: [
            { name: 'Email', value: email || 'N/A', inline: true },
            { name: 'ID', value: `\`${withdrawId}\``, inline: true },
            { name: 'Valor Total', value: `R$ ${valueInReais}`, inline: true },
            { name: 'Taxa', value: `R$ ${feeInReais}`, inline: true },
            { name: 'Valor Enviado', value: `R$ ${sentInReais}`, inline: true },
            { name: 'Status', value: status || 'PROCESSING', inline: true },
            { name: 'Plano', value: plan || 'N/A', inline: true },
            { name: 'IP', value: ip || 'N/A', inline: true },
            { name: 'Tipo PIX', value: pixKeyType || 'N/A', inline: true },
            { name: 'Chave PIX', value: pixKey ? `\`${pixKey}\`` : 'N/A', inline: false }
        ],
        footer: { text: 'Transferências' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.TRANSFERS, embed, 'TRANSFERS');
}

/**
 * Notifica transferência interna realizada
 */
export async function notifyInternalTransfer({ transferId, senderEmail, recipientEmail, recipientName, value, description, ip }) {
    const valueInReais = (value / 100).toFixed(2);

    const embed = {
        title: 'Transferência Interna',
        color: 0x0099FF,
        fields: [
            { name: 'Remetente', value: senderEmail || 'N/A', inline: true },
            { name: 'Destinatário', value: recipientEmail || 'N/A', inline: true },
            { name: 'Nome Dest.', value: recipientName || 'N/A', inline: true },
            { name: 'ID', value: `\`${transferId}\``, inline: true },
            { name: 'Valor', value: `R$ ${valueInReais}`, inline: true },
            { name: 'Descrição', value: description || 'Transferência interna', inline: true },
            { name: 'IP', value: ip || 'N/A', inline: true }
        ],
        footer: { text: 'Transferências' }
    };

    sendDiscordNotification(DISCORD_WEBHOOKS.TRANSFERS, embed, 'TRANSFERS');
}

export default {
    notifyRateLimit,
    notifyRegister,
    notifyLogin,
    notifyRequest,
    notifyPaymentApproved,
    notifyWithdraw,
    notifyInternalTransfer
};
