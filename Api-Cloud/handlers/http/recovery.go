package http

import (
	"amethys-api/database"
	"amethys-api/services"
	"net/http"
	"time"
)

type RecoveryResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

func HandleRecovery(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}

	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	botID := r.URL.Query().Get("botId")
	if botID == "" {
		respondJSON(w, 400, RecoveryResponse{
			Success: false,
			Message: "botId é obrigatório",
		})
		return
	}

	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil {
		respondJSON(w, 404, RecoveryResponse{
			Success: false,
			Message: "Bot não encontrado",
		})
		return
	}

	gifts, _ := database.DB.ReadGifts()
	botGifts := []map[string]interface{}{}
	
	for _, gift := range gifts {
		if gift.BotID == botID {
			botGifts = append(botGifts, map[string]interface{}{
				"id":        gift.ID,
				"status":    gift.Status,
				"createdAt": gift.CreatedAt,
			})
		}
	}

	activeGifts := 0
	pendingGifts := 0
	for _, gift := range botGifts {
		status := gift["status"].(string)
		if status == "active" {
			activeGifts++
		} else if status == "pending" {
			pendingGifts++
		}
	}

	recoveryInfo := map[string]interface{}{
		"bot": map[string]interface{}{
			"id":       bot.ID,
			"clientId": bot.ClientID,
		},
		"gifts": botGifts,
		"statistics": map[string]interface{}{
			"totalGifts":   len(botGifts),
			"activeGifts":  activeGifts,
			"pendingGifts": pendingGifts,
		},
		"recoveredAt": time.Now().Format(time.RFC3339),
	}

	services.LogSuccess(
		"Recovery Complete",
		"Bot data recovered successfully",
		map[string]string{
			"BotID": botID,
			"Gifts": string(rune(len(botGifts))),
		},
	)

	respondJSON(w, 200, RecoveryResponse{
		Success: true,
		Message: "Recuperação realizada com sucesso",
		Data:    recoveryInfo,
	})
}
