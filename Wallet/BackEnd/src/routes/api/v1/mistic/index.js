import express from 'express';
import balanceRoutes from './balance.js';

import transactionsRoutes from './transactions.js';

const router = express.Router();

router.use('/balance', balanceRoutes);
router.use('/transactions', transactionsRoutes);

export default router;
