import jwt from "jsonwebtoken";
import { JWT_SECRET } from "../config/env.js";
import { securityConfig } from "../config/security.js";

// Gerar token JWT
export function generateToken(userId) {
  if (!JWT_SECRET) {
    throw new Error("JWT_SECRET não está definido");
  }

  return jwt.sign(
    { userId },
    JWT_SECRET,
    { 
      expiresIn: securityConfig.jwt.accessTokenExpiry,
      algorithm: securityConfig.jwt.algorithm,
      issuer: securityConfig.jwt.issuer,
      audience: securityConfig.jwt.audience,
    }
  );
}

// Verificar token JWT e se a sessão está revogada
export async function verifyToken(token) {
  if (!JWT_SECRET) {
    throw new Error("JWT_SECRET não está definido");
  }

  try {
    // Primeiro verificar se o token é válido
    const decoded = jwt.verify(token, JWT_SECRET, {
      algorithms: [securityConfig.jwt.algorithm],
      issuer: securityConfig.jwt.issuer,
      audience: securityConfig.jwt.audience,
    });

    // Verificar se a sessão está revogada (opcional - não falha se sessão não existir)
    try {
      const Session = (await import("../database/models/Session.js")).default;
      const session = await Session.findByToken(token);
      
      if (session) {
        if (session.revoked) {
          return null; // Sessão revogada
        }
        // Atualizar última atividade se sessão existir
        await session.updateActivity();
      }
      // Se sessão não existir, ainda permite o token (compatibilidade com tokens antigos)
    } catch (sessionError) {
      // Se der erro ao verificar sessão, ainda permite o token
      // Isso garante compatibilidade e não quebra autenticação se houver problema no banco
      console.warn("[AUTH] Erro ao verificar sessão, permitindo token:", sessionError.message);
    }

    return decoded;
  } catch (error) {
    return null;
  }
}

