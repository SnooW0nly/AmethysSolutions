package http

import (
	"amethys-api/database"
	"amethys-api/services"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/mux"
)

// ── Estado em memória do recovery (substitui wio.db do JS) ───────────────────
type recoveryState struct {
	Status                string                    `json:"status"`
	ClientID              string                    `json:"client_id"`
	ServerID              string                    `json:"server_id"`
	TotalMembers          int                       `json:"total_members"`
	ProcessedMembers      int                       `json:"processed_members"`
	FailedMembers         int                       `json:"failed_members"`
	SkippedAlreadyInGuild int                       `json:"skipped_already_in_guild"`
	Failures              []database.RecoveryFailure `json:"failures"`
	StartedAt             int64                     `json:"started_at"`
	EstimatedCompletion   int64                     `json:"estimated_completion"`
	EstimatedTime         string                    `json:"estimated_time"`
	LastProcessedMember   string                    `json:"last_processed_member"`
	Error                 string                    `json:"error,omitempty"`
	aborted               bool
}

var (
	recoveryStore      = make(map[string]*recoveryState)
	recoveryStoreMutex sync.RWMutex
)

const (
	StatusPending             = "pending"
	StatusInProgress          = "in_progress"
	StatusCompleted           = "completed"
	StatusCompletedWithErrors = "completed_with_errors"
	StatusFailed              = "failed"
	StatusAborted             = "aborted"
)

// ── HandleBotRecover → GET /api/bot/recover?botId=xxx ────────────────────────
func HandleBotRecover(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}
	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	botID := r.URL.Query().Get("botId")
	if botID == "" {
		respondJSON(w, 400, map[string]interface{}{"success": false, "message": "botId é obrigatório"})
		return
	}

	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil {
		respondJSON(w, 404, map[string]interface{}{"success": false, "message": "Bot não encontrado"})
		return
	}

	respondJSON(w, 200, map[string]interface{}{
		"success": true,
		"message": "Dados recuperados com sucesso",
		"data": map[string]interface{}{
			"id":       bot.ID,
			"clientId": bot.ClientID,
			"members":  len(bot.Members),
		},
	})
}

// ── HandleRecoverMembers → POST /api/recover/members ─────────────────────────
// Agora retorna recovery_id real e processa em goroutine com estado persistido
func HandleRecoverMembers(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}
	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	var body struct {
		Data struct {
			ClientID     string `json:"client_id"`
			ClientSecret string `json:"client_secret"`
			Token        string `json:"token"`
			ServerID     string `json:"server_id"`
			Concurrency  int    `json:"concurrency"`
			BaseDelayMs  int    `json:"baseDelayMs"`
		} `json:"data"`
	}

	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		respondJSON(w, 400, map[string]interface{}{"success": false, "message": "Corpo da requisição inválido"})
		return
	}

	clientID := body.Data.ClientID
	serverID := body.Data.ServerID
	botToken := body.Data.Token

	if serverID == "" {
		respondJSON(w, 400, map[string]interface{}{"success": false, "message": "server_id é obrigatório"})
		return
	}

	// Buscar bot: por clientId, depois por token, senão o primeiro
	var bot *database.Bot
	var err error

	if clientID != "" {
		bot, err = database.DB.FindBotByClientID(clientID)
	}
	if bot == nil && botToken != "" {
		bots, _ := database.DB.ReadBots()
		for i := range bots {
			if bots[i].Token == botToken {
				bot = &bots[i]
				break
			}
		}
	}
	if bot == nil {
		bots, readErr := database.DB.ReadBots()
		if readErr == nil && len(bots) > 0 {
			bot = &bots[0]
		}
	}
	if bot == nil || err != nil {
		respondJSON(w, 404, map[string]interface{}{"success": false, "message": "Bot não encontrado"})
		return
	}

	// Usar token do body se fornecido, senão usar o do bot
	if botToken == "" {
		botToken = bot.Token
	}
	if botToken == "" {
		respondJSON(w, 400, map[string]interface{}{"success": false, "message": "Token do bot não configurado"})
		return
	}

	verifiedMembers := []database.Member{}
	for _, m := range bot.Members {
		if m.VerifiedAt != "" && m.AccessToken != "" {
			verifiedMembers = append(verifiedMembers, m)
		}
	}

	if len(verifiedMembers) == 0 {
		respondJSON(w, 404, map[string]interface{}{
			"success": false,
			"message": "Nenhum membro verificado disponível para recuperação",
			"data": map[string]interface{}{
				"recovery_id":    "",
				"total_members":  0,
				"estimated_time": 0,
			},
		})
		return
	}

	concurrency := body.Data.Concurrency
	if concurrency < 1 {
		concurrency = 3
	}
	if concurrency > 8 {
		concurrency = 8
	}

	baseDelayMs := body.Data.BaseDelayMs
	if baseDelayMs < 0 {
		baseDelayMs = 0
	}

	const msPerMember = 2000
	totalBatches := int(math.Ceil(float64(len(verifiedMembers)) / float64(concurrency)))
	totalMs := totalBatches * msPerMember
	totalSeconds := int(math.Ceil(float64(totalMs) / 1000))
	if totalSeconds < 1 {
		totalSeconds = 1
	}

	estimatedCompletion := time.Now().Unix() + int64(totalSeconds)
	estimatedMin := totalSeconds / 60
	estimatedSec := totalSeconds % 60
	var estimatedTimeStr string
	if estimatedMin > 0 {
		estimatedTimeStr = fmt.Sprintf("%d minutos e %d segundos", estimatedMin, estimatedSec)
	} else {
		estimatedTimeStr = fmt.Sprintf("%d segundos", estimatedSec)
	}

	recoveryID := fmt.Sprintf("%s_%d", clientID[:min(8, len(clientID))], time.Now().Unix())

	state := &recoveryState{
		Status:              StatusPending,
		ClientID:            clientID,
		ServerID:            serverID,
		TotalMembers:        len(verifiedMembers),
		ProcessedMembers:    0,
		FailedMembers:       0,
		Failures:            []database.RecoveryFailure{},
		StartedAt:           time.Now().Unix(),
		EstimatedCompletion: estimatedCompletion,
		EstimatedTime:       estimatedTimeStr,
	}

	recoveryStoreMutex.Lock()
	recoveryStore[recoveryID] = state
	recoveryStoreMutex.Unlock()

	// Processar em goroutine
	go func() {
		time.Sleep(1 * time.Second)

		recoveryStoreMutex.Lock()
		state.Status = StatusInProgress
		recoveryStoreMutex.Unlock()

		var idx int
		var idxMu sync.Mutex

		worker := func() {
			for {
				idxMu.Lock()
				cur := idx
				idx++
				idxMu.Unlock()

				if cur >= len(verifiedMembers) {
					return
				}
				member := verifiedMembers[cur]

				recoveryStoreMutex.Lock()
				state.LastProcessedMember = member.Username
				aborted := state.aborted
				recoveryStoreMutex.Unlock()

				if aborted {
					return
				}

				// Verificar se já está no servidor
				var checkAttempts int
				var check *checkResult
				for {
					present, headers, checkErr := services.IsMemberInGuild(member.ID, serverID, botToken)
					check = &checkResult{present: present, headers: headers, err: checkErr}
					if checkErr != nil && checkErr.Error() == "rate limited" && checkAttempts < 4 {
						waitMs := 2000
						if headers != nil && headers.ResetAfterMs > 0 {
							waitMs = headers.ResetAfterMs
						}
						wait := int(float64(waitMs)*math.Pow(1.5, float64(checkAttempts))) + services.Jitter(100, 300)
						services.Sleep(wait)
						checkAttempts++
						continue
					}
					break
				}

				if check.present {
					recoveryStoreMutex.Lock()
					state.SkippedAlreadyInGuild++
					state.ProcessedMembers++
					recoveryStoreMutex.Unlock()
					if baseDelayMs > 0 {
						services.Sleep(baseDelayMs + services.Jitter(50, 150))
					}
					continue
				}

				// Adicionar ao servidor
				var attempts int
				for {
					result, headers, _ := services.AddMemberToGuild(member.AccessToken, member.ID, serverID, botToken)
					if result.Success {
						recoveryStoreMutex.Lock()
						state.ProcessedMembers++
						recoveryStoreMutex.Unlock()

						if headers != nil && headers.Remaining == 0 && headers.ResetAfterMs > 0 {
							services.Sleep(headers.ResetAfterMs + services.Jitter(50, 150))
						} else if baseDelayMs > 0 {
							services.Sleep(baseDelayMs + services.Jitter(50, 150))
						}
						break
					}

					if result.Message == "RateLimited" && attempts < 4 {
						waitMs := int(2000*math.Pow(1.5, float64(attempts))) + services.Jitter(100, 300)
						services.Sleep(waitMs)
						attempts++
						continue
					}

					recoveryStoreMutex.Lock()
					state.FailedMembers++
					state.ProcessedMembers++
					state.Failures = append(state.Failures, database.RecoveryFailure{
						Username: member.Username,
						UserID:   member.ID,
						Reason:   result.Message,
					})
					recoveryStoreMutex.Unlock()

					if baseDelayMs > 0 {
						services.Sleep(baseDelayMs + services.Jitter(50, 150))
					}
					break
				}
			}
		}

		workerCount := concurrency
		if workerCount > len(verifiedMembers) {
			workerCount = len(verifiedMembers)
		}

		var wg sync.WaitGroup
		for i := 0; i < workerCount; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				worker()
			}()
		}
		wg.Wait()

		recoveryStoreMutex.Lock()
		if state.aborted {
			state.Status = StatusAborted
		} else if state.FailedMembers > 0 {
			state.Status = StatusCompletedWithErrors
		} else {
			state.Status = StatusCompleted
		}
		recoveryStoreMutex.Unlock()

		services.LogSuccess(
			"Recovery Complete (HTTP)",
			fmt.Sprintf("Recovery %s concluído para servidor %s", recoveryID, serverID),
			map[string]string{"RecoveryID": recoveryID, "BotID": clientID, "GuildID": serverID},
		)

		// Limpar estado após 60 segundos
		time.AfterFunc(60*time.Second, func() {
			recoveryStoreMutex.Lock()
			delete(recoveryStore, recoveryID)
			recoveryStoreMutex.Unlock()
		})
	}()

	respondJSON(w, 200, map[string]interface{}{
		"status":  200,
		"message": "Recovery process started",
		"data": map[string]interface{}{
			"recovery_id":                      recoveryID,
			"server_id":                        serverID,
			"total_members":                    len(verifiedMembers),
			"estimated_completion_timestamp":   estimatedCompletion,
			"estimated_time":                   estimatedTimeStr,
		},
	})
}

// ── HandleRecoverStatus → GET /api/recover/status/{recoveryId} ───────────────
func HandleRecoverStatus(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}
	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	vars := mux.Vars(r)
	recoveryID := vars["recoveryId"]

	if recoveryID == "" {
		respondJSON(w, 400, map[string]interface{}{"success": false, "message": "recoveryId é obrigatório"})
		return
	}

	recoveryStoreMutex.RLock()
	state, exists := recoveryStore[recoveryID]
	recoveryStoreMutex.RUnlock()

	if !exists {
		respondJSON(w, 404, map[string]interface{}{"status": 404, "message": "Recovery process not found"})
		return
	}

	recoveryStoreMutex.RLock()
	progress := 0.0
	if state.TotalMembers > 0 {
		progress = float64(state.ProcessedMembers) / float64(state.TotalMembers) * 100
	}
	successRate := 100.0
	if state.ProcessedMembers > 0 {
		successRate = float64(state.ProcessedMembers-state.FailedMembers) / float64(state.ProcessedMembers) * 100
	}
	isFinal := state.Status == StatusCompleted ||
		state.Status == StatusCompletedWithErrors ||
		state.Status == StatusFailed ||
		state.Status == StatusAborted
	now := time.Now().Unix()
	var cleanupTime int64
	var willBeDeletedIn string
	if isFinal {
		cleanupTime = now + 60
		willBeDeletedIn = fmt.Sprintf("%d segundos", max(0, int(cleanupTime-now)))
	}

	resp := map[string]interface{}{
		"status": 200,
		"data": map[string]interface{}{
			"status":                    state.Status,
			"client_id":                 state.ClientID,
			"server_id":                 state.ServerID,
			"total_members":             state.TotalMembers,
			"processed_members":         state.ProcessedMembers,
			"failed_members":            state.FailedMembers,
			"skipped_already_in_guild":  state.SkippedAlreadyInGuild,
			"failures":                  state.Failures,
			"started_at":                state.StartedAt,
			"estimated_completion":      state.EstimatedCompletion,
			"estimated_time":            state.EstimatedTime,
			"last_processed_member":     state.LastProcessedMember,
			"progress":                  math.Round(progress*10) / 10,
			"success_rate":              math.Round(successRate*10) / 10,
			"current_time":              now,
			"cleanup_scheduled_for":     cleanupTime,
			"will_be_deleted_in":        willBeDeletedIn,
		},
	}
	recoveryStoreMutex.RUnlock()

	respondJSON(w, 200, resp)
}

// ── HandleAbortRecovery → POST /api/recover/abort/{recoveryId} ───────────────
// Rota nova que estava só no JS
func HandleAbortRecovery(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}
	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	vars := mux.Vars(r)
	recoveryID := vars["recoveryId"]

	var body struct {
		Data struct {
			ClientID     string `json:"client_id"`
			ClientSecret string `json:"client_secret"`
			Token        string `json:"token"`
		} `json:"data"`
	}
	json.NewDecoder(r.Body).Decode(&body)

	recoveryStoreMutex.RLock()
	state, exists := recoveryStore[recoveryID]
	recoveryStoreMutex.RUnlock()

	if !exists {
		respondJSON(w, 404, map[string]interface{}{"status": 404, "message": "Recovery process not found"})
		return
	}

	if body.Data.ClientID != "" && state.ClientID != body.Data.ClientID {
		respondJSON(w, 403, map[string]interface{}{"status": 403, "message": "You don't have permission to abort this recovery"})
		return
	}

	if state.Status != StatusPending && state.Status != StatusInProgress {
		respondJSON(w, 400, map[string]interface{}{
			"status":  400,
			"message": fmt.Sprintf("Cannot abort recovery in %s status", state.Status),
		})
		return
	}

	recoveryStoreMutex.Lock()
	state.aborted = true
	state.Status = StatusAborted
	recoveryStoreMutex.Unlock()

	// Limpar após 60 segundos
	time.AfterFunc(60*time.Second, func() {
		recoveryStoreMutex.Lock()
		delete(recoveryStore, recoveryID)
		recoveryStoreMutex.Unlock()
	})

	respondJSON(w, 200, map[string]interface{}{
		"status":  200,
		"message": "Recovery process aborted successfully",
		"data": map[string]interface{}{
			"recovery_id":       recoveryID,
			"final_status":      StatusAborted,
			"processed_members": state.ProcessedMembers,
		},
	})
}

// ── Helpers ───────────────────────────────────────────────────────────────────

type checkResult struct {
	present bool
	headers *database.RateLimitHeaders
	err     error
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
