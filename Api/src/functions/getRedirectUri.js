export default function getRedirectUri(req) {
  // 1. Se a variável de ambiente estiver definida, use-a (recomendado para produção)
  const explicit = process.env.DISCORD_REDIRECT_URI;
  if (explicit) return explicit;

  // 2. Se não, tenta construir a partir da FRONTEND_URL (útil para desenvolvimento)
  const frontendBase = process.env.FRONTEND_URL;
  if (frontendBase) return `${frontendBase}/api/auth/callback`;

  // 3. Fallback: constrói dinamicamente a partir dos headers da requisição
  const protocol = req.headers["x-forwarded-proto"] || (req.secure ? "https" : "http");
  const host = req.headers["x-forwarded-host"] || req.headers.host;
  return `${protocol}://${host}/auth/callback`;
}
