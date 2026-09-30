import User from '../database/models/User.js';
import { verifyToken } from '../services/authService.js';

/**
 * Autenticação de administrador via JWT (Dashboard)
 * - Exige token JWT válido
 * - Verifica se o usuário (modelo User) possui admin = true
 * - NÃO aceita API Key para admin
 */
export async function authenticateAdmin(req, res, next) {
  try {
    // Se já estiver autenticado e for admin
    if (req.user && req.user.admin === true) {
      req.isAdmin = true;
      return next();
    }

    const token = req.headers.authorization?.replace('Bearer ', '') || req.cookies?.token;

    if (!token || !token.includes('.')) {
      return res.status(401).json({
        error: 'Não autenticado',
        message: 'Forneça um token JWT válido'
      });
    }

    const decoded = await verifyToken(token);
    if (!decoded?.userId) {
      return res.status(401).json({
        error: 'Token inválido',
        message: 'Token inválido ou expirado'
      });
    }

    const user = await User.findById(decoded.userId).select('-password');
    if (!user || user.blocked) {
      return res.status(401).json({
        error: 'Não autenticado',
        message: 'Usuário inválido ou bloqueado'
      });
    }

    if (!user.admin) {
      return res.status(403).json({
        error: 'Acesso negado',
        message: 'Apenas administradores podem acessar esta rota'
      });
    }

    req.user = user;
    req.isAdmin = true;
    return next();
  } catch (error) {
    console.error('Erro na autenticação de admin:', error);
    return res.status(500).json({
      error: 'Erro interno',
      message: 'Erro ao verificar permissões de administrador'
    });
  }
}

/**
 * Requer que o usuário já autenticado seja admin
 */
export function requireAdmin(req, res, next) {
  if (req.user && req.user.admin === true) {
    return next();
  }
  return res.status(403).json({
    error: 'Acesso negado',
    message: 'Apenas administradores podem acessar esta rota'
  });
}

/**
 * Caminho legado não suportado: admin via API Key
 */
export async function requireAdminApiKey(req, res, next) {
  return res.status(401).json({
    error: 'Não autorizado',
    message: 'Admin disponível apenas com JWT (Dashboard)'
  });
}

