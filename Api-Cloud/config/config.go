package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Port           string
	DiscordWebhook string
	RedirectURI    string
	DatabaseType   string
}

var AppConfig *Config

func LoadConfig() {
	godotenv.Load()

	AppConfig = &Config{
		Port:           getEnv("PORT", "8080"),
		DiscordWebhook: getEnv("DISCORD_WEBHOOK", ""),
		RedirectURI:    getEnv("REDIRECT_URI", ""),
		DatabaseType:   getEnv("DATABASE_TYPE", "json"),
	}

	if AppConfig.DiscordWebhook == "" {
		log.Println("WARNING: DISCORD_WEBHOOK not set, logs will not be sent to Discord")
	}
	if AppConfig.RedirectURI == "" {
		log.Println("WARNING: REDIRECT_URI not set")
	}
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
