import express from "express";
import { sendVerificationCode, verifyCode } from "../../services/emailVerification.js";
import { generateToken } from "../../database/auth.js";

const router = express.Router();

/**
 * POST /auth/email/send-code
 * Envia código de verificação para o email
 */
router.post("/send-code", async (req, res) => {
  try {
    const { email } = req.body;

    // Validação
    if (!email) {
      return res.status(400).json({
        success: false,
        message: "Email é obrigatório",
      });
    }

    // Valida formato do email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({
        success: false,
        message: "Email inválido",
      });
    }

    // Obtém IP e User-Agent
    const ip = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers["user-agent"];

    // Envia código
    const result = await sendVerificationCode(email, ip, userAgent);

    return res.status(result.success ? 200 : 400).json(result);
  } catch (error) {
    console.error("[EMAIL LOGIN] Erro ao enviar código:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao enviar código de verificação",
    });
  }
});

/**
 * POST /auth/email/verify-code
 * Verifica código e faz login
 */
router.post("/verify-code", async (req, res) => {
  try {
    const { email, code } = req.body;

    // Validação
    if (!email || !code) {
      return res.status(400).json({
        success: false,
        message: "Email e código são obrigatórios",
      });
    }

    // Valida formato do código (6 dígitos)
    if (!/^\d{6}$/.test(code)) {
      return res.status(400).json({
        success: false,
        message: "Código inválido",
      });
    }

    // Verifica código
    const result = await verifyCode(email, code);

    if (!result.success) {
      return res.status(400).json(result);
    }

    // Gera token JWT (inclui tokenVersion e método de login)
    const token = generateToken({
      id: result.user._id.toString(),
      email: result.user.email,
      tokenVersion: result.user.tokenVersion ?? 0,
      loginMethod: 'email',
    });

    // Define cookie
    const isProduction = process.env.NODE_ENV === "production";
    res.cookie("token", token, {
      httpOnly: true,
      secure: isProduction,
      sameSite: "strict",
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 dias
      domain: process.env.COOKIE_DOMAIN,
    });

    console.log(`[EMAIL LOGIN] Login bem-sucedido para ${email}`);

    return res.status(200).json({
      success: true,
      message: "Login realizado com sucesso",
      user: {
        id: result.user._id,
        email: result.user.email,
        discordId: result.user.discordId,
        username: result.user.username,
        avatar: result.user.avatar,
      },
    });
  } catch (error) {
    console.error("[EMAIL LOGIN] Erro ao verificar código:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao verificar código",
    });
  }
});

export default router;
