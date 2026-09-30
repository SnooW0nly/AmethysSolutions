import Register from '../database/models/Register.js';
import { verifyToken } from '../services/authService.js';
import User from '../database/models/User.js';
import crypto from 'crypto';

/**
 * Middleware de autenticação exclusiva para Dashboard
 * Exige token JWT válido e garante que o usuário tenha um perfil Register.
 * Não aceita API Key.
 */
export async function requireDashboardAuth(req, res, next) {
    try {
        const authHeader = req.headers['authorization'];
        const token = authHeader && authHeader.startsWith('Bearer ')
            ? authHeader.replace('Bearer ', '')
            : req.cookies?.token;

        if (!token) {
            return res.status(401).json({
                error: 'Não autenticado',
                message: 'Token de autenticação não fornecido'
            });
        }

        // Verificar se é um token JWT
        if (!token.includes('.')) {
            return res.status(401).json({
                error: 'Token inválido',
                message: 'Formato de token inválido'
            });
        }

        try {
            const decoded = await verifyToken(token);

            if (!decoded || !decoded.userId) {
                return res.status(401).json({
                    error: 'Token inválido',
                    message: 'Token inválido ou expirado'
                });
            }

            // Buscar User do banco
            const userModel = await User.findById(decoded.userId);

            if (!userModel) {
                return res.status(401).json({
                    error: 'Usuário não encontrado',
                    message: 'Usuário associado ao token não existe'
                });
            }

            if (userModel.blocked) {
                return res.status(403).json({
                    error: 'Conta bloqueada',
                    message: 'Sua conta foi bloqueada. Entre em contato com o suporte.'
                });
            }

            // Buscar Register correspondente pelo email
            let register = await Register.findOne({ email: userModel.email.toLowerCase() });

            // Se não existir Register, criar um básico (Auto-Register)
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
                        taxID: `TMP${crypto.randomBytes(8).toString('hex').toUpperCase()}`, // ID temporário com entropia garantida
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

            if (!register) {
                return res.status(500).json({
                    error: 'Erro de perfil',
                    message: 'Não foi possível carregar ou criar seu perfil de usuário.'
                });
            }

            if (register.status !== 'active' || register.blocked) {
                return res.status(403).json({
                    error: 'Acesso negado',
                    message: 'Seu perfil está inativo ou bloqueado.'
                });
            }

            // Autenticação bem-sucedida
            req.user = register;
            req.userModel = userModel; // Disponibiliza o model User também se necessário
            req.isAuthenticated = true;
            return next();

        } catch (jwtError) {
            return res.status(401).json({
                error: 'Token inválido',
                message: 'Falha na verificação do token'
            });
        }

    } catch (error) {
        console.error('Erro na autenticação do dashboard:', error);
        return res.status(500).json({
            error: 'Erro interno',
            message: 'Erro ao processar autenticação'
        });
    }
}
