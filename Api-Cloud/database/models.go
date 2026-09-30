package database

import "time"

type Bot struct {
	ID           string                 `json:"id"`
	Token        string                 `json:"token"`
	ClientSecret string                 `json:"clientSecret"`
	ClientID     string                 `json:"clientId"`
	MainServerID string                 `json:"mainServerId,omitempty"`
	Members      []Member               `json:"members"`
	Definitions  map[string]interface{} `json:"definitions"`
}

type Member struct {
	ID            string `json:"id"`
	Username      string `json:"username"`
	Discriminator string `json:"discriminator"`
	Email         string `json:"email"`
	Avatar        string `json:"avatar,omitempty"` // campo adicionado (estava faltando vs JS)
	IP            string `json:"ip"`
	VerifiedAt    string `json:"verified_at,omitempty"`
	AccessToken   string `json:"access_token"`
	RefreshToken  string `json:"refresh_token"`
	GuildID       string `json:"guild_id,omitempty"`
	ClientID      string `json:"client_id,omitempty"`
	UnverifiedAt  string `json:"unverified_at,omitempty"`
	Reason        string `json:"reason,omitempty"`
}

type Gift struct {
	ID           string    `json:"id"`
	BotID        string    `json:"bot_id"`
	MembersCount int       `json:"members_count"`
	MaxUses      int       `json:"max_uses"`
	UsedCount    int       `json:"used_count"`
	Status       string    `json:"status"`
	CreatedBy    string    `json:"created_by"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedBy    string    `json:"updated_by,omitempty"`
	UpdatedAt    time.Time `json:"updated_at,omitempty"`
	LastUsed     time.Time `json:"last_used,omitempty"`
	LastGuildID  string    `json:"last_guild_id,omitempty"`
}

type DiscordUser struct {
	ID            string `json:"id"`
	Username      string `json:"username"`
	Discriminator string `json:"discriminator"`
	Avatar        string `json:"avatar"`
	Bot           bool   `json:"bot"`
	Email         string `json:"email,omitempty"`
	Verified      bool   `json:"verified,omitempty"` // campo adicionado para block_no_verified_email
}

type DiscordTokenResponse struct {
	AccessToken  string `json:"access_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int    `json:"expires_in"`
	RefreshToken string `json:"refresh_token"`
	Scope        string `json:"scope"`
}

type AddMemberResult struct {
	UserID   string `json:"userId"`
	Username string `json:"username"`
	Success  bool   `json:"success"`
	Message  string `json:"message"`
}

type RateLimitHeaders struct {
	Remaining    int
	ResetAfterMs int
}

// RecoveryStatus representa o estado de um processo de recuperação em andamento
type RecoveryStatus struct {
	Status                  string        `json:"status"`
	ClientID                string        `json:"client_id"`
	ServerID                string        `json:"server_id"`
	TotalMembers            int           `json:"total_members"`
	ProcessedMembers        int           `json:"processed_members"`
	FailedMembers           int           `json:"failed_members"`
	SkippedAlreadyInGuild   int           `json:"skipped_already_in_guild"`
	Failures                []RecoveryFailure `json:"failures"`
	StartedAt               int64         `json:"started_at"`
	EstimatedCompletion     int64         `json:"estimated_completion"`
	EstimatedTime           string        `json:"estimated_time"`
	LastProcessedMember     string        `json:"last_processed_member"`
	Error                   string        `json:"error,omitempty"`
}

type RecoveryFailure struct {
	Username string `json:"username"`
	UserID   string `json:"userId"`
	Reason   string `json:"reason"`
}
