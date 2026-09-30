"""
modules/utilitarios/comunidade/formulario/response_handler.py

Processa respostas de usuários e as envia para o destino configurado.
Suporta: canal de respostas, tópico privado, DM do staff.
Também gerencia aprovação/rejeição.
"""
from __future__ import annotations

import uuid
import time
import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from .helpers import get_formulario, salvar_formulario, FIELD_TYPES, get_colors

RESPOSTAS_DB_KEY = "formulario_respostas"


# ─── Helpers de DB de respostas ───────────────────────────────────────────────

def carregar_respostas(form_id: str) -> list[dict]:
    dados = db.get_document(RESPOSTAS_DB_KEY) or {}
    return dados.get(form_id, [])


def salvar_resposta(form_id: str, resposta: dict) -> None:
    dados = db.get_document(RESPOSTAS_DB_KEY) or {}
    lista = dados.get(form_id, [])
    # Atualiza se já existe, senão adiciona
    for i, r in enumerate(lista):
        if r.get("id") == resposta.get("id"):
            lista[i] = resposta
            dados[form_id] = lista
            db.save_document(RESPOSTAS_DB_KEY, dados)
            return
    lista.append(resposta)
    dados[form_id] = lista
    db.save_document(RESPOSTAS_DB_KEY, dados)


def get_resposta(form_id: str, resposta_id: str) -> dict | None:
    return next((r for r in carregar_respostas(form_id) if r.get("id") == resposta_id), None)


# ─── Verificações antes de responder ─────────────────────────────────────────

async def verificar_permissao(inter: disnake.MessageInteraction, form: dict) -> tuple[bool, str]:
    cargos_perm = form.get("cargos_permitidos", [])
    if not cargos_perm:
        return True, ""
    user_roles = [r.id for r in getattr(inter.author, "roles", [])]
    if any(int(c) in user_roles for c in cargos_perm):
        return True, ""
    return False, f"{emoji.wrong} Você não tem permissão para preencher este formulário."


def verificar_limite(form: dict) -> tuple[bool, str]:
    limite = form.get("limite_respostas", 0)
    if not limite:
        return True, ""
    respostas = carregar_respostas(form["id"])
    aprovadas = sum(1 for r in respostas if not r.get("rejeitado"))
    if aprovadas >= limite:
        return False, f"{emoji.wrong} Este formulário atingiu o limite máximo de respostas."
    return True, ""


def verificar_ja_respondeu(form: dict, user_id: int) -> bool:
    respostas = carregar_respostas(form["id"])
    return any(r.get("user_id") == user_id and not r.get("rejeitado") for r in respostas)


# ─── Processador principal de resposta modal ─────────────────────────────────

async def processar_resposta_modal(
    inter: disnake.ModalInteraction,
    form: dict,
    modal_instance,
) -> None:
    await inter.response.defer(ephemeral=True)

    # Verificações
    ok, msg = await verificar_permissao(inter, form)
    if not ok:
        return await inter.followup.send(msg, ephemeral=True)

    ok, msg = verificar_limite(form)
    if not ok:
        return await inter.followup.send(msg, ephemeral=True)

    if verificar_ja_respondeu(form, inter.author.id):
        return await inter.followup.send(
            f"{emoji.warn} Você já enviou uma resposta para este formulário.", ephemeral=True
        )

    # Monta a resposta
    respostas_campos = {}
    campos = form.get("campos", [])
    for campo in campos:
        if campo.get("tipo") != "choice":
            valor = inter.text_values.get(campo["id"], "")
            respostas_campos[campo["id"]] = valor

    resposta = {
        "id": str(uuid.uuid4())[:12],
        "form_id": form["id"],
        "user_id": inter.author.id,
        "user_name": inter.author.display_name,
        "user_discriminator": getattr(inter.author, "discriminator", "0"),
        "guild_id": inter.guild.id if inter.guild else None,
        "timestamp": int(time.time()),
        "aprovado": not form.get("requer_aprovacao", False),
        "rejeitado": False,
        "campos": respostas_campos,
        "anonimo": form.get("anonimo", False),
        "channel_id": None,
    }

    salvar_resposta(form["id"], resposta)

    # Incrementar contador
    form["respostas_count"] = form.get("respostas_count", 0) + 1
    salvar_formulario(form["id"], form)

    # Enviar para o destino
    await enviar_resposta_destino(inter, form, resposta)

    msg_sucesso = form.get("mensagem_sucesso") or f"{emoji.correct} Sua resposta foi enviada com sucesso!"
    await inter.followup.send(msg_sucesso, ephemeral=True)


# ─── Enviar resposta para o destino configurado ───────────────────────────────

async def enviar_resposta_destino(
    inter: disnake.Interaction,
    form: dict,
    resposta: dict,
) -> None:
    send_mode = form.get("send_mode", "channel")
    bot = inter.bot

    embed = _build_resposta_embed(form, resposta)
    components = _build_aprovacao_components(form, resposta) if form.get("requer_aprovacao") else []

    if send_mode == "channel":
        canal_id = form.get("canal_respostas_id")
        if canal_id:
            try:
                canal = bot.get_channel(int(canal_id)) or await bot.fetch_channel(int(canal_id))
                msg = await canal.send(embed=embed, components=components or None)
                resposta["channel_id"] = canal.id
                resposta["message_id"] = msg.id
                salvar_resposta(form["id"], resposta)
            except Exception as e:
                print(f"[Formulário] Erro ao enviar para canal: {e}")

    elif send_mode == "topic":
        canal_id = form.get("canal_topicos_id")
        if canal_id and inter.guild:
            try:
                canal = bot.get_channel(int(canal_id)) or await bot.fetch_channel(int(canal_id))
                if isinstance(canal, disnake.TextChannel):
                    user_name = resposta["user_name"] if not resposta.get("anonimo") else "Anônimo"
                    thread = await canal.create_thread(
                        name=f"{form.get('nome', 'Form')[:30]} — {user_name}",
                        type=disnake.ChannelType.private_thread,
                        invitable=False,
                    )
                    await thread.send(embed=embed, components=components or None)

                    # Adicionar o autor ao tópico se não for anônimo
                    if not resposta.get("anonimo") and inter.guild:
                        member = inter.guild.get_member(resposta["user_id"])
                        if member:
                            await thread.add_user(member)

                    resposta["channel_id"] = thread.id
                    salvar_resposta(form["id"], resposta)
            except Exception as e:
                print(f"[Formulário] Erro ao criar tópico: {e}")

    elif send_mode == "dm":
        cargos_noti = form.get("cargos_notificar", [])
        if inter.guild and cargos_noti:
            for cargo_id in cargos_noti:
                try:
                    role = inter.guild.get_role(int(cargo_id))
                    if role:
                        for member in role.members[:10]:  # limita a 10 por cargo
                            try:
                                await member.send(embed=embed, components=components or None)
                            except disnake.Forbidden:
                                pass
                except Exception as e:
                    print(f"[Formulário] Erro ao enviar DM: {e}")

    # Notificar cargos se configurado e send_mode não for dm
    if send_mode != "dm":
        await _notificar_cargos(inter, form, resposta)


async def _notificar_cargos(inter: disnake.Interaction, form: dict, resposta: dict) -> None:
    cargos_noti = form.get("cargos_notificar", [])
    if not cargos_noti or not inter.guild:
        return
    primary_hex, ck = get_colors()
    for cargo_id in cargos_noti:
        try:
            role = inter.guild.get_role(int(cargo_id))
            if not role:
                continue
            canal_id = form.get("canal_respostas_id") or form.get("canal_topicos_id")
            canal_mention = f"<#{canal_id}>" if canal_id else "canal configurado"
            nome_form = form.get("nome", "Formulário")
            user_str = f"<@{resposta['user_id']}>" if not resposta.get("anonimo") else "um usuário anônimo"
            texto = f"{emoji.warn} Nova resposta em **{nome_form}** de {user_str}! Veja em {canal_mention}."
            for member in role.members[:5]:
                try:
                    await member.send(texto)
                except disnake.Forbidden:
                    pass
        except Exception:
            pass


# ─── Builders de embed de resposta ───────────────────────────────────────────

def _build_resposta_embed(form: dict, resposta: dict) -> disnake.Embed:
    primary_hex, _ = get_colors()
    cor = int(primary_hex.replace("#", ""), 16) if primary_hex else 0x5865F2

    user_str = (
        f"<@{resposta['user_id']}> (`{resposta.get('user_name', '?')}`)"
        if not resposta.get("anonimo")
        else "🕵️ Anônimo"
    )
    ts = resposta.get("timestamp")
    ts_fmt = f"<t:{ts}:f>" if ts else "?"

    embed = disnake.Embed(
        title=f"📋 Nova Resposta — {form.get('nome', 'Formulário')}",
        color=cor,
    )
    embed.add_field(name="Enviado por", value=user_str, inline=True)
    embed.add_field(name="Enviado em", value=ts_fmt, inline=True)

    if form.get("requer_aprovacao"):
        embed.add_field(name="Status", value="⏳ Aguardando aprovação", inline=True)

    embed.add_field(name="\u200b", value="\u200b", inline=False)

    campos_form = {c["id"]: c for c in form.get("campos", [])}
    for campo_id, valor in resposta.get("campos", {}).items():
        campo = campos_form.get(campo_id, {})
        label = campo.get("label", campo_id)
        embed.add_field(name=label, value=valor[:1024] if valor else "`(vazio)`", inline=False)

    embed.set_footer(text=f"ID da resposta: {resposta.get('id', '?')}")
    return embed


def _build_aprovacao_components(form: dict, resposta: dict) -> list[disnake.ui.ActionRow]:
    form_id = form["id"]
    resp_id = resposta["id"]
    return [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Aprovar", style=disnake.ButtonStyle.green,emoji=emoji.correct,
                custom_id=f"Form_Aprovar:{form_id}:{resp_id}",
            ),
            disnake.ui.Button(
                label="Rejeitar", style=disnake.ButtonStyle.red, emoji=emoji.wrong,
                custom_id=f"Form_Rejeitar:{form_id}:{resp_id}",
            ),
        )
    ]


# ─── Aprovação e rejeição ─────────────────────────────────────────────────────

async def processar_aprovacao(
    inter: disnake.MessageInteraction,
    form_id: str,
    resposta_id: str,
) -> None:
    await inter.response.defer(ephemeral=True)
    form = get_formulario(form_id)
    resposta = get_resposta(form_id, resposta_id)

    if not form or not resposta:
        return await inter.followup.send(f"{emoji.wrong} Resposta não encontrada.", ephemeral=True)

    resposta["aprovado"] = True
    resposta["rejeitado"] = False
    resposta["aprovado_por"] = inter.author.id
    resposta["aprovado_em"] = int(time.time())
    salvar_resposta(form_id, resposta)

    # Notificar o usuário e conceder cargo se configurado
    try:
        user = inter.guild.get_member(resposta["user_id"]) if inter.guild else None
        if user:
            primary_hex, _ = get_colors()
            cor = int(primary_hex.replace("#", ""), 16) if primary_hex else 0x57F287

            # Conceder cargo de aprovação se configurado
            cargo_id = form.get("cargo_aprovacao_id")
            if cargo_id and inter.guild:
                try:
                    role = inter.guild.get_role(int(cargo_id))
                    if role and role not in user.roles:
                        await user.add_roles(role, reason=f"Formulário aprovado: {form.get('nome')}")
                except Exception as e:
                    print(f"[Formulário] Erro ao conceder cargo: {e}")

            # Mensagem customizada de aprovação
            template = form.get("msg_aprovado") or f"{emoji.correct} Sua resposta ao formulário **{nome}** foi aprovada!"
            descricao = template.replace("{nome}", form.get("nome", "")).replace("{aprovador}", inter.author.display_name)
            embed = disnake.Embed(
                title="Resposta Aprovada",
                description=descricao,
                color=cor,
            )
            await user.send(embed=embed)
    except Exception:
        pass

    # Atualizar a mensagem original
    try:
        embed_novo = _build_resposta_embed(form, resposta)
        embed_novo.color = 0x57F287
        embed_novo.set_field_at(2, name="Status", value=f"{emoji.correct} Aprovada", inline=True)
        await inter.edit_original_message(embed=embed_novo, components=[])
    except Exception:
        pass

    await inter.followup.send(f"{emoji.correct} Resposta aprovada com sucesso!", ephemeral=True)

    # ── Registrar ponto de formulário aprovado para quem aprovou ─────────────
    try:
        from .staff_manager import registrar_ponto
        registrar_ponto(
            inter.author.id,
            "form_aprovado",
            detalhes=f"Formulário: {form.get('nome', '')}",
            guild=inter.guild,
        )
    except Exception:
        pass


async def processar_rejeicao(
    inter: disnake.ModalInteraction | disnake.MessageInteraction,
    form_id: str,
    resposta_id: str,
    motivo: str = "",
) -> None:
    form = get_formulario(form_id)
    resposta = get_resposta(form_id, resposta_id)

    if not form or not resposta:
        if inter.response.is_done():
            return await inter.followup.send(f"{emoji.wrong} Resposta não encontrada.", ephemeral=True)
        return await inter.response.send_message(f"{emoji.wrong} Resposta não encontrada.", ephemeral=True)

    resposta["aprovado"] = False
    resposta["rejeitado"] = True
    resposta["rejeitado_por"] = inter.author.id
    resposta["rejeitado_em"] = int(time.time())
    if motivo:
        resposta["motivo_rejeicao"] = motivo
    salvar_resposta(form_id, resposta)

    # Notificar o usuário
    try:
        guild = inter.guild
        user = guild.get_member(resposta["user_id"]) if guild else None
        if user:
            primary_hex, _ = get_colors()
            template = form.get("msg_reprovado") or f"{emoji.wrong} Sua resposta ao formulário **{nome}** foi reprovada."
            descricao = template.replace("{nome}", form.get("nome", "")).replace("{reprovador}", inter.author.display_name)
            embed = disnake.Embed(
                title=f"{emoji.wrong}Resposta Rejeitada",
                description=descricao,
                color=0xED4245,
            )
            if motivo:
                embed.add_field(name="Motivo", value=motivo, inline=False)
            await user.send(embed=embed)
    except Exception:
        pass

    try:
        if inter.response.is_done():
            await inter.edit_original_message(components=[])
        else:
            await inter.response.edit_message(components=[])
    except Exception:
        pass

    try:
        await inter.followup.send(f"{emoji.correct} Resposta rejeitada.", ephemeral=True)
    except Exception:
        pass

    # ── Registrar ponto de formulário rejeitado para quem rejeitou ───────────
    try:
        from .staff_manager import registrar_ponto
        registrar_ponto(
            inter.author.id,
            "form_rejeitado",
            detalhes=f"Formulário: {form.get('nome', '')}",
            guild=inter.guild,
        )
    except Exception:
        pass