package services

import (
	"amethys-api/database"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"math/rand"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

var httpClient = &http.Client{
	Timeout: 30 * time.Second,
	Transport: &http.Transport{
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 100,
		IdleConnTimeout:     90 * time.Second,
	},
}

const discordAPIBase = "https://discord.com/api/v10"

func GetDiscordUser(accessToken string) (*database.DiscordUser, error) {
	req, err := http.NewRequest("GET", discordAPIBase+"/users/@me", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("discord API returned status %d", resp.StatusCode)
	}

	var user database.DiscordUser
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, err
	}

	return &user, nil
}

// RefreshAccessToken usa o refresh_token para obter novos tokens do Discord.
func RefreshAccessToken(refreshToken, clientID, clientSecret string) (*database.DiscordTokenResponse, error) {
	formData := url.Values{}
	formData.Set("client_id", clientID)
	formData.Set("client_secret", clientSecret)
	formData.Set("grant_type", "refresh_token")
	formData.Set("refresh_token", refreshToken)

	req, err := http.NewRequest("POST", discordAPIBase+"/oauth2/token", bytes.NewBufferString(formData.Encode()))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("refresh failed (status %d): %s", resp.StatusCode, string(body))
	}

	var tokenResp database.DiscordTokenResponse
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return nil, err
	}
	return &tokenResp, nil
}

// CheckTokenStatus verifica se o token é definitivamente inválido.
// Retorna (invalid bool, temporary bool, err).
// - invalid=true  → token rejeitado pelo Discord (401/403), pode tentar refresh.
// - temporary=true → erro de rede, rate-limit ou 5xx; não remover o membro.
func CheckTokenStatus(accessToken string) (invalid bool, temporary bool, err error) {
	req, err := http.NewRequest("GET", discordAPIBase+"/users/@me", nil)
	if err != nil {
		return false, true, err
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)

	resp, err := httpClient.Do(req)
	if err != nil {
		return false, true, err // erro de rede — temporário
	}
	defer resp.Body.Close()

	switch resp.StatusCode {
	case 200:
		return false, false, nil // token ok
	case 401, 403:
		return true, false, nil // definitivamente inválido
	default:
		// 429, 500, 503, etc — temporário, não remover
		return false, true, fmt.Errorf("status temporário %d", resp.StatusCode)
	}
}

func GetBotUser(botToken string) (*database.DiscordUser, error) {
	req, err := http.NewRequest("GET", discordAPIBase+"/users/@me", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bot "+botToken)

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("discord API returned status %d", resp.StatusCode)
	}

	var user database.DiscordUser
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, err
	}

	return &user, nil
}

// ExchangeCode troca o authorization code por tokens de acesso.
// IMPORTANTE: a API do Discord exige Content-Type: application/x-www-form-urlencoded.
// Enviar JSON resulta em erro 400 "unsupported_grant_type" ou resposta inválida.
func ExchangeCode(code, clientID, clientSecret, redirectURI string) (*database.DiscordTokenResponse, error) {
	formData := url.Values{}
	formData.Set("client_id", clientID)
	formData.Set("client_secret", clientSecret)
	formData.Set("grant_type", "authorization_code")
	formData.Set("code", code)
	formData.Set("redirect_uri", redirectURI)

	req, err := http.NewRequest("POST", discordAPIBase+"/oauth2/token", bytes.NewBufferString(formData.Encode()))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("token exchange failed (status %d): %s", resp.StatusCode, string(body))
	}

	var tokenResp database.DiscordTokenResponse
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return nil, err
	}

	return &tokenResp, nil
}

func IsMemberInGuild(userID, guildID, botToken string) (bool, *database.RateLimitHeaders, error) {
	req, err := http.NewRequest("GET", fmt.Sprintf("%s/guilds/%s/members/%s", discordAPIBase, guildID, userID), nil)
	if err != nil {
		return false, nil, err
	}
	req.Header.Set("Authorization", "Bot "+botToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return false, nil, err
	}
	defer resp.Body.Close()

	headers := parseRateLimitHeaders(resp.Header)

	if resp.StatusCode == 200 {
		return true, headers, nil
	}

	if resp.StatusCode == 404 {
		return false, headers, nil
	}

	if resp.StatusCode == 429 {
		retryAfter := parseRetryAfter(resp.Header)
		return false, &database.RateLimitHeaders{ResetAfterMs: retryAfter}, fmt.Errorf("rate limited")
	}

	return false, headers, fmt.Errorf("status %d", resp.StatusCode)
}

func AddMemberToGuild(accessToken, userID, guildID, botToken string) (*database.AddMemberResult, *database.RateLimitHeaders, error) {
	data := map[string]string{"access_token": accessToken}
	jsonData, _ := json.Marshal(data)

	req, err := http.NewRequest("PUT", fmt.Sprintf("%s/guilds/%s/members/%s", discordAPIBase, guildID, userID), bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, nil, err
	}
	req.Header.Set("Authorization", "Bot "+botToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, nil, err
	}
	defer resp.Body.Close()

	headers := parseRateLimitHeaders(resp.Header)

	if resp.StatusCode == 201 || resp.StatusCode == 204 {
		return &database.AddMemberResult{Success: true, Message: "Success"}, headers, nil
	}

	if resp.StatusCode == 429 {
		retryAfter := parseRetryAfter(resp.Header)
		return &database.AddMemberResult{Success: false, Message: "RateLimited"}, &database.RateLimitHeaders{ResetAfterMs: retryAfter}, nil
	}

	if resp.StatusCode == 403 {
		return &database.AddMemberResult{Success: false, Message: "Forbidden"}, headers, nil
	}

	if resp.StatusCode == 400 {
		return &database.AddMemberResult{Success: false, Message: "BadRequest"}, headers, nil
	}

	body, _ := io.ReadAll(resp.Body)
	return &database.AddMemberResult{Success: false, Message: string(body)}, headers, nil
}

func parseRateLimitHeaders(header http.Header) *database.RateLimitHeaders {
	remaining, _ := strconv.Atoi(header.Get("X-RateLimit-Remaining"))
	resetAfter, _ := strconv.ParseFloat(header.Get("X-RateLimit-Reset-After"), 64)
	resetAfterMs := int(math.Ceil(resetAfter * 1000))

	return &database.RateLimitHeaders{
		Remaining:    remaining,
		ResetAfterMs: resetAfterMs,
	}
}

func parseRetryAfter(header http.Header) int {
	retryAfter, _ := strconv.ParseFloat(header.Get("Retry-After"), 64)
	if retryAfter == 0 {
		retryAfter, _ = strconv.ParseFloat(header.Get("X-RateLimit-Reset-After"), 64)
	}
	if retryAfter == 0 {
		retryAfter = 2
	}
	return int(math.Ceil(retryAfter * 1000))
}

func Sleep(ms int) {
	time.Sleep(time.Duration(ms) * time.Millisecond)
}

func Jitter(min, max int) int {
	return rand.Intn(max-min+1) + min
}