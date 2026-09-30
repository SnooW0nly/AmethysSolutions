import express from 'express';
import { authenticateApiKey } from '../../../../middlewares/apiAuth.js';
import Register from '../../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// DELETE /api/v1/user/delete - Deleta conta do usuário (soft delete)
router.delete('/', authenticateApiKey, async (req, res) => {
  try {
    const user = req.user;

    const balance = user.balance || 0;
    
    if (balance > 0) {
      return res.status(400).json({
        error: 'Não é possível deletar conta com saldo',
        message: 'Saque todo o saldo antes de deletar a conta',
        balance: balance
      });
    }

    // Log de auditoria antes de deletar
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_DELETED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        name: user.name,
        email: user.email,
        balance: user.balance,
        status: user.status
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Usuário deletado: ${user.name} (${user.email})`
    });

    // Soft delete
    await Register.findOneAndUpdate(
      { id: user.id },
      {
        $set: {
          status: 'deleted',
          deletedAt: new Date().toISOString()
        }
      }
    );

    res.json({
      success: true,
      message: 'Conta deletada com sucesso'
    });

  } catch (error) {
    console.error('Erro ao deletar usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;

