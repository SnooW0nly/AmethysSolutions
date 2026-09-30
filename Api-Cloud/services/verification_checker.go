package services

import (
	"amethys-api/database"
	"fmt"
	"log"
	"sync"
	"time"
)

// How often the checker runs.  The original value (5 s) made a Discord API
// call for every member every 5 seconds, which causes rate-limiting and
// incorrectly removes freshly-verified members when Discord returns a 429.
// 1 hour is a safe baseline; increase if you have many members.
const verificationCheckInterval = 1 * time.Hour

// Minimum time a member must have been verified before we bother checking
// their token.  This prevents newly-verified members from being removed if
// the checker happens to run right after they verified.
const minVerificationAge = 30 * time.Minute

type ConnectedBot struct {
	ClientID  string
	LastCheck time.Time
}

var (
	connectedBots = make(map[string]*ConnectedBot)
	botsMutex     sync.RWMutex
	ticker        *time.Ticker
	stopChan      chan bool
)

func RegisterBot(botID, clientID string) {
	botsMutex.Lock()
	defer botsMutex.Unlock()

	connectedBots[botID] = &ConnectedBot{
		ClientID:  clientID,
		LastCheck: time.Now(),
	}

	log.Printf("Bot registered for verification: %s (ClientID: %s)", botID, clientID)
	log.Printf("Total connected bots: %d", len(connectedBots))
}

func UnregisterBot(botID string) {
	botsMutex.Lock()
	defer botsMutex.Unlock()

	delete(connectedBots, botID)
	log.Printf("Bot removed from verification: %s", botID)
}

func StartVerificationChecker(notifyFunc func(string, []database.Member)) {
	if ticker != nil {
		return
	}

	ticker = time.NewTicker(verificationCheckInterval)
	stopChan = make(chan bool)

	go func() {
		for {
			select {
			case <-ticker.C:
				performVerificationCheck(notifyFunc)
			case <-stopChan:
				ticker.Stop()
				return
			}
		}
	}()

	log.Printf("Verification checker started (interval: %s)", verificationCheckInterval)
}

func StopVerificationChecker() {
	if ticker != nil {
		stopChan <- true
		ticker = nil
		log.Println("Verification checker stopped")
	}
}

func performVerificationCheck(notifyFunc func(string, []database.Member)) {
	botsMutex.RLock()
	botsToCheck := make(map[string]*ConnectedBot)
	for k, v := range connectedBots {
		botsToCheck[k] = v
	}
	botsMutex.RUnlock()

	for botID, botInfo := range botsToCheck {
		checkBotMembers(botID, botInfo.ClientID, notifyFunc)
	}
}

func checkBotMembers(botID, clientID string, notifyFunc func(string, []database.Member)) {
	bot, err := database.DB.FindBotByClientID(clientID)
	if err != nil || bot == nil || len(bot.Members) == 0 {
		return
	}

	unverifiedMembers := []database.Member{}
	cutoff := time.Now().Add(-minVerificationAge)

	for _, member := range bot.Members {
		if member.AccessToken == "" {
			continue
		}

		// Skip members that verified very recently to avoid incorrectly
		// evicting them if Discord temporarily rate-limits us.
		if member.VerifiedAt != "" {
			verifiedAt, parseErr := time.Parse(time.RFC3339, member.VerifiedAt)
			if parseErr == nil && verifiedAt.After(cutoff) {
				log.Printf("[CHECKER] Skipping recently-verified member %s (verified %s ago)",
					member.Username, time.Since(verifiedAt).Round(time.Second))
				continue
			}
		}

		invalid, temporary, checkErr := CheckTokenStatus(member.AccessToken)
		if temporary {
			// Erro de rede, rate-limit ou 5xx — não remove, tenta na próxima rodada.
			log.Printf("[CHECKER] Erro temporário ao verificar %s (%s): %v — pulando",
				member.Username, member.ID, checkErr)
			time.Sleep(500 * time.Millisecond)
			continue
		}

		if invalid {
			// Token rejeitado pelo Discord. Tenta renovar via refresh_token antes de remover.
			if member.RefreshToken != "" {
				newTokens, refreshErr := RefreshAccessToken(member.RefreshToken, bot.ClientID, bot.ClientSecret)
				if refreshErr == nil && newTokens != nil {
					// Refresh funcionou — atualiza tokens no slice e salva.
					for i := range bot.Members {
						if bot.Members[i].ID == member.ID {
							bot.Members[i].AccessToken = newTokens.AccessToken
							bot.Members[i].RefreshToken = newTokens.RefreshToken
							break
						}
					}
					if dbErr := database.DB.UpdateBot(bot); dbErr != nil {
						log.Printf("[CHECKER] Falha ao salvar tokens renovados de %s: %v", member.Username, dbErr)
					} else {
						log.Printf("[CHECKER] Token renovado com sucesso para %s (%s)", member.Username, member.ID)
					}
					time.Sleep(500 * time.Millisecond)
					continue
				}
				log.Printf("[CHECKER] Refresh falhou para %s (%s): %v — removendo", member.Username, member.ID, refreshErr)
			}

			member.UnverifiedAt = time.Now().Format(time.RFC3339)
			member.Reason = "Token invalid or expired"
			unverifiedMembers = append(unverifiedMembers, member)
			log.Printf("[CHECKER] Member unverified: %s (%s) – %s",
				member.Username, member.ID, member.Reason)
		}

		// Small sleep between API calls to avoid hitting Discord rate limits.
		time.Sleep(500 * time.Millisecond)
	}

	if len(unverifiedMembers) == 0 {
		return
	}

	// Remove unverified members from the database.
	unverifiedIDs := make(map[string]struct{}, len(unverifiedMembers))
	for _, m := range unverifiedMembers {
		unverifiedIDs[m.ID] = struct{}{}
	}

	newMembers := bot.Members[:0]
	for _, m := range bot.Members {
		if _, bad := unverifiedIDs[m.ID]; !bad {
			newMembers = append(newMembers, m)
		}
	}

	bot.Members = newMembers
	if dbErr := database.DB.UpdateBot(bot); dbErr != nil {
		log.Printf("[CHECKER] Failed to update bot %s after removing unverified members: %v", clientID, dbErr)
		return
	}

	if notifyFunc != nil {
		notifyFunc(botID, unverifiedMembers)
	}

	log.Printf("[CHECKER] %d unverified member(s) removed from bot %s", len(unverifiedMembers), clientID)
}

func CheckUserVerification(botID, userID string) (bool, error) {
	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil || bot == nil {
		return false, nil
	}

	for _, member := range bot.Members {
		if member.ID == userID && member.VerifiedAt != "" {
			return true, nil
		}
	}

	return false, nil
}

func UpdateBotDefinitions(botID string, definitions map[string]interface{}, mainServerID string) error {
	bot, err := database.DB.FindBotByClientID(botID)
	if err != nil {
		return fmt.Errorf("bot not found: %s", botID)
	}

	bot.Definitions = definitions
	if mainServerID != "" {
		bot.MainServerID = mainServerID
	}

	return database.DB.UpdateBot(bot)
}