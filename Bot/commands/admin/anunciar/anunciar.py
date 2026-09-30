import disnake
from disnake.ext import commands

from functions.database import database
from functions.emoji import emoji
from functions.utils import utils
from functions.message import message
from functions.perms import perms

# Rótulos amigáveis para o modo de envio
SEND_MODE_LABELS = {
    "auto":      "Automático",
    "content":   "Só Texto",
    "embed":     "Embed",
    "container": "Container",
}

# Ordem padrão dos componentes
DEFAULT_ORDER = ["buttons", "selects"]


class Anunciar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── Helpers internos ────────────────────────────────────────────────────

    @staticmethod
    def _safe_get(cfg: dict, path: str, default=None):
        cur = cfg
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    # ─── Estado da mensagem ──────────────────────────────────────────────────

    @staticmethod
    def is_empty() -> bool:
        cfg = database.get_document("messages_anunciar") or {}
        msg = cfg.get("message", {}) or {}

        has_container = Anunciar._safe_get(msg, "container") is not None
        has_message   = bool(Anunciar._safe_get(msg, "content"))
        has_embed     = any([
            Anunciar._safe_get(msg, "embed.title"),
            Anunciar._safe_get(msg, "embed.description"),
            Anunciar._safe_get(msg, "embed.color"),
            Anunciar._safe_get(msg, "embed.footer"),
        ])
        buttons_list = Anunciar._safe_get(msg, "buttons", []) or []
        has_buttons  = isinstance(buttons_list, list) and len(buttons_list) > 0
        selects_list = Anunciar._safe_get(msg, "selects", []) or []
        has_selects  = isinstance(selects_list, list) and len(selects_list) > 0
        has_audio    = bool(Anunciar._safe_get(msg, "audio"))

        return not any([has_message, has_container, has_embed, has_buttons, has_selects, has_audio])

    # ─── Painel principal ────────────────────────────────────────────────────

    @staticmethod
    def create_buttons() -> list:
        # ── Modo Telegram ──
        tg_cfg  = database.get_document("telegram_anunciar") or {}
        tg_mode = tg_cfg.get("mode") == "telegram"

        cfg = database.get_document("messages_anunciar") or {}
        msg = cfg.get("message", {}) or {}

        has_container = Anunciar._safe_get(msg, "container") is not None
        has_message   = bool(Anunciar._safe_get(msg, "content"))
        has_embed     = any([
            Anunciar._safe_get(msg, "embed.title"),
            Anunciar._safe_get(msg, "embed.description"),
            Anunciar._safe_get(msg, "embed.color"),
            Anunciar._safe_get(msg, "embed.footer"),
        ])
        has_image     = any([
            Anunciar._safe_get(msg, "externalImage"),
            Anunciar._safe_get(msg, "embed.banner"),
            Anunciar._safe_get(msg, "embed.thumbnail"),
        ])
        buttons_list = Anunciar._safe_get(msg, "buttons", []) or []
        has_buttons  = isinstance(buttons_list, list) and len(buttons_list) > 0
        selects_list = Anunciar._safe_get(msg, "selects", []) or []
        has_selects  = isinstance(selects_list, list) and len(selects_list) > 0
        has_audio    = bool(Anunciar._safe_get(msg, "audio"))

        others_exist = has_embed
        has_any      = any([has_message, has_container, has_embed, has_buttons, has_selects, has_audio])

        # Ordem dos componentes
        comp_order = msg.get("component_order", DEFAULT_ORDER)
        order_strs = []
        for i, c in enumerate(comp_order, 1):
            icon = emoji.plus if c == "buttons" else emoji.route
            name = "Botões" if c == "buttons" else "Selects"
            order_strs.append(f"`{i}.` {icon} **{name}**")
        order_display = " → ".join(order_strs) if order_strs else "`Padrão`"

        # Modo de envio
        send_mode       = msg.get("send_mode", "auto")
        send_mode_label = SEND_MODE_LABELS.get(send_mode, "Automático")

        def _row(label, define_id, delete_id, icon_define, has_value, define_disabled=False):
            return disnake.ui.ActionRow(
                disnake.ui.Button(
                    style=disnake.ButtonStyle.red,
                    custom_id=delete_id,
                    emoji=emoji.delete,
                    disabled=not has_value,
                ),
                disnake.ui.Button(
                    label=f"Definir {label}",
                    style=disnake.ButtonStyle.secondary,
                    custom_id=define_id,
                    emoji=icon_define,
                    disabled=define_disabled,
                ),
            )

        # Toggle label/emoji
        toggle_label = "Modo: Telegram" if tg_mode else "Modo: Discord"
        toggle_emoji = emoji.on if tg_mode else emoji.off

        if tg_mode:
            # ── Painel no modo Telegram ────────────────────────────────────────
            tg_text      = tg_cfg.get("text") or ""
            tg_image     = tg_cfg.get("image_url") or ""
            tg_chat      = tg_cfg.get("chat_id") or ""
            tg_buttons   = tg_cfg.get("buttons") or []
            tg_has_any   = bool(tg_text or tg_image)
            tg_text_prev = (tg_text[:60] + "…") if len(tg_text) > 60 else tg_text or "_(não definido)_"

            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}"),
                    disnake.ui.TextDisplay(
                        "Modo **Telegram** ativo. Configure a mensagem e envie pelo bot PTB.\n"
                        "Container, Embed, Áudio e Selects não são suportados pelo Telegram."
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                    disnake.ui.TextDisplay(
                        f"**Texto:** {tg_text_prev}\n"
                        f"**Imagem URL:** {tg_image or '_(não definida)_'}\n"
                        f"**Chat ID:** `{tg_chat or 'não definido'}`\n"
                        f"**Botões inline:** {len(tg_buttons)} configurado(s)"
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Configurar Telegram",
                            style=disnake.ButtonStyle.secondary,
                            emoji=emoji.edit,
                            custom_id="Anunciar_TelegramConfig",
                        ),
                        disnake.ui.Button(
                            label=toggle_label,
                            style=disnake.ButtonStyle.secondary,
                            emoji=toggle_emoji,
                            custom_id="Anunciar_ToggleTelegram",
                        ),
                    ),
                ),

                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Apagar tudo", style=disnake.ButtonStyle.red,   emoji=emoji.delete, custom_id="Anunciar_ApagarTudo",    disabled=not tg_has_any),
                    disnake.ui.Button(label="Postar",      style=disnake.ButtonStyle.green, emoji=emoji.arrow,  custom_id="Anunciar_PostarMensagem", disabled=not tg_has_any),
                ),
            ]
        else:
            # ── Painel no modo Discord (original) ─────────────────────────────
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}"),
                    disnake.ui.TextDisplay(
                        "Crie, personalize e anuncie mensagens em canais.\n"
                        "Aplique e salve templates de mensagens."
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                    _row("Mensagem",  "Anunciar_DefinirMensagem",  "Anunciar_ApagarMensagem",  emoji.message,  has_message),
                    _row("Container", "Anunciar_DefinirContainer", "Anunciar_ApagarContainer", emoji.commands, has_container, define_disabled=others_exist),
                    _row("Embed",     "Anunciar_DefinirEmbed",     "Anunciar_ApagarEmbed",     emoji.embed,    has_embed,     define_disabled=has_container),
                    _row("Imagens",   "Anunciar_DefinirImagem",    "Anunciar_ApagarImagem",    emoji.image,    has_image),
                    _row("Áudio",     "Anunciar_AbrirAudio",       "Anunciar_ApagarAudio",     emoji.message,  has_audio),

                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                    _row("Botões",  "Anunciar_DefinirBotoes",  "Anunciar_ApagarBotoes",  emoji.plus,  has_buttons),
                    _row("Selects", "Anunciar_DefinirSelects", "Anunciar_ApagarSelects", emoji.route, has_selects),

                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                    disnake.ui.TextDisplay(
                        f"-# {emoji.flag} Ordem: {order_display}  ·  "
                        f"{emoji.arrow} Modo: **{send_mode_label}**"
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Ordenar componentes",
                            style=disnake.ButtonStyle.secondary,
                            emoji=emoji.edit,
                            custom_id="Anunciar_OrdenarComponentes",
                            disabled=not (has_buttons or has_selects),
                        ),
                        disnake.ui.Button(
                            label="Modo de envio",
                            style=disnake.ButtonStyle.secondary,
                            emoji=emoji.save,
                            custom_id="Anunciar_ModoEnvio",
                        ),
                        disnake.ui.Button(
                            label=toggle_label,
                            style=disnake.ButtonStyle.secondary,
                            emoji=toggle_emoji,
                            custom_id="Anunciar_ToggleTelegram",
                        ),
                    ),
                ),

                # ── Linha de ações principais ──
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Apagar tudo",      style=disnake.ButtonStyle.red,      emoji=emoji.delete, custom_id="Anunciar_ApagarTudo",       disabled=not has_any),
                    disnake.ui.Button(label="Visualizar",       style=disnake.ButtonStyle.secondary, emoji=emoji.search, custom_id="Anunciar_Visualizar",        disabled=not has_any),
                    disnake.ui.Button(label="Postar",           style=disnake.ButtonStyle.green,     emoji=emoji.arrow,  custom_id="Anunciar_PostarMensagem",    disabled=not has_any),
                    disnake.ui.Button(label="Importar do site", style=disnake.ButtonStyle.blurple,   emoji=emoji.route,  custom_id="Anunciar_ImportarDoSite"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Salvar template",  style=disnake.ButtonStyle.secondary, emoji=emoji.save, custom_id="Anunciar_SalvarTemplate",  disabled=not has_any),
                    disnake.ui.Button(label="Templates salvos", style=disnake.ButtonStyle.blurple,   emoji=emoji.flag, custom_id="Anunciar_Templates"),
                ),
            ]

        return components

    # ─── Painel de ordenação de componentes ──────────────────────────────────

    @staticmethod
    def create_order_panel() -> list:
        cfg        = database.get_document("messages_anunciar") or {}
        msg        = cfg.get("message", {}) or {}
        comp_order = list(msg.get("component_order", DEFAULT_ORDER))
        for c in DEFAULT_ORDER:
            if c not in comp_order:
                comp_order.append(c)

        rows = []
        for i, comp_key in enumerate(comp_order):
            icon = emoji.plus if comp_key == "buttons" else emoji.route
            name = "Botões" if comp_key == "buttons" else "Selects"
            rows.append(
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        emoji=emoji.up,
                        style=disnake.ButtonStyle.secondary,
                        custom_id=f"Anunciar_Ordem_Subir_{comp_key}",
                        disabled=(i == 0),
                    ),
                    disnake.ui.Button(
                        emoji=emoji.down,
                        style=disnake.ButtonStyle.secondary,
                        custom_id=f"Anunciar_Ordem_Descer_{comp_key}",
                        disabled=(i == len(comp_order) - 1),
                    ),
                    disnake.ui.Button(
                        label=f"{icon} {name}",
                        style=disnake.ButtonStyle.secondary,
                        custom_id=f"Anunciar_Ordem_Info_{comp_key}",
                        disabled=True,
                    ),
                )
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Anunciar > Ordenar Componentes"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Defina a ordem em que **Botões** e **Select Menus** aparecem na mensagem.\n"
                    "Use **▲** e **▼** para reposicionar cada tipo."
                ),
                disnake.ui.Separator(),
                *rows,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial")
            ),
        ]

    # ─── Painel de modo de envio ──────────────────────────────────────────────

    @staticmethod
    def create_send_mode_panel() -> list:
        cfg       = database.get_document("messages_anunciar") or {}
        msg       = cfg.get("message", {}) or {}
        send_mode = msg.get("send_mode", "auto")

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Anunciar > Modo de Envio"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Escolha como a mensagem será enviada.\n\n"
                    f"**Modo atual:** `{SEND_MODE_LABELS.get(send_mode, 'Automático')}`\n\n"
                    "- **Automático** — detecta o melhor modo com base no conteúdo configurado\n"
                    "- **Só Texto** — envia somente o campo *Mensagem*, ignorando embed e container\n"
                    "- **Embed** — força o modo embed (título, descrição, cor, footer)\n"
                    "- **Container** — força o modo container/v2 (componentes avançados)"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione o modo de envio",
                        custom_id="Anunciar_ModoEnvio_Selecionar",
                        options=[
                            disnake.SelectOption(
                                label="Automático",
                                value="auto",
                                emoji=emoji.search,
                                default=send_mode == "auto",
                                description="Detecta automaticamente o melhor modo.",
                            ),
                            disnake.SelectOption(
                                label="Só Texto",
                                value="content",
                                emoji=emoji.message,
                                default=send_mode == "content",
                                description="Envia apenas o texto da mensagem.",
                            ),
                            disnake.SelectOption(
                                label="Embed",
                                value="embed",
                                emoji=emoji.embed,
                                default=send_mode == "embed",
                                description="Força o envio em modo embed.",
                            ),
                            disnake.SelectOption(
                                label="Container (v2)",
                                value="container",
                                emoji=emoji.commands,
                                default=send_mode == "container",
                                description="Força o modo container (componentes v2).",
                            ),
                        ],
                    )
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial")
            ),
        ]

    # ─── Slash command ────────────────────────────────────────────────────────

    @commands.slash_command(
        name="anunciar",
        description="Crie, personalize e anuncie mensagens em canais.",
        guild_ids=[utils.obter_server_principal()],
    )
    async def anunciar(self, inter: disnake.ApplicationCommandInteraction):
        if not await perms.check(inter.user.id):
            await inter.response.send_message(
                components=[disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Você não tem permissão para usar este comando")
                )],
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True,
            )
            return

        await inter.response.send_message(
            components=self.create_buttons(),
            flags=disnake.MessageFlags(is_components_v2=True),
            ephemeral=True,
        )

        # Registra o ID da mensagem do painel para o on_message de áudio poder editá-la
        panel_msg = await inter.original_message()
        db = database.get_document("messages_anunciar")
        db.setdefault("_meta", {})["panel_message_id"] = panel_msg.id
        db["_meta"]["panel_channel_id"] = inter.channel.id
        database.save_document("messages_anunciar", {}, db)

    # ─── Listeners ────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Voltar ao painel inicial ──
        if cid == "Anunciar_PainelInicial":
            await inter.response.edit_message(components=self.create_buttons())

        # ── Apagar tudo ──
        elif cid == "Anunciar_ApagarTudo":
            tg_cfg = database.get_document("telegram_anunciar") or {}
            if tg_cfg.get("mode") == "telegram":
                return  # TelegramAnunciar cuida disso nesse modo
            db = database.get_document("messages_anunciar")
            db["message"]["content"]       = None
            db["message"]["container"]     = None
            db["message"]["externalImage"] = None
            db["message"]["audio"]         = None
            db["message"]["buttons"]       = []
            db["message"]["selects"]       = []
            for key in db["message"]["embed"]:
                db["message"]["embed"][key] = None
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=Anunciar.create_buttons())

        # ── Ordenar componentes ──
        elif cid == "Anunciar_OrdenarComponentes":
            await inter.response.edit_message(components=Anunciar.create_order_panel())

        elif cid.startswith("Anunciar_Ordem_Subir_") or cid.startswith("Anunciar_Ordem_Descer_"):
            is_up    = cid.startswith("Anunciar_Ordem_Subir_")
            comp_key = cid.removeprefix("Anunciar_Ordem_Subir_" if is_up else "Anunciar_Ordem_Descer_")

            db         = database.get_document("messages_anunciar")
            msg_data   = db.get("message", {})
            comp_order = list(msg_data.get("component_order", DEFAULT_ORDER))
            for c in DEFAULT_ORDER:
                if c not in comp_order:
                    comp_order.append(c)

            idx = comp_order.index(comp_key) if comp_key in comp_order else -1
            if idx >= 0:
                new_idx = idx - 1 if is_up else idx + 1
                if 0 <= new_idx < len(comp_order):
                    comp_order[idx], comp_order[new_idx] = comp_order[new_idx], comp_order[idx]
                    msg_data["component_order"] = comp_order
                    database.save_document("messages_anunciar", {}, db)

            await inter.response.edit_message(components=Anunciar.create_order_panel())

        # ── Modo de envio ──
        elif cid == "Anunciar_ModoEnvio":
            await inter.response.edit_message(components=Anunciar.create_send_mode_panel())

        # ── Apagar áudio (atalho do painel principal) ──
        elif cid == "Anunciar_ApagarAudio":
            db = database.get_document("messages_anunciar")
            db.setdefault("message", {})["audio"] = None
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=Anunciar.create_buttons())

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "Anunciar_ModoEnvio_Selecionar":
            selected = inter.values[0] if inter.values else "auto"
            db       = database.get_document("messages_anunciar")
            db.get("message", {})["send_mode"] = selected
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=Anunciar.create_send_mode_panel())