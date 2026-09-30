import base64
from functions.database import database as db
from modules.loja.cart.purchase_manager import PurchaseManager

def carregar_config() -> dict:
    """Carrega a configuração do MongoDB."""
    return db.get_document("automations_cont_vendas") or {}

def salvar_config(data: dict) -> None:
    """Salva a configuração no MongoDB."""
    db.save_document("automations_cont_vendas", {}, data)

def sanitizar_prefixo(prefixo: str) -> str:
    """Remove caracteres inválidos do prefixo que não podem estar em nomes de canais/categorias."""
    # Caracteres inválidos em nomes de canais Discord: / \ < > : * ? " |
    caracteres_invalidos = ['/', '\\', '<', '>', ':', '*', '?', '"', '|']
    prefixo_sanitizado = prefixo
    for char in caracteres_invalidos:
        prefixo_sanitizado = prefixo_sanitizado.replace(char, '')
    # Remove espaços extras e limita o tamanho
    prefixo_sanitizado = ' '.join(prefixo_sanitizado.split())
    return prefixo_sanitizado[:50]  # Limita a 50 caracteres

def codificar_prefixo(prefixo: str) -> str:
    """Codifica o prefixo em base64 para uso seguro em custom_id."""
    return base64.urlsafe_b64encode(prefixo.encode('utf-8')).decode('utf-8')

def decodificar_prefixo(prefixo_codificado: str) -> str:
    """Decodifica o prefixo de base64."""
    try:
        return base64.urlsafe_b64decode(prefixo_codificado.encode('utf-8')).decode('utf-8')
    except Exception:
        return prefixo_codificado  # Retorna o original se falhar

def formatar_nome_contador(prefixo: str, contagem: int, estilo: int) -> str:
    """Formata o nome do contador com base no estilo."""
    estilos = {
        0: f"{prefixo}: {contagem}",
        1: f"{prefixo} {contagem}",
        2: f"{contagem} {prefixo}",
        3: f"{contagem}: {prefixo}",
    }
    return estilos.get(estilo, estilos[0])

def estilo_legenda(estilo: int) -> str:
    """Retorna a legenda descritiva para um estilo."""
    legendas = {
        0: "Prefixo: Contagem",
        1: "Prefixo Contagem",
        2: "Contagem Prefixo",
        3: "Contagem: Prefixo",
    }
    return legendas.get(estilo, legendas[0])

def contar_todas_vendas(bot=None) -> int:
    """Conta todas as vendas realizadas em todos os servidores (total geral)."""
    try:
        # Obter todas as compras
        all_purchases = PurchaseManager.get_all_purchases()
        
        # Retornar o total de vendas (sem filtrar por servidor)
        return len(all_purchases)
    except Exception as e:
        # Em caso de erro, retornar 0 para não quebrar o sistema
        print(f"[ContVendas] Erro ao contar todas as vendas: {e}")
        import traceback
        traceback.print_exc()
        return 0

def contar_vendas(guild_id: int, bot=None) -> int:
    """Conta quantas vendas foram realizadas no servidor específico."""
    try:
        # Obter todas as compras
        all_purchases = PurchaseManager.get_all_purchases()
        
        # Normalizar guild_id para comparação
        guild_id_int = int(guild_id)
        
        # Contar vendas do servidor específico
        count = 0
        purchases_without_guild = 0
        
        for purchase in all_purchases:
            metadata = purchase.get("metadata", {})
            
            # Prioridade 1: guild_id direto no metadata (mais confiável)
            purchase_guild_id = metadata.get("guild_id")
            
            # Prioridade 2: buscar pelo cart_id se não tiver guild_id direto
            if purchase_guild_id is None:
                cart_id = metadata.get("cart_id")
                if cart_id:
                    # Carregar carts apenas se necessário
                    loja_data = db.get_document("loja_data")
                    carts = loja_data.get("carts", {})
                    
                    cart = carts.get(str(cart_id)) or (carts.get(int(cart_id)) if str(cart_id).isdigit() else None)
                    if cart:
                        purchase_guild_id = cart.get("guild_id")
                    elif bot:
                        # Tentar buscar pelo thread_id se temos bot
                        thread_id = metadata.get("thread_id")
                        if thread_id:
                            try:
                                thread = bot.get_thread(int(thread_id))
                                if thread:
                                    purchase_guild_id = thread.guild.id
                            except:
                                pass
            
            # Normalizar para int se encontrou
            if purchase_guild_id:
                purchase_guild_id = int(purchase_guild_id)
                if purchase_guild_id == guild_id_int:
                    count += 1
            else:
                purchases_without_guild += 1
        
        # Debug: imprimir informações se houver vendas sem guild
        if purchases_without_guild > 0:
            print(f"[ContVendas] Guild {guild_id}: {count} vendas encontradas | {purchases_without_guild} vendas sem guild_id identificado")
        
        return count
    except Exception as e:
        # Em caso de erro, retornar 0 para não quebrar o sistema
        print(f"[ContVendas] Erro ao contar vendas para guild {guild_id}: {e}")
        import traceback
        traceback.print_exc()
        return 0