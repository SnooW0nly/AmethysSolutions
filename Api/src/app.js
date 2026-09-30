import "./config/env.js"; 

import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";

import dbConnect from "./database/db.js";
import routes from "./routes/index.js";
import errorHandler from "./middlewares/errorHandler.js";
import corsOptions, { corsLogger } from "./config/cors.js";
import { validateEnvironment, securityConfig } from "./config/security.js";
import securityHeaders, { suspiciousActivityLogger } from "./middlewares/securityHeaders.js";
import { apiRateLimiter } from "./middlewares/rateLimiter.js";
import { 
  ipBlockMiddleware, 
  maintenanceMiddleware, 
  cacheMiddleware, 
  dynamicRateLimiter,
  setupDefenseRoutes 
} from "./middlewares/defense.js";
import { startAIMonitor } from "./services/aiMonitorService.js";

// ========================= SECURITY CONFIGURATION =========================
validateEnvironment();

// ========================= DATABASE CONNECTION =========================
await dbConnect();
// startAIMonitor();

const app = express();

// ========================= DEFENSE SYSTEM =========================
app.use(ipBlockMiddleware);
app.use(maintenanceMiddleware);
app.use(cacheMiddleware);
app.use(dynamicRateLimiter);

// ========================= SECURITY HEADERS =========================
app.use(securityHeaders);

// ========================= SUSPICIOUS ACTIVITY LOGGER =========================
app.use(suspiciousActivityLogger);

// ========================= BODY PARSERS =========================
app.use(express.json({ limit: securityConfig.validation.maxBodySize }));
app.use(express.urlencoded({ 
  extended: true, 
  limit: securityConfig.validation.maxBodySize 
}));

// ========================= COOKIES =========================
app.use(cookieParser());

// ========================= CORS =========================
app.use(corsLogger);
app.use(cors(corsOptions));

// ========================= RATE LIMITING (GLOBAL) =========================
app.use(apiRateLimiter);

// ========================= REQUEST LOGGER =========================
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  if (req.method === "GET" && req.originalUrl === "/bot/bio") return next();
  console.log(`[${timestamp}] ${req.method} ${req.originalUrl}`);
  next();
});

// ========================= DEFENSE ROUTES =========================
setupDefenseRoutes(app);

// ========================= ROUTES =========================
app.use("/", routes);
app.use("/api", routes); 

// ========================= 404 HANDLER =========================
app.use((req, res, next) => {
  console.warn(`[404] Rota não encontrada: ${req.method} ${req.originalUrl}`);
  res.status(404).json({ 
    success: false,
    error: "Rota não encontrada",
    path: req.originalUrl 
  });
});

// ========================= ERROR HANDLER =========================
app.use(errorHandler);

export default app;