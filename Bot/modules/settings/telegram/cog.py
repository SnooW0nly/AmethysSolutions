"""
modules/settings/telegram/cog.py

Painel de Configurar Telegram — Settings.
Aqui só valida e salva o token do bot + chat ID padrão.
O sistema de notificações via Telegram em si fica em outra seção.

Fluxo:
  Painel_Configuracoes  →  Select "telegram"  →  panel()
    ├─ ConfigTelegram_Abrir    → modal de token/chat id (valida via aiogram)
    └─ ConfigTelegram_Remover  → limpa a configuração salva
"""

import re
import disnake
from disnake.ext import commands
from telegram import Bot
from telegram.error import InvalidToken, NetworkError, TimedOut

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

TOKEN_REGEX = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,40}$")


async def validate_telegram(token: str):
    """Valida o token do bot via get_me()."""
    try:
        async with Bot(token=token) as bot:
            try:
                me = await bot.get_me()
            except InvalidToken:
                return False, "Token inválido ou revogado pelo Telegram.", None
            except (NetworkError, TimedOut):
                return False, "Não foi possível conectar à API do Telegram. Tente novamente.", None

            return True, None, {"bot_username": me.username, "bot_id": me.id}
    except Exception:
        return False, "Erro inesperado ao validar com o Telegram.", None


# ─────────────────────────────────────────────────────────────────────────────
# Modal
# ─────────────────────────────────────────────────────────────────────────────


async def _restart_telegram(token: str, bot):
    from modules.telegram.runner import stop_telegram_bot, start_telegram_bot
    await stop_telegram_bot()
    await start_telegram_bot(token, bot)


class TelegramModal(disnake.ui.Modal):
    def __init__(self, cog):
        self.cog = cog
        config = TelegramConfig.get_config()
        super().__init__(
            title="Configurar Telegram",
            custom_id="ConfigTelegram_Modal",
            components=[
                disnake.ui.TextInput(
                    label="Token do Bot",
                    placeholder="123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ",
                    custom_id="input_token",
                    value=config.get("token") or None,
                    min_length=20, max_length=60,
                    style=disnake.TextInputStyle.short,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        token = inter.text_values["input_token"].strip()
        if not TOKEN_REGEX.match(token):
            await inter.followup.send(
                f"{emoji.error} Token em formato inválido. Esperado algo como `123456789:ABC-Def1234ghIkl...`.",
                ephemeral=True,
            )
            return


        ok, error_msg, info = await validate_telegram(token)
        if not ok:
            await inter.followup.send(f"{emoji.wrong} {error_msg}", ephemeral=True)
            return

        config = TelegramConfig.get_config()
        config.update({
            "token": token,
            "bot_username": info["bot_username"],
            "bot_id": info["bot_id"],
            "validated": True,
        })
        db.save_document("telegram_config", config)

        # Inicia/reinicia o bot do Telegram sem precisar reiniciar o processo
        try:
            import asyncio
            from modules.telegram.runner import start_telegram_bot, stop_telegram_bot
            bot = self.cog.bot
            asyncio.create_task(_restart_telegram(config["token"], bot))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[Telegram] Erro ao reiniciar bot: {e}")

        panel = TelegramConfig.panel(inter, config)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel)

        await inter.followup.send(
            f"{emoji.correct} Telegram configurado! Bot: **@{info['bot_username']}** ",
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cog
# ─────────────────────────────────────────────────────────────────────────────

class TelegramConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def get_config() -> dict:
        config = db.get_document("telegram_config")
        if not config:
            config = {
                "token": None,
                "bot_username": None, "bot_id": None,
                "validated": False,
            }
            db.save_document("telegram_config", config)
        return config

    @staticmethod
    def _colors():
        colors = db.get_document("custom_colors")
        primary_hex = colors.get("primary") if colors else None
        kwargs = {}
        if primary_hex:
            kwargs["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))
        return primary_hex, kwargs

    @staticmethod
    def panel(inter, config: dict = None) -> dict:
        if config is None:
            config = TelegramConfig.get_config()

        primary_hex, ck = TelegramConfig._colors()
        validated = config.get("validated", False)

        st_emoji = emoji.on if validated else emoji.off
        st_txt = "Configurado" if validated else "Não configurado"

        token = config.get("token")
        token_display = f"`{token[:10]}...{token[-4:]}`" if token else "`Não definido`"
        bot_display = f"@{config['bot_username']}" if config.get("bot_username") else "—"

        config_btn = disnake.ui.Button(
            label="Reconfigurar" if validated else "Configurar",
            style=disnake.ButtonStyle.blurple,
            emoji=emoji.edit,
            custom_id="ConfigTelegram_Abrir",
        )
        remove_btn = disnake.ui.Button(
            label="Remover Configuração",
            style=disnake.ButtonStyle.red,
            emoji=emoji.delete,
            custom_id="ConfigTelegram_Remover",
            disabled=not validated,
        )
        back_btn = disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="Painel_Configuracoes",
        )

        desc = (
            f"### {emoji.members} Telegram\n"
            f"**Status:** {st_emoji} {st_txt}\n"
            f"**Bot:** {bot_display}\n"
            f"**Token:** {token_display}\n"
            f"-# Esse painel só valida e salva o token do bot e o chat padrão.\n"
            f"-# As demais configurações do sistema de notificações via Telegram ficam em outra seção."
        )

        mode = db.get_document("custom_mode").get("mode")

        if mode == "embed":
            emb = disnake.Embed(title="Configurar Telegram", description=desc)
            if primary_hex:
                emb.color = ck.get("accent_colour")
            return {
                "embed": emb,
                "components": [
                    disnake.ui.ActionRow(config_btn, remove_btn),
                    disnake.ui.ActionRow(back_btn),
                ],
            }
        else:
            return {
                "components": [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            f"-# Configurações > **Telegram**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(),
                        disnake.ui.ActionRow(config_btn, remove_btn),
                        **ck,
                    ),
                    disnake.ui.ActionRow(back_btn),
                ],
            }

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("ConfigTelegram_"):
            return

        mode = db.get_document("custom_mode").get("mode")

        async def wait():
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

        async def edit(payload):
            if mode == "embed":
                await inter.edit_original_message(content=None, **payload)
            else:
                await inter.edit_original_message(**payload)

        if cid == "ConfigTelegram_Abrir":
            await inter.response.send_modal(TelegramModal(self))

        elif cid == "ConfigTelegram_Remover":
            config = {
                "token": None,
                "bot_username": None, "bot_id": None,
                "validated": False,
            }
            db.save_document("telegram_config", config)
            await wait()
            await edit(self.panel(inter, config))


def setup(bot: commands.Bot):
    bot.add_cog(TelegramConfig(bot))