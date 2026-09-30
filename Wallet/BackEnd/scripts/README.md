# Scripts de Administração

Scripts utilitários para gerenciar o sistema Amethys Wallet.

## set-admin.js

Script para definir um usuário como administrador.

### Uso

```bash
# Usando npm script (recomendado)
npm run set-admin 692dff925b3d26812a0b9315

# Ou diretamente com node
node scripts/set-admin.js 692dff925b3d26812a0b9315
```

### Parâmetros

- `<userId>` (opcional): ID do usuário a ser definido como admin. Se não fornecido, usa o ID padrão: `692dff925b3d26812a0b9315`

### Exemplo

```bash
# Definir usuário específico como admin
npm run set-admin 692dff925b3d26812a0b9315

# Usar o ID padrão
npm run set-admin
```

### O que o script faz

1. Conecta ao MongoDB usando as variáveis de ambiente do `.env`
2. Busca o usuário pelo ID fornecido
3. Verifica se o usuário já é admin
4. Define o campo `admin` como `true` se ainda não for admin
5. Salva as alterações no banco de dados
6. Exibe informações do usuário atualizado

### Requisitos

- Arquivo `.env` configurado com `MONGODB_URI`
- Usuário deve existir no banco de dados
- Conexão com MongoDB deve estar disponível

### Saída de Exemplo

```
🔌 Conectando ao MongoDB...
✅ Conectado ao MongoDB

🔍 Buscando usuário com ID: 692dff925b3d26812a0b9315
📋 Usuário encontrado:
   Nome: João Silva
   Email: joao@example.com
   Admin atual: Não

🔧 Definindo usuário como admin...
✅ Usuário definido como admin com sucesso!

📊 Informações atualizadas:
   Nome: João Silva
   Email: joao@example.com
   Admin: Sim
   Atualizado em: 2024-01-15T10:30:00.000Z

🔌 Desconectado do MongoDB
```

