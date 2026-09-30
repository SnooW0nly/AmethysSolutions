"""
modules/utilitarios/comunidade/reputacao/cog.py

Sistema de Reputação por Usuário — Amethys Bot
- Painel de config completo
- Pesquisa de membro + avaliação 1-10 (1 voto por usuário)
- Ranking automático com cargos por nota
- Task de atualização periódica do ranking e painel de pesquisa
- Personalização de mensagens (igual Anunciar/Registro/Verificação)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from functions.emoji import emoji
from commands.admin.anunciar.builder import Builder

from . import helpers
from .helpers import (
    carregar_config, salvar_config,
    carregar_avaliacoes, registrar_avaliacao, obter_perfil,
    gerar_ranking, barra_nota, estrelas_nota, nota_cor,
    accent, color, _mode, _primary_hex,
    BUTTON_STYLE_MAP,
)
from .enviar_painel import enviar_painel_pesquisa, enviar_painel_ranking


# ══════════════════════════════════════════════════════════════════════════════
# MODAIS
# ══════════════════════════════════════════════════════════════════════════════

class BuscarMembroModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Buscar Membro",
            custom_id="Reputacao_BuscarModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome ou ID do membro",
                    custom_id="busca",
                    style=disnake.TextInputStyle.short,
                    placeholder="Ex: João#0001 ou 123456789",
                    required=True,
                    max_length=100,
                ),
            ],
        )


class NotaMinimaCargosModal(disnake.ui.Modal):
    def __init__(self, cargo_id: str = "", nota: str = ""):
        super().__init__(
            title="Cargo por Nota Mínima",
            custom_id="Reputacao_NotaMinimaCargosModal",
            components=[
                disnake.ui.Label(
                    text="Cargo a conceder",
                    component=disnake.ui.RoleSelect(
                        placeholder="Selecione o cargo...",
                        custom_id="cargo",
                        min_values=1,
                        max_values=1,
                    ),
                    description="Cargo dado a quem atingir a nota mínima.",
                ),
                disnake.ui.TextInput(
                    label="Nota mínima (1.0 a 10.0)",
                    custom_id="nota_minima",
                    style=disnake.TextInputStyle.short,
                    placeholder="Ex: 8.5",
                    required=True,
                    max_length=4,
                    value=nota,
                ),
            ],
        )


class IntervaloModal(disnake.ui.Modal):
    def __init__(self, atual: int = 60):
        super().__init__(
            title="Intervalo de Atualização do Ranking",
            custom_id="Reputacao_IntervaloModal",
            components=[
                disnake.ui.TextInput(
                    label="Intervalo (minutos)",
                    custom_id="intervalo",
                    style=disnake.TextInputStyle.short,
                    placeholder="Ex: 60 (mínimo: 5)",
                    required=True,
                    max_length=4,
                    value=str(atual),
                ),
            ],
        )


# ══════════════════════════════════════════════════════════════════════════════
# BUILDERS DE PAINEL
# ══════════════════════════════════════════════════════════════════════════════

def _build_config_painel(cfg: dict) -> list:
    """Painel principal de configuração do sistema de reputação."""
    ativado = cfg.get("ativado", False)
    canal_pesquisa_id = cfg.get("canal_pesquisa")
    canal_ranking_id = cfg.get("canal_ranking")
    intervalo = cfg.get("intervalo_ranking", 60)
    auto_avaliacao = cfg.get("permitir_auto_avaliacao", False)
    nota_anonima = cfg.get("nota_anonima", False)

    canal_pesquisa_txt = f"<#{canal_pesquisa_id}>" if canal_pesquisa_id else "`Não configurado`"
    canal_ranking_txt = f"<#{canal_ranking_id}>" if canal_ranking_id else "`Não configurado`"

    resumo = (
        f"{emoji.on if ativado else emoji.off} **Status:** {'`Ativado`' if ativado else '`Desativado`'}\n"
        f"{emoji.textc} **Canal de Pesquisa:** {canal_pesquisa_txt}\n"
        f"{emoji.textc} **Canal de Ranking:** {canal_ranking_txt}\n"
        f"{emoji.time} **Intervalo:** `{intervalo} min`\n"
        f"{emoji.on if auto_avaliacao else emoji.off} **Auto-avaliação:** {'`Permitida`' if auto_avaliacao else '`Bloqueada`'}\n"
        f"{emoji.on if nota_anonima else emoji.off} **Avaliação anônima:** {'`Sim`' if nota_anonima else '`Não`'}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Comunidade > **Reputação**\n"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(resumo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            # Linha 1 — Toggle + Canais
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    #label=f"{'Desativar' if ativado else 'Ativar'} Sistema",
                    style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.gray,
                    emoji=emoji.power,
                    custom_id="Reputacao_ToggleAtivado",
                ),
                disnake.ui.Button(
                    label="Canal de Pesquisa",
                    style=disnake.ButtonStyle.gray,
                    emoji=emoji.textc,
                    custom_id="Reputacao_SetCanalPesquisa",
                ),
                disnake.ui.Button(
                    label="Canal de Ranking",
                    style=disnake.ButtonStyle.gray,
                    emoji=emoji.textc,
                    custom_id="Reputacao_SetCanalRanking",
                ),
            ),
            # Linha 2 — Cargos + Personalizar
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Cargos",
                    style=disnake.ButtonStyle.gray,
                    emoji=emoji.role,
                    custom_id="Reputacao_PainelCargos",
                ),
                disnake.ui.Button(
                    label="Personalizar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Reputacao_PainelPersonalizar",
                ),
            ),
            **accent(),
        ),
        # Fora do container — opções soltas + voltar
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.gray,
                emoji=emoji.back,
                custom_id="Reputacao_VoltarComunidade",
            ),
            disnake.ui.Button(
                label=f"Intervalo: {intervalo}min",
                style=disnake.ButtonStyle.gray,
                emoji=emoji.time,
                custom_id="Reputacao_SetIntervalo",
            ),
            disnake.ui.Button(
                label=f"Auto-avaliação",
                style=disnake.ButtonStyle.green if auto_avaliacao else disnake.ButtonStyle.gray,
                emoji=emoji.power,
                custom_id="Reputacao_ToggleAutoAvaliacao",
            ),
            disnake.ui.Button(
                label=f"Anônimo",
                style=disnake.ButtonStyle.green if nota_anonima else disnake.ButtonStyle.gray,
                emoji=emoji.power,
                custom_id="Reputacao_ToggleAnonimo",
            ),
        ),
    ]


def _build_cargos_nota_painel(cfg: dict) -> list:
    """Sub-painel unificado de cargos — Top 1 e por nota mínima."""
    nota_minima_cargos = cfg.get("nota_minima_cargo", {})
    cargo_top1_id = cfg.get("cargo_top1")

    cargo_top1_txt = f"<@&{cargo_top1_id}>" if cargo_top1_id else "`Não configurado`"

    if nota_minima_cargos:
        linhas = [f"{emoji.role} <@&{cid}> → nota ≥ `{n}`" for cid, n in nota_minima_cargos.items()]
        lista_txt = "\n".join(linhas)
    else:
        lista_txt = "`Nenhum cargo configurado ainda.`"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Reputação > **Cargos**\n"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.role} **Cargo Top 1:** {cargo_top1_txt}\n\n"
                f"**Cargos por Nota Mínima:**\n{lista_txt}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Cargo Top 1",
                    style=disnake.ButtonStyle.gray,
                    emoji=emoji.role,
                    custom_id="Reputacao_SetCargoTop1",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Adicionar Cargo por Nota",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.plus,
                    custom_id="Reputacao_AdicionarCargoNota",
                ),
                disnake.ui.Button(
                    label="Remover",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="Reputacao_RemoverCargoNota",
                    disabled=not nota_minima_cargos,
                ),
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.gray,
                emoji=emoji.back,
                custom_id="Reputacao_VoltarConfig",
            ),
        ),
    ]


def _build_personalizar_menu(cfg: dict) -> list:
    """Painel intermediário — escolher o que personalizar."""
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Reputação > **Personalizar**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("Escolha o painel que deseja personalizar."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Painel de Busca",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.search,
                    custom_id="Reputacao_PersonalizarPesquisa",
                ),
                disnake.ui.Button(
                    label="Ranking",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Reputacao_PersonalizarRanking",
                ),
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.gray,
                emoji=emoji.back,
                custom_id="Reputacao_VoltarConfig",
            ),
        ),
    ]


def _build_personalizar_painel(tipo: str, cfg: dict) -> list:
    """Editor de mensagem para painel de busca ou ranking."""
    key_msg = "mensagem_pesquisa" if tipo == "pesquisa" else "mensagem_ranking"
    editor = cfg.get(key_msg, {})
    has_message = bool(editor.get("content"))
    embed_data = editor.get("embed", {})
    has_embed = any(embed_data.get(k) for k in ("title", "description", "footer"))
    has_image = bool(editor.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
    has_container = bool(editor.get("container"))
    other_disabled = has_container

    label_tipo = "Painel de Busca" if tipo == "pesquisa" else "Ranking"
    prefix_custom_id = f"Reputacao_Msg{'Pesquisa' if tipo == 'pesquisa' else 'Ranking'}"
    enviar_id = "Reputacao_EnviarPainelPesquisa" if tipo == "pesquisa" else "Reputacao_EnviarRanking"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Reputação > Personalizar > **{label_tipo}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(f"Personalize a mensagem enviada no canal de {label_tipo.lower()}."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"{prefix_custom_id}_ApagarContent",
                    disabled=not has_message or other_disabled,
                ),
                disnake.ui.Button(
                    label="Definir Mensagem", style=disnake.ButtonStyle.gray,
                    emoji=emoji.message, custom_id=f"{prefix_custom_id}_DefinirMensagem",
                    disabled=other_disabled,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"{prefix_custom_id}_ApagarEmbed",
                    disabled=not has_embed or other_disabled,
                ),
                disnake.ui.Button(
                    label="Definir Embed", style=disnake.ButtonStyle.gray,
                    emoji=emoji.embed, custom_id=f"{prefix_custom_id}_DefinirEmbed",
                    disabled=other_disabled,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"{prefix_custom_id}_ApagarImagem",
                    disabled=not has_image or other_disabled,
                ),
                disnake.ui.Button(
                    label="Definir Imagem", style=disnake.ButtonStyle.gray,
                    emoji=emoji.image, custom_id=f"{prefix_custom_id}_DefinirImagem",
                    disabled=other_disabled,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Importar do Anunciar", style=disnake.ButtonStyle.blurple,
                    emoji=emoji.commands, custom_id=f"{prefix_custom_id}_Importar",
                ),
                disnake.ui.Button(
                    label="Visualizar", style=disnake.ButtonStyle.gray,
                    emoji=emoji.search, custom_id=f"{prefix_custom_id}_Preview",
                    disabled=not (has_message or has_embed or has_container),
                ),
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=f"Enviar {label_tipo}",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.arrow,
                    custom_id=enviar_id,
                ),
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.gray,
                emoji=emoji.back,
                custom_id="Reputacao_VoltarPersonalizar",
            ),
        ),
    ]


async def _build_perfil_membro(
    guild: disnake.Guild,
    membro: disnake.Member,
    cfg: dict,
    avaliador_id: Optional[str] = None,
) -> list:
    """Monta o painel de perfil de reputação de um membro."""
    perfil = obter_perfil(str(membro.id))
    media = perfil.get("media", 0.0)
    count = perfil.get("count", 0)
    barra = barra_nota(media)
    estrelas = estrelas_nota(media)
    cor_indicador = nota_cor(media)

    nota_anonima = cfg.get("nota_anonima", False)
    nota_avaliador = None
    if avaliador_id:
        nota_avaliador = perfil.get("avaliacoes", {}).get(avaliador_id)

    # Top ranking
    ranking = gerar_ranking(limit=100)
    posicao = next((i + 1 for i, r in enumerate(ranking) if r["user_id"] == str(membro.id)), None)
    posicao_txt = f"#{posicao}" if posicao else "Fora do ranking"

    nota_avaliador_txt = f"`{nota_avaliador}/10`" if nota_avaliador else "`Você ainda não avaliou`"

    texto = (
        f"## {membro.display_name}\n"
        f"-# {membro.mention} · {posicao_txt} no ranking\n\n"
        f"{cor_indicador} **Média:** `{media}/10`\n"
        f"{estrelas}\n"
        f"`{barra}`\n\n"
        f"{emoji.member} **Avaliações:** `{count}`\n"
    )
    if avaliador_id:
        texto += f"{emoji.correct} **Sua avaliação:** {nota_avaliador_txt}\n"

    # Botões de avaliação (1-10 em duas linhas de 5)
    auto_avaliacao = cfg.get("permitir_auto_avaliacao", False)
    pode_avaliar = avaliador_id and (auto_avaliacao or avaliador_id != str(membro.id))

    def _nota_btn(n: int) -> disnake.ui.Button:
        é_selecionada = (nota_avaliador == n)
        return disnake.ui.Button(
            label=str(n),
            style=disnake.ButtonStyle.green if é_selecionada else disnake.ButtonStyle.gray,
            custom_id=f"Reputacao_Avaliar:{membro.id}:{n}",
            disabled=not pode_avaliar,
        )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(texto),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(f"-# Avalie este membro de 1 a 10:"),
            disnake.ui.ActionRow(*[_nota_btn(n) for n in range(1, 6)]),
            disnake.ui.ActionRow(*[_nota_btn(n) for n in range(6, 11)]),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Nova Busca",
                style=disnake.ButtonStyle.gray,
                emoji=emoji.search,
                custom_id="Reputacao_NovaBusca",
            ),
        ),
    ]


def _build_ranking_components(guild: disnake.Guild, cfg: dict, limit: int = 15) -> list:
    """Monta o componente do ranking para envio no canal."""
    ranking = gerar_ranking(limit=limit)

    if not ranking:
        corpo = "`Ainda não há avaliações registradas.`"
    else:
        linhas = []
        medalhas = ["🥇", "🥈", "🥉"]
        for i, item in enumerate(ranking):
            member = guild.get_member(int(item["user_id"]))
            nome = member.display_name if member else f"ID {item['user_id']}"
            medalha = medalhas[i] if i < 3 else f"`#{i+1}`"
            cor = nota_cor(item["media"])
            linhas.append(
                f"{medalha} **{nome}** — {cor} `{item['media']}/10` · {item['count']} avaliações"
            )
        corpo = "\n".join(linhas)

    agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M") + " UTC"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# 🏆 Ranking de Reputação\n"
                f"-# Atualizado em {agora}\n\n"
                f"{corpo}"
            ),
            **accent(),
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class ReputacaoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task_running = False
        self._task_intervalo = 60  # minutos

    # ── Painel de Config (acessado via cog.Painel()) ──────────────────────────

    def Painel(self) -> list:
        cfg = carregar_config()
        return _build_config_painel(cfg)

    def PainelEmbed(self) -> tuple:
        cfg = carregar_config()
        embed = disnake.Embed(
            title="Sistema de Reputação",
            description="Configure o sistema de reputação por usuário.",
            color=color(),
        )
        return embed, []

    # ── Task de atualização periódica ──────────────────────────────────────────

    def _restart_task(self, intervalo_min: int):
        """Para e reinicia a task com novo intervalo."""
        if self._task_loop.is_running():
            self._task_loop.cancel()
        self._task_loop.change_interval(minutes=intervalo_min)
        self._task_loop.start()

    @tasks.loop(minutes=60)
    async def _task_loop(self):
        cfg = carregar_config()
        if not cfg.get("ativado"):
            return
        await self._atualizar_paineis(cfg)
        await self._aplicar_cargos(cfg)

    @_task_loop.before_loop
    async def _before_task(self):
        await self.bot.wait_until_ready()

    async def _atualizar_paineis(self, cfg: dict):
        """Atualiza ranking e painel de busca nos canais configurados."""
        # Ranking
        canal_ranking_id = cfg.get("canal_ranking")
        if canal_ranking_id:
            canal: disnake.TextChannel | None = self.bot.get_channel(int(canal_ranking_id))
            if canal:
                guild = canal.guild
                msg_id = cfg.get("mensagem_ranking_id")
                componentes = _build_ranking_components(guild, cfg)

                if msg_id:
                    try:
                        msg = await canal.fetch_message(int(msg_id))
                        await msg.edit(components=componentes)
                    except (disnake.NotFound, disnake.HTTPException):
                        msg = await enviar_painel_ranking(canal, guild, cfg)
                        cfg["mensagem_ranking_id"] = str(msg.id)
                        salvar_config(cfg)
                else:
                    msg = await enviar_painel_ranking(canal, guild, cfg)
                    cfg["mensagem_ranking_id"] = str(msg.id)
                    salvar_config(cfg)

    async def _aplicar_cargos(self, cfg: dict):
        """Aplica/remove cargos baseados em notas."""
        guild_id = None
        # Pegar qualquer guild do bot
        guilds = list(self.bot.guilds)
        if not guilds:
            return
        guild = guilds[0]

        nota_minima_cargos = cfg.get("nota_minima_cargo", {})
        cargo_top1_id = cfg.get("cargo_top1")
        ranking = gerar_ranking(limit=100)

        # Top 1
        if cargo_top1_id and ranking:
            top1_id = int(ranking[0]["user_id"])
            cargo_top1 = guild.get_role(int(cargo_top1_id))
            if cargo_top1:
                for member in guild.members:
                    tem = cargo_top1 in member.roles
                    deveria = (member.id == top1_id)
                    if deveria and not tem:
                        try:
                            await member.add_roles(cargo_top1, reason="[Reputação] Top 1")
                        except disnake.HTTPException:
                            pass
                    elif not deveria and tem:
                        try:
                            await member.remove_roles(cargo_top1, reason="[Reputação] Não é mais Top 1")
                        except disnake.HTTPException:
                            pass

        # Cargos por nota mínima
        if nota_minima_cargos:
            avaliacoes = helpers.carregar_avaliacoes()
            for cargo_id, nota_min in nota_minima_cargos.items():
                cargo = guild.get_role(int(cargo_id))
                if not cargo:
                    continue
                for member in guild.members:
                    perfil = avaliacoes.get(str(member.id), {})
                    media = perfil.get("media", 0.0)
                    count = perfil.get("count", 0)
                    tem = cargo in member.roles
                    deveria = (count >= 1 and media >= float(nota_min))
                    if deveria and not tem:
                        try:
                            await member.add_roles(cargo, reason=f"[Reputação] Média {media} ≥ {nota_min}")
                        except disnake.HTTPException:
                            pass
                    elif not deveria and tem:
                        try:
                            await member.remove_roles(cargo, reason=f"[Reputação] Média abaixo de {nota_min}")
                        except disnake.HTTPException:
                            pass

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENERS — Botões
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def on_reputacao_button(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Avaliação de nota ─────────────────────────────────────────────────
        if cid.startswith("Reputacao_Avaliar:"):
            await self._handle_avaliar(inter, cid)
            return

        # ── Nova busca (painel público) ───────────────────────────────────────
        if cid == "Reputacao_NovaBusca":
            await inter.response.send_modal(BuscarMembroModal())
            return

        # ── Voltar para comunidade ────────────────────────────────────────────
        if cid == "Reputacao_VoltarComunidade":
            cog_com = self.bot.get_cog("ComunidadeCog")
            if cog_com:
                if not inter.response.is_done():
                    await inter.response.defer(with_message=False)
                if _mode() == "embed":
                    embed, comps = cog_com.community_embed()
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=cog_com.community_components())
            return

        # ── Voltar para config ────────────────────────────────────────────────
        if cid == "Reputacao_VoltarConfig":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        # ── Voltar para menu de personalizar ─────────────────────────────────
        if cid == "Reputacao_VoltarPersonalizar":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_personalizar_menu(cfg))
            return

        # ── Painel de cargos (intermediário) ──────────────────────────────────
        if cid == "Reputacao_PainelCargos":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_cargos_nota_painel(cfg))
            return

        # ── Painel de personalizar (intermediário) ────────────────────────────
        if cid == "Reputacao_PainelPersonalizar":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_personalizar_menu(cfg))
            return

        # ── Toggle ativado ────────────────────────────────────────────────────
        if cid == "Reputacao_ToggleAtivado":
            cfg = carregar_config()
            cfg["ativado"] = not cfg.get("ativado", False)
            salvar_config(cfg)
            if cfg["ativado"]:
                intervalo = cfg.get("intervalo_ranking", 60)
                self._restart_task(intervalo)
            else:
                if self._task_loop.is_running():
                    self._task_loop.cancel()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        # ── Toggle auto-avaliação ─────────────────────────────────────────────
        if cid == "Reputacao_ToggleAutoAvaliacao":
            cfg = carregar_config()
            cfg["permitir_auto_avaliacao"] = not cfg.get("permitir_auto_avaliacao", False)
            salvar_config(cfg)
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        # ── Toggle anônimo ────────────────────────────────────────────────────
        if cid == "Reputacao_ToggleAnonimo":
            cfg = carregar_config()
            cfg["nota_anonima"] = not cfg.get("nota_anonima", False)
            salvar_config(cfg)
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        # ── Selects de canal/cargo ─────────────────────────────────────────────
        if cid in ("Reputacao_SetCanalPesquisa", "Reputacao_SetCanalRanking"):
            await self._handle_set_select(inter, cid)
            return

        if cid == "Reputacao_SetCargoTop1":
            await self._handle_set_select(inter, cid)
            return

        # ── Intervalo ─────────────────────────────────────────────────────────
        if cid == "Reputacao_SetIntervalo":
            cfg = carregar_config()
            await inter.response.send_modal(IntervaloModal(cfg.get("intervalo_ranking", 60)))
            return

        # ── Cargos por nota ───────────────────────────────────────────────────
        if cid == "Reputacao_GerenciarCargosNota":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_cargos_nota_painel(cfg))
            return

        if cid == "Reputacao_AdicionarCargoNota":
            await inter.response.send_modal(NotaMinimaCargosModal())
            return

        if cid == "Reputacao_RemoverCargoNota":
            await self._handle_remover_cargo_nota(inter)
            return

        # ── Personalizar mensagens ────────────────────────────────────────────
        if cid == "Reputacao_PersonalizarPesquisa":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_personalizar_painel("pesquisa", cfg))
            return

        if cid == "Reputacao_PersonalizarRanking":
            cfg = carregar_config()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_personalizar_painel("ranking", cfg))
            return

        # ── Enviar painéis ────────────────────────────────────────────────────
        if cid == "Reputacao_EnviarPainelPesquisa":
            await self._handle_enviar_painel_pesquisa(inter)
            return

        if cid == "Reputacao_EnviarRanking":
            await self._handle_enviar_ranking(inter)
            return

        # ── Ações do editor de mensagem (Pesquisa) ────────────────────────────
        if cid.startswith("Reputacao_MsgPesquisa_"):
            await self._handle_editor_msg(inter, cid, "pesquisa")
            return

        # ── Ações do editor de mensagem (Ranking) ────────────────────────────
        if cid.startswith("Reputacao_MsgRanking_"):
            await self._handle_editor_msg(inter, cid, "ranking")
            return

    # ──────────────────────────────────────────────────────────────────────────
    # HANDLERS INTERNOS
    # ──────────────────────────────────────────────────────────────────────────

    async def _handle_avaliar(self, inter: disnake.MessageInteraction, cid: str):
        """Processa a avaliação de um membro."""
        # custom_id = "Reputacao_Avaliar:{membro_id}:{nota}"
        partes = cid.split(":")
        if len(partes) != 3:
            return
        _, membro_id, nota_str = partes
        nota = int(nota_str)

        cfg = carregar_config()
        avaliador_id = str(inter.author.id)

        # Verificar auto-avaliação
        if avaliador_id == membro_id and not cfg.get("permitir_auto_avaliacao", False):
            await inter.response.send_message(
                f"{emoji.warn} Você não pode avaliar a si mesmo.", ephemeral=True
            )
            return

        resultado = registrar_avaliacao(membro_id, avaliador_id, nota)

        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        membro = inter.guild.get_member(int(membro_id))
        if membro:
            componentes = await _build_perfil_membro(inter.guild, membro, cfg, avaliador_id)
            await inter.edit_original_message(components=componentes)

        # Aplicar cargos se necessário
        asyncio.create_task(self._aplicar_cargos(cfg))

        # Atualizar ranking se houver canal configurado
        asyncio.create_task(self._atualizar_paineis(cfg))

    async def _handle_set_select(self, inter: disnake.MessageInteraction, cid: str):
        """Mostra seletor de canal ou cargo inline."""
        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        mapa = {
            "Reputacao_SetCanalPesquisa": ("channel", "Reputacao_ConfirmarCanalPesquisa", "Canal de Pesquisa"),
            "Reputacao_SetCanalRanking": ("channel", "Reputacao_ConfirmarCanalRanking", "Canal de Ranking"),
            "Reputacao_SetCargoTop1": ("role", "Reputacao_ConfirmarCargoTop1", "Cargo Top 1"),
        }
        tipo, confirm_id, label = mapa[cid]

        if tipo == "channel":
            select = disnake.ui.ChannelSelect(
                placeholder=f"Selecione o {label}...",
                custom_id=confirm_id,
                channel_types=[disnake.ChannelType.text],
                min_values=1, max_values=1,
            )
        else:
            select = disnake.ui.RoleSelect(
                placeholder=f"Selecione o {label}...",
                custom_id=confirm_id,
                min_values=1, max_values=1,
            )

        cfg = carregar_config()
        # Canais voltam pro config principal; cargo top1 volta pro painel de cargos
        if cid == "Reputacao_SetCargoTop1":
            comps = _build_cargos_nota_painel(cfg)
        else:
            comps = _build_config_painel(cfg)
        comps.insert(0, disnake.ui.ActionRow(select))
        await inter.edit_original_message(components=comps)

    async def _handle_remover_cargo_nota(self, inter: disnake.MessageInteraction):
        """Mostra select para remover cargo por nota."""
        cfg = carregar_config()
        nota_minima_cargos = cfg.get("nota_minima_cargo", {})
        if not nota_minima_cargos:
            await inter.response.send_message(f"{emoji.warn} Nenhum cargo configurado.", ephemeral=True)
            return

        options = [
            disnake.SelectOption(
                label=f"Cargo {cargo_id} — nota ≥ {nota}",
                value=cargo_id,
                description=f"Nota mínima: {nota}",
            )
            for cargo_id, nota in nota_minima_cargos.items()
        ]

        select = disnake.ui.StringSelect(
            placeholder="Selecione o cargo para remover...",
            custom_id="Reputacao_ConfirmarRemoverCargoNota",
            options=options,
        )

        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        comps = _build_cargos_nota_painel(cfg)
        comps.insert(0, disnake.ui.ActionRow(select))
        await inter.edit_original_message(components=comps)

    async def _handle_enviar_painel_pesquisa(self, inter: disnake.MessageInteraction):
        cfg = carregar_config()
        canal_id = cfg.get("canal_pesquisa")
        if not canal_id:
            await inter.response.send_message(
                f"{emoji.warn} Configure o canal de pesquisa primeiro.", ephemeral=True
            )
            return

        canal = inter.guild.get_channel(int(canal_id))
        if not canal:
            await inter.response.send_message(f"{emoji.warn} Canal não encontrado.", ephemeral=True)
            return

        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        # Apagar msg antiga
        msg_id = cfg.get("mensagem_pesquisa_id")
        if msg_id:
            try:
                old = await canal.fetch_message(int(msg_id))
                await old.delete()
            except (disnake.NotFound, disnake.HTTPException):
                pass

        msg = await enviar_painel_pesquisa(canal, inter.guild, cfg)
        cfg["mensagem_pesquisa_id"] = str(msg.id)
        salvar_config(cfg)
        await inter.edit_original_message(
            content=None,
            components=_build_personalizar_painel("pesquisa", cfg),
        )
        await inter.followup.send(
            f"{emoji.correct} Painel de busca enviado em {canal.mention}!", ephemeral=True
        )

    async def _handle_enviar_ranking(self, inter: disnake.MessageInteraction):
        cfg = carregar_config()
        canal_id = cfg.get("canal_ranking")
        if not canal_id:
            await inter.response.send_message(
                f"{emoji.warn} Configure o canal de ranking primeiro.", ephemeral=True
            )
            return

        canal = inter.guild.get_channel(int(canal_id))
        if not canal:
            await inter.response.send_message(f"{emoji.warn} Canal não encontrado.", ephemeral=True)
            return

        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        # Apagar msg antiga
        msg_id = cfg.get("mensagem_ranking_id")
        if msg_id:
            try:
                old = await canal.fetch_message(int(msg_id))
                await old.delete()
            except (disnake.NotFound, disnake.HTTPException):
                pass

        msg = await enviar_painel_ranking(canal, inter.guild, cfg)
        cfg["mensagem_ranking_id"] = str(msg.id)
        salvar_config(cfg)
        await inter.edit_original_message(
            content=None,
            components=_build_personalizar_painel("ranking", cfg),
        )
        await inter.followup.send(
            f"{emoji.correct} Ranking enviado em {canal.mention}!", ephemeral=True
        )

    async def _handle_editor_msg(self, inter: disnake.MessageInteraction, cid: str, tipo: str):
        """Lida com ações do editor de mensagem personalizada."""
        key_msg = "mensagem_pesquisa" if tipo == "pesquisa" else "mensagem_ranking"
        acao = cid.split("_", 2)[-1]  # Ex: "ApagarContent", "DefinirMensagem", etc.
        cfg = carregar_config()

        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        if acao == "ApagarContent":
            editor = cfg.get(key_msg, {})
            editor.pop("content", None)
            cfg[key_msg] = editor
            salvar_config(cfg)
            await inter.edit_original_message(components=_build_personalizar_painel(tipo, cfg))

        elif acao == "ApagarEmbed":
            editor = cfg.get(key_msg, {})
            editor.pop("embed", None)
            cfg[key_msg] = editor
            salvar_config(cfg)
            await inter.edit_original_message(components=_build_personalizar_painel(tipo, cfg))

        elif acao == "ApagarImagem":
            editor = cfg.get(key_msg, {})
            editor.pop("externalImage", None)
            embed = editor.get("embed", {})
            embed.pop("banner", None)
            embed.pop("thumbnail", None)
            editor["embed"] = embed
            cfg[key_msg] = editor
            salvar_config(cfg)
            await inter.edit_original_message(components=_build_personalizar_painel(tipo, cfg))

        elif acao == "Importar":
            # Importar mensagem do Anunciar
            msg_anunciar = db.get_document("messages_anunciar") or {}
            if msg_anunciar:
                cfg[key_msg] = msg_anunciar
                salvar_config(cfg)
                await inter.edit_original_message(components=_build_personalizar_painel(tipo, cfg))
            else:
                await inter.followup.send(
                    f"{emoji.warn} Nenhuma mensagem configurada no Anunciar.", ephemeral=True
                )

        elif acao == "Preview":
            editor = cfg.get(key_msg, {})
            if editor:
                built = Builder.build_from_cfg(editor)
                if built["mode"] == "v2":
                    await inter.followup.send(
                        components=built["components"],
                        flags=built.get("flags", disnake.MessageFlags(is_components_v2=True)),
                        ephemeral=True,
                    )
                else:
                    kwargs = {"ephemeral": True}
                    if built.get("content"):
                        kwargs["content"] = built["content"]
                    if built.get("embed"):
                        kwargs["embed"] = built["embed"]
                    await inter.followup.send(**kwargs)

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENERS — Selects (canal/cargo/dropdown)
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def on_reputacao_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "Reputacao_ConfirmarCanalPesquisa":
            cfg = carregar_config()
            cfg["canal_pesquisa"] = str(inter.values[0].id)
            salvar_config(cfg)
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        if cid == "Reputacao_ConfirmarCanalRanking":
            cfg = carregar_config()
            cfg["canal_ranking"] = str(inter.values[0].id)
            salvar_config(cfg)
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        if cid == "Reputacao_ConfirmarCargoTop1":
            cfg = carregar_config()
            cfg["cargo_top1"] = str(inter.values[0].id)
            salvar_config(cfg)
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_cargos_nota_painel(cfg))
            return

        if cid == "Reputacao_ConfirmarRemoverCargoNota":
            cfg = carregar_config()
            cargo_id = inter.values[0]
            cfg.get("nota_minima_cargo", {}).pop(cargo_id, None)
            salvar_config(cfg)
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_cargos_nota_painel(cfg))
            return

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENERS — Modais
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_modal_submit")
    async def on_reputacao_modal(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id

        # ── Buscar membro ──────────────────────────────────────────────────────
        if cid == "Reputacao_BuscarModal":
            busca = inter.text_values.get("busca", "").strip()
            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)

            membro = await self._buscar_membro(inter.guild, busca)
            if not membro:
                await inter.followup.send(
                    f"{emoji.warn} Membro `{busca}` não encontrado.", ephemeral=True
                )
                return

            cfg = carregar_config()
            comps = await _build_perfil_membro(inter.guild, membro, cfg, str(inter.author.id))
            await inter.followup.send(components=comps, ephemeral=True)
            return

        # ── Intervalo ──────────────────────────────────────────────────────────
        if cid == "Reputacao_IntervaloModal":
            valor_str = inter.text_values.get("intervalo", "60").strip()
            try:
                valor = int(valor_str)
                if valor < 5:
                    valor = 5
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.warn} Valor inválido. Use um número inteiro.", ephemeral=True
                )
                return

            cfg = carregar_config()
            cfg["intervalo_ranking"] = valor
            salvar_config(cfg)
            self._restart_task(valor)

            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_config_painel(cfg))
            return

        # ── Adicionar cargo por nota ───────────────────────────────────────────
        if cid == "Reputacao_NotaMinimaCargosModal":
            cargo = inter.resolved.roles.get(
                list(inter.text_values.keys())[0]
                if False else None
            )
            # Pegar cargo do select
            cargo_vals = inter.resolved.roles
            nota_str = inter.text_values.get("nota_minima", "").strip().replace(",", ".")
            try:
                nota = float(nota_str)
                if not (1.0 <= nota <= 10.0):
                    raise ValueError
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.warn} Nota inválida. Use um valor entre 1.0 e 10.0.", ephemeral=True
                )
                return

            if not cargo_vals:
                await inter.response.send_message(
                    f"{emoji.warn} Selecione um cargo.", ephemeral=True
                )
                return

            cargo_id = str(list(cargo_vals.keys())[0])
            cfg = carregar_config()
            cfg.setdefault("nota_minima_cargo", {})[cargo_id] = nota
            salvar_config(cfg)

            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=_build_cargos_nota_painel(cfg))
            return

    # ── Utilitário de busca ────────────────────────────────────────────────────

    async def _buscar_membro(self, guild: disnake.Guild, busca: str) -> disnake.Member | None:
        """Busca membro por ID numérico ou por nome/apelido."""
        # Tenta por ID
        if busca.isdigit():
            member = guild.get_member(int(busca))
            if member:
                return member
            try:
                member = await guild.fetch_member(int(busca))
                return member
            except (disnake.NotFound, disnake.HTTPException):
                pass

        # Busca por nome (case-insensitive)
        busca_lower = busca.lower()
        for member in guild.members:
            if busca_lower in member.display_name.lower() or busca_lower in member.name.lower():
                return member
        return None

    def cog_unload(self):
        if self._task_loop.is_running():
            self._task_loop.cancel()


def setup(bot: commands.Bot):
    bot.add_cog(ReputacaoCog(bot))