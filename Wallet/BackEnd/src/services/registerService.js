import Register from '../database/models/Register.js';
import BusinessProfile from '../database/models/BusinessProfile.js';
import { generateApiKey, generateUniqueId, validateTaxID, validateEmail } from './security.js';
import { determineCategory } from './categoryService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../database/models/Audit.js';
import { generateUniqueId as generateAuditId } from './security.js';

/**
 * Cria um registro completo da API quando um usuário se registra no site
 * @param {Object} userData - Dados do usuário
 * @param {string} userData.name - Nome completo
 * @param {string} userData.email - Email
 * @param {string} userData.taxID - CPF/CNPJ
 * @param {string} userData.phone - Telefone (opcional)
 * @param {string} userData.pixKey - Chave PIX (opcional, pode ser criado depois)
 * @param {string} userData.pixKeyType - Tipo da chave PIX (opcional)
 * @param {string} userData.affiliateCode - Código de afiliado (opcional)
 * @param {string} ipAddress - IP do usuário
 * @param {string} userAgent - User agent
 * @returns {Object} - Registro criado
 */
export async function createRegister(userData, ipAddress = null, userAgent = null) {
  const { name, email, taxID, phone, pixKey, pixKeyType, webhookUrl, affiliateCode, birthDate, zipCode, businessProfile: businessProfileData } = userData;

  // Validações
  if (!name || !email) {
    throw new Error('Nome e email são obrigatórios');
  }

  if (!taxID) {
    throw new Error('CPF é obrigatório para criar uma conta');
  }

  if (!birthDate) {
    throw new Error('Data de nascimento é obrigatória para criar uma conta');
  }

  if (!zipCode) {
    throw new Error('CEP é obrigatório para criar uma conta');
  }

  if (!validateEmail(email)) {
    throw new Error('Email inválido');
  }

  const cleanedTaxID = taxID.replace(/[.\-/]/g, '');
  if (!validateTaxID(taxID)) {
    if (cleanedTaxID.length === 11) {
      throw new Error('CPF inválido. Verifique os dígitos verificadores.');
    } else if (cleanedTaxID.length === 14) {
      throw new Error('CNPJ inválido. Verifique os dígitos verificadores.');
    } else {
      throw new Error('CPF/CNPJ inválido. Deve conter 11 dígitos (CPF) ou 14 dígitos (CNPJ)');
    }
  }

  // Validar formato da data de nascimento (YYYY-MM-DD)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) {
    throw new Error('Data de nascimento inválida. Use o formato YYYY-MM-DD');
  }

  // Validar CEP (8 dígitos)
  const cleanedZipCode = zipCode.replace(/\D/g, '');
  if (cleanedZipCode.length !== 8) {
    throw new Error('CEP inválido. Deve conter 8 dígitos');
  }

  // Verificar se já existe
  const existing = await Register.getByEmailOrTaxID(email.toLowerCase(), cleanedTaxID);
  if (existing) {
    throw new Error('Email ou CPF/CNPJ já cadastrado');
  }

  // Validar tipo de chave PIX se fornecido
  if (pixKey && pixKeyType) {
    const validPixKeyTypes = ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'RANDOM'];
    if (!validPixKeyTypes.includes(pixKeyType.toUpperCase())) {
      throw new Error(`Tipo de chave PIX inválido. Deve ser um dos seguintes: ${validPixKeyTypes.join(', ')}`);
    }
  }

  // Verificar se foi indicado por um afiliado
  let affiliate = null;

  if (affiliateCode) {
    try {
      const Affiliate = (await import('../database/models/Affiliate.js')).default;
      affiliate = await Affiliate.findOne({ code: affiliateCode.toLowerCase(), status: 'active' });

      if (affiliate) {
        console.log(`🎁 Novo usuário indicado por afiliado ${affiliate.userEmail} (código: ${affiliateCode})`);
      }
    } catch (affiliateError) {
      console.error('Erro ao verificar código de afiliado:', affiliateError.message);
    }
  }

  // Determinar categoria baseado no perfil do negócio (se fornecido)
  let category = 'WHITE';
  let tier = 1;
  let businessProfileId = null;
  const now = new Date().toISOString();

  // Criar BusinessProfile se dados foram fornecidos
  if (businessProfileData && businessProfileData.businessName && businessProfileData.description) {
    category = determineCategory(businessProfileData);

    const profileId = generateUniqueId();
    const newProfile = {
      id: profileId,
      userId: generateUniqueId(), // Será atualizado após criar o Register
      businessName: businessProfileData.businessName,
      website: businessProfileData.website || null,
      description: businessProfileData.description,
      medFrequency: businessProfileData.medFrequency || 'NEVER',
      category,
      categorizedAt: now,
      categorizedBy: 'SYSTEM',
    };

    const profile = await BusinessProfile.create(newProfile);
    businessProfileId = profile.id;
  }

  // Criar novo registro
  const registerId = generateUniqueId();
  const hasBusinessProfile = businessProfileData && businessProfileData.businessName && businessProfileData.description;

  const newRegister = {
    // Identificação
    id: registerId,
    apiKey: generateApiKey(),

    // Dados pessoais
    name: name.trim(),
    email: email.toLowerCase().trim(),
    taxID: cleanedTaxID || null,
    phone: phone ? phone.trim() : null,

    // Chave PIX (opcional no registro inicial)
    pixKey: pixKey ? pixKey.trim() : null,
    pixKeyType: pixKeyType ? pixKeyType.toUpperCase() : null,
    pixKeyValidated: false,

    // Saldos (todos em centavos)
    balance: 0,
    saldo_split: 0,

    // Categoria (sistema WHITE/BLACK)
    category,
    tier,
    businessProfileId,
    businessProfileCompleted: hasBusinessProfile,

    // Status e limites
    blocked: false,
    status: 'active',
    limits: {
      daily: 999999999,
      monthly: 999999999,
      perTransaction: 500000
    },
    dailyUsed: 0,
    monthlyUsed: 0,

    // API Keys secundárias (vazio inicialmente)
    apiKeys: [],

    // Webhook
    webhookUrl: webhookUrl ? webhookUrl.trim() : null,

    // Sistema de Afiliados
    referredBy: affiliate ? affiliate.id : null,
    referredByCode: affiliate ? affiliateCode.toLowerCase() : null,
    referralDate: affiliate ? now : null,
    isAffiliate: false,
  };

  const register = await Register.create(newRegister);

  // Criar subconta na GoatPay para segregar o saldo do usuário
  try {
    const { createSubaccount } = await import('./goatpayClient.js');
    const subaccountResp = await createSubaccount({
      name: register.name,
      taxID: cleanedTaxID,
      birthDate,
      zipCode: cleanedZipCode,
      externalReference: register.id,
    });
    const subaccountId = subaccountResp?.data?.id || subaccountResp?.id;
    if (subaccountId) {
      await Register.updateOne({ id: register.id }, { $set: { goatpaySubaccountId: subaccountId } });
      register.goatpaySubaccountId = subaccountId;
      console.log(`✅ Subconta GoatPay criada para ${register.email}: ${subaccountId}`);
    } else {
      console.warn(`⚠️ Subconta GoatPay criada mas sem ID retornado para ${register.email}`, subaccountResp);
    }
  } catch (subErr) {
    // Não bloquear o registro se a subconta falhar — logar para investigar
    const errMsg = subErr?.message || subErr?.error || JSON.stringify(subErr);
    console.error(`❌ Erro ao criar subconta GoatPay para ${register.email}:`, errMsg);
    if (subErr?.data) console.error(`❌ Detalhes GoatPay:`, JSON.stringify(subErr.data));
  }

  // Se foi indicado, atualizar estatísticas do afiliado
  if (affiliate) {
    try {
      const Affiliate = (await import('../database/models/Affiliate.js')).default;
      await Affiliate.findOneAndUpdate(
        { id: affiliate.id },
        { $inc: { totalReferrals: 1 } }
      );
      console.log(`📊 Afiliado ${affiliate.userEmail} agora tem ${(affiliate.totalReferrals || 0) + 1} indicados`);
    } catch (affiliateUpdateError) {
      console.error('Erro ao atualizar estatísticas do afiliado:', affiliateUpdateError.message);
    }
  }

  // Log de auditoria
  try {
    await Audit.saveLog({
      id: generateAuditId(),
      action: AUDIT_ACTIONS.USER_CREATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: register.id,
      userId: register.id,
      userEmail: register.email,
      dataAfter: {
        name: register.name,
        email: register.email,
        taxID: register.taxID,
        category: register.category,
        tier: register.tier,
        businessProfileCompleted: register.businessProfileCompleted,
        referredBy: register.referredBy,
        referredByCode: register.referredByCode
      },
      ipAddress,
      userAgent,
      description: `Novo usuário registrado: ${register.name} (${register.email}) [${register.category}]${affiliate ? ` - Indicado por ${affiliate.userEmail}` : ''}`
    });
  } catch (auditError) {
    // Não falhar se o log de auditoria falhar
    console.error('Erro ao salvar log de auditoria:', auditError.message);
  }

  return register;
}

/**
 * Busca um registro por ID
 */
export async function getRegisterById(id) {
  return await Register.getById(id);
}

/**
 * Busca um registro por API Key
 */
export async function getRegisterByApiKey(apiKey) {
  return await Register.getByApiKey(apiKey);
}

/**
 * Busca um registro por email ou taxID
 */
export async function getRegisterByEmailOrTaxID(email, taxID) {
  return await Register.getByEmailOrTaxID(email, taxID);
}
