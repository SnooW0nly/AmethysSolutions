export default (err, req, res, next) => {
  const status = err.status || 500;
  const message = err?.message || "Erro interno no servidor";
  
  // Log detalhado do erro
  console.error("=".repeat(80));
  console.error(`[ERROR HANDLER] Erro capturado - Status: ${status}`);
  console.error(`[ERROR HANDLER] Rota: ${req.method} ${req.originalUrl}`);
  console.error(`[ERROR HANDLER] Mensagem: ${message}`);
  console.error(`[ERROR HANDLER] Stack:`, err.stack);
  console.error(`[ERROR HANDLER] Body:`, req.body);
  console.error(`[ERROR HANDLER] Query:`, req.query);
  console.error(`[ERROR HANDLER] Params:`, req.params);
  console.error("=".repeat(80));
  
  res.status(status).json({ 
    success: false,
    error: message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
};