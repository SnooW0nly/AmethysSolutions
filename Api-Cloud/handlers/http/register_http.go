package http

import (
	"amethys-api/database"
	"amethys-api/services"
	"encoding/json"
	"fmt"
	"net/http"
)

type RegisterHTTPRequest struct {
	Token        string `json:"token"`
	ClientSecret string `json:"clientSecret"`
	ClientID     string `json:"clientId"`
	MainBotID    string `json:"mainBotId"`
}

type RegisterHTTPResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	BotID   string                 `json:"botId,omitempty"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

func HandleRegisterBot(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}

	var req RegisterHTTPRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		services.LogHTTPRequest(r.Method, r.URL.Path, ip, 400)
		respondJSON(w, 400, RegisterHTTPResponse{
			Success: false,
			Message: "Corpo da requisição inválido",
		})
		return
	}

	if req.Token == "" || req.ClientSecret == "" || req.ClientID == "" {
		services.LogHTTPRequest(r.Method, r.URL.Path, ip, 400)
		respondJSON(w, 400, RegisterHTTPResponse{
			Success: false,
			Message: "token, clientSecret e clientId são obrigatórios",
		})
		return
	}

	// Validar token com a API do Discord
	botInfo, err := services.GetBotUser(req.Token)
	if err != nil {
		services.LogHTTPRequest(r.Method, r.URL.Path, ip, 401)
		respondJSON(w, 401, RegisterHTTPResponse{
			Success: false,
			Message: "Token do bot inválido",
		})
		return
	}

	// Garantir que o token pertence ao clientId informado
	if botInfo.ID != req.ClientID {
		services.LogHTTPRequest(r.Method, r.URL.Path, ip, 400)
		respondJSON(w, 400, RegisterHTTPResponse{
			Success: false,
			Message: "Token não pertence ao clientId especificado",
		})
		return
	}

	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	// Verificar se o bot já existe
	existingBot, _ := database.DB.FindBotByClientID(req.ClientID)

	if existingBot != nil {
		// Atualizar token/secret se mudaram
		if existingBot.Token != req.Token || existingBot.ClientSecret != req.ClientSecret {
			existingBot.Token = req.Token
			existingBot.ClientSecret = req.ClientSecret
			if existingBot.Definitions == nil {
				existingBot.Definitions = make(map[string]interface{})
			}
			database.DB.UpdateBot(existingBot)

			services.LogSuccess(
				"Bot Updated (HTTP)",
				fmt.Sprintf("Bot %s atualizado via HTTP", req.ClientID),
				map[string]string{"ClientID": req.ClientID, "BotID": existingBot.ID},
			)

			respondJSON(w, 200, RegisterHTTPResponse{
				Success: true,
				Message: "Bot atualizado com novo token",
				BotID:   existingBot.ID,
				Data: map[string]interface{}{
					"id":       existingBot.ID,
					"clientId": existingBot.ClientID,
				},
			})
			return
		}

		respondJSON(w, 200, RegisterHTTPResponse{
			Success: true,
			Message: "Bot já registrado",
			BotID:   existingBot.ID,
			Data: map[string]interface{}{
				"id":       existingBot.ID,
				"clientId": existingBot.ClientID,
			},
		})
		return
	}

	// Criar novo bot
	newBot := &database.Bot{
		ID:           botInfo.ID,
		Token:        req.Token,
		ClientSecret: req.ClientSecret,
		ClientID:     req.ClientID,
		Members:      []database.Member{},
		Definitions:  make(map[string]interface{}),
	}

	bots, _ := database.DB.ReadBots()
	bots = append(bots, *newBot)
	if err := database.DB.WriteBots(bots); err != nil {
		services.LogError("Register Failed (HTTP)", "Failed to save bot", err)
		respondJSON(w, 500, RegisterHTTPResponse{
			Success: false,
			Message: "Erro ao salvar dados no servidor",
		})
		return
	}

	services.LogSuccess(
		"Bot Registered (HTTP)",
		fmt.Sprintf("Novo bot registrado via HTTP: %s", req.ClientID),
		map[string]string{"ClientID": req.ClientID, "BotID": newBot.ID},
	)

	respondJSON(w, 200, RegisterHTTPResponse{
		Success: true,
		Message: "Bot registrado com sucesso",
		BotID:   newBot.ID,
		Data: map[string]interface{}{
			"id":       newBot.ID,
			"clientId": newBot.ClientID,
		},
	})
}