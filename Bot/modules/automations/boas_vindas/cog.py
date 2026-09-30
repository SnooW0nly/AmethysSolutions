import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from modules.automations.boas_vindas import helpers

# Importa o Builder do sistema de anúncios (igual ao msg_auto faz)
from commands.admin.anunciar.builder import Builder
from commands.admin.anunciar.components.helper import Helper as AnunciarHelper
from commands.admin.anunciar.components.buttons import Buttons as AnunciarButtons


# ─── Modais ───────────────────────────────────────────────────────────────────

class DefinirMensagemBVModal(disnake.ui.Modal):
    def __init__(self, rota: str):
        self.rota = rota
        editor_data = helpers.get_editor_data(rota)
        super().__init__(
            title=f"Definir Mensagem — {'Canal' if rota == 'canal' else 'DM'}",
            custom_id=f"BV_DefinirMensagemModal:{rota}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="message",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Use {user}, {nameserver}, {nameuser}, {servercount}",
                    value=editor_data.get("content", ""),
                    max_length=2000,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        editor_data = helpers.get_editor_data(self.rota)
        editor_data["content"] = inter.text_values["message"]
        editor_data.pop("container", None)
        helpers.set_editor_data(self.rota, editor_data)
        await inter.response.edit_message(
            components=BoasVindasConfig.PainelEditor(self.rota)
        )


class DefinirEmbedBVModal(disnake.ui.Modal):
    def __init__(self, rota: str):
        self.rota = rota
        editor_data = helpers.get_editor_data(rota)
        embed_data = editor_data.get("embed", {})
        super().__init__(
            title=f"Definir Embed — {'Canal' if rota == 'canal' else 'DM'}",
            custom_id=f"BV_DefinirEmbedModal:{rota}",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="embed_title", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("title", "")),
                disnake.ui.TextInput(label="Descrição", custom_id="embed_description", style=disnake.TextInputStyle.paragraph, placeholder="Descrição do embed — use {user}, {nameserver}...", required=True, value=embed_data.get("description", "")),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="embed_color", style=disnake.TextInputStyle.short, required=False, placeholder="#5865F2", value=embed_data.get("color", "")),
                disnake.ui.TextInput(label="Footer", custom_id="embed_footer", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("footer", "")),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        def validar_hex(codigo: str) -> str | None:
            if not codigo: return None
            codigo = codigo.strip().lstrip("#")
            if len(codigo) not in (3, 6): return None
            try: int(codigo, 16)
            except ValueError: return None
            return f"#{codigo.upper()}"

        embed_data = {
            "title": inter.text_values.get("embed_title") or None,
            "description": inter.text_values.get("embed_description") or None,
            "color": validar_hex(inter.text_values.get("embed_color", "")),
            "footer": inter.text_values.get("embed_footer") or None,
        }
        editor_data = helpers.get_editor_data(self.rota)
        editor_data["embed"] = embed_data
        editor_data.pop("container", None)
        helpers.set_editor_data(self.rota, editor_data)
        await inter.response.edit_message(
            components=BoasVindasConfig.PainelEditor(self.rota)
        )


class DefinirImagensBVModal(disnake.ui.Modal):
    def __init__(self, rota: str):
        self.rota = rota
        editor_data = helpers.get_editor_data(rota)
        embed_data = editor_data.get("embed", {})
        has_embed = bool(embed_data.get("title") or embed_data.get("description"))

        components = [
            disnake.ui.TextInput(
                label="URL da imagem externa",
                custom_id="externalImage",
                style=disnake.TextInputStyle.short,
                required=False,
                value=editor_data.get("externalImage", ""),
            )
        ]
        if has_embed:
            components.extend([
                disnake.ui.TextInput(label="URL do Banner do Embed", custom_id="banner", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("banner", "")),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed", custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("thumbnail", "")),
            ])

        super().__init__(
            title=f"Definir Imagens — {'Canal' if rota == 'canal' else 'DM'}",
            custom_id=f"BV_DefinirImagensModal:{rota}",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        editor_data = helpers.get_editor_data(self.rota)
        editor_data["externalImage"] = inter.text_values.get("externalImage") or None
        if "banner" in inter.text_values:
            editor_data.setdefault("embed", {})["banner"] = inter.text_values.get("banner") or None
        if "thumbnail" in inter.text_values:
            editor_data.setdefault("embed", {})["thumbnail"] = inter.text_values.get("thumbnail") or None
        helpers.set_editor_data(self.rota, editor_data)
        await inter.response.edit_message(
            components=BoasVindasConfig.PainelEditor(self.rota)
        )


class DefinirContainerBVModal(disnake.ui.Modal):
    def __init__(self, rota: str):
        self.rota = rota
        editor_data = helpers.get_editor_data(rota)
        super().__init__(
            title=f"Definir Container — {'Canal' if rota == 'canal' else 'DM'}",
            custom_id=f"BV_DefinirContainerModal:{rota}",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container",
                    style=disnake.TextInputStyle.paragraph,
                    custom_id="container_content",
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}. Digite /ajuda para exemplos.",
                    required=True,
                    value=editor_data.get("container", ""),
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        if inter.text_values.get("container_content", "").strip() == "/ajuda":
            await inter.response.send_message(
                components=AnunciarHelper.helper("example"),
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        editor_data = helpers.get_editor_data(self.rota)
        editor_data["container"] = inter.text_values["container_content"]
        editor_data.pop("content", None)
        editor_data.pop("embed", None)
        helpers.set_editor_data(self.rota, editor_data)
        await inter.response.edit_message(
            components=BoasVindasConfig.PainelEditor(self.rota)
        )


class EditarTempoBVModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        valor_atual = int(config.get("canal", {}).get("tempo_segundos", 0) or 0)
        super().__init__(
            title="Editar Duração da Mensagem (Canal)",
            custom_id="BV_EditarTempoModal",
            components=[
                disnake.ui.TextInput(
                    label="Tempo em segundos (0 = não apagar)",
                    placeholder="Ex: 0, 30, 60",
                    value=str(valor_atual),
                    custom_id="tempo",
                    style=disnake.TextInputStyle.short,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        texto = inter.text_values.get("tempo", "0").strip()
        try:
            valor = max(0, int(texto))
            config = helpers.carregar_config()
            config.setdefault("canal", {})["tempo_segundos"] = valor
            db.save_document("automations_boas_vindas", {}, config)
            await inter.response.edit_message(
                components=BoasVindasConfig.PainelEditor("canal")
            )
        except Exception:
            await inter.response.send_message("Valor inválido para tempo.", ephemeral=True)


# ─── Cog Principal ────────────────────────────────────────────────────────────

class BoasVindasConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Helper de cor ──────────────────────────────────────────────────────────

    @staticmethod
    def _container_kwargs() -> dict:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        if primary_color_hex:
            return {"accent_colour": disnake.Colour(int(primary_color_hex.replace("#", ""), 16))}
        return {}

    # ── Painel principal ───────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        config = helpers.carregar_config()
        ativado = bool(config.get("ativado", True))
        rota = str(config.get("rota_envio", "canal"))
        ghost_ping_ativo = bool(config.get("ghost_ping_ativo", False))
        ghost_ping_canais = config.get("ghost_ping_canais", [])

        canal_ed = config.get("canal", {}).get("editor_data", {})
        dm_ed = config.get("dm", {}).get("editor_data", {})
        tempo = int(config.get("canal", {}).get("tempo_segundos", 0) or 0)

        def _resumo_rota(ed: dict) -> str:
            has_content = bool(ed.get("content"))
            has_embed = any((ed.get("embed") or {}).get(k) for k in ("title", "description"))
            has_container = bool(ed.get("container"))
            has_image = bool(ed.get("externalImage") or (ed.get("embed") or {}).get("banner"))
            has_buttons = bool(ed.get("botoes"))
            partes = []
            if has_content: partes.append("Mensagem")
            if has_embed: partes.append("Embed")
            if has_container: partes.append("Container")
            if has_image: partes.append("Imagem")
            if has_buttons: partes.append("Botões")
            return ", ".join(partes) if partes else "Vazio"

        rota_label = {
            "canal": "Somente Canal",
            "dm": "Somente DM",
            "canal_dm": "Canal + DM",
        }.get(rota, rota)

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.route} **Rota:** `{rota_label}`\n"
            f"{emoji.clock} **Duração (canal):** `{tempo}s`\n"
            f"{emoji.message} **Mensagem canal:** `{_resumo_rota(canal_ed)}`\n"
            f"{emoji.message} **Mensagem DM:** `{_resumo_rota(dm_ed)}`\n"
            f"{emoji.on if ghost_ping_ativo else emoji.off} **Ghost Ping:** `{'Ativado' if ghost_ping_ativo else 'Desativado'}`"
            + (f" · `{len(ghost_ping_canais)}` canal(is)" if ghost_ping_ativo and ghost_ping_canais else "")
        )

        ghost_ping_buttons = [
            disnake.ui.Button(
                label="Ghost Ping Ativado" if ghost_ping_ativo else "Ghost Ping Desativado",
                style=disnake.ButtonStyle.green if ghost_ping_ativo else disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="BV_ToggleGhostPing",
                disabled=not ativado,
            ),
        ]
        if ghost_ping_ativo:
            ghost_ping_buttons.append(
                disnake.ui.Button(
                    label=f"Canais Ghost Ping ({len(ghost_ping_canais)})",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.textc,
                    custom_id="BV_AbrirCanaisGhostPing",
                    disabled=not ativado,
                )
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Boas-Vindas**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure as mensagens de boas-vindas do servidor.\nCada rota (Canal / DM) possui sua própria mensagem independente."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="BV_ToggleAtivo"),
                    disnake.ui.Button(label="Mudar Rota", style=disnake.ButtonStyle.grey, emoji=emoji.route, custom_id="BV_AbrirRota", disabled=not ativado),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar Mensagem do Canal",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.textc,
                        custom_id="BV_AbrirEditorCanal",
                        disabled=not ativado or rota == "dm",
                    ),
                    disnake.ui.Button(
                        label="Editar Mensagem da DM",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.message,
                        custom_id="BV_AbrirEditorDM",
                        disabled=not ativado or rota == "canal",
                    ),
                ),
                disnake.ui.ActionRow(*ghost_ping_buttons),
                **BoasVindasConfig._container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomacoes"),
            ),
        ]

    # ── Painel Editor por Rota (igual ao PainelEditor do MsgAuto) ─────────────

    @staticmethod
    def PainelEditor(rota: str) -> list:
        editor_data = helpers.get_editor_data(rota)
        config = helpers.carregar_config()
        tempo = int(config.get("canal", {}).get("tempo_segundos", 0) or 0)

        has_message = bool(editor_data.get("content"))
        embed_data = editor_data.get("embed", {})
        has_embed = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        has_container = bool(editor_data.get("container"))
        botoes = editor_data.get("botoes", [])
        has_buttons = isinstance(botoes, list) and len(botoes) > 0
        limite_botoes = isinstance(botoes, list) and len(botoes) >= 5
        has_any = any([has_message, has_embed, has_container, has_image, has_buttons])

        other_fields_disabled = has_container
        rota_label = "Canal" if rota == "canal" else "DM"

        rows = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"BV_ApagarCampo:content:{rota}", disabled=not has_message or other_fields_disabled),
                disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.message, custom_id=f"BV_DefinirMensagem:{rota}", disabled=other_fields_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"BV_ApagarCampo:embed:{rota}", disabled=not has_embed or other_fields_disabled),
                disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id=f"BV_DefinirEmbed:{rota}", disabled=other_fields_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"BV_ApagarImagensMulti:{rota}", disabled=not has_image),
                disnake.ui.Button(label="Definir Imagens", style=disnake.ButtonStyle.grey, emoji=emoji.image, custom_id=f"BV_DefinirImagens:{rota}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"BV_ApagarCampo:container:{rota}", disabled=not has_container),
                disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id=f"BV_DefinirContainer:{rota}", disabled=(has_message or has_embed) and not has_container),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"BV_ApagarCampo:botoes:{rota}", disabled=not has_buttons),
                disnake.ui.Button(label="Botões", style=disnake.ButtonStyle.grey, emoji=emoji.plus, custom_id=f"BV_DefinirBotoes:{rota}", disabled=limite_botoes),
            ),
        ]

        # Linha extra somente para o canal: tempo de duração
        extra_info = f"{emoji.message} **Rota:** `{rota_label}`"
        if rota == "canal":
            extra_info += f"\n{emoji.clock} **Duração:** `{tempo}s`"

        inner = [
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Boas-Vindas > **Editor — {rota_label}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(extra_info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            *rows,
        ]

        bottom_row_btns = [
            disnake.ui.Button(
                label="Visualizar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.search,
                custom_id=f"BV_Visualizar:{rota}",
                disabled=not has_any,
            ),
        ]
        if rota == "canal":
            bottom_row_btns.append(
                disnake.ui.Button(
                    label="Editar Duração",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.clock,
                    custom_id="BV_EditarTempo",
                )
            )

        return [
            disnake.ui.Container(*inner, **BoasVindasConfig._container_kwargs()),
            disnake.ui.ActionRow(*bottom_row_btns),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="BV_VoltarPainelBV"),
            ),
        ]

    # ── Painel de botões (igual ao ButtonManager do MsgAuto) ──────────────────

    @staticmethod
    def PainelBotoes(rota: str) -> list:
        editor_data = helpers.get_editor_data(rota)
        botoes = editor_data.get("botoes", [])
        rota_label = "Canal" if rota == "canal" else "DM"

        options = [
            disnake.SelectOption(
                label=b.get("label", "Sem nome"),
                value=b.get("id"),
                emoji=emoji.plus,
                description=AnunciarButtons.description_names.get(b.get("button", {}).get("type", "disabled"), "Botão"),
            )
            for b in botoes
        ] or [disnake.SelectOption(label="Nenhum botão registrado", value="none")]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Boas-Vindas > Editor {rota_label} > **Botões**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"Configure os botões da mensagem de boas-vindas ({rota_label}).\n"
                    f"**Quantidade:** `{len(botoes)}` · Limite: `5`"
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione um botão para configurar",
                        custom_id=f"BV_Botao_Selecionar:{rota}",
                        options=options,
                        disabled=len(botoes) == 0,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Adicionar botão", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"BV_Botao_Adicionar:{rota}", disabled=len(botoes) >= 5),
                    disnake.ui.Button(label="Apagar todos", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"BV_Botao_ApagarTodos:{rota}", disabled=len(botoes) == 0),
                ),
                **BoasVindasConfig._container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id=f"BV_VoltarEditor:{rota}")
            ),
        ]

    @staticmethod
    def PainelBotaoConfig(rota: str, button_id: str) -> list | None:
        editor_data = helpers.get_editor_data(rota)
        botoes = editor_data.get("botoes", [])
        button = next((b for b in botoes if b.get("id") == button_id), None)
        if not button:
            return None

        label = button.get("label", "Sem label")
        data = button.get("button", {})
        btn_type = data.get("type", "disabled")
        emoji_raw = data.get("emoji")
        emoji_btn = AnunciarButtons.processar_emoji(emoji_raw) if emoji_raw else None
        url = data.get("url")
        style = AnunciarButtons._style_from_str(data.get("style"))
        style_str = data.get("style") or "gray"
        rota_label = "Canal" if rota == "canal" else "DM"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Boas-Vindas > Botões {rota_label} > **{label}**"
                ),
                disnake.ui.Separator(),
                disnake.ui.Section(
                    disnake.ui.TextDisplay(
                        f"**Label:** `{label}`\n"
                        f"**Emoji:** {emoji_btn if emoji_btn else '`Nenhum`'}\n"
                        f"**Tipo:** `{AnunciarButtons.description_names.get(btn_type, 'Desabilitado')}`"
                    ),
                    accessory=disnake.ui.Button(label=label, emoji=emoji_btn, disabled=True, style=style, url=url),
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Estilo do botão",
                        custom_id=f"BV_Botao_Estilo:{rota}:{button_id}",
                        options=[
                            disnake.SelectOption(label="Cinza", value="gray", emoji=emoji.gray, default=style_str in ("gray", "grey")),
                            disnake.SelectOption(label="Verde", value="green", emoji=emoji.green, default=style_str == "green"),
                            disnake.SelectOption(label="Vermelho", value="red", emoji=emoji.red, default=style_str == "red"),
                            disnake.SelectOption(label="Azul", value="blue", emoji=emoji.blue, default=style_str == "blue"),
                        ],
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar botão", emoji=emoji.edit, custom_id=f"BV_Botao_Editar:{rota}:{button_id}", style=disnake.ButtonStyle.blurple),
                    disnake.ui.Button(label="Editar ações", emoji=emoji.route, custom_id=f"BV_Botao_EditarAcoes:{rota}:{button_id}"),
                    disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"BV_Botao_Apagar:{rota}:{button_id}", style=disnake.ButtonStyle.red),
                ),
                **BoasVindasConfig._container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id=f"BV_DefinirBotoes:{rota}")
            ),
        ]

    @staticmethod
    def PainelAcoesBotao(rota: str, button_id: str, inter: disnake.MessageInteraction) -> list | None:
        editor_data = helpers.get_editor_data(rota)
        button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None)
        if not button:
            return None

        data = button.get("button", {})
        current_type = data.get("type")
        action_data = data.get("action") or {}
        action_type = action_data.get("type")
        rota_label = "Canal" if rota == "canal" else "DM"

        extra_row = None
        if current_type == "action":
            role_id = action_data.get("role")
            role = inter.guild.get_role(int(role_id)) if role_id else None
            extra_row = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione o cargo" + (" (adicionar/toggle)" if action_type == "addrole" else " (remover)"),
                    custom_id=f"BV_Botao_Cargo:{rota}:{button_id}:{action_type}",
                    default_values=[role] if role else [],
                )
            )
        elif current_type == "url":
            extra_row = disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar URL", emoji=emoji.edit, custom_id=f"BV_Botao_EditarURL:{rota}:{button_id}", style=disnake.ButtonStyle.blurple)
            )
        elif current_type == "message":
            extra_row = disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar mensagem efêmera", emoji=emoji.edit, custom_id=f"BV_Botao_EditarMensagemEfemera:{rota}:{button_id}", style=disnake.ButtonStyle.blurple)
            )

        inner = [
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Boas-Vindas > Botões {rota_label} > Ações"
            ),
            disnake.ui.Separator(),
        ]
        if extra_row:
            inner.append(extra_row)
        inner.append(
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"BV_Botao_AlterarAcao:{rota}:{button_id}",
                    placeholder="Selecione a ação do botão",
                    options=[
                        disnake.SelectOption(label="Dar Cargo (Toggle)", emoji=emoji.plus, value="DarCargo", default=(current_type == "action" and action_type == "addrole")),
                        disnake.SelectOption(label="Remover Cargo", emoji=emoji.minus, value="RemoverCargo", default=(current_type == "action" and action_type == "removerole")),
                        disnake.SelectOption(label="Mensagem Efêmera", emoji=emoji.message, value="MensagemEfemera", default=(current_type == "message")),
                        disnake.SelectOption(label="URL", emoji=emoji.route, value="URL", default=(current_type == "url")),
                        disnake.SelectOption(label="Desativado", emoji=emoji.wrong, value="Desativado", default=(current_type == "disabled")),
                    ],
                )
            )
        )

        return [
            disnake.ui.Container(*inner, **BoasVindasConfig._container_kwargs()),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id=f"BV_Botao_VerConfig:{rota}:{button_id}")
            ),
        ]

    # ── Painel de seleção de rota ──────────────────────────────────────────────

    @staticmethod
    def PainelSelecionarRota() -> list:
        cfg = helpers.carregar_config()
        rota_atual = str(cfg.get("rota_envio", "canal"))
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Boas-Vindas > **Selecionar Rota**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Escolha para onde as mensagens de boas-vindas serão enviadas.\n"
                    "Você pode ativar **Canal**, **DM** ou ambos simultaneamente.\n"
                    "Cada rota possui sua própria mensagem configurável."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="BV_SelectRota",
                        placeholder="Escolha o(s) destino(s)",
                        options=[
                            disnake.SelectOption(label="Canal", value="canal", description="Envia no canal de boas-vindas", default=(rota_atual in ("canal", "canal_dm"))),
                            disnake.SelectOption(label="DM", value="dm", description="Envia por mensagem direta", default=(rota_atual in ("dm", "canal_dm"))),
                        ],
                        min_values=1,
                        max_values=2,
                    )
                ),
                **BoasVindasConfig._container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="BV_VoltarPainelBV"),
            ),
        ]

    @staticmethod
    def PainelCanaisGhostPing() -> list:
        cfg = helpers.carregar_config()
        canais_atuais = [int(c) for c in (cfg.get("ghost_ping_canais") or []) if str(c).isdigit()]
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Boas-Vindas > **Canais Ghost Ping**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Selecione os canais onde o Ghost Ping será enviado quando um membro entrar.\n"
                    "-# O bot menciona o membro e apaga a mensagem após 2,5 segundos."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="BV_SelectCanaisGhostPing",
                        placeholder="Selecione os canais de ghost ping...",
                        channel_types=[disnake.ChannelType.text],
                        min_values=0,
                        max_values=10,
                        default_values=[disnake.Object(id=c) for c in canais_atuais] if canais_atuais else [],
                    )
                ),
                **BoasVindasConfig._container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="BV_VoltarPainelBV"),
            ),
        ]

    # ── Modais de botão ────────────────────────────────────────────────────────

    class RegistrarBotaoModal(disnake.ui.Modal):
        def __init__(self, rota: str, action: str, button_id: str = None):
            self.rota = rota
            self.action = action
            self.button_id = button_id
            editor_data = helpers.get_editor_data(rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None) if button_id else None
            import uuid
            self._new_id = str(uuid.uuid4())

            super().__init__(
                title="Registrar Botão",
                custom_id=f"BV_BotaoModal_Reg:{rota}:{action}:{button_id or ''}",
                components=[
                    disnake.ui.TextInput(label="Label", custom_id="label", placeholder="Label do botão", required=True, value=button.get("label", "") if button else ""),
                    disnake.ui.TextInput(label="Emoji (opcional)", custom_id="emoji", placeholder="Emoji do botão", required=False, value=(button.get("button", {}).get("emoji") or "") if button else ""),
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            import uuid
            label = inter.text_values.get("label", "").strip()
            emoji_input = inter.text_values.get("emoji", "").strip()

            editor_data = helpers.get_editor_data(self.rota)
            botoes = editor_data.setdefault("botoes", [])

            if self.action == "create":
                if len(botoes) >= 5:
                    await inter.response.send_message("Limite de 5 botões atingido.", ephemeral=True)
                    return
                new_id = str(uuid.uuid4())
                botoes.append({
                    "id": new_id,
                    "label": label,
                    "button": {"type": "disabled", "emoji": emoji_input or None, "url": None, "style": "gray", "disabled": True, "action": {}},
                })
                helpers.set_editor_data(self.rota, editor_data)
                await inter.response.edit_message(components=BoasVindasConfig.PainelBotaoConfig(self.rota, new_id))
            elif self.action == "edit":
                button = next((b for b in botoes if b.get("id") == self.button_id), None)
                if not button:
                    await inter.response.send_message("Botão não encontrado.", ephemeral=True)
                    return
                button["label"] = label
                button["button"]["emoji"] = emoji_input or None
                helpers.set_editor_data(self.rota, editor_data)
                await inter.response.edit_message(components=BoasVindasConfig.PainelBotaoConfig(self.rota, self.button_id))

    class EditarURLBotaoModal(disnake.ui.Modal):
        def __init__(self, rota: str, button_id: str):
            self.rota = rota
            self.button_id = button_id
            editor_data = helpers.get_editor_data(rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None)
            url_val = (button or {}).get("button", {}).get("url") or ""
            super().__init__(
                title="Editar URL",
                custom_id=f"BV_BotaoModal_URL:{rota}:{button_id}",
                components=[
                    disnake.ui.TextInput(label="URL", custom_id="url", placeholder="https://exemplo.com", required=True, value=url_val)
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            url = inter.text_values.get("url", "").strip()
            if not AnunciarButtons._is_valid_url(url):
                await inter.response.send_message(f"{emoji.wrong} URL inválida.", ephemeral=True)
                return
            editor_data = helpers.get_editor_data(self.rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == self.button_id), None)
            if not button: return
            button["button"].update(type="url", url=url, action={}, disabled=False)
            helpers.set_editor_data(self.rota, editor_data)
            await inter.response.edit_message(components=BoasVindasConfig.PainelAcoesBotao(self.rota, self.button_id, inter))

    class EditarMensagemEfemeraBotaoModal(disnake.ui.Modal):
        def __init__(self, rota: str, button_id: str):
            self.rota = rota
            self.button_id = button_id
            editor_data = helpers.get_editor_data(rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None)
            msg_val = ((button or {}).get("button", {}).get("action") or {}).get("message", "") or ""
            super().__init__(
                title="Mensagem Efêmera",
                custom_id=f"BV_BotaoModal_Msg:{rota}:{button_id}",
                components=[
                    disnake.ui.TextInput(label="Mensagem", custom_id="message", placeholder="Texto da mensagem efêmera", required=True, value=msg_val, style=disnake.TextInputStyle.paragraph)
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            text = inter.text_values.get("message", "").strip()
            editor_data = helpers.get_editor_data(self.rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == self.button_id), None)
            if not button: return
            button["button"].update(type="message", url=None, action={"message": text}, disabled=False)
            helpers.set_editor_data(self.rota, editor_data)
            await inter.response.edit_message(components=BoasVindasConfig.PainelAcoesBotao(self.rota, self.button_id, inter))

    # ── Listeners ──────────────────────────────────────────────────────────────

    async def _update_panel(self, inter: disnake.Interaction):
        if not inter.response.is_done():
            await inter.response.defer(with_message=False)
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        await inter.edit_original_message(content=None, components=self.Painel())

    @commands.Cog.listener("on_button_click")
    async def BoasVindas_Button_Listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid or not cid.startswith("BV_"):
            return

        # ── Toggle e navegação principal ──
        if cid == "BV_ToggleAtivo":
            cfg = helpers.carregar_config()
            cfg["ativado"] = not bool(cfg.get("ativado", True))
            db.save_document("automations_boas_vindas", {}, cfg)
            await self._update_panel(inter)

        elif cid == "BV_ToggleGhostPing":
            cfg = helpers.carregar_config()
            cfg["ghost_ping_ativo"] = not bool(cfg.get("ghost_ping_ativo", False))
            db.save_document("automations_boas_vindas", {}, cfg)
            await self._update_panel(inter)

        elif cid == "BV_VoltarPainelBV":
            await self._update_panel(inter)

        elif cid == "BV_AbrirRota":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelSelecionarRota())

        elif cid == "BV_AbrirCanaisGhostPing":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelCanaisGhostPing())

        # ── Abrir editor por rota ──
        elif cid == "BV_AbrirEditorCanal":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelEditor("canal"))

        elif cid == "BV_AbrirEditorDM":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelEditor("dm"))

        elif cid.startswith("BV_VoltarEditor:"):
            rota = cid.split(":", 1)[1]
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelEditor(rota))

        # ── Modais de conteúdo ──
        elif cid.startswith("BV_DefinirMensagem:"):
            rota = cid.split(":", 1)[1]
            await inter.response.send_modal(DefinirMensagemBVModal(rota))

        elif cid.startswith("BV_DefinirEmbed:"):
            rota = cid.split(":", 1)[1]
            await inter.response.send_modal(DefinirEmbedBVModal(rota))

        elif cid.startswith("BV_DefinirImagens:"):
            rota = cid.split(":", 1)[1]
            await inter.response.send_modal(DefinirImagensBVModal(rota))

        elif cid.startswith("BV_DefinirContainer:"):
            rota = cid.split(":", 1)[1]
            await inter.response.send_modal(DefinirContainerBVModal(rota))

        elif cid == "BV_EditarTempo":
            await inter.response.send_modal(EditarTempoBVModal())

        # ── Apagar campos ──
        elif cid.startswith("BV_ApagarCampo:"):
            _, field, rota = cid.split(":", 2)
            if field == "botoes":
                editor_data = helpers.get_editor_data(rota)
                editor_data["botoes"] = []
                helpers.set_editor_data(rota, editor_data)
            else:
                helpers.clear_editor_field(rota, field)
                if field == "embed":
                    # Limpa imagens relacionadas ao embed também
                    editor_data = helpers.get_editor_data(rota)
                    editor_data.pop("embed", None)
                    helpers.set_editor_data(rota, editor_data)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelEditor(rota))

        elif cid.startswith("BV_ApagarImagensMulti:"):
            rota = cid.split(":", 1)[1]
            editor_data = helpers.get_editor_data(rota)
            editor_data["externalImage"] = None
            if "embed" in editor_data:
                editor_data["embed"]["banner"] = None
                editor_data["embed"]["thumbnail"] = None
            helpers.set_editor_data(rota, editor_data)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelEditor(rota))

        # ── Visualizar ──
        elif cid.startswith("BV_Visualizar:"):
            rota = cid.split(":", 1)[1]
            await inter.response.defer(ephemeral=True)
            editor_data = helpers.get_editor_data(rota)
            data_to_build = editor_data.copy()
            # Converte "botoes" → "buttons" para o Builder do anunciar
            if "botoes" in data_to_build:
                data_to_build["buttons"] = data_to_build.pop("botoes")
            built = await Builder.build_from_cfg({"message": data_to_build})
            await self._send_built(inter, built, ephemeral=True)

        # ── Botões: painel de lista ──
        elif cid.startswith("BV_DefinirBotoes:"):
            rota = cid.split(":", 1)[1]
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelBotoes(rota))

        elif cid.startswith("BV_Botao_Adicionar:"):
            rota = cid.split(":", 1)[1]
            await inter.response.send_modal(self.RegistrarBotaoModal(rota, "create"))

        elif cid.startswith("BV_Botao_ApagarTodos:"):
            rota = cid.split(":", 1)[1]
            editor_data = helpers.get_editor_data(rota)
            editor_data["botoes"] = []
            helpers.set_editor_data(rota, editor_data)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelBotoes(rota))

        elif cid.startswith("BV_Botao_Editar:"):
            _, rota, button_id = cid.split(":", 2)
            await inter.response.send_modal(self.RegistrarBotaoModal(rota, "edit", button_id))

        elif cid.startswith("BV_Botao_Apagar:"):
            _, rota, button_id = cid.split(":", 2)
            editor_data = helpers.get_editor_data(rota)
            editor_data["botoes"] = [b for b in editor_data.get("botoes", []) if b.get("id") != button_id]
            helpers.set_editor_data(rota, editor_data)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelBotoes(rota))

        elif cid.startswith("BV_Botao_VerConfig:"):
            _, rota, button_id = cid.split(":", 2)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelBotaoConfig(rota, button_id))

        elif cid.startswith("BV_Botao_EditarAcoes:"):
            _, rota, button_id = cid.split(":", 2)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelAcoesBotao(rota, button_id, inter))

        elif cid.startswith("BV_Botao_EditarURL:"):
            _, rota, button_id = cid.split(":", 2)
            await inter.response.send_modal(self.EditarURLBotaoModal(rota, button_id))

        elif cid.startswith("BV_Botao_EditarMensagemEfemera:"):
            _, rota, button_id = cid.split(":", 2)
            await inter.response.send_modal(self.EditarMensagemEfemeraBotaoModal(rota, button_id))

        # ── Runtime: botão clicado numa mensagem de boas-vindas postada ──
        elif cid.startswith("BV_RuntimeBotao_"):
            await self._handle_runtime_botao(inter, cid)

    @commands.Cog.listener("on_dropdown")
    async def BoasVindas_Dropdown_Listener(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id
        if not cid or not cid.startswith("BV_"):
            return

        if cid == "BV_SelectRota":
            valores = list(inter.values or [])
            if "canal" in valores and "dm" in valores:
                rota = "canal_dm"
            elif "dm" in valores:
                rota = "dm"
            else:
                rota = "canal"
            helpers.salvar_config({"rota_envio": rota})
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelSelecionarRota())

        elif cid == "BV_SelectCanaisGhostPing":
            canais_ids = [str(v.id) if hasattr(v, "id") else str(v) for v in (inter.values or [])]
            helpers.salvar_config({"ghost_ping_canais": canais_ids})
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelCanaisGhostPing())

        elif cid.startswith("BV_Botao_Selecionar:"):
            rota = cid.split(":", 1)[1]
            button_id = inter.values[0] if inter.values else None
            if not button_id or button_id == "none":
                return
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelBotaoConfig(rota, button_id))

        elif cid.startswith("BV_Botao_Estilo:"):
            _, rota, button_id = cid.split(":", 2)
            editor_data = helpers.get_editor_data(rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None)
            if not button: return
            button["button"]["style"] = inter.values[0]
            helpers.set_editor_data(rota, editor_data)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelBotaoConfig(rota, button_id))

        elif cid.startswith("BV_Botao_AlterarAcao:"):
            _, rota, button_id = cid.split(":", 2)
            editor_data = helpers.get_editor_data(rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None)
            if not button: return
            data = button.setdefault("button", {})
            action = data.setdefault("action", {})
            selected = inter.values[0] if inter.values else None

            if selected == "DarCargo":
                existing_role = action.get("role")
                data.update(type="action", url=None, disabled=False)
                data["action"] = {"type": "addrole"}
                if existing_role: data["action"]["role"] = existing_role
                helpers.set_editor_data(rota, editor_data)
                await inter.response.edit_message(components=self.PainelAcoesBotao(rota, button_id, inter))

            elif selected == "RemoverCargo":
                existing_role = action.get("role")
                data.update(type="action", url=None, disabled=False)
                data["action"] = {"type": "removerole"}
                if existing_role: data["action"]["role"] = existing_role
                helpers.set_editor_data(rota, editor_data)
                await inter.response.edit_message(components=self.PainelAcoesBotao(rota, button_id, inter))

            elif selected == "MensagemEfemera":
                msg = (action or {}).get("message")
                if not msg:
                    await inter.response.send_modal(self.EditarMensagemEfemeraBotaoModal(rota, button_id))
                    return
                data.update(type="message", url=None, action={"message": msg}, disabled=False)
                helpers.set_editor_data(rota, editor_data)
                await inter.response.edit_message(components=self.PainelAcoesBotao(rota, button_id, inter))

            elif selected == "URL":
                if not data.get("url") or not AnunciarButtons._is_valid_url(data.get("url")):
                    await inter.response.send_modal(self.EditarURLBotaoModal(rota, button_id))
                    return
                data.update(type="url", action={}, disabled=False)
                helpers.set_editor_data(rota, editor_data)
                await inter.response.edit_message(components=self.PainelAcoesBotao(rota, button_id, inter))

            elif selected == "Desativado":
                data.update(type="disabled", url=None, action={}, disabled=True)
                helpers.set_editor_data(rota, editor_data)
                await inter.response.edit_message(components=self.PainelAcoesBotao(rota, button_id, inter))

        elif cid.startswith("BV_Botao_Cargo:"):
            parts = cid.split(":")
            # BV_Botao_Cargo:{rota}:{button_id}:{action_type}
            _, rota, button_id, action_type = parts
            editor_data = helpers.get_editor_data(rota)
            button = next((b for b in editor_data.get("botoes", []) if b.get("id") == button_id), None)
            if not button: return
            data = button.setdefault("button", {})
            action = data.setdefault("action", {})
            action["type"] = action_type
            if inter.values:
                action["role"] = int(inter.values[0])
            data["disabled"] = False
            helpers.set_editor_data(rota, editor_data)
            await inter.response.edit_message(components=self.PainelAcoesBotao(rota, button_id, inter))

    # ── Helpers internos ───────────────────────────────────────────────────────

    @staticmethod
    async def _send_built(target, built: dict, ephemeral: bool = False):
        """Envia uma mensagem já construída (igual ao MsgAuto)."""
        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
        if ephemeral:
            kwargs["ephemeral"] = True

        if built["mode"] == "v2":
            kwargs["components"] = built["components"]
            kwargs["flags"] = built.get("flags")
            if isinstance(target, disnake.Interaction):
                return await target.followup.send(**kwargs)
            return await target.send(**kwargs)
        else:
            if built.get("content"):
                kwargs["content"] = built["content"]
            if built.get("embed"):
                kwargs["embed"] = built["embed"]
            if built.get("components"):
                kwargs["components"] = built["components"]
            if built.get("files"):
                kwargs["files"] = built["files"]
            if isinstance(target, disnake.Interaction):
                return await target.followup.send(**kwargs)
            return await target.send(**kwargs)

    async def _handle_runtime_botao(self, inter: disnake.MessageInteraction, cid: str):
        """Processa clique num botão de boas-vindas postado."""
        button_id = cid.removeprefix("BV_RuntimeBotao_")
        # Busca em ambas as rotas
        button = None
        for rota in ("canal", "dm"):
            ed = helpers.get_editor_data(rota)
            button = next((b for b in ed.get("botoes", []) if b.get("id") == button_id), None)
            if button:
                break

        if not button:
            await inter.response.send_message(f"{emoji.warn} Botão não encontrado.", ephemeral=True)
            return

        data = button.get("button", {})
        btn_type = data.get("type")
        action = data.get("action") or {}

        if btn_type == "message":
            text = action.get("message") or "Mensagem não configurada."
            if inter.response.is_done():
                await inter.followup.send(text, ephemeral=True)
            else:
                await inter.response.send_message(text, ephemeral=True)

        elif btn_type == "action":
            action_type = action.get("type")
            role_id = action.get("role")
            if not role_id:
                await inter.response.send_message(f"{emoji.warn} Nenhum cargo configurado.", ephemeral=True)
                return
            role = inter.guild.get_role(int(role_id))
            if not role:
                await inter.response.send_message(f"{emoji.warn} Cargo não encontrado.", ephemeral=True)
                return
            member = inter.user if isinstance(inter.user, disnake.Member) else await inter.guild.fetch_member(inter.user.id)
            me: disnake.Member = inter.guild.me
            if not me.guild_permissions.manage_roles or role >= me.top_role:
                await inter.response.send_message(f"{emoji.wrong} Sem permissão para gerenciar este cargo.", ephemeral=True)
                return
            try:
                if action_type == "addrole":
                    if role in member.roles:
                        await member.remove_roles(role)
                        await inter.response.send_message(f"{emoji.correct} Cargo removido: {role.mention}", ephemeral=True)
                    else:
                        await member.add_roles(role)
                        await inter.response.send_message(f"{emoji.correct} Cargo adicionado: {role.mention}", ephemeral=True)
                elif action_type == "removerole":
                    if role in member.roles:
                        await member.remove_roles(role)
                        await inter.response.send_message(f"{emoji.correct} Cargo removido: {role.mention}", ephemeral=True)
                    else:
                        await inter.response.send_message(f"{emoji.warn} Você não possui este cargo.", ephemeral=True)
            except disnake.Forbidden:
                await inter.response.send_message(f"{emoji.wrong} Sem permissão.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(BoasVindasConfig(bot))