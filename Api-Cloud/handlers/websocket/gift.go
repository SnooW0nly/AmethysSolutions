package websocket

import (
	"amethys-api/database"
	"amethys-api/services"
	"fmt"
	"time"
)

type GiftRequest struct {
	BotID    string         `json:"botId"`
	GiftData *database.Gift `json:"giftData"`
}

type UpdateGiftRequest struct {
	GiftID          string `json:"gift_id"`
	NewMembersCount int    `json:"new_members_count"`
	UpdatedBy       string `json:"updated_by"`
}

type DeleteGiftRequest struct {
	GiftID    string `json:"gift_id"`
	DeletedBy string `json:"deleted_by"`
}

type GetGiftsRequest struct {
	BotID string `json:"botId"`
}

type GiftResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

func HandleGift(req GiftRequest) GiftResponse {
	if req.BotID == "" || req.GiftData == nil {
		return GiftResponse{
			Success: false,
			Message: "Bot ID e dados do gift são obrigatórios",
		}
	}

	err := database.DB.AddGift(req.GiftData)
	if err != nil {
		services.LogError("Gift Creation Failed", "Failed to create gift", err)
		return GiftResponse{
			Success: false,
			Message: "Erro interno do servidor ao criar gift",
		}
	}

	services.LogSuccess(
		"Gift Created",
		fmt.Sprintf("Gift %s created with %d members", req.GiftData.ID, req.GiftData.MembersCount),
		map[string]string{
			"GiftID":       req.GiftData.ID,
			"BotID":        req.BotID,
			"MemberCount":  fmt.Sprintf("%d", req.GiftData.MembersCount),
		},
	)

	return GiftResponse{
		Success: true,
		Message: "Gift criado com sucesso",
		Data: map[string]interface{}{
			"gift_id": req.GiftData.ID,
		},
	}
}

func HandleUpdateGift(req UpdateGiftRequest) GiftResponse {
	if req.GiftID == "" || req.NewMembersCount == 0 {
		return GiftResponse{
			Success: false,
			Message: "Gift ID e nova quantidade de membros são obrigatórios",
		}
	}

	gift, err := database.DB.FindGiftByID(req.GiftID)
	if err != nil {
		return GiftResponse{
			Success: false,
			Message: "Gift não encontrado",
		}
	}

	gift.MembersCount = req.NewMembersCount
	gift.UpdatedBy = req.UpdatedBy
	gift.UpdatedAt = time.Now()

	err = database.DB.UpdateGift(gift)
	if err != nil {
		services.LogError("Gift Update Failed", "Failed to update gift", err)
		return GiftResponse{
			Success: false,
			Message: "Erro interno do servidor ao atualizar gift",
		}
	}

	services.LogSuccess(
		"Gift Updated",
		fmt.Sprintf("Gift %s updated to %d members", req.GiftID, req.NewMembersCount),
		map[string]string{
			"GiftID":      req.GiftID,
			"MemberCount": fmt.Sprintf("%d", req.NewMembersCount),
		},
	)

	return GiftResponse{
		Success: true,
		Message: "Gift atualizado com sucesso",
	}
}

func HandleDeleteGift(req DeleteGiftRequest) GiftResponse {
	if req.GiftID == "" {
		return GiftResponse{
			Success: false,
			Message: "Gift ID é obrigatório",
		}
	}

	gift, err := database.DB.FindGiftByID(req.GiftID)
	if err != nil {
		return GiftResponse{
			Success: false,
			Message: "Gift não encontrado",
		}
	}

	err = database.DB.DeleteGift(req.GiftID)
	if err != nil {
		services.LogError("Gift Deletion Failed", "Failed to delete gift", err)
		return GiftResponse{
			Success: false,
			Message: "Erro interno do servidor ao deletar gift",
		}
	}

	services.LogSuccess(
		"Gift Deleted",
		fmt.Sprintf("Gift %s deleted", req.GiftID),
		map[string]string{"GiftID": req.GiftID},
	)

	return GiftResponse{
		Success: true,
		Message: "Gift deletado com sucesso",
		Data: map[string]interface{}{
			"deleted_gift": gift,
		},
	}
}

func HandleGetGifts(req GetGiftsRequest) GiftResponse {
	if req.BotID == "" {
		return GiftResponse{
			Success: false,
			Message: "Bot ID é obrigatório",
		}
	}

	gifts, err := database.DB.ReadGifts()
	if err != nil {
		services.LogError("Get Gifts Failed", "Failed to read gifts", err)
		return GiftResponse{
			Success: false,
			Message: "Erro interno do servidor ao listar gifts",
		}
	}

	botGifts := []database.Gift{}
	for _, gift := range gifts {
		if gift.BotID == req.BotID {
			botGifts = append(botGifts, gift)
		}
	}

	return GiftResponse{
		Success: true,
		Message: fmt.Sprintf("%d gifts encontrados", len(botGifts)),
		Data: map[string]interface{}{
			"gifts": botGifts,
		},
	}
}
