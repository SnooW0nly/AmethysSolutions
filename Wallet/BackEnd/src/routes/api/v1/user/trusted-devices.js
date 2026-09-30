import express from 'express';
import { authenticate } from '../../../../middlewares/auth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import TrustedDevice from '../../../../database/models/TrustedDevice.js';

const router = express.Router();

// GET /api/v1/user/trusted-devices - Listar dispositivos confiáveis
router.get('/', defaultSmartRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;
    
    const devices = await TrustedDevice.findByUserId(user._id);
    
    res.json({
      success: true,
      data: devices.map(device => ({
        id: device._id,
        deviceName: device.deviceName,
        userAgent: device.userAgent,
        ip: device.ip,
        lastUsedAt: device.lastUsedAt,
        createdAt: device.createdAt,
      })),
    });
  } catch (error) {
    console.error('Erro ao listar dispositivos confiáveis:', error);
    res.status(500).json({
      success: false,
      error: 'Erro ao listar dispositivos confiáveis',
      message: error.message,
    });
  }
});

// DELETE /api/v1/user/trusted-devices/:deviceId - Remover dispositivo confiável
router.delete('/:deviceId', defaultSmartRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { deviceId } = req.params;
    
    const device = await TrustedDevice.findOne({
      _id: deviceId,
      userId: user._id,
    });
    
    if (!device) {
      return res.status(404).json({
        success: false,
        error: 'Dispositivo não encontrado',
      });
    }
    
    await TrustedDevice.findByIdAndDelete(deviceId);
    
    res.json({
      success: true,
      message: 'Dispositivo removido com sucesso',
    });
  } catch (error) {
    console.error('Erro ao remover dispositivo confiável:', error);
    res.status(500).json({
      success: false,
      error: 'Erro ao remover dispositivo confiável',
      message: error.message,
    });
  }
});

// DELETE /api/v1/user/trusted-devices - Remover todos os dispositivos confiáveis
router.delete('/', defaultSmartRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;
    
    await TrustedDevice.deleteMany({ userId: user._id });
    
    res.json({
      success: true,
      message: 'Todos os dispositivos confiáveis foram removidos',
    });
  } catch (error) {
    console.error('Erro ao remover dispositivos confiáveis:', error);
    res.status(500).json({
      success: false,
      error: 'Erro ao remover dispositivos confiáveis',
      message: error.message,
    });
  }
});

export default router;

