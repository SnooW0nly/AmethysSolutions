"""
Script auxiliar para configurar o Nubank IMAP
"""
import sys
from pathlib import Path
import re

# Adicionar o diretório raiz ao path para imports funcionarem
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from functions.database import database as db


def validate_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_pix_key(pix_key: str, key_type: str) -> bool:
    """Valida formato de chave PIX"""
    if key_type == "email":
        return validate_email(pix_key)
    elif key_type == "cpf":
        clean = re.sub(r'[^0-9]', '', pix_key)
        return len(clean) == 11
    elif key_type == "cnpj":
        clean = re.sub(r'[^0-9]', '', pix_key)
        return len(clean) == 14
    elif key_type == "telefone":
        clean = re.sub(r'[^0-9]', '', pix_key)
        return len(clean) >= 10 and len(clean) <= 11
    elif key_type == "random":
        return len(pix_key) == 36  # UUID format
    return False


def setup_nubank_imap(
    email: str,
    password: str,
    pix_key: str,
    pix_key_type: str = "email",
    enabled: bool = True
) -> dict:
    """
    Configura o Nubank IMAP no database
    
    Args:
        email: Email do Gmail usado no Nubank
        password: Senha de app do Gmail (16 dígitos)
        pix_key: Chave PIX que receberá os pagamentos
        pix_key_type: Tipo da chave (email, cpf, cnpj, telefone, random)
        enabled: Se o sistema está habilitado
    
    Returns:
        Configuração salva
    """
    # Validações
    if not validate_email(email):
        raise ValueError("Email inválido")
    
    if not password or len(password.replace(' ', '')) != 16:
        raise ValueError("Senha de app deve ter 16 caracteres")
    
    if not validate_pix_key(pix_key, pix_key_type):
        raise ValueError(f"Chave PIX inválida para o tipo '{pix_key_type}'")
    
    # Carregar configuração existente
    config = db.get_document("payment_configs") or {}
    
    # Atualizar configuração do Nubank IMAP
    config["nubank_imap"] = {
        "enabled": enabled,
        "email": email.strip(),
        "password": password.replace(' ', ''),  # Remover espaços
        "pix_key": pix_key.strip(),
        "pix_key_type": pix_key_type
    }
    
    # Salvar no database
    db.set_document("payment_configs", config)
    
    print("✅ Configuração do Nubank IMAP salva com sucesso!")
    print(f"\n📋 Detalhes:")
    print(f"   - Email: {email}")
    print(f"   - Chave PIX: {pix_key} ({pix_key_type})")
    print(f"   - Status: {'Habilitado' if enabled else 'Desabilitado'}")
    
    return config["nubank_imap"]


def get_nubank_config() -> dict:
    """Retorna a configuração atual do Nubank IMAP"""
    config = db.get_document("payment_configs") or {}
    return config.get("nubank_imap", {})


def disable_nubank_imap():
    """Desabilita o Nubank IMAP"""
    config = db.get_document("payment_configs") or {}
    if "nubank_imap" in config:
        config["nubank_imap"]["enabled"] = False
        db.set_document("payment_configs", config)
        print("✅ Nubank IMAP desabilitado")
    else:
        print("⚠️  Nubank IMAP não está configurado")


def enable_nubank_imap():
    """Habilita o Nubank IMAP"""
    config = db.get_document("payment_configs") or {}
    if "nubank_imap" in config:
        config["nubank_imap"]["enabled"] = True
        db.set_document("payment_configs", config)
        print("✅ Nubank IMAP habilitado")
    else:
        print("⚠️  Nubank IMAP não está configurado")


def show_nubank_config():
    """Exibe a configuração atual"""
    config = get_nubank_config()
    
    if not config:
        print("⚠️  Nubank IMAP não está configurado")
        return
    
    print("\n" + "="*60)
    print("⚙️  CONFIGURAÇÃO NUBANK IMAP")
    print("="*60)
    print(f"\nStatus: {'✅ Habilitado' if config.get('enabled') else '❌ Desabilitado'}")
    print(f"Email: {config.get('email', 'Não configurado')}")
    print(f"Senha: {'●●●●●●●●●●●●●●●●' if config.get('password') else 'Não configurada'}")
    print(f"Chave PIX: {config.get('pix_key', 'Não configurada')}")
    print(f"Tipo de Chave: {config.get('pix_key_type', 'Não configurado')}")
    print("="*60)


def interactive_setup():
    """Setup interativo via linha de comando"""
    print("\n" + "="*60)
    print("🚀 CONFIGURAÇÃO INTERATIVA - NUBANK IMAP")
    print("="*60)
    
    print("\n📧 PASSO 1: Email do Gmail")
    print("   (O mesmo usado no Nubank para receber notificações)")
    email = input("   Email: ").strip()
    
    print("\n🔑 PASSO 2: Senha de App do Gmail")
    print("   (16 dígitos gerados em: myaccount.google.com/apppasswords)")
    password = input("   Senha: ").strip()
    
    print("\n💳 PASSO 3: Chave PIX")
    print("   (A chave que receberá os pagamentos)")
    pix_key = input("   Chave PIX: ").strip()
    
    print("\n📋 PASSO 4: Tipo da Chave PIX")
    print("   Opções: email, cpf, cnpj, telefone, random")
    pix_key_type = input("   Tipo (padrão: email): ").strip() or "email"
    
    print("\n🔄 Salvando configuração...")
    
    try:
        setup_nubank_imap(email, password, pix_key, pix_key_type)
        
        print("\n" + "="*60)
        print("✅ CONFIGURAÇÃO CONCLUÍDA!")
        print("="*60)
        print("\n📝 Próximos passos:")
        print("   1. Ative notificações por email no app Nubank")
        print("   2. Execute o teste: python test_nubank_imap.py")
        print("   3. Faça um pagamento de teste de R$ 0,01")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "show":
            show_nubank_config()
        elif command == "enable":
            enable_nubank_imap()
        elif command == "disable":
            disable_nubank_imap()
        elif command == "setup":
            interactive_setup()
        else:
            print("Comandos disponíveis:")
            print("  python nubank_setup.py show      - Mostrar configuração atual")
            print("  python nubank_setup.py enable    - Habilitar Nubank IMAP")
            print("  python nubank_setup.py disable   - Desabilitar Nubank IMAP")
            print("  python nubank_setup.py setup     - Configuração interativa")
    else:
        interactive_setup()

