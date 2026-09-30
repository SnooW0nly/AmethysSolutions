import re
import unicodedata
import disnake

from functions.database import database as db
from functions.emoji import emoji

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────

# Limite de caracteres da bio de aplicação no Discord
DISCORD_BIO_LIMIT = 400

# Separador visual entre a bio da Amethys e a bio do usuário
BIO_SEPARATOR = "\n~~                                                                                                                 ~~\n"

# Palavras/padrões bloqueados — qualquer texto que difame, desvie créditos ou
# redirecione autoria para terceiros.  Todos os padrões são case-insensitive e
# ignoram acentos/diacríticos (ver _normalize).
_BLOCKED_PATTERNS: list[str] = [
    # Difamação direta da Amethys
    r"ameth[yi]s\s*(é|e|eh)\s*(ruim|lixo|péssim[ao]|merda|uma\s*bosta|horrív[eo]l)",
    r"(não\s*(é|e)\s*da|nao\s*(e)\s*da)\s*ameth[yi]s",
    r"(fake|falso|mentira|fraude|golpe|scam)\s*(ameth[yi]s)?",
    # Redirecionamento de créditos — "feito por X", "criado por X", "desenvolvido por X"
    r"(feito|criado|desenvolvido|produzido|mantido|programado)\s*(por|pela?)\s+(?!ameth[yi]s)",
    r"(made|created|developed|built|powered)\s+by\s+(?!ameth[yi]s)",
    # Substituição direta de autoria
    r"autor[ia]?\s*:\s*(?!ameth[yi]s)",
    r"créditos?\s*:\s*(?!ameth[yi]s)",
    r"credits?\s*:\s*(?!ameth[yi]s)",
    r"(dev|developer|desenvolvedor)\s*:\s*(?!ameth[yi]s)",
    # Links que não sejam da Amethys tentando se passar por origem
    r"(github\.com|discord\.gg|discord\.com/invite)/(?!ameth[yi]s)",
    # Termos de concorrência direta tentando substituir créditos
    r"(não\s*use\s*ameth[yi]s|dont?\s*use\s*ameth[yi]s)",
    r"(copiad[oa]\s*d[ae]|stolen\s*from)\s*ameth[yi]s",
]

_COMPILED_BLOCKED: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE | re.UNICODE) for p in _BLOCKED_PATTERNS
]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Remove diacríticos para comparação case-insensitive com acentos."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")


def _contains_blocked(text: str) -> str | None:
    """
    Verifica se o texto contém algum padrão bloqueado.
    Retorna o trecho problemático (para exibir ao usuário) ou None se estiver ok.
    """
    normalized = _normalize(text)
    for pattern in _COMPILED_BLOCKED:
        match = pattern.search(normalized)
        if match:
            # Retorna o trecho original (não normalizado) para a mensagem de erro
            start, end = match.span()
            return text[start:end] if end <= len(text) else normalized[start:end]
    return None


def build_final_bio(amethys_bio: str, user_bio: str) -> str:
    """
    Combina a bio da Amethys (imutável) com a bio do usuário.

    Regras:
    - A bio da Amethys sempre vem primeiro e nunca é truncada.
    - Se a bio do usuário + separador ultrapassar o limite do Discord,
      a bio do usuário é truncada pelo final, preservando a bio da Amethys
      integralmente.  Um indicador "…" é adicionado ao fim do trecho do usuário.
    - Se a bio do usuário estiver vazia, retorna apenas a bio da Amethys.
    """
    if not user_bio:
        return amethys_bio

    base = amethys_bio + BIO_SEPARATOR
    available = DISCORD_BIO_LIMIT - len(base)

    if available <= 0:
        # Bio da Amethys já ocupa todo o espaço — usuário não cabe
        return amethys_bio

    if len(user_bio) <= available:
        return base + user_bio

    # Trunca a bio do usuário para caber no espaço disponível
    truncated = user_bio[: available - 1] + "…"
    return base + truncated


# ──────────────────────────────────────────────────────────────────────────────
# Modal
# ──────────────────────────────────────────────────────────────────────────────

class EditBioModal(disnake.ui.Modal):
    def __init__(self, current_user_bio: str = ""):
        components = [
            disnake.ui.TextInput(
                label="Biografia Personalizada",
                custom_id="user_bio",
                value=current_user_bio,
                placeholder="Escreva algo sobre o seu bot… (aparece abaixo da bio padrão)",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=300,   # margem segura — a lógica de build_final_bio trata o resto
            ),
        ]
        super().__init__(title="Editar Biografia do Bot", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        from core.change_bio import change_bio   # import local para evitar circular

        mode     = db.get_document("custom_mode").get("mode")
        user_bio = inter.text_values.get("user_bio", "").strip()

        # ── Validação de conteúdo bloqueado ──────────────────────────────────
        if user_bio:
            blocked_snippet = _contains_blocked(user_bio)
            if blocked_snippet:
                error_msg = (
                    f"-# {emoji.alert} Sua biografia contém conteúdo não permitido: `{blocked_snippet[:60]}`\n"
                    "-# Textos que difamem a Amethys ou redirecionem créditos para terceiros são bloqueados."
                )
                await inter.response.send_message(content=error_msg, ephemeral=True)
                return

        # ── Salva e aplica ───────────────────────────────────────────────────
        bio_doc = db.get_document("custom_bio") or {}
        bio_doc["user_bio"] = user_bio
        db.save_document("custom_bio", {}, bio_doc)

        # Reaplica a bio completa no Discord (amethys + usuário)
        try:
            change_bio()
        except Exception as e:
            print(f"[edit_bio] Erro ao aplicar bio após edição: {e}")

        # ── Atualiza o painel ─────────────────────────────────────────────────
        if mode == "embed":
            embed, comps = EditBioCog.get_panel_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(
                components=EditBioCog.get_panel_components(inter)
            )


# ──────────────────────────────────────────────────────────────────────────────
# Cog / painel
# ──────────────────────────────────────────────────────────────────────────────

class EditBioCog:
    """Métodos estáticos de construção de painel — sem listener próprio."""

    @staticmethod
    def _get_user_bio() -> str:
        return (db.get_document("custom_bio") or {}).get("user_bio", "")

    # ── Components V2 ─────────────────────────────────────────────────────────
    @staticmethod
    def get_panel_components(inter=None) -> list:
        colors      = db.get_document("custom_colors") or {}
        hex_str     = colors.get("primary")
        ck          = {}
        if hex_str:
            ck["accent_colour"] = disnake.Colour(int(hex_str.replace("#", ""), 16))

        user_bio    = EditBioCog._get_user_bio()
        preview_txt = f"`{user_bio}`" if user_bio else "*Nenhuma biografia personalizada definida.*"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Personalização > **Biografia**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Adicione um texto personalizado à bio do seu bot.\n"
                    "Ele será exibido **abaixo** da bio padrão da Amethys.\n\n"
                    f"-# {emoji.alert} A bio padrão **nunca é removida** — se o texto ultrapassar o limite "
                    "do Discord, ele será truncado automaticamente para preservá-la."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Texto atual:**\n{preview_txt}"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar Biografia",
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Personalizacao_EditarBio_Modal",
                        emoji=emoji.edit,
                    ),
                    disnake.ui.Button(
                        label="Limpar Biografia",
                        style=disnake.ButtonStyle.red,
                        custom_id="Personalizacao_LimparBio",
                        emoji=emoji.delete,
                        disabled=not bool(user_bio),
                    ),
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    custom_id="Painel_Personalizacao",
                    emoji=emoji.back,
                ),
            ),
        ]

    # ── Embed (V1) ────────────────────────────────────────────────────────────
    @staticmethod
    def get_panel_embed(inter=None):
        colors      = db.get_document("custom_colors") or {}
        hex_str     = colors.get("primary")
        color       = int(hex_str.replace("#", ""), 16) if hex_str else 0x5C5EF0

        user_bio    = EditBioCog._get_user_bio()
        preview_txt = f"`{user_bio}`" if user_bio else "*Nenhuma biografia personalizada definida.*"

        embed = disnake.Embed(
            title="Biografia do Bot",
            description=(
                "Adicione um texto personalizado à bio do seu bot.\n"
                "Ele será exibido **abaixo** da bio padrão da Amethys.\n\n"
                f"-# {emoji.alert} A bio padrão **nunca é removida** — se o texto ultrapassar o limite "
                "do Discord, ele será truncado automaticamente para preservá-la."
            ),
            color=color,
        )
        embed.add_field(name="Texto atual:", value=preview_txt, inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Editar Biografia",
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Personalizacao_EditarBio_Modal",
                    emoji=emoji.edit,
                ),
                disnake.ui.Button(
                    label="Limpar Biografia",
                    style=disnake.ButtonStyle.red,
                    custom_id="Personalizacao_LimparBio",
                    emoji=emoji.delete,
                    disabled=not bool(user_bio),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    custom_id="Painel_Personalizacao",
                    emoji=emoji.back,
                ),
            ),
        ]
        return embed, components