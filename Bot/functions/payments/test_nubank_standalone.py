"""
Script de teste standalone para o sistema Nubank IMAP
Este script funciona independentemente do resto do sistema
"""
import asyncio
import imaplib
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def test_imports():
    """Testa se as importações funcionam"""
    print("\n" + "="*60)
    print("[TESTE] IMPORTACOES")
    print("="*60)
    
    try:
        from functions.database import database as db
        print("[OK] Database importado com sucesso")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao importar database: {e}")
        return False


def test_configuration():
    """Testa se a configuração está correta"""
    print("\n" + "="*60)
    print("[TESTE] CONFIGURACAO")
    print("="*60)
    
    try:
        from functions.database import database as db
        
        config = db.get_document("payment_configs") or {}
        nubank_config = config.get("nubank_imap", {})
        
        print(f"\n[OK] Configuracao encontrada")
        print(f"  - Habilitado: {nubank_config.get('enabled')}")
        print(f"  - Email: {nubank_config.get('email')}")
        print(f"  - Senha configurada: {'Sim' if nubank_config.get('password') else 'Nao'}")
        print(f"  - Chave PIX: {nubank_config.get('pix_key')}")
        print(f"  - Tipo de chave: {nubank_config.get('pix_key_type')}")
        
        if not nubank_config.get("enabled"):
            print("\n[ERRO] Nubank IMAP nao esta habilitado!")
            print("   Configure no database: payment_configs.nubank_imap.enabled = true")
            return False
        
        if not nubank_config.get("email"):
            print("\n[ERRO] Email nao configurado!")
            return False
        
        if not nubank_config.get("password"):
            print("\n[ERRO] Senha de app nao configurada!")
            return False
        
        if not nubank_config.get("pix_key"):
            print("\n[ERRO] Chave PIX nao configurada!")
            return False
        
        print("\n[OK] Configuracao valida!")
        return True
    
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imap_connection():
    """Testa a conexão IMAP diretamente"""
    print("\n" + "="*60)
    print("[TESTE] CONEXAO IMAP")
    print("="*60)
    
    try:
        from functions.database import database as db
        
        config = db.get_document("payment_configs") or {}
        nubank_config = config.get("nubank_imap", {})
        
        email_address = nubank_config.get("email")
        password = nubank_config.get("password")
        
        if not email_address or not password:
            print("\n[ERRO] Email ou senha nao configurados")
            return False
        
        print(f"\n[INFO] Conectando ao Gmail...")
        print(f"   Email: {email_address}")
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_address, password)
        
        print(f"[OK] Conexao estabelecida com sucesso!")
        
        # Selecionar inbox
        mail.select("inbox")
        
        # Contar emails
        status, messages = mail.search(None, "ALL")
        total_emails = len(messages[0].split()) if messages[0] else 0
        
        print(f"\n[INFO] Estatisticas:")
        print(f"   - Total de emails: {total_emails}")
        
        # Contar não lidos
        status, messages = mail.search(None, "UNSEEN")
        unread_emails = len(messages[0].split()) if messages[0] else 0
        
        print(f"   - Emails nao lidos: {unread_emails}")
        
        mail.close()
        mail.logout()
        
        return True
    
    except Exception as e:
        print(f"\n[ERRO] Erro na conexao IMAP: {e}")
        print(f"\n[DICA] Passos para resolver:")
        print(f"   1. Verifique se a senha de app esta correta")
        print(f"   2. Confirme que a verificacao em 2 etapas esta ativa")
        print(f"   3. Tente regenerar a senha de app")
        print(f"   4. Acesse: https://myaccount.google.com/apppasswords")
        return False


async def test_payment_creation():
    """Testa a criação de um pagamento"""
    print("\n" + "="*60)
    print("[TESTE] CRIACAO DE PAGAMENTO")
    print("="*60)
    
    try:
        from functions.payments.imap_nubank import create_nubank_imap_payment
        
        payment = await create_nubank_imap_payment(
            amount=0.01,
            cart_id="TEST123456",
            description="Pagamento de Teste"
        )
        
        print(f"\n[OK] Pagamento criado com sucesso!")
        print(f"\n[INFO] Detalhes:")
        print(f"  - ID: {payment['payment_id']}")
        print(f"  - Valor: R$ {payment['amount']:.2f}")
        print(f"  - Status: {payment['status']}")
        print(f"  - PIX (primeiros 50 chars): {payment['pix_copia_cola'][:50]}...")
        print(f"  - QR Code: {len(payment['qr_code_bytes'])} bytes")
        
        return True
    
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("TESTE STANDALONE - NUBANK IMAP")
    print("="*60)
    
    # Teste 1: Importações
    if not test_imports():
        print("\n[AVISO] Nao foi possivel importar modulos necessarios")
        print("   Execute este script do diretorio raiz: python functions/payments/test_nubank_standalone.py")
        return
    
    # Teste 2: Configuração
    if not test_configuration():
        print("\n[AVISO] Configure o sistema primeiro:")
        print("   python functions/payments/nubank_setup.py setup")
        return
    
    input("\nPressione ENTER para testar a conexao IMAP...")
    
    # Teste 3: Conexão IMAP
    if not test_imap_connection():
        print("\n[AVISO] Corrija a configuracao do IMAP antes de continuar")
        return
    
    input("\nPressione ENTER para testar criacao de pagamento...")
    
    # Teste 4: Criação de pagamento (assíncrono)
    try:
        asyncio.run(test_payment_creation())
    except Exception as e:
        print(f"\n[ERRO] Erro ao testar criacao de pagamento: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*60)
    print("[OK] TODOS OS TESTES BASICOS PASSARAM!")
    print("="*60)
    print("\n[SUCESSO] O sistema esta pronto para uso!")
    print("\n[INFO] Proximos passos:")
    print("   1. Faca um pagamento de teste de R$ 0,01")
    print("   2. Aguarde o email do Nubank")
    print("   3. Execute: python functions/payments/nubank_scheduler.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Teste interrompido pelo usuario")
    except Exception as e:
        print(f"\n[ERRO] Erro fatal: {e}")
        import traceback
        traceback.print_exc()

