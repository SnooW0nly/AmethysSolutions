"""
cog_painel.py — Painel principal do Gerador
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from .helpers import load_config, save_config, list_services, list_groups


# ──────────────────────────────────────────────────────────
#  Builder de painéis
# ──────────────────────────────────────────────────────────

def _accent(cfg: dict) -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _embed_color() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"color": int(hex_.replace("#", ""), 16)}
    return {}


def build_main_panel(mode: str) -> dict:
    cfg = load_config()
    enabled = cfg.get("enabled", False)
    servicos = list_services()
    grupos = list_groups()
    trigger = cfg.get("trigger", {})
    config = cfg.get("config", {})

    trigger_type = trigger.get("type", "prefix")
    trigger_map = {"prefix": f"Prefixo `{trigger.get('prefix', '+')}`",
                   "slash": f"Slash `/{trigger.get('slash_name', 'gen')}`",
                   "channel": f"Canal <#{trigger.get('canal_id', '?')}>" if trigger.get("canal_id") else "Canal (não configurado)"}
    trigger_label = trigger_map.get(trigger_type, "Não configurado")

    status_icon = emoji.on if enabled else emoji.off
    status_text = "Ativo" if enabled else "Inativo"

    body = (
        f"{status_icon} **Status:** `{status_text}`\n"
        f"{emoji.commands} **Trigger:** {trigger_label}\n"
        f"{emoji.cardbox} **Serviços:** `{len(servicos)}`\n"
        f"{emoji.members} **Grupos:** `{len(grupos)}`\n"
        f"{emoji.information} **Destino:** `{'DM' if config.get('enviar_dm', True) else 'Canal'}`\n"
        f"-# Canal de log: {'<#' + str(config['canal_log_id']) + '>' if config.get('canal_log_id') else '`Não configurado`'}"
    )

    btn_toggle = disnake.ui.Button(
        label="Desativar" if enabled else "Ativar",
        style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
        emoji=emoji.off if enabled else emoji.on,
        custom_id="Gerador_ToggleAtivo",
    )

    row1 = disnake.ui.ActionRow(
        btn_toggle,
        disnake.ui.Button(label="Serviços", emoji=emoji.cardbox, style=disnake.ButtonStyle.blurple, custom_id="Gerador_PainelServicos"),
        disnake.ui.Button(label="Grupos", emoji=emoji.members, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelGrupos"),
    )
    row2 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Trigger", emoji=emoji.route, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelTrigger"),
        disnake.ui.Button(label="Configurações", emoji=emoji.settings2, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelConfig"),
        disnake.ui.Button(label="Logs", emoji=emoji.double_speech, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelLogs"),
    )

    if mode == "embed":
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Gerador",
            description=f"-# Painel > Loja > Extensões > **Gerador**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": [row1, row2, disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                              custom_id="LojaExtensoes_Panel")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Extensões > **Gerador**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                row1,
                row2,
                **_accent({}),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id="LojaExtensoes_Panel")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_config_panel(mode: str) -> dict:
    cfg = load_config()
    config = cfg.get("config", {})

    enviar_dm = config.get("enviar_dm", True)
    apagar = config.get("apagar_mensagem_trigger", True)
    mostrar = config.get("mostrar_quem_gerou", True)
    cooldown = config.get("cooldown_segundos", 0)
    max_dia = config.get("max_por_dia", 0)
    log_id = config.get("canal_log_id")
    gen_id = config.get("canal_gen_id")

    body = (
        f"{emoji.information} **Destino:** `{'DM do usuário' if enviar_dm else 'No canal'}`\n"
        f"{emoji.delete} **Apagar trigger:** `{'Sim' if apagar else 'Não'}`\n"
        f"{emoji.member} **Mostrar quem gerou:** `{'Sim' if mostrar else 'Não'}`\n"
        f"{emoji.clock} **Cooldown global:** `{cooldown}s` (0 = sem cooldown)\n"
        f"{emoji.warn} **Máx/dia por usuário:** `{max_dia}` (0 = ilimitado)\n"
        f"{emoji.textc} **Canal de log:** {'<#' + str(log_id) + '>' if log_id else '`Não configurado`'}\n"
        f"{emoji.textc} **Canal de geração:** {'<#' + str(gen_id) + '>' if gen_id else '`Herda do trigger`'}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Destino: DM" if not enviar_dm else "Destino: Canal",
                              emoji=emoji.member, style=disnake.ButtonStyle.grey,
                              custom_id="Gerador_Config_ToggleDM"),
            disnake.ui.Button(label="Apagar trigger: Sim" if not apagar else "Apagar trigger: Não",
                              emoji=emoji.delete, style=disnake.ButtonStyle.grey,
                              custom_id="Gerador_Config_ToggleApagar"),
            disnake.ui.Button(label="Quem gerou: Sim" if not mostrar else "Quem gerou: Não",
                              emoji=emoji.member, style=disnake.ButtonStyle.grey,
                              custom_id="Gerador_Config_ToggleMostrar"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Cooldown", emoji=emoji.clock, style=disnake.ButtonStyle.blurple,
                              custom_id="Gerador_Config_Cooldown"),
            disnake.ui.Button(label="Limite Diário", emoji=emoji.warn, style=disnake.ButtonStyle.blurple,
                              custom_id="Gerador_Config_MaxDia"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Canal de log (opcional)",
                custom_id="Gerador_Config_CanalLog",
                channel_types=[disnake.ChannelType.text],
                min_values=0, max_values=1,
            )
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title="Configurações do Gerador",
            description=f"-# Painel > Gerador > **Configurações**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerador > **Configurações**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent({}),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_trigger_panel(mode: str) -> dict:
    cfg = load_config()
    trigger = cfg.get("trigger", {})
    t_type = trigger.get("type", "prefix")
    prefix = trigger.get("prefix", "+")
    slash_name = trigger.get("slash_name", "gen")
    canal_id = trigger.get("canal_id")

    options = [
        disnake.SelectOption(label="Prefixo", value="prefix", description=f"Ex: {prefix}gen Netflix",
                             emoji=emoji.commands, default=(t_type == "prefix")),
        disnake.SelectOption(label="Slash Command", value="slash", description=f"Ex: /{slash_name} Netflix",
                             emoji=emoji.route, default=(t_type == "slash")),
        disnake.SelectOption(label="Mensagem no Canal", value="channel", description="Usuário digita nome do serviço no canal",
                             emoji=emoji.textc, default=(t_type == "channel")),
    ]

    body = (
        f"**Tipo atual:** `{t_type}`\n"
        f"**Prefixo:** `{prefix}`\n"
        f"**Nome Slash:** `/{slash_name}`\n"
        f"**Canal:** {'<#' + str(canal_id) + '>' if canal_id else '`Não configurado`'}\n\n"
        f"-# No modo **prefixo**, o usuário digita: `{prefix}gen <serviço>`\n"
        f"-# No modo **slash**, o usuário usa: `/{slash_name} <serviço>`\n"
        f"-# No modo **canal**, qualquer mensagem no canal é interpretada como nome de serviço."
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Selecionar tipo de trigger",
                custom_id="Gerador_Trigger_SelectType",
                options=options,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Editar Prefixo / Nome Slash", emoji=emoji.edit, style=disnake.ButtonStyle.blurple,
                              custom_id="Gerador_Trigger_EditarModal"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Canal de trigger (modo canal)",
                custom_id="Gerador_Trigger_SelectCanal",
                channel_types=[disnake.ChannelType.text],
                min_values=0, max_values=1,
            )
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title="Trigger do Gerador",
            description=f"-# Painel > Gerador > **Trigger**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerador > **Trigger**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent({}),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_logs_panel(mode: str) -> dict:
    from .helpers import DB_LOGS_KEY
    logs_data = db.get_document(DB_LOGS_KEY) or {"logs": []}
    logs = logs_data.get("logs", [])[-15:]  # Últimos 15
    logs.reverse()

    if not logs:
        body = "-# Nenhuma geração registrada ainda."
    else:
        lines = []
        for lg in logs:
            import datetime
            ts = lg.get("timestamp", 0)
            dt = datetime.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
            lines.append(f"`{dt}` **{lg.get('service_name', '?')}** — <@{lg.get('user_id', 0)}>")
        body = "\n".join(lines)

    if mode == "embed":
        embed = disnake.Embed(
            title="Logs do Gerador",
            description=f"-# Painel > Gerador > **Logs**\n\nÚltimas 15 gerações:\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerador > **Logs**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Últimas 15 gerações:**\n{body}"),
                **_accent({}),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Modais de configuração
# ──────────────────────────────────────────────────────────

class CooldownModal(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        val = cfg.get("config", {}).get("cooldown_segundos", 0)
        super().__init__(
            title="Cooldown Global",
            custom_id="Gerador_Config_CooldownModal",
            components=[
                disnake.ui.TextInput(
                    label="Segundos de cooldown (0 = sem cooldown)",
                    custom_id="cooldown",
                    value=str(val),
                    max_length=6,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            val = max(0, int(inter.text_values["cooldown"].strip()))
        except Exception:
            val = 0
        cfg = load_config()
        cfg["config"]["cooldown_segundos"] = val
        save_config(cfg)
        mode = db.get_document("custom_mode").get("mode")
        panel = build_config_panel(mode)
        if mode == "embed":
            await inter.response.edit_message(**panel)
        else:
            await inter.response.edit_message(**panel)


class MaxDiaModal(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        val = cfg.get("config", {}).get("max_por_dia", 0)
        super().__init__(
            title="Limite Diário",
            custom_id="Gerador_Config_MaxDiaModal",
            components=[
                disnake.ui.TextInput(
                    label="Máx. por dia por usuário (0 = ilimitado)",
                    custom_id="max_dia",
                    value=str(val),
                    max_length=5,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            val = max(0, int(inter.text_values["max_dia"].strip()))
        except Exception:
            val = 0
        cfg = load_config()
        cfg["config"]["max_por_dia"] = val
        save_config(cfg)
        mode = db.get_document("custom_mode").get("mode")
        panel = build_config_panel(mode)
        await inter.response.edit_message(**panel)


class TriggerEditModal(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        trigger = cfg.get("trigger", {})
        super().__init__(
            title="Editar Trigger",
            custom_id="Gerador_Trigger_EditModal",
            components=[
                disnake.ui.TextInput(
                    label="Prefixo (ex: +)",
                    custom_id="prefix",
                    value=trigger.get("prefix", "+"),
                    max_length=5,
                    required=False,
                ),
                disnake.ui.TextInput(
                    label="Nome do slash command (ex: gen)",
                    custom_id="slash_name",
                    value=trigger.get("slash_name", "gen"),
                    max_length=32,
                    required=False,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = load_config()
        prefix = inter.text_values.get("prefix", "").strip() or "+"
        slash_name = inter.text_values.get("slash_name", "").strip() or "gen"
        cfg["trigger"]["prefix"] = prefix
        cfg["trigger"]["slash_name"] = slash_name
        save_config(cfg)
        mode = db.get_document("custom_mode").get("mode")
        panel = build_trigger_panel(mode)
        await inter.response.edit_message(**panel)


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class GeradorPainelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _mode(self):
        return db.get_document("custom_mode").get("mode")

    async def _reply(self, inter, panel: dict):
        mode = self._mode()
        if inter.response.is_done():
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                await inter.edit_original_message(**panel, flags=flags)
        else:
            if mode == "embed":
                await (embed_message if mode == "embed" else message).wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel)
            else:
                await (embed_message if mode == "embed" else message).wait(inter, send=False)
                flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                await inter.edit_original_message(**panel, flags=flags)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid == "Gerador_PainelPrincipal":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_main_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_ToggleAtivo":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            cfg["enabled"] = not cfg.get("enabled", False)
            save_config(cfg)
            panel = build_main_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_PainelConfig":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_config_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_PainelTrigger":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_trigger_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_PainelLogs":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_logs_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        # Config toggles
        elif cid == "Gerador_Config_ToggleDM":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            cfg["config"]["enviar_dm"] = not cfg["config"].get("enviar_dm", True)
            save_config(cfg)
            panel = build_config_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_Config_ToggleApagar":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            cfg["config"]["apagar_mensagem_trigger"] = not cfg["config"].get("apagar_mensagem_trigger", True)
            save_config(cfg)
            panel = build_config_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_Config_ToggleMostrar":
            mode = self._mode()
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            cfg["config"]["mostrar_quem_gerou"] = not cfg["config"].get("mostrar_quem_gerou", True)
            save_config(cfg)
            panel = build_config_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_Config_Cooldown":
            await inter.response.send_modal(CooldownModal())

        elif cid == "Gerador_Config_MaxDia":
            await inter.response.send_modal(MaxDiaModal())

        elif cid == "Gerador_Trigger_EditarModal":
            await inter.response.send_modal(TriggerEditModal())

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""
        mode = self._mode()

        if cid == "Gerador_Trigger_SelectType":
            t_type = inter.values[0]
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            cfg["trigger"]["type"] = t_type
            save_config(cfg)
            panel = build_trigger_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_Trigger_SelectCanal":
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            if inter.values:
                cfg["trigger"]["canal_id"] = int(inter.values[0])
            else:
                cfg["trigger"]["canal_id"] = None
            save_config(cfg)
            panel = build_trigger_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Gerador_Config_CanalLog":
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            if inter.values:
                cfg["config"]["canal_log_id"] = int(inter.values[0])
            else:
                cfg["config"]["canal_log_id"] = None
            save_config(cfg)
            panel = build_config_panel(mode)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)
