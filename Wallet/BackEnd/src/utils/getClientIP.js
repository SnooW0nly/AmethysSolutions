/**
 * Função centralizada para obter o IP real do cliente
 * Considera proxies reversos (Cloudflare, nginx, etc.)
 * 
 * Ordem de prioridade:
 * 1. CF-Connecting-IP (Cloudflare)
 * 2. X-Forwarded-For (primeiro IP da cadeia)
 * 3. X-Real-IP
 * 4. X-Client-IP
 * 5. req.ip (quando trust proxy está configurado)
 * 6. req.connection.remoteAddress / req.socket.remoteAddress
 */

export function getClientIP(req) {
  // 1. Cloudflare - header mais confiável quando usando Cloudflare
  if (req.headers['cf-connecting-ip']) {
    return req.headers['cf-connecting-ip'].trim();
  }

  // 2. X-Forwarded-For - pode conter múltiplos IPs separados por vírgula
  // O primeiro IP é o IP original do cliente
  const forwardedFor = req.headers['x-forwarded-for'];
  if (forwardedFor) {
    const ips = forwardedFor.split(',').map(ip => ip.trim()).filter(ip => ip);
    if (ips.length > 0 && ips[0]) {
      return ips[0];
    }
  }

  // 3. X-Real-IP - usado por alguns proxies (nginx, etc.)
  if (req.headers['x-real-ip']) {
    return req.headers['x-real-ip'].trim();
  }

  // 4. X-Client-IP - usado por alguns proxies
  if (req.headers['x-client-ip']) {
    return req.headers['x-client-ip'].trim();
  }

  // 5. req.ip - funciona quando trust proxy está configurado
  // Com trust proxy: true, Express automaticamente pega o IP do X-Forwarded-For
  if (req.ip && req.ip !== '::1' && req.ip !== '127.0.0.1') {
    return req.ip;
  }

  // 6. Fallback para conexão direta
  const remoteAddress = req.connection?.remoteAddress || req.socket?.remoteAddress;
  if (remoteAddress) {
    // Remover prefixo IPv6 se existir
    return remoteAddress.replace(/^::ffff:/, '');
  }

  // 7. Último fallback
  return 'unknown';
}

