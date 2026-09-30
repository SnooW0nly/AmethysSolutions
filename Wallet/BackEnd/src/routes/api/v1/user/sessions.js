import express from 'express';
import { authenticate } from '../../../../middlewares/auth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Session from '../../../../database/models/Session.js';

const router = express.Router();

// GET /api/v1/user/sessions - Listar sessões ativas
router.get('/', defaultSmartRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;
    
    // Obter token atual da requisição
    const currentToken = req.headers.authorization?.replace('Bearer ', '') || req.cookies?.token;
    
    const sessions = await Session.findActiveByUserId(user._id);
    
    res.json({
      success: true,
      data: sessions.map(session => ({
        id: session._id,
        deviceName: session.deviceInfo?.deviceName || 'Dispositivo desconhecido',
        userAgent: session.deviceInfo?.userAgent || 'N/A',
        ip: session.deviceInfo?.ip || 'N/A',
        lastActivity: session.lastActivity,
        createdAt: session.createdAt,
        expiresAt: session.expiresAt,
        isCurrent: session.token === currentToken,
      })),
    });
  } catch (error) {
    console.error('Erro ao listar sessões:', error);
    res.status(500).json({
      success: false,
      error: 'Erro ao listar sessões',
      message: error.message,
    });
  }
});

// DELETE /api/v1/user/sessions/:sessionId - Revogar sessão específica
router.delete('/:sessionId', defaultSmartRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { sessionId } = req.params;
    
    const session = await Session.findOne({
      _id: sessionId,
      userId: user._id,
      revoked: false,
    });
    
    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Sessão não encontrada ou já revogada',
      });
    }
    
    // Revogar sessão
    await session.revoke();
    
    res.json({
      success: true,
      message: 'Sessão revogada com sucesso',
    });
  } catch (error) {
    console.error('Erro ao revogar sessão:', error);
    res.status(500).json({
      success: false,
      error: 'Erro ao revogar sessão',
      message: error.message,
    });
  }
});

// DELETE /api/v1/user/sessions - Revogar todas as sessões (exceto a atual)
router.delete('/', defaultSmartRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;
    
    // Obter token atual da requisição
    const currentToken = req.headers.authorization?.replace('Bearer ', '') || req.cookies?.token;
    
    // Revogar todas as sessões exceto a atual
    const result = await Session.revokeAllByUserId(user._id, currentToken);
    
    res.json({
      success: true,
      message: `${result.modifiedCount} sessão(ões) revogada(s) com sucesso`,
      revokedCount: result.modifiedCount,
    });
  } catch (error) {
    console.error('Erro ao revogar sessões:', error);
    res.status(500).json({
      success: false,
      error: 'Erro ao revogar sessões',
      message: error.message,
    });
  }
});

export default router;

