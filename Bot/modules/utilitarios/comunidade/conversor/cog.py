"""
modules/utilitarios/comunidade/conversor/cog.py

Sistema de Conversor de Mídia.
- Admin configura canal e categoria via painel
- Painel público tem botão "Converter"
- Ao clicar, abre tópico privado no canal configurado
- Todo o processo de upload → escolha → conversão → entrega ocorre no tópico
- Conversões rodam em ProcessPoolExecutor (não bloqueiam o bot)
"""
from __future__ import annotations

import asyncio
import io
import traceback
from datetime import datetime, timezone

import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from functions.emoji import emoji

from .helpers import (
    CONVERSOES,
    MAX_INPUT_BYTES,
    accent, color, carregar_config, salvar_config,
    conversoes_disponiveis, detectar_conversao,
    converter_async, formatar_tamanho,
)


# ─── Semáforo global: máx 2 conversões simultâneas ────────────────────────────
_SEM = asyncio.Semaphore(2)


class ConversorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ══════════════════════════════════════════════════════════════════════════
    #  PAINEL DE ADMIN
    # ══════════════════════════════════════════════════════════════════════════

    def Painel(self) -> list:
        cfg = carregar_config()
        ativo = cfg.get("ativado", False)
        canal_id = cfg.get("canal_painel")
        cat_id = cfg.get("categoria_topicos")
        max_mb = cfg.get("max_mb", 50)
        ativas = cfg.get("conversoes_ativas", list(CONVERSOES.keys()))

        canal_txt = f"<#{canal_id}>" if canal_id else "`Não configurado`"
        cat_txt = f"<#{cat_id}>" if cat_id else "`Não configurada`"
        status_txt = f"{emoji.correct}Ativado" if ativo else f"{emoji.wrong} Desativado"

        tipos_txt = "\n".join(
            f"{f'{emoji.correct}' if k in ativas else f'{emoji.wrong}'} {v['label']}"
            for k, v in CONVERSOES.items()
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"#  {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Comunidade > **Conversor**\n\n"
                    f"**Status:** {status_txt}\n"
                    f"**Canal do painel:** {canal_txt}\n"
                    f"**Categoria dos tópicos:** {cat_txt}\n"
                    f"**Limite de arquivo:** `{max_mb} MB`\n\n"
                    f"**Conversões disponíveis:**\n> -# {tipos_txt}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not ativo else "Desativar",
                        style=disnake.ButtonStyle.green if not ativo else disnake.ButtonStyle.red,
                        custom_id="Conversor_ToggleAtivo",
                        emoji=emoji.power
                    ),
                    disnake.ui.Button(
                        label="Configurar Canal",
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Conversor_ConfigCanal",
                        emoji=emoji.textc,
                    ),
                    disnake.ui.Button(
                        label="Configurar Categoria",
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Conversor_ConfigCategoria",
                        emoji=emoji.textc,
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Enviar Painel",
                        style=disnake.ButtonStyle.green,
                        custom_id="Conversor_EnviarPainel",
                        emoji=emoji.arrow,
                    ),
                    disnake.ui.Button(
                        label="Gerenciar Tipos",
                        style=disnake.ButtonStyle.grey,
                        custom_id="Conversor_GerenciarTipos",
                        emoji=emoji.commands,
                    ),
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        custom_id="Conversor_VoltarComunidade",
                        emoji=emoji.back,
                    ),
                ),
                **accent(),
            )
        ]

    # ══════════════════════════════════════════════════════════════════════════
    #  BOTÕES DO PAINEL ADMIN
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def on_conversor_button(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Toggle ativo ──────────────────────────────────────────────────────
        if cid == "Conversor_ToggleAtivo":
            cfg = carregar_config()
            cfg["ativado"] = not cfg.get("ativado", False)
            salvar_config(cfg)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.Painel())
            return

        # ── Config canal ──────────────────────────────────────────────────────
        if cid == "Conversor_ConfigCanal":
            await inter.response.send_modal(
                disnake.ui.Modal(
                    title="Canal do Painel",
                    custom_id="Conversor_ModalCanal",
                    components=[
                        disnake.ui.TextInput(
                            label="ID do canal",
                            custom_id="canal_id",
                            placeholder="Ex: 1234567890123456789",
                            min_length=17,
                            max_length=20,
                        )
                    ],
                )
            )
            return

        # ── Config categoria ──────────────────────────────────────────────────
        if cid == "Conversor_ConfigCategoria":
            await inter.response.send_modal(
                disnake.ui.Modal(
                    title="Categoria dos Tópicos",
                    custom_id="Conversor_ModalCategoria",
                    components=[
                        disnake.ui.TextInput(
                            label="ID da categoria",
                            custom_id="cat_id",
                            placeholder="Ex: 1234567890123456789",
                            min_length=17,
                            max_length=20,
                        )
                    ],
                )
            )
            return

        # ── Enviar painel ─────────────────────────────────────────────────────
        if cid == "Conversor_EnviarPainel":
            await inter.response.defer(ephemeral=True)
            cfg = carregar_config()
            canal_id = cfg.get("canal_painel")
            if not canal_id:
                await inter.followup.send(f"{emoji.wrong} Configure o canal primeiro.", ephemeral=True)
                return
            canal = inter.guild.get_channel(int(canal_id))
            if not canal:
                await inter.followup.send(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
                return
            from .enviar_painel import enviar_painel_conversor
            msg = await enviar_painel_conversor(canal, inter.guild, cfg)
            cfg["mensagem_painel_id"] = str(msg.id)
            salvar_config(cfg)
            await inter.followup.send(f"{emoji.correct} Painel enviado em {canal.mention}!", ephemeral=True)
            return

        # ── Gerenciar tipos ───────────────────────────────────────────────────
        if cid == "Conversor_GerenciarTipos":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self._painel_tipos())
            return

        # ── Toggle individual de tipo ─────────────────────────────────────────
        if cid.startswith("Conversor_Toggle_"):
            tipo = cid.removeprefix("Conversor_Toggle_")
            cfg = carregar_config()
            ativas = set(cfg.get("conversoes_ativas", list(CONVERSOES.keys())))
            if tipo in ativas:
                ativas.discard(tipo)
            else:
                ativas.add(tipo)
            cfg["conversoes_ativas"] = list(ativas)
            salvar_config(cfg)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self._painel_tipos())
            return

        # ── Voltar da tela de tipos ───────────────────────────────────────────
        if cid == "Conversor_VoltarAdmin":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.Painel())
            return

        # ── Voltar pra Comunidade ─────────────────────────────────────────────
        if cid == "Conversor_VoltarComunidade":
            cog = self.bot.get_cog("ComunidadeCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo não encontrado.", ephemeral=True)
                return
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=cog.community_components())
            return

        # ── Iniciar conversor (painel público) ────────────────────────────────
        if cid == "Conversor_Iniciar":
            await self._iniciar_topico(inter)
            return

        # ── Fechar tópico ─────────────────────────────────────────────────────
        if cid == "Conversor_FecharTopico":
            await inter.response.defer(ephemeral=True)
            canal = inter.channel
            if isinstance(canal, (disnake.Thread, disnake.ForumChannel)):
                try:
                    await canal.delete()
                except Exception:
                    pass
            return

        # ── Selecionar tipo de conversão (dentro do tópico) ───────────────────
        if cid.startswith("Conversor_Fazer_"):
            tipo = cid.removeprefix("Conversor_Fazer_")
            await self._solicitar_arquivo(inter, tipo)
            return

        # ── Nova conversão no mesmo tópico ────────────────────────────────────
        if cid == "Conversor_NovaConversao":
            await inter.response.defer(with_message=False)
            await self._mostrar_menu_tipos(inter.channel, inter)
            return

    def _painel_tipos(self) -> list:
        cfg = carregar_config()
        ativas = set(cfg.get("conversoes_ativas", list(CONVERSOES.keys())))
        rows = []
        for k, v in CONVERSOES.items():
            ativo = k in ativas
            rows.append(
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label=f"{v['label']}",
                        style=disnake.ButtonStyle.green if ativo else disnake.ButtonStyle.red,
                        custom_id=f"Conversor_Toggle_{k}",
                    )
                )
            )
        rows.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    custom_id="Conversor_VoltarAdmin",
                    emoji=emoji.back,
                )
            )
        )
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    "# Gerenciar Tipos de Conversão\n"
                    "Clique para ativar/desativar cada tipo."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **accent(),
            )
        ]

    # ══════════════════════════════════════════════════════════════════════════
    #  MODAIS
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_modal_submit")
    async def on_conversor_modal(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id

        if cid == "Conversor_ModalCanal":
            canal_id = inter.text_values.get("canal_id", "").strip()
            canal = inter.guild.get_channel(int(canal_id)) if canal_id.isdigit() else None
            if not canal:
                await inter.response.send_message(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
                return
            cfg = carregar_config()
            cfg["canal_painel"] = canal_id
            salvar_config(cfg)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.Painel())
            return

        if cid == "Conversor_ModalCategoria":
            cat_id = inter.text_values.get("cat_id", "").strip()
            cat = inter.guild.get_channel(int(cat_id)) if cat_id.isdigit() else None
            if not cat:
                await inter.response.send_message(f"{emoji.wrong} Categoria não encontrada.", ephemeral=True)
                return
            cfg = carregar_config()
            cfg["categoria_topicos"] = cat_id
            salvar_config(cfg)
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.Painel())
            return

    # ══════════════════════════════════════════════════════════════════════════
    #  FLUXO DO USUÁRIO — TÓPICO PRIVADO
    # ══════════════════════════════════════════════════════════════════════════

    async def _iniciar_topico(self, inter: disnake.MessageInteraction):
        """Cria tópico privado para o usuário e exibe menu de tipos."""
        await inter.response.defer(ephemeral=True)
        cfg = carregar_config()

        if not cfg.get("ativado", False):
            await inter.followup.send(f"{emoji.wrong} O conversor está desativado.", ephemeral=True)
            return

        canal_id = cfg.get("canal_painel")
        if not canal_id:
            await inter.followup.send(f"{emoji.wrong} Conversor não configurado pelo admin.", ephemeral=True)
            return

        canal_base = inter.guild.get_channel(int(canal_id))
        if not canal_base:
            await inter.followup.send(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
            return

        # Verifica se usuário já tem tópico aberto (busca por nome)
        nome_topico = f"🔄 {inter.author.display_name}"
        if hasattr(canal_base, "threads"):
            for t in canal_base.threads:
                if t.name == nome_topico and not t.archived:
                    await inter.followup.send(
                        f"⚠️ Você já tem um tópico aberto: {t.mention}",
                        ephemeral=True,
                    )
                    return

        # Cria tópico privado
        try:
            topico: disnake.Thread = await canal_base.create_thread(
                name=nome_topico,
                type=disnake.ChannelType.private_thread,
                invitable=False,
                reason=f"Conversor: solicitado por {inter.author}",
            )
            await topico.add_user(inter.author)
        except disnake.Forbidden:
            await inter.followup.send(
                f"{emoji.wrong} Sem permissão para criar tópicos privados nesse canal.",
                ephemeral=True,
            )
            return
        except Exception as e:
            await inter.followup.send(f"{emoji.wrong} Erro ao criar tópico: `{e}`", ephemeral=True)
            return

        await inter.followup.send(
            f"{emoji.correct} Tópico criado: {topico.mention}",
            ephemeral=True,
        )
        await self._mostrar_menu_tipos(topico, inter)

    async def _mostrar_menu_tipos(
        self,
        topico: disnake.Thread,
        inter: disnake.MessageInteraction | None = None,
    ):
        """Envia menu de seleção de tipo de conversão no tópico."""
        cfg = carregar_config()
        disponiveis = conversoes_disponiveis(cfg)

        if not disponiveis:
            await topico.send(f"{emoji.wrong} Nenhum tipo de conversão está habilitado no momento.")
            return

        botoes = [
            disnake.ui.Button(
                label=f"{v['label']}",
                style=disnake.ButtonStyle.blurple,
                custom_id=f"Conversor_Fazer_{k}",
            )
            for k, v in disponiveis.items()
        ]

        # Divide botões em ActionRows de 3
        rows = []
        for i in range(0, len(botoes), 3):
            rows.append(disnake.ui.ActionRow(*botoes[i:i+3]))

        rows.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Fechar tópico",
                    style=disnake.ButtonStyle.red,
                    custom_id="Conversor_FecharTopico",
                    emoji=emoji.delete,
                )
            )
        )

        await topico.send(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.reload} Conversor de Mídia\n"
                        f"Olá, {topico.owner.mention if topico.owner else 'usuário'}!\n"
                        f"Escolha o tipo de conversão que deseja realizar:"
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    *rows,
                    **accent(),
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )

    async def _solicitar_arquivo(self, inter: disnake.MessageInteraction, tipo: str):
        """Pede ao usuário para enviar o arquivo no tópico."""
        info = CONVERSOES.get(tipo)
        if not info:
            await inter.response.send_message(f"{emoji.wrong} Tipo inválido.", ephemeral=True)
            return

        cfg = carregar_config()
        max_mb = cfg.get("max_mb", 50)
        exts = ", ".join(sorted(info["extensoes_entrada"]))

        await inter.response.defer(with_message=False)
        await inter.channel.send(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"## {info['label']}\n"
                        f"{info['desc']}\n\n"
                        f"**Envie o arquivo agora neste tópico.**\n"
                        f"-# Formatos aceitos: `{exts}`\n"
                        f"-# Tamanho máximo: `{max_mb} MB`\n\n"
                        f"Aguardando seu arquivo por **2 minutos**…"
                    ),
                    **accent(),
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )

        # Aguarda mensagem com anexo no tópico
        def check(msg: disnake.Message):
            return (
                msg.channel.id == inter.channel.id
                and msg.author.id == inter.author.id
                and len(msg.attachments) > 0
            )

        try:
            msg: disnake.Message = await self.bot.wait_for(
                "message", check=check, timeout=120.0
            )
        except asyncio.TimeoutError:
            await inter.channel.send(
                f"{emoji.clock} Tempo esgotado. Use o botão abaixo para tentar novamente.",
                components=[disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Nova conversão",
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Conversor_NovaConversao",
                    )
                )],
            )
            return

        anexo = msg.attachments[0]
        await self._processar_conversao(inter.channel, inter.author, anexo, tipo, cfg)

    async def _processar_conversao(
        self,
        topico: disnake.Thread,
        autor: disnake.Member,
        anexo: disnake.Attachment,
        tipo: str,
        cfg: dict,
    ):
        """Baixa o arquivo, converte e devolve no tópico."""
        max_bytes = cfg.get("max_mb", 50) * 1024 * 1024
        info = CONVERSOES[tipo]

        # Validação de extensão
        ext_entrada = "." + anexo.filename.rsplit(".", 1)[-1].lower() if "." in anexo.filename else ""
        if ext_entrada not in info["extensoes_entrada"]:
            await topico.send(
                f"{emoji.wrong} Arquivo `{anexo.filename}` não é compatível com **{info['label']}**.\n"
                f"-# Formatos aceitos: `{', '.join(sorted(info['extensoes_entrada']))}`"
            )
            return

        # Validação de tamanho
        if anexo.size > max_bytes:
            await topico.send(
                f"{emoji.wrong} Arquivo muito grande: `{formatar_tamanho(anexo.size)}`.\n"
                f"-# Máximo permitido: `{cfg.get('max_mb', 50)} MB`"
            )
            return

        status_msg = await topico.send(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"⏳ **Convertendo…**\n"
                        f"-# Arquivo: `{anexo.filename}` ({formatar_tamanho(anexo.size)})\n"
                        f"-# Tipo: {info['label']}\n\n"
                        f"Isso pode levar alguns segundos. Não feche o tópico."
                    ),
                    **accent(),
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )

        async with _SEM:  # Limita concorrência global
            try:
                # Download em memória
                input_bytes = await anexo.read()

                # Conversão em processo separado (não trava o bot)
                output_bytes = await converter_async(tipo, input_bytes, anexo.filename)

                # Deleta mensagem de status
                try:
                    await status_msg.delete()
                except Exception:
                    pass

                nome_saida = anexo.filename.rsplit(".", 1)[0] + info["extensao_saida"]
                tamanho_saida = formatar_tamanho(len(output_bytes))

                # Envia resultado
                await topico.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{emoji.correct} **Conversão concluída!**\n"
                                f"-# {info['label']} — `{nome_saida}` ({tamanho_saida})"
                            ),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            disnake.ui.ActionRow(
                                disnake.ui.Button(
                                    label="Nova conversão",
                                    style=disnake.ButtonStyle.blurple,
                                    emoji=emoji.reload,
                                    custom_id="Conversor_NovaConversao",
                                ),
                                disnake.ui.Button(
                                    label="Fechar tópico",
                                    style=disnake.ButtonStyle.red,
                                    custom_id="Conversor_FecharTopico",
                                    emoji=emoji.delete,
                                ),
                            ),
                            **accent(),
                        )
                    ],
                    file=disnake.File(
                        io.BytesIO(output_bytes),
                        filename=nome_saida,
                    ),
                    flags=disnake.MessageFlags(is_components_v2=True),
                )

                # Log opcional
                log_id = cfg.get("log_canal")
                if log_id:
                    log_ch = topico.guild.get_channel(int(log_id))
                    if log_ch:
                        try:
                            await log_ch.send(
                                embed=disnake.Embed(
                                    title=f"{emoji.reload} Conversão realizada",
                                    color=color(),
                                    description=(
                                        f"**Usuário:** {autor.mention} (`{autor.id}`)\n"
                                        f"**Tipo:** {info['label']}\n"
                                        f"**Entrada:** `{anexo.filename}` ({formatar_tamanho(anexo.size)})\n"
                                        f"**Saída:** `{nome_saida}` ({tamanho_saida})"
                                    ),
                                ).set_footer(
                                    text=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                                )
                            )
                        except Exception:
                            pass

            except Exception as e:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                await topico.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{emoji.wrong} **Erro na conversão**\n"
                                f"-# `{type(e).__name__}: {e}`\n\n"
                                f"Verifique se o arquivo não está corrompido e tente novamente."
                            ),
                            disnake.ui.ActionRow(
                                disnake.ui.Button(
                                    label="Tentar novamente",
                                    style=disnake.ButtonStyle.blurple,
                                    custom_id="Conversor_NovaConversao",
                                ),
                                disnake.ui.Button(
                                    label="Fechar tópico",
                                    style=disnake.ButtonStyle.red,
                                    custom_id="Conversor_FecharTopico",
                                    emoji=emoji.delete,
                                ),
                            ),
                            **accent(),
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                )


def setup(bot: commands.Bot):
    bot.add_cog(ConversorCog(bot))