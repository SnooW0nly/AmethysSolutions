import string, random
import re
import unicodedata
import disnake
from functions.database import database as db

class utils:
    @staticmethod
    def get_emoji_from_string(emoji_str: str):
        """
        Tenta converter uma string em um emoji válido.
        Retorna None se o emoji for inválido ou não puder ser processado.
        NÃO aceita letras, números ou combinações deles.
        """
        if not emoji_str:
            return None
        
        # Limpar espaços
        emoji_str = str(emoji_str).strip()
        if not emoji_str:
            return None
        
        # Verificar se é um formato de emoji personalizado inválido (ex: :nome: sem < >)
        if emoji_str.startswith(":") and emoji_str.endswith(":") and not emoji_str.startswith("<"):
            # Formato inválido como :suport: - retornar None
            return None
        
        try:
            # This handles custom emojis like <:name:id> or <a:name:id>
            if emoji_str.startswith("<") and emoji_str.endswith(">"):
                return disnake.PartialEmoji.from_str(emoji_str)
        except (ValueError, TypeError, AttributeError):
            pass
        
        # Verificar se contém dois-pontos mas não está no formato <:name:id>, é inválido
        if ":" in emoji_str and not emoji_str.startswith("<"):
            return None
        
        # IMPORTANTE: Rejeitar letras e números
        # Verificar se é apenas letras ASCII (a-z, A-Z)
        if re.match(r'^[a-zA-Z]+$', emoji_str):
            return None
        
        # Verificar se é apenas números (0-9)
        if re.match(r'^\d+$', emoji_str):
            return None
        
        # Verificar se é apenas letras e números (sem emojis)
        if re.match(r'^[a-zA-Z0-9]+$', emoji_str):
            return None
        
        # Verificar se contém caracteres alfanuméricos ASCII sem emojis
        # Se todos os caracteres são alfanuméricos ASCII, rejeitar
        all_ascii_alnum = True
        for char in emoji_str:
            if not char.isalnum() or ord(char) > 127:
                all_ascii_alnum = False
                break
        
        if all_ascii_alnum and len(emoji_str) > 0:
            return None
        
        # Verificar se contém pelo menos um caractere de emoji válido
        has_emoji_char = False
        
        # Verificar ranges Unicode de emojis
        for char in emoji_str:
            code_point = ord(char)
            
            # Ranges principais de emojis Unicode
            if (
                (0x1F300 <= code_point <= 0x1F9FF) or  # Miscellaneous Symbols and Pictographs, Emoticons, etc
                (0x2600 <= code_point <= 0x26FF) or   # Miscellaneous Symbols
                (0x2700 <= code_point <= 0x27BF) or   # Dingbats
                (0x1F600 <= code_point <= 0x1F64F) or  # Emoticons
                (0x1F680 <= code_point <= 0x1F6FF) or  # Transport and Map Symbols
                (0x1F1E0 <= code_point <= 0x1F1FF) or   # Regional Indicator Symbols (bandeiras)
                (0x1F900 <= code_point <= 0x1F9FF) or  # Supplemental Symbols and Pictographs
                (0x1FA00 <= code_point <= 0x1FAFF) or  # Chess Symbols, Symbols and Pictographs Extended-A
                (unicodedata.category(char) == "So")   # Symbol, Other
            ):
                has_emoji_char = True
                break
        
        # Se não encontrou nenhum caractere de emoji válido, rejeitar
        if not has_emoji_char:
            return None
        
        # Verificar se é um emoji unicode válido
        try:
            # Tentar criar PartialEmoji com o nome (para emojis unicode)
            # Se for muito longo, provavelmente é inválido
            if len(emoji_str) > 50:
                return None
            return disnake.PartialEmoji(name=emoji_str)
        except (ValueError, TypeError, AttributeError):
            return None
    
    @staticmethod
    def safe_get_emoji(emoji_str: str, default=None):
        """
        Versão segura de get_emoji_from_string que sempre retorna None ou default
        para emojis inválidos, nunca lança exceções.
        
        Args:
            emoji_str: String do emoji a ser processado
            default: Valor padrão a retornar se o emoji for inválido (padrão: None)
        
        Returns:
            disnake.PartialEmoji ou default se inválido
        """
        try:
            result = utils.get_emoji_from_string(emoji_str)
            return result if result is not None else default
        except Exception:
            return default
    
    @staticmethod
    def validate_emoji_for_components(emoji_str: str) -> dict:
        """
        Valida se um emoji pode ser usado em componentes do Discord (botões, selects, etc).
        
        O Discord tem restrições específicas para emojis em componentes:
        - Emojis customizados devem estar no formato <:name:id> ou <a:name:id>
        - Emojis unicode são aceitos, mas alguns podem não funcionar
        - Emojis que não são do servidor não funcionam em componentes
        - NÃO aceita letras, números ou combinações deles
        
        Args:
            emoji_str: String do emoji a ser validado
        
        Returns:
            dict com:
                - "valid": bool - Se o emoji é válido para componentes
                - "emoji": disnake.PartialEmoji | str | None - O emoji processado
                - "error": str | None - Mensagem de erro se inválido
                - "original": str - String original fornecida
        """
        if not emoji_str:
            return {
                "valid": False,
                "emoji": None,
                "error": "Emoji vazio",
                "original": ""
            }
        
        emoji_str = str(emoji_str).strip()
        original = emoji_str
        
        # Se estiver vazio após trim
        if not emoji_str:
            return {
                "valid": False,
                "emoji": None,
                "error": "Emoji vazio",
                "original": original
            }
        
        # Validar formato de emoji customizado <:name:id> ou <a:name:id>
        if emoji_str.startswith("<") and emoji_str.endswith(">"):
            try:
                # Tentar parsear como PartialEmoji
                partial_emoji = disnake.PartialEmoji.from_str(emoji_str)
                
                # Verificar se tem ID válido (emojis customizados precisam de ID)
                if partial_emoji.id is None:
                    return {
                        "valid": False,
                        "emoji": None,
                        "error": "Emoji customizado precisa ter um ID válido",
                        "original": original
                    }
                
                # Verificar formato: deve ser <:name:id> ou <a:name:id>
                if not (emoji_str.startswith("<:") or emoji_str.startswith("<a:")):
                    return {
                        "valid": False,
                        "emoji": None,
                        "error": "Formato inválido. Use <:nome:id> ou <a:nome:id>",
                        "original": original
                    }
                
                # Verificar se tem nome e ID
                if not partial_emoji.name or not partial_emoji.id:
                    return {
                        "valid": False,
                        "emoji": None,
                        "error": "Emoji customizado precisa ter nome e ID",
                        "original": original
                    }
                
                return {
                    "valid": True,
                    "emoji": partial_emoji,
                    "error": None,
                    "original": original
                }
            except (ValueError, TypeError, AttributeError) as e:
                return {
                    "valid": False,
                    "emoji": None,
                    "error": f"Formato de emoji customizado inválido: {str(e)}",
                    "original": original
                }
        
        # Validar emoji unicode
        # Emojis unicode são aceitos em componentes, mas vamos validar se é realmente um emoji
        try:
            # Verificar se é um formato inválido como :nome: sem <>
            if emoji_str.startswith(":") and emoji_str.endswith(":") and len(emoji_str) > 2:
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Formato inválido. Use um emoji unicode ou <:nome:id>",
                    "original": original
                }
            
            # Verificar se contém dois-pontos mas não está no formato <:name:id>, é inválido
            if ":" in emoji_str and not emoji_str.startswith("<"):
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Formato inválido. Use um emoji unicode ou <:nome:id>",
                    "original": original
                }
            
            # IMPORTANTE: Verificar se contém apenas letras ASCII ou números
            # Rejeitar strings que são apenas letras/números
            
            # Verificar se é apenas letras ASCII (a-z, A-Z)
            if re.match(r'^[a-zA-Z]+$', emoji_str):
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Não é um emoji válido. Não aceita apenas letras.",
                    "original": original
                }
            
            # Verificar se é apenas números (0-9)
            if re.match(r'^\d+$', emoji_str):
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Não é um emoji válido. Não aceita apenas números.",
                    "original": original
                }
            
            # Verificar se é apenas letras e números (sem emojis)
            if re.match(r'^[a-zA-Z0-9]+$', emoji_str):
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Não é um emoji válido. Não aceita apenas letras e números.",
                    "original": original
                }
            
            # Verificar se contém caracteres alfanuméricos ASCII sem emojis
            # Se todos os caracteres são alfanuméricos ASCII, rejeitar
            all_ascii_alnum = True
            for char in emoji_str:
                if not char.isalnum() or ord(char) > 127:
                    all_ascii_alnum = False
                    break
            
            if all_ascii_alnum and len(emoji_str) > 0:
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Não é um emoji válido. Não aceita apenas letras e números.",
                    "original": original
                }
            
            # Verificar comprimento máximo
            if len(emoji_str) > 50:
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Emoji muito longo",
                    "original": original
                }
            
            # Verificar se contém pelo menos um caractere de emoji válido
            has_emoji_char = False
            
            # Verificar ranges Unicode de emojis
            for char in emoji_str:
                code_point = ord(char)
                
                # Ranges principais de emojis Unicode
                if (
                    (0x1F300 <= code_point <= 0x1F9FF) or  # Miscellaneous Symbols and Pictographs, Emoticons, etc
                    (0x2600 <= code_point <= 0x26FF) or   # Miscellaneous Symbols
                    (0x2700 <= code_point <= 0x27BF) or   # Dingbats
                    (0x1F600 <= code_point <= 0x1F64F) or  # Emoticons
                    (0x1F680 <= code_point <= 0x1F6FF) or  # Transport and Map Symbols
                    (0x1F1E0 <= code_point <= 0x1F1FF) or   # Regional Indicator Symbols (bandeiras)
                    (0x1F900 <= code_point <= 0x1F9FF) or  # Supplemental Symbols and Pictographs
                    (0x1FA00 <= code_point <= 0x1FAFF) or  # Chess Symbols, Symbols and Pictographs Extended-A
                    (unicodedata.category(char) == "So")   # Symbol, Other
                ):
                    has_emoji_char = True
                    break
            
            # Se não encontrou nenhum caractere de emoji válido, rejeitar
            if not has_emoji_char:
                return {
                    "valid": False,
                    "emoji": None,
                    "error": "Não é um emoji válido. Use um emoji unicode ou <:nome:id>",
                    "original": original
                }
            
            # Se passou todas as validações, é um emoji unicode válido
            return {
                "valid": True,
                "emoji": emoji_str,
                "error": None,
                "original": original
            }
        except Exception as e:
            return {
                "valid": False,
                "emoji": None,
                "error": f"Erro ao validar emoji: {str(e)}",
                "original": original
            }

    @staticmethod
    def gerar_id(tamanho: int = 10):
        return "".join(random.choices(string.ascii_letters + string.digits, k=tamanho))
    
    @staticmethod
    def obter_server_principal():
        return int(db.obter("config.json")["bot"]["server"])

    @staticmethod
    def is_valid_url(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = disnake.utils.parse_time(url)  # dummy to keep import usage consistent; not used
        except Exception:
            pass
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    @staticmethod
    def normalize_hex_color(hex_str: str):
        if not hex_str or not isinstance(hex_str, str):
            return None
        s = hex_str.strip()
        if not s:
            return None
        if s.startswith("#"):
            s = s[1:]
        if len(s) not in (3, 6):
            return None
        try:
            int(s, 16)
        except ValueError:
            return None
        return f"#{s.lower()}"
    
    @staticmethod
    def format_timestamp(timestamp: int | None) -> str:
        try:
            ts = int(timestamp) if timestamp is not None else None
            if not ts or ts <= 0:
                return "Nunca"
            return f"<t:{ts}:f> (<t:{ts}:R>)"
        except Exception:
            return "Nunca"

    @staticmethod
    def wrap_text_hyphenate(text: str, max_width: int = 40) -> str:
        if not text:
            return ""
        try:
            width = int(max_width)
        except Exception:
            width = 40
        if width <= 1:
            return str(text)

        output_lines = []
        for paragraph in str(text).splitlines():
            if paragraph.strip() == "":
                # Preserve blank lines between paragraphs
                output_lines.append("")
                continue

            current_line = ""
            words = paragraph.split(" ")
            for word in words:
                # Preserve multiple spaces by allowing empty tokens to add a space if it fits
                if word == "":
                    if current_line and len(current_line) + 1 <= width:
                        current_line += " "
                    elif not current_line:
                        current_line = " "
                    continue

                # If the word itself is longer than the width, split with hyphenation
                if len(word) > width:
                    if current_line:
                        output_lines.append(current_line)
                        current_line = ""
                    remaining = word
                    while len(remaining) > width:
                        chunk = remaining[: width - 1]
                        output_lines.append(chunk + "-")
                        remaining = remaining[width - 1 :]
                    # Start a new line with the remainder (may be empty)
                    if remaining:
                        current_line = remaining
                    continue

                # Normal fitting on current line or move to next
                if not current_line:
                    current_line = word
                elif len(current_line) + 1 + len(word) <= width:
                    current_line += " " + word
                else:
                    output_lines.append(current_line)
                    current_line = word

            if current_line:
                output_lines.append(current_line)

        return "\n".join(output_lines)

    def format_price_brl(price: float) -> str:
        return f"R$ {price:.2f}".replace(".", ",")
    
    @staticmethod
    def normalize_embed_data(embed_data: dict) -> dict:
        """
        Normaliza os dados do embed para garantir compatibilidade com disnake.Embed.from_dict().
        Converte cores em formato string hexadecimal para inteiros.
        Converte image_url e thumbnail_url para o formato esperado pelo disnake.
        """
        if not embed_data or not isinstance(embed_data, dict):
            return embed_data
        
        # Cria uma cópia para não modificar o original
        normalized = embed_data.copy()
        
        # Converte o campo 'color' se for string
        if "color" in normalized:
            color_value = normalized["color"]
            if isinstance(color_value, str):
                # Remove '#' se presente e converte para int
                hex_color = color_value.strip()
                if hex_color.startswith("#"):
                    hex_color = hex_color[1:]
                try:
                    # Converte hex string para inteiro
                    normalized["color"] = int(hex_color, 16)
                except (ValueError, TypeError):
                    # Se falhar, remove o campo color
                    del normalized["color"]
            elif color_value is None:
                # Remove se for None
                del normalized["color"]
        
        # Converte image_url para o formato esperado pelo disnake
        if "image_url" in normalized:
            image_url = normalized.pop("image_url")
            if image_url:
                normalized["image"] = {"url": image_url}
        
        # Converte thumbnail_url para o formato esperado pelo disnake
        if "thumbnail_url" in normalized:
            thumbnail_url = normalized.pop("thumbnail_url")
            if thumbnail_url:
                normalized["thumbnail"] = {"url": thumbnail_url}
        
        return normalized
    
    @staticmethod
    async def url_to_file(url: str, filename: str = "image.png") -> disnake.File:
        """
        Baixa uma imagem de uma URL e retorna como disnake.File.
        """
        import aiohttp
        import io
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    return disnake.File(io.BytesIO(data), filename=filename)
                else:
                    raise Exception(f"Falha ao baixar imagem: Status {response.status}")
