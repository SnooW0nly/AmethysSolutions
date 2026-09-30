"""
modules/settings/notificacoes/cog.py

Painel de Notificações — Settings.
Fluxo:
  Painel_Configuracoes  →  ConfigNotif_Menu  (painel intermediário)
    ├─ ConfigNotif_Email          → modal de email
    ├─ ConfigNotif_TestEmail      → envia email de teste (cooldown)
    ├─ ConfigNotif_Toggle         → liga/desliga WhatsApp
    └─ ConfigNotif_ConfigNumber   → modal de telefone
"""

import re
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.email_utils import (
    is_valid_email,
    configure_dest_email,
    get_dest_email,
    send_test_email,
    is_email_enabled,
    TEST_COOLDOWN_SECONDS,
    _test_cooldowns,
)
import time

# Todos os DDDs do Brasil (para validação)
ALL_DDDS = [
    "11","12","13","14","15","16","17","18","19",
    "21","22","24","27","28",
    "31","32","33","34","35","37","38",
    "41","42","43","44","45","46","47","48","49",
    "51","53","54","55",
    "61","62","63","64","65","66","67","68","69",
    "71","73","74","75","77","79",
    "81","82","83","84","85","86","87","88","89",
    "91","92","93","94","95","96","97","98","99",
]


# ─────────────────────────────────────────────────────────────────────────────
# Modals
# ─────────────────────────────────────────────────────────────────────────────

class ConfigPhoneModal(disnake.ui.Modal):
    def __init__(self, cog):
        self.cog = cog
        config = ConfigureNotifications.get_config()
        super().__init__(
            title="Configurar Número WhatsApp",
            components=[
                disnake.ui.TextInput(
                    label="DDD",
                    placeholder="Ex: 11",
                    custom_id="input_ddd",
                    value=config.get("ddd", ""),
                    min_length=2, max_length=2,
                    style=disnake.TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Número de Celular",
                    placeholder="99999-9999",
                    custom_id="input_number",
                    value=config.get("number", ""),
                    min_length=8, max_length=15,
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

        ddd    = inter.text_values["input_ddd"].strip()
        number = inter.text_values["input_number"].strip()

        if ddd not in ALL_DDDS:
            await inter.followup.send(
                f"{emoji.error} DDD inválido. Ex: 11, 21, 31...", ephemeral=True
            )
            return

        clean = re.sub(r"\D", "", number)
        if len(clean) < 8:
            await inter.followup.send(
                f"{emoji.error} Número inválido. Verifique se digitou corretamente.", ephemeral=True
            )
            return

        config = ConfigureNotifications.get_config()
        config.update({"ddd": ddd, "number": clean, "enabled": True})
        db.save_document("notifications_config", config)

        panel = ConfigureNotifications.panel(inter, config)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel)

        await inter.followup.send(
            f"{emoji.correct} Número configurado: ({ddd}) {clean}", ephemeral=True
        )


class ConfigEmailModal(disnake.ui.Modal):
    """Modal simples — só pede o email de destino. SMTP fica no notification.json."""

    def __init__(self, cog):
        self.cog = cog
        current = get_dest_email() or ""
        super().__init__(
            title="Configurar Email de Notificações",
            components=[
                disnake.ui.TextInput(
                    label="Seu Email (receberá notificações de venda)",
                    placeholder="seuemail@exemplo.com",
                    custom_id="email_dest",
                    value=current,
                    min_length=6,
                    max_length=120,
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

        email = inter.text_values["email_dest"].strip()

        ok, msg_txt = configure_dest_email(email)
        if not ok:
            await inter.followup.send(f"{emoji.error} {msg_txt}", ephemeral=True)
            return

        panel = ConfigureNotifications.build_email_panel(inter)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel)

        await inter.followup.send(
            f"{emoji.correct} Email **{email}** salvo! Use **Testar Email** para confirmar.",
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cog
# ─────────────────────────────────────────────────────────────────────────────

class ConfigureNotifications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Helpers de config ────────────────────────────────────────────────────

    @staticmethod
    def get_config() -> dict:
        config = db.get_document("notifications_config")
        if not config:
            config = {"enabled": False, "ddd": None, "number": None}
            db.save_document("notifications_config", config)
        return config

    @staticmethod
    def _colors():
        colors = db.get_document("custom_colors")
        primary_hex = colors.get("primary") if colors else None
        kwargs = {}
        if primary_hex:
            kwargs["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))
        return primary_hex, kwargs

    # ── Painel principal (WhatsApp) ──────────────────────────────────────────

    @staticmethod
    def panel(inter, config: dict = None) -> dict:
        if config is None:
            config = ConfigureNotifications.get_config()

        primary_hex, ck = ConfigureNotifications._colors()
        enabled = config.get("enabled", False)

        phone_info = "Nenhum número configurado"
        if config.get("ddd") and config.get("number"):
            phone_info = f"({config['ddd']}) {config['number']}"

        st_txt   = "Ativado"  if enabled else "Desativado"
        st_emoji = emoji.on   if enabled else emoji.off

        toggle_btn = disnake.ui.Button(
            label=f"WhatsApp: {'Desativar' if enabled else 'Ativar'}",
            style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
            emoji=emoji.whatsapp,
            custom_id="ConfigNotif_Toggle",
        )
        config_num_btn = disnake.ui.Button(
            label="Configurar Número",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.edit,
            custom_id="ConfigNotif_ConfigNumber",
            disabled=not enabled,
        )
        email_btn = disnake.ui.Button(
            label="Notificações por Email",
            style=disnake.ButtonStyle.blurple,
            emoji=emoji.mail2,
            custom_id="ConfigNotif_EmailPanel",
        )
        back_btn = disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="Painel_Configuracoes",
        )

        mode = db.get_document("custom_mode").get("mode")

        if mode == "embed":
            emb = disnake.Embed(
                title="Configuração de Notificações",
                description=(
                    f"### {emoji.whatsapp} WhatsApp\n"
                    f"**Status:** {st_emoji} {st_txt}\n"
                    f"**Número:** `{phone_info}`\n\n"
                    f"### {emoji.mail2} Email\n"
                    f"Clique em **Notificações por Email** para configurar."
                ),
            )
            if primary_hex:
                emb.color = ck.get("accent_colour")
            return {
                "embed": emb,
                "components": [
                    disnake.ui.ActionRow(toggle_btn, config_num_btn),
                    disnake.ui.ActionRow(email_btn),
                    disnake.ui.ActionRow(back_btn),
                ],
            }
        else:
            return {
                "components": [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            f"-# Configurações > **Notificações**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"### {emoji.whatsapp} WhatsApp\n"
                            f"**Status:** {st_emoji} {st_txt}\n"
                            f"**Número:** `{phone_info}`"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.ActionRow(toggle_btn, config_num_btn),
                        disnake.ui.ActionRow(email_btn),
                        **ck,
                    ),
                    disnake.ui.ActionRow(back_btn),
                ],
            }

    # ── Painel intermediário — Email ─────────────────────────────────────────

    @staticmethod
    def build_email_panel(inter) -> dict:
        primary_hex, ck = ConfigureNotifications._colors()
        mode = db.get_document("custom_mode").get("mode")

        dest    = get_dest_email() or "Nenhum email configurado"
        enabled = is_email_enabled()
        st_emoji = emoji.on  if enabled else emoji.off
        st_txt   = "Ativado" if enabled else "Desativado"

        # Cooldown restante do botão de teste
        guild_id = inter.guild_id if inter else 0
        now      = time.time()
        last_test = _test_cooldowns.get(guild_id, 0)
        remaining  = max(0, int(TEST_COOLDOWN_SECONDS - (now - last_test)))
        test_label = f"Testar Email ({remaining}s)" if remaining > 0 else "Testar Email"
        test_disabled = remaining > 0

        config_email_btn = disnake.ui.Button(
            label="Configurar Email",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.edit,
            custom_id="ConfigNotif_ConfigEmail",
        )
        test_btn = disnake.ui.Button(
            label=test_label,
            style=disnake.ButtonStyle.green,
            emoji="📨",
            custom_id="ConfigNotif_TestEmail",
            disabled=test_disabled,
        )
        back_btn = disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="ConfigNotif_BackToWhatsApp",
        )

        desc = (
            f"### {emoji.mail2} Notificações por Email\n"
            f"**Status:** {st_emoji} {st_txt}\n"
            f"**Email de destino:** `{dest}`\n\n"
            f"-# As credenciais SMTP ficam em `configs/notification.json`.\n"
            f"-# Você só precisa definir o email que receberá as notificações."
        )

        if mode == "embed":
            emb = disnake.Embed(
                title="Email — Notificações de Venda",
                description=desc,
            )
            if primary_hex:
                emb.color = ck.get("accent_colour")
            return {
                "embed": emb,
                "components": [
                    disnake.ui.ActionRow(config_email_btn, test_btn),
                    disnake.ui.ActionRow(back_btn),
                ],
            }
        else:
            return {
                "components": [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            f"-# Configurações > Notificações > **Email**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(),
                        disnake.ui.ActionRow(config_email_btn, test_btn),
                        **ck,
                    ),
                    disnake.ui.ActionRow(back_btn),
                ],
            }

    # ── Listener de botões ───────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("ConfigNotif_"):
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

        # ── Toggle WhatsApp ──────────────────────────────────────────────────
        if cid == "ConfigNotif_Toggle":
            config = self.get_config()
            config["enabled"] = not config.get("enabled", False)
            db.save_document("notifications_config", config)
            await wait()
            await edit(self.panel(inter, config))

        # ── Abrir modal de número ────────────────────────────────────────────
        elif cid == "ConfigNotif_ConfigNumber":
            await inter.response.send_modal(ConfigPhoneModal(self))

        # ── Abrir painel de email ────────────────────────────────────────────
        elif cid == "ConfigNotif_EmailPanel":
            await wait()
            await edit(self.build_email_panel(inter))

        # ── Abrir modal de email ─────────────────────────────────────────────
        elif cid == "ConfigNotif_ConfigEmail":
            await inter.response.send_modal(ConfigEmailModal(self))

        # ── Testar email (com cooldown) ──────────────────────────────────────
        elif cid == "ConfigNotif_TestEmail":
            await wait()

            ok, msg_txt = await send_test_email(inter.guild_id)

            if ok:
                dest = get_dest_email()
                await inter.followup.send(
                    f"{emoji.correct} Email de teste enviado para **{dest}**!\nVerifique sua caixa de entrada.",
                    ephemeral=True,
                )
            else:
                await inter.followup.send(
                    f"{emoji.error} {msg_txt}", ephemeral=True
                )

            # Atualiza painel para refletir o novo cooldown
            await edit(self.build_email_panel(inter))

        # ── Voltar ao painel de WhatsApp ─────────────────────────────────────
        elif cid == "ConfigNotif_BackToWhatsApp":
            config = self.get_config()
            await wait()
            await edit(self.panel(inter, config))


def setup(bot: commands.Bot):
    bot.add_cog(ConfigureNotifications(bot))
