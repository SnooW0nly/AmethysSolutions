package http

import (
	"amethys-api/database"
	"amethys-api/services"
	"fmt"
	"net/http"
	"time"

	"github.com/gorilla/mux"
)

// HandleGiftPage — rota GET /gifts/:giftId (alinhada com a versão JS)
func HandleGiftPage(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	giftID := vars["giftId"]
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}

	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	gift, err := database.DB.FindGiftByID(giftID)
	if err != nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprint(w, giftNotFoundPage())
		return
	}

	if gift.Status != "active" {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, giftInactivePage())
		return
	}

	createdAt := gift.CreatedAt.Format("02/01/2006")
	if gift.CreatedAt.IsZero() {
		createdAt = time.Now().Format("02/01/2006")
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, giftActivePage(gift, createdAt))
}

func giftNotFoundPage() string {
	return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Gift Não Encontrado — Amethyst Applications</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #a855f7;
      --primary-light: #c084fc;
      --primary-glow: rgba(168, 85, 247, 0.25);
      --danger: #ef4444;
      --danger-dim: rgba(239, 68, 68, 0.1);
      --bg: #000000;
      --surface: rgba(255, 255, 255, 0.02);
      --border: rgba(255, 255, 255, 0.06);
      --text: #fafafa;
      --text-secondary: #a1a1aa;
      --text-muted: #71717a;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Grid Background */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      z-index: 0;
      background-image: 
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
      background-size: 64px 64px;
      pointer-events: none;
    }

    /* Red Glow for Error */
    body::after {
      content: '';
      position: fixed;
      top: -50%;
      left: 50%;
      transform: translateX(-50%);
      width: 100%;
      height: 100%;
      z-index: 0;
      background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(239, 68, 68, 0.06), transparent 60%);
      pointer-events: none;
    }

    /* Header */
    header {
      position: relative;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 48px;
      border-bottom: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(20px);
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 24px var(--primary-glow);
    }

    .logo-icon svg {
      width: 20px;
      height: 20px;
      color: white;
    }

    .logo-text {
      font-weight: 700;
      font-size: 18px;
      color: var(--text);
      letter-spacing: -0.02em;
    }

    .header-badge {
      font-size: 12px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 24px;
      letter-spacing: 0.02em;
    }

    /* Main */
    main {
      position: relative;
      z-index: 1;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 80px 24px;
    }

    .container {
      max-width: 600px;
      width: 100%;
      text-align: center;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--danger-dim);
      border: 1px solid rgba(239, 68, 68, 0.2);
      padding: 8px 18px;
      border-radius: 32px;
      margin-bottom: 32px;
      font-size: 13px;
      color: var(--danger);
      font-weight: 500;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--danger);
    }

    .error-code {
      font-size: 120px;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.04em;
      background: linear-gradient(180deg, rgba(239, 68, 68, 0.5), rgba(239, 68, 68, 0.1));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 16px;
      user-select: none;
    }

    h1 {
      font-size: 36px;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.1;
      margin-bottom: 16px;
    }

    .desc {
      font-size: 17px;
      color: var(--text-secondary);
      line-height: 1.7;
      max-width: 440px;
      margin: 0 auto 48px;
    }

    .divider {
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--border), transparent);
      margin: 0 auto 48px;
      max-width: 400px;
    }

    .info-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      display: flex;
      align-items: flex-start;
      gap: 16px;
      text-align: left;
    }

    .info-icon {
      width: 44px;
      height: 44px;
      background: rgba(168, 85, 247, 0.1);
      border: 1px solid rgba(168, 85, 247, 0.2);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .info-icon svg {
      width: 20px;
      height: 20px;
      color: var(--primary-light);
    }

    .info-content {
      flex: 1;
    }

    .info-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 6px;
    }

    .info-text {
      font-size: 14px;
      color: var(--text-secondary);
      line-height: 1.6;
    }

    /* Footer */
    footer {
      position: relative;
      z-index: 1;
      border-top: 1px solid var(--border);
      padding: 24px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(12px);
    }

    .footer-brand {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .footer-logo {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-muted);
    }

    .footer-logo span {
      color: var(--primary-light);
    }

    .footer-copy {
      font-size: 13px;
      color: var(--text-muted);
    }

    .footer-links {
      display: flex;
      gap: 24px;
    }

    .footer-links a {
      font-size: 13px;
      color: var(--text-muted);
      text-decoration: none;
    }

    .footer-links a:hover {
      color: var(--text-secondary);
    }

    @media (max-width: 768px) {
      header { padding: 16px 20px; }
      main { padding: 48px 16px; }
      .error-code { font-size: 80px; }
      h1 { font-size: 28px; }
      footer { flex-direction: column; gap: 16px; text-align: center; padding: 20px; }
      .footer-brand { flex-direction: column; gap: 8px; }
    }
  </style>
</head>
<body>
  <header>
    <a class="logo" href="#">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
          <line x1="12" y1="22" x2="12" y2="15.5"/>
          <polyline points="22 8.5 12 15.5 2 8.5"/>
        </svg>
      </div>
      <span class="logo-text">Amethyst</span>
    </a>
    <span class="header-badge">Gift System</span>
  </header>

  <main>
    <div class="container">
      <div class="status-badge">
        <span class="status-dot"></span>
        Erro 404
      </div>
      <div class="error-code">404</div>
      <h1>Gift Não Encontrado</h1>
      <p class="desc">O gift que você está procurando não existe na nossa base de dados ou pode ter sido removido pelo administrador.</p>
      <div class="divider"></div>
      <div class="info-card">
        <div class="info-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <div class="info-content">
          <div class="info-title">O que fazer?</div>
          <p class="info-text">Verifique se o link está correto e tente novamente. Se o problema persistir, entre em contato com quem enviou o gift.</p>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div class="footer-brand">
      <span class="footer-logo"><span>Amethyst</span> Applications</span>
      <span class="footer-copy">© 2025 Todos os direitos reservados</span>
    </div>
    <div class="footer-links">
      <a href="https://amethysapplications.com" target="_blank">Site</a>
      <a href="#" target="_blank">Termos</a>
      <a href="#" target="_blank">Suporte</a>
    </div>
  </footer>
</body>
</html>`
}

func giftInactivePage() string {
	return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Gift Inativo — Amethyst Applications</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #a855f7;
      --primary-light: #c084fc;
      --primary-glow: rgba(168, 85, 247, 0.25);
      --warn: #f59e0b;
      --warn-dim: rgba(245, 158, 11, 0.1);
      --bg: #000000;
      --surface: rgba(255, 255, 255, 0.02);
      --border: rgba(255, 255, 255, 0.06);
      --text: #fafafa;
      --text-secondary: #a1a1aa;
      --text-muted: #71717a;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    body::before {
      content: '';
      position: fixed;
      inset: 0;
      z-index: 0;
      background-image: 
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
      background-size: 64px 64px;
      pointer-events: none;
    }

    body::after {
      content: '';
      position: fixed;
      top: -50%;
      left: 50%;
      transform: translateX(-50%);
      width: 100%;
      height: 100%;
      z-index: 0;
      background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(245, 158, 11, 0.05), transparent 60%);
      pointer-events: none;
    }

    header {
      position: relative;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 48px;
      border-bottom: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(20px);
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 24px var(--primary-glow);
    }

    .logo-icon svg {
      width: 20px;
      height: 20px;
      color: white;
    }

    .logo-text {
      font-weight: 700;
      font-size: 18px;
      color: var(--text);
      letter-spacing: -0.02em;
    }

    .header-badge {
      font-size: 12px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 24px;
    }

    main {
      position: relative;
      z-index: 1;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 80px 24px;
    }

    .container {
      max-width: 600px;
      width: 100%;
      text-align: center;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--warn-dim);
      border: 1px solid rgba(245, 158, 11, 0.2);
      padding: 8px 18px;
      border-radius: 32px;
      margin-bottom: 32px;
      font-size: 13px;
      color: var(--warn);
      font-weight: 500;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--warn);
    }

    .icon-wrap {
      width: 96px;
      height: 96px;
      margin: 0 auto 32px;
      background: var(--warn-dim);
      border: 1px solid rgba(245, 158, 11, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .icon-wrap svg {
      width: 44px;
      height: 44px;
      color: var(--warn);
    }

    h1 {
      font-size: 40px;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.1;
      margin-bottom: 16px;
    }

    .desc {
      font-size: 17px;
      color: var(--text-secondary);
      line-height: 1.7;
      max-width: 440px;
      margin: 0 auto 48px;
    }

    .divider {
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--border), transparent);
      margin: 0 auto 48px;
      max-width: 400px;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }

    .info-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      text-align: left;
    }

    .info-label {
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 8px;
    }

    .info-value {
      font-size: 16px;
      font-weight: 600;
      color: var(--text);
    }

    .info-value.warn {
      color: var(--warn);
    }

    footer {
      position: relative;
      z-index: 1;
      border-top: 1px solid var(--border);
      padding: 24px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(12px);
    }

    .footer-brand {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .footer-logo {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-muted);
    }

    .footer-logo span {
      color: var(--primary-light);
    }

    .footer-copy {
      font-size: 13px;
      color: var(--text-muted);
    }

    .footer-links {
      display: flex;
      gap: 24px;
    }

    .footer-links a {
      font-size: 13px;
      color: var(--text-muted);
      text-decoration: none;
    }

    @media (max-width: 768px) {
      header { padding: 16px 20px; }
      main { padding: 48px 16px; }
      h1 { font-size: 30px; }
      .info-grid { grid-template-columns: 1fr; }
      footer { flex-direction: column; gap: 16px; text-align: center; padding: 20px; }
      .footer-brand { flex-direction: column; gap: 8px; }
    }
  </style>
</head>
<body>
  <header>
    <a class="logo" href="#">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
          <line x1="12" y1="22" x2="12" y2="15.5"/>
          <polyline points="22 8.5 12 15.5 2 8.5"/>
        </svg>
      </div>
      <span class="logo-text">Amethyst</span>
    </a>
    <span class="header-badge">Gift System</span>
  </header>

  <main>
    <div class="container">
      <div class="status-badge">
        <span class="status-dot"></span>
        Indisponível
      </div>
      <div class="icon-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="10" y1="15" x2="10" y2="9"/>
          <line x1="14" y1="15" x2="14" y2="9"/>
        </svg>
      </div>
      <h1>Gift Inativo</h1>
      <p class="desc">Este gift foi desativado pelo administrador e não está mais disponível para resgate no momento.</p>
      <div class="divider"></div>
      <div class="info-grid">
        <div class="info-card">
          <div class="info-label">Status</div>
          <div class="info-value warn">Desativado</div>
        </div>
        <div class="info-card">
          <div class="info-label">O que fazer?</div>
          <div class="info-value">Contate o suporte</div>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div class="footer-brand">
      <span class="footer-logo"><span>Amethyst</span> Applications</span>
      <span class="footer-copy">© 2025 Todos os direitos reservados</span>
    </div>
    <div class="footer-links">
      <a href="https://amethysapplications.com" target="_blank">Site</a>
      <a href="#" target="_blank">Termos</a>
      <a href="#" target="_blank">Suporte</a>
    </div>
  </footer>
</body>
</html>`
}

func giftActivePage(gift *database.Gift, createdAt string) string {
	return fmt.Sprintf(`<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Resgatar Gift — Amethyst Applications</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #a855f7;
      --primary-light: #c084fc;
      --primary-dark: #9333ea;
      --primary-glow: rgba(168, 85, 247, 0.25);
      --success: #22c55e;
      --success-dim: rgba(34, 197, 94, 0.1);
      --danger: #ef4444;
      --danger-dim: rgba(239, 68, 68, 0.1);
      --bg: #000000;
      --surface: rgba(255, 255, 255, 0.02);
      --surface-hover: rgba(255, 255, 255, 0.04);
      --border: rgba(255, 255, 255, 0.06);
      --border-light: rgba(255, 255, 255, 0.1);
      --text: #fafafa;
      --text-secondary: #a1a1aa;
      --text-muted: #71717a;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%%; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Grid Background */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      z-index: 0;
      background-image: 
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
      background-size: 64px 64px;
      pointer-events: none;
    }

    /* Purple Glow */
    body::after {
      content: '';
      position: fixed;
      top: -50%%;
      left: 50%%;
      transform: translateX(-50%%);
      width: 100%%;
      height: 100%%;
      z-index: 0;
      background: radial-gradient(ellipse 80%% 50%% at 50%% 0%%, rgba(168, 85, 247, 0.08), transparent 60%%);
      pointer-events: none;
    }

    /* Header */
    header {
      position: relative;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 48px;
      border-bottom: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(20px);
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 24px var(--primary-glow);
    }

    .logo-icon svg {
      width: 20px;
      height: 20px;
      color: white;
    }

    .logo-text {
      font-weight: 700;
      font-size: 18px;
      color: var(--text);
      letter-spacing: -0.02em;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-badge {
      font-size: 12px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 24px;
      letter-spacing: 0.02em;
    }

    .header-status {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--success);
      background: var(--success-dim);
      border: 1px solid rgba(34, 197, 94, 0.2);
      padding: 6px 14px;
      border-radius: 24px;
      font-weight: 500;
    }

    .live-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
    }

    /* Main Content */
    main {
      position: relative;
      z-index: 1;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 60px 24px;
    }

    .container {
      max-width: 720px;
      width: 100%%;
    }

    /* Hero Section */
    .hero {
      text-align: center;
      margin-bottom: 48px;
    }

    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(168, 85, 247, 0.1);
      border: 1px solid rgba(168, 85, 247, 0.2);
      padding: 8px 18px;
      border-radius: 32px;
      margin-bottom: 28px;
      font-size: 13px;
      color: var(--primary-light);
      font-weight: 500;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    .hero-badge svg {
      width: 16px;
      height: 16px;
    }

    h1 {
      font-size: 48px;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.1;
      margin-bottom: 16px;
      background: linear-gradient(135deg, var(--text) 0%%, var(--primary-light) 100%%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .hero-desc {
      font-size: 17px;
      color: var(--text-secondary);
      line-height: 1.7;
      max-width: 520px;
      margin: 0 auto;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 32px;
    }

    .stat {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      text-align: center;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -0.02em;
      margin-bottom: 6px;
    }

    .stat-value.purple {
      color: var(--primary-light);
    }

    .stat-value.green {
      color: var(--success);
    }

    .stat-label {
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    /* Form Panel */
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 32px;
      position: relative;
      overflow: hidden;
    }

    .panel::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--primary), transparent);
    }

    .panel-title {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
    }

    .panel-desc {
      font-size: 15px;
      color: var(--text-secondary);
      margin-bottom: 28px;
      line-height: 1.6;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }

    .input-wrap {
      position: relative;
      margin-bottom: 24px;
    }

    .input-icon {
      position: absolute;
      left: 16px;
      top: 50%%;
      transform: translateY(-50%%);
      color: var(--text-muted);
      pointer-events: none;
    }

    .input-icon svg {
      width: 18px;
      height: 18px;
    }

    input[type="text"] {
      width: 100%%;
      padding: 16px 16px 16px 48px;
      border: 1px solid var(--border);
      border-radius: 14px;
      font-size: 15px;
      background: rgba(0, 0, 0, 0.4);
      color: var(--text);
      font-family: inherit;
      outline: none;
    }

    input[type="text"]:focus {
      border-color: rgba(168, 85, 247, 0.4);
      box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
    }

    input[type="text"]::placeholder {
      color: var(--text-muted);
    }

    /* Buttons */
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 16px 24px;
      border-radius: 14px;
      font-weight: 600;
      font-size: 15px;
      border: none;
      cursor: pointer;
      text-decoration: none;
      letter-spacing: -0.01em;
    }

    .btn svg {
      width: 18px;
      height: 18px;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      color: white;
      box-shadow: 0 8px 32px var(--primary-glow);
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 40px rgba(168, 85, 247, 0.35);
    }

    .btn-outline {
      background: var(--surface-hover);
      color: var(--text);
      border: 1px solid var(--border-light);
    }

    .btn-outline:hover {
      background: rgba(255, 255, 255, 0.06);
      transform: translateY(-2px);
    }

    /* Status Messages */
    .status {
      display: none;
      padding: 16px 20px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 500;
      margin-top: 20px;
      align-items: center;
      gap: 12px;
    }

    .status.show {
      display: flex;
    }

    .st-loading {
      background: rgba(168, 85, 247, 0.1);
      border: 1px solid rgba(168, 85, 247, 0.2);
      color: var(--primary-light);
    }

    .st-error {
      background: var(--danger-dim);
      border: 1px solid rgba(239, 68, 68, 0.2);
      color: var(--danger);
    }

    .st-success {
      background: var(--success-dim);
      border: 1px solid rgba(34, 197, 94, 0.2);
      color: var(--success);
    }

    /* Footer */
    footer {
      position: relative;
      z-index: 1;
      border-top: 1px solid var(--border);
      padding: 24px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(12px);
    }

    .footer-brand {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .footer-logo {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-muted);
    }

    .footer-logo span {
      color: var(--primary-light);
    }

    .footer-copy {
      font-size: 13px;
      color: var(--text-muted);
    }

    .footer-links {
      display: flex;
      gap: 24px;
    }

    .footer-links a {
      font-size: 13px;
      color: var(--text-muted);
      text-decoration: none;
    }

    .footer-links a:hover {
      color: var(--text-secondary);
    }

    @media (max-width: 768px) {
      header { padding: 16px 20px; }
      .header-badge { display: none; }
      main { padding: 32px 16px; }
      h1 { font-size: 32px; }
      .stats-grid { grid-template-columns: 1fr 1fr; }
      .stats-grid .stat:last-child { grid-column: span 2; }
      .panel { padding: 24px; }
      .actions { grid-template-columns: 1fr; }
      footer { flex-direction: column; gap: 16px; text-align: center; padding: 20px; }
      .footer-brand { flex-direction: column; gap: 8px; }
    }
  </style>
</head>
<body>
  <header>
    <a class="logo" href="#">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
          <line x1="12" y1="22" x2="12" y2="15.5"/>
          <polyline points="22 8.5 12 15.5 2 8.5"/>
        </svg>
      </div>
      <span class="logo-text">Amethyst</span>
    </a>
    <div class="header-right">
      <span class="header-badge">Gift System</span>
      <span class="header-status"><span class="live-dot"></span>Ativo</span>
    </div>
  </header>

  <main>
    <div class="container">
      <div class="hero">
        <div class="hero-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 12v10H4V12"/>
            <path d="M2 7h20v5H2z"/>
            <path d="M12 22V7"/>
            <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/>
            <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
          </svg>
          Gift disponível para resgate
        </div>
        <h1>Resgatar Gift</h1>
        <p class="hero-desc">Adicione o bot ao seu servidor Discord e resgate seus membros de forma rápida e segura.</p>
      </div>

      <div class="stats-grid">
        <div class="stat">
          <div class="stat-value purple">%s</div>
          <div class="stat-label">ID do Gift</div>
        </div>
        <div class="stat">
          <div class="stat-value green">%d</div>
          <div class="stat-label">Membros</div>
        </div>
        <div class="stat">
          <div class="stat-value">%s</div>
          <div class="stat-label">Criado em</div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">Informações do Servidor</div>
        <p class="panel-desc">Digite o ID do servidor Discord onde deseja resgatar os membros deste gift.</p>
        <label for="guildId">Guild ID</label>
        <div class="input-wrap">
          <span class="input-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </span>
          <input type="text" id="guildId" placeholder="Ex: 1234567890123456789">
        </div>
        <div class="actions">
          <button class="btn btn-primary" onclick="redeemGift()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Resgatar Gift
          </button>
          <a href="https://discord.com/api/oauth2/authorize?client_id=%s&permissions=8&scope=bot%%20applications.commands" class="btn btn-outline" target="_blank">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
            Adicionar Bot
          </a>
        </div>
        <div class="status st-loading" id="loading">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M21 12a9 9 0 11-6.219-8.56"/>
          </svg>
          Processando resgate...
        </div>
        <div class="status st-error" id="error"></div>
        <div class="status st-success" id="success"></div>
      </div>
    </div>
  </main>

  <footer>
    <div class="footer-brand">
      <span class="footer-logo"><span>Amethyst</span> Applications</span>
      <span class="footer-copy">© 2025 Todos os direitos reservados</span>
    </div>
    <div class="footer-links">
      <a href="https://amethysapplications.com" target="_blank">Site</a>
      <a href="#" target="_blank">Termos</a>
      <a href="#" target="_blank">Suporte</a>
    </div>
  </footer>

  <script>
    async function redeemGift() {
      const guildId = document.getElementById('guildId').value.trim();
      const loading = document.getElementById('loading');
      const error = document.getElementById('error');
      const success = document.getElementById('success');
      const hide = el => el.classList.remove('show');
      const show = el => el.classList.add('show');
      if (!guildId) { error.textContent='Por favor, digite o ID do servidor.'; show(error); return; }
      if (!/^\d+$/.test(guildId)) { error.textContent='Por favor, digite um ID de servidor válido (apenas números).'; show(error); return; }
      show(loading); hide(error); hide(success);
      try {
        const response = await fetch('/api/redeem-gift', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({giftId:'%s',guildId:guildId})
        });
        const result = await response.json();
        hide(loading);
        if (result.success) { success.textContent=result.message; show(success); }
        else { error.textContent=result.message; show(error); }
      } catch(err) { hide(loading); error.textContent='Erro ao processar resgate: '+err.message; show(error); }
    }
  </script>
</body>
</html>`, gift.ID, gift.MembersCount, createdAt, gift.BotID, gift.ID)
}
