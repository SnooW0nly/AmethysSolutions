import express from 'express';
import registerRoutes from './register.js';
import meRoutes from './me.js';
import updateCodeRoutes from './update-code.js';
import statsRoutes from './stats.js';
import validateRoutes from './validate.js';

const router = express.Router();

// Rotas autenticadas
router.use('/register', registerRoutes);
router.use('/me', meRoutes);
router.use('/code', updateCodeRoutes);
router.use('/stats', statsRoutes);

// Rota pública
router.use('/validate', validateRoutes);

export default router;
