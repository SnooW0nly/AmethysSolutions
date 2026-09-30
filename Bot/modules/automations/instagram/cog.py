"""
modules/automations/instagram/cog.py

Painel de configuração do Sistema de Instagram + listeners de botões/selects/modais.
A lógica de publicação (on_message, webhook, etc.) está em:
  tasks/automations/tsk_instagram.py
"""
from __future__ import annotations

import disnake
from disnake.ext import commands
from datetime import datetime

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from . import helpers
from .helpers import (
    accent, color,
    build_post_buttons, build_post_container, build_post_embed,
    load_json, save_json,
    REACTIONS_JSON, COMMENTS_JSON, POSTS_JSON,
)


class InstagramCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Painel Components ─────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        config      = helpers.carregar_config()
        ativado     = config.get("ativado", False)
        canal_id    = config.get("canal_id")
        cargo_id    = config.get("cargo_id")
        logs_on     = config.get("logs_ativados", False)
        emojis      = config.get("emojis", {})
        primary_hex = db.get_document("custom_colors").get("primary")

        canal_txt = f"<#{canal_id}>" if canal_id else "`Não configurado`"
        cargo_txt = f"<@&{cargo_id}>" if cargo_id else "`Não configurado`"
        e_curtir  = emojis.get("curtir",      f"{emoji.heart}")
        e_ver     = emojis.get("comentarios", f"{emoji.mail2}")
        e_add     = emojis.get("comentar",    f"{emoji.edit}")
        e_del     = emojis.get("apagar",      f"{emoji.delete}")

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_on else emoji.off} **Logs:** `{'Ativado' if logs_on else 'Desativado'}`\n"
            f"{emoji.textc} **Canal:** {canal_txt}\n"
            f"{emoji.role} **Cargo necessário:** {cargo_txt}\n"
            f"**Emojis dos botões:** {e_curtir} {e_ver} {e_add} {e_del}"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Automações > **Sistema de Instagram**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Tenha um instagram dentro do servidor, com curtidas, comentários e muito mais."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", emoji=emoji.power,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="IG_ToggleAtivo",
                                      disabled=not bool(canal_id)),
                    disnake.ui.Button(label="Canal", emoji=emoji.textc,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="IG_ConfigCanal"),
                    disnake.ui.Button(label="Emojis", emoji=emoji.colors,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="IG_ConfigEmojis"),
                    disnake.ui.Button(label="Cargo", emoji=emoji.role,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="IG_ConfigCargo"),
                    disnake.ui.Button(label="Logs", emoji=emoji.power,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="IG_ToggleLogs"),
                ),
                **accent(primary_hex),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="VoltarAutomações"),
            ),
        ]

    # ── Painel Embed ──────────────────────────────────────────────────────────

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        config      = helpers.carregar_config()
        ativado     = config.get("ativado", False)
        canal_id    = config.get("canal_id")
        cargo_id    = config.get("cargo_id")
        logs_on     = config.get("logs_ativados", False)
        emojis      = config.get("emojis", {})
        primary_hex = db.get_document("custom_colors").get("primary")

        canal_txt = f"<#{canal_id}>" if canal_id else "`Não configurado`"
        cargo_txt = f"<@&{cargo_id}>" if cargo_id else "`Não configurado`"
        e_curtir  = emojis.get("curtir",      f"{emoji.heart}")
        e_ver     = emojis.get("comentarios", f"{emoji.mail2}")
        e_add     = emojis.get("comentar",    f"{emoji.edit}")
        e_del     = emojis.get("apagar",      f"{emoji.delete}")
      
        embed = disnake.Embed(
            title="Sistema de Instagram",
            description="Tenha um instagram dentro do servidor.",
        )
        if primary_hex:
            embed.color = color(primary_hex)
        embed.add_field(name="Configurações", inline=False, value=(
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_on else emoji.off} **Logs:** `{'Ativado' if logs_on else 'Desativado'}`\n"
            f"{emoji.textc} **Canal:** {canal_txt}\n"
            f"{emoji.role} **Cargo necessário:** {cargo_txt}\n"
            f"**Emojis:** {e_curtir} {e_ver} {e_add} {e_del}"
        ))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="IG_ToggleAtivo",
                                  disabled=not bool(canal_id)),
                disnake.ui.Button(label="Canal", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="IG_ConfigCanal"),
                disnake.ui.Button(label="Emojis", emoji=emoji.colors,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="IG_ConfigEmojis"),
                disnake.ui.Button(label="Cargo", emoji=emoji.role,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="IG_ConfigCargo"),
                disnake.ui.Button(label="Logs", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="IG_ToggleLogs"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="VoltarAutomações"),
            ),
        ]
        return embed, components

    # ─────────────────────────────────────────────────────────────────────────
    # LISTENER — botões do painel de config + botões dos posts
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _ig_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("IG_"):
            return

        # Botões que abrem modal — responder ANTES do wait, senão dá InteractionResponded
        if cid.startswith("IG_EmojiEdit_"):
            chave = cid.replace("IG_EmojiEdit_", "")
            await inter.response.send_modal(EmojiModal(chave))
            return

        if cid.startswith("IG_comentar_"):
            post_id = cid.replace("IG_comentar_", "")
            await inter.response.send_modal(ComentarModal(post_id, self.bot))
            return

        # Botões dos posts — delegar para handler próprio
        if any(cid.startswith(p) for p in ("IG_curtir_", "IG_comentarios_", "IG_apagar_")):
            await self._handle_post_button(inter, cid)
            return

        # ── Botões do painel ──────────────────────────────────────────────────
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        primary_hex = db.get_document("custom_colors").get("primary")

        if cid == "IG_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "IG_ToggleLogs":
            config = helpers.carregar_config()
            config["logs_ativados"] = not config.get("logs_ativados", False)
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "IG_ConfigCanal":
            select_row = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione um canal de texto...",
                    custom_id="IG_SelectCanal",
                    min_values=1, max_values=1,
                    channel_types=[disnake.ChannelType.text],
                )
            )
            voltar_row = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="IG_VoltarPainel"),
            )
            if mode == "embed":
                embed = disnake.Embed(
                    title="Configurar Canal",
                    description="Selecione o canal onde os posts serão enviados.",
                )
                if primary_hex:
                    embed.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=embed, components=[select_row, voltar_row])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Painel > Automações > Instagram > **Configurar Canal**"
                        ),
                        disnake.ui.Separator(),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar_row,
                ])
            return

        if cid == "IG_ConfigCargo":
            select_row = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione um cargo...",
                    custom_id="IG_SelectCargo",
                    min_values=0, max_values=1,
                )
            )
            action_row = disnake.ui.ActionRow(
                disnake.ui.Button(label="Remover cargo", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id="IG_RemoverCargo"),
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="IG_VoltarPainel"),
            )
            desc = (
                "Selecione o cargo necessário para postar.\n"
                "Clique em **Remover cargo** para liberar para todos."
            )
            if mode == "embed":
                embed = disnake.Embed(title="Configurar Cargo Necessário", description=desc)
                if primary_hex:
                    embed.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=embed, components=[select_row, action_row])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Painel > Automações > Instagram > **Cargo Necessário**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **accent(primary_hex),
                    ),
                    action_row,
                ])
            return

        if cid == "IG_RemoverCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "IG_ConfigEmojis":
            await self._render_emojis_panel(inter, mode)
            return

        if cid == "IG_VoltarPainel":
            await self._render_painel(inter, mode)
            return

    # ── Helpers de renderização ───────────────────────────────────────────────

    async def _render_painel(self, inter: disnake.MessageInteraction, mode: str):
        if mode == "embed":
            embed, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(components=self.Painel())

    async def _render_emojis_panel(self, inter: disnake.MessageInteraction, mode: str):
        config      = helpers.carregar_config()
        emojis      = config.get("emojis", {})
        primary_hex = db.get_document("custom_colors").get("primary")

        e_curtir  = emojis.get("curtir",      f"{emoji.heart}")
        e_ver     = emojis.get("comentarios", f"{emoji.mail2}")
        e_add     = emojis.get("comentar",    f"{emoji.edit}")
        e_del     = emojis.get("apagar",      f"{emoji.delete}")

        desc = (
            "Clique no botão para trocar o emoji da ação correspondente.\n"
            "Os botões mostram o emoji **atual** de cada ação."
        )
        row_btns = disnake.ui.ActionRow(
            disnake.ui.Button(emoji=e_curtir, style=disnake.ButtonStyle.secondary, custom_id="IG_EmojiEdit_curtir"),
            disnake.ui.Button(emoji=e_ver,    style=disnake.ButtonStyle.secondary, custom_id="IG_EmojiEdit_comentarios"),
            disnake.ui.Button(emoji=e_add,    style=disnake.ButtonStyle.primary,   custom_id="IG_EmojiEdit_comentar"),
            disnake.ui.Button(emoji=e_del,    style=disnake.ButtonStyle.danger,    custom_id="IG_EmojiEdit_apagar"),
        )
        voltar_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id="IG_VoltarPainel"),
        )

        if mode == "embed":
            embed = disnake.Embed(title="Configurar Emojis", description=desc)
            if primary_hex:
                embed.color = color(primary_hex)
            await inter.edit_original_message(content=None, embed=embed, components=[row_btns, voltar_row])
        else:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        "-# Painel > Automações > Instagram > **Emojis**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(desc),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    row_btns,
                    **accent(primary_hex),
                ),
                voltar_row,
            ])

    # ── Interações nos botões dos POSTS ───────────────────────────────────────

    async def _handle_post_button(self, inter: disnake.MessageInteraction, cid: str):
        config      = helpers.carregar_config()
        emojis      = config.get("emojis", {})
        primary_hex = db.get_document("custom_colors").get("primary")
        mode        = db.get_document("custom_mode").get("mode")

        if cid.startswith("IG_curtir_"):
            post_id   = cid.replace("IG_curtir_", "")
            reactions = load_json(REACTIONS_JSON)
            user_id   = str(inter.author.id)
            lista     = reactions.get(post_id, [])

            if user_id in lista:
                lista.remove(user_id)
                resp = "Você removeu sua curtida."
            else:
                lista.append(user_id)
                resp = "Você curtiu esta publicação!"

            reactions[post_id] = lista
            save_json(REACTIONS_JSON, reactions)

            await inter.response.send_message(resp, ephemeral=True)
            await self._update_post_message(inter.message, post_id, emojis, mode, primary_hex)
            return

        if cid.startswith("IG_comentarios_"):
            post_id  = cid.replace("IG_comentarios_", "")
            comments = load_json(COMMENTS_JSON)
            lista    = comments.get(post_id, [])

            if not lista:
                await inter.response.send_message("Nenhum comentário ainda.", ephemeral=True)
                return

            texto = "\n".join(
                f"**{c.get('autor_nome', '?')}:** {c.get('conteudo', '')}"
                for c in lista[-10:]
            )
            if len(lista) > 10:
                texto = f"*... e mais {len(lista) - 10} comentário(s) anteriores*\n" + texto

            if mode == "embed":
                embed = disnake.Embed(title=f"Comentários ({len(lista)})", description=texto)
                if primary_hex:
                    embed.color = color(primary_hex)
                await inter.response.send_message(embed=embed, ephemeral=True)
            else:
                await inter.response.send_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# Comentários ({len(lista)})\n{texto}"),
                            **accent(primary_hex),
                        )
                    ],
                    ephemeral=True,
                )
            return

        if cid.startswith("IG_apagar_"):
            post_id = cid.replace("IG_apagar_", "")
            posts   = load_json(POSTS_JSON)
            post    = posts.get(post_id)

            is_author = post and str(inter.author.id) == str(post.get("autor_id"))
            is_admin  = inter.author.guild_permissions.manage_messages

            if not is_author and not is_admin:
                await inter.response.send_message("Você não pode apagar este post.", ephemeral=True)
                return

            await inter.response.defer(ephemeral=True)
            try:
                await inter.message.delete()
            except disnake.HTTPException:
                pass

            for json_path in (POSTS_JSON, REACTIONS_JSON, COMMENTS_JSON):
                data = load_json(json_path)
                data.pop(post_id, None)
                save_json(json_path, data)

            await inter.followup.send("Post apagado com sucesso.", ephemeral=True)
            return

    async def _update_post_message(
        self,
        msg: disnake.Message,
        post_id: str,
        emojis: dict,
        mode: str,
        primary_hex: str | None,
    ):
        """Re-renderiza o post após interação (curtida/comentário)."""
        try:
            post = load_json(POSTS_JSON).get(post_id)
            if not post:
                return

            autor_mencao = f"<@{post['autor_id']}>"
            imagem_url   = post.get("imagem_url", "")
            conteudo     = post.get("conteudo")
            autor_nome   = post.get("autor_nome", "")
            autor_avatar = post.get("autor_avatar", "")

            if mode == "embed":
                embed, comps = build_post_embed(
                    autor_nome, autor_avatar, autor_mencao,
                    imagem_url, conteudo, post_id, emojis, primary_hex,
                )
                await msg.edit(embed=embed, components=comps)
            else:
                comps = build_post_container(
                    autor_mencao, imagem_url, conteudo,
                    post_id, emojis, primary_hex,
                )
                await msg.edit(components=comps)
        except Exception:
            pass

    # ── Dropdowns (ChannelSelect / RoleSelect) ────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _ig_select_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("IG_"):
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "IG_SelectCanal":
            config = helpers.carregar_config()
            config["canal_id"] = inter.values[0]
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "IG_SelectCargo":
            if not inter.values:
                return
            config = helpers.carregar_config()
            config["cargo_id"] = inter.values[0]
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return


# ─── Modais ──────────────────────────────────────────────────────────────────

class EmojiModal(disnake.ui.Modal):
    LABELS = {
        "curtir":      "Emoji do botão Curtir",
        "comentarios": "Emoji do botão Ver Comentários",
        "comentar":    "Emoji do botão Comentar",
        "apagar":      "Emoji do botão Apagar",
    }

    def __init__(self, chave: str):
        self.chave = chave
        super().__init__(
            title=self.LABELS.get(chave, "Emoji"),
            custom_id=f"IG_EmojiModal_{chave}",
            components=[
                disnake.ui.TextInput(
                    label="Novo emoji",
                    placeholder="Cole o emoji aqui (ex: 🔥 ou <:custom:123>)",
                    custom_id="novo_emoji",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    min_length=1,
                    max_length=64,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        novo_emoji = inter.text_values.get("novo_emoji", "").strip()
        mode = db.get_document("custom_mode").get("mode")

        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        config = helpers.carregar_config()
        config["emojis"][self.chave] = novo_emoji
        helpers.salvar_config(config)

        # Re-renderizar tela de emojis com valores atualizados
        cog: InstagramCog | None = inter.bot.get_cog("InstagramCog")
        if cog:
            await cog._render_emojis_panel(inter, mode)


class ComentarModal(disnake.ui.Modal):
    def __init__(self, post_id: str, bot: commands.Bot):
        self.post_id = post_id
        self.bot     = bot
        super().__init__(
            title="Comentar",
            custom_id=f"IG_ComentarModal_{post_id}",
            components=[
                disnake.ui.TextInput(
                    label="Seu comentário",
                    placeholder="Escreva seu comentário aqui...",
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

        await inter.response.send_message("Comentário adicionado!", ephemeral=True)

        # Atualizar contagem nos botões do post
        config      = helpers.carregar_config()
        emojis      = config.get("emojis", {})
        primary_hex = db.get_document("custom_colors").get("primary")
        mode        = db.get_document("custom_mode").get("mode")
        canal_id    = config.get("canal_id")

        try:
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    msg  = await canal.fetch_message(int(self.post_id))
                    post = load_json(POSTS_JSON).get(self.post_id)
                    if post and msg:
                        autor_mencao = f"<@{post['autor_id']}>"
                        imagem_url   = post.get("imagem_url", "")
                        texto_post   = post.get("conteudo")
                        autor_nome   = post.get("autor_nome", "")
                        autor_avatar = post.get("autor_avatar", "")
                        if mode == "embed":
                            embed, comps = build_post_embed(
                                autor_nome, autor_avatar, autor_mencao,
                                imagem_url, texto_post, self.post_id, emojis, primary_hex,
                            )
                            await msg.edit(embed=embed, components=comps)
                        else:
                            comps = build_post_container(
                                autor_mencao, imagem_url, texto_post,
                                self.post_id, emojis, primary_hex,
                            )
                            await msg.edit(components=comps)
        except Exception:
            pass


def setup(bot: commands.Bot):
    bot.add_cog(InstagramCog(bot))