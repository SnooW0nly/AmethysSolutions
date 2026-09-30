from __future__ import annotations

import asyncio
import io
from datetime import datetime

import aiohttp
import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from modules.utilitarios.comunidade.instagram import helpers
from modules.utilitarios.comunidade.instagram.helpers import (
    build_post_container, build_post_embed,
    load_json, save_json,
    REACTIONS_JSON, COMMENTS_JSON, POSTS_JSON,
)

_WEBHOOK_DB_KEY  = "automations_instagram_webhook"
_HALL_MSG_DB_KEY = "automations_instagram_hall_msg"


async def _baixar_imagem(url: str) -> tuple[bytes, str] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                ct   = resp.content_type or "image/png"
                return data, ct
    except Exception:
        return None


async def _obter_ou_criar_webhook(canal: disnake.TextChannel) -> disnake.Webhook | None:
    salvo    = db.get_document(_WEBHOOK_DB_KEY) or {}
    wh_id    = salvo.get("id")
    wh_token = salvo.get("token")

    if wh_id and wh_token:
        try:
            webhooks = await canal.webhooks()
            for wh in webhooks:
                if str(wh.id) == str(wh_id):
                    return wh
        except disnake.HTTPException:
            pass

    try:
        webhook = await canal.create_webhook(name="Instagram")
        db.save_document(_WEBHOOK_DB_KEY, {}, {"id": str(webhook.id), "token": webhook.token})
        return webhook
    except disnake.HTTPException:
        return None


class InstagramTaskCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._hall_loop.start()

    def cog_unload(self):
        self._hall_loop.cancel()

    # ── Hall da Fama (loop a cada 5 minutos) ─────────────────────────────────

    @tasks.loop(minutes=5)
    async def _hall_loop(self):
        try:
            config      = helpers.carregar_config()
            hall_id     = config.get("hall_id")
            if not hall_id:
                return

            canal: disnake.TextChannel | None = self.bot.get_channel(int(hall_id))
            if not isinstance(canal, disnake.TextChannel):
                return

            reactions = load_json(REACTIONS_JSON)
            posts     = load_json(POSTS_JSON)
            if not posts or not reactions:
                return

            # Post com mais curtidas
            melhor_id = max(posts.keys(), key=lambda pid: len(reactions.get(pid, [])), default=None)
            if not melhor_id:
                return

            qtd_likes = len(reactions.get(melhor_id, []))
            post      = posts[melhor_id]

            mode        = db.get_document("custom_mode").get("mode")
            primary_hex = db.get_document("custom_colors").get("primary")
            canal_post  = config.get("canal_id")
            jump_url    = f"https://discord.com/channels/{canal.guild.id}/{canal_post}/{melhor_id}"

            # Montar componentes do hall
            btn_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ver publicacao",
                    style=disnake.ButtonStyle.link,
                    url=jump_url,
                    emoji="📸",
                )
            )

            salvo_hall = db.get_document(_HALL_MSG_DB_KEY) or {}
            msg_id     = salvo_hall.get("msg_id")

            if mode == "embed":
                embed = disnake.Embed(
                    title="🏆 Hall da Fama",
                    description=(
                        f"**Autor:** {post['autor_mencao']}\n"
                        f"**Curtidas:** {qtd_likes} ❤️\n"
                        f"**Publicado em:** <t:{int(datetime.fromisoformat(post['criado_em']).timestamp())}:R>"
                        + (f"\n\n{post['conteudo']}" if post.get("conteudo") else "")
                    ),
                )
                embed.set_image(url=post["imagem_url"])
                if primary_hex:
                    embed.color = helpers.color(primary_hex)

                if msg_id:
                    try:
                        msg = await canal.fetch_message(int(msg_id))
                        await msg.edit(embed=embed, components=[btn_row])
                        return
                    except disnake.HTTPException:
                        pass

                msg = await canal.send(embed=embed, components=[btn_row])
            else:
                texto = (
                    f"# 🏆 Hall da Fama\n"
                    f"**Autor:** {post['autor_mencao']}\n"
                    f"**Curtidas:** {qtd_likes} ❤️\n"
                    f"**Publicado em:** <t:{int(datetime.fromisoformat(post['criado_em']).timestamp())}:R>"
                    + (f"\n\n{post['conteudo']}" if post.get("conteudo") else "")
                )
                container = disnake.ui.Container(
                    disnake.ui.MediaGallery(
                        disnake.MediaGalleryItem(media=post["imagem_url"], description="Post mais curtido")
                    ),
                    disnake.ui.Separator(divider=True, spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.TextDisplay(texto),
                    disnake.ui.Separator(divider=True, spacing=disnake.SeparatorSpacing.small),
                    btn_row,
                    **helpers.accent(primary_hex),
                )

                if msg_id:
                    try:
                        msg = await canal.fetch_message(int(msg_id))
                        await msg.edit(components=[container])
                        return
                    except disnake.HTTPException:
                        pass

                msg = await canal.send(components=[container])

            db.save_document(_HALL_MSG_DB_KEY, {}, {"msg_id": str(msg.id)})
        except Exception:
            pass

    @_hall_loop.before_loop
    async def _before_hall(self):
        await self.bot.wait_until_ready()

    # ── Listener on_message ───────────────────────────────────────────────────

    @commands.Cog.listener("on_message")
    async def _instagram_on_message(self, msg: disnake.Message):
        if msg.author.bot or not msg.guild:
            return

        config   = helpers.carregar_config()
        ativado  = config.get("ativado", False)
        canal_id = config.get("canal_id")

        if not ativado or not canal_id:
            return

        if msg.channel.id != int(canal_id):
            return

        # Verificar cargo obrigatorio
        cargo_id = config.get("cargo_id")
        if cargo_id:
            member_roles = [r.id for r in getattr(msg.author, "roles", [])]
            if int(cargo_id) not in member_roles:
                try:
                    await msg.delete()
                except disnake.HTTPException:
                    pass
                return

        # Verificar imagem obrigatoria
        imagem_att: disnake.Attachment | None = None
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                imagem_att = att
                break

        if not imagem_att:
            try:
                await msg.delete()
            except disnake.HTTPException:
                pass
            return

        # Baixar imagem ANTES de deletar a mensagem
        resultado = await _baixar_imagem(imagem_att.url)
        if not resultado:
            # Sem imagem baixada nao da pra continuar (URL vai expirar)
            try:
                await msg.delete()
            except disnake.HTTPException:
                pass
            return

        imagem_bytes, imagem_ct = resultado
        ext = imagem_ct.split("/")[-1].replace("jpeg", "jpg")

        autor_nome   = msg.author.display_name
        autor_avatar = msg.author.display_avatar.url
        autor_mencao = msg.author.mention
        conteudo     = msg.content.strip() or None
        emojis       = config.get("emojis", {})
        mode         = db.get_document("custom_mode").get("mode")
        primary_hex  = db.get_document("custom_colors").get("primary")
        filename     = f"post.{ext}"
        attach_url   = f"attachment://{filename}"

        # Obter webhook fixo
        webhook = await _obter_ou_criar_webhook(msg.channel)

        # Deletar mensagem original
        try:
            await msg.delete()
        except disnake.HTTPException:
            pass

        # ── Enviar post com a imagem como File (URL permanente via attachment://) ──
        # Nao deletamos a mensagem de upload — ela É o post.
        # O disnake aceita attachment://filename.ext dentro de embed/MediaGallery.
        sent_msg: disnake.WebhookMessage | disnake.Message | None = None

        arquivo = disnake.File(io.BytesIO(imagem_bytes), filename=filename)

        try:
            if webhook:
                if mode == "embed":
                    embed, comps = build_post_embed(
                        autor_nome, autor_avatar, autor_mencao,
                        attach_url, conteudo, 0, emojis, primary_hex,
                    )
                    sent_msg = await webhook.send(
                        embed=embed, components=comps,
                        file=arquivo,
                        username=autor_nome, avatar_url=autor_avatar,
                        wait=True,
                    )
                else:
                    comps = build_post_container(
                        autor_mencao, attach_url, conteudo,
                        0, emojis, primary_hex,
                    )
                    sent_msg = await webhook.send(
                        components=comps,
                        file=arquivo,
                        username=autor_nome, avatar_url=autor_avatar,
                        wait=True,
                    )
        except disnake.HTTPException:
            pass

        if not sent_msg:
            arquivo = disnake.File(io.BytesIO(imagem_bytes), filename=filename)
            try:
                if mode == "embed":
                    embed, comps = build_post_embed(
                        autor_nome, autor_avatar, autor_mencao,
                        attach_url, conteudo, 0, emojis, primary_hex,
                    )
                    sent_msg = await msg.channel.send(embed=embed, components=comps, file=arquivo)
                else:
                    comps = build_post_container(
                        autor_mencao, attach_url, conteudo,
                        0, emojis, primary_hex,
                    )
                    sent_msg = await msg.channel.send(components=comps, file=arquivo)
            except disnake.HTTPException:
                pass

        if not sent_msg:
            return

        real_id = str(sent_msg.id)

        # Pegar a URL CDN do attachment da mensagem enviada.
        # Mantemos a query string (?ex=&is=&hm=) intacta — ela é válida por horas,
        # tempo suficiente para o edit imediato. Para o Hall da Fama (loop de 5min),
        # o Discord refresca automaticamente as URLs de attachments persistidos.
        imagem_url_final = imagem_att.url  # fallback: URL original ainda válida
        if sent_msg.attachments:
            imagem_url_final = sent_msg.attachments[0].url
        elif sent_msg.embeds and sent_msg.embeds[0].image:
            imagem_url_final = sent_msg.embeds[0].image.url

        # ── Salvar dados ANTES de editar (edit le o JSON para montar label) ───
        posts = load_json(POSTS_JSON)
        posts[real_id] = {
            "canal_id":     msg.channel.id,
            "autor_id":     msg.author.id,
            "autor_nome":   autor_nome,
            "autor_avatar": autor_avatar,
            "autor_mencao": autor_mencao,
            "conteudo":     conteudo,
            "imagem_url":   imagem_url_final,
            "criado_em":    datetime.now().isoformat(),
        }
        save_json(POSTS_JSON, posts)

        for json_path in (REACTIONS_JSON, COMMENTS_JSON):
            data = load_json(json_path)
            if real_id not in data:
                data[real_id] = []
                save_json(json_path, data)

        # ── Editar via webhook para ativar botoes com real_id ─────────────────
        # IMPORTANTE: no edit, precisamos reenviar o arquivo para que attachment://
        # continue válido. Sem isso a imagem quebra pois attachment:// só existe
        # enquanto o file estiver presente na requisição.
        try:
            arquivo_edit = disnake.File(io.BytesIO(imagem_bytes), filename=filename)
            if mode == "embed":
                embed, comps = build_post_embed(
                    autor_nome, autor_avatar, autor_mencao,
                    attach_url, conteudo, real_id, emojis, primary_hex,
                )
                await sent_msg.edit(embed=embed, components=comps, file=arquivo_edit)
            else:
                comps = build_post_container(
                    autor_mencao, attach_url, conteudo,
                    real_id, emojis, primary_hex,
                )
                await sent_msg.edit(components=comps, file=arquivo_edit)
        except disnake.HTTPException:
            pass

        await helpers.enviar_log(
            self.bot,
            "Novo Post no Instagram",
            (
                f"**Autor:** {autor_mencao}\n"
                f"**Canal:** <#{msg.channel.id}>\n"
                f"**Post:** [Clique aqui]({sent_msg.jump_url})"
            ),
        )


def setup(bot: commands.Bot):
    bot.add_cog(InstagramTaskCog(bot))