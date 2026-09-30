import https from 'https';
import {
  getCachedTransaction,
  cacheTransaction,
  canMakeRequest,
  recordRequest,
  recordRateLimit,
  resetBackoff,
  getBackoffRemaining,
} from './goatpayCache.js';

const DEFAULT_BASE_URL = 'https://api.goatpay.com.br/v1';

function getApiKey(useBlackCredentials = false) {
  if (useBlackCredentials) {
    return process.env.GOATPAY_API_KEY_BLACK || process.env.GOATPAY_API_KEY || '';
  }
  return process.env.GOATPAY_API_KEY || '';
}

function getBaseUrl() {
  return (process.env.GOATPAY_API_URL || DEFAULT_BASE_URL).replace(/\/+$/, '');
}

function mapPixKeyType(pixKeyType) {
  const upper = (pixKeyType || '').toUpperCase();
  if (upper === 'PHONE') return 'TELEFONE';
  if (upper === 'RANDOM') return 'CHAVE_ALEATORIA';
  if (upper === 'COPYPASTE') return null;
  return upper;
}

function normalizeStatus(status) {
  const value = (status || '').toUpperCase();
  if (value === 'COMPLETED') return 'COMPLETO';
  if (value === 'FAILED' || value === 'CANCELED' || value === 'REVERSED') return 'FALHA';
  if (value === 'PROCESSING') return 'PROCESSANDO';
  return 'PENDENTE';
}

function wrapTransactionData(data) {
  const tx = data || {};
  const state = normalizeStatus(tx.status);
  return {
    transactionId: tx.id,
    transactionState: state,
    status: tx.status,
    transactionAmount: tx.amount,
    transactionFee: tx.feeAmount,
    copyPaste: tx.copyPaste,
    qrCodeBase64: tx.qrCodeBase64,
    qrcodeUrl: tx.qrcodeUrl,
    ...tx,
  };
}

function doRequest(method, endpoint, body = null, requestOptions = {}) {
  return new Promise((resolve, reject) => {
    const apiKey = getApiKey(requestOptions.useBlackCredentials);

    if (!apiKey) {
      return resolve({ simulated: true, method, endpoint, body });
    }

    let urlObj;
    try {
      // Remove leading slash so new URL() doesn't discard the /v1 base path
      const normalizedEndpoint = endpoint.replace(/^\//, '');
      urlObj = new URL(normalizedEndpoint, `${getBaseUrl()}/`);
    } catch (error) {
      return reject({ error: 'URL inválida', message: error.message });
    }

    const data = body ? JSON.stringify(body) : null;
    const httpOptions = {
      protocol: urlObj.protocol,
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method,
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
    };

    if (data) {
      httpOptions.headers['Content-Length'] = Buffer.byteLength(data);
    }

    const req = https.request(httpOptions, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        const bodyStr = Buffer.concat(chunks).toString();
        try {
          const parsedJson = bodyStr ? JSON.parse(bodyStr) : {};
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsedJson);
          } else {
            reject({
              status: res.statusCode,
              error: parsedJson.message || (typeof parsedJson.error === 'string' ? parsedJson.error : JSON.stringify(parsedJson.error)) || bodyStr || 'Erro desconhecido da GoatPay',
              data: parsedJson,
            });
          }
        } catch {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ ok: true, raw: bodyStr });
          } else {
            reject({
              status: res.statusCode,
              error: bodyStr || 'Erro desconhecido da GoatPay',
            });
          }
        }
      });
    });

    req.on('error', (err) => reject({ error: 'Erro de conexão com a GoatPay', message: err.message }));
    if (data) req.write(data);
    req.end();
  });
}

/** POST /payment-pix/create */
export async function createTransaction({
  amount,
  payerName,
  payerDocument,
  transactionId,
  splitUser,
  splitTax,
  description,
  coverFee,
  useBlackCredentials = false,
}) {
  const payload = {
    amount,
    description: description || 'Deposito',
    coverFee: coverFee === true,
    payerName,
    payerDocument,
    externalReference: transactionId,
  };

  if (splitUser && splitTax != null && splitTax !== '') {
    payload.splitUser = splitUser;
    payload.splitTax = parseFloat(splitTax);
  }

  const response = await doRequest('POST', '/payment-pix/create', payload, { useBlackCredentials });
  const data = wrapTransactionData(response.data || response);
  return { ...response, data };
}

/** POST /transfer-pix/create */
export async function withdraw({
  amount,
  pixKey,
  pixKeyType,
  description,
  coverFee,
  externalReference,
  useBlackCredentials = false,
}) {
  const payload = {
    amount,
    description: description || 'Transferência',
    coverFee: coverFee !== false,
    externalReference,
  };

  const mappedType = mapPixKeyType(pixKeyType);
  if (mappedType === null || (pixKeyType || '').toUpperCase() === 'COPYPASTE') {
    payload.pixCopyPaste = pixKey;
  } else {
    payload.pixKey = pixKey;
    payload.pixKeyType = mappedType;
  }

  const response = await doRequest('POST', '/transfer-pix/create', payload, { useBlackCredentials });
  const data = wrapTransactionData(response.data || response);
  return { ...response, data };
}

/** GET /payment-pix/get/:id ou /transfer-pix/get/:id */
export async function checkTransaction({
  transactionId,
  type = 'payment',
  useBlackCredentials = false,
}) {
  const cacheKey = `${type}:${transactionId}`;
  const cached = getCachedTransaction(cacheKey);
  if (cached) {
    return { ...cached, fromCache: true };
  }

  const backoffRemaining = getBackoffRemaining();
  if (backoffRemaining > 0) {
    throw {
      status: 429,
      error: `Rate limit ativo, aguarde ${Math.ceil(backoffRemaining / 1000)}s`,
      retryAfter: backoffRemaining,
    };
  }

  if (!canMakeRequest()) {
    throw {
      status: 429,
      error: 'Limite de requisições por segundo atingido',
      retryAfter: 1000,
    };
  }

  recordRequest();

  const endpoint = type === 'transfer'
    ? `/transfer-pix/get/${encodeURIComponent(transactionId)}`
    : `/payment-pix/get/${encodeURIComponent(transactionId)}`;

  try {
    const response = await doRequest('GET', endpoint, null, { useBlackCredentials });
    const data = wrapTransactionData(response.data || response);
    const result = {
      ...response,
      transaction: data,
      data,
    };

    resetBackoff();
    cacheTransaction(cacheKey, result);
    return result;
  } catch (error) {
    if (error.status === 429) {
      recordRateLimit();
    }
    throw error;
  }
}

/** GET /account/balance */
export async function getBalance(useBlackCredentials = false) {
  const response = await doRequest('GET', '/account/balance', null, { useBlackCredentials });
  const data = response.data || response;
  return {
    ...response,
    data: {
      balance: data.availableAmount ?? data.padrao?.available ?? data.livre?.available ?? 0,
      ...data,
    },
  };
}

/** GET /account/transactions */
export async function listTransactions({ page = 1, pageSize = 50, useBlackCredentials = false } = {}) {
  const endpoint = `/account/transactions?page=${page}&pageSize=${pageSize}`;
  return doRequest('GET', endpoint, null, { useBlackCredentials });
}

/** POST /subaccount/create */
export async function createSubaccount({ name, taxID, birthDate, zipCode, externalReference }) {
  const payload = {
    personType: 'PF',
    fullName: name,
    cpf: taxID,
    birthDate, // formato YYYY-MM-DD
    postalCode: zipCode,
    externalReference,
  };
  return doRequest('POST', '/subaccount/create', payload);
}

/** GET /subaccount/balance?id=:id */
export async function getSubaccountBalance(subaccountId) {
  return doRequest('GET', `/subaccount/balance?id=${encodeURIComponent(subaccountId)}`);
}

/** POST /transfer-crypto/create */
export async function cryptoWithdraw({
  amount,
  wallet,
  description,
  externalReference,
  useBlackCredentials = false,
}) {
  const payload = {
    amount,
    address: wallet,
    payCurrency: process.env.GOATPAY_CRYPTO_CURRENCY || 'usdtbsc',
    description: description || 'Saque crypto',
    externalReference,
    coverFee: true,
  };

  const response = await doRequest('POST', '/transfer-crypto/create', payload, { useBlackCredentials });
  const data = wrapTransactionData(response.data || response);
  return {
    ...response,
    data: {
      ...data,
      jobId: data.id,
    },
  };
}
