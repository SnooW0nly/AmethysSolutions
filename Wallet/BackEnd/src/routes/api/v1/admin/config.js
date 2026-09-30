import express from 'express';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { authenticateAdmin } from '../../../../middlewares/adminAuth.js';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CONFIG_FILE = path.join(process.cwd(), 'config.json');

const router = express.Router();

// GET /api/v1/admin/config - Buscar configurações
router.get('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const configData = await fs.readFile(CONFIG_FILE, 'utf8');
    const config = JSON.parse(configData);

    res.json({
      success: true,
      data: {
        saques_auto: config.saques_auto === 'true' || config.saques_auto === true,
        raw: config
      }
    });
  } catch (error) {
    console.error('Erro ao ler configurações:', error);
    res.status(500).json({
      error: 'Erro ao ler configurações',
      message: error.message
    });
  }
});

// PUT /api/v1/admin/config - Atualizar configurações
router.put('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { saques_auto } = req.body;

    if (saques_auto === undefined) {
      return res.status(400).json({
        error: 'Campo obrigatório ausente',
        message: 'O campo "saques_auto" é obrigatório (true ou false)'
      });
    }

    // Validar valor
    if (typeof saques_auto !== 'boolean' && saques_auto !== 'true' && saques_auto !== 'false') {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'O campo "saques_auto" deve ser true ou false'
      });
    }

    // Ler configuração atual
    let config = {};
    try {
      const configData = await fs.readFile(CONFIG_FILE, 'utf8');
      config = JSON.parse(configData);
    } catch (error) {
      console.log('Arquivo config.json não existe, criando novo...');
    }

    // Ler configuração antiga para auditoria
    const oldConfig = { ...config };

    // Atualizar configuração
    config.saques_auto = saques_auto.toString();

    // Salvar arquivo
    await fs.writeFile(CONFIG_FILE, JSON.stringify(config, null, 4));

    console.log(`✅ Configuração atualizada: saques_auto = ${config.saques_auto}`);

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.CONFIG_UPDATED,
      entity: AUDIT_ENTITIES.CONFIG,
      entityId: 'SYSTEM_CONFIG',
      userId: 'ADMIN',
      userEmail: null,
      dataBefore: oldConfig,
      dataAfter: config,
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Configuração atualizada: saques_auto = ${config.saques_auto}`
    });

    res.json({
      success: true,
      message: 'Configuração atualizada com sucesso',
      data: {
        saques_auto: config.saques_auto === 'true',
        message: 'A alteração será aplicada na próxima verificação do poller (não precisa reiniciar a API)'
      }
    });
  } catch (error) {
    console.error('Erro ao atualizar configurações:', error);
    res.status(500).json({
      error: 'Erro ao atualizar configurações',
      message: error.message
    });
  }
});

export default router;

