package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"amethys-api/config"
)

type DiscordEmbed struct {
	Title       string                 `json:"title,omitempty"`
	Description string                 `json:"description,omitempty"`
	Color       int                    `json:"color,omitempty"`
	Fields      []DiscordEmbedField    `json:"fields,omitempty"`
	Footer      *DiscordEmbedFooter    `json:"footer,omitempty"`
	Timestamp   string                 `json:"timestamp,omitempty"`
}

type DiscordEmbedField struct {
	Name   string `json:"name"`
	Value  string `json:"value"`
	Inline bool   `json:"inline,omitempty"`
}

type DiscordEmbedFooter struct {
	Text string `json:"text"`
}

type DiscordWebhookPayload struct {
	Content string         `json:"content,omitempty"`
	Embeds  []DiscordEmbed `json:"embeds,omitempty"`
}

func LogToDiscord(title, description string, fields map[string]string, color int) {
	if config.AppConfig.DiscordWebhook == "" {
		return
	}

	embedFields := make([]DiscordEmbedField, 0)
	for k, v := range fields {
		embedFields = append(embedFields, DiscordEmbedField{
			Name:   k,
			Value:  v,
			Inline: true,
		})
	}

	embed := DiscordEmbed{
		Title:       title,
		Description: description,
		Color:       color,
		Fields:      embedFields,
		Footer: &DiscordEmbedFooter{
			Text: "Amethys API",
		},
		Timestamp: time.Now().Format(time.RFC3339),
	}

	payload := DiscordWebhookPayload{
		Embeds: []DiscordEmbed{embed},
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return
	}

	go func() {
		client := &http.Client{Timeout: 10 * time.Second}
		req, err := http.NewRequest("POST", config.AppConfig.DiscordWebhook, bytes.NewBuffer(jsonData))
		if err != nil {
			return
		}
		req.Header.Set("Content-Type", "application/json")
		client.Do(req)
	}()
}

func LogHTTPRequest(method, path, ip string, statusCode int) {
	color := 3066993
	if statusCode >= 400 && statusCode < 500 {
		color = 15844367
	} else if statusCode >= 500 {
		color = 15158332
	}

	LogToDiscord(
		fmt.Sprintf("HTTP %s %s", method, path),
		fmt.Sprintf("Status: %d", statusCode),
		map[string]string{
			"IP":     ip,
			"Method": method,
			"Path":   path,
		},
		color,
	)
}

func LogWebSocketEvent(event, clientID, message string) {
	LogToDiscord(
		fmt.Sprintf("WebSocket: %s", event),
		message,
		map[string]string{
			"Event":     event,
			"Client ID": clientID,
		},
		5793266,
	)
}

func LogError(title, description string, err error) {
	fields := make(map[string]string)
	if err != nil {
		fields["Error"] = err.Error()
	}

	LogToDiscord(
		title,
		description,
		fields,
		15158332,
	)
}

func LogSuccess(title, description string, fields map[string]string) {
	LogToDiscord(
		title,
		description,
		fields,
		3066993,
	)
}
