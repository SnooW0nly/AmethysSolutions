"""
Helper para gerenciar templates no MongoDB.
Templates são armazenados como uma lista dentro do documento 'messages_templates1'.
"""
from functions.database import database


def get_all_templates() -> list:
    """Retorna todos os templates salvos."""
    doc = database.get_document("messages_templates1")
    return doc.get("templates", [])


def get_template_by_id(template_id: str) -> dict | None:
    """Retorna um template específico pelo ID."""
    templates = get_all_templates()
    for tpl in templates:
        if tpl.get("id") == template_id:
            return tpl
    return None


def save_template(template: dict) -> None:
    """Salva ou atualiza um template."""
    doc = database.get_document("messages_templates1")
    templates = doc.get("templates", [])
    
    # Verifica se já existe um template com o mesmo ID
    existing_index = None
    for i, tpl in enumerate(templates):
        if tpl.get("id") == template.get("id"):
            existing_index = i
            break
    
    if existing_index is not None:
        # Atualiza template existente
        templates[existing_index] = template
    else:
        # Adiciona novo template
        templates.append(template)
    
    doc["templates"] = templates
    database.save_document("messages_templates1", doc)


def delete_template(template_id: str) -> bool:
    """Deleta um template pelo ID. Retorna True se deletado com sucesso."""
    doc = database.get_document("messages_templates1")
    templates = doc.get("templates", [])
    
    new_templates = [tpl for tpl in templates if tpl.get("id") != template_id]
    
    if len(new_templates) < len(templates):
        doc["templates"] = new_templates
        database.save_document("messages_templates1", doc)
        return True
    return False


def delete_all_templates() -> None:
    """Deleta todos os templates."""
    doc = database.get_document("messages_templates1")
    doc["templates"] = []
    database.save_document("messages_templates1", doc)
