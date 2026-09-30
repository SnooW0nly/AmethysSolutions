// src/routes/api/v1/admin/index.js

import express from 'express';
import usersRoutes  from './users.js';
import statsRoutes  from './stats.js';
import configRoutes from './config.js';
import auditRoutes  from './audit.js';
import plansRoutes  from './plans.js';
import feesRoutes   from './fees.js';

const router = express.Router();

router.use('/users',  usersRoutes);
router.use('/stats',  statsRoutes);
router.use('/config', configRoutes);
router.use('/audit',  auditRoutes);
router.use('/plans',  plansRoutes);
router.use('/fees',   feesRoutes);      // ← NOVO

export default router;
