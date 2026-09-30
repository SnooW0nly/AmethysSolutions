import express from 'express';
import createRoutes from './create.js';
import getRoutes from './get.js';
import listRoutes from './list.js';
import cryptoRoutes from './crypto.js';

const router = express.Router();

router.use('/create', createRoutes);
router.use('/get', getRoutes);
router.use('/list', listRoutes);
router.use('/crypto', cryptoRoutes);

export default router;


