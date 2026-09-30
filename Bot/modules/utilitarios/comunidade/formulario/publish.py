"""
modules/utilitarios/comunidade/formulario/publish.py

Publica o painel do formulário no canal configurado.
"""
from __future__ import annotations

import io
import csv
import disnake
from functions.emoji import emoji
from .helpers import get_formulario, salvar_formulario, build_formulario_embed, build_formulario_components, get_colors
from .response_handler import carregar_respostas


async def publicar_formulario(inter: disnake.MessageInteraction, form_id: str) -> None:
    """Publica ou atualiza o formulário no canal configurado."""
    await inter.response.defer(ephemeral=True)

    form = get_formulario(form_id)
    if not form:
        return await inter.followup.send(f"{emoji.wrong} Formulário não encontrado.", ephemeral=True)

    canal_id = form.get("canal_painel_id")
    if not canal_id:
        return await inter.followup.send(
            f"{emoji.wrong} Configure o **canal do painel** antes de publicar.\n"
            f"Acesse **Canais** no editor do formulário.",
            ephemeral=True,
        )

    if not form.get("campos"):
        return await inter.followup.send(
            f"{emoji.wrong} Adicione pelo menos **1 campo** antes de publicar.",
            ephemeral=True,
        )

    try:
        canal = inter.bot.get_channel(int(canal_id)) or await inter.bot.fetch_channel(int(canal_id))
    except Exception:
        return await inter.followup.send(
            f"{emoji.wrong} O canal configurado não foi encontrado.", ephemeral=True
        )

    mode = form.get("display_mode", "modal")
    primary_hex, _ = get_colors()

    # Se o formulário tem dados do editor do Anúncios, usa o Builder para montar a mensagem
    anunciar_editor = form.get("anunciar_editor")
    if anunciar_editor:
        from commands.admin.anunciar.builder import Builder
        cfg = {
            "message": {
                "content":       anunciar_editor.get("content"),
                "container":     anunciar_editor.get("container"),
                "externalImage": anunciar_editor.get("externalImage"),
                "embed": anunciar_editor.get("embed") or {
                    "title": None, "description": None,
                    "color": None, "footer": None,
                    "banner": None, "thumbnail": None,
                },
                "buttons": [],
                "selects": [],
                "send_mode": "auto",
                "component_order": ["buttons", "selects"],
            }
        }
        built = await Builder.build_from_cfg(cfg)
        btn_row = build_formulario_components(form)

        # Monta kwargs de envio com o botão do formulário sempre presente
        if built["mode"] == "v2":
            send_kwargs = {
                "components": built["components"] + btn_row,
                "flags": built["flags"],
            }
        else:
            send_kwargs = {}
            if built.get("content"):
                send_kwargs["content"] = built["content"]
            if built.get("embed"):
                send_kwargs["embed"] = built["embed"]
            send_kwargs["components"] = btn_row
            if built.get("files"):
                send_kwargs["files"] = built["files"]
    else:
        embed = build_formulario_embed(form)
        components = build_formulario_components(form)

        if mode == "channel":
            canal_form_id = form.get("canal_painel_id")
            if canal_form_id:
                embed.add_field(
                    name="Como preencher",
                    value="Envie suas respostas diretamente neste canal ou clique no botão abaixo.",
                    inline=False,
                )

        send_kwargs = {"embed": embed, "components": components}

    # Se tem mensagem publicada, tentar editar
    msg_id = form.get("message_id")
    if msg_id:
        try:
            msg = await canal.fetch_message(int(msg_id))
            await msg.edit(**send_kwargs)
            form["ativado"] = True
            salvar_formulario(form_id, form)
            await inter.followup.send(
                f"{emoji.correct} Formulário **{form['nome']}** atualizado em {canal.mention}!",
                ephemeral=True,
            )
            return
        except disnake.NotFound:
            pass

    # Enviar nova mensagem
    try:
        msg = await canal.send(**send_kwargs)
        form["message_id"] = msg.id
        form["ativado"] = True
        salvar_formulario(form_id, form)
        await inter.followup.send(
            f"{emoji.correct} Formulário **{form['nome']}** publicado em {canal.mention}!",
            ephemeral=True,
        )
    except disnake.Forbidden:
        await inter.followup.send(
            f"{emoji.wrong} Não tenho permissão para enviar mensagens em {canal.mention}.",
            ephemeral=True,
        )
    except Exception as e:
        await inter.followup.send(
            f"{emoji.wrong} Erro ao publicar: `{e}`",
            ephemeral=True,
        )


async def exportar_csv(inter: disnake.MessageInteraction, form_id: str) -> None:
    """Exporta as respostas do formulário em CSV e envia como arquivo."""
    await inter.response.defer(ephemeral=True)

    form = get_formulario(form_id)
    if not form:
        return await inter.followup.send(f"{emoji.wrong} Formulário não encontrado.", ephemeral=True)

    respostas = carregar_respostas(form_id)
    if not respostas:
        return await inter.followup.send(f"{emoji.warn} Nenhuma resposta encontrada.", ephemeral=True)

    campos = form.get("campos", [])
    headers = ["ID", "Usuário", "User ID", "Data/Hora", "Aprovado", "Rejeitado"] + [
        c["label"] for c in campos
    ]

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)

    import datetime
    for r in respostas:
        ts = r.get("timestamp")
        dt_str = datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M") if ts else ""
        user_str = "Anônimo" if r.get("anonimo") else r.get("user_name", "?")
        user_id_str = "" if r.get("anonimo") else str(r.get("user_id", ""))

        row = [
            r.get("id", ""),
            user_str,
            user_id_str,
            dt_str,
            "Sim" if r.get("aprovado") else "Não",
            "Sim" if r.get("rejeitado") else "Não",
        ]
        campos_dict = r.get("campos", {})
        for c in campos:
            row.append(campos_dict.get(c["id"], ""))

        writer.writerow(row)

    output.seek(0)
    file_bytes = output.getvalue().encode("utf-8-sig")
    file = disnake.File(
        io.BytesIO(file_bytes),
        filename=f"respostas_{form.get('nome', 'formulario').replace(' ', '_')}.csv",
    )
    await inter.followup.send(
        f"{emoji.receipt} Exportação de **{len(respostas)}** respostas:",
        file=file,
        ephemeral=True,
    )