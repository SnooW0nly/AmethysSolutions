package websocket

import (
	"amethys-api/database"
	"amethys-api/services"
	"fmt"
)

type RegisterRequest struct {
	Token        string `json:"token"`
	ClientSecret string `json:"clientSecret"`
	ClientID     string `json:"clientId"`
}

type RegisterResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	BotID   string                 `json:"botId,omitempty"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

func HandleRegister(req RegisterRequest) RegisterResponse {
	if req.Token == "" || req.ClientSecret == "" || req.ClientID == "" {
		services.LogError("Register Failed", "Missing required fields", nil)
		return RegisterResponse{
			Success: false,
			Message: "Token, clientSecret e clientId são obrigatórios",
		}
	}

	existingBot, _ := database.DB.FindBotByClientID(req.ClientID)

	// Fast-path: bot já registrado com token idêntico — responde sem chamar
	// a API do Discord, evitando 100-500 ms bloqueantes em toda reconexão.
	if existingBot != nil && existingBot.Token == req.Token {
		services.LogSuccess(
			"Bot Already Registered",
			fmt.Sprintf("Bot %s already registered (token unchanged)", req.ClientID),
			map[string]string{"ClientID": req.ClientID, "BotID": existingBot.ID},
		)
		return RegisterResponse{
			Success: true,
			Message: "Bot já registrado",
			BotID:   existingBot.ID,
			Data: map[string]interface{}{
				"id":       existingBot.ID,
				"clientId": existingBot.ClientID,
			},
		}
	}

	// Bot novo ou token mudou — valida contra a API do Discord.
	botInfo, err := services.GetBotUser(req.Token)
	if err != nil {
		services.LogError("Register Failed", "Invalid bot token", err)
		return RegisterResponse{
			Success: false,
			Message: "Token do bot inválido",
		}
	}

	if botInfo.ID != req.ClientID {
		return RegisterResponse{
			Success: false,
			Message: "Token não pertence ao clientId especificado",
		}
	}

	// Token mudou para um bot já existente — atualiza.
	if existingBot != nil {
		existingBot.Token = req.Token
		existingBot.ClientSecret = req.ClientSecret
		if existingBot.Definitions == nil {
			existingBot.Definitions = make(map[string]interface{})
		}
		database.DB.UpdateBot(existingBot)

		services.LogSuccess(
			"Bot Updated",
			fmt.Sprintf("Bot %s updated with new token", req.ClientID),
			map[string]string{"ClientID": req.ClientID, "BotID": existingBot.ID},
		)

		return RegisterResponse{
			Success: true,
			Message: "Bot atualizado com novo token",
			BotID:   existingBot.ID,
			Data: map[string]interface{}{
				"id":       existingBot.ID,
				"clientId": existingBot.ClientID,
			},
		}
	}

	// Bot completamente novo — registra.
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
	if err = database.DB.WriteBots(bots); err != nil {
		services.LogError("Register Failed", "Failed to save bot", err)
		return RegisterResponse{
			Success: false,
			Message: "Erro ao salvar dados no arquivo",
		}
	}

	services.LogSuccess(
		"Bot Registered",
		fmt.Sprintf("New bot registered: %s", req.ClientID),
		map[string]string{"ClientID": req.ClientID, "BotID": newBot.ID},
	)

	return RegisterResponse{
		Success: true,
		Message: "Bot registrado com sucesso",
		BotID:   newBot.ID,
		Data: map[string]interface{}{
			"id":       newBot.ID,
			"clientId": newBot.ClientID,
		},
	}
}
