import { verifyToken } from "../database/auth.js";
import User from "../database/models/User.js";

import { securityConfig } from "../config/security.js";

// Cache de tokens inválidos (blacklist em memória)
const tokenBlacklist = new Set();

// Limpa blacklist periodicamente (a cada 1 hora)
setInterval(() => {
  tokenBlacklist.clear();
}, 60 * 60 * 1000);

/**
 * Adiciona token à blacklist
 */
export function blacklistToken(token) {
  tokenBlacklist.add(token);
}

/**
 * Middleware de autenticação com validações de segurança
 */
export default async function authMiddleware(req, res, next) {
  const header = req.headers["authorization"];
  const fromHeader = header?.startsWith("Bearer ") ? header.split(" ")[1] : null;
  const fromCookie = req.cookies?.token;
  const token = fromHeader || fromCookie;

  const ip = req.ip || req.connection.remoteAddress;
  const whitelist = securityConfig.rateLimit.whitelist || [];

  if (req.method === 'OPTIONS' || req.method === 'HEAD') {
    return next();
  }
  
  // Valida presença do token
  if (!token) {
    if (whitelist.includes(ip)) {
      console.log(`[AUTH] Tentativa de acesso sem token (IP confiável) - IP: ${ip}`);
    } else {
      console.warn(`[AUTH] Tentativa de acesso sem token - IP: ${ip}`);
    }
    return res.status(401).json({ error: "Token não fornecido" });
  }

  // Verifica se token está na blacklist
  if (tokenBlacklist.has(token)) {
    console.warn(`[AUTH] Token na blacklist usado - IP: ${req.ip}`);
    return res.status(401).json({ error: "Token revogado" });
  }

  // Verifica validade do token
  const decoded = verifyToken(token);
  if (!decoded) {
    console.warn(`[AUTH] Token inválido - IP: ${req.ip}`);
    return res.status(403).json({ error: "Token inválido" });
  }

  // Valida tokenVersion e status do usuário
  try {
    const user = await User.findById(decoded.id)
      .select("tokenVersion blocked email discordId")
      .lean();
    
    if (!user) {
      console.warn(`[AUTH] Usuário não encontrado - ID: ${decoded.id}`);
      return res.status(401).json({ error: "Usuário não encontrado" });
    }
    
    // Verifica se a versão do token é válida
    if ((decoded.tokenVersion ?? 0) !== (user.tokenVersion ?? 0)) {
      console.warn(`[AUTH] Token com versão desatualizada - User: ${user.email}`);
      return res.status(401).json({ error: "Sessão expirada" });
    }
    
    // Verifica se usuário está bloqueado
    if (user.blocked) {
      console.warn(`[AUTH] Usuário bloqueado tentou acessar - User: ${user.email}`);
      return res.status(403).json({ error: "Acesso bloqueado" });
    }

    // Adiciona informações do usuário à requisição (incluindo discordId)
    req.user = {
      _id: decoded.id,
      email: user.email,
      discordId: user.discordId || null,
      tokenVersion: user.tokenVersion,
    };
    
    // Log de acesso bem-sucedido (apenas em desenvolvimento)
    if (process.env.NODE_ENV === 'development') {
      console.log(`[AUTH] Acesso autorizado - User: ${user.email}`);
    }
    
    next();
  } catch (error) {
    console.error(`[AUTH] Erro na validação - Error: ${error.message}`);
    return res.status(500).json({ error: "Erro de autenticação" });
  }
}