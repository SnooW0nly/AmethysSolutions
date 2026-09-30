import User from "../database/models/User.js";

export default async function requireAdmin(req, res, next) {
  try {
    // Verifica se o token enviado corresponde ao ADMIN_JWT do .env
    const authHeader = req.headers.authorization || "";
    const token = authHeader.replace("Bearer ", "");

    if (process.env.ADMIN_JWT && token === process.env.ADMIN_JWT) {
      console.log(`[REQUIRE ADMIN] Acesso autorizado via ADMIN_JWT global`);
      return next(); // token mestre aceito, pula validação no banco
    }

    // Caso contrário, segue a lógica normal com usuário do banco
    const userId = req.user?._id;
    if (!userId) {
      console.warn(`[REQUIRE ADMIN] Acesso negado - Usuário não autenticado`);
      return res.status(401).json({ error: "Não autenticado" });
    }

    const user = await User.findById(userId).select("admin email").lean();
    if (!user) {
      console.warn(`[REQUIRE ADMIN] Acesso negado - Usuário não encontrado: ${userId}`);
      return res.status(401).json({ error: "Usuário não encontrado" });
    }

    if (!user.admin) {
      console.warn(`[REQUIRE ADMIN] Acesso negado - Usuário sem permissão de admin: ${user.email}`);
      return res.status(403).json({ error: "Acesso negado" });
    }

    console.log(`[REQUIRE ADMIN] Acesso autorizado - Admin: ${user.email}`);
    next();
  } catch (err) {
    console.error(`[REQUIRE ADMIN] Erro ao verificar permissões:`, err);
    return res.status(500).json({ error: "Erro de autorização" });
  }
}
