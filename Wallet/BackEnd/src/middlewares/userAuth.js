/**
 * Middleware de autenticação para rotas de usuário
 * Aceita tanto JWT (User) quanto API Key (Register)
 * Quando autenticado via JWT, busca o Register correspondente pelo email
 */

import { verifyToken } from '../services/authService.js';
import User from '../database/models/User.js';
import Register from '../database/models/Register.js';

/**
 * Autentica usuário via JWT ou API Key
 * Se autenticado via JWT, busca o Register correspondente pelo email
 */
export async function authenticateUser(req, res, next) {
  try {
    // Se já autenticado, continuar
    if (req.user && req.user.id) {
      return next();
    }

    const token = req.headers.authorization?.replace('Bearer ', '');
    // Só considera como API Key do usuário se começar com 'vp_'
    // O X-API-Key do frontend (validação de origem) NÃO deve ser usado aqui
    const headerApiKey = req.headers['x-api-key'];
    const apiKey = (headerApiKey && headerApiKey.startsWith('vp_'))
      ? headerApiKey
      : (token && token.startsWith('vp_') ? token : null);

    // Tentar autenticar via JWT primeiro (se não for API Key)
    if (token && !apiKey && token.includes('.')) {
      try {
        const decoded = await verifyToken(token);
        if (decoded && decoded.userId) {
          const user = await User.findById(decoded.userId).select('-password');

          if (user && !user.blocked) {
            // Buscar Register correspondente pelo email
            const register = await Register.findOne({
              email: user.email.toLowerCase(),
              status: 'active'
            });

            if (register) {
              if (register.blocked) {
                return res.status(403).json({
                  error: 'Conta bloqueada',
                  message: 'Sua conta está suspensa. Entre em contato com o suporte.'
                });
              }
              req.user = register;
              req.authMethod = 'jwt';
              return next();
            } else {
              return res.status(404).json({
                error: 'Conta não encontrada',
                message: 'Não foi encontrada uma conta API associada a este usuário. Por favor, crie uma conta na API primeiro.'
              });
            }
          }
        }
      } catch (error) {
        // Se falhar, tentar API Key
        console.log('[AUTH] Falha ao autenticar via JWT, tentando API Key:', error.message);
      }
    }

    // Tentar autenticar via API Key
    if (apiKey) {
      try {
        const register = await Register.getByApiKey(apiKey);

        if (register && register.status === 'active') {
          req.user = register;
          req.authMethod = 'apiKey';
          return next();
        }
      } catch (error) {
        console.error('[AUTH] Erro ao autenticar via API Key:', error);
      }
    }

    // Se nenhum método funcionou, retornar erro
    return res.status(401).json({
      error: 'Não autenticado',
      message: 'É necessário fornecer um token JWT válido ou uma API Key válida'
    });

  } catch (error) {
    console.error('[AUTH] Erro na autenticação:', error);
    return res.status(500).json({
      error: 'Erro na autenticação',
      message: error.message
    });
  }
}
