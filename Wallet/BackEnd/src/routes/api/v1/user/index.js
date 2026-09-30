import express from 'express';
import registerRoutes from './register.js';
import getRoutes from './get.js';
import updateRoutes from './update.js';
import deleteRoutes from './delete.js';
import balanceRoutes from './balance.js';
import limitRoutes from './limit.js';
import blockRoutes from './block.js';
import apiKeyRoutes from './api-key.js';
import securityRoutes from './security.js';
import trustedDevicesRoutes from './trusted-devices.js';
import sessionsRoutes from './sessions.js';
import dashboardRoutes from './dashboard.js';
import completeBusinessProfileRoutes from './complete-business-profile.js';
import transactionsRoutes from './transactions.js';
import planRoutes from './plan.js';
// ⬇️ ADICIONE ESTA LINHA ⬇️
import myPlanRoutes from './my-plan.js';

const router = express.Router();

// Rotas de usuário
router.use('/register', registerRoutes);
router.use('/get', getRoutes);
router.use('/update', updateRoutes);
router.use('/delete', deleteRoutes);
router.use('/balance', balanceRoutes);
router.use('/limit', limitRoutes);
router.use('/block', blockRoutes);
router.use('/api-key', apiKeyRoutes);
router.use('/security', securityRoutes);
router.use('/trusted-devices', trustedDevicesRoutes);
router.use('/sessions', sessionsRoutes);
router.use('/dashboard', dashboardRoutes);
router.use('/complete-business-profile', completeBusinessProfileRoutes);
router.use('/transactions', transactionsRoutes);
router.use('/plan', planRoutes);
// ⬇️ ADICIONE ESTA LINHA ⬇️
router.use('/my-plan', myPlanRoutes);

export default router;