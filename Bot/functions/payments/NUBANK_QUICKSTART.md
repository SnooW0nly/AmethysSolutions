# 🚀 Nubank IMAP - Guia Rápido de Início

## 📝 Resumo

Sistema de pagamento PIX via Nubank com **aprovação automática** através de monitoramento de emails via IMAP.

**Principais vantagens:**
- ✅ **100% Gratuito** - sem taxas por transação
- ✅ **Aprovação automática** - em até 2 minutos
- ✅ **Fácil configuração** - apenas 5 minutos
- ✅ **QR Code personalizado** - com logo e cores
- ✅ **TXID rastreável** - vinculado ao carrinho

---

## ⚡ Início Rápido (5 minutos)

### 1️⃣ Ativar Notificações no Nubank (2 min)

Abra o **app do Nubank**:
1. Toque no sino 🔔 (canto superior direito)
2. Entre em "Configurações" ⚙️
3. Ative "**Receber notificações por e-mail**" para Pix

### 2️⃣ Criar Senha de App no Gmail (2 min)

⚠️ **Pré-requisito:** Verificação em 2 etapas ativa

1. Acesse: https://myaccount.google.com/apppasswords
2. Escolha "**Outro (personalizado)**"
3. Digite um nome (ex: `BotPagamentos`)
4. Clique em "**Gerar**"
5. **Copie a senha de 16 dígitos** ⚠️ (só aparece uma vez!)

### 3️⃣ Configurar no Bot (1 min)

Execute o script de configuração:

```bash
cd bot-2/functions/payments
python nubank_setup.py setup
```

Ou configure manualmente via código:

```python
from functions.payments.nubank_setup import setup_nubank_imap

setup_nubank_imap(
    email="seuemail@gmail.com",          # Email do Nubank
    password="xxxx xxxx xxxx xxxx",      # Senha de app (16 dígitos)
    pix_key="suachave@pix.com",          # Sua chave PIX
    pix_key_type="email"                 # Tipo: email, cpf, cnpj, telefone, random
)
```

---

## 🧪 Testar Configuração

Execute o teste automático:

```bash
python test_nubank_imap.py
```

Ou teste rápido:

```bash
python test_nubank_imap.py --quick
```

---

## 💻 Usar no Código

### Criar Pagamento

```python
from functions.payments import create_nubank_imap_payment

payment = await create_nubank_imap_payment(
    amount=29.90,
    cart_id="CART12345",           # ID único do carrinho
    description="Produto XYZ"
)

# Retorna QR code e código PIX
print(payment['pix_copia_cola'])   # Código para copiar e colar
qr_bytes = payment['qr_code_bytes'] # QR code em bytes (PNG)
```

### Verificar Pagamento

```python
from functions.payments import check_nubank_imap_payment

status = await check_nubank_imap_payment("CART12345")

if status['status'] == 'approved':
    print("✅ Pago!")
    print(f"Valor: R$ {status['amount']:.2f}")
    print(f"Pagador: {status['payer_name']}")
```

### Monitorar Todos os Pagamentos

```python
from functions.payments import monitor_nubank_imap_payments

# Executar a cada 30 segundos
approved = await monitor_nubank_imap_payments()

for payment in approved:
    print(f"✅ Pagamento aprovado: {payment['cart_id']}")
    # Liberar produto/serviço aqui
```

---

## 🤖 Integrar com Discord Bot

### Setup Básico

```python
from discord.ext import commands, tasks
from functions.payments import create_nubank_imap_payment, monitor_nubank_imap_payments

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor_payments.start()  # Iniciar monitoramento
    
    @tasks.loop(seconds=30)
    async def monitor_payments(self):
        """Monitora pagamentos a cada 30 segundos"""
        approved = await monitor_nubank_imap_payments()
        
        for payment in approved:
            await self.deliver_product(payment['cart_id'])
    
    @commands.command()
    async def comprar(self, ctx, produto: str, valor: float):
        """Comando de compra"""
        cart_id = f"CART{ctx.author.id}{int(time.time())}"
        
        payment = await create_nubank_imap_payment(
            amount=valor,
            cart_id=cart_id,
            description=f"Compra: {produto}"
        )
        
        # Enviar QR code para o usuário
        await ctx.author.send(
            f"**PIX Gerado!**\nValor: R$ {valor:.2f}\n"
            f"```{payment['pix_copia_cola']}```"
        )
```

Veja exemplo completo em: `nubank_integration_example.py`

---

## 🔧 Comandos Úteis

### Ver Configuração Atual
```bash
python nubank_setup.py show
```

### Habilitar/Desabilitar
```bash
python nubank_setup.py enable
python nubank_setup.py disable
```

### Testar Conexão IMAP
```python
from functions.payments.test_nubank_imap import test_imap_connection
await test_imap_connection()
```

---

## 🔍 Como Funciona

```
1. Cliente solicita pagamento
   ↓
2. Bot gera QR Code PIX com TXID = cart_id
   ↓
3. Cliente paga via PIX
   ↓
4. Nubank envia email: "Você recebeu um Pix"
   ↓
5. Bot monitora IMAP a cada 30 segundos
   ↓
6. Bot detecta email e extrai TXID/valor
   ↓
7. Bot compara com pagamentos pendentes
   ↓
8. Se corresponder: aprova automaticamente!
   ↓
9. Sistema libera produto/serviço
```

---

## ❓ FAQ

### Por que usar IMAP ao invés de API?
- Nubank não tem API pública
- IMAP é gratuito e funciona para qualquer banco
- Aprovação automática sem custos

### Qual a latência média?
- **30 a 120 segundos** após o pagamento
- Depende do tempo de chegada do email

### É seguro?
- ✅ Usa senha de app (não expõe senha principal)
- ✅ Conexão SSL/TLS (criptografada)
- ✅ Validação dupla: TXID + valor
- ✅ Apenas emails do Nubank são processados

### Funciona com outros bancos?
Sim! Funciona com qualquer banco que:
- Envie notificações de PIX por email
- Inclua valor e/ou TXID no email

**Testado com:**
- ✅ Nubank
- ✅ Inter
- ✅ C6 Bank
- ⚠️ Outros bancos: teste antes de usar

### O que fazer se não detectar pagamento?
1. Verifique se notificações por email estão ativas
2. Confirme que a senha de app está correta
3. Aguarde até 2 minutos
4. Veja os logs para debug

---

## 📊 Comparação com Outros Métodos

| Método | Automático | Taxa | Setup | Latência |
|--------|-----------|------|-------|----------|
| **Nubank IMAP** | ✅ | 0% | 5 min | 30-120s |
| PIX Manual | ❌ | 0% | 2 min | Manual |
| Mercado Pago | ✅ | 4.99% | 10 min | Instantâneo |
| PagBank | ✅ | 3.99% | 15 min | Instantâneo |
| Asaas | ✅ | 1.99% | 20 min | Instantâneo |

---

## 🆘 Suporte

**Problemas comuns:**
- Email não detectado → Verifique notificações no Nubank
- Erro de login IMAP → Regenere senha de app
- Pagamento não aprovado → Verifique TXID nos logs

**Debug:**
```python
# Ativar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Precisa de ajuda?**
- 📖 Leia: `nubank_imap_readme.md` (documentação completa)
- 🔧 Execute: `python test_nubank_imap.py` (diagnóstico)
- 💬 Veja exemplos em: `nubank_integration_example.py`

---

## ✅ Checklist de Implementação

- [ ] Notificações por email ativadas no Nubank
- [ ] Senha de app criada no Gmail
- [ ] Configuração salva no database
- [ ] Testes executados com sucesso
- [ ] Monitoramento em background ativo
- [ ] Integração com sistema de vendas completa
- [ ] Logs e notificações configurados

---

**🎉 Pronto! Seu sistema de pagamentos está configurado!**

Faça um pagamento teste de **R$ 0,01** para validar tudo.

