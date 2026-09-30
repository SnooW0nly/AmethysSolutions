"""
Teste rápido da conexão IMAP (sem interação)
"""
import sys
from pathlib import Path
import imaplib

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from functions.database import database as db

def test_imap():
    print("\n" + "="*60)
    print("[TESTE] CONEXAO IMAP - NUBANK")
    print("="*60)
    
    config = db.get_document("payment_configs") or {}
    nubank_config = config.get("nubank_imap", {})
    
    email_address = nubank_config.get("email")
    password = nubank_config.get("password")
    
    if not email_address or not password:
        print("\n[ERRO] Email ou senha nao configurados")
        return False
    
    print(f"\n[INFO] Conectando ao Gmail...")
    print(f"   Email: {email_address}")
    
    try:
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
        
        # Procurar emails do Nubank
        status, messages = mail.search(None, '(FROM "nubank")')
        nubank_emails = len(messages[0].split()) if messages[0] else 0
        
        print(f"   - Emails do Nubank: {nubank_emails}")
        
        mail.close()
        mail.logout()
        
        print(f"\n[OK] Teste de conexao IMAP concluido com sucesso!")
        print(f"\n[SUCESSO] O sistema esta pronto para receber pagamentos!")
        return True
    
    except Exception as e:
        print(f"\n[ERRO] Erro na conexao IMAP: {e}")
        print(f"\n[DICA] Passos para resolver:")
        print(f"   1. Verifique se a senha de app esta correta")
        print(f"   2. Confirme que a verificacao em 2 etapas esta ativa")
        print(f"   3. Tente regenerar a senha de app")
        print(f"   4. Acesse: https://myaccount.google.com/apppasswords")
        return False

if __name__ == "__main__":
    try:
        test_imap()
    except Exception as e:
        print(f"\n[ERRO] Erro fatal: {e}")
        import traceback
        traceback.print_exc()

