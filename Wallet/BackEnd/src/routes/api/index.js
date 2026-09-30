import express from 'express';
import v1Routes from './v1/index.js';

const router = express.Router();

// Rotas da API v1
// routes/index.js já monta isso em /v1, então aqui não precisa repetir
router.use('/', v1Routes);

export default router;

