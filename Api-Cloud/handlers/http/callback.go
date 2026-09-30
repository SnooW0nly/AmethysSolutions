package http

import (
	"amethys-api/config"
	"amethys-api/database"
	"amethys-api/services"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// HandleCallback — rota /auth/callback
func HandleCallback(w http.ResponseWriter, r *http.Request) {
	code := r.URL.Query().Get("code")
	state := r.URL.Query().Get("state")
	oauthError := r.URL.Query().Get("error")
	oauthErrorDesc := r.URL.Query().Get("error_description")

	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.Header.Get("X-Real-IP")
	}
	if ip == "" {
		ip = r.RemoteAddr
	}

	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	// Erro vindo do Discord
	if oauthError != "" {
		renderErrorPage(w, "Verificação falhou", "Ocorreu um erro durante a autorização.",
			fmt.Sprintf("<div><strong>Erro:</strong> %s</div><div><strong>Descrição:</strong> %s</div>",
				oauthError, oauthErrorDesc))
		return
	}

	if code == "" {
		renderErrorPage(w, "Verificação falhou", "Não recebemos o código de autorização.",
			"<div><strong>Detalhe:</strong> Código de autorização não encontrado.</div>")
		return
	}

	// state = "clientId-guildId"
	// IDs do Discord são puramente numéricos, então o primeiro "-" separa clientId de guildId.
	// Usamos LastIndex para ser robusto caso o formato mude no futuro.
	var clientID, guildID string
	dashIdx := strings.Index(state, "-")
	if dashIdx == -1 {
		clientID = state
		guildID = ""
	} else {
		clientID = state[:dashIdx]
		guildID = state[dashIdx+1:]
	}

	if clientID == "" {
		renderErrorPage(w, "Verificação falhou", "Estado da requisição inválido.",
			"<div><strong>Detalhe:</strong> client_id não encontrado no state.</div>")
		return
	}

	bot, err := database.DB.FindBotByClientID(clientID)
	if err != nil {
		renderErrorPage(w, "Verificação falhou", "Bot não encontrado.",
			fmt.Sprintf("<div><strong>Detalhe:</strong> Bot não encontrado para client_id: %s</div>", clientID))
		return
	}

	tokenResp, err := services.ExchangeCode(code, bot.ClientID, bot.ClientSecret, config.AppConfig.RedirectURI)
	if err != nil {
		renderErrorPage(w, "Erro na verificação", "Ocorreu um problema ao processar sua verificação.",
			fmt.Sprintf("<div><strong>Erro:</strong> %s</div>", err.Error()))
		return
	}

	user, err := services.GetDiscordUser(tokenResp.AccessToken)
	if err != nil {
		renderErrorPage(w, "Erro na verificação", "Não foi possível obter informações do usuário.",
			fmt.Sprintf("<div><strong>Erro:</strong> %s</div>", err.Error()))
		return
	}

	// ── Regras de bloqueio baseadas em definitions do bot ─────────────────────
	defs := bot.Definitions

	if blockVPN, ok := defs["block_vpn"].(map[string]interface{}); ok {
		if enabled, _ := blockVPN["enabled"].(bool); enabled {
			if ip == "" || strings.EqualFold(ip, "unknown") {
				renderBlockedPage(w, "Verificação Bloqueada", "Detecção de VPN/Proxy.")
				return
			}
		}
	}

	if blockMobile, ok := defs["block_mobile"].(map[string]interface{}); ok {
		if enabled, _ := blockMobile["enabled"].(bool); enabled {
			ua := strings.ToLower(r.Header.Get("User-Agent"))
			if strings.ContainsAny(ua, "mobile") ||
				strings.Contains(ua, "android") ||
				strings.Contains(ua, "iphone") ||
				strings.Contains(ua, "ipad") {
				renderBlockedPage(w, "Verificação Bloqueada", "Acesso por rede móvel não permitido.")
				return
			}
		}
	}

	if blockNoEmail, ok := defs["block_no_email"].(map[string]interface{}); ok {
		if enabled, _ := blockNoEmail["enabled"].(bool); enabled {
			if user.Email == "" {
				renderBlockedPage(w, "Verificação Bloqueada", "Sua conta não possui e-mail vinculado.")
				return
			}
		}
	}

	if blockSpam, ok := defs["block_spam"].(map[string]interface{}); ok {
		if enabled, _ := blockSpam["enabled"].(bool); enabled {
			if user.Email == "" && user.Avatar == "" {
				renderBlockedPage(w, "Verificação Bloqueada", "Conta sinalizada como suspeita.")
				return
			}
		}
	}
	// ──────────────────────────────────────────────────────────────────────────

	member := database.Member{
		ID:            user.ID,
		Username:      user.Username,
		Discriminator: user.Discriminator,
		Email:         user.Email,
		Avatar:        user.Avatar,
		IP:            ip,
		VerifiedAt:    time.Now().Format(time.RFC3339),
		AccessToken:   tokenResp.AccessToken,
		RefreshToken:  tokenResp.RefreshToken,
		ClientID:      bot.ClientID,
		GuildID:       guildID,
	}

	memberExists := false
	for i, m := range bot.Members {
		if m.ID == member.ID {
			bot.Members[i] = member
			memberExists = true
			break
		}
	}
	if !memberExists {
		bot.Members = append(bot.Members, member)
	}

	if err := database.DB.UpdateBot(bot); err != nil {
		services.LogError("OAuth Callback Failed", "Failed to save member", err)
		renderErrorPage(w, "Erro interno", "Não foi possível salvar os dados.",
			"<div><strong>Erro:</strong> Falha ao salvar membro no banco de dados.</div>")
		return
	}

	// ── Enviar auth_log via WebSocket para o bot ──────────────────────────────
	authData := map[string]interface{}{
		"success": true,
		"user": map[string]interface{}{
			"id":            user.ID,
			"username":      user.Username,
			"discriminator": user.Discriminator,
			"email":         user.Email,
			"avatar":        user.Avatar,
			"ip":            ip,
			"verified_at":   member.VerifiedAt,
		},
		"guild_id":  guildID,
		"client_id": clientID,
	}
	services.SendAuthLog(clientID, authData)

	// ── sync_oauth2: dar papel no servidor principal ───────────────────────────
	if syncOAuth2, ok := defs["sync_oauth2"].(map[string]interface{}); ok {
		if enabled, _ := syncOAuth2["enabled"].(bool); enabled && bot.MainServerID != "" {
			syncData := map[string]interface{}{
				"success": true,
				"user": map[string]interface{}{
					"id":            user.ID,
					"username":      user.Username,
					"discriminator": user.Discriminator,
					"email":         user.Email,
					"avatar":        user.Avatar,
					"ip":            ip,
					"verified_at":   member.VerifiedAt,
				},
				"guild_id":  bot.MainServerID,
				"client_id": clientID,
				"reason":    "sync_oauth2",
			}
			services.SendAuthLog(clientID, syncData)
		}
	}

	// ── auto_join_oauth2: puxar usuário para servidor principal ───────────────
	if autoJoin, ok := defs["auto_join_oauth2"].(map[string]interface{}); ok {
		if enabled, _ := autoJoin["enabled"].(bool); enabled && bot.MainServerID != "" && bot.Token != "" {
			go func() {
				services.AddMemberToGuild(tokenResp.AccessToken, user.ID, bot.MainServerID, bot.Token)
			}()
		}
	}
	// ──────────────────────────────────────────────────────────────────────────

	services.LogSuccess(
		"Member Verified",
		fmt.Sprintf("User %s verified for bot %s", user.Username, bot.ClientID),
		map[string]string{
			"UserID":   user.ID,
			"Username": user.Username,
			"BotID":    bot.ClientID,
			"IP":       ip,
		},
	)

	log.Printf("Member verified: %s (%s) for bot %s", user.Username, user.ID, bot.ClientID)

	renderSuccessPage(w, user)
}

// ── Páginas HTML ──────────────────────────────────────────────────────────────

func renderSuccessPage(w http.ResponseWriter, user *database.DiscordUser) {
	defaultAvatarIndex := 0
	if user.Discriminator != "" && user.Discriminator != "0" {
		disc := 0
		fmt.Sscanf(user.Discriminator, "%d", &disc)
		defaultAvatarIndex = disc % 5
	}

	avatarURL := fmt.Sprintf("https://cdn.discordapp.com/embed/avatars/%d.png", defaultAvatarIndex)
	if user.Avatar != "" {
		ext := "png"
		if strings.HasPrefix(user.Avatar, "a_") {
			ext = "gif"
		}
		avatarURL = fmt.Sprintf("https://cdn.discordapp.com/avatars/%s/%s.%s?size=128", user.ID, user.Avatar, ext)
	}

	displayName := user.Username
	if user.Discriminator != "" && user.Discriminator != "0" {
		displayName = user.Username + "#" + user.Discriminator
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Verificação Concluída — Amethyst Cloud</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <meta http-equiv="Cache-Control" content="no-store"/>
  <meta name="robots" content="noindex,nofollow">
  <style>
    :root {
      --primary: #a855f7;
      --primary-light: #c084fc;
      --primary-dark: #9333ea;
      --primary-glow: rgba(168, 85, 247, 0.25);
      --success: #22c55e;
      --success-dim: rgba(34, 197, 94, 0.1);
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

    .header-badge {
      font-size: 12px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 24px;
      letter-spacing: 0.02em;
    }

    /* Main Content */
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
      max-width: 720px;
      width: 100%%;
    }

    /* Hero Section */
    .hero {
      text-align: center;
      margin-bottom: 48px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--success-dim);
      border: 1px solid rgba(34, 197, 94, 0.2);
      padding: 8px 18px;
      border-radius: 32px;
      margin-bottom: 32px;
      font-size: 13px;
      color: var(--success);
      font-weight: 500;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%%;
      background: var(--success);
      box-shadow: 0 0 12px var(--success);
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
      max-width: 480px;
      margin: 0 auto;
    }

    /* User Card */
    .user-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 32px;
      margin-bottom: 24px;
      position: relative;
      overflow: hidden;
    }

    .user-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--primary), transparent);
    }

    .user-profile {
      display: flex;
      align-items: center;
      gap: 24px;
    }

    .avatar-wrapper {
      position: relative;
    }

    .user-avatar {
      width: 88px;
      height: 88px;
      border-radius: 50%%;
      border: 3px solid var(--primary);
      box-shadow: 0 0 32px var(--primary-glow);
      object-fit: cover;
    }

    .verified-badge {
      position: absolute;
      bottom: 0;
      right: 0;
      width: 28px;
      height: 28px;
      background: var(--success);
      border-radius: 50%%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 3px solid var(--bg);
    }

    .verified-badge svg {
      width: 14px;
      height: 14px;
      color: white;
    }

    .user-info {
      flex: 1;
    }

    .user-name {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 6px;
      letter-spacing: -0.02em;
    }

    .user-email {
      font-size: 15px;
      color: var(--text-secondary);
      margin-bottom: 4px;
    }

    .user-id {
      font-size: 13px;
      color: var(--text-muted);
      font-family: 'SF Mono', Monaco, monospace;
    }

    .user-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      color: white;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      margin-top: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    /* Info Grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 32px;
    }

    .info-item {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
      text-align: center;
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

    .info-value.purple {
      color: var(--primary-light);
    }

    /* Button */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 16px 32px;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      color: white;
      font-weight: 600;
      font-size: 16px;
      border: none;
      cursor: pointer;
      text-decoration: none;
      box-shadow: 0 8px 32px var(--primary-glow);
      width: 100%%;
    }

    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 40px rgba(168, 85, 247, 0.35);
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
      h1 { font-size: 32px; }
      .user-profile { flex-direction: column; text-align: center; }
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
      <span class="logo-text">Amethyst Cloud</span>
    </a>
    <span class="header-badge">Sistema de Verificação</span>
  </header>

  <main>
    <div class="container">
      <div class="hero">
        <div class="status-badge">
          <span class="status-dot"></span>
          Verificação Concluída
        </div>
        <h1>Identidade Confirmada</h1>
        <p class="hero-desc">Sua verificação foi processada com sucesso. Seus dados foram validados e registrados no sistema.</p>
      </div>

      <div class="user-card">
        <div class="user-profile">
          <div class="avatar-wrapper">
            <img src="%s" alt="Avatar" class="user-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/%d.png'">
            <div class="verified-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
          </div>
          <div class="user-info">
            <h2 class="user-name">%s</h2>
            <p class="user-email">%s</p>
            <p class="user-id">ID: %s</p>
            <div class="user-tag">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              Verificado
            </div>
          </div>
        </div>
      </div>

      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">Status</div>
          <div class="info-value purple">Ativo</div>
        </div>
        <div class="info-item">
          <div class="info-label">Plataforma</div>
          <div class="info-value">Discord</div>
        </div>
        <div class="info-item">
          <div class="info-label">Proteção</div>
          <div class="info-value">OAuth2</div>
        </div>
      </div>

      <a class="btn" href="javascript:window.close()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        Fechar Janela
      </a>
    </div>
  </main>

  <footer>
    <div class="footer-brand">
      <span class="footer-logo"><span>Amethyst</span> Applications</span>
      <span class="footer-copy">© 2025 Todos os direitos reservados</span>
    </div>
    <div class="footer-links">
      <a href="https://amethysapp.vercel.app/" target="_blank">Site</a>
      <a href="#" target="_blank">Termos</a>
      <a href="#" target="_blank">Suporte</a>
    </div>
  </footer>
</body>
</html>`, avatarURL, defaultAvatarIndex, displayName, user.Email, user.ID)
}

func renderErrorPage(w http.ResponseWriter, title, subtitle, detailsHTML string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusBadRequest)
	fmt.Fprintf(w, `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>%s — Amethyst Cloud</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
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
      top: -50%%;
      left: 50%%;
      transform: translateX(-50%%);
      width: 100%%;
      height: 100%%;
      z-index: 0;
      background: radial-gradient(ellipse 80%% 50%% at 50%% 0%%, rgba(239, 68, 68, 0.06), transparent 60%%);
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
      max-width: 640px;
      width: 100%%;
    }

    .hero {
      text-align: center;
      margin-bottom: 48px;
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
      border-radius: 50%%;
      background: var(--danger);
    }

    .error-icon {
      width: 80px;
      height: 80px;
      margin: 0 auto 24px;
      background: var(--danger-dim);
      border: 1px solid rgba(239, 68, 68, 0.2);
      border-radius: 50%%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .error-icon svg {
      width: 36px;
      height: 36px;
      color: var(--danger);
    }

    h1 {
      font-size: 40px;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.1;
      margin-bottom: 16px;
    }

    .hero-desc {
      font-size: 17px;
      color: var(--text-secondary);
      line-height: 1.7;
      max-width: 480px;
      margin: 0 auto;
    }

    .error-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 32px;
    }

    .error-card-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .error-card-content {
      font-size: 14px;
      color: var(--text-secondary);
      line-height: 1.7;
    }

    .error-card-content div {
      margin-bottom: 8px;
    }

    .error-card-content strong {
      color: var(--text);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 16px 32px;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      color: white;
      font-weight: 600;
      font-size: 16px;
      border: none;
      cursor: pointer;
      text-decoration: none;
      box-shadow: 0 8px 32px var(--primary-glow);
      width: 100%%;
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
      <span class="logo-text">Amethyst Cloud</span>
    </a>
    <span class="header-badge">Sistema de Verificação</span>
  </header>

  <main>
    <div class="container">
      <div class="hero">
        <div class="status-badge">
          <span class="status-dot"></span>
          Erro Detectado
        </div>
        <div class="error-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <h1>%s</h1>
        <p class="hero-desc">%s</p>
      </div>

      <div class="error-card">
        <div class="error-card-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          Detalhes do Erro
        </div>
        <div class="error-card-content">%s</div>
      </div>

      <a class="btn" href="javascript:window.close()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        Fechar Janela
      </a>
    </div>
  </main>

  <footer>
    <div class="footer-brand">
      <span class="footer-logo"><span>Amethyst</span> Applications</span>
      <span class="footer-copy">© 2025 Todos os direitos reservados</span>
    </div>
    <div class="footer-links">
      <a href="https://amethys.solutions/" target="_blank">Site</a>
      <a href="#" target="_blank">Termos</a>
      <a href="#" target="_blank">Suporte</a>
    </div>
  </footer>
</body>
</html>`, title, title, subtitle, detailsHTML)
}

func renderBlockedPage(w http.ResponseWriter, title, detail string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusForbidden)
	fmt.Fprintf(w, `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>%s — Amethyst Cloud</title>
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
      top: -50%%;
      left: 50%%;
      transform: translateX(-50%%);
      width: 100%%;
      height: 100%%;
      z-index: 0;
      background: radial-gradient(ellipse 80%% 50%% at 50%% 0%%, rgba(239, 68, 68, 0.06), transparent 60%%);
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
      max-width: 560px;
      width: 100%%;
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
      border-radius: 50%%;
      background: var(--danger);
    }

    .blocked-icon {
      width: 96px;
      height: 96px;
      margin: 0 auto 32px;
      background: var(--danger-dim);
      border: 1px solid rgba(239, 68, 68, 0.2);
      border-radius: 50%%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .blocked-icon svg {
      width: 44px;
      height: 44px;
      color: var(--danger);
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
      max-width: 420px;
      margin: 0 auto 40px;
    }

    .info-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 32px;
      text-align: left;
    }

    .info-card-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .info-card-content {
      font-size: 14px;
      color: var(--text-secondary);
      line-height: 1.7;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 16px 32px;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--danger), #f87171);
      color: white;
      font-weight: 600;
      font-size: 16px;
      border: none;
      cursor: pointer;
      text-decoration: none;
      box-shadow: 0 8px 32px rgba(239, 68, 68, 0.25);
      width: 100%%;
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
      <span class="logo-text">Amethyst Cloud</span>
    </a>
    <span class="header-badge">Sistema de Verificação</span>
  </header>

  <main>
    <div class="container">
      <div class="status-badge">
        <span class="status-dot"></span>
        Acesso Bloqueado
      </div>
      <div class="blocked-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
        </svg>
      </div>
      <h1>%s</h1>
      <p class="desc">%s</p>

      <div class="info-card">
        <div class="info-card-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          O que fazer?
        </div>
        <div class="info-card-content">
          Se você acredita que isso é um erro, entre em contato com o administrador do servidor ou tente novamente mais tarde.
        </div>
      </div>

      <a class="btn" href="javascript:window.close()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        Fechar Janela
      </a>
    </div>
  </main>

  <footer>
    <div class="footer-brand">
      <span class="footer-logo"><span>Amethyst</span> Applications</span>
      <span class="footer-copy">© 2025 Todos os direitos reservados</span>
    </div>
    <div class="footer-links">
      <a href="https://amethysapp.vercel.app" target="_blank">Site</a>
      <a href="#" target="_blank">Termos</a>
      <a href="#" target="_blank">Suporte</a>
    </div>
  </footer>
</body>
</html>`, title, title, detail)
}
