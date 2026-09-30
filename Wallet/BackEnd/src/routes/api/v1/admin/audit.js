import express from 'express';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';

const router = express.Router();

import { authenticateAdmin } from '../../../../middlewares/adminAuth.js';

// GET /api/v1/admin/audit - Lista logs de auditoria (Admin only)
router.get('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const {
      action,
      entity,
      entityId,
      userId,
      startDate,
      endDate,
      limit = 100,
      offset = 0
    } = req.query;

    const filters = {};
    if (action) filters.action = action;
    if (entity) filters.entity = entity;
    if (entityId) filters.entityId = entityId;
    if (userId) filters.userId = userId;
    if (startDate) filters.startDate = startDate;
    if (endDate) filters.endDate = endDate;

    const result = await Audit.getLogs(filters, {
      limit: parseInt(limit),
      offset: parseInt(offset)
    });

    res.json({
      success: true,
      data: {
        logs: result.logs,
        pagination: {
          total: result.total,
          limit: result.limit,
          offset: result.offset,
          hasMore: result.hasMore
        },
        filters: {
          action,
          entity,
          entityId,
          userId,
          startDate,
          endDate
        }
      }
    });
  } catch (error) {
    console.error('Erro ao buscar logs de auditoria:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/admin/audit/actions - Lista todas as ações disponíveis
router.get('/actions', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    res.json({
      success: true,
      data: {
        actions: Object.values(AUDIT_ACTIONS),
        entities: Object.values(AUDIT_ENTITIES)
      }
    });
  } catch (error) {
    console.error('Erro ao buscar ações de auditoria:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/admin/audit/entity/:entity/:entityId - Logs de uma entidade específica
router.get('/entity/:entity/:entityId', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { entity, entityId } = req.params;
    const { limit = 50 } = req.query;

    const result = await Audit.getLogsByEntity(entity, entityId, parseInt(limit));

    res.json({
      success: true,
      data: {
        entity,
        entityId,
        logs: result.logs || [],
        total: result.total || 0
      }
    });
  } catch (error) {
    console.error('Erro ao buscar logs da entidade:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/admin/audit/user/:userId - Logs de um usuário específico
router.get('/user/:userId', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { userId } = req.params;
    const { limit = 50 } = req.query;

    const result = await Audit.getLogsByUser(userId, parseInt(limit));

    res.json({
      success: true,
      data: {
        userId,
        logs: result.logs || [],
        total: result.total || 0
      }
    });
  } catch (error) {
    console.error('Erro ao buscar logs do usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;

