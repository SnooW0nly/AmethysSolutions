import Register from '../database/models/Register.js';

/**
 * Middleware de autenticação - APENAS API Key
 * - Aceita X-API-Key ou Authorization: Bearer <apiKey>
 * - NÃO aceita JWT
 */
export async function authenticateApiKey(req, res, next) {
  try {
    const rawAuth = req.headers['authorization'];
    const headerApiKey = req.headers['x-api-key'];
    const bearer = rawAuth && rawAuth.startsWith('Bearer ') ? rawAuth.replace('Bearer ', '') : null;
    // Só considera como API Key do usuário se começar com 'vp_'
    const apiKey = (headerApiKey && headerApiKey.startsWith('vp_'))
      ? headerApiKey
      : (bearer && bearer.startsWith('vp_') ? bearer : null);

    if (!apiKey) {
      return res.status(401).json({
        error: 'API Key não fornecida',
        message: 'Inclua a API Key no header X-API-Key ou Authorization: Bearer'
      });
    }

    // Bloquear tokens com formato de JWT
    if (apiKey.includes('.')) {
      return res.status(401).json({
        error: 'Token inválido',
        message: 'Use uma API Key válida (não JWT) para esta rota'
      });
    }

    // Buscar usuário pela API Key no MongoDB (principal ou secundária)
    const user = await Register.getByApiKey(apiKey);

    if (!user || user.status !== 'active') {
      return res.status(401).json({
        error: 'API Key inválida ou usuário inativo'
      });
    }

    // Bloqueio não impede autenticação - apenas operações específicas (saque, transferência)

    // Se é uma API Key secundária, verificar se está ativa
    if (user.usedApiKey && user.usedApiKey.type === 'secondary') {
      const keyIndex = user.usedApiKey.index;
      const secondaryKey = user.apiKeys[keyIndex];
      if (!secondaryKey || secondaryKey.active === false) {
        return res.status(403).json({
          error: 'API Key inativa',
          message: 'Esta API Key foi desativada'
        });
      }
    }

    req.user = user;
    req.apiKeyInfo = user.usedApiKey || { type: 'main', permissions: ['admin:all'] };
    next();
  } catch (error) {
    console.error('Erro na autenticação por API Key:', error);
    res.status(500).json({
      error: 'Erro no servidor',
      message: error.message
    });
  }
}

/**
 * Middleware para verificar permissões da API Key
 * @param {string|string[]} requiredPermissions - Permissão(ões) necessária(s)
 */
export function requirePermission(requiredPermissions) {
  const permissions = Array.isArray(requiredPermissions) ? requiredPermissions : [requiredPermissions];

  return (req, res, next) => {
    try {
      const apiKeyInfo = req.apiKeyInfo || { type: 'main', permissions: ['admin:all'] };

      // API Key principal tem acesso total
      if (apiKeyInfo.type === 'main' || apiKeyInfo.permissions.includes('admin:all')) {
        return next();
      }

      // Verificar se a API Key tem todas as permissões necessárias
      const hasAllPermissions = permissions.every(perm => {
        // Verificar permissão exata
        if (apiKeyInfo.permissions.includes(perm)) {
          return true;
        }
        // Verificar permissão wildcard (ex: 'read:*' cobre 'read:balance')
        const permParts = perm.split(':');
        if (permParts.length >= 2) {
          const wildcard = `${permParts[0]}:*`;
          if (apiKeyInfo.permissions.includes(wildcard)) {
            return true;
          }
        }
        return false;
      });

      if (!hasAllPermissions) {
        return res.status(403).json({
          error: 'Permissão insuficiente',
          message: `Esta operação requer uma das seguintes permissões: ${permissions.join(', ')}`,
          requiredPermissions: permissions,
          currentPermissions: apiKeyInfo.permissions
        });
      }

      next();
    } catch (error) {
      console.error('Erro na verificação de permissões:', error);
      res.status(500).json({
        error: 'Erro no servidor',
        message: error.message
      });
    }
  };
}

/**
 * Middleware de autenticação Admin - DEPRECATED
 * Use requireAdminApiKey do adminAuth.js que verifica admin: true na DB
 * @deprecated Use requireAdminApiKey from './adminAuth.js'
 */
export function authenticateAdmin(req, res, next) {
  // Redirecionar para o novo middleware
  const { requireAdminApiKey } = require('./adminAuth.js');
  return requireAdminApiKey(req, res, next);
}

/**
 * Middleware para verificar limites do usuário
 * NOTA: Limites diários e mensais foram removidos.
 * Apenas limite por transação de R$ 1.000,00 é verificado na rota de pagamento.
 */
export function checkLimits(req, res, next) {
  // Limites diários e mensais removidos - apenas limite por transação de R$ 1.000,00 na rota de pagamento
  next();
}

