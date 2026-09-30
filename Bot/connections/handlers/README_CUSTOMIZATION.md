# Módulo de Customização - WebSocket Integration

Documentação completa do módulo de Customização integrado via WebSocket.

## 📋 Visão Geral

O módulo de Customização permite controlar em tempo real todas as configurações de personalização do bot através da dashboard, incluindo:

- ✅ **Status do Bot** - Tipo e nomes rotativos
- ✅ **Cores Personalizadas** - Tema visual completo
- ✅ **Modo de Exibição** - Embed ou Components v2
- ✅ **Informações do Bot** - Dados configuráveis

## 🔧 Arquitetura

```
Dashboard → API Manager → WebSocket → Bot Handler → Database
                                          ↓
                                    Aplica Mudanças
                                          ↓
                                    Discord API
```

## 📁 Estrutura de Arquivos

### Bot (Python)
```
connections/handlers/
└── customization.py          # Handlers WebSocket (492 linhas)
    ├── Status Management     # 3 funções
    ├── Colors Management     # 4 funções
    ├── Display Mode          # 2 funções
    ├── Bot Information       # 2 funções
    ├── Complete Config       # 2 funções
    └── Reset Functions       # 2 funções
```

### API Manager (Node.js)
```
api-socket-manager/
├── core/functionMapper.js    # Mapeamento de funções
├── docs/CUSTOMIZATION_API.md # Documentação da API
└── test-customization.js     # Script de testes
```

## 🎯 Funções Disponíveis

### 1. Status Management

#### `customization.getStatus`
Obtém configuração atual do status do bot.

**Retorna:**
```python
{
    'config': {
        'type': 'online',
        'names': ['Sync Bot', 'Online 24/7']
    },
    'current': {
        'type': 'online',
        'activity': {
            'name': 'Sync Bot',
            'type': 'playing'
        }
    },
    'available_types': ['online', 'idle', 'dnd', 'streaming', 'offline']
}
```

#### `customization.updateStatus`
Atualiza tipo e nomes do status.

**Parâmetros:**
- `type` (string): Tipo do status
- `names` (list): Lista de nomes rotativos (máx 5)

**Exemplo:**
```python
{
    'type': 'dnd',
    'names': ['Sync Bot', 'Gerenciando', 'Online 24/7']
}
```

#### `customization.updateStatusNames`
Atualiza apenas os nomes rotativos.

**Parâmetros:**
- `names` (list): Lista de nomes

---

### 2. Colors Management

#### `customization.getColors`
Obtém cores personalizadas atuais.

**Retorna:**
```python
{
    'colors': {
        'primary': '#ffffff',
        'secondary': '#6c757d',
        'success': '#28a745',
        'danger': '#dc3545',
        'warning': '#ffc107'
    },
    'available_colors': ['primary', 'secondary', 'success', 'danger', 'warning']
}
```

#### `customization.updateColors`
Atualiza todas as cores.

**Parâmetros:**
- `colors` (dict): Objeto com todas as cores

**Validação:**
- Formato hexadecimal obrigatório: `#RRGGBB`
- Todas as cores são validadas
- Normalização automática

#### `customization.updateSingleColor`
Atualiza uma cor específica.

**Parâmetros:**
- `key` (string): Nome da cor
- `value` (string): Valor hexadecimal

#### `customization.resetColors`
Reseta todas as cores para o padrão.

---

### 3. Display Mode

#### `customization.getMode`
Obtém modo de exibição atual.

**Retorna:**
```python
{
    'mode': 'components',
    'available_modes': ['embed', 'components'],
    'description': {
        'embed': 'Classic embed mode with traditional Discord embeds',
        'components': 'Modern components v2 mode with containers'
    }
}
```

#### `customization.updateMode`
Altera o modo de exibição.

**Parâmetros:**
- `mode` (string): 'embed' ou 'components'

---

### 4. Bot Information

#### `customization.getInfo`
Obtém informações do bot.

**Retorna:**
```python
{
    'config': {},  # Configurações salvas
    'current': {   # Dados atuais do Discord
        'name': 'Sync Bot',
        'discriminator': '0000',
        'id': '1410764952142090365',
        'avatar': 'https://...',
        'bot': True
    }
}
```

#### `customization.updateInfo`
Atualiza informações configuráveis.

**Parâmetros:**
- `info` (dict): Objeto com informações

---

### 5. Complete Configuration

#### `customization.getAllConfig`
Obtém toda a configuração de uma vez.

**Retorna:**
```python
{
    'status': {...},
    'colors': {...},
    'mode': 'components',
    'info': {...}
}
```

#### `customization.updateAllConfig`
Atualiza múltiplas seções de uma vez.

**Parâmetros:**
- `config` (dict): Objeto com seções a atualizar

---

### 6. Reset Functions

#### `customization.resetColors`
Reseta apenas as cores.

#### `customization.resetAll`
Reseta toda a configuração para padrão.

---

## 💾 Persistência de Dados

### Documentos do Database

```python
# Status
db.get_document("custom_status")
{
    'type': 'online',
    'names': ['Sync Bot', 'Online 24/7']
}

# Colors
db.get_document("custom_colors")
{
    'primary': '#ffffff',
    'secondary': '#6c757d',
    'success': '#28a745',
    'danger': '#dc3545',
    'warning': '#ffc107'
}

# Mode
db.get_document("custom_mode")
{
    'mode': 'components'
}

# Info
db.get_document("custom_info")
{
    'description': '...',
    'version': '2.0.0'
}
```

---

## ⚡ Aplicação em Tempo Real

### Status
```python
# Após atualizar status
await core.change_status(bot)
```

Isso aplica imediatamente:
- Tipo de status (online, idle, dnd, etc)
- Nome da atividade (rotativo se múltiplos)
- Visível no Discord instantaneamente

### Colors
```python
# Cores são salvas no database
db.save_document("custom_colors", {}, validated_colors)
```

Afeta:
- Containers com `accent_colour`
- Embeds com `color`
- Todos os painéis do bot

### Mode
```python
# Modo é salvo e usado em todas as interações
db.save_document("custom_mode", {}, {'mode': mode})
```

Afeta:
- Como mensagens são renderizadas
- Embed vs Components v2
- Layout de todos os painéis

---

## 🔒 Validações

### Status
- ✅ Tipo deve ser válido: online, idle, dnd, streaming, offline
- ✅ Máximo 5 nomes rotativos
- ✅ Nomes vazios são filtrados automaticamente

### Colors
- ✅ Formato hexadecimal obrigatório: `#RRGGBB`
- ✅ Validação via regex: `^#?([0-9a-fA-F]{6})$`
- ✅ Normalização via `utils.normalize_hex_color()`
- ✅ Todas as cores devem ser válidas

### Mode
- ✅ Apenas 'embed' ou 'components'
- ✅ Validação case-sensitive

---

## 🧪 Testes

### Executar Testes
```bash
cd api-socket-manager
node test-customization.js
```

### Testes Incluídos
- ✅ Get/Update Status
- ✅ Get/Update Colors (todas e individual)
- ✅ Get/Update Mode
- ✅ Get/Update Info
- ✅ Get/Update All Config
- ✅ Reset Functions
- ✅ Validações de erro
- ✅ Limites e restrições

---

## 📚 Exemplos de Uso

### Via REST API

```javascript
const axios = require('axios');

// Atualizar status
await axios.post('https://cloud.syncapplications.com.br/api/functions/execute', {
  botId: 'SyncBot8',
  function: 'customization.updateStatus',
  params: {
    type: 'dnd',
    names: ['Sync Bot', 'Em manutenção']
  }
});

// Atualizar cor primária
await axios.post('https://cloud.syncapplications.com.br/api/functions/execute', {
  botId: 'SyncBot8',
  function: 'customization.updateSingleColor',
  params: {
    key: 'primary',
    value: '#ff0000'
  }
});

// Mudar para modo components
await axios.post('https://cloud.syncapplications.com.br/api/functions/execute', {
  botId: 'SyncBot8',
  function: 'customization.updateMode',
  params: {
    mode: 'components'
  }
});
```

### Via Dashboard (React/Next.js)

```typescript
// Hook personalizado
const useCustomization = (botId: string) => {
  const updateStatus = async (type: string, names: string[]) => {
    const response = await fetch('/api/bot/customization/status', {
      method: 'POST',
      body: JSON.stringify({ botId, type, names })
    });
    return response.json();
  };
  
  const updateColors = async (colors: Record<string, string>) => {
    const response = await fetch('/api/bot/customization/colors', {
      method: 'POST',
      body: JSON.stringify({ botId, colors })
    });
    return response.json();
  };
  
  return { updateStatus, updateColors };
};
```

---

## 🚨 Tratamento de Erros

Todos os erros retornam:
```python
{
    'error': 'Mensagem de erro descritiva',
    'status': 'error'
}
```

### Erros Comuns
- `status type is required` - Tipo não fornecido
- `Invalid status type` - Tipo inválido
- `Maximum 5 status names allowed` - Muitos nomes
- `Invalid hex color` - Formato de cor inválido
- `Invalid mode` - Modo inválido
- `Bot is offline` - Bot não conectado

---

## 📈 Performance

- ⚡ Respostas em < 100ms
- 💾 Persistência imediata no MongoDB
- 🔄 Aplicação em tempo real no Discord
- 📊 Sem cache (sempre dados atuais)

---

## 🔗 Links Úteis

- [Documentação API Completa](../../../api-socket-manager/docs/CUSTOMIZATION_API.md)
- [Script de Testes](../../../api-socket-manager/test-customization.js)
- [Function Mapper](../../../api-socket-manager/core/functionMapper.js)

---

**Última Atualização:** 2025-01-30  
**Versão:** 1.0.0  
**Status:** ✅ Produção
