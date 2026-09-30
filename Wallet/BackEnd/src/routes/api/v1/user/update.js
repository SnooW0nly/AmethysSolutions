import express from 'express';
import { optionalApiKeyAuth } from '../../../../middlewares/optionalAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { validateEmail } from '../../../../services/security.js';
import Register from '../../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';
import { assertSafeWebhookUrl } from '../../../../services/webhookService.js';

const router = express.Router();

// PUT /api/v1/user/update - Atualiza dados do próprio usuário autenticado
// Rate limit: JWT = 30 req/min | API Key = 50 req/min
router.put('/', strictSmartRateLimiter, optionalApiKeyAuth, async (req, res) => {
  try {
    // Exigir autenticação obrigatória - usar apenas o usuário autenticado
    if (!req.isAuthenticated || !req.user) {
      return res.status(401).json({
        error: 'Autenticação necessária',
        message: 'É necessário fornecer uma API Key válida ou token JWT para atualizar dados do usuário'
      });
    }

    const user = req.user; // Garantir que é o usuário autenticado
    const { name, email, phone, pixKey, pixKeyType, webhookUrl, planAutoRenew, autoUpgrade, aiEnabled } = req.body;

    const updates = {};

    if (phone) updates.phone = phone;

    if (email) {
      if (!validateEmail(email)) {
        return res.status(400).json({
          error: 'Email inválido'
        });
      }
      updates.email = email.toLowerCase().trim();
    }

    if (name) {
      updates.name = name.trim();
    }

    // Atualizar chave PIX se fornecida
    if (pixKey || pixKeyType) {
      if (!pixKey || !pixKeyType) {
        return res.status(400).json({
          error: 'Chave PIX incompleta',
          message: 'É necessário informar tanto "pixKey" quanto "pixKeyType"'
        });
      }

      const validPixKeyTypes = ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'RANDOM'];
      if (!validPixKeyTypes.includes(pixKeyType.toUpperCase())) {
        return res.status(400).json({
          error: 'Tipo de chave PIX inválido',
          message: `O tipo deve ser um dos seguintes: ${validPixKeyTypes.join(', ')}`
        });
      }

      updates.pixKey = pixKey.trim();
      updates.pixKeyType = pixKeyType.toUpperCase();
      updates.pixKeyValidated = false;
    }

    // Atualizar webhook URL se fornecida
    if (webhookUrl !== undefined) {
      if (webhookUrl && typeof webhookUrl === 'string' && webhookUrl.trim()) {
        // Validar URL básica
        try {
          new URL(webhookUrl.trim());
        } catch (urlError) {
          return res.status(400).json({
            error: 'URL de webhook inválida',
            message: 'Forneça uma URL válida (ex: https://seusite.com/webhook)'
          });
        }
        // Validar contra SSRF (bloqueia IPs privados/internos)
        try {
          await assertSafeWebhookUrl(webhookUrl.trim());
        } catch (ssrfErr) {
          return res.status(400).json({
            error: 'URL de webhook inválida',
            message: 'A URL informada aponta para um endereço não permitido.'
          });
        }
        updates.webhookUrl = webhookUrl.trim();
      } else {
        updates.webhookUrl = null;
      }
    }

    // Atualizar renovação automática se fornecida
    if (planAutoRenew !== undefined) {
      if (typeof planAutoRenew !== 'boolean') {
        return res.status(400).json({
          error: 'Valor inválido',
          message: 'O campo "planAutoRenew" deve ser true ou false'
        });
      }
      updates.planAutoRenew = planAutoRenew;
    }

    // Atualizar upgrade automático se fornecido
    if (autoUpgrade !== undefined) {
      if (typeof autoUpgrade !== 'boolean') {
        return res.status(400).json({
          error: 'Valor inválido',
          message: 'O campo "autoUpgrade" deve ser true ou false'
        });
      }
      updates.autoUpgrade = autoUpgrade;
    }



    // Buscar dados antes da atualização para auditoria
    const userBefore = await Register.getById(user.id);

    // Aplicar atualizações
    const updatedUser = await Register.findOneAndUpdate(
      { id: user.id },
      { $set: updates },
      { new: true }
    );

    // Log de auditoria
    if (Object.keys(updates).length > 0) {
      await Audit.saveLog({
        id: generateUniqueId(),
        action: AUDIT_ACTIONS.USER_UPDATED,
        entity: AUDIT_ENTITIES.USER,
        entityId: user.id,
        userId: user.id,
        userEmail: user.email,
        dataBefore: {
          name: userBefore?.name,
          email: userBefore?.email,
          phone: userBefore?.phone,
          pixKey: userBefore?.pixKey,
          pixKeyType: userBefore?.pixKeyType,
          webhookUrl: userBefore?.webhookUrl,
          planAutoRenew: userBefore?.planAutoRenew,
          autoUpgrade: userBefore?.autoUpgrade,
          aiEnabled: userBefore?.aiEnabled !== undefined ? userBefore.aiEnabled : true
        },
        dataAfter: {
          name: updatedUser.name,
          email: updatedUser.email,
          phone: updatedUser.phone,
          pixKey: updatedUser.pixKey,
          pixKeyType: updatedUser.pixKeyType,
          webhookUrl: updatedUser.webhookUrl,
          planAutoRenew: updatedUser.planAutoRenew,
          autoUpgrade: updatedUser.autoUpgrade,
          aiEnabled: updatedUser.aiEnabled !== undefined ? updatedUser.aiEnabled : true
        },
        metadata: { updates },
        ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
        userAgent: req.headers['user-agent'],
        description: `Usuário atualizado: ${updatedUser.name} (${updatedUser.email})`
      });
    }

    res.json({
      success: true,
      message: 'Usuário atualizado com sucesso',
      data: {
        id: updatedUser.id,
        name: updatedUser.name,
        email: updatedUser.email,
        phone: updatedUser.phone,
        pixKey: updatedUser.pixKey,
        pixKeyType: updatedUser.pixKeyType,
        webhookUrl: updatedUser.webhookUrl,
        planAutoRenew: updatedUser.planAutoRenew !== undefined ? updatedUser.planAutoRenew : true,
        autoUpgrade: updatedUser.autoUpgrade || false,
        aiEnabled: updatedUser.aiEnabled !== undefined ? updatedUser.aiEnabled : true,
        updatedAt: updatedUser.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao atualizar usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;
