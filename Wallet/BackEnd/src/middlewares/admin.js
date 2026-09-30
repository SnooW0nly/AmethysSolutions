import { authenticate } from "./auth.js";

// Middleware para verificar se o usuário é admin
export function requireAdmin(req, res, next) {
  authenticate(req, res, () => {
    if (!req.user || !req.user.admin) {
      return res.status(403).json({
        success: false,
        error: "Acesso negado. Apenas administradores.",
      });
    }
    next();
  });
}

