package database

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sync"
)

type JSONStore struct {
	dataDir   string
	botsMutex sync.RWMutex
	giftMutex sync.RWMutex

	// Cache em memória — evita leituras de disco repetidas durante a conexão
	// do bot (register + bot_connected chegam em sequência e liam o arquivo 3-4x).
	botsCache     []Bot
	botsCacheValid bool
}

func NewJSONStore(dataDir string) *JSONStore {
	os.MkdirAll(dataDir, 0755)
	return &JSONStore{dataDir: dataDir}
}

func (s *JSONStore) botsPath() string {
	return filepath.Join(s.dataDir, "bots.json")
}

func (s *JSONStore) giftsPath() string {
	return filepath.Join(s.dataDir, "gifts.json")
}

func (s *JSONStore) ReadBots() ([]Bot, error) {
	s.botsMutex.RLock()
	if s.botsCacheValid {
		out := make([]Bot, len(s.botsCache))
		copy(out, s.botsCache)
		s.botsMutex.RUnlock()
		return out, nil
	}
	s.botsMutex.RUnlock()

	// Cache miss — lê do disco com write lock para popular o cache.
	s.botsMutex.Lock()
	defer s.botsMutex.Unlock()

	// Double-check após adquirir write lock.
	if s.botsCacheValid {
		out := make([]Bot, len(s.botsCache))
		copy(out, s.botsCache)
		return out, nil
	}

	data, err := os.ReadFile(s.botsPath())
	if err != nil {
		if os.IsNotExist(err) {
			s.botsCache = []Bot{}
			s.botsCacheValid = true
			return []Bot{}, nil
		}
		return nil, err
	}

	var bots []Bot
	if err := json.Unmarshal(data, &bots); err != nil {
		bots = []Bot{}
	}

	s.botsCache = bots
	s.botsCacheValid = true

	out := make([]Bot, len(bots))
	copy(out, bots)
	return out, nil
}

func (s *JSONStore) WriteBots(bots []Bot) error {
	s.botsMutex.Lock()
	defer s.botsMutex.Unlock()

	data, err := json.MarshalIndent(bots, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(s.botsPath(), data, 0644); err != nil {
		return err
	}

	// Atualiza o cache após escrita bem-sucedida.
	s.botsCache = make([]Bot, len(bots))
	copy(s.botsCache, bots)
	s.botsCacheValid = true

	return nil
}

func (s *JSONStore) FindBotByClientID(clientID string) (*Bot, error) {
	bots, err := s.ReadBots()
	if err != nil {
		return nil, err
	}

	for i := range bots {
		if bots[i].ClientID == clientID {
			return &bots[i], nil
		}
	}

	return nil, errors.New("bot not found")
}

func (s *JSONStore) FindBotByID(botID string) (*Bot, error) {
	bots, err := s.ReadBots()
	if err != nil {
		return nil, err
	}

	for i := range bots {
		if bots[i].ID == botID {
			return &bots[i], nil
		}
	}

	return nil, errors.New("bot not found")
}

func (s *JSONStore) UpdateBot(bot *Bot) error {
	s.botsMutex.Lock()
	defer s.botsMutex.Unlock()

	// Usa o cache se válido; caso contrário lê do disco sem o lock (já temos write lock).
	var bots []Bot
	if s.botsCacheValid {
		bots = make([]Bot, len(s.botsCache))
		copy(bots, s.botsCache)
	} else {
		data, err := os.ReadFile(s.botsPath())
		if err != nil {
			if os.IsNotExist(err) {
				return errors.New("bot not found")
			}
			return err
		}
		if err := json.Unmarshal(data, &bots); err != nil {
			return err
		}
	}

	found := false
	for i := range bots {
		if bots[i].ClientID == bot.ClientID {
			bots[i] = *bot
			found = true
			break
		}
	}

	if !found {
		return errors.New("bot not found")
	}

	data, err := json.MarshalIndent(bots, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(s.botsPath(), data, 0644); err != nil {
		return err
	}

	s.botsCache = make([]Bot, len(bots))
	copy(s.botsCache, bots)
	s.botsCacheValid = true

	return nil
}

func (s *JSONStore) ReadGifts() ([]Gift, error) {
	s.giftMutex.RLock()
	defer s.giftMutex.RUnlock()

	data, err := os.ReadFile(s.giftsPath())
	if err != nil {
		if os.IsNotExist(err) {
			return []Gift{}, nil
		}
		return nil, err
	}

	var gifts []Gift
	if err := json.Unmarshal(data, &gifts); err != nil {
		return []Gift{}, nil
	}

	return gifts, nil
}

func (s *JSONStore) WriteGifts(gifts []Gift) error {
	s.giftMutex.Lock()
	defer s.giftMutex.Unlock()

	data, err := json.MarshalIndent(gifts, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(s.giftsPath(), data, 0644)
}

func (s *JSONStore) FindGiftByID(giftID string) (*Gift, error) {
	gifts, err := s.ReadGifts()
	if err != nil {
		return nil, err
	}

	for i := range gifts {
		if gifts[i].ID == giftID {
			return &gifts[i], nil
		}
	}

	return nil, errors.New("gift not found")
}

func (s *JSONStore) AddGift(gift *Gift) error {
	gifts, err := s.ReadGifts()
	if err != nil {
		return err
	}

	gifts = append(gifts, *gift)
	return s.WriteGifts(gifts)
}

func (s *JSONStore) UpdateGift(gift *Gift) error {
	gifts, err := s.ReadGifts()
	if err != nil {
		return err
	}

	for i := range gifts {
		if gifts[i].ID == gift.ID {
			gifts[i] = *gift
			return s.WriteGifts(gifts)
		}
	}

	return errors.New("gift not found")
}

func (s *JSONStore) DeleteGift(giftID string) error {
	gifts, err := s.ReadGifts()
	if err != nil {
		return err
	}

	for i := range gifts {
		if gifts[i].ID == giftID {
			gifts = append(gifts[:i], gifts[i+1:]...)
			return s.WriteGifts(gifts)
		}
	}

	return errors.New("gift not found")
}
