import { verifyToken } from "../services/authService.js";
import User from "../database/models/User.js";

// Middleware para verificar autenticação
export async function authenticate(req, res, next) {
  try {
    // Apenas header Authorization
    const token = req.headers.authorization?.replace("Bearer ", "");

    if (!token) {
      return res.status(401).json({
        success: false,
        error: "Token não fornecido",
      });
    }

    // Verificar token
    const decoded = await verifyToken(token);
    if (!decoded) {
      return res.status(401).json({
        success: false,
        error: "Token inválido ou expirado",
      });
    }

    // Buscar usuário
    const user = await User.findById(decoded.userId).select("-password");
    if (!user) {
      return res.status(401).json({
        success: false,
        error: "Usuário não encontrado",
      });
    }

    // Bloqueio não impede autenticação - apenas operações específicas

    // Adicionar usuário à requisição
    req.user = user;
    next();
  } catch (error) {
    console.error("[AUTH] Erro na autenticação:", error);
    return res.status(500).json({
      success: false,
      error: "Erro na autenticação",
    });
  }
}

// Middleware opcional - não retorna erro se não autenticado
export async function optionalAuth(req, res, next) {
  try {
    const token = req.headers.authorization?.replace("Bearer ", "") || req.cookies?.token;

    if (token) {
      const decoded = await verifyToken(token);
      if (decoded) {
        const user = await User.findById(decoded.userId).select("-password");
        if (user) {
          req.user = user;
        }
      }
    }

    next();
  } catch (error) {
    // Ignorar erros no auth opcional
    next();
  }
}

