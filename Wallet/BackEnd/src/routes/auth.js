import express from "express";
import User from "../database/models/User.js";
import VerificationCode from "../database/models/VerificationCode.js";
import { generateVerificationCode, sendVerificationCode, sendSignupVerificationCode } from "../services/emailService.js";
import { generateToken } from "../services/authService.js";
import { authenticate } from "../middlewares/auth.js";
import { authRateLimiter } from "../middlewares/rateLimiter.js";
import { securityConfig } from "../config/security.js";
import { validatePassword } from "../utils/passwordValidator.js";
import cors from "cors";
import { corsOptions } from "../config/cors.js";

const router = express.Router();

// Importar função centralizada para obter IP do cliente
import { getClientIP } from "../utils/getClientIP.js";

// Rate limiting para cadastro e login (usa o sistema de segurança)
const authLimiter = authRateLimiter;

// Cache para rate limiting por email
const codeRequestCounts = new Map();
const signupRequestCounts = new Map();

// Cache para rate limiting por IP (proteção contra spam)
const ipCodeRequestCounts = new Map();
const ipSignupRequestCounts = new Map();

// Lista de domínios temporários conhecidos (para bloquear)
const TEMPORARY_EMAIL_DOMAINS = [
  // Clássicos
  '10minutemail.com',
  '10minutemail.net',
  '10minemail.com',
  'guerrillamail.com',
  'guerrillamail.net',
  'guerrillamail.org',
  'guerrillamailblock.com',
  'guerrillamail.biz',
  'tempmail.com',
  'temp-mail.org',
  'temp-mail.io',
  'temp-mail.net',
  'throwaway.email',
  'mailinator.com',
  'mailinator.net',
  'mailinator.org',
  'yopmail.com',
  'yopmail.fr',
  'yopmail.net',
  'getnada.com',
  'mohmal.com',
  'fakeinbox.com',
  'trashmail.com',
  'dispostable.com',
  'mintemail.com',
  'sharklasers.com',
  'grr.la',
  'spamgourmet.com',
  'firemail.com.br',

  // Bastante usados hoje
  'emailondeck.com',
  'emaildrop.io',
  'inboxbear.com',
  'inboxkitten.com',
  'tempr.email',
  'tempmailo.com',
  'tempmail.plus',
  'tempmail.ninja',
  'tempmail.dev',
  'tempmail.space',
  'tempinbox.com',
  'tempinbox.co.uk',
  'tempmailbox.com',
  'tempmailaddress.com',
  'discard.email',
  'discardmail.com',
  'burnermail.io',
  'burneremail.co',
  'anonaddy.com',
  'simplelogin.com',

  // Variantes / aliases comuns
  'maildrop.cc',
  'maildrop.xyz',
  'mytemp.email',
  'temporarymail.com',
  'fakemail.net',
  'fakemailgenerator.com',
  'spambox.us',
  'spamdecoy.net',
  'spamavert.com',
  'spamfree24.org',

  // Menos conhecidos (mas usados por bots)
  'dropmail.me',
  'dropmail.to',
  'luxusmail.org',
  'nowmymail.com',
  'oneoffemail.com',
  'mail-temporaire.fr',
  'mail-temporaire.com',
  'mailforspam.com',
  'mailcatch.com',
  'mailnesia.com',
  'mailnull.com'
];

// Função para validar email (bloquear domínios temporários)
function isValidEmail(email) {
  if (!email || typeof email !== 'string') return false;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) return false;

  const domain = email.split('@')[1]?.toLowerCase();
  if (!domain) return false;

  // Bloquear domínios temporários conhecidos
  if (TEMPORARY_EMAIL_DOMAINS.some(tempDomain => domain.includes(tempDomain))) {
    return false;
  }

  return true;
}

// Limpa contadores expirados periodicamente
setInterval(() => {
  const now = Date.now();
  for (const [email, data] of codeRequestCounts.entries()) {
    if (now - data.resetTime > 5 * 60 * 1000) {
      codeRequestCounts.delete(email);
    }
  }
  for (const [email, data] of signupRequestCounts.entries()) {
    if (now - data.resetTime > 15 * 60 * 1000) {
      signupRequestCounts.delete(email);
    }
  }
  for (const [ip, data] of ipCodeRequestCounts.entries()) {
    if (now - data.resetTime > 15 * 60 * 1000) {
      ipCodeRequestCounts.delete(ip);
    }
  }
  for (const [ip, data] of ipSignupRequestCounts.entries()) {
    if (now - data.resetTime > 60 * 60 * 1000) {
      ipSignupRequestCounts.delete(ip);
    }
  }
}, 60000); // Limpa a cada 1 minuto

// Rate limiting para solicitar código (mais restritivo) - POR EMAIL E POR IP
// Não aplica rate limit se o dispositivo for confiável
const codeLimiter = async (req, res, next) => {
  const email = req.body?.email;
  const clientIP = getClientIP(req);

  // Validar email antes de processar
  if (email && !isValidEmail(email)) {
    return res.status(400).json({
      success: false,
      error: "E-mail inválido ou não permitido",
    });
  }

  if (!email) {
    return next(); // Se não tiver email, deixa passar (será validado depois)
  }

  // Verificar se o dispositivo é confiável ANTES de aplicar rate limit
  try {
    const user = await User.findOne({ email: email.toLowerCase() });
    if (user) {
      const TrustedDevice = (await import("../database/models/TrustedDevice.js")).default;
      const deviceId = TrustedDevice.generateDeviceId(
        req.headers["user-agent"],
        clientIP
      );

      const trustedDevice = await TrustedDevice.findTrustedDevice(user._id, deviceId);

      // Se dispositivo é confiável, não aplicar rate limit
      if (trustedDevice) {
        return next();
      }
    }
  } catch (error) {
    // Se der erro ao verificar dispositivo, continua com rate limit normal
    // Não logar erro por segurança
  }

  // Rate limiting por IP (proteção contra spam de múltiplos emails)
  const ipWindowMs = 15 * 60 * 1000; // 15 minutos
  const ipMax = 10; // Máximo 10 requisições de código por IP em 15 minutos

  let ipData = ipCodeRequestCounts.get(clientIP);
  if (!ipData || Date.now() - ipData.resetTime > ipWindowMs) {
    ipData = {
      count: 0,
      resetTime: Date.now(),
    };
    ipCodeRequestCounts.set(clientIP, ipData);
  }

  ipData.count++;

  if (ipData.count > ipMax) {
    const retryAfter = Math.ceil((ipData.resetTime + ipWindowMs - Date.now()) / 1000);
    return res.status(429).json({
      success: false,
      error: "Muitas tentativas deste IP. Tente novamente em 15 minutos.",
      retryAfter,
    });
  }

  // Rate limiting por email
  const identifier = email.toLowerCase();
  const windowMs = 5 * 60 * 1000; // 5 minutos
  const max = 3; // 3 tentativas por email

  const now = Date.now();

  let data = codeRequestCounts.get(identifier);

  if (!data || now - data.resetTime > windowMs) {
    data = {
      count: 0,
      resetTime: now,
    };
    codeRequestCounts.set(identifier, data);
  }

  data.count++;

  res.setHeader('X-RateLimit-Limit', max);
  res.setHeader('X-RateLimit-Remaining', Math.max(0, max - data.count));
  res.setHeader('X-RateLimit-Reset', Math.floor((data.resetTime + windowMs) / 1000));

  if (data.count > max) {
    const retryAfter = Math.ceil((data.resetTime + windowMs - now) / 1000);
    return res.status(429).json({
      success: false,
      error: "Muitas tentativas. Tente novamente em 5 minutos.",
      retryAfter,
    });
  }

  next();
};

// Rate limiting específico para criação de contas (verificação de código) - POR EMAIL E POR IP
const signupVerifyLimiter = (req, res, next) => {
  const email = req.body?.email;
  const clientIP = getClientIP(req);

  // Validar email antes de processar
  if (email && !isValidEmail(email)) {
    return res.status(400).json({
      success: false,
      error: "E-mail inválido ou não permitido",
    });
  }

  if (!email) {
    return next(); // Se não tiver email, deixa passar (será validado depois)
  }

  // Rate limiting por IP (proteção contra spam de múltiplas contas)
  const ipWindowMs = 60 * 60 * 1000; // 1 hora
  const ipMax = 5; // Máximo 5 criações de conta por IP em 1 hora

  let ipData = ipSignupRequestCounts.get(clientIP);
  if (!ipData || Date.now() - ipData.resetTime > ipWindowMs) {
    ipData = {
      count: 0,
      resetTime: Date.now(),
    };
    ipSignupRequestCounts.set(clientIP, ipData);
  }

  ipData.count++;

  if (ipData.count > ipMax) {
    const retryAfter = Math.ceil((ipData.resetTime + ipWindowMs - Date.now()) / 1000);
    return res.status(429).json({
      success: false,
      error: "Muitas tentativas de criação de conta deste IP. Tente novamente em 1 hora.",
      retryAfter,
    });
  }

  // Rate limiting por email
  const identifier = email.toLowerCase();
  const windowMs = 15 * 60 * 1000; // 15 minutos
  const max = 5; // 5 tentativas de criar conta por email

  const now = Date.now();

  let data = signupRequestCounts.get(identifier);

  if (!data || now - data.resetTime > windowMs) {
    data = {
      count: 0,
      resetTime: now,
    };
    signupRequestCounts.set(identifier, data);
  }

  data.count++;

  res.setHeader('X-RateLimit-Limit', max);
  res.setHeader('X-RateLimit-Remaining', Math.max(0, max - data.count));
  res.setHeader('X-RateLimit-Reset', Math.floor((data.resetTime + windowMs) / 1000));

  if (data.count > max) {
    const retryAfter = Math.ceil((data.resetTime + windowMs - now) / 1000);
    return res.status(429).json({
      success: false,
      error: "Muitas tentativas de criação de conta. Tente novamente em 15 minutos.",
      retryAfter,
    });
  }

  next();
};

// Middleware para validar origem CORS em rotas sensíveis
const validateCorsOrigin = (req, res, next) => {
  const origin = req.headers.origin;
  const referer = req.headers.referer;
  const nodeEnv = process.env.NODE_ENV || 'development';

  // Em produção, sempre validar origem
  if (nodeEnv === 'production') {
    if (!origin && !referer) {
      return res.status(403).json({
        success: false,
        error: "Acesso negado. Requisições devem ser feitas através da dashboard.",
      });
    }

    // Verificar se origin ou referer está na lista de permitidos
    const allowedOrigins = [
      process.env.FRONTEND_URL,
      process.env.FRONTEND_URL_SECONDARY,
    ].filter(Boolean);

    if (allowedOrigins.length > 0) {
      const isAllowed = origin && allowedOrigins.includes(origin) ||
        referer && allowedOrigins.some(url => referer.startsWith(url));

      if (!isAllowed) {
        return res.status(403).json({
          success: false,
          error: "Acesso negado. Requisições devem ser feitas através da dashboard.",
        });
      }
    }
  }

  next();
};

// Middleware para validar IP confiável em rotas restritas
const validateTrustedIP = (req, res, next) => {
  const trustedIPs = (process.env.TRUSTED_IPS || '').split(',').map(ip => ip.trim()).filter(Boolean);

  // Se não houver IPs confiáveis definidos, permitir acesso (ou bloquear tudo, dependendo da política - aqui assumimos que se não definido, não restringe)
  // Mas o usuário pediu explicitamente para aceitar SÓ nessas rotas pelo IP em .env.
  // Se TRUSTED_IPS estiver vazio, talvez devêssemos bloquear? O usuário disse "faça a api só aceitar requisição nessas rotas pelo ip em .env".
  // Vou assumir que se TRUSTED_IPS estiver definido, a restrição vale.

  if (trustedIPs.length > 0) {
    const clientIP = getClientIP(req);

    // Verificar se o IP do cliente está na lista de IPs confiáveis
    if (!trustedIPs.includes(clientIP)) {
      console.warn(`[AUTH] Acesso negado para IP não confiável: ${clientIP} na rota ${req.path}`);
      return res.status(403).json({
        success: false,
        error: "Acesso negado. IP não autorizado.",
      });
    }
  }

  next();
};

// ========================= ANÁLISE DE DESCRIÇÃO DE NEGÓCIO POR IA =========================
router.post("/analyze-business", validateCorsOrigin, cors(corsOptions), async (req, res) => {
  try {
    const { description } = req.body;

    if (!description) {
      return res.status(400).json({
        success: false,
        error: "Descrição é obrigatória",
      });
    }

    // Validar tamanho mínimo e máximo
    if (description.length < 100) {
      return res.status(400).json({
        success: false,
        error: "Descrição deve ter pelo menos 100 caracteres",
        minLength: 100,
        currentLength: description.length,
      });
    }

    if (description.length > 1000) {
      return res.status(400).json({
        success: false,
        error: "Descrição deve ter no máximo 1000 caracteres",
        maxLength: 1000,
        currentLength: description.length,
      });
    }

    // Analisar descrição usando IA
    const { analyzeBusinessDescription } = await import('../services/aiService.js');
    const analysis = await analyzeBusinessDescription(description);

    res.json({
      success: true,
      ...analysis,
    });
  } catch (error) {
    console.error("[AUTH] Erro ao analisar descrição:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao analisar descrição",
    });
  }
});

// ========================= CADASTRO - SOLICITAR CÓDIGO =========================
// Em produção, validar origem da dashboard (CORS) ao invés de restringir por IP
router.post("/signup/request-code", validateCorsOrigin, cors(corsOptions), codeLimiter, async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email) {
      return res.status(400).json({
        success: false,
        error: "E-mail é obrigatório",
      });
    }

    // Validar formato de email novamente (dupla validação)
    if (!isValidEmail(email)) {
      return res.status(400).json({
        success: false,
        error: "E-mail inválido ou não permitido",
      });
    }

    // Validar senha antes de enviar código (opcional, mas recomendado)
    if (password) {
      const passwordValidation = validatePassword(password);
      if (!passwordValidation.valid) {
        return res.status(400).json({
          success: false,
          error: passwordValidation.errors.join(', '),
        });
      }
    }

    // Verificar se o usuário já existe
    const existingUser = await User.findOne({ email: email.toLowerCase() });
    if (existingUser) {
      return res.status(400).json({
        success: false,
        error: "E-mail já cadastrado",
      });
    }

    // Gerar código de verificação
    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10); // Expira em 10 minutos

    // Salvar código no banco
    await VerificationCode.create({
      email: email.toLowerCase(),
      code,
      expiresAt,
      ip: getClientIP(req),
      userAgent: req.headers["user-agent"],
      type: 'signup',
    });

    // Enviar código por e-mail
    const emailSent = await sendSignupVerificationCode(email.toLowerCase(), code);

    if (!emailSent) {
      console.error(`[AUTH] Falha ao enviar código para ${email}`);
      // Não retornar erro ao usuário por questões de segurança
    }

    res.json({
      success: true,
      message: "Código de verificação enviado para seu e-mail",
    });
  } catch (error) {
    console.error("[AUTH] Erro ao solicitar código de cadastro:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar solicitação",
    });
  }
});

// ========================= CADASTRO - VERIFICAR CÓDIGO E CRIAR CONTA =========================
// Em produção, validar origem da dashboard (CORS) ao invés de restringir por IP
router.post("/signup/verify-code", validateCorsOrigin, cors(corsOptions), signupVerifyLimiter, async (req, res) => {
  try {
    const { fullName, email, password, code, birthDate, phone, zipCode } = req.body;

    // Validações
    if (!fullName || !email || !password || !code) {
      return res.status(400).json({
        success: false,
        error: "Nome completo, e-mail, senha e código são obrigatórios",
      });
    }

    // Validar formato de email novamente (dupla validação)
    if (!isValidEmail(email)) {
      return res.status(400).json({
        success: false,
        error: "E-mail inválido ou não permitido",
      });
    }

    // Validar senha forte
    const passwordValidation = validatePassword(password);
    if (!passwordValidation.valid) {
      return res.status(400).json({
        success: false,
        error: passwordValidation.errors.join(', '),
      });
    }

    // Verificar se o usuário já existe
    const existingUser = await User.findOne({ email: email.toLowerCase() });
    if (existingUser) {
      return res.status(400).json({
        success: false,
        error: "E-mail já cadastrado",
      });
    }

    // Buscar código de verificação mais recente para o email
    const verificationCode = await VerificationCode.findOne({
      email: email.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
    }).sort({ createdAt: -1 });

    if (!verificationCode) {
      return res.status(401).json({
        success: false,
        error: "Código inválido ou expirado",
      });
    }

    // Verificar limite de tentativas (máximo 3)
    if (verificationCode.attempts >= 3) {
      return res.status(429).json({
        success: false,
        error: "Limite de tentativas excedido. Solicite um novo código.",
      });
    }

    // Verificar se o código está correto
    if (verificationCode.code !== code) {
      // Incrementar tentativas
      verificationCode.attempts += 1;
      await verificationCode.save();

      const remainingAttempts = 3 - verificationCode.attempts;
      return res.status(401).json({
        success: false,
        error: `Código inválido. ${remainingAttempts > 0 ? `Restam ${remainingAttempts} tentativa(s).` : 'Limite de tentativas excedido.'}`,
      });
    }

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    // Criar usuário
    const user = new User({
      fullName,
      email: email.toLowerCase(),
      password,
      birthDate: birthDate ? new Date(birthDate) : undefined,
      phone,
      emailVerified: true, // E-mail verificado via código
    });

    await user.save();

    // Criar registro completo da API (Register)
    let registerData = null;
    try {
      // Validar taxID apenas se fornecido
      if (req.body.taxID) {
        const { validateTaxID } = await import('../services/security.js');
        const cleanedTaxID = req.body.taxID.replace(/[.\-/]/g, '');

        if (!validateTaxID(req.body.taxID)) {
          // Determinar se é CPF ou CNPJ para mensagem de erro mais específica
          let errorMessage = 'CPF/CNPJ inválido. Deve conter 11 dígitos (CPF) ou 14 dígitos (CNPJ)';
          if (cleanedTaxID.length === 11) {
            errorMessage = 'CPF inválido. Verifique os dígitos verificadores.';
          } else if (cleanedTaxID.length === 14) {
            errorMessage = 'CNPJ inválido. Verifique os dígitos verificadores.';
          }

          return res.status(400).json({
            success: false,
            error: errorMessage,
          });
        }
      }

      const { createRegister } = await import('../services/registerService.js');
      // Passar o taxID original, o service fará a limpeza necessária
      // Passar plan (FREE ou BLACK) - se não informado, será FREE
      const register = await createRegister(
        {
          name: fullName,
          email: email.toLowerCase(),
          taxID: req.body.taxID,
          phone,
          birthDate,
          zipCode,
          pixKey: req.body.pixKey || null,
          pixKeyType: req.body.pixKeyType || null,
          affiliateCode: req.body.affiliateCode || null, // Código de afiliado para indicação
          plan: req.body.plan || 'FREE', // Plano inicial (FREE ou BLACK)
          businessProfile: req.body.businessProfile || null, // Perfil de negócio preenchido no cadastro
        },
        getClientIP(req),
        req.headers['user-agent']
      );

      registerData = {
        registerId: register.id,
        apiKey: register.apiKey,
      };
    } catch (registerError) {
      // Se falhar ao criar registro, retornar erro
      console.error('[AUTH] Erro ao criar registro da API:', registerError.message);
      return res.status(400).json({
        success: false,
        error: registerError.message || 'Erro ao criar registro da API',
      });
    }

    // Remover senha da resposta
    const userResponse = user.toObject();
    delete userResponse.password;

    // Adicionar dados do registro se criado
    if (registerData) {
      Object.assign(userResponse, registerData);
    }

    // Gerar token JWT para login automático após cadastro
    const token = generateToken(user._id);

    // Criar sessão para o novo usuário
    try {
      const Session = (await import("../database/models/Session.js")).default;
      const userAgent = req.headers["user-agent"] || "Unknown";
      let deviceName = "Dispositivo desconhecido";

      if (userAgent.includes("Chrome")) {
        deviceName = "Chrome";
      } else if (userAgent.includes("Firefox")) {
        deviceName = "Firefox";
      } else if (userAgent.includes("Safari")) {
        deviceName = "Safari";
      } else if (userAgent.includes("Edge")) {
        deviceName = "Edge";
      }

      if (userAgent.includes("Windows")) {
        deviceName += " no Windows";
      } else if (userAgent.includes("Mac")) {
        deviceName += " no macOS";
      } else if (userAgent.includes("Linux")) {
        deviceName += " no Linux";
      } else if (userAgent.includes("Android")) {
        deviceName += " no Android";
      } else if (userAgent.includes("iPhone") || userAgent.includes("iPad")) {
        deviceName += " no iOS";
      }

      await Session.createFromToken(token, user._id, {
        userAgent,
        ip: getClientIP(req),
        deviceName,
      });
    } catch (sessionError) {
      console.error("[AUTH] Erro ao criar sessão no signup:", sessionError);
      // Continuar mesmo se falhar ao criar sessão
    }

    // Notificação Discord de novo registro
    (async () => {
      try {
        const { notifyRegister } = await import('../services/discordNotifier.js');
        await notifyRegister({
          email: email.toLowerCase(),
          name: fullName,
          taxID: req.body.taxID,
          plan: req.body.plan || 'FREE',
          ip: getClientIP(req),
          userAgent: req.headers['user-agent']
        });
      } catch (e) {
        console.error('[DISCORD] Erro ao notificar registro:', e.message);
      }
    })();

    res.status(201).json({
      success: true,
      message: "Usuário cadastrado com sucesso",
      token,
      user: userResponse,
    });
  } catch (error) {
    console.error("[AUTH] Erro no cadastro:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao cadastrar usuário",
    });
  }
});

// ========================= LOGIN - SOLICITAR CÓDIGO =========================
router.post("/login/request-code", validateCorsOrigin, codeLimiter, async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        success: false,
        error: "E-mail e senha são obrigatórios",
      });
    }

    // Buscar usuário
    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      return res.status(401).json({
        success: false,
        error: "E-mail ou senha incorretos",
      });
    }

    // Bloqueio não impede login - apenas operações específicas

    // Verificar senha
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      return res.status(401).json({
        success: false,
        error: "E-mail ou senha incorretos",
      });
    }

    // Verificar se o dispositivo é confiável
    const TrustedDevice = (await import("../database/models/TrustedDevice.js")).default;
    const deviceId = TrustedDevice.generateDeviceId(
      req.headers["user-agent"],
      getClientIP(req)
    );

    const trustedDevice = await TrustedDevice.findTrustedDevice(user._id, deviceId);

    if (trustedDevice) {
      // Dispositivo confiável - fazer login direto sem código
      await trustedDevice.updateLastUsed();

      // Atualizar último login e IP
      user.lastLogin = new Date();
      user.addIpToHistory(getClientIP(req));
      await user.save();

      // Gerar token JWT
      const token = generateToken(user._id);

      // Criar sessão
      try {
        const Session = (await import("../database/models/Session.js")).default;
        const userAgent = req.headers["user-agent"] || "Unknown";
        let deviceName = "Dispositivo desconhecido";

        if (userAgent.includes("Chrome")) {
          deviceName = "Chrome";
        } else if (userAgent.includes("Firefox")) {
          deviceName = "Firefox";
        } else if (userAgent.includes("Safari")) {
          deviceName = "Safari";
        } else if (userAgent.includes("Edge")) {
          deviceName = "Edge";
        }

        if (userAgent.includes("Windows")) {
          deviceName += " no Windows";
        } else if (userAgent.includes("Mac")) {
          deviceName += " no macOS";
        } else if (userAgent.includes("Linux")) {
          deviceName += " no Linux";
        } else if (userAgent.includes("Android")) {
          deviceName += " no Android";
        } else if (userAgent.includes("iPhone") || userAgent.includes("iPad")) {
          deviceName += " no iOS";
        }

        await Session.createFromToken(token, user._id, {
          userAgent,
          ip: getClientIP(req),
          deviceName,
        });
      } catch (sessionError) {
        console.error("[AUTH] Erro ao criar sessão:", sessionError);
        // Continuar mesmo se falhar ao criar sessão
      }

      // Remover senha da resposta
      const userResponse = user.toObject();
      delete userResponse.password;

      // Notificação Discord de login
      (async () => {
        try {
          const { notifyLogin } = await import('../services/discordNotifier.js');
          await notifyLogin({
            email: user.email,
            name: user.fullName,
            ip: getClientIP(req),
            userAgent: req.headers['user-agent'],
            method: 'Dispositivo Confiável',
            success: true
          });
        } catch (e) {
          console.error('[DISCORD] Erro ao notificar login:', e.message);
        }
      })();

      // Cookie removed as requested
      // res.cookie("token", token, cookieOptions);

      return res.json({
        success: true,
        message: "Login realizado com sucesso",
        token,
        user: userResponse,
        trustedDevice: true,
      });
    }

    // Dispositivo não confiável - gerar código de verificação
    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10); // Expira em 10 minutos

    // Salvar código no banco
    await VerificationCode.create({
      email: email.toLowerCase(),
      code,
      expiresAt,
      ip: getClientIP(req),
      userAgent: req.headers["user-agent"],
      type: 'login',
    });

    // Enviar código por e-mail
    const emailSent = await sendVerificationCode(email.toLowerCase(), code);

    if (!emailSent) {
      console.error(`[AUTH] Falha ao enviar código para ${email}`);
      // Não retornar erro ao usuário por questões de segurança
    }

    res.json({
      success: true,
      message: "Código de verificação enviado para seu e-mail",
      requiresCode: true,
    });
  } catch (error) {
    console.error("[AUTH] Erro ao solicitar código:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar solicitação",
    });
  }
});

// ========================= ESQUECEU SENHA - SOLICITAR CÓDIGO =========================
router.post("/forgot-password/request-code", validateCorsOrigin, codeLimiter, async (req, res) => {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({
        success: false,
        error: "E-mail é obrigatório",
      });
    }

    // Buscar usuário
    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      // Por segurança, não informar se o email existe ou não
      return res.json({
        success: true,
        message: "Se o e-mail estiver cadastrado, você receberá um código de verificação",
      });
    }

    // Bloqueio não impede recuperação de senha

    // Gerar código de verificação
    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10); // Expira em 10 minutos

    // Salvar código no banco
    await VerificationCode.create({
      email: email.toLowerCase(),
      code,
      expiresAt,
      ip: getClientIP(req),
      userAgent: req.headers["user-agent"],
      type: 'forgot-password',
    });

    // Enviar código por e-mail
    const emailSent = await sendVerificationCode(email.toLowerCase(), code);

    if (!emailSent) {
      console.error(`[AUTH] Falha ao enviar código para ${email}`);
    }

    // Por segurança, sempre retornar sucesso mesmo se o email não existir
    res.json({
      success: true,
      message: "Se o e-mail estiver cadastrado, você receberá um código de verificação",
    });
  } catch (error) {
    console.error("[AUTH] Erro ao solicitar código de recuperação:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar solicitação",
    });
  }
});

// ========================= ESQUECEU SENHA - VERIFICAR CÓDIGO E REDEFINIR SENHA =========================
router.post("/forgot-password/verify-code", validateCorsOrigin, authLimiter, async (req, res) => {
  try {
    const { email, code, newPassword } = req.body;

    if (!email || !code || !newPassword) {
      return res.status(400).json({
        success: false,
        error: "E-mail, código e nova senha são obrigatórios",
      });
    }

    // Validar senha forte
    const passwordValidation = validatePassword(newPassword);
    if (!passwordValidation.valid) {
      return res.status(400).json({
        success: false,
        error: passwordValidation.errors.join(', '),
      });
    }

    // Buscar código de verificação
    const verificationCode = await VerificationCode.findOne({
      email: email.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
      type: 'forgot-password',
    }).sort({ createdAt: -1 });

    if (!verificationCode) {
      return res.status(401).json({
        success: false,
        error: "Código inválido ou expirado",
      });
    }

    if (verificationCode.attempts >= 3) {
      return res.status(429).json({
        success: false,
        error: "Limite de tentativas excedido. Solicite um novo código.",
      });
    }

    if (verificationCode.code !== code) {
      verificationCode.attempts += 1;
      await verificationCode.save();

      const remainingAttempts = 3 - verificationCode.attempts;
      return res.status(401).json({
        success: false,
        error: `Código inválido. ${remainingAttempts > 0 ? `Restam ${remainingAttempts} tentativa(s).` : 'Limite de tentativas excedido.'}`,
      });
    }

    // Buscar usuário
    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      return res.status(404).json({
        success: false,
        error: "Usuário não encontrado",
      });
    }

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    // Atualizar senha
    user.password = newPassword;
    await user.save();

    // Gerar token JWT para login automático
    const token = generateToken(user._id);

    // Remover senha da resposta
    const userResponse = user.toObject();
    delete userResponse.password;

    // Configurar cookie usando configurações de segurança
    const cookieOptions = {
      httpOnly: securityConfig.cookies.httpOnly,
      secure: securityConfig.cookies.secure,
      sameSite: securityConfig.cookies.sameSite,
      maxAge: securityConfig.cookies.maxAge,
      path: securityConfig.cookies.path,
    };

    // Adicionar domain apenas se estiver definido e não for vazio
    const domain = securityConfig.cookies.domain;
    if (domain && typeof domain === 'string' && domain.trim() !== '') {
      cookieOptions.domain = domain.trim();
    }

    res.cookie("token", token, cookieOptions);

    res.json({
      success: true,
      message: "Senha redefinida com sucesso",
      token,
      user: userResponse,
    });
  } catch (error) {
    console.error("[AUTH] Erro ao redefinir senha:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar redefinição de senha",
    });
  }
});

// ========================= LOGIN - VERIFICAR CÓDIGO =========================
router.post("/login/verify-code", validateCorsOrigin, authLimiter, async (req, res) => {
  try {
    const { email, code, trustDevice } = req.body;

    if (!email || !code) {
      return res.status(400).json({
        success: false,
        error: "E-mail e código são obrigatórios",
      });
    }

    // Buscar código de verificação mais recente para o email
    const verificationCode = await VerificationCode.findOne({
      email: email.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
    }).sort({ createdAt: -1 });

    if (!verificationCode) {
      return res.status(401).json({
        success: false,
        error: "Código inválido ou expirado",
      });
    }

    // Verificar limite de tentativas (máximo 3)
    if (verificationCode.attempts >= 3) {
      return res.status(429).json({
        success: false,
        error: "Limite de tentativas excedido. Solicite um novo código.",
      });
    }

    // Verificar se o código está correto
    if (verificationCode.code !== code) {
      // Incrementar tentativas
      verificationCode.attempts += 1;
      await verificationCode.save();

      const remainingAttempts = 3 - verificationCode.attempts;
      return res.status(401).json({
        success: false,
        error: `Código inválido. ${remainingAttempts > 0 ? `Restam ${remainingAttempts} tentativa(s).` : 'Limite de tentativas excedido.'}`,
      });
    }

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    // Buscar usuário
    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      return res.status(404).json({
        success: false,
        error: "Usuário não encontrado",
      });
    }

    // Se trustDevice for true, adicionar dispositivo aos confiáveis
    if (trustDevice === true) {
      const TrustedDevice = (await import("../database/models/TrustedDevice.js")).default;
      const deviceId = TrustedDevice.generateDeviceId(
        req.headers["user-agent"],
        getClientIP(req)
      );

      // Verificar se já existe
      let trustedDevice = await TrustedDevice.findTrustedDevice(user._id, deviceId);

      if (!trustedDevice) {
        // Gerar nome do dispositivo baseado no userAgent
        const userAgent = req.headers["user-agent"] || "Dispositivo desconhecido";
        let deviceName = "Dispositivo desconhecido";

        if (userAgent.includes("Chrome")) {
          deviceName = "Chrome";
        } else if (userAgent.includes("Firefox")) {
          deviceName = "Firefox";
        } else if (userAgent.includes("Safari")) {
          deviceName = "Safari";
        } else if (userAgent.includes("Edge")) {
          deviceName = "Edge";
        }

        // Adicionar informações do sistema operacional
        if (userAgent.includes("Windows")) {
          deviceName += " no Windows";
        } else if (userAgent.includes("Mac")) {
          deviceName += " no macOS";
        } else if (userAgent.includes("Linux")) {
          deviceName += " no Linux";
        } else if (userAgent.includes("Android")) {
          deviceName += " no Android";
        } else if (userAgent.includes("iPhone") || userAgent.includes("iPad")) {
          deviceName += " no iOS";
        }

        // Criar dispositivo confiável
        trustedDevice = await TrustedDevice.create({
          userId: user._id,
          deviceId,
          deviceName,
          userAgent: req.headers["user-agent"],
          ip: getClientIP(req),
        });
      } else {
        // Atualizar último uso
        await trustedDevice.updateLastUsed();
      }
    }

    // Atualizar último login e IP
    user.lastLogin = new Date();
    user.addIpToHistory(getClientIP(req));
    await user.save();

    // Gerar token JWT
    const token = generateToken(user._id);

    // Criar sessão
    try {
      const Session = (await import("../database/models/Session.js")).default;
      const userAgent = req.headers["user-agent"] || "Unknown";
      let deviceName = "Dispositivo desconhecido";

      if (userAgent.includes("Chrome")) {
        deviceName = "Chrome";
      } else if (userAgent.includes("Firefox")) {
        deviceName = "Firefox";
      } else if (userAgent.includes("Safari")) {
        deviceName = "Safari";
      } else if (userAgent.includes("Edge")) {
        deviceName = "Edge";
      }

      if (userAgent.includes("Windows")) {
        deviceName += " no Windows";
      } else if (userAgent.includes("Mac")) {
        deviceName += " no macOS";
      } else if (userAgent.includes("Linux")) {
        deviceName += " no Linux";
      } else if (userAgent.includes("Android")) {
        deviceName += " no Android";
      } else if (userAgent.includes("iPhone") || userAgent.includes("iPad")) {
        deviceName += " no iOS";
      }

      await Session.createFromToken(token, user._id, {
        userAgent,
        ip: getClientIP(req),
        deviceName,
      });
    } catch (sessionError) {
      console.error("[AUTH] Erro ao criar sessão:", sessionError);
      // Continuar mesmo se falhar ao criar sessão
    }

    // Remover senha da resposta
    const userResponse = user.toObject();
    delete userResponse.password;

    // Cookie setting removed as per permanent session requirement

    res.json({
      success: true,
      message: "Login realizado com sucesso",
      token,
      user: userResponse,
      deviceTrusted: trustDevice === true,
    });
  } catch (error) {
    console.error("[AUTH] Erro ao verificar código:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar verificação",
    });
  }
});

// ========================= VERIFICAR AUTENTICAÇÃO =========================
// Somente dashboard (validação por origem via CORS)
router.get("/me", validateCorsOrigin, cors(corsOptions), authenticate, async (req, res) => {
  try {
    // Buscar Register correspondente para obter taxID e configurações
    let taxID = null;
    let register = null;
    try {
      const Register = (await import("../database/models/Register.js")).default;
      register = await Register.findOne({
        email: req.user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        taxID = register.taxID;
      }
    } catch (registerError) {
      // Se não encontrar Register, continuar sem taxID
      console.log("[AUTH] Register não encontrado para o usuário");
    }

    const userResponse = req.user.toObject();
    if (taxID) {
      userResponse.taxID = taxID;
    }

    // Adicionar campos de configuração (priorizando Register se existir)
    if (register) {
      userResponse.aiEnabled = register.aiEnabled !== undefined ? register.aiEnabled : true;
      userResponse.transferSecurityEnabled = register.transferSecurityEnabled || false;
      // Sync fields from Register to User response
      userResponse.category = register.category || 'WHITE';
      userResponse.tier = register.tier || 1;
      userResponse.categoryLockedByAdmin = register.categoryLockedByAdmin || false;
      userResponse.businessProfileCompleted = register.businessProfileCompleted || false;
    } else {
      // Defaults se não tiver Register
      userResponse.aiEnabled = true;
      userResponse.transferSecurityEnabled = false;
      userResponse.category = 'WHITE';
      userResponse.tier = 1;
      userResponse.categoryLockedByAdmin = false;
      userResponse.businessProfileCompleted = false;
    }

    res.json({
      success: true,
      user: userResponse,
    });
  } catch (error) {
    console.error("[AUTH] Erro ao buscar usuário:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao buscar informações do usuário",
    });
  }
});

// ========================= LOGOUT =========================
router.post("/logout", authenticate, async (req, res) => {
  try {
    // Revogar sessão se existir
    try {
      const Session = (await import("../database/models/Session.js")).default;
      const token = req.cookies?.token || req.headers.authorization?.replace("Bearer ", "");
      if (token) {
        const session = await Session.findByToken(token);
        if (session) {
          session.revoked = true;
          session.revokedAt = new Date();
          await session.save();
        }
      }
    } catch (sessionError) {
      // Continuar mesmo se não conseguir revogar sessão
      console.warn("[AUTH] Erro ao revogar sessão no logout:", sessionError.message);
    }

    // Limpar cookie com as mesmas opções de segurança
    const cookieOptions = {
      httpOnly: securityConfig.cookies.httpOnly,
      secure: securityConfig.cookies.secure,
      sameSite: securityConfig.cookies.sameSite,
      path: securityConfig.cookies.path,
    };

    const domain = securityConfig.cookies.domain;
    if (domain && typeof domain === 'string' && domain.trim() !== '') {
      cookieOptions.domain = domain.trim();
    }

    res.clearCookie("token", cookieOptions);
    res.json({
      success: true,
      message: "Logout realizado com sucesso",
    });
  } catch (error) {
    console.error("[AUTH] Erro no logout:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao fazer logout",
    });
  }
});

export default router;