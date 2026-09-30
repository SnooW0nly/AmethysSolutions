import disnake

from functions.database import database as db
from functions.emoji import emoji
from functions.prefix import get_prefix, set_prefix


class edit_prefix:

    @staticmethod
    def get_panel_components(inter=None) -> list:
        colors = db.get_document("custom_colors") or {}
        hex_str = colors.get("primary")
        ck = {}
        if hex_str:
            ck["accent_colour"] = disnake.Colour(int(hex_str.replace("#", ""), 16))

        current = get_prefix()

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Personalização > **Prefixo**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"Configure o prefixo usado antes dos comandos do bot.\n\n"
                    f"**Prefixo atual:** `{current}`\n"
                    f"-# Exemplo: `{current}daily` · `{current}balance` · `{current}play`\n\n"
                    f"⚠️ Máximo de **5 caracteres**. A mudança vale imediatamente."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label=f"Alterar Prefixo  (atual: {current})",
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Personalizacao_EditarPrefixo_Modal",
                        emoji=emoji.edit,
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

    @staticmethod
    def get_panel_embed(inter=None):
        colors = db.get_document("custom_colors") or {}
        hex_str = colors.get("primary")
        color = int(hex_str.replace("#", ""), 16) if hex_str else 0x5c5ef0

        current = get_prefix()

        embed = disnake.Embed(
            title="Prefixo do Bot",
            description=(
                f"Configure o prefixo usado antes dos comandos do bot.\n\n"
                f"**Prefixo atual:** `{current}`\n"
                f"-# Exemplo: `{current}daily` · `{current}balance` · `{current}play`\n\n"
                f"⚠️ Máximo de **5 caracteres**. A mudança vale imediatamente."
            ),
            color=color,
        )

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=f"Alterar Prefixo  (atual: {current})",
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Personalizacao_EditarPrefixo_Modal",
                    emoji=emoji.edit,
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

    class edit_prefix_modal(disnake.ui.Modal):
        def __init__(self):
            current = get_prefix()
            components = [
                disnake.ui.TextInput(
                    label="Novo Prefixo",
                    custom_id="novo_prefix",
                    value=current,
                    placeholder="Ex:  !  /  ?  >>  $",
                    min_length=1,
                    max_length=5,
                    style=disnake.TextInputStyle.short,
                    required=True,
                ),
            ]
            super().__init__(title="Alterar Prefixo do Bot", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            mode = db.get_document("custom_mode").get("mode")
            novo = inter.text_values.get("novo_prefix", "").strip()

            try:
                salvo = set_prefix(novo)
            except ValueError as e:
                await inter.response.send_message(f"{emoji.wrong} {e}", ephemeral=True)
                return

            if mode == "embed":
                embed, components = edit_prefix.get_panel_embed(inter)
                await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                await inter.response.edit_message(
                    components=edit_prefix.get_panel_components(inter)
                )