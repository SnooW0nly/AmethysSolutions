import Register from '../database/models/Register.js';
import { verifyToken } from '../services/authService.js';
import User from '../database/models/User.js';

/**
 * Middleware de autenticação opcional
 * Tenta autenticar se API Key ou JWT token fornecidos, mas não bloqueia se não fornecidos
 */
export async function optionalApiKeyAuth(req, res, next) {
  try {
    const authHeader = req.headers['authorization'];
    const headerApiKey = req.headers['x-api-key'];
    // Só considera como API Key do usuário se começar com 'vp_'
    const apiKeyHeader = (headerApiKey && headerApiKey.startsWith('vp_')) ? headerApiKey : null;

    // Tentar autenticar com API Key primeiro (apenas se for API Key de usuário vp_)
    if (apiKeyHeader) {
      const user = await Register.getByApiKey(apiKeyHeader);

      if (user && user.status === 'active') {
        // Se é uma API Key secundária, verificar se está ativa
        if (user.usedApiKey && user.usedApiKey.type === 'secondary') {
          const keyIndex = user.usedApiKey.index;
          const secondaryKey = user.apiKeys[keyIndex];

          if (!secondaryKey || secondaryKey.active === false) {
            req.user = null;
            req.apiKeyInfo = null;
            req.isAuthenticated = false;
            return next();
          }
        }

        // Autenticação bem-sucedida com API Key
        req.user = user;
        req.apiKeyInfo = user.usedApiKey || { type: 'main', permissions: ['admin:all'] };
        req.isAuthenticated = true;
        return next();
      }
    }

    // Tentar autenticar com JWT token (Bearer token)
    if (authHeader && authHeader.startsWith('Bearer ')) {
      const token = authHeader.replace('Bearer ', '');

      // Verificar se é um token JWT (não uma API Key)
      if (token.includes('.')) {
        try {
          const decoded = await verifyToken(token);

          if (decoded && decoded.userId) {
            // Buscar User do banco
            const userModel = await User.findById(decoded.userId);

            if (userModel) {
              // Buscar Register correspondente pelo email
              let register = await Register.findOne({ email: userModel.email.toLowerCase() });

              // Se não existir Register, criar um básico
              if (!register) {
                try {
                  const { generateApiKey, generateUniqueId } = await import('../services/security.js');
                  const { getPlan, getSplitFee, initializePlanDates } = await import('../services/planService.js');

                  const freePlan = await getPlan('FREE');
                  const planDates = initializePlanDates();
                  const splitFee = await getSplitFee('FREE');

                  register = await Register.create({
                    id: generateUniqueId(),
                    apiKey: generateApiKey(),
                    name: userModel.fullName || 'Usuário',
                    email: userModel.email.toLowerCase(),
                    taxID: `TMP${Date.now().toString().slice(-8)}`, // CPF temporário único
                    phone: userModel.phone || null,
                    balance: 0,
                    saldo_split: 0,
                    plan: 'FREE',
                    paymentFee: freePlan.transactionFee,
                    splitFee: splitFee,
                    autoUpgrade: false,
                    planAutoRenew: true,
                    planStartDate: planDates.planStartDate,
                    planEndDate: planDates.planEndDate,
                    planRenewalDate: planDates.planRenewalDate,
                    monthlyTransactions: 0,
                    blocked: false,
                    status: 'active',
                    limits: {
                      daily: 999999999,
                      monthly: 999999999,
                      perTransaction: 500000
                    },
                    dailyUsed: 0,
                    monthlyUsed: 0,
                    apiKeys: [],
                    webhookUrl: null,
                  });
                } catch (createError) {
                  console.error(`[AUTH] Erro ao criar Register automaticamente:`, createError);
                  // Se falhar (ex: race condition), tentar buscar novamente
                  register = await Register.findOne({ email: userModel.email.toLowerCase() });
                }
              }

              if (register && register.status === 'active') {
                // Autenticação bem-sucedida com JWT
                req.user = register;
                req.apiKeyInfo = { type: 'main', permissions: ['admin:all'] };
                req.isAuthenticated = true;
                return next();
              }
            }
          }
        } catch (jwtError) {
          // Token inválido, continuar para tentar como API Key
        }
      } else {
        // Não é JWT, tentar como API Key
        const user = await Register.getByApiKey(token);

        if (user && user.status === 'active') {
          if (user.usedApiKey && user.usedApiKey.type === 'secondary') {
            const keyIndex = user.usedApiKey.index;
            const secondaryKey = user.apiKeys[keyIndex];

            if (!secondaryKey || secondaryKey.active === false) {
              req.user = null;
              req.apiKeyInfo = null;
              req.isAuthenticated = false;
              return next();
            }
          }

          req.user = user;
          req.apiKeyInfo = user.usedApiKey || { type: 'main', permissions: ['admin:all'] };
          req.isAuthenticated = true;
          return next();
        }
      }
    }

    // Sem autenticação - continuar sem autenticação
    req.user = null;
    req.apiKeyInfo = null;
    req.isAuthenticated = false;
    next();
  } catch (error) {
    console.error('Erro na autenticação opcional:', error);
    // Em caso de erro, continuar sem autenticação
    req.user = null;
    req.apiKeyInfo = null;
    req.isAuthenticated = false;
    next();
  }
}

/**
 * Middleware que requer autenticação opcional mas valida se dados pertencem ao usuário
 */
export function requireOwnershipOrPublic(entityUserId) {
  return (req, res, next) => {
    // Se não autenticado, permitir acesso público (para leitura)
    if (!req.isAuthenticated || !req.user) {
      return next();
    }

    // Se autenticado, verificar se o recurso pertence ao usuário
    const resourceUserId = typeof entityUserId === 'function'
      ? entityUserId(req)
      : req[entityUserId]?.userId || req.params.userId;

    if (resourceUserId && resourceUserId !== req.user.id) {
      return res.status(403).json({
        error: 'Acesso negado',
        message: 'Você não tem permissão para acessar este recurso'
      });
    }

    next();
  };
}

