export default (err, req, res, next) => {
  const status = err.status || 500;
  const message = err?.message || "Erro interno no servidor";

  // Sanitize error message - don't expose internal details in production
  const isProduction = process.env.NODE_ENV === 'production';
  const safeMessage = isProduction && status === 500
    ? 'Erro interno no servidor'
    : message;

  // Log detalhado do erro (sem dados sensíveis)
  console.error("=".repeat(80));
  console.error(`[ERROR HANDLER] Erro capturado - Status: ${status}`);
  console.error(`[ERROR HANDLER] Rota: ${req.method} ${req.originalUrl?.split('?')[0]}`);
  console.error(`[ERROR HANDLER] Mensagem: ${message}`);

  // Em desenvolvimento, mostra mais detalhes (mas nunca o body completo - pode ter senhas)
  if (!isProduction) {
    console.error(`[ERROR HANDLER] Stack:`, err.stack);
    // Mostra apenas chaves do body, não os valores (para debug sem expor dados)
    if (req.body && typeof req.body === 'object') {
      console.error(`[ERROR HANDLER] Body keys:`, Object.keys(req.body));
    }
  }
  console.error("=".repeat(80));

  res.status(status).json({
    success: false,
    error: safeMessage,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
};

