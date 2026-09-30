from functions.database import database as db

def truncar_texto(texto: str, limite: int, sufixo: str = "...") -> str:
    """Trunca um texto respeitando um limite de caracteres, tentando não cortar palavras."""
    if not texto or len(texto) <= limite:
        return texto
    
    # Se o limite é muito pequeno, apenas trunca
    if limite <= len(sufixo):
        return texto[:limite]
    
    texto_truncado = texto[:limite - len(sufixo)]
    
    # Tenta encontrar o último espaço para não cortar palavras
    ultimo_espaco = texto_truncado.rfind(' ')
    if ultimo_espaco > limite * 0.7:  # Se encontrou um espaço em uma posição razoável
        texto_truncado = texto_truncado[:ultimo_espaco]
    
    return texto_truncado + sufixo

def truncar_para_mensagem(texto: str) -> str:
    """Trunca texto para uso em mensagem normal (limite: 2000 caracteres)."""
    return truncar_texto(texto, 2000)

class RespAutomaticasDB:
    def __init__(self):
        self.collection_name = "automations_response_auto"
        self.db_data = self._load()

    def _load(self):
        data = db.get_document(self.collection_name)
        if not data:
            return {"status": False, "responses": []}
        return data

    def _save(self):
        db.save_document(self.collection_name, {}, self.db_data)

    def get_status(self):
        # Reload data to get latest status
        self.db_data = self._load()
        return self.db_data.get("status", False)

    def set_status(self, status: bool):
        self.db_data["status"] = status
        self._save()

    def add_response(self, keyword: str, response: str, ephemeral: bool):
        if "responses" not in self.db_data:
            self.db_data["responses"] = []
        
        self.db_data["responses"] = [r for r in self.db_data.get("responses", []) if r.get("keyword", "").lower() != keyword.lower()]
        
        self.db_data["responses"].append({"keyword": keyword, "response": response, "ephemeral": ephemeral})
        self._save()

    def remove_response(self, keyword: str):
        if "responses" not in self.db_data:
            return

        self.db_data["responses"] = [r for r in self.db_data.get("responses", []) if r.get("keyword", "").lower() != keyword.lower()]
        self._save()

    def get_responses(self):
        # Reload data to get latest responses
        self.db_data = self._load()
        return self.db_data.get("responses", [])
