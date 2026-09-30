"""
cog_runtime.py — Motor de geração em tempo real
Processa triggers de prefixo, slash e canal, valida permissões,
aplica cooldowns/limites, retira estoque e entrega mensagens.
"""
from __future__ import annotations

import asyncio
import disnake
from disnake.ext import commands
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji
from commands.admin.anunciar.builder import Builder

from .helpers import (
    load_config, list_services,
    get_service, get_stock_count, pop_stock_item,
    check_cooldown, set_cooldown, check_daily_limit, increment_daily,
    log_generation, update_service,
)
from .cog_triggers import _replace_vars_in_cfg


# ──────────────────────────────────────────────────────────
#  Utilitários
# ──────────────────────────────────────────────────────────

def _find_service_by_alias(alias: str) -> Optional[dict]:
    """Encontra um serviço pelo alias/nome (case-insensitive)."""
    alias = alias.strip().lower()
    for svc in list_services().values():
        if not svc.get("ativo", True):
            continue
        for a in svc.get("alias", []):
            if a.lower() == alias:
                return svc
        # Fallback: comparar com nome
        if svc.get("nome", "").lower() == alias:
            return svc
    return None


def _check_permissions(svc: dict, member: disnake.Member, channel_id: int) -> Optional[str]:
    """Retorna mensagem de erro se sem permissão, None se OK."""
    member_role_ids = [r.id for r in member.roles]

    # Cargos bloqueados
    bloqueados = svc.get("cargos_bloqueados", [])
    for rid in bloqueados:
        if int(rid) in member_role_ids:
            return f"{emoji.wrong} Você não tem permissão para gerar este serviço."

    # Cargos permitidos (se vazio = todos)
    permitidos = svc.get("cargos_permitidos", [])
    if permitidos:
        if not any(int(rid) in member_role_ids for rid in permitidos):
            return f"{emoji.wrong} Você não tem permissão para gerar este serviço."

    # Canais bloqueados
    canais_bloq = svc.get("canais_bloqueados", [])
    if channel_id and canais_bloq and channel_id in [int(c) for c in canais_bloq]:
        return f"{emoji.wrong} Não é possível gerar neste canal."

    # Canais permitidos (se vazio = todos)
    canais_perm = svc.get("canais_permitidos", [])
    if canais_perm and channel_id and channel_id not in [int(c) for c in canais_perm]:
        return f"{emoji.wrong} Não é possível gerar neste canal."

    return None


def _resolve_cfg(cfg_global: dict, svc: dict, key: str, default):
    """Resolve configuração: serviço primeiro, depois global, depois default."""
    val = svc.get(key)
    if val is not None:
        return val
    return cfg_global.get("config", {}).get(key, default)


async def _send_delivery(
    bot: commands.Bot,
    channel: disnake.TextChannel,
    user: disnake.Member,
    svc: dict,
    item: str,
    cfg_global: dict,
    quem_gerou: Optional[disnake.Member] = None,
):
    """Monta e envia a mensagem de entrega."""
    msg_cfg = svc.get("mensagem", {})
    enviar_dm: bool = _resolve_cfg(cfg_global, svc, "enviar_dm", True)
    mostrar: bool = _resolve_cfg(cfg_global, svc, "mostrar_quem_gerou", True)

    # Se não tem mensagem configurada, usar formato padrão
    has_any = any([
        msg_cfg.get("content"),
        msg_cfg.get("embed", {}).get("description") or msg_cfg.get("embed", {}).get("title"),
        msg_cfg.get("container"),
    ])

    if not has_any:
        # Mensagem padrão
        content = (
            f"✅ **{svc['nome']}** gerado para {user.mention}!\n\n"
            f"```{item}```"
        )
        if mostrar and quem_gerou:
            content += f"\n-# Gerado por {quem_gerou.mention}"

        target = user if enviar_dm else channel
        try:
            await target.send(content, allowed_mentions=disnake.AllowedMentions.none())
        except disnake.Forbidden:
            if enviar_dm:
                await channel.send(content, allowed_mentions=disnake.AllowedMentions.none())
        return

    # Substituir variáveis
    preview_cfg = _replace_vars_in_cfg(msg_cfg, user, svc["nome"], item, quem_gerou or user)

    # Se mostrar quem gerou e não está na mensagem, adicionar como suffix
    extra_footer = None
    if mostrar and quem_gerou:
        extra_footer = f"-# Gerado por {quem_gerou.mention}"

    built = Builder.build_from_cfg({"message": preview_cfg})

    async def _send(target):
        try:
            if built["mode"] == "v2":
                comps = built["components"]
                flags = built["flags"]
                await target.send(components=comps, flags=flags, allowed_mentions=disnake.AllowedMentions.none())
                if extra_footer:
                    await target.send(extra_footer, allowed_mentions=disnake.AllowedMentions.none())
            else:
                kw = {"allowed_mentions": disnake.AllowedMentions.none()}
                if built.get("content"):
                    kw["content"] = built["content"]
                if built.get("embed"):
                    kw["embed"] = built["embed"]
                if built.get("components"):
                    kw["components"] = built["components"]
                if extra_footer:
                    kw["content"] = (kw.get("content") or "") + f"\n{extra_footer}"
                await target.send(**kw)
        except disnake.Forbidden:
            return False
        return True

    target = user if enviar_dm else channel
    success = await _send(target)
    if not success and enviar_dm:
        # Fallback para canal
        await _send(channel)


async def _send_no_stock(
    channel: disnake.TextChannel,
    user: disnake.Member,
    svc: dict,
    cfg_global: dict,
):
    """Envia mensagem de sem estoque."""
    msg_cfg = svc.get("mensagem_sem_estoque", {})
    enviar_dm: bool = _resolve_cfg(cfg_global, svc, "enviar_dm", True)

    has_any = any([
        msg_cfg.get("content"),
        msg_cfg.get("embed", {}).get("description") or msg_cfg.get("embed", {}).get("title"),
        msg_cfg.get("container"),
    ])

    if not has_any:
        # Mensagem padrão
        content = f"{emoji.wrong} {user.mention}, **{svc['nome']}** está sem estoque no momento."
        target = user if enviar_dm else channel
        try:
            await target.send(content, allowed_mentions=disnake.AllowedMentions.none())
        except disnake.Forbidden:
            if enviar_dm:
                await channel.send(content, allowed_mentions=disnake.AllowedMentions.none())
        return

    preview_cfg = _replace_vars_in_cfg(msg_cfg, user, svc["nome"], "", None)
    built = Builder.build_from_cfg({"message": preview_cfg})

    target = user if enviar_dm else channel
    try:
        if built["mode"] == "v2":
            await target.send(components=built["components"], flags=built["flags"],
                              allowed_mentions=disnake.AllowedMentions.none())
        else:
            kw = {"allowed_mentions": disnake.AllowedMentions.none()}
            if built.get("content"):
                kw["content"] = built["content"]
            if built.get("embed"):
                kw["embed"] = built["embed"]
            if built.get("components"):
                kw["components"] = built["components"]
            await target.send(**kw)
    except disnake.Forbidden:
        if enviar_dm:
            await channel.send(
                f"{emoji.wrong} {user.mention}, **{svc['nome']}** está sem estoque.",
                allowed_mentions=disnake.AllowedMentions.none()
            )


async def _send_log(bot: commands.Bot, cfg_global: dict, user: disnake.Member,
                    svc: dict, item: str, guild: disnake.Guild):
    """Envia log para o canal configurado."""
    canal_log_id = cfg_global.get("config", {}).get("canal_log_id")
    if not canal_log_id:
        return
    channel = bot.get_channel(int(canal_log_id))
    if not channel:
        return

    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    mode = db.get_document("custom_mode").get("mode")
    stock_remaining = get_stock_count(svc["id"])

    try:
        if mode == "embed":
            e = disnake.Embed(
                description=(
                    f"**Serviço:** `{svc['nome']}`\n"
                    f"**Usuário:** {user.mention} (`{user.id}`)\n"
                    f"**Item:** ||`{item[:50]}...`|| (censurado)\n"
                    f"**Estoque restante:** `{stock_remaining}`"
                ),
            )
            if hex_:
                e.color = int(hex_.replace("#", ""), 16)
            await channel.send(embed=e)
        else:
            kw = {}
            if hex_:
                kw["accent_colour"] = disnake.Colour(int(hex_.replace("#", ""), 16))
            await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"## {emoji.correct} Geração — {svc['nome']}\n"
                            f"**Usuário:** {user.mention} · **Estoque restante:** `{stock_remaining}`"
                        ),
                        **kw,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────
#  Motor central de geração
# ──────────────────────────────────────────────────────────

async def process_generation(
    bot: commands.Bot,
    service_alias: str,
    member: disnake.Member,
    channel: disnake.TextChannel,
    guild: disnake.Guild,
    trigger_message: Optional[disnake.Message] = None,
) -> Optional[str]:
    """
    Executa o fluxo completo de geração.
    Retorna mensagem de erro (str) ou None se OK.
    """
    cfg = load_config()
    if not cfg.get("enabled"):
        return None  # silêncio quando desativado

    # Encontrar serviço
    svc = _find_service_by_alias(service_alias)
    if not svc:
        return None  # alias não encontrado — ignorar silenciosamente

    service_id = svc["id"]

    # Permissões
    perm_error = _check_permissions(svc, member, channel.id)
    if perm_error:
        try:
            await channel.send(perm_error, delete_after=8, allowed_mentions=disnake.AllowedMentions.none())
        except Exception:
            pass
        return perm_error

    # Cooldown
    cooldown_s: int = _resolve_cfg(cfg, svc, "cooldown_segundos", 0)
    remaining = check_cooldown(member.id, service_id, cooldown_s)
    if remaining > 0:
        try:
            await channel.send(
                f"{emoji.clock} {member.mention}, aguarde **{remaining:.0f}s** para gerar novamente.",
                delete_after=8, allowed_mentions=disnake.AllowedMentions.none(),
            )
        except Exception:
            pass
        return "cooldown"

    # Limite diário
    max_dia: int = _resolve_cfg(cfg, svc, "max_por_dia", 0)
    if not check_daily_limit(member.id, service_id, max_dia):
        try:
            await channel.send(
                f"{emoji.wrong} {member.mention}, você atingiu o limite diário para **{svc['nome']}**.",
                delete_after=8, allowed_mentions=disnake.AllowedMentions.none(),
            )
        except Exception:
            pass
        return "daily_limit"

    # Apagar trigger
    apagar: bool = _resolve_cfg(cfg, svc, "apagar_mensagem_trigger", True)
    if apagar and trigger_message:
        try:
            await trigger_message.delete()
        except Exception:
            pass

    # Obter item do estoque
    fake = svc.get("stock_fake", {})
    fake_enabled = fake.get("enabled", False)

    if fake_enabled:
        # Stock fake — usar mensagem fake
        fake_msg = fake.get("mensagem_fake") or f"✅ {member.mention} aqui está o {svc['nome']}!\n\n`CONTA_FAKE`"
        fake_msg = fake_msg.replace("{user}", member.mention).replace("{servico}", svc["nome"]).replace("{item}", "CONTA_FAKE").replace("{quem_gerou}", member.mention)
        enviar_dm: bool = _resolve_cfg(cfg, svc, "enviar_dm", True)
        target = member if enviar_dm else channel
        try:
            await target.send(fake_msg, allowed_mentions=disnake.AllowedMentions.none())
        except disnake.Forbidden:
            if enviar_dm:
                await channel.send(fake_msg, allowed_mentions=disnake.AllowedMentions.none())
        item = "FAKE"
    else:
        item = pop_stock_item(service_id)
        if item is None:
            # Sem estoque
            await _send_no_stock(channel, member, svc, cfg)
            return "no_stock"

        # Entregar item
        await _send_delivery(bot, channel, member, svc, item, cfg)

    # Pós-geração
    set_cooldown(member.id, service_id)
    increment_daily(member.id, service_id)
    update_service(service_id, {"total_gerado": svc.get("total_gerado", 0) + 1})
    log_generation(member.id, service_id, svc["nome"], item, guild.id)
    await _send_log(bot, cfg, member, svc, item, guild)

    return None  # sucesso


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class GeradorRuntimeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Modo prefixo: on_message ───────────────────────────────────────────

    @commands.Cog.listener("on_message")
    async def on_message(self, msg: disnake.Message):
        if msg.author.bot:
            return
        if not msg.guild:
            return

        cfg = load_config()
        if not cfg.get("enabled"):
            return

        trigger = cfg.get("trigger", {})
        t_type = trigger.get("type", "prefix")

        # ── Modo prefixo ──
        if t_type == "prefix":
            prefix = trigger.get("prefix", "+")
            content = msg.content.strip()

            # Aceitar: "+gen Netflix" ou "+Netflix" ou "+gen"
            if not content.startswith(prefix):
                return

            after_prefix = content[len(prefix):].strip()

            # Extrair alias: remover "gen " do início se existir
            gen_keyword = "gen"
            if after_prefix.lower().startswith(gen_keyword + " "):
                alias = after_prefix[len(gen_keyword):].strip()
            elif after_prefix.lower().startswith(gen_keyword):
                alias = after_prefix[len(gen_keyword):].strip()
            else:
                alias = after_prefix

            if not alias:
                return

            if not isinstance(msg.channel, disnake.TextChannel):
                return

            await process_generation(
                bot=self.bot,
                service_alias=alias,
                member=msg.author,
                channel=msg.channel,
                guild=msg.guild,
                trigger_message=msg,
            )

        # ── Modo canal ──
        elif t_type == "channel":
            canal_id = trigger.get("canal_id")
            if not canal_id:
                return
            if msg.channel.id != int(canal_id):
                return

            alias = msg.content.strip()
            if not alias:
                return

            if not isinstance(msg.channel, disnake.TextChannel):
                return

            await process_generation(
                bot=self.bot,
                service_alias=alias,
                member=msg.author,
                channel=msg.channel,
                guild=msg.guild,
                trigger_message=msg,
            )

    # ── Modo slash: comando dinâmico ──────────────────────────────────────

    @commands.slash_command(name="gen", description="Gerar um serviço")
    async def gen_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        servico: str = commands.Param(description="Nome do serviço a gerar"),
    ):
        cfg = load_config()
        if not cfg.get("enabled"):
            await inter.response.send_message(f"{emoji.wrong} O sistema de geração está desativado.", ephemeral=True)
            return

        trigger = cfg.get("trigger", {})
        if trigger.get("type") != "slash":
            await inter.response.send_message(f"{emoji.wrong} O modo slash não está ativado.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=False)

        if not isinstance(inter.channel, disnake.TextChannel):
            await inter.followup.send(f"{emoji.wrong} Comando disponível apenas em canais de texto.", ephemeral=True)
            return

        error = await process_generation(
            bot=self.bot,
            service_alias=servico,
            member=inter.author,
            channel=inter.channel,
            guild=inter.guild,
            trigger_message=None,
        )

        if error == "no_stock":
            # Já enviou mensagem de sem estoque
            try:
                await inter.delete_original_message()
            except Exception:
                pass
        elif error and error not in ("cooldown", "daily_limit"):
            # Serviço não encontrado
            servicos = list_services()
            ativos = [s for s in servicos.values() if s.get("ativo", True)]
            if ativos:
                nomes = ", ".join(f"`{s['nome']}`" for s in ativos[:10])
                await inter.followup.send(
                    f"{emoji.wrong} Serviço **{servico}** não encontrado.\nServiços disponíveis: {nomes}",
                    ephemeral=True,
                )
            else:
                await inter.followup.send(f"{emoji.wrong} Nenhum serviço disponível.", ephemeral=True)
        elif error is None:
            # Sucesso — apagar a resposta do slash (entrega foi na DM ou canal)
            try:
                await inter.delete_original_message()
            except Exception:
                pass

    # ── Autocomplete do slash ──────────────────────────────────────────────

    @gen_slash.autocomplete("servico")
    async def gen_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str):
        servicos = list_services()
        return [
            s["nome"]
            for s in servicos.values()
            if s.get("ativo", True) and string.lower() in s["nome"].lower()
        ][:25]
