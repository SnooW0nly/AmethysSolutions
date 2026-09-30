import express from 'express';
import internalRoute from './internal.js';

const router = express.Router();

router.use('/internal', internalRoute);

export default router;
