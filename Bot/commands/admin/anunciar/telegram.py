"""
commands/admin/anunciar/telegram.py

Painel Telegram do /anunciar.
Cuida de:
  - Toggle de modo Discord/Telegram                 (Anunciar_ToggleTelegram)
  - Subpainel de configuração Telegram              (Anunciar_TelegramConfig)
  - Modais: texto, imagem URL, chat_id, botão       (AnunciarTg_*)
  - Select de parse mode                            (AnunciarTg_ParseMode)
  - Remoção individual de botões                    (AnunciarTg_RemoverBotao_<idx>)
  - Apagar tudo (modo telegram)                     (Anunciar_ApagarTudo) — intercepta quando modo=telegram
  - Envio pelo Telegram                             (Anunciar_PostarMensagem) — intercepta quando modo=telegram
    ↳ Escolha: canal configurado OU broadcast todos os usuários com /start
"""

import disnake
from disnake.ext import commands

from functions.database import database
from functions.emoji import emoji
from functions.message import message

# ─── Helpers de DB ────────────────────────────────────────────────────────────

def _get_tg() -> dict:
    return database.get_document("telegram_anunciar") or {}


def _save_tg(doc: dict):
    database.save_document("telegram_anunciar", {}, doc)


def _tg_mode() -> bool:
    return _get_tg().get("mode") == "telegram"


# ─── Helpers de painel ────────────────────────────────────────────────────────

PARSE_MODE_OPTIONS = [
    disnake.SelectOption(label="Markdown",  value="Markdown", description="*negrito*, _itálico_, `código`"),
    disnake.SelectOption(label="HTML",      value="HTML",     description="<b>negrito</b>, <i>itálico</i>"),
    disnake.SelectOption(label="Nenhum",    value="none",     description="Texto simples, sem formatação"),
]


def _build_config_panel() -> list:
    tg = _get_tg()
    text       = tg.get("text") or ""
    image_url  = tg.get("image_url") or ""
    chat_id    = tg.get("chat_id") or ""
    parse_mode = tg.get("parse_mode") or "Markdown"
    buttons    = tg.get("buttons") or []

    text_preview = (text[:80] + "…") if len(text) > 80 else text or "_(não definido)_"

    # Botões configurados
    btn_lines = []
    for i, b in enumerate(buttons):
        label = b.get("label", "?")
        if b.get("url"):
            btn_lines.append(f"`{i+1}.` 🔗 **{label}** — {b['url']}")
        else:
            resp = (b.get("callback_answer") or "")
            resp = (resp[:40] + "…") if len(resp) > 40 else resp
            btn_lines.append(f"`{i+1}.` 💬 **{label}** — resposta: {resp or '_(vazia)_'}")
    btn_display = "\n".join(btn_lines) if btn_lines else "_(nenhum)_"

    opts_with_default = [
        disnake.SelectOption(
            label=o.label,
            value=o.value,
            description=o.description,
            default=o.value == (parse_mode if parse_mode else "none"),
        )
        for o in PARSE_MODE_OPTIONS
    ]

    rows_botoes = []
    for i, b in enumerate(buttons):
        label = b.get("label", "?")
        rows_botoes.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=f"✕ {label}",
                    style=disnake.ButtonStyle.red,
                    custom_id=f"AnunciarTg_RemoverBotao_{i}",
                ),
            )
        )

    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Anunciar > Configuração Telegram"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

            disnake.ui.TextDisplay(
                f"**Texto:**\n{text_preview}\n\n"
                f"**Imagem URL:** {image_url or '_(não definida)_'}\n\n"
                f"**Chat ID de destino:** `{chat_id or 'não definido'}`\n\n"
                f"**Parse Mode:** `{parse_mode}`\n\n"
                f"**Botões inline:**\n{btn_display}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

            # Linha: texto + imagem
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Definir Texto",
                    style=disnake.ButtonStyle.secondary,
                    emoji=emoji.message,
                    custom_id="AnunciarTg_DefinirTexto",
                ),
                disnake.ui.Button(
                    label="Definir Imagem URL",
                    style=disnake.ButtonStyle.secondary,
                    emoji=emoji.image,
                    custom_id="AnunciarTg_DefinirImagem",
                ),
            ),
            # Linha: chat_id + botão inline
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Definir Chat ID",
                    style=disnake.ButtonStyle.secondary,
                    emoji=emoji.flag,
                    custom_id="AnunciarTg_DefinirChatId",
                ),
                disnake.ui.Button(
                    label="Adicionar Botão",
                    style=disnake.ButtonStyle.secondary,
                    emoji=emoji.plus,
                    custom_id="AnunciarTg_AdicionarBotao",
                ),
            ),

            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

            # Select de parse mode
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Parse Mode",
                    custom_id="AnunciarTg_ParseMode",
                    options=opts_with_default,
                )
            ),

            # Botões a remover
            *rows_botoes,
        ),

        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial"),
        ),
    ]

    return components


def _build_post_panel() -> list:
    """Painel de envio Telegram: escolha entre canal configurado ou broadcast."""
    tg      = _get_tg()
    chat_id = tg.get("chat_id") or ""
    has_content = bool(tg.get("text") or tg.get("image_url"))

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"-# Selecione o destino do envio pelo Telegram"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Chat ID configurado:** `{chat_id or 'não definido'}`\n\n"
                "**Broadcast:** envia para todos os usuários que já deram `/start` no bot."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Enviar para o Chat ID configurado",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.arrow,
                    custom_id="AnunciarTg_EnviarCanalConfig",
                    disabled=not (chat_id and has_content),
                ),
                disnake.ui.Button(
                    label="Broadcast — todos os usuários",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.route,
                    custom_id="AnunciarTg_EnviarBroadcast",
                    disabled=not has_content,
                ),
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial"),
        ),
    ]


# ─── Helpers de envio ─────────────────────────────────────────────────────────

async def _build_inline_kb(buttons: list):
    """Retorna um InlineKeyboardMarkup ou None.

    Cada botão é OU de URL (abre link) OU de callback (interativo — ao
    clicar, o bot responde com um alerta usando `callback_answer`).
    O índice na lista é usado como callback_data (`anunciar_btn:<i>`).
    """
    if not buttons:
        return None
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    for i, b in enumerate(buttons):
        label = b.get("label")
        if not label:
            continue
        if b.get("url"):
            rows.append([InlineKeyboardButton(label, url=b["url"])])
        elif b.get("callback_answer"):
            rows.append([InlineKeyboardButton(label, callback_data=f"anunciar_btn:{i}")])
    return InlineKeyboardMarkup(rows) if rows else None


async def anunciar_callback_responder(update, context):
    """Handler PTB genérico pra botões interativos do /anunciar (registrar em runner.py)."""
    from telegram.error import BadRequest

    query = update.callback_query
    try:
        idx = int(query.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await query.answer()
        return

    tg = _get_tg()
    buttons = tg.get("buttons") or []
    resposta = "Ok!"
    if 0 <= idx < len(buttons):
        resposta = buttons[idx].get("callback_answer") or resposta

    try:
        await query.answer(text=resposta, show_alert=True)
    except BadRequest:
        await query.answer()


async def _send_to_chat(app, chat_id: str, tg: dict) -> str:
    """Envia para um único chat_id. Retorna a descrição do resultado."""
    text       = tg.get("text") or ""
    image_url  = tg.get("image_url")
    parse_mode = tg.get("parse_mode") or None
    if parse_mode == "none":
        parse_mode = None
    buttons = tg.get("buttons") or []
    reply_markup = await _build_inline_kb(buttons)

    if image_url:
        await app.bot.send_photo(
            chat_id,
            photo=image_url,
            caption=text or None,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    else:
        await app.bot.send_message(
            chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    return str(chat_id)


async def _do_broadcast(app, tg: dict) -> tuple[int, int]:
    """Envia para todos os usuários com /start registrado.
    Remove da lista quem bloqueou o bot (Forbidden).
    Retorna (enviados, falhas).
    """
    from telegram.error import Forbidden

    users_doc = database.get_document("telegram_users") or {}
    users     = users_doc.get("users") or {}  # dict chat_id → data
    if not users:
        return 0, 0

    ok = 0
    fail = 0
    bloqueados = []
    for chat_id in list(users.keys()):
        try:
            await _send_to_chat(app, chat_id, tg)
            ok += 1
        except Forbidden:
            fail += 1
            bloqueados.append(chat_id)
        except Exception:
            fail += 1

    if bloqueados:
        for chat_id in bloqueados:
            users.pop(chat_id, None)
        users_doc["users"] = users
        database.save_document("telegram_users", {}, users_doc)

    return ok, fail


# ─── Modals ───────────────────────────────────────────────────────────────────

class ModalDefinirTexto(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Definir texto Telegram",
            custom_id="AnunciarTg_DefinirTexto",
            components=[
                disnake.ui.TextInput(
                    label="Texto da mensagem",
                    custom_id="text",
                    style=disnake.TextInputStyle.paragraph,
                    max_length=4000,
                    required=False,
                    placeholder="Suporta Markdown do Telegram: *negrito*, _itálico_, `código`…",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        text = inter.text_values.get("text", "").strip()
        tg = _get_tg()
        tg["text"] = text or None
        _save_tg(tg)
        await inter.response.edit_message(components=_build_config_panel())


class ModalDefinirImagem(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Definir imagem por URL",
            custom_id="AnunciarTg_DefinirImagem",
            components=[
                disnake.ui.TextInput(
                    label="URL da imagem",
                    custom_id="image_url",
                    style=disnake.TextInputStyle.short,
                    max_length=500,
                    required=False,
                    placeholder="https://exemplo.com/imagem.jpg",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        url = inter.text_values.get("image_url", "").strip()
        tg = _get_tg()
        tg["image_url"] = url or None
        _save_tg(tg)
        await inter.response.edit_message(components=_build_config_panel())


class ModalDefinirChatId(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Definir Chat ID de destino",
            custom_id="AnunciarTg_DefinirChatId",
            components=[
                disnake.ui.TextInput(
                    label="Chat ID ou @username do canal",
                    custom_id="chat_id",
                    style=disnake.TextInputStyle.short,
                    max_length=100,
                    required=False,
                    placeholder="-1001234567890 ou @meucanal",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        chat_id = inter.text_values.get("chat_id", "").strip()
        tg = _get_tg()
        tg["chat_id"] = chat_id or None
        _save_tg(tg)
        await inter.response.edit_message(components=_build_config_panel())


class ModalAdicionarBotao(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar botão inline",
            custom_id="AnunciarTg_AdicionarBotao",
            components=[
                disnake.ui.TextInput(
                    label="Label do botão",
                    custom_id="label",
                    style=disnake.TextInputStyle.short,
                    max_length=64,
                    required=True,
                    placeholder="ex: Acessar site / Mais detalhes",
                ),
                disnake.ui.TextInput(
                    label="URL (deixe vazio se for botão interativo)",
                    custom_id="url",
                    style=disnake.TextInputStyle.short,
                    max_length=500,
                    required=False,
                    placeholder="https://exemplo.com",
                ),
                disnake.ui.TextInput(
                    label="Resposta ao clicar (se for callback)",
                    custom_id="callback_answer",
                    style=disnake.TextInputStyle.paragraph,
                    max_length=200,
                    required=False,
                    placeholder="Só preencha se NÃO tiver URL. Ex: 'Fale com o suporte em @canal'",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        label    = inter.text_values.get("label", "").strip()
        url      = inter.text_values.get("url", "").strip()
        resposta = inter.text_values.get("callback_answer", "").strip()

        if not label or not (url or resposta):
            await inter.response.send_message(
                "Informe o label e, ou uma URL, ou uma resposta de callback.",
                ephemeral=True,
            )
            return

        btn = {"label": label}
        if url:
            # URL tem prioridade — Telegram não permite url + callback_data no mesmo botão
            btn["url"] = url
        else:
            btn["callback_answer"] = resposta

        tg = _get_tg()
        tg.setdefault("buttons", []).append(btn)
        _save_tg(tg)
        await inter.response.edit_message(components=_build_config_panel())


# ─── Cog ──────────────────────────────────────────────────────────────────────

class TelegramAnunciar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Botões ────────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        from .anunciar import Anunciar

        cid = inter.component.custom_id

        # ── Toggle modo Discord/Telegram ──
        if cid == "Anunciar_ToggleTelegram":
            tg = _get_tg()
            tg["mode"] = "discord" if tg.get("mode") == "telegram" else "telegram"
            _save_tg(tg)
            await inter.response.edit_message(components=Anunciar.create_buttons())

        # ── Abrir subpainel de configuração Telegram ──
        elif cid == "Anunciar_TelegramConfig":
            await inter.response.edit_message(components=_build_config_panel())

        # ── Modals de texto / imagem / chat_id / botão ──
        elif cid == "AnunciarTg_DefinirTexto":
            await inter.response.send_modal(ModalDefinirTexto())

        elif cid == "AnunciarTg_DefinirImagem":
            await inter.response.send_modal(ModalDefinirImagem())

        elif cid == "AnunciarTg_DefinirChatId":
            await inter.response.send_modal(ModalDefinirChatId())

        elif cid == "AnunciarTg_AdicionarBotao":
            await inter.response.send_modal(ModalAdicionarBotao())

        # ── Remover botão individual ──
        elif cid.startswith("AnunciarTg_RemoverBotao_"):
            idx_str = cid.removeprefix("AnunciarTg_RemoverBotao_")
            try:
                idx = int(idx_str)
            except ValueError:
                return
            tg = _get_tg()
            buttons = tg.get("buttons") or []
            if 0 <= idx < len(buttons):
                buttons.pop(idx)
                tg["buttons"] = buttons
                _save_tg(tg)
            await inter.response.edit_message(components=_build_config_panel())

        # ── Apagar tudo (modo telegram) ──
        elif cid == "Anunciar_ApagarTudo" and _tg_mode():
            tg = _get_tg()
            tg["text"]      = None
            tg["image_url"] = None
            tg["buttons"]   = []
            _save_tg(tg)
            await inter.response.edit_message(components=Anunciar.create_buttons())

        # ── Postar → mostrar painel de destino do Telegram ──
        elif cid == "Anunciar_PostarMensagem" and _tg_mode():
            await inter.response.edit_message(components=_build_post_panel())

        # ── Enviar para o chat_id configurado ──
        elif cid == "AnunciarTg_EnviarCanalConfig":
            await self._enviar_canal_config(inter)

        # ── Broadcast para todos os usuários ──
        elif cid == "AnunciarTg_EnviarBroadcast":
            await self._enviar_broadcast(inter)

    # ── Dropdowns ─────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "AnunciarTg_ParseMode":
            selected = inter.values[0] if inter.values else "Markdown"
            tg = _get_tg()
            tg["parse_mode"] = selected
            _save_tg(tg)
            await inter.response.edit_message(components=_build_config_panel())

    # ── Lógica de envio ───────────────────────────────────────────────────────

    async def _get_app(self, inter: disnake.MessageInteraction):
        app = getattr(inter.bot, "telegram_app", None)
        if not app:
            await message.error(inter, "Bot do Telegram não está rodando.", send=False)
        return app

    async def _enviar_canal_config(self, inter: disnake.MessageInteraction):
        from .anunciar import Anunciar

        await inter.response.defer(with_message=False)
        app = await self._get_app(inter)
        if not app:
            return

        tg      = _get_tg()
        chat_id = tg.get("chat_id")
        if not chat_id:
            await message.error(inter, "Chat ID não configurado. Acesse **Configurar Telegram** e defina o destino.", followup=True)
            return

        try:
            await _send_to_chat(app, chat_id, tg)
        except Exception as e:
            await message.error(inter, f"Erro ao enviar pelo Telegram: {e}", followup=True)
            return

        await inter.edit_original_message(components=Anunciar.create_buttons())
        await message.success(
            inter,
            f"Mensagem enviada com sucesso para `{chat_id}` pelo Telegram!",
            followup=True,
        )

    async def _enviar_broadcast(self, inter: disnake.MessageInteraction):
        from .anunciar import Anunciar

        await inter.response.defer(with_message=False)
        app = await self._get_app(inter)
        if not app:
            return

        tg = _get_tg()

        try:
            ok, fail = await _do_broadcast(app, tg)
        except Exception as e:
            await message.error(inter, f"Erro no broadcast: {e}", followup=True)
            return

        await inter.edit_original_message(components=Anunciar.create_buttons())
        await message.success(
            inter,
            f"Broadcast concluído! ✅ {ok} enviados · ❌ {fail} falhas.",
            followup=True,
        )


def setup(bot: commands.Bot):
    bot.add_cog(TelegramAnunciar(bot))
