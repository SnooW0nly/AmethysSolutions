package http

import (
	"amethys-api/database"
	"amethys-api/services"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"sync"
	"time"
)

type RedeemGiftRequest struct {
	GiftID      string `json:"giftId"`
	GuildID     string `json:"guildId"`
	Concurrency int    `json:"concurrency"`
	BaseDelayMs int    `json:"baseDelayMs"`
}

type RedeemGiftResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

func HandleRedeemGift(w http.ResponseWriter, r *http.Request) {
	ip := r.Header.Get("X-Forwarded-For")
	if ip == "" {
		ip = r.RemoteAddr
	}

	services.LogHTTPRequest(r.Method, r.URL.Path, ip, 200)

	var req RedeemGiftRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: "Invalid request body",
		})
		return
	}

	if req.GiftID == "" || req.GuildID == "" {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: "Gift ID e Guild ID são obrigatórios",
		})
		return
	}

	gift, err := database.DB.FindGiftByID(req.GiftID)
	if err != nil {
		respondJSON(w, 404, RedeemGiftResponse{
			Success: false,
			Message: "Gift não encontrado",
		})
		return
	}

	if gift.Status != "active" {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: "Este gift não está mais disponível",
		})
		return
	}

	if gift.UsedCount >= gift.MaxUses {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: "Este gift já foi usado o máximo de vezes",
		})
		return
	}

	bot, err := database.DB.FindBotByClientID(gift.BotID)
	if err != nil {
		respondJSON(w, 404, RedeemGiftResponse{
			Success: false,
			Message: "Bot associado ao gift não encontrado",
		})
		return
	}

	verifiedMembers := []database.Member{}
	for _, m := range bot.Members {
		if m.VerifiedAt != "" && m.AccessToken != "" {
			verifiedMembers = append(verifiedMembers, m)
		}
	}

	if len(verifiedMembers) < gift.MembersCount {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: fmt.Sprintf("Membros verificados insuficientes. Disponível: %d, Necessário: %d", len(verifiedMembers), gift.MembersCount),
		})
		return
	}

	if bot.Token == "" {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: "Token do bot não configurado",
		})
		return
	}

	concurrency := req.Concurrency
	if concurrency < 1 {
		concurrency = 3
	}
	if concurrency > 8 {
		concurrency = 8
	}

	baseDelayMs := req.BaseDelayMs
	if baseDelayMs < 0 {
		baseDelayMs = 0
	}
	if baseDelayMs > 1000 {
		baseDelayMs = 1000
	}

	results := processMembers(verifiedMembers, req.GuildID, bot.Token, gift.MembersCount, concurrency, baseDelayMs)

	added := []database.AddMemberResult{}
	skipped := []database.AddMemberResult{}
	failed := []database.AddMemberResult{}

	for _, r := range results {
		if r.Success {
			added = append(added, r)
		} else if r.Message == "AlreadyMember" {
			skipped = append(skipped, r)
		} else {
			failed = append(failed, r)
		}
	}

	if len(added) > 0 {
		gift.UsedCount++
		if gift.UsedCount >= gift.MaxUses {
			gift.Status = "used"
		}
		gift.LastUsed = time.Now()
		gift.LastGuildID = req.GuildID
		database.DB.UpdateGift(gift)

		services.LogSuccess(
			"Gift Redeemed",
			fmt.Sprintf("Gift %s redeemed - %d members added to guild %s", req.GiftID, len(added), req.GuildID),
			map[string]string{
				"GiftID":      req.GiftID,
				"GuildID":     req.GuildID,
				"AddedCount":  fmt.Sprintf("%d", len(added)),
				"FailedCount": fmt.Sprintf("%d", len(failed)),
			},
		)

		respondJSON(w, 200, RedeemGiftResponse{
			Success: true,
			Message: fmt.Sprintf("Gift resgatado. Adicionados: %d/%d.", len(added), gift.MembersCount),
			Data: map[string]interface{}{
				"added_count":                 len(added),
				"failed_count":                len(failed),
				"skipped_already_in_guild":    len(skipped),
				"failures":                    failed,
			},
		})
	} else {
		respondJSON(w, 400, RedeemGiftResponse{
			Success: false,
			Message: "Nenhum membro pôde ser adicionado agora. Tente novamente em alguns instantes.",
			Data: map[string]interface{}{
				"added_count":                 0,
				"failed_count":                len(failed),
				"skipped_already_in_guild":    len(skipped),
				"failures":                    failed,
			},
		})
	}
}

func processMembers(members []database.Member, guildID, botToken string, targetCount, concurrency, baseDelayMs int) []database.AddMemberResult {
	results := []database.AddMemberResult{}
	var resultsMutex sync.Mutex
	var addedCount int
	var index int
	var indexMutex sync.Mutex

	worker := func() {
		for {
			indexMutex.Lock()
			if addedCount >= targetCount {
				indexMutex.Unlock()
				return
			}
			currentIndex := index
			index++
			indexMutex.Unlock()

			if currentIndex >= len(members) {
				return
			}

			member := members[currentIndex]
			attempts := 0

			for {
				checkAttempts := 0
				var check bool
				var checkHeaders *database.RateLimitHeaders
				var checkErr error

				for {
					check, checkHeaders, checkErr = services.IsMemberInGuild(member.ID, guildID, botToken)
					if checkErr != nil && checkErr.Error() == "rate limited" && checkAttempts < 4 {
						waitMs := checkHeaders.ResetAfterMs
						if waitMs == 0 {
							waitMs = 2000
						}
						services.Sleep(int(float64(waitMs) * math.Pow(1.5, float64(checkAttempts))) + services.Jitter(100, 300))
						checkAttempts++
						continue
					}
					break
				}

				if check {
					resultsMutex.Lock()
					results = append(results, database.AddMemberResult{
						UserID:   member.ID,
						Username: member.Username,
						Success:  false,
						Message:  "AlreadyMember",
					})
					resultsMutex.Unlock()
					if baseDelayMs > 0 {
						services.Sleep(baseDelayMs + services.Jitter(50, 150))
					}
					break
				}

				indexMutex.Lock()
				if addedCount >= targetCount {
					indexMutex.Unlock()
					return
				}
				indexMutex.Unlock()

				result, headers, _ := services.AddMemberToGuild(member.AccessToken, member.ID, guildID, botToken)
				if result.Success {
					resultsMutex.Lock()
					result.UserID = member.ID
					result.Username = member.Username
					results = append(results, *result)
					resultsMutex.Unlock()

					indexMutex.Lock()
					addedCount++
					indexMutex.Unlock()

					if headers != nil && headers.Remaining == 0 && headers.ResetAfterMs > 0 {
						services.Sleep(headers.ResetAfterMs + services.Jitter(50, 150))
					} else if baseDelayMs > 0 {
						services.Sleep(baseDelayMs + services.Jitter(50, 150))
					}
					break
				}

				if result.Message == "RateLimited" && attempts < 4 {
					waitMs := 2000
					services.Sleep(int(float64(waitMs) * math.Pow(1.5, float64(attempts))) + services.Jitter(100, 300))
					attempts++
					continue
				}

				resultsMutex.Lock()
				result.UserID = member.ID
				result.Username = member.Username
				results = append(results, *result)
				resultsMutex.Unlock()

				if baseDelayMs > 0 {
					services.Sleep(baseDelayMs + services.Jitter(50, 150))
				}
				break
			}
		}
	}

	workerCount := concurrency
	if workerCount > len(members) {
		workerCount = len(members)
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

	log.Printf("Gift redemption complete: %d added, %d total results", addedCount, len(results))

	return results
}

func respondJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}
