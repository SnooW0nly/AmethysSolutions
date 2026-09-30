import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { generateUniqueId } from '../../../../services/security.js';
import PushSubscription from '../../../../database/models/PushSubscription.js';
import { getVapidPublicKey } from '../../../../services/pushService.js';

const router = express.Router();

// GET /api/v1/push/vapid-key - Obter chave pública VAPID
router.get('/vapid-key', (req, res) => {
    const publicKey = getVapidPublicKey();

    if (!publicKey) {
        return res.status(503).json({
            success: false,
            error: 'Push notifications não configuradas'
        });
    }

    res.json({
        success: true,
        publicKey
    });
});

// POST /api/v1/push/subscribe - Registrar subscription de push
router.post('/subscribe', authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const { subscription, deviceType } = req.body;

        if (!subscription || !subscription.endpoint || !subscription.keys) {
            return res.status(400).json({
                success: false,
                error: 'Subscription inválida'
            });
        }

        // Verificar se já existe
        const existing = await PushSubscription.getByEndpoint(subscription.endpoint);

        if (existing) {
            // Atualizar se já existe
            await PushSubscription.findOneAndUpdate(
                { endpoint: subscription.endpoint },
                {
                    $set: {
                        userId: user.id,
                        keys: subscription.keys,
                        active: true,
                        lastUsed: new Date(),
                        userAgent: req.headers['user-agent'],
                        deviceType: deviceType || 'desktop'
                    }
                }
            );

            return res.json({
                success: true,
                message: 'Subscription atualizada',
                subscriptionId: existing.id
            });
        }

        // Criar nova subscription
        const subscriptionId = generateUniqueId();
        await PushSubscription.create({
            id: subscriptionId,
            userId: user.id,
            endpoint: subscription.endpoint,
            keys: subscription.keys,
            userAgent: req.headers['user-agent'],
            deviceType: deviceType || 'desktop',
            active: true
        });

        res.status(201).json({
            success: true,
            message: 'Subscription registrada',
            subscriptionId
        });

    } catch (error) {
        console.error('Erro ao registrar push subscription:', error);
        res.status(500).json({
            success: false,
            error: 'Erro ao registrar subscription'
        });
    }
});

// DELETE /api/v1/push/unsubscribe - Remover subscription
router.delete('/unsubscribe', authenticateUser, async (req, res) => {
    try {
        const { endpoint } = req.body;

        if (!endpoint) {
            return res.status(400).json({
                success: false,
                error: 'Endpoint obrigatório'
            });
        }

        await PushSubscription.deactivate(endpoint);

        res.json({
            success: true,
            message: 'Subscription removida'
        });

    } catch (error) {
        console.error('Erro ao remover push subscription:', error);
        res.status(500).json({
            success: false,
            error: 'Erro ao remover subscription'
        });
    }
});

// GET /api/v1/push/status - Verificar status das subscriptions do usuário
router.get('/status', authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const subscriptions = await PushSubscription.getByUserId(user.id);

        res.json({
            success: true,
            hasSubscriptions: subscriptions.length > 0,
            count: subscriptions.length,
            subscriptions: subscriptions.map(s => ({
                id: s.id,
                deviceType: s.deviceType,
                lastUsed: s.lastUsed,
                createdAt: s.createdAt
            }))
        });

    } catch (error) {
        console.error('Erro ao verificar status push:', error);
        res.status(500).json({
            success: false,
            error: 'Erro ao verificar status'
        });
    }
});

export default router;
