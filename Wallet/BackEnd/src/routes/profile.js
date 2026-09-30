import express from "express";
import User from "../database/models/User.js";
import VerificationCode from "../database/models/VerificationCode.js";
import { authenticate } from "../middlewares/auth.js";
import { generateVerificationCode, sendVerificationCode } from "../services/emailService.js";
import { validatePassword } from "../utils/passwordValidator.js";
import rateLimit from "express-rate-limit";
import multer from "multer";
import path from "path";
import fs from "fs";
import { getClientIP } from "../utils/getClientIP.js";

const router = express.Router();

// Rate limiting para atualizações
const updateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutos
  max: 10, // 10 tentativas por IP
  message: {
    success: false,
    error: "Muitas tentativas. Tente novamente em 15 minutos.",
  },
  // Usar função customizada para obter IP ao invés de confiar no trust proxy
  keyGenerator: (req) => {
    return getClientIP(req);
  }
});

// Configuração do multer para upload de avatar
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadPath = path.join(process.cwd(), 'database', 'uploads', 'avatars');
    if (!fs.existsSync(uploadPath)) {
      fs.mkdirSync(uploadPath, { recursive: true });
    }
    cb(null, uploadPath);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, `avatar-${req.user._id}-${uniqueSuffix}${path.extname(file.originalname)}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
  fileFilter: (req, file, cb) => {
    const allowedTypes = /jpeg|jpg|png|gif|webp/;
    const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
    const mimetype = allowedTypes.test(file.mimetype);

    if (mimetype && extname) {
      return cb(null, true);
    } else {
      cb(new Error('Apenas imagens são permitidas (JPEG, PNG, GIF, WEBP)'));
    }
  }
});

// ========================= ATUALIZAR TELEFONE =========================
router.put("/phone", authenticate, updateLimiter, async (req, res) => {
  try {
    const { phone } = req.body;
    const user = req.user;

    if (!phone) {
      return res.status(400).json({
        success: false,
        error: "Telefone é obrigatório",
      });
    }

    user.phone = phone;
    await user.save();

    const userResponse = user.toObject();
    delete userResponse.password;

    res.json({
      success: true,
      message: "Telefone atualizado com sucesso",
      user: userResponse,
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao atualizar telefone:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao atualizar telefone",
    });
  }
});

// ========================= ATUALIZAR DATA DE NASCIMENTO =========================
router.put("/birthdate", authenticate, updateLimiter, async (req, res) => {
  try {
    const { birthDate } = req.body;
    const user = req.user;

    if (!birthDate) {
      return res.status(400).json({
        success: false,
        error: "Data de nascimento é obrigatória",
      });
    }

    user.birthDate = new Date(birthDate);
    await user.save();

    const userResponse = user.toObject();
    delete userResponse.password;

    res.json({
      success: true,
      message: "Data de nascimento atualizada com sucesso",
      user: userResponse,
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao atualizar data de nascimento:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao atualizar data de nascimento",
    });
  }
});

// ========================= SOLICITAR CÓDIGO PARA ALTERAR EMAIL =========================
router.post("/email/request-code", authenticate, updateLimiter, async (req, res) => {
  try {
    const { newEmail } = req.body;
    const user = req.user;

    if (!newEmail) {
      return res.status(400).json({
        success: false,
        error: "Novo e-mail é obrigatório",
      });
    }

    // Verificar se o novo email já está em uso
    const existingUser = await User.findOne({ email: newEmail.toLowerCase() });
    if (existingUser && existingUser._id.toString() !== user._id.toString()) {
      return res.status(400).json({
        success: false,
        error: "Este e-mail já está em uso",
      });
    }

    // Gerar código de verificação
    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10);

    // Salvar código no banco
    await VerificationCode.create({
      email: newEmail.toLowerCase(),
      code,
      expiresAt,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
      type: 'email-change', // Tipo especial para mudança de email
    });

    // Enviar código por e-mail
    const emailSent = await sendVerificationCode(newEmail.toLowerCase(), code);

    if (!emailSent) {
      console.error(`[PROFILE] Falha ao enviar código para ${newEmail}`);
    }

    res.json({
      success: true,
      message: "Código de verificação enviado para o novo e-mail",
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao solicitar código:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar solicitação",
    });
  }
});

// ========================= VERIFICAR CÓDIGO E ALTERAR EMAIL =========================
router.put("/email/verify-code", authenticate, updateLimiter, async (req, res) => {
  try {
    const { newEmail, code } = req.body;
    const user = req.user;

    if (!newEmail || !code) {
      return res.status(400).json({
        success: false,
        error: "Novo e-mail e código são obrigatórios",
      });
    }

    // Buscar código de verificação
    const verificationCode = await VerificationCode.findOne({
      email: newEmail.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
      type: 'email-change',
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

    // Verificar se o novo email já está em uso
    const existingUser = await User.findOne({ email: newEmail.toLowerCase() });
    if (existingUser && existingUser._id.toString() !== user._id.toString()) {
      return res.status(400).json({
        success: false,
        error: "Este e-mail já está em uso",
      });
    }

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    // Atualizar email
    user.email = newEmail.toLowerCase();
    await user.save();

    const userResponse = user.toObject();
    delete userResponse.password;

    res.json({
      success: true,
      message: "E-mail atualizado com sucesso",
      user: userResponse,
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao atualizar e-mail:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao atualizar e-mail",
    });
  }
});

// ========================= ATUALIZAR NOME =========================
router.put("/name", authenticate, updateLimiter, async (req, res) => {
  try {
    const { fullName } = req.body;
    const user = req.user;

    if (!fullName || fullName.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: "Nome completo é obrigatório",
      });
    }

    user.fullName = fullName.trim();
    await user.save();

    const userResponse = user.toObject();
    delete userResponse.password;

    res.json({
      success: true,
      message: "Nome atualizado com sucesso",
      user: userResponse,
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao atualizar nome:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao atualizar nome",
    });
  }
});

// ========================= ATUALIZAR AVATAR =========================
router.put("/avatar", authenticate, upload.single('avatar'), updateLimiter, async (req, res) => {
  try {
    const user = req.user;

    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: "Arquivo de imagem é obrigatório",
      });
    }

    // Remover avatar antigo se existir
    if (user.avatar) {
      const oldAvatarPath = path.join(process.cwd(), 'database', 'uploads', 'avatars', path.basename(user.avatar));
      if (fs.existsSync(oldAvatarPath)) {
        fs.unlinkSync(oldAvatarPath);
      }
    }

    // Salvar caminho do novo avatar
    user.avatar = `/uploads/avatars/${req.file.filename}`;
    await user.save();

    const userResponse = user.toObject();
    delete userResponse.password;

    res.json({
      success: true,
      message: "Avatar atualizado com sucesso",
      user: userResponse,
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao atualizar avatar:", error);
    res.status(500).json({
      success: false,
      error: error.message || "Erro ao atualizar avatar",
    });
  }
});

// ========================= SOLICITAR CÓDIGO PARA ALTERAR SENHA =========================
router.post("/password/request-code", authenticate, updateLimiter, async (req, res) => {
  try {
    const { oldPassword, forgotPassword } = req.body;
    const user = req.user;

    // Se não esqueceu a senha, verificar senha antiga
    if (!forgotPassword) {
      if (!oldPassword) {
        return res.status(400).json({
          success: false,
          error: "Senha antiga é obrigatória",
        });
      }

      const isPasswordValid = await user.comparePassword(oldPassword);
      if (!isPasswordValid) {
        return res.status(401).json({
          success: false,
          error: "Senha antiga incorreta",
        });
      }
    }

    // Gerar código de verificação
    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10);

    // Salvar código no banco
    await VerificationCode.create({
      email: user.email.toLowerCase(),
      code,
      expiresAt,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
      type: 'password-change',
    });

    // Enviar código por e-mail
    const emailSent = await sendVerificationCode(user.email.toLowerCase(), code);

    if (!emailSent) {
      console.error(`[PROFILE] Falha ao enviar código para ${user.email}`);
    }

    res.json({
      success: true,
      message: "Código de verificação enviado para seu e-mail",
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao solicitar código:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao processar solicitação",
    });
  }
});

// ========================= VERIFICAR CÓDIGO E ALTERAR SENHA =========================
router.put("/password/verify-code", authenticate, updateLimiter, async (req, res) => {
  try {
    const { newPassword, code } = req.body;
    const user = req.user;

    if (!newPassword || !code) {
      return res.status(400).json({
        success: false,
        error: "Nova senha e código são obrigatórios",
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
      email: user.email.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
      type: 'password-change',
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

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    // Atualizar senha
    user.password = newPassword;
    await user.save();

    const userResponse = user.toObject();
    delete userResponse.password;

    res.json({
      success: true,
      message: "Senha atualizada com sucesso",
      user: userResponse,
    });
  } catch (error) {
    console.error("[PROFILE] Erro ao atualizar senha:", error);
    res.status(500).json({
      success: false,
      error: "Erro ao atualizar senha",
    });
  }
});

export default router;

