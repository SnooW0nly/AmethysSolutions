package database

type Store interface {
	ReadBots() ([]Bot, error)
	WriteBots(bots []Bot) error
	FindBotByClientID(clientID string) (*Bot, error)
	FindBotByID(botID string) (*Bot, error)
	UpdateBot(bot *Bot) error
	
	ReadGifts() ([]Gift, error)
	WriteGifts(gifts []Gift) error
	FindGiftByID(giftID string) (*Gift, error)
	AddGift(gift *Gift) error
	UpdateGift(gift *Gift) error
	DeleteGift(giftID string) error
}

var DB Store

func InitStore(storeType string) error {
	switch storeType {
	case "json":
		DB = NewJSONStore("./data")
		return nil
	default:
		DB = NewJSONStore("./data")
		return nil
	}
}
