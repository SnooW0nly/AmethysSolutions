package main

import (
	"amethys-api/config"
	"amethys-api/database"
	httpHandlers "amethys-api/handlers/http"
	wsHandlers "amethys-api/handlers/websocket"
	"amethys-api/services"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/mux"
	"github.com/gorilla/websocket"
)

// SafeConn wraps a websocket.Conn with a mutex so multiple goroutines can
// write concurrently without corrupting the connection.
// gorilla/websocket explicitly states: "Connections support one concurrent
// reader and one concurrent writer." We were violating this by writing from
// SendAuthLog's goroutine AND from handleEvent at the same time.
type SafeConn struct {
	conn *websocket.Conn
	mu   sync.Mutex
}

func newSafeConn(conn *websocket.Conn) *SafeConn {
	return &SafeConn{conn: conn}
}

func (sc *SafeConn) WriteJSON(v interface{}) error {
	sc.mu.Lock()
	defer sc.mu.Unlock()
	return sc.conn.WriteJSON(v)
}

func (sc *SafeConn) WritePong(data []byte) error {
	sc.mu.Lock()
	defer sc.mu.Unlock()
	return sc.conn.WriteMessage(websocket.PongMessage, data)
}

func (sc *SafeConn) RemoteAddr() string {
	return sc.conn.RemoteAddr().String()
}

var (
	upgrader = websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
		CheckOrigin: func(r *http.Request) bool {
			return true
		},
	}

	// botSockets maps oauth_client_id → safe connection wrapper
	botSockets      = make(map[string]*SafeConn)
	botSocketsMutex sync.RWMutex

	// activeConns tracks total open WS connections (bots + unidentified)
	activeConns     int
	activeConnsMu   sync.Mutex
)

// wsLog emite log padronizado com timestamp preciso para todo evento WebSocket.
// Formato: [WS][TAG] mensagem  (+elapsed se fornecido)
func wsLog(tag, msg string, elapsed ...time.Duration) {
	ts := time.Now().Format("2006-01-02 15:04:05.000")
	if len(elapsed) > 0 && elapsed[0] > 0 {
		log.Printf("[WS][%s] %s  (+%s) @ %s", tag, msg, elapsed[0].Round(time.Millisecond), ts)
	} else {
		log.Printf("[WS][%s] %s  @ %s", tag, msg, ts)
	}
}

func main() {
	log.Println("Starting Amethys API...")

	config.LoadConfig()

	if err := database.InitStore(config.AppConfig.DatabaseType); err != nil {
		log.Fatal("Failed to initialize database:", err)
	}

	// Register the auth-log sender.  This is called from SendAuthLog which
	// already runs inside a goroutine, so the write MUST go through SafeConn.
	services.RegisterAuthLogSender(func(botID string, data map[string]interface{}) {
		t0 := time.Now()
		botSocketsMutex.RLock()
		sc, exists := botSockets[botID]
		botSocketsMutex.RUnlock()

		if !exists {
			wsLog("AUTH_LOG", fmt.Sprintf("❌ bot %s não conectado — auth_log descartado", botID))
			return
		}

		payload := map[string]interface{}{"event": "auth_log", "data": data}
		if err := sc.WriteJSON(payload); err != nil {
			wsLog("AUTH_LOG", fmt.Sprintf("❌ erro ao enviar para bot %s: %v", botID, err), time.Since(t0))
		} else {
			wsLog("AUTH_LOG", fmt.Sprintf("✅ enviado para bot %s", botID), time.Since(t0))
		}
	})

	services.StartVerificationChecker(notifyBotUnverified)

	r := mux.NewRouter()

	r.HandleFunc("/", handleHome).Methods("GET")

	// OAuth2 callback – registered under both paths for compatibility
	r.HandleFunc("/auth/callback", httpHandlers.HandleCallback).Methods("GET")
	r.HandleFunc("/api/auth/callback", httpHandlers.HandleCallback).Methods("GET")

	r.HandleFunc("/api/bot/register", httpHandlers.HandleRegisterBot).Methods("POST")
	r.HandleFunc("/api/bot/recover", httpHandlers.HandleBotRecover).Methods("GET")
	r.HandleFunc("/api/recover/members", httpHandlers.HandleRecoverMembers).Methods("POST")
	r.HandleFunc("/api/recover/status/{recoveryId}", httpHandlers.HandleRecoverStatus).Methods("GET")
	r.HandleFunc("/api/recover/abort/{recoveryId}", httpHandlers.HandleAbortRecovery).Methods("POST")
	r.HandleFunc("/gifts/{giftId}", httpHandlers.HandleGiftPage).Methods("GET")
	r.HandleFunc("/api/gift-page/{giftId}", httpHandlers.HandleGiftPage).Methods("GET")
	r.HandleFunc("/api/redeem-gift", httpHandlers.HandleRedeemGift).Methods("POST")
	r.HandleFunc("/api/recovery", httpHandlers.HandleRecovery).Methods("GET")
	r.HandleFunc("/api/bot/database/{botId}", httpHandlers.HandleDatabaseViewer).Methods("GET")
	r.HandleFunc("/api/bot/database/{botId}/download", httpHandlers.HandleDatabaseDownload).Methods("GET")
	r.HandleFunc("/ws", handleWebSocket)

	log.Printf("Amethys API running on port %s", config.AppConfig.Port)
	log.Fatal(http.ListenAndServe(":"+config.AppConfig.Port, r))
}

func handleHome(w http.ResponseWriter, r *http.Request) {
	services.LogHTTPRequest(r.Method, r.URL.Path, r.RemoteAddr, 200)
	w.Write([]byte("Amethys WebSocket Server Ready"))
}

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	connStart := time.Now()

	// Contar conexão ativa
	activeConnsMu.Lock()
	activeConns++
	totalActive := activeConns
	activeConnsMu.Unlock()

	remoteAddr := r.RemoteAddr
	userAgent  := r.Header.Get("User-Agent")
	wsLog("CONNECT", fmt.Sprintf("⬆ novo cliente: addr=%s ua=%q  (total abertas: %d)", remoteAddr, userAgent, totalActive))

	rawConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		wsLog("CONNECT", fmt.Sprintf("❌ upgrade HTTP→WS falhou: %v  addr=%s", err, remoteAddr), time.Since(connStart))
		activeConnsMu.Lock()
		activeConns--
		activeConnsMu.Unlock()
		return
	}
	defer rawConn.Close()

	upgradeElapsed := time.Since(connStart)
	wsLog("CONNECT", fmt.Sprintf("✅ upgrade concluído  addr=%s", remoteAddr), upgradeElapsed)

	sc := newSafeConn(rawConn)

	// ── Ping/Pong: responder corretamente aos pings do cliente Python ──────────
	// O cliente websockets (Python) envia ping frames automáticos a cada
	// ping_interval segundos e aguarda pong dentro de ping_timeout.
	// Sem handler explícito, o gorilla pode não renovar o deadline a tempo.
	const (
		wsPongWait   = 60 * time.Second // tempo máximo sem receber pong/ping
		wsPingPeriod = 54 * time.Second // deve ser < wsPongWait
	)
	rawConn.SetReadDeadline(time.Now().Add(wsPongWait))

	rawConn.SetPongHandler(func(appData string) error {
		rawConn.SetReadDeadline(time.Now().Add(wsPongWait))
		return nil
	})

	rawConn.SetPingHandler(func(appData string) error {
		// Renovar deadline e responder com pong (thread-safe via SafeConn)
		rawConn.SetReadDeadline(time.Now().Add(wsPongWait))
		if err := sc.WritePong([]byte(appData)); err != nil {
			wsLog("PING", fmt.Sprintf("⚠ erro ao enviar pong: %v  addr=%s", err, remoteAddr))
		}
		return nil
	})
	// ──────────────────────────────────────────────────────────────────────────

	// Identificador dinâmico: começa como addr, vira bot_id após bot_connected
	connLabel := remoteAddr
	var connBotID string

	defer func() {
		activeConnsMu.Lock()
		activeConns--
		remaining := activeConns
		activeConnsMu.Unlock()
		wsLog("DISCONNECT", fmt.Sprintf("🔌 conexão encerrada  label=%s  duração=%s  (restantes: %d)",
			connLabel, time.Since(connStart).Round(time.Millisecond), remaining))
	}()

	msgCount := 0

	for {
		readStart := time.Now()
		var msg map[string]interface{}
		if err := rawConn.ReadJSON(&msg); err != nil {
			if connBotID != "" {
				wsLog("READ", fmt.Sprintf("❌ leitura falhou  bot=%s  err=%v", connLabel, err))
			} else {
				wsLog("READ", fmt.Sprintf("❌ leitura falhou  addr=%s  err=%v", remoteAddr, err))
			}

			// Limpar mapa de bots
			botSocketsMutex.Lock()
			for botID, c := range botSockets {
				if c == sc {
					delete(botSockets, botID)
					services.UnregisterBot(botID)
					botSocketsMutex.RLock()
					remaining := len(botSockets)
					botSocketsMutex.RUnlock()
					wsLog("DISCONNECT", fmt.Sprintf("🗑  bot removido do mapa  bot=%s  (bots restantes: %d)", botID, remaining))
					break
				}
			}
			botSocketsMutex.Unlock()
			break
		}

		readElapsed := time.Since(readStart)
		msgCount++
		// Renovar deadline a cada mensagem recebida (além dos pings)
		rawConn.SetReadDeadline(time.Now().Add(wsPongWait))

		event, ok := msg["event"].(string)
		if !ok {
			wsLog("READ", fmt.Sprintf("⚠ mensagem sem campo 'event' ignorada  addr=%s  msg#%d", remoteAddr, msgCount))
			continue
		}

		wsLog("EVENT", fmt.Sprintf("📨 recebido  event=%-25s  label=%s  msg#%d  (leitura: %s)",
			event, connLabel, msgCount, readElapsed.Round(time.Millisecond)))

		handleEvent(sc, event, msg["data"])

		// Após bot_connected, atualizar o label da conexão
		if event == "bot_connected" {
			if data, ok := msg["data"].(map[string]interface{}); ok {
				if bid, ok := data["bot_id"].(string); ok && bid != "" {
					connBotID = bid
					connLabel = "bot=" + bid
				}
			}
		}
	}
}

// handleEvent processes a single WebSocket message.  All replies are written
// through sc (SafeConn) which serialises concurrent writes.
func handleEvent(sc *SafeConn, event string, data interface{}) {
	dataBytes, _ := json.Marshal(data)

	switch event {
	case "register":
		var req wsHandlers.RegisterRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleRegister(req)
		sc.WriteJSON(map[string]interface{}{"event": "register_response", "data": resp})

	case "bot_connected":
		var botData map[string]interface{}
		json.Unmarshal(dataBytes, &botData)

		botID, _ := botData["bot_id"].(string)
		if botID == "" {
			log.Printf("[WS] bot_connected received but bot_id is empty – ignoring")
			return
		}

		// Store the safe connection keyed by the bot's oauth_client_id.
		botSocketsMutex.Lock()
		botSockets[botID] = sc
		botSocketsMutex.Unlock()

		// Register for the verification checker.
		// ReadBots() agora usa cache em memória — sem I/O de disco na maioria dos casos.
		// Uma única leitura cobre tanto a busca por ClientID quanto por ID.
		clientIDForRegister := botID // fallback
		if bots, err := database.DB.ReadBots(); err == nil {
			for _, b := range bots {
				if b.ClientID == botID || b.ID == botID {
					clientIDForRegister = b.ClientID
					break
				}
			}
		}
		services.RegisterBot(botID, clientIDForRegister)

		log.Printf("[WS] Bot connected and registered: %s (total: %d)", botID, func() int {
			botSocketsMutex.RLock()
			defer botSocketsMutex.RUnlock()
			return len(botSockets)
		}())

	case "gift":
		var req wsHandlers.GiftRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleGift(req)
		sc.WriteJSON(map[string]interface{}{"event": "gift_response", "data": resp})

	case "update_gift":
		var req wsHandlers.UpdateGiftRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleUpdateGift(req)
		sc.WriteJSON(map[string]interface{}{"event": "update_gift_response", "data": resp})

	case "delete_gift":
		var req wsHandlers.DeleteGiftRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleDeleteGift(req)
		sc.WriteJSON(map[string]interface{}{"event": "delete_gift_response", "data": resp})

	case "get_gifts":
		var req wsHandlers.GetGiftsRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleGetGifts(req)
		sc.WriteJSON(map[string]interface{}{"event": "get_gifts_response", "data": resp})

	case "list_members":
		var req wsHandlers.ListMembersRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleListMembers(req)
		sc.WriteJSON(map[string]interface{}{"event": "list_members_response", "data": resp})

	case "check_auth_count":
		var req wsHandlers.CheckAuthCountRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleCheckAuthCount(req)
		sc.WriteJSON(map[string]interface{}{"event": "check_auth_count_response", "data": resp})

	case "recover_members":
		var req wsHandlers.RecoverMembersRequest
		json.Unmarshal(dataBytes, &req)
		resp := wsHandlers.HandleRecoverMembers(req)
		sc.WriteJSON(map[string]interface{}{"event": "recover_members_response", "data": resp})

	case "check_user_verification":
		var reqData map[string]interface{}
		json.Unmarshal(dataBytes, &reqData)
		botID, _ := reqData["botId"].(string)
		userID, _ := reqData["userId"].(string)

		if botID == "" || userID == "" {
			sc.WriteJSON(map[string]interface{}{
				"event": "check_user_verification_response",
				"data":  map[string]interface{}{"success": false, "message": "botId e userId são obrigatórios"},
			})
			return
		}

		isVerified, _ := services.CheckUserVerification(botID, userID)
		sc.WriteJSON(map[string]interface{}{
			"event": "check_user_verification_response",
			"data": map[string]interface{}{
				"success": true,
				"data":    map[string]interface{}{"is_verified": isVerified},
			},
		})

	case "update_definitions":
		var reqData map[string]interface{}
		json.Unmarshal(dataBytes, &reqData)
		botID, _ := reqData["bot_id"].(string)
		definitions, _ := reqData["definitions"].(map[string]interface{})
		mainServerID, _ := reqData["main_server_id"].(string)

		if botID != "" && definitions != nil {
			services.UpdateBotDefinitions(botID, definitions, mainServerID)
			log.Printf("Definitions updated for bot: %s", botID)
		}

	case "delete_all_gifts":
		var reqData map[string]interface{}
		json.Unmarshal(dataBytes, &reqData)
		botID, _ := reqData["bot_id"].(string)

		if botID == "" {
			sc.WriteJSON(map[string]interface{}{
				"event": "delete_all_gifts_response",
				"data":  map[string]interface{}{"success": false, "message": "bot_id é obrigatório"},
			})
			return
		}

		gifts, err := database.DB.ReadGifts()
		if err != nil {
			sc.WriteJSON(map[string]interface{}{
				"event": "delete_all_gifts_response",
				"data":  map[string]interface{}{"success": false, "message": "Erro ao listar gifts"},
			})
			return
		}

		deletedCount := 0
		remaining := []database.Gift{}
		for _, g := range gifts {
			if g.BotID == botID {
				deletedCount++
			} else {
				remaining = append(remaining, g)
			}
		}
		database.DB.WriteGifts(remaining)

		sc.WriteJSON(map[string]interface{}{
			"event": "delete_all_gifts_response",
			"data": map[string]interface{}{
				"success": true,
				"message": fmt.Sprintf("%d gifts deletados", deletedCount),
				"data":    map[string]interface{}{"deleted_count": deletedCount},
			},
		})

	case "synchronization":
		log.Printf("Synchronization event received")
		sc.WriteJSON(map[string]interface{}{
			"event": "synchronization_response",
			"data":  map[string]interface{}{"success": true, "message": "Sincronizado"},
		})

	case "recover":
		log.Printf("Recover event received")
		var reqData map[string]interface{}
		json.Unmarshal(dataBytes, &reqData)
		botID, _ := reqData["botId"].(string)

		respData := map[string]interface{}{"success": false, "message": "botId é obrigatório"}
		if botID != "" {
			bot, err := database.DB.FindBotByClientID(botID)
			if err == nil && bot != nil {
				respData = map[string]interface{}{
					"success": true,
					"message": "Dados recuperados com sucesso",
					"data": map[string]interface{}{
						"id":       bot.ID,
						"clientId": bot.ClientID,
						"members":  len(bot.Members),
					},
				}
			} else {
				respData = map[string]interface{}{"success": false, "message": "Bot não encontrado"}
			}
		}
		sc.WriteJSON(map[string]interface{}{"event": "recover_response", "data": respData})
	}
}

// notifyBotUnverified is called from the verification-checker ticker goroutine.
// It must use SafeConn to avoid concurrent-write panics.
func notifyBotUnverified(botID string, unverifiedMembers []database.Member) {
	botSocketsMutex.RLock()
	sc, exists := botSockets[botID]
	botSocketsMutex.RUnlock()

	if !exists {
		return
	}

	for _, member := range unverifiedMembers {
		data := map[string]interface{}{
			"success": false,
			"user": map[string]interface{}{
				"id":            member.ID,
				"username":      member.Username,
				"discriminator": member.Discriminator,
				"email":         member.Email,
				"ip":            member.IP,
				"unverified_at": member.UnverifiedAt,
				"reason":        member.Reason,
			},
			"guild_id":  member.GuildID,
			"client_id": member.ClientID,
		}

		if err := sc.WriteJSON(map[string]interface{}{"event": "auth_log", "data": data}); err != nil {
			log.Printf("Error sending unverification notification to bot %s: %v", botID, err)
			return
		}
		log.Printf("Unverification notification sent to bot %s: %s", botID, member.Username)
	}
}