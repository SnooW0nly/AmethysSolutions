import express from 'express';
import { requireDashboardAuth } from '../../../../middlewares/dashboardAuth.js';
import { defaultSmartRateLimiter, strictSmartRateLimiter, apiKeyCreationSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateApiKey } from '../../../../services/security.js';
import Register from '../../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// Permissões disponíveis
const AVAILABLE_PERMISSIONS = {
  'read:balance': 'Ler saldo e estatísticas',
  'read:payments': 'Listar e consultar pagamentos',
  'read:withdraws': 'Listar e consultar saques',
  'read:profile': 'Ler dados do perfil',
  'write:payment:create': 'Criar transações PIX',
  'write:payment:send': 'Enviar dinheiro/reembolsar',
  'write:withdraw:create': 'Criar saques',
  'write:profile:update': 'Atualizar dados do perfil',
  'admin:all': 'Acesso total'
};

// GET /api/v1/user/api-key/permissions - Lista todas as permissões disponíveis (público)
router.get('/permissions', defaultSmartRateLimiter, (req, res) => {
  res.json({
    success: true,
    data: {
      permissions: AVAILABLE_PERMISSIONS,
      description: 'Lista de permissões disponíveis para API Keys'
    }
  });
});

// POST /api/v1/user/api-key/reset - Reseta a API Key usada na autenticação (requer autenticação obrigatória)
router.post('/reset', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const apiKeyInfo = { type: 'main', permissions: ['admin:all'] };

    let newApiKey;
    let keyName;
    let description;

    if (apiKeyInfo.type === 'main') {
      newApiKey = generateApiKey();

      await Register.findOneAndUpdate(
        { id: user.id },
        { $set: { apiKey: newApiKey } }
      );

      keyName = 'API Key Principal';
      description = `API Key principal resetada pelo usuário`;
    }

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: { apiKeyType: apiKeyInfo.type, apiKeyName: keyName },
      dataAfter: { apiKeyType: apiKeyInfo.type, apiKeyName: keyName },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: description
    });

    res.json({
      success: true,
      message: 'API Key resetada com sucesso',
      data: {
        apiKey: newApiKey,
        keyType: apiKeyInfo.type,
        keyName: keyName,
        warning: 'A API Key anterior foi invalidada. Atualize suas integrações com a nova chave.'
      }
    });

  } catch (error) {
    console.error('Erro ao resetar API Key:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/api-key/create - Cria uma nova API Key com permissões específicas
router.post('/create', apiKeyCreationSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const { name, permissions, webhookUrl, plan } = req.body;

    const VALID_PLANS = ['WHITE', 'BLACK'];
    const resolvedPlan = plan && VALID_PLANS.includes(String(plan).toUpperCase())
      ? String(plan).toUpperCase()
      : 'WHITE';

    if (!name || typeof name !== 'string' || name.trim().length === 0) {
      return res.status(400).json({
        error: 'Nome é obrigatório',
        message: 'Forneça um nome descritivo para a API Key'
      });
    }

    if (!permissions || !Array.isArray(permissions) || permissions.length === 0) {
      return res.status(400).json({
        error: 'Permissões são obrigatórias',
        message: 'Forneça pelo menos uma permissão',
        availablePermissions: Object.keys(AVAILABLE_PERMISSIONS)
      });
    }

    const invalidPermissions = permissions.filter(p => !AVAILABLE_PERMISSIONS[p]);
    if (invalidPermissions.length > 0) {
      return res.status(400).json({
        error: 'Permissões inválidas',
        invalidPermissions: invalidPermissions,
        availablePermissions: Object.keys(AVAILABLE_PERMISSIONS)
      });
    }

    if (permissions.includes('admin:all')) {
      return res.status(400).json({
        error: 'Permissão não permitida',
        message: 'A permissão "admin:all" está disponível apenas para a API Key principal'
      });
    }

    const newApiKey = generateApiKey();
    const now = new Date().toISOString();

    // Validar webhookUrl se fornecida
    if (webhookUrl !== undefined && webhookUrl !== null && webhookUrl !== '') {
      try {
        new URL(webhookUrl.trim());
      } catch (urlError) {
        return res.status(400).json({
          error: 'URL de webhook inválida',
          message: 'Forneça uma URL válida (ex: https://seusite.com/webhook)'
        });
      }
    }

    const apiKeyData = {
      key: newApiKey,
      name: name.trim(),
      permissions: permissions,
      plan: resolvedPlan,
      webhookUrl: webhookUrl && webhookUrl.trim() ? webhookUrl.trim() : null,
      createdAt: now,
      lastUsedAt: null,
      active: true
    };

    const currentUser = await Register.getById(user.id);
    const apiKeys = currentUser.apiKeys || [];
    apiKeys.push(apiKeyData);

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { apiKeys: apiKeys } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataAfter: {
        apiKeyCreated: {
          name: apiKeyData.name,
          permissions: apiKeyData.permissions
        }
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Nova API Key criada: ${apiKeyData.name}`
    });

    res.status(201).json({
      success: true,
      message: 'API Key criada com sucesso',
      data: {
        apiKey: newApiKey,
        name: apiKeyData.name,
        permissions: apiKeyData.permissions,
        permissionsDescription: permissions.map(p => ({
          permission: p,
          description: AVAILABLE_PERMISSIONS[p]
        })),
        warning: 'Guarde esta API Key em local seguro. Ela não será exibida novamente.'
      }
    });

  } catch (error) {
    console.error('Erro ao criar API Key:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/user/api-key/list - Lista todas as API Keys do usuário
router.get('/list', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;

    const apiKeysList = [];

    // API Key principal - tratada igual às outras (sem distinção visual)
    apiKeysList.push({
      id: 'main',
      type: 'main',
      name: 'API Key',
      key: user.apiKey, // Incluir a chave para poder copiar
      permissions: ['admin:all'],
      permissionsDescription: [{ permission: 'admin:all', description: AVAILABLE_PERMISSIONS['admin:all'] }],
      webhookUrl: user.webhookUrl || null,
      createdAt: user.createdAt,
      lastUsedAt: user.updatedAt,
      active: user.status === 'active' && !user.blocked
    });

    if (user.apiKeys && Array.isArray(user.apiKeys)) {
      user.apiKeys.forEach((key, index) => {
        apiKeysList.push({
          id: index,
          type: 'secondary',
          name: key.name,
          key: key.key, // Incluir a chave para poder copiar
          permissions: key.permissions,
          plan: key.plan || 'WHITE',
          permissionsDescription: key.permissions.map(p => ({
            permission: p,
            description: AVAILABLE_PERMISSIONS[p]
          })),
          webhookUrl: key.webhookUrl || null,
          createdAt: key.createdAt,
          lastUsedAt: key.lastUsedAt,
          active: key.active !== false
        });
      });
    }

    res.json({
      success: true,
      data: {
        apiKeys: apiKeysList,
        total: apiKeysList.length
      }
    });

  } catch (error) {
    console.error('Erro ao listar API Keys:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/api-key/:index/reset - Reseta uma API Key secundária específica
router.post('/:index/reset', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const index = parseInt(req.params.index);

    if (isNaN(index) || index < 0) {
      return res.status(400).json({
        error: 'Índice inválido',
        message: 'O índice deve ser um número válido'
      });
    }

    const apiKeys = user.apiKeys || [];

    if (index >= apiKeys.length) {
      return res.status(404).json({
        error: 'API Key não encontrada',
        message: 'O índice fornecido não existe'
      });
    }

    const oldKey = apiKeys[index];
    const keyName = oldKey.name || `API Key #${index}`;

    const newApiKey = generateApiKey();

    apiKeys[index].key = newApiKey;
    apiKeys[index].updatedAt = new Date().toISOString();

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { apiKeys: apiKeys } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: { apiKeyType: 'secondary', apiKeyName: keyName },
      dataAfter: { apiKeyType: 'secondary', apiKeyName: keyName },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `API Key secundária resetada: ${keyName}`
    });

    res.json({
      success: true,
      message: 'API Key resetada com sucesso',
      data: {
        apiKey: newApiKey,
        keyType: 'secondary',
        keyName: keyName,
        warning: 'A API Key anterior foi invalidada. Atualize suas integrações com a nova chave.'
      }
    });

  } catch (error) {
    console.error('Erro ao resetar API Key:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// IMPORTANTE: Rotas específicas (/ips) devem vir ANTES de rotas com parâmetros (/:index)
// GET /api/v1/user/api-key/ips - Lista IPs autorizados
router.get('/ips', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;

    const authorizedIPs = (user.authorizedIPs || []).map(ip => ({
      ip: ip.ip,
      active: ip.active !== false,
      createdAt: ip.createdAt
    }));

    res.json({
      success: true,
      data: {
        authorizedIPs,
        total: authorizedIPs.length,
        hasRestriction: authorizedIPs.length > 0
      }
    });

  } catch (error) {
    console.error('Erro ao listar IPs autorizados:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/api-key/ips - Adiciona IP autorizado
router.post('/ips', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const { ip } = req.body;

    if (!ip || typeof ip !== 'string' || ip.trim().length === 0) {
      return res.status(400).json({
        error: 'IP inválido',
        message: 'Forneça um endereço IP válido'
      });
    }

    // Validar formato de IP (IPv4 ou IPv6 básico)
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^0\.0\.0\.0$/;
    const cleanedIP = ip.trim();

    if (!ipRegex.test(cleanedIP)) {
      return res.status(400).json({
        error: 'IP inválido',
        message: 'Forneça um endereço IP válido (IPv4 ou IPv6)'
      });
    }

    const authorizedIPs = user.authorizedIPs || [];

    // Verificar se IP já existe
    if (authorizedIPs.some(aip => aip.ip === cleanedIP)) {
      return res.status(400).json({
        error: 'IP já existe',
        message: 'Este IP já está na lista de IPs autorizados'
      });
    }

    authorizedIPs.push({
      ip: cleanedIP,
      active: true,
      createdAt: new Date().toISOString()
    });

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { authorizedIPs: authorizedIPs } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataAfter: {
        authorizedIPAdded: cleanedIP
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `IP autorizado adicionado: ${cleanedIP}`
    });

    res.status(201).json({
      success: true,
      message: 'IP autorizado adicionado com sucesso',
      data: {
        ip: cleanedIP,
        active: true,
        createdAt: authorizedIPs[authorizedIPs.length - 1].createdAt
      }
    });

  } catch (error) {
    console.error('Erro ao adicionar IP autorizado:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// DELETE /api/v1/user/api-key/ips - Remove IP autorizado
router.delete('/ips', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const { ip } = req.body;
    const ipToRemove = ip;

    if (!ipToRemove || typeof ipToRemove !== 'string' || ipToRemove.trim().length === 0) {
      return res.status(400).json({
        error: 'IP inválido',
        message: 'Forneça um endereço IP válido no body'
      });
    }

    const authorizedIPs = user.authorizedIPs || [];
    const initialLength = authorizedIPs.length;

    const filteredIPs = authorizedIPs.filter(aip => aip.ip !== ipToRemove);

    if (filteredIPs.length === initialLength) {
      return res.status(404).json({
        error: 'IP não encontrado',
        message: 'Este IP não está na lista de IPs autorizados'
      });
    }

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { authorizedIPs: filteredIPs } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        authorizedIPRemoved: ipToRemove
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `IP autorizado removido: ${ipToRemove}`
    });

    res.json({
      success: true,
      message: 'IP autorizado removido com sucesso'
    });

  } catch (error) {
    console.error('Erro ao remover IP autorizado:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/api-key/ips/clear - Remove todos os IPs autorizados
router.post('/ips/clear', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;

    const authorizedIPs = user.authorizedIPs || [];
    const removedCount = authorizedIPs.length;

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { authorizedIPs: [] } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        authorizedIPsCleared: removedCount
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Todos os IPs autorizados foram removidos (${removedCount} IPs)`
    });

    res.json({
      success: true,
      message: 'Todos os IPs autorizados foram removidos',
      data: {
        removedCount
      }
    });

  } catch (error) {
    console.error('Erro ao limpar IPs autorizados:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// DELETE /api/v1/user/api-key/:index - Remove uma API Key secundária
router.delete('/:index', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const index = parseInt(req.params.index);

    if (isNaN(index) || index < 0) {
      return res.status(400).json({
        error: 'Índice inválido',
        message: 'O índice deve ser um número válido'
      });
    }

    const apiKeys = user.apiKeys || [];

    if (index >= apiKeys.length) {
      return res.status(404).json({
        error: 'API Key não encontrada',
        message: 'O índice fornecido não existe'
      });
    }

    const removedKey = apiKeys[index];
    apiKeys.splice(index, 1);

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { apiKeys: apiKeys } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        apiKeyRemoved: {
          name: removedKey.name,
          permissions: removedKey.permissions
        }
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `API Key removida: ${removedKey.name}`
    });

    res.json({
      success: true,
      message: 'API Key removida com sucesso',
      data: {
        removedKey: {
          name: removedKey.name,
          permissions: removedKey.permissions
        }
      }
    });

  } catch (error) {
    console.error('Erro ao remover API Key:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/user/api-key/:index - Atualiza uma API Key secundária
router.put('/:index', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const index = parseInt(req.params.index);
    const { name, permissions, active, webhookUrl, plan } = req.body || {};

    if (isNaN(index) || index < 0) {
      return res.status(400).json({
        error: 'Índice inválido',
        message: 'O índice deve ser um número válido'
      });
    }

    const apiKeys = user.apiKeys || [];

    if (index >= apiKeys.length) {
      return res.status(404).json({
        error: 'API Key não encontrada',
        message: 'O índice fornecido não existe'
      });
    }

    const currentKey = apiKeys[index];
    const updates = {};

    if (name !== undefined) {
      if (typeof name !== 'string' || name.trim().length === 0) {
        return res.status(400).json({
          error: 'Nome inválido',
          message: 'O nome deve ser uma string não vazia'
        });
      }
      updates.name = name.trim();
    }

    if (permissions !== undefined) {
      if (!Array.isArray(permissions) || permissions.length === 0) {
        return res.status(400).json({
          error: 'Permissões inválidas',
          message: 'As permissões devem ser um array não vazio',
          availablePermissions: Object.keys(AVAILABLE_PERMISSIONS)
        });
      }

      const invalidPermissions = permissions.filter(p => !AVAILABLE_PERMISSIONS[p]);
      if (invalidPermissions.length > 0) {
        return res.status(400).json({
          error: 'Permissões inválidas',
          invalidPermissions: invalidPermissions,
          availablePermissions: Object.keys(AVAILABLE_PERMISSIONS)
        });
      }

      if (permissions.includes('admin:all')) {
        return res.status(400).json({
          error: 'Permissão não permitida',
          message: 'A permissão "admin:all" está disponível apenas para a API Key principal'
        });
      }

      updates.permissions = permissions;
    }

    if (active !== undefined) {
      if (typeof active !== 'boolean') {
        return res.status(400).json({
          error: 'Status inválido',
          message: 'O campo "active" deve ser um booleano'
        });
      }
      updates.active = active;
    }

    if (webhookUrl !== undefined) {
      if (webhookUrl && typeof webhookUrl === 'string' && webhookUrl.trim()) {
        try {
          new URL(webhookUrl.trim());
          updates.webhookUrl = webhookUrl.trim();
        } catch (urlError) {
          return res.status(400).json({
            error: 'URL de webhook inválida',
            message: 'Forneça uma URL válida (ex: https://seusite.com/webhook)'
          });
        }
      } else {
        updates.webhookUrl = null;
      }
    }

    if (plan !== undefined) {
      const VALID_PLANS = ['WHITE', 'BLACK'];
      const resolvedPlan = String(plan).toUpperCase();
      if (!VALID_PLANS.includes(resolvedPlan)) {
        return res.status(400).json({
          error: 'Plano inválido',
          message: 'O plano deve ser WHITE ou BLACK'
        });
      }
      updates.plan = resolvedPlan;
    }

    Object.assign(apiKeys[index], updates);
    apiKeys[index].updatedAt = new Date().toISOString();

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { apiKeys: apiKeys } }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        apiKey: {
          name: currentKey.name,
          permissions: currentKey.permissions,
          active: currentKey.active
        }
      },
      dataAfter: {
        apiKey: {
          name: apiKeys[index].name,
          permissions: apiKeys[index].permissions,
          active: apiKeys[index].active
        }
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `API Key atualizada: ${apiKeys[index].name}`
    });

    res.json({
      success: true,
      message: 'API Key atualizada com sucesso',
      data: {
        apiKey: {
          name: apiKeys[index].name,
          permissions: apiKeys[index].permissions,
          permissionsDescription: apiKeys[index].permissions.map(p => ({
            permission: p,
            description: AVAILABLE_PERMISSIONS[p]
          })),
          webhookUrl: apiKeys[index].webhookUrl || null,
          active: apiKeys[index].active,
          updatedAt: apiKeys[index].updatedAt
        }
      }
    });

  } catch (error) {
    console.error('Erro ao atualizar API Key:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/user/api-key/main - Atualiza a API Key principal (webhook)
router.put('/main', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;
    const { webhookUrl } = req.body;

    const updates = {};

    if (webhookUrl !== undefined) {
      if (webhookUrl && typeof webhookUrl === 'string' && webhookUrl.trim()) {
        try {
          new URL(webhookUrl.trim());
          updates.webhookUrl = webhookUrl.trim();
        } catch (urlError) {
          return res.status(400).json({
            error: 'URL de webhook inválida',
            message: 'Forneça uma URL válida (ex: https://seusite.com/webhook)'
          });
        }
      } else {
        updates.webhookUrl = null;
      }
    }

    await Register.findOneAndUpdate(
      { id: user.id },
      { $set: updates }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataAfter: {
        mainApiKeyWebhookUpdated: updates.webhookUrl
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Webhook da API Key principal atualizado`
    });

    res.json({
      success: true,
      message: 'API Key principal atualizada com sucesso',
      data: {
        webhookUrl: updates.webhookUrl || null
      }
    });

  } catch (error) {
    console.error('Erro ao atualizar API Key principal:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/user/api-key/main - Obtém a API Key principal
router.get('/main', defaultSmartRateLimiter, requireDashboardAuth, async (req, res) => {
  try {
    const user = req.user;

    res.json({
      success: true,
      data: {
        apiKey: user.apiKey,
        webhookUrl: user.webhookUrl || null
      }
    });

  } catch (error) {
    console.error('Erro ao obter API Key principal:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;