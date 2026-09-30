import express from 'express';
import userRoutes from './user/index.js';
import paymentRoutes from './payment/index.js';
import withdrawRoutes from './withdraw/index.js';
import adminRoutes from './admin/index.js';
import pushRoutes from './push/index.js';
import transferRoutes from './transfer/index.js';
import publicStatsRoutes from './public-stats.js';
import affiliateRoutes from './affiliate/index.js';
import goatpayRoutes from './goatpay/index.js';
import goatpayWebhookRoutes from './goatpay-webhook.js';

const router = express.Router();

// Rotas v1
router.use('/user', userRoutes);
router.use('/payment', paymentRoutes);
router.use('/withdraw', withdrawRoutes);
router.use('/admin', adminRoutes);
router.use('/push', pushRoutes);
router.use('/transfer', transferRoutes);
router.use('/public-stats', publicStatsRoutes);
router.use('/affiliate', affiliateRoutes);
router.use('/goatpay', goatpayRoutes);
router.use('/goatpay-webhook', goatpayWebhookRoutes);

export default router;

