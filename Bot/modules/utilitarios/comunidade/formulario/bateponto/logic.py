"""
modules/utilitarios/comunidade/formulario/bateponto/logic.py

Lógica de processamento de ponto e logs.
"""
from __future__ import annotations

import datetime
import disnake
from functions.emoji import emoji
from .helpers import (
    get_bateponto, salvar_bateponto, get_colors, 
    format_duration, estilo_para_disnake
)

def build_bp_anunciar_panel(bp_id: str) -> list:
    """
    Painel de aparência completo do Bate Ponto (similar ao formulário).
    """
    from commands.admin.anunciar.anunciar import Anunciar
    from functions.database import database as _db

    cfg = _db.get_document("messages_anunciar") or {}
    msg = cfg.get("message", {}) or {}

    has_container = Anunciar._safe_get(msg, "container") is not None
    has_message   = bool(Anunciar._safe_get(msg, "content"))
    has_embed     = any([
        Anunciar._safe_get(msg, "embed.title"),
        Anunciar._safe_get(msg, "embed.description"),
        Anunciar._safe_get(msg, "embed.color"),
        Anunciar._safe_get(msg, "embed.footer"),
    ])
    has_image = any([
        Anunciar._safe_get(msg, "externalImage"),
        Anunciar._safe_get(msg, "embed.banner"),
        Anunciar._safe_get(msg, "embed.thumbnail"),
    ])
    others_exist = has_embed

    # Dados do Bate Ponto
    bp = get_bateponto(bp_id) or {}
    btn_in_label  = bp.get("botao_entrada_label") or "Bater Ponto (Entrada)"
    btn_in_emoji  = bp.get("botao_entrada_emoji") or f"{emoji.on}"
    btn_in_estilo = bp.get("botao_entrada_estilo", "green")
    
    btn_out_label  = bp.get("botao_saida_label") or "Bater Ponto (Saída)"
    btn_out_emoji  = bp.get("botao_saida_emoji") or f"{emoji.off}"
    btn_out_estilo = bp.get("botao_saida_estilo", "red")
    
    msg_suc = (bp.get("mensagem_sucesso") or "")[:60]

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

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Bate Ponto > **Aparência**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**{emoji.embed} Mensagem publicada**\n"
                f"-# Conteúdo exibido no canal onde o ponto é publicado."
            ),
            _row("Mensagem",  "Anunciar_DefinirMensagem",  "Anunciar_ApagarMensagem",  emoji.message,  has_message),
            _row("Container", "Anunciar_DefinirContainer", "Anunciar_ApagarContainer", emoji.commands, has_container, define_disabled=others_exist),
            _row("Embed",     "Anunciar_DefinirEmbed",     "Anunciar_ApagarEmbed",     emoji.embed,    has_embed,     define_disabled=has_container),
            _row("Imagens",   "Anunciar_DefinirImagem",    "Anunciar_ApagarImagem",    emoji.image,    has_image),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**{emoji.wand} Botões do ponto**\n"
                f"-# Entrada: `{btn_in_label}` | Saída: `{btn_out_label}`"
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Entrada", emoji=emoji.on, style=disnake.ButtonStyle.secondary,
                                  custom_id=f"BP_EditarBotao:entrada:{bp_id}"),
                disnake.ui.Button(label="Editar Saída", emoji=emoji.off, style=disnake.ButtonStyle.secondary,
                                  custom_id=f"BP_EditarBotao:saida:{bp_id}"),
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**{emoji.correct} Mensagem de sucesso**\n"
                f"-# `{msg_suc or 'Não definida'}`"
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Mensagem de Sucesso", emoji=emoji.correct,
                                  style=disnake.ButtonStyle.secondary, custom_id=f"BP_EditarMsgSucesso:{bp_id}"),
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Salvar e Voltar", style=disnake.ButtonStyle.green,
                              emoji=emoji.correct, custom_id=f"BP_SalvarEditorAnunciar:{bp_id}"),
            disnake.ui.Button(label="Descartar", style=disnake.ButtonStyle.red,
                              emoji=emoji.delete, custom_id=f"BP_DescartarEditorAnunciar:{bp_id}"),
        ),
    ]

def build_bateponto_embed(bp: dict) -> disnake.Embed:
    """Constrói o embed público do bate-ponto baseado no editor de anúncios."""
    editor = bp.get("anunciar_editor", {})
    embed_cfg = editor.get("embed", {})
    
    title = embed_cfg.get("title") or bp.get("embed_titulo") or bp.get("nome")
    desc = embed_cfg.get("description") or bp.get("embed_descricao") or "Clique abaixo para bater o ponto."
    color_hex = embed_cfg.get("color") or bp.get("embed_cor")
    
    embed = disnake.Embed(title=title, description=desc)
    if color_hex:
        try: embed.color = int(color_hex.replace("#", ""), 16)
        except: pass
    
    if embed_cfg.get("footer"): embed.set_footer(text=embed_cfg["footer"])
    if embed_cfg.get("thumbnail"): embed.set_thumbnail(url=embed_cfg["thumbnail"])
    if embed_cfg.get("banner"): embed.set_image(url=embed_cfg["banner"])
    elif editor.get("externalImage"): embed.set_image(url=editor["externalImage"])
    
    return embed

def build_bateponto_components(bp: dict) -> list:
    """Constrói os botões públicos do bate-ponto."""
    bp_id = bp["id"]
    return [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label=bp.get("botao_entrada_label") or "Entrada",
                emoji=bp.get("botao_entrada_emoji") or emoji.on,
                style=estilo_para_disnake(bp.get("botao_entrada_estilo", "green")),
                custom_id=f"BP_Acao:entrada:{bp_id}"
            ),
            disnake.ui.Button(
                label=bp.get("botao_saida_label") or "Saída",
                emoji=bp.get("botao_saida_emoji") or emoji.off,
                style=estilo_para_disnake(bp.get("botao_saida_estilo", "red")),
                custom_id=f"BP_Acao:saida:{bp_id}"
            )
        )
    ]

async def publicar_bateponto(inter: disnake.MessageInteraction, bp_id: str):
    """Publica o painel de bate-ponto no canal configurado."""
    bp = get_bateponto(bp_id)
    if not bp: return
    
    canal_id = bp.get("canal_painel_id")
    if not canal_id:
        return await inter.followup.send(f"{emoji.wrong} Canal do painel não configurado!", ephemeral=True)
        
    canal = inter.guild.get_channel(canal_id)
    if not canal:
        return await inter.followup.send(f"{emoji.wrong} Canal não encontrado!", ephemeral=True)

    embed = build_bateponto_embed(bp)
    components = build_bateponto_components(bp)
    content = bp.get("anunciar_editor", {}).get("content")

    try:
        msg = await canal.send(content=content, embed=embed, components=components)
        bp["message_id"] = msg.id
        salvar_bateponto(bp_id, bp)
        await inter.followup.send(f"{emoji.correct} Painel publicado em {canal.mention}!", ephemeral=True)
    except Exception as e:
        await inter.followup.send(f"{emoji.wrong} Erro ao publicar: `{e}`", ephemeral=True)

async def processar_bateponto(inter: disnake.MessageInteraction, bp_id: str, acao: str):
    bp = get_bateponto(bp_id)
    if not bp or not bp.get("ativado"):
        return await inter.response.send_message(f"{emoji.wrong} Este sistema de bate-ponto está desativado.", ephemeral=True)

    # Verificação de cargos
    cargos_perm = bp.get("cargos_permitidos", [])
    if cargos_perm:
        user_roles = [r.id for r in inter.author.roles]
        if not any(int(c) in user_roles for c in cargos_perm):
            return await inter.response.send_message(f"{emoji.wrong} Você não tem permissão para usar este bate-ponto.", ephemeral=True)

    user_id = str(inter.author.id)
    registros = bp.get("registros", {})
    user_data = registros.get(user_id, {"status": "off", "start_time": None, "total_today": 0})
    
    now = datetime.datetime.now()
    log_channel_id = bp.get("canal_logs_id")
    log_channel = inter.guild.get_channel(log_channel_id) if log_channel_id else None

    primary_hex, _ = get_colors()
    color = int(primary_hex.replace("#", ""), 16) if primary_hex else 0x5865F2

    if acao == "entrada":
        if user_data["status"] == "on":
            return await inter.response.send_message(f"{emoji.warn} Você já possui um ponto aberto!", ephemeral=True)
        
        user_data["status"] = "on"
        user_data["start_time"] = now.isoformat()
        
        if log_channel:
            embed = disnake.Embed(title="📥 Entrada Registrada", color=disnake.Color.green())
            embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
            embed.add_field(name="Usuário", value=inter.author.mention)
            embed.add_field(name="Horário", value=f"<t:{int(now.timestamp())}:F>")
            await log_channel.send(embed=embed)

    elif acao == "saida":
        if user_data["status"] == "off":
            return await inter.response.send_message(f"{emoji.warn} Você não possui um ponto aberto!", ephemeral=True)
        
        start_time = datetime.datetime.fromisoformat(user_data["start_time"])
        duration = (now - start_time).total_seconds()
        user_data["total_today"] += duration
        user_data["status"] = "off"
        user_data["start_time"] = None
        
        if log_channel:
            embed = disnake.Embed(title="📤 Saída Registrada", color=disnake.Color.red())
            embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
            embed.add_field(name="Usuário", value=inter.author.mention)
            embed.add_field(name="Duração do Turno", value=f"`{format_duration(duration)}`")
            embed.add_field(name="Horário", value=f"<t:{int(now.timestamp())}:F>")
            await log_channel.send(embed=embed)

    registros[user_id] = user_data
    bp["registros"] = registros
    salvar_bateponto(bp_id, bp)
    
    msg_sucesso = bp.get("mensagem_sucesso", "✅ Seu ponto foi registrado com sucesso!")
    await inter.response.send_message(msg_sucesso, ephemeral=True)
