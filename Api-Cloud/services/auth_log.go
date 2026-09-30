package services

import "sync"

// AuthLogSender é uma função que envia auth_log para o socket de um bot específico.
// É registrada pelo main.go ao inicializar o servidor WebSocket.
var (
	authLogSender     func(botID string, data map[string]interface{})
	authLogSenderOnce sync.Once
	authLogMu         sync.RWMutex
)

// RegisterAuthLogSender registra a função que envia eventos para o bot via WebSocket.
// Deve ser chamado em main.go após inicializar o mapa botSockets.
func RegisterAuthLogSender(fn func(botID string, data map[string]interface{})) {
	authLogMu.Lock()
	defer authLogMu.Unlock()
	authLogSender = fn
}

// SendAuthLog envia um evento auth_log para o bot identificado por botID.
// Se o bot não estiver conectado via WebSocket, o envio é silenciosamente ignorado.
func SendAuthLog(botID string, data map[string]interface{}) {
	authLogMu.RLock()
	fn := authLogSender
	authLogMu.RUnlock()

	if fn != nil {
		go fn(botID, data)
	}
}
