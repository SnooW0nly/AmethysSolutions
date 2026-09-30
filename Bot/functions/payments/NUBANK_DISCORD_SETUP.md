# 🎮 Configurar Nubank IMAP no Discord

## 📋 Pré-requisitos

Antes de configurar no Discord, você precisa:

### 1. Ativar Notificações no Nubank
1. Abra o **app do Nubank**
2. Toque no ícone de sino 🔔 (canto superior direito)
3. Entre em **Configurações** ⚙️
4. Ative **"Receber notificações por e-mail"** para transferências Pix

### 2. Criar Senha de App no Gmail

⚠️ **Importante:** A verificação em 2 etapas deve estar ativa!

#### Ativar Verificação em 2 Etapas
1. Acesse: https://myaccount.google.com/security
2. Vá até **"Fazer login no Google"**
3. Clique em **Verificação em duas etapas** e ative

#### Gerar Senha de App
1. Acesse: https://myaccount.google.com/apppasswords
2. Em **Selecionar o app**, escolha **"Outro (personalizado)"**
3. Digite um nome, como: `BotPagamentos` ou `Discord Bot`
4. Clique em **Gerar**
5. **Copie a senha de 16 dígitos** (aparece apenas uma vez!)

Exemplo: `abcd efgh ijkl mnop` (16 dígitos separados por espaços)

---

## 🚀 Configurar no Discord

### Passo 1: Abrir Painel de Configurações

No Discord, execute o comando:
```
/panel
```

### Passo 2: Navegar até Pagamentos

1. Clique em **Configurações** ⚙️
2. Clique em **Formas de Pagamento** 💳
3. No seletor dropdown, escolha **"Configurar Nubank IMAP"**

### Passo 3: Preencher o Modal

Um formulário aparecerá com os seguintes campos:

#### 📝 Status do Provedor
- **Ativado** - O Nubank IMAP ficará ativo para pagamentos
- **Desativado** - Não será usado (mas mantém configuração salva)

⚠️ Só ative após preencher todos os outros campos!

#### 📧 Email do Gmail
- Digite o **email completo** usado no Nubank
- Exemplo: `seuemail@gmail.com`
- ⚠️ Deve ser o **mesmo email** cadastrado no app Nubank para receber notificações

#### 🔑 Senha de App do Gmail
- Cole a **senha de 16 dígitos** gerada anteriormente
- Exemplo: `abcd efgh ijkl mnop` ou `abcdefghijklmnop` (com ou sem espaços)
- ⚠️ NÃO use sua senha normal do Gmail!

#### 💳 Chave PIX
- Digite sua **chave PIX** que receberá os pagamentos
- Pode ser: Email, CPF, CNPJ, Telefone ou Aleatória
- Exemplo: `meupix@gmail.com` ou `12345678900`

#### 📋 Tipo da Chave PIX
Selecione o tipo correto da sua chave:
- **Email** 📧 - se é um endereço de email
- **CPF** 👤 - se é um CPF (11 dígitos)
- **CNPJ** 🏢 - se é um CNPJ (14 dígitos)
- **Telefone** 📱 - se é um número de telefone
- **Aleatória** 🔗 - se é uma chave aleatória (UUID)

### Passo 4: Enviar e Ativar

1. Preencha **todos os campos**
2. Selecione **Status: Ativado**
3. Clique em **Enviar**

---

## ✅ Validações Automáticas

O sistema valida automaticamente:

### Email do Gmail
- ✅ Formato válido de email
- ❌ Erro se formato incorreto

### Senha de App
- ✅ Deve ter exatamente **16 caracteres** (sem contar espaços)
- ❌ Erro se não tiver 16 dígitos

### Chave PIX (Email)
- ✅ Formato válido: `usuario@dominio.com`
- ❌ Erro se formato incorreto

### Chave PIX (CPF)
- ✅ 11 dígitos válidos com verificação de dígitos
- ❌ Erro se CPF inválido

### Chave PIX (CNPJ)
- ✅ 14 dígitos válidos com verificação de dígitos
- ❌ Erro se CNPJ inválido

### Chave PIX (Telefone)
- ✅ 10 ou 11 dígitos
- ❌ Erro se quantidade incorreta

### Chave PIX (Aleatória)
- ✅ Entre 8 e 50 caracteres
- ❌ Erro se fora do limite

---

## 🎯 Testando a Configuração

Após configurar, teste executando:

```bash
cd "C:\Users\souza\OneDrive\Documentos\Sync Projects\bot-2"
python functions/payments/test_nubank_standalone.py
```

O script irá:
1. ✅ Verificar se está configurado corretamente
2. ✅ Testar conexão IMAP com Gmail
3. ✅ Criar um pagamento de teste de R$ 0,01
4. ✅ Verificar se o QR Code foi gerado

---

## 🔍 Verificar Status no Painel

Após configurar, volte ao painel de pagamentos:

```
/panel → Configurações → Formas de Pagamento
```

O **Nubank IMAP** deve mostrar:
- ✅ **Status: Ativado** (se ativou)
- ⚙️ **Status: Desativado** (se desativou mas está configurado)
- ❌ **Status: Não Configurado** (se falta algum campo)

---

## 🔄 Como Funciona

Uma vez configurado e ativado:

1. **Cliente faz pedido** no seu sistema
2. **Bot gera QR Code PIX** com TXID único
3. **Cliente paga** via PIX escaneando o QR Code
4. **Nubank envia email** com notificação de recebimento
5. **Bot monitora o email** a cada 30 segundos via IMAP
6. **Bot detecta o pagamento** e extrai TXID/valor
7. **Bot aprova automaticamente** se corresponder
8. **Produto é liberado** para o cliente

**Latência:** 30 a 120 segundos após o pagamento

---

## 🚨 Problemas Comuns

### Email não está sendo detectado
✅ **Solução:** Verifique se as notificações por email estão ativas no app Nubank

### Erro: "Senha de app inválida"
✅ **Solução:** 
- Verifique se tem exatamente 16 dígitos (sem contar espaços)
- Regenere a senha em: https://myaccount.google.com/apppasswords
- Confirme que a verificação em 2 etapas está ativa

### Erro: "Email inválido"
✅ **Solução:** Use o formato completo: `seuemail@gmail.com`

### Erro: "Chave PIX inválida"
✅ **Solução:** 
- Verifique se selecionou o **tipo correto** de chave
- Remova formatação (pontos, hífens) ao digitar CPF/CNPJ
- Para telefone, use 10 ou 11 dígitos

### Não consigo ativar
✅ **Solução:** Preencha **todos os campos** antes de marcar como "Ativado"

---

## 📝 Dicas Importantes

1. **Use o mesmo email** do Nubank para receber notificações
2. **Não compartilhe** a senha de app com ninguém
3. **Teste primeiro** com um pagamento de R$ 0,01
4. **Monitore os logs** na primeira vez
5. **Chave PIX** deve ser a mesma que está no app Nubank

---

## 🔐 Segurança

- ✅ Senha de app **não expõe** sua senha principal
- ✅ Conexão **criptografada** (SSL/TLS)
- ✅ Validação **dupla**: TXID + valor
- ✅ Apenas emails **do Nubank** são processados
- ✅ Senhas **não aparecem** nos logs

---

## 📊 Exemplo de Configuração

```
Status do Provedor: Ativado ✅

Email do Gmail: meuemail@gmail.com

Senha de App: abcd efgh ijkl mnop

Chave PIX: meupix@gmail.com

Tipo da Chave PIX: Email 📧
```

Após enviar:
- ✅ **Configuração salva** no database
- ✅ **Nubank IMAP ativado** no painel
- ✅ **Pronto para receber** pagamentos

---

## 🆘 Precisa de Ajuda?

Se ainda tiver problemas:

1. Execute o teste: `python functions/payments/test_nubank_standalone.py`
2. Verifique a documentação completa: `nubank_imap_readme.md`
3. Veja exemplos de integração: `nubank_integration_example.py`

---

**✨ Configuração completa! Seu sistema está pronto para receber pagamentos PIX automaticamente via Nubank!**

