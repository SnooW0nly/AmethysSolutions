"""
modules/utilitarios/comunidade/twitter/cog.py

Sistema de Twitter/X — painel simples (canal, cargo, admin, toggle)
+ listener de mensagens + todos os botões/modais.
"""
from __future__ import annotations

import asyncio
import io
from datetime import datetime

import aiohttp
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from . import helpers
from .helpers import (
    accent, color,
    build_post_buttons,
    load_json, save_json,
    gerar_imagem_tweet,
    REACTIONS_JSON, COMMENTS_JSON, RETWEETS_JSON, POSTS_JSON,
)

# ── X webhook avatar (logo X branco em fundo preto, PNG 256x256 em base64) ────
# Pequeno PNG gerado via Pillow na primeira chamada
_X_AVATAR_CACHE: bytes | None = None


def _get_x_avatar() -> bytes:
    global _X_AVATAR_CACHE
    if _X_AVATAR_CACHE:
        return _X_AVATAR_CACHE
    from PIL import Image, ImageDraw
    size = 256
    img  = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad  = int(size * 0.20)
    lw   = max(12, int(size * 0.10))
    draw.line([(pad, pad), (size - pad, size - pad)], fill=(255, 255, 255), width=lw)
    draw.line([(size - pad, pad), (pad, size - pad)], fill=(255, 255, 255), width=lw)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    _X_AVATAR_CACHE = buf.getvalue()
    return _X_AVATAR_CACHE


async def _fetch_bytes(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return await r.read()
    except Exception:
        return None


def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


def _primary() -> str | None:
    return (db.get_document("custom_colors") or {}).get("primary")


def _fmt_timestamp(dt: datetime) -> str:
    months = [
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    ]
    return f"{dt.day}/{months[dt.month - 1]}/{dt.year} às {dt.strftime('%H:%M')}"


# ─── Cog ─────────────────────────────────────────────────────────────────────

class TwitterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Painel ───────────────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        config       = helpers.carregar_config()
        ativado      = config.get("ativado", False)
        canal_id     = config.get("canal_id")
        cargo_id     = config.get("cargo_id")
        admin_id     = config.get("admin_cargo_id")
        primary_hex  = _primary()

        canal_txt = f"<#{canal_id}>"  if canal_id  else "`Não configurado`"
        cargo_txt = f"<@&{cargo_id}>" if cargo_id  else "`Qualquer um`"
        admin_txt = f"<@&{admin_id}>" if admin_id  else "`Não configurado`"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.textc} **Canal:** {canal_txt}\n"
            f"{emoji.role} **Cargo para postar:** {cargo_txt}\n"
            f"{emoji.shield} **Cargo admin:** {admin_txt}"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# 𝕏 Twitter/X\n"
                    f"-# Painel > Comunidade > **Twitter/X**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Tenha um Twitter/X dentro do servidor."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="", emoji=emoji.power,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TW_ToggleAtivo",
                        disabled=not bool(canal_id),
                    ),
                    disnake.ui.Button(
                        label="Canal", emoji=emoji.textc,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TW_ConfigCanal",
                    ),
                    disnake.ui.Button(
                        label="Cargo postar", emoji=emoji.role,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TW_ConfigCargo",
                    ),
                    disnake.ui.Button(
                        label="Cargo admin", emoji=emoji.shield,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TW_ConfigAdmin",
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Remover cargo postar", emoji=emoji.minus,
                        style=disnake.ButtonStyle.red,
                        custom_id="TW_RemoverCargo",
                        disabled=not bool(cargo_id),
                    ),
                    disnake.ui.Button(
                        label="Remover cargo admin", emoji=emoji.minus,
                        style=disnake.ButtonStyle.red,
                        custom_id="TW_RemoverAdmin",
                        disabled=not bool(admin_id),
                    ),
                ),
                **accent(primary_hex),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", emoji=emoji.back,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Comunidade_VoltarFeature",
                ),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        config      = helpers.carregar_config()
        ativado     = config.get("ativado", False)
        canal_id    = config.get("canal_id")
        cargo_id    = config.get("cargo_id")
        admin_id    = config.get("admin_cargo_id")
        primary_hex = _primary()

        canal_txt = f"<#{canal_id}>"  if canal_id  else "`Não configurado`"
        cargo_txt = f"<@&{cargo_id}>" if cargo_id  else "`Qualquer um`"
        admin_txt = f"<@&{admin_id}>" if admin_id  else "`Não configurado`"

        embed = disnake.Embed(title="𝕏 Twitter/X", description="Tenha um Twitter/X dentro do servidor.")
        if primary_hex:
            embed.color = color(primary_hex)
        embed.add_field(name="Configurações", inline=False, value=(
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.textc} **Canal:** {canal_txt}\n"
            f"{emoji.role} **Cargo para postar:** {cargo_txt}\n"
            f"{emoji.shield} **Cargo admin:** {admin_txt}"
        ))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", emoji=emoji.power,
                    style=disnake.ButtonStyle.grey,
                    custom_id="TW_ToggleAtivo",
                    disabled=not bool(canal_id),
                ),
                disnake.ui.Button(
                    label="Canal", emoji=emoji.textc,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="TW_ConfigCanal",
                ),
                disnake.ui.Button(
                    label="Cargo postar", emoji=emoji.role,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="TW_ConfigCargo",
                ),
                disnake.ui.Button(
                    label="Cargo admin", emoji=emoji.shield,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="TW_ConfigAdmin",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Remover cargo postar", emoji=emoji.minus,
                    style=disnake.ButtonStyle.red,
                    custom_id="TW_RemoverCargo",
                    disabled=not bool(cargo_id),
                ),
                disnake.ui.Button(
                    label="Remover cargo admin", emoji=emoji.minus,
                    style=disnake.ButtonStyle.red,
                    custom_id="TW_RemoverAdmin",
                    disabled=not bool(admin_id),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", emoji=emoji.back,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Comunidade_VoltarFeature",
                ),
            ),
        ]
        return embed, components

    # ── Renderizar painel ─────────────────────────────────────────────────────

    async def _render_painel(self, inter: disnake.MessageInteraction, mode: str):
        if mode == "embed":
            emb, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=self.Painel())

    # ─────────────────────────────────────────────────────────────────────────
    # LISTENER — mensagens no canal configurado
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_message")
    async def _twitter_on_message(self, msg: disnake.Message):
        if msg.author.bot or not msg.guild:
            return

        config   = helpers.carregar_config()
        if not config.get("ativado"):
            return

        canal_id = config.get("canal_id")
        if not canal_id or msg.channel.id != int(canal_id):
            return

        # Verificar cargo
        cargo_id = config.get("cargo_id")
        if cargo_id:
            roles = [r.id for r in getattr(msg.author, "roles", [])]
            if int(cargo_id) not in roles:
                try:
                    await msg.delete()
                except disnake.HTTPException:
                    pass
                return

        # Precisa ter texto
        conteudo = msg.content.strip()
        if not conteudo:
            try:
                await msg.delete()
            except disnake.HTTPException:
                pass
            return

        await asyncio.sleep(0.2)

        autor_nome   = msg.author.display_name
        autor_handle = msg.author.name
        autor_avatar_url = str(msg.author.display_avatar.url)

        # Baixar avatar
        avatar_bytes = await _fetch_bytes(autor_avatar_url)

        now = datetime.now()
        ts  = _fmt_timestamp(now)

        # Gerar imagem (sem post_id ainda — stats zerados)
        buf = gerar_imagem_tweet(
            mensagem           = conteudo,
            autor_nome         = autor_nome,
            autor_handle       = autor_handle,
            autor_avatar_bytes = avatar_bytes,
            timestamp          = ts,
        )

        # Criar webhook com nome "X" e avatar do X
        webhook: disnake.Webhook | None = None
        try:
            x_av = _get_x_avatar()
            webhook = await msg.channel.create_webhook(
                name="𝕏",
                avatar=x_av,
            )
        except disnake.HTTPException:
            pass

        # Deletar mensagem original
        try:
            await msg.delete()
        except disnake.HTTPException:
            pass

        file  = disnake.File(io.BytesIO(buf.read()), filename="tweet.png")
        comps = [build_post_buttons(0)]   # botões desabilitados até termos o ID real

        sent_msg = None
        if webhook:
            try:
                sent_msg = await webhook.send(
                    file=file,
                    components=comps,
                    username="𝕏",
                    avatar_url=None,   # usa o avatar do webhook
                    wait=True,
                )
            except disnake.HTTPException:
                pass
            finally:
                try:
                    await webhook.delete()
                except disnake.HTTPException:
                    pass

        if not sent_msg:
            buf.seek(0)
            file2 = disnake.File(io.BytesIO(buf.read()), filename="tweet.png")
            try:
                sent_msg = await msg.channel.send(file=file2, components=comps)
            except disnake.HTTPException:
                return

        real_id = str(sent_msg.id)

        # Salvar post
        posts = load_json(POSTS_JSON)
        posts[real_id] = {
            "canal_id":        str(msg.channel.id),
            "autor_id":        str(msg.author.id),
            "autor_nome":      autor_nome,
            "autor_handle":    autor_handle,
            "autor_avatar_url": autor_avatar_url,
            "conteudo":        conteudo,
            "timestamp":       ts,
            "criado_em":       now.isoformat(),
        }
        save_json(POSTS_JSON, posts)

        for jp in (REACTIONS_JSON, COMMENTS_JSON, RETWEETS_JSON):
            d = load_json(jp)
            if real_id not in d:
                d[real_id] = []
                save_json(jp, d)

        # Reeditar com botões usando o ID real
        buf2 = gerar_imagem_tweet(
            mensagem           = conteudo,
            autor_nome         = autor_nome,
            autor_handle       = autor_handle,
            autor_avatar_bytes = avatar_bytes,
            timestamp          = ts,
            post_id            = real_id,
        )
        try:
            f3 = disnake.File(io.BytesIO(buf2.read()), filename="tweet.png")
            await sent_msg.edit(
                attachments=[f3],
                components=[build_post_buttons(real_id)],
            )
        except disnake.HTTPException:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # LISTENER — botões
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _tw_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("TW_"):
            return

        # ── Botões que abrem modal ────────────────────────────────────────────
        if cid.startswith("TW_comentar_"):
            post_id = cid.replace("TW_comentar_", "")
            await inter.response.send_modal(ComentarModal(post_id, self.bot))
            return

        # ── Botões de post (curtir, retweet, stats, apagar) ───────────────────
        if any(cid.startswith(p) for p in ("TW_curtir_", "TW_retweet_", "TW_stats_", "TW_apagar_")):
            await self._handle_post_button(inter, cid)
            return

        # ── Botões do painel ──────────────────────────────────────────────────
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        primary_hex = _primary()

        if cid == "TW_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "TW_RemoverCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "TW_RemoverAdmin":
            config = helpers.carregar_config()
            config["admin_cargo_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "TW_VoltarPainel":
            await self._render_painel(inter, mode)
            return

        if cid == "TW_ConfigCanal":
            row_sel = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal do Twitter/X...",
                    custom_id="TW_SelectCanal",
                    min_values=1, max_values=1,
                    channel_types=[disnake.ChannelType.text],
                )
            )
            row_back = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TW_VoltarPainel"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Configurar Canal",
                                    description="Selecione o canal onde os tweets serão publicados.")
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[row_sel, row_back])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay("# 𝕏 Twitter/X\n-# Painel > Twitter/X > **Canal**"),
                        disnake.ui.Separator(),
                        row_sel,
                        **accent(primary_hex),
                    ),
                    row_back,
                ])
            return

        if cid == "TW_ConfigCargo":
            row_sel = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargo necessário para postar...",
                    custom_id="TW_SelectCargo",
                    min_values=1, max_values=1,
                )
            )
            row_back = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TW_VoltarPainel"),
            )
            desc = "Selecione o cargo necessário para publicar tweets.\nSe não configurar, qualquer membro pode postar."
            if mode == "embed":
                emb = disnake.Embed(title="Cargo para Postar", description=desc)
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[row_sel, row_back])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay("# 𝕏 Twitter/X\n-# Painel > Twitter/X > **Cargo para Postar**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        row_sel,
                        **accent(primary_hex),
                    ),
                    row_back,
                ])
            return

        if cid == "TW_ConfigAdmin":
            row_sel = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargo admin (pode apagar qualquer tweet)...",
                    custom_id="TW_SelectAdmin",
                    min_values=1, max_values=1,
                )
            )
            row_back = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TW_VoltarPainel"),
            )
            desc = "Selecione o cargo que pode apagar qualquer tweet (além do próprio autor)."
            if mode == "embed":
                emb = disnake.Embed(title="Cargo Admin", description=desc)
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[row_sel, row_back])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay("# 𝕏 Twitter/X\n-# Painel > Twitter/X > **Cargo Admin**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        row_sel,
                        **accent(primary_hex),
                    ),
                    row_back,
                ])
            return

    # ── Interações nos botões dos POSTS ───────────────────────────────────────

    async def _handle_post_button(self, inter: disnake.MessageInteraction, cid: str):
        config      = helpers.carregar_config()
        primary_hex = _primary()
        mode        = _mode()

        # ── Curtir ────────────────────────────────────────────────────────────
        if cid.startswith("TW_curtir_"):
            post_id   = cid.replace("TW_curtir_", "")
            reactions = load_json(REACTIONS_JSON)
            user_id   = str(inter.author.id)
            lista     = reactions.get(post_id, [])

            if user_id in lista:
                lista.remove(user_id)
                msg_resp = "Você removeu sua curtida."
            else:
                lista.append(user_id)
                msg_resp = "❤️ Você curtiu este tweet!"

            reactions[post_id] = lista
            save_json(REACTIONS_JSON, reactions)

            await inter.response.send_message(msg_resp, ephemeral=True)
            await self._update_tweet_image(inter.message, post_id)
            return

        # ── Retweet ───────────────────────────────────────────────────────────
        if cid.startswith("TW_retweet_"):
            post_id  = cid.replace("TW_retweet_", "")
            retweets = load_json(RETWEETS_JSON)
            user_id  = str(inter.author.id)
            lista    = retweets.get(post_id, [])

            if user_id in lista:
                await inter.response.send_message(
                    "Você já retweetou este post. Não é possível desfazer por aqui.", ephemeral=True
                )
                return

            lista.append(user_id)
            retweets[post_id] = lista
            save_json(RETWEETS_JSON, retweets)

            await inter.response.defer(ephemeral=True)

            # Buscar dados do post original
            posts = load_json(POSTS_JSON)
            post  = posts.get(post_id)
            if not post:
                await inter.followup.send("Post não encontrado.", ephemeral=True)
                return

            # Atualizar imagem do original
            await self._update_tweet_image(inter.message, post_id)

            # Gerar imagem do retweet (com label "X retweetou")
            av_bytes = await _fetch_bytes(post["autor_avatar_url"])
            rt_buf = gerar_imagem_tweet(
                mensagem           = post["conteudo"],
                autor_nome         = post["autor_nome"],
                autor_handle       = post["autor_handle"],
                autor_avatar_bytes = av_bytes,
                timestamp          = post["timestamp"],
                post_id            = post_id,
                is_retweet_of      = inter.author.display_name,
            )

            # Botão link para o original
            try:
                orig_msg_url = inter.message.jump_url
            except Exception:
                orig_msg_url = None

            link_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ver tweet original",
                    emoji="🔗",
                    style=disnake.ButtonStyle.link,
                    url=orig_msg_url or "https://discord.com",
                )
            )

            # Enviar retweet no mesmo canal como webhook
            canal = inter.channel
            webhook: disnake.Webhook | None = None
            try:
                x_av = _get_x_avatar()
                webhook = await canal.create_webhook(name="𝕏", avatar=x_av)
            except disnake.HTTPException:
                pass

            f_rt = disnake.File(io.BytesIO(rt_buf.read()), filename="retweet.png")

            if webhook:
                try:
                    await webhook.send(
                        file=f_rt,
                        components=[link_row],
                        username="𝕏",
                        wait=False,
                    )
                except disnake.HTTPException:
                    pass
                finally:
                    try:
                        await webhook.delete()
                    except disnake.HTTPException:
                        pass
            else:
                rt_buf.seek(0)
                f_rt2 = disnake.File(io.BytesIO(rt_buf.read()), filename="retweet.png")
                try:
                    await canal.send(file=f_rt2, components=[link_row])
                except disnake.HTTPException:
                    pass

            await inter.followup.send("🔁 Retweetado!", ephemeral=True)
            return

        # ── Stats ─────────────────────────────────────────────────────────────
        if cid.startswith("TW_stats_"):
            post_id  = cid.replace("TW_stats_", "")
            reactions = load_json(REACTIONS_JSON)
            comments  = load_json(COMMENTS_JSON)
            retweets  = load_json(RETWEETS_JSON)
            posts     = load_json(POSTS_JSON)
            post      = posts.get(post_id, {})

            qtd_l  = len(reactions.get(post_id, []))
            qtd_rt = len(retweets.get(post_id, []))
            qtd_c  = len(comments.get(post_id, []))

            desc = (
                f"🤍 **Curtidas:** `{qtd_l}`\n"
                f"🔁 **Retweets:** `{qtd_rt}`\n"
                f"💬 **Comentários:** `{qtd_c}`\n"
                f"\n📅 **Postado em:** {post.get('timestamp', '?')}"
            )

            if mode == "embed":
                emb = disnake.Embed(title="📊 Estatísticas do Tweet", description=desc)
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.response.send_message(embed=emb, ephemeral=True)
            else:
                await inter.response.send_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# 📊 Estatísticas do Tweet\n{desc}"),
                            **accent(primary_hex),
                        )
                    ],
                    ephemeral=True,
                )
            return

        # ── Apagar ────────────────────────────────────────────────────────────
        if cid.startswith("TW_apagar_"):
            post_id = cid.replace("TW_apagar_", "")
            posts   = load_json(POSTS_JSON)
            post    = posts.get(post_id)

            admin_id  = config.get("admin_cargo_id")
            is_author = post and str(inter.author.id) == str(post.get("autor_id"))
            is_admin  = (
                inter.author.guild_permissions.manage_messages
                or (admin_id and admin_id in [str(r.id) for r in getattr(inter.author, "roles", [])])
            )

            if not is_author and not is_admin:
                await inter.response.send_message(
                    "Você não pode apagar este tweet.", ephemeral=True
                )
                return

            await inter.response.defer(ephemeral=True)
            try:
                await inter.message.delete()
            except disnake.HTTPException:
                pass

            for jp in (POSTS_JSON, REACTIONS_JSON, COMMENTS_JSON, RETWEETS_JSON):
                d = load_json(jp)
                d.pop(post_id, None)
                save_json(jp, d)

            await inter.followup.send("Tweet apagado.", ephemeral=True)
            return

    # ── Atualizar imagem do tweet ─────────────────────────────────────────────

    async def _update_tweet_image(self, msg: disnake.Message, post_id: str):
        try:
            posts = load_json(POSTS_JSON)
            post  = posts.get(post_id)
            if not post:
                return

            av_bytes = await _fetch_bytes(post["autor_avatar_url"])
            buf = gerar_imagem_tweet(
                mensagem           = post["conteudo"],
                autor_nome         = post["autor_nome"],
                autor_handle       = post["autor_handle"],
                autor_avatar_bytes = av_bytes,
                timestamp          = post["timestamp"],
                post_id            = post_id,
            )
            f = disnake.File(io.BytesIO(buf.read()), filename="tweet.png")
            await msg.edit(
                attachments=[f],
                components=[build_post_buttons(post_id)],
            )
        except Exception:
            pass

    # ── Dropdowns (selects) ───────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _tw_select_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("TW_"):
            return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "TW_SelectCanal":
            config = helpers.carregar_config()
            config["canal_id"] = inter.values[0]
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "TW_SelectCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "TW_SelectAdmin":
            config = helpers.carregar_config()
            config["admin_cargo_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return


# ─── Modais ──────────────────────────────────────────────────────────────────

class ComentarModal(disnake.ui.Modal):
    def __init__(self, post_id: str, bot: commands.Bot):
        self.post_id = post_id
        self.bot     = bot
        super().__init__(
            title="Comentar Tweet",
            custom_id=f"TW_ComentarModal_{post_id}",
            components=[
                disnake.ui.TextInput(
                    label="Seu comentário",
                    placeholder="Escreva seu comentário...",
                    custom_id="comentario",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    min_length=1,
                    max_length=500,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        conteudo = inter.text_values.get("comentario", "").strip()
        if not conteudo:
            await inter.response.send_message("Comentário vazio.", ephemeral=True)
            return

        comments = load_json(COMMENTS_JSON)
        lista    = comments.get(self.post_id, [])
        lista.append({
            "autor_id":   inter.author.id,
            "autor_nome": inter.author.display_name,
            "conteudo":   conteudo,
            "criado_em":  datetime.now().isoformat(),
        })
        comments[self.post_id] = lista
        save_json(COMMENTS_JSON, comments)

        await inter.response.send_message("💬 Comentário adicionado!", ephemeral=True)

        # Atualizar imagem
        cog: TwitterCog | None = inter.bot.get_cog("TwitterCog")
        if not cog:
            return

        config    = helpers.carregar_config()
        canal_id  = config.get("canal_id")
        posts     = load_json(POSTS_JSON)
        post      = posts.get(self.post_id)
        if not post or not canal_id:
            return

        try:
            canal = self.bot.get_channel(int(canal_id))
            if not canal:
                return
            msg = await canal.fetch_message(int(self.post_id))
            await cog._update_tweet_image(msg, self.post_id)
        except Exception:
            pass


def setup(bot: commands.Bot):
    bot.add_cog(TwitterCog(bot))