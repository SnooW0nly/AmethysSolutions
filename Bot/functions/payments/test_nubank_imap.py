"""
Script de teste para o sistema Nubank IMAP
Execute este arquivo para testar a configuração e funcionalidades
"""
import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports funcionarem
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from functions.payments.imap_nubank import (
    create_nubank_imap_payment,
    check_nubank_imap_payment,
    monitor_nubank_imap_payments
)
from functions.database import database as db


async def test_configuration():
    """Testa se a configuração está correta"""
    print("\n" + "="*60)
    print("🔧 TESTE DE CONFIGURAÇÃO")
    print("="*60)
    
    config = db.get_document("payment_configs") or {}
    nubank_config = config.get("nubank_imap", {})
    
    print(f"\n✓ Configuração encontrada")
    print(f"  - Habilitado: {nubank_config.get('enabled')}")
    print(f"  - Email: {nubank_config.get('email')}")
    print(f"  - Senha configurada: {'Sim' if nubank_config.get('password') else 'Não'}")
    print(f"  - Chave PIX: {nubank_config.get('pix_key')}")
    print(f"  - Tipo de chave: {nubank_config.get('pix_key_type')}")
    
    if not nubank_config.get("enabled"):
        print("\n❌ ERRO: Nubank IMAP não está habilitado!")
        print("   Configure no database: payment_configs.nubank_imap.enabled = true")
        return False
    
    if not nubank_config.get("email"):
        print("\n❌ ERRO: Email não configurado!")
        return False
    
    if not nubank_config.get("password"):
        print("\n❌ ERRO: Senha de app não configurada!")
        return False
    
    if not nubank_config.get("pix_key"):
        print("\n❌ ERRO: Chave PIX não configurada!")
        return False
    
    print("\n✅ Configuração válida!")
    return True


async def test_create_payment():
    """Testa a criação de um pagamento"""
    print("\n" + "="*60)
    print("💳 TESTE DE CRIAÇÃO DE PAGAMENTO")
    print("="*60)
    
    try:
        # Criar pagamento de teste
        payment = await create_nubank_imap_payment(
            amount=0.01,  # R$ 0,01 para teste
            cart_id="TEST123456",
            description="Pagamento de Teste",
            merchant_name="Loja Teste",
            merchant_city="Sao Paulo"
        )
        
        print(f"\n✅ Pagamento criado com sucesso!")
        print(f"\n📋 Detalhes do pagamento:")
        print(f"  - ID: {payment['payment_id']}")
        print(f"  - Valor: R$ {payment['amount']:.2f}")
        print(f"  - Status: {payment['status']}")
        print(f"  - Chave PIX: {payment['pix_key']}")
        print(f"\n📱 Código PIX (primeiros 50 chars):")
        print(f"  {payment['pix_copia_cola'][:50]}...")
        print(f"\n🖼️  QR Code gerado: {len(payment['qr_code_bytes'])} bytes")
        
        return payment['payment_id']
    
    except Exception as e:
        print(f"\n❌ Erro ao criar pagamento: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_check_payment(payment_id: str):
    """Testa a verificação de status de um pagamento"""
    print("\n" + "="*60)
    print("🔍 TESTE DE VERIFICAÇÃO DE PAGAMENTO")
    print("="*60)
    
    try:
        status = await check_nubank_imap_payment(payment_id)
        
        print(f"\n✅ Verificação concluída!")
        print(f"\n📊 Status:")
        print(f"  - Payment ID: {status['payment_id']}")
        print(f"  - Status: {status['status']}")
        
        if status['status'] == 'approved':
            print(f"  - Aprovado em: {status.get('approved_at')}")
            print(f"  - Pagador: {status.get('payer_name', 'N/A')}")
            print(f"  - Valor: R$ {status.get('amount', 0):.2f}")
        else:
            print(f"  - Aguardando pagamento...")
        
        return status
    
    except Exception as e:
        print(f"\n❌ Erro ao verificar pagamento: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_monitor_payments():
    """Testa o monitoramento de pagamentos"""
    print("\n" + "="*60)
    print("👁️  TESTE DE MONITORAMENTO DE PAGAMENTOS")
    print("="*60)
    
    try:
        print("\n🔄 Verificando emails...")
        approved = await monitor_nubank_imap_payments()
        
        if not approved:
            print(f"\n✓ Nenhum pagamento novo detectado")
        else:
            print(f"\n✅ {len(approved)} pagamento(s) aprovado(s)!")
            for payment in approved:
                print(f"\n  💰 Pagamento #{payment['payment_id']}")
                print(f"     - Carrinho: {payment['cart_id']}")
                print(f"     - Valor: R$ {payment['amount']:.2f}")
                print(f"     - Pagador: {payment.get('payer_name', 'N/A')}")
                print(f"     - Aprovado: {payment['approved_at']}")
        
        return approved
    
    except Exception as e:
        print(f"\n❌ Erro ao monitorar pagamentos: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_imap_connection():
    """Testa a conexão IMAP diretamente"""
    print("\n" + "="*60)
    print("🔌 TESTE DE CONEXÃO IMAP")
    print("="*60)
    
    try:
        import imaplib
        config = db.get_document("payment_configs") or {}
        nubank_config = config.get("nubank_imap", {})
        
        email_address = nubank_config.get("email")
        password = nubank_config.get("password")
        
        print(f"\n🔄 Conectando ao Gmail...")
        print(f"   Email: {email_address}")
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_address, password)
        
        print(f"✅ Conexão estabelecida com sucesso!")
        
        # Selecionar inbox
        mail.select("inbox")
        
        # Contar emails
        status, messages = mail.search(None, "ALL")
        total_emails = len(messages[0].split())
        
        print(f"\n📧 Estatísticas:")
        print(f"   - Total de emails: {total_emails}")
        
        # Contar não lidos
        status, messages = mail.search(None, "UNSEEN")
        unread_emails = len(messages[0].split()) if messages[0] else 0
        
        print(f"   - Emails não lidos: {unread_emails}")
        
        mail.close()
        mail.logout()
        
        return True
    
    except Exception as e:
        print(f"\n❌ Erro na conexão IMAP: {e}")
        print(f"\n💡 Dicas:")
        print(f"   1. Verifique se a senha de app está correta")
        print(f"   2. Confirme que a verificação em 2 etapas está ativa")
        print(f"   3. Tente regenerar a senha de app")
        return False


async def interactive_test():
    """Teste interativo passo a passo"""
    print("\n" + "="*60)
    print("🧪 SISTEMA DE TESTE INTERATIVO - NUBANK IMAP")
    print("="*60)
    
    # 1. Testar configuração
    if not await test_configuration():
        print("\n⚠️  Corrija a configuração antes de continuar")
        return
    
    input("\nPressione ENTER para testar a conexão IMAP...")
    
    # 2. Testar conexão IMAP
    if not await test_imap_connection():
        print("\n⚠️  Corrija a conexão IMAP antes de continuar")
        return
    
    input("\nPressione ENTER para criar um pagamento de teste...")
    
    # 3. Criar pagamento de teste
    payment_id = await test_create_payment()
    
    if not payment_id:
        print("\n⚠️  Não foi possível criar o pagamento de teste")
        return
    
    print("\n" + "="*60)
    print("💰 AGUARDANDO PAGAMENTO")
    print("="*60)
    print(f"\n📱 Agora você pode:")
    print(f"   1. Escanear o QR Code gerado")
    print(f"   2. Pagar R$ 0,01 via PIX")
    print(f"   3. Aguardar o email do Nubank")
    print(f"\n⏱️  Este teste irá verificar o pagamento por 5 minutos")
    
    # 4. Monitorar pagamento
    for i in range(10):  # 10 tentativas de 30 segundos = 5 minutos
        print(f"\n🔄 Verificação {i+1}/10...")
        
        status = await check_nubank_imap_payment(payment_id)
        
        if status and status['status'] == 'approved':
            print("\n" + "="*60)
            print("🎉 PAGAMENTO APROVADO COM SUCESSO!")
            print("="*60)
            print(f"\n✅ Todos os testes passaram!")
            print(f"   O sistema está funcionando corretamente!")
            return
        
        if i < 9:  # Não esperar na última iteração
            print(f"   Aguardando 30 segundos...")
            await asyncio.sleep(30)
    
    print("\n" + "="*60)
    print("⏱️  TIMEOUT")
    print("="*60)
    print(f"\n⚠️  O pagamento não foi detectado em 5 minutos")
    print(f"\nPossíveis motivos:")
    print(f"   - O email ainda não chegou (pode demorar)")
    print(f"   - Notificações não estão ativas no Nubank")
    print(f"   - O TXID não foi capturado corretamente")
    print(f"\n💡 Tente executar:")
    print(f"   await monitor_nubank_imap_payments()")


async def quick_test():
    """Teste rápido sem interação"""
    print("\n🚀 TESTE RÁPIDO - NUBANK IMAP\n")
    
    # Testar tudo em sequência
    config_ok = await test_configuration()
    
    if config_ok:
        await test_imap_connection()
        await test_monitor_payments()
    
    print("\n✅ Teste rápido concluído!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(quick_test())
    else:
        asyncio.run(interactive_test())

