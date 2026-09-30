"""
Utilitários para manipulação de texto e validação de limites do Discord.
"""

def truncate_text(text: str, max_length: int = 4000, suffix: str = "...") -> str:
    """
    Trunca um texto para não exceder o limite especificado.
    
    Args:
        text: Texto a ser truncado
        max_length: Tamanho máximo permitido (padrão: 4000 para TextDisplay)
        suffix: Sufixo a adicionar quando truncar (padrão: "...")
    
    Returns:
        Texto truncado se necessário
    """
    if not text:
        return text
    
    if len(text) <= max_length:
        return text
    
    # Remover espaço para o sufixo
    truncate_at = max_length - len(suffix)
    return text[:truncate_at] + suffix


def safe_textdisplay(text: str, max_length: int = 3900) -> str:
    """
    Garante que um texto seja seguro para uso em TextDisplay.
    Usa 3900 como padrão para dar margem de segurança (limite real é 4000).
    
    Args:
        text: Texto a ser validado
        max_length: Tamanho máximo (padrão: 3900)
    
    Returns:
        Texto seguro para TextDisplay
    """
    return truncate_text(text, max_length)


def safe_select_option_label(text: str) -> str:
    """
    Garante que um label de SelectOption seja válido (máximo 100 caracteres).
    
    Args:
        text: Label a ser validado
    
    Returns:
        Label seguro para SelectOption
    """
    return truncate_text(text, 100)


def safe_select_option_description(text: str) -> str:
    """
    Garante que uma description de SelectOption seja válida (máximo 100 caracteres).
    
    Args:
        text: Description a ser validada
    
    Returns:
        Description segura para SelectOption
    """
    return truncate_text(text, 100)


def safe_button_label(text: str) -> str:
    """
    Garante que um label de Button seja válido (máximo 80 caracteres).
    
    Args:
        text: Label a ser validado
    
    Returns:
        Label seguro para Button
    """
    return truncate_text(text, 80)


def safe_embed_title(text: str) -> str:
    """
    Garante que um título de Embed seja válido (máximo 256 caracteres).
    
    Args:
        text: Título a ser validado
    
    Returns:
        Título seguro para Embed
    """
    return truncate_text(text, 256)


def safe_embed_description(text: str) -> str:
    """
    Garante que uma descrição de Embed seja válida (máximo 4096 caracteres).
    
    Args:
        text: Descrição a ser validada
    
    Returns:
        Descrição segura para Embed
    """
    return truncate_text(text, 4096)


def safe_embed_field_name(text: str) -> str:
    """
    Garante que um nome de field de Embed seja válido (máximo 256 caracteres).
    
    Args:
        text: Nome a ser validado
    
    Returns:
        Nome seguro para field
    """
    return truncate_text(text, 256)


def safe_embed_field_value(text: str) -> str:
    """
    Garante que um valor de field de Embed seja válido (máximo 1024 caracteres).
    
    Args:
        text: Valor a ser validado
    
    Returns:
        Valor seguro para field
    """
    return truncate_text(text, 1024)


def wrap_text(text: str, max_line_length: int = 50) -> str:
    """
    Quebra texto em linhas para melhor visualização em containers.
    Mantém quebras de linha existentes e adiciona novas quando necessário.
    
    Args:
        text: Texto a ser quebrado
        max_line_length: Comprimento máximo de cada linha (padrão: 50)
    
    Returns:
        Texto com quebras de linha
    """
    if not text or len(text) <= max_line_length:
        return text
    
    # Processar linha por linha (manter quebras existentes)
    lines = text.split('\n')
    wrapped_lines = []
    
    for line in lines:
        if len(line) <= max_line_length:
            wrapped_lines.append(line)
            continue
        
        # Quebrar linha longa em palavras
        words = line.split(' ')
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            # Se a palavra sozinha é maior que o limite, quebrar ela
            if word_length > max_line_length:
                if current_line:
                    wrapped_lines.append(' '.join(current_line))
                    current_line = []
                    current_length = 0
                
                # Quebrar palavra em pedaços
                for i in range(0, len(word), max_line_length):
                    wrapped_lines.append(word[i:i+max_line_length])
                continue
            
            # Verificar se adicionar a palavra ultrapassa o limite
            if current_length + word_length + len(current_line) > max_line_length:
                if current_line:
                    wrapped_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                current_line.append(word)
                current_length += word_length
        
        # Adicionar última linha
        if current_line:
            wrapped_lines.append(' '.join(current_line))
    
    return '\n'.join(wrapped_lines)
