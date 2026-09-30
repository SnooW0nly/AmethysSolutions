from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db

from . import helpers


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de UI
# ══════════════════════════════════════════════════════════════════════════════

def _primary_colour() -> disnake.Colour | None:
    try:
        colors = db.get_document("custom_colors") or {}
        h = (colors.get("primary") or "").strip().lstrip("#")
        if h:
            return disnake.Colour(int(h, 16))
    except Exception:
        pass
    return None


def _container_kwargs() -> dict:
    cor = _primary_colour()
    return {"accent_colour": cor} if cor else {}


def _resumo_thresholds(cfg: dict) -> str:
    thr = helpers.get_sorted_thresholds(cfg)
    if not thr:
        return "-# *Nenhum threshold configurado.*"
    linhas = []
    for t in thr:
        label = t.get("label") or helpers.format_seconds(int(t.get("segundos", 0)))
        cid   = t.get("cargo_id")
        cargo = f"<@&{cid}>" if cid else "`?`"
        linhas.append(f"• **{label}** → {cargo}")
    return "\n".join(linhas)


def _resumo_filtros(cfg: dict) -> str:
    contar_muted    = cfg.get("contar_muted", False)
    contar_deafened = cfg.get("contar_deafened", False)
    excluir         = cfg.get("excluir_canais", [])
    incluir         = cfg.get("incluir_apenas_canais", [])

    partes = [
        f"{emoji.on if contar_muted else emoji.off} Contar membro mutado",
        f"{emoji.on if contar_deafened else emoji.off} Contar membro com fone",
    ]
    if excluir:
        partes.append(f"{emoji.delete} `{len(excluir)}` canal(is) excluído(s)")
    if incluir:
        partes.append(f"{emoji.search} Apenas `{len(incluir)}` canal(is) permitido(s)")
    return "\n".join(partes)


# ══════════════════════════════════════════════════════════════════════════════
# Painel principal
# ══════════════════════════════════════════════════════════════════════════════

class TempCallConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Painel V2 ──────────────────────────────────────────────────────────────
    @staticmethod
    def Painel() -> list:
        cfg     = helpers.carregar_config()
        ativado = bool(cfg.get("ativado", False))

        canal_ranking_id  = cfg.get("canal_ranking_id")
        canal_ranking_txt = f"<#{canal_ranking_id}>" if canal_ranking_id else "`Não configurado`"
        intervalo         = int(cfg.get("ranking_intervalo_minutos", 5))
        top_n             = int(cfg.get("ranking_top", 10))
        modo              = cfg.get("modo_envio", "v2")
        modo_label        = "Componentes V2" if modo == "v2" else "Embed"
        log_canal_id      = cfg.get("log_cargo_canal_id")
        log_canal_txt     = f"<#{log_canal_id}>" if log_canal_id else "`Não configurado`"
        titulo            = cfg.get("ranking_titulo", "🏆 Ranking de Voz")

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.voice} **Canal do Ranking:** {canal_ranking_txt}\n"
            f"{emoji.clock} **Intervalo de atualização:** `{intervalo}` min\n"
            f"{emoji.role} **Top:** `{top_n}` membros\n"
            f"{emoji.reload} **Modo de envio:** `{modo_label}`\n"
            f"{emoji.textc} **Canal de log (cargos):** {log_canal_txt}\n"
            f"{emoji.edit} **Título:** `{titulo}`"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Automações > **Tempo em Call**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Rastreie o tempo dos membros em call, conceda cargos automaticamente "
                    "e exiba um ranking atualizado em tempo real."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                # Linha 1: toggle + canal ranking + intervalo
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativado" if ativado else "Desativado",
                        style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.grey,
                        emoji=emoji.power,
                        custom_id="TC_ToggleAtivo",
                    ),
                    disnake.ui.Button(
                        label="Canal do Ranking",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.voice,
                        custom_id="TC_CanalRanking",
                        disabled=not ativado,
                    ),
                    disnake.ui.Button(
                        label="Canal de Log",
                        style=disnake.ButtonStyle.secondary,
                        emoji=emoji.textc,
                        custom_id="TC_CanalLog",
                        disabled=not ativado,
                    ),
                ),

                # Linha 2: thresholds + filtros
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Thresholds de Cargo",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.role,
                        custom_id="TC_AbrirThresholds",
                        disabled=not ativado,
                    ),
                    disnake.ui.Button(
                        label="Filtros",
                        style=disnake.ButtonStyle.secondary,
                        emoji=emoji.shield_star,
                        custom_id="TC_AbrirFiltros",
                        disabled=not ativado,
                    ),
                    disnake.ui.Button(
                        label="Personalizar Ranking",
                        style=disnake.ButtonStyle.secondary,
                        emoji=emoji.edit,
                        custom_id="TC_PersonalizarRanking",
                        disabled=not ativado,
                    ),
                ),

                # Linha 3: publicar ranking + ver top agora
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Publicar/Atualizar Ranking Agora",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.reload,
                        custom_id="TC_PublicarRankingAgora",
                        disabled=not ativado or not canal_ranking_id,
                    ),
                    disnake.ui.Button(
                        label="Prévia do Ranking",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.search,
                        custom_id="TC_PreviaRanking",
                        disabled=not ativado,
                    ),
                ),

                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="VoltarAutomações",
                ),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        cfg     = helpers.carregar_config()
        ativado = bool(cfg.get("ativado", False))

        canal_ranking_id  = cfg.get("canal_ranking_id")
        canal_ranking_txt = f"<#{canal_ranking_id}>" if canal_ranking_id else "Não configurado"
        intervalo         = int(cfg.get("ranking_intervalo_minutos", 5))
        top_n             = int(cfg.get("ranking_top", 10))
        modo              = cfg.get("modo_envio", "v2")
        modo_label        = "Componentes V2" if modo == "v2" else "Embed"
        log_canal_id      = cfg.get("log_cargo_canal_id")
        log_canal_txt     = f"<#{log_canal_id}>" if log_canal_id else "Não configurado"

        embed = disnake.Embed(
            title="Tempo em Call",
            description="Rastreie tempo de voz, conceda cargos e exiba ranking em tempo real.",
        )
        cor = _primary_colour()
        if cor:
            embed.colour = cor
        embed.add_field(
            name="Configurações",
            value=(
                f"{emoji.on if ativado else emoji.off} Status: {'Ativado' if ativado else 'Desativado'}\n"
                f"{emoji.voice} Canal Ranking: {canal_ranking_txt}\n"
                f"{emoji.clock} Intervalo: {intervalo} min\n"
                f"{emoji.role} Top: {top_n} membros\n"
                f"{emoji.reload} Modo: {modo_label}\n"
                f"{emoji.textc} Canal Log: {log_canal_txt}"
            ),
            inline=False,
        )

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ativado" if ativado else "Desativado", style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="TC_ToggleAtivo"),
                disnake.ui.Button(label="Canal do Ranking", style=disnake.ButtonStyle.blurple, emoji=emoji.voice, custom_id="TC_CanalRanking", disabled=not ativado),
                disnake.ui.Button(label="Canal de Log", style=disnake.ButtonStyle.secondary, emoji=emoji.textc, custom_id="TC_CanalLog", disabled=not ativado),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Thresholds de Cargo", style=disnake.ButtonStyle.blurple, emoji=emoji.role, custom_id="TC_AbrirThresholds", disabled=not ativado),
                disnake.ui.Button(label="Filtros", style=disnake.ButtonStyle.secondary, emoji=emoji.shield_star, custom_id="TC_AbrirFiltros", disabled=not ativado),
                disnake.ui.Button(label="Personalizar Ranking", style=disnake.ButtonStyle.secondary, emoji=emoji.edit, custom_id="TC_PersonalizarRanking", disabled=not ativado),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Publicar/Atualizar Ranking Agora", style=disnake.ButtonStyle.green, emoji=emoji.reload, custom_id="TC_PublicarRankingAgora", disabled=not ativado or not canal_ranking_id),
                disnake.ui.Button(label="Prévia do Ranking", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="TC_PreviaRanking", disabled=not ativado),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            ),
        ]
        return embed, components

    # ── Sub-painel: Thresholds ─────────────────────────────────────────────────
    @staticmethod
    def PainelThresholds() -> list:
        cfg = helpers.carregar_config()
        thr = helpers.get_sorted_thresholds(cfg)

        resumo = _resumo_thresholds(cfg)

        # Opções de remoção
        opcoes_remover = [
            disnake.SelectOption(
                label=f"{t.get('label') or helpers.format_seconds(int(t.get('segundos',0)))} → cargo {t.get('cargo_id')}",
                value=str(i),
                description=f"{helpers.format_seconds(int(t.get('segundos',0)))} | Cargo ID: {t.get('cargo_id')}",
            )
            for i, t in enumerate(thr)
        ]

        rows = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Threshold", style=disnake.ButtonStyle.green, emoji=emoji.role, custom_id="TC_AdicionarThreshold"),
            ),
        ]
        if opcoes_remover:
            rows.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="TC_RemoverThreshold",
                        placeholder="Selecionar threshold para remover...",
                        options=opcoes_remover[:25],
                        min_values=1,
                        max_values=1,
                    )
                )
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Automações > Tempo em Call > **Thresholds de Cargo**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Configure os cargos que serão concedidos automaticamente ao atingir "
                    "determinado tempo acumulado em call."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TC_VoltarPainel"),
            ),
        ]

    # ── Sub-painel: Filtros ────────────────────────────────────────────────────
    @staticmethod
    def PainelFiltros() -> list:
        cfg             = helpers.carregar_config()
        contar_muted    = bool(cfg.get("contar_muted", False))
        contar_deafened = bool(cfg.get("contar_deafened", False))
        excluir         = cfg.get("excluir_canais", [])
        incluir         = cfg.get("incluir_apenas_canais", [])

        resumo = _resumo_filtros(cfg)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Automações > Tempo em Call > **Filtros**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Defina quais membros e canais devem ser contabilizados no tracking de voz."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                # Toggles mute/deaf
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Contar Mutado: Sim" if contar_muted else "Contar Mutado: Não",
                        style=disnake.ButtonStyle.green if contar_muted else disnake.ButtonStyle.grey,
                        emoji=emoji.power,
                        custom_id="TC_ToggleMuted",
                    ),
                    disnake.ui.Button(
                        label="Contar com Fone: Sim" if contar_deafened else "Contar com Fone: Não",
                        style=disnake.ButtonStyle.green if contar_deafened else disnake.ButtonStyle.grey,
                        emoji=emoji.power,
                        custom_id="TC_ToggleDeafened",
                    ),
                ),

                # Seleção de canais excluídos
                disnake.ui.TextDisplay("-# **Canais ignorados** (o tempo nesses canais NÃO conta):"),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="TC_SelectExcluirCanais",
                        placeholder="Canais a IGNORAR...",
                        channel_types=[disnake.ChannelType.voice, disnake.ChannelType.stage_voice],
                        min_values=0,
                        max_values=25,
                        default_values=[disnake.Object(id=int(c)) for c in excluir if str(c).isdigit()],
                    )
                ),

                # Seleção de canais permitidos
                disnake.ui.TextDisplay("-# **Canais permitidos** (se preenchido, APENAS esses canais contam):"),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="TC_SelectIncluirCanais",
                        placeholder="Canais PERMITIDOS (deixe vazio = todos)...",
                        channel_types=[disnake.ChannelType.voice, disnake.ChannelType.stage_voice],
                        min_values=0,
                        max_values=25,
                        default_values=[disnake.Object(id=int(c)) for c in incluir if str(c).isdigit()],
                    )
                ),

                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TC_VoltarPainel"),
            ),
        ]

    # ── Sub-painel: Personalizar Ranking ──────────────────────────────────────
    @staticmethod
    def PainelPersonalizarRanking() -> list:
        cfg       = helpers.carregar_config()
        modo      = cfg.get("modo_envio", "v2")
        top_n     = int(cfg.get("ranking_top", 10))
        intervalo = int(cfg.get("ranking_intervalo_minutos", 5))

        modo_options = [
            disnake.SelectOption(label="Componentes V2", value="v2", default=(modo == "v2")),
            disnake.SelectOption(label="Embed", value="embed", default=(modo == "embed")),
        ]
        intervalo_options = [
            disnake.SelectOption(label="1 minuto", value="1", default=(intervalo == 1)),
            disnake.SelectOption(label="2 minutos", value="2", default=(intervalo == 2)),
            disnake.SelectOption(label="5 minutos", value="5", default=(intervalo == 5)),
            disnake.SelectOption(label="10 minutos", value="10", default=(intervalo == 10)),
            disnake.SelectOption(label="15 minutos", value="15", default=(intervalo == 15)),
            disnake.SelectOption(label="30 minutos", value="30", default=(intervalo == 30)),
            disnake.SelectOption(label="60 minutos", value="60", default=(intervalo == 60)),
        ]
        top_options = [
            disnake.SelectOption(label=f"Top {n}", value=str(n), default=(top_n == n))
            for n in [3, 5, 10, 15, 20, 25]
        ]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Automações > Tempo em Call > **Personalizar Ranking**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                disnake.ui.TextDisplay("-# **Modo de envio:**"),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="TC_SelectModoEnvio",
                        placeholder="Escolha o modo de envio do ranking...",
                        options=modo_options,
                    )
                ),

                disnake.ui.TextDisplay("-# **Intervalo de atualização:**"),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="TC_SelectIntervalo",
                        placeholder="Com que frequência atualizar?",
                        options=intervalo_options,
                    )
                ),

                disnake.ui.TextDisplay("-# **Quantidade de membros no ranking:**"),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="TC_SelectTopN",
                        placeholder="Quantos membros mostrar?",
                        options=top_options,
                    )
                ),

                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar Título e Cor",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id="TC_EditarTituloRanking",
                    ),
                ),

                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TC_VoltarPainel"),
            ),
        ]

    # ── Sub-painel: Canal do Ranking (ChannelSelect) ───────────────────────────
    @staticmethod
    def PainelCanalRanking() -> list:
        cfg = helpers.carregar_config()
        canal_id = cfg.get("canal_ranking_id")
        defaults = [disnake.Object(id=int(canal_id))] if canal_id and str(canal_id).isdigit() else []

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Automações > Tempo em Call > **Canal do Ranking**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Selecione o canal onde o ranking de tempo em call será publicado e "
                    "atualizado automaticamente."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="TC_SelectCanalRanking",
                        placeholder="Selecione o canal do ranking...",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1,
                        max_values=1,
                        default_values=defaults,
                    )
                ),
                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TC_VoltarPainel"),
            ),
        ]

    @staticmethod
    def PainelCanalLog() -> list:
        cfg      = helpers.carregar_config()
        canal_id = cfg.get("log_cargo_canal_id")
        defaults = [disnake.Object(id=int(canal_id))] if canal_id and str(canal_id).isdigit() else []

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Automações > Tempo em Call > **Canal de Log**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Selecione o canal onde será enviada uma mensagem sempre que "
                    "um membro atingir um threshold e receber um cargo."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="TC_SelectCanalLog",
                        placeholder="Selecione o canal de log (ou nenhum para desativar)...",
                        channel_types=[disnake.ChannelType.text],
                        min_values=0,
                        max_values=1,
                        default_values=defaults,
                    )
                ),
                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TC_VoltarPainel"),
            ),
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # Listeners
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def TC_Button_Listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid or not cid.startswith("TC_"):
            return

        # ── Toggle Ativo ─────────────────────────────────────────────────────
        if cid == "TC_ToggleAtivo":
            cfg  = helpers.carregar_config()
            novo = not bool(cfg.get("ativado", False))
            helpers.salvar_config({"ativado": novo})
            await self._update_panel(inter, "painel")

        # ── Abrir sub-painéis ─────────────────────────────────────────────────
        elif cid in ("TC_CanalRanking",):
            await self._update_panel(inter, "canal_ranking")
        elif cid in ("TC_CanalLog",):
            await self._update_panel(inter, "canal_log")
        elif cid == "TC_AbrirThresholds":
            await self._update_panel(inter, "thresholds")
        elif cid == "TC_AbrirFiltros":
            await self._update_panel(inter, "filtros")
        elif cid == "TC_PersonalizarRanking":
            await self._update_panel(inter, "personalizar")
        elif cid == "TC_VoltarPainel":
            await self._update_panel(inter, "painel")

        # ── Toggle Muted ──────────────────────────────────────────────────────
        elif cid == "TC_ToggleMuted":
            cfg = helpers.carregar_config()
            helpers.salvar_config({"contar_muted": not bool(cfg.get("contar_muted", False))})
            await self._update_panel(inter, "filtros")

        elif cid == "TC_ToggleDeafened":
            cfg = helpers.carregar_config()
            helpers.salvar_config({"contar_deafened": not bool(cfg.get("contar_deafened", False))})
            await self._update_panel(inter, "filtros")

        # ── Adicionar Threshold ───────────────────────────────────────────────
        elif cid == "TC_AdicionarThreshold":
            await inter.response.send_modal(ModalAdicionarThreshold())
            return

        # ── Editar Título e Cor ───────────────────────────────────────────────
        elif cid == "TC_EditarTituloRanking":
            await inter.response.send_modal(ModalEditarTituloRanking())
            return

        # ── Publicar Ranking Agora ────────────────────────────────────────────
        elif cid == "TC_PublicarRankingAgora":
            await inter.response.defer(ephemeral=True)
            cfg  = helpers.carregar_config()
            msg_id = await helpers.enviar_ou_editar_ranking(self.bot, inter.guild, cfg)
            if msg_id:
                canal_id = cfg.get("canal_ranking_id")
                await inter.followup.send(
                    f"{emoji.correct} Ranking publicado/atualizado em <#{canal_id}>!", ephemeral=True
                )
            else:
                await inter.followup.send(
                     f"{emoji.wrong} Não foi possível publicar o ranking. Verifique se o canal está configurado "
                    "e se o bot tem permissão de enviar mensagens.",
                    ephemeral=True,
                )
            return

        # ── Prévia do Ranking ─────────────────────────────────────────────────
        elif cid == "TC_PreviaRanking":
            await inter.response.defer(ephemeral=True)
            cfg  = helpers.carregar_config()
            modo = cfg.get("modo_envio", "v2")
            try:
                if modo == "embed":
                    embed = helpers.build_ranking_embed(inter.guild, cfg)
                    await inter.followup.send(embed=embed, ephemeral=True)
                else:
                    components = helpers.build_ranking_container(inter.guild, cfg)
                    await inter.followup.send(
                        components=components,
                        flags=disnake.MessageFlags(is_components_v2=True),
                        ephemeral=True,
                    )
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro na prévia: {e}", ephemeral=True)
            return

    @commands.Cog.listener("on_dropdown")
    async def TC_Dropdown_Listener(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id
        if not cid or not cid.startswith("TC_"):
            return

        values = inter.values or []

        if cid == "TC_SelectCanalRanking":
            canal = values[0] if values else None
            if canal:
                cid_val = canal.id if hasattr(canal, "id") else canal
                helpers.salvar_config({"canal_ranking_id": str(cid_val), "ranking_message_id": None})
            await self._update_panel(inter, "painel")

        elif cid == "TC_SelectCanalLog":
            if values:
                canal = values[0]
                cid_val = canal.id if hasattr(canal, "id") else canal
                helpers.salvar_config({"log_cargo_canal_id": str(cid_val)})
            else:
                helpers.salvar_config({"log_cargo_canal_id": None})
            await self._update_panel(inter, "painel")

        elif cid == "TC_RemoverThreshold":
            idx = int(values[0]) if values else None
            if idx is not None:
                cfg = helpers.carregar_config()
                thr = helpers.get_sorted_thresholds(cfg)
                if 0 <= idx < len(thr):
                    thr.pop(idx)
                    helpers.salvar_config({"thresholds": thr})
            await self._update_panel(inter, "thresholds")

        elif cid == "TC_SelectModoEnvio":
            helpers.salvar_config({"modo_envio": values[0], "ranking_message_id": None})
            await self._update_panel(inter, "personalizar")

        elif cid == "TC_SelectIntervalo":
            helpers.salvar_config({"ranking_intervalo_minutos": int(values[0])})
            await self._update_panel(inter, "personalizar")

        elif cid == "TC_SelectTopN":
            helpers.salvar_config({"ranking_top": int(values[0])})
            await self._update_panel(inter, "personalizar")

        elif cid == "TC_SelectExcluirCanais":
            ids = [str(v.id if hasattr(v, "id") else v) for v in values]
            helpers.salvar_config({"excluir_canais": ids})
            await self._update_panel(inter, "filtros")

        elif cid == "TC_SelectIncluirCanais":
            ids = [str(v.id if hasattr(v, "id") else v) for v in values]
            helpers.salvar_config({"incluir_apenas_canais": ids})
            await self._update_panel(inter, "filtros")

    # ── Roteador de painéis ───────────────────────────────────────────────────

    async def _update_panel(self, inter: disnake.Interaction, destino: str = "painel"):
        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if mode == "embed":
            # Embed só tem painel principal
            embed, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            if destino == "thresholds":
                comps = self.PainelThresholds()
            elif destino == "filtros":
                comps = self.PainelFiltros()
            elif destino == "personalizar":
                comps = self.PainelPersonalizarRanking()
            elif destino == "canal_ranking":
                comps = self.PainelCanalRanking()
            elif destino == "canal_log":
                comps = self.PainelCanalLog()
            else:
                comps = self.Painel()
            await inter.edit_original_message(content=None, components=comps)


# ══════════════════════════════════════════════════════════════════════════════
# Modais
# ══════════════════════════════════════════════════════════════════════════════

class ModalAdicionarThreshold(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Threshold de Cargo",
            custom_id="TC_ModalAdicionarThreshold",
            components=[
                disnake.ui.TextInput(
                    label="Tempo necessário",
                    custom_id="tempo",
                    placeholder="Ex: 24h  |  7d  |  2d12h  |  3600  (segundos puros)",
                    max_length=30,
                ),
                disnake.ui.TextInput(
                    label="ID do Cargo",
                    custom_id="cargo_id",
                    placeholder="Ex: 123456789012345678",
                    max_length=20,
                ),
                disnake.ui.TextInput(
                    label="Rótulo (opcional, aparece no log)",
                    custom_id="label",
                    placeholder="Ex: 24h em Call",
                    max_length=50,
                    required=False,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        tempo_raw = inter.text_values.get("tempo", "").strip()
        cargo_raw = inter.text_values.get("cargo_id", "").strip()
        label_raw = inter.text_values.get("label", "").strip()

        segundos = helpers.parse_tempo_input(tempo_raw)
        if not segundos:
            await inter.response.send_message(
                f"{emoji.wrong} Tempo inválido. Use formatos como `24h`, `7d`, `2d12h` ou `3600` (segundos).",
                ephemeral=True,
            )
            return

        if not cargo_raw.isdigit():
            await inter.response.send_message(f"{emoji.wrong} ID do cargo inválido.", ephemeral=True)
            return

        cargo_id = int(cargo_raw)
        role     = inter.guild.get_role(cargo_id)
        if not role:
            await inter.response.send_message(
                f"{emoji.wrong} Cargo `{cargo_id}` não encontrado no servidor.", ephemeral=True
            )
            return

        cfg = helpers.carregar_config()
        thr = list(cfg.get("thresholds", []))

        # Evita duplicata de cargo_id
        if any(str(t.get("cargo_id")) == str(cargo_id) for t in thr):
            await inter.response.send_message(
                f"{emoji.wrong} O cargo {role.mention} já está associado a um threshold.", ephemeral=True
            )
            return

        label_final = label_raw or helpers.format_seconds(segundos)
        thr.append({
            "segundos": segundos,
            "cargo_id": cargo_id,
            "label":    label_final,
        })
        helpers.salvar_config({"thresholds": thr})

        cog = inter.bot.get_cog("TempCallConfig")
        if cog:
            await cog._update_panel(inter, "thresholds")


class ModalEditarTituloRanking(disnake.ui.Modal):
    def __init__(self):
        cfg = helpers.carregar_config()
        super().__init__(
            title="Personalizar Ranking",
            custom_id="TC_ModalEditarTitulo",
            components=[
                disnake.ui.TextInput(
                    label="Título do Ranking",
                    custom_id="titulo",
                    placeholder="Ex: 🏆 Ranking de Voz",
                    value=str(cfg.get("ranking_titulo", "🏆 Ranking de Voz"))[:256],
                    max_length=100,
                ),
                disnake.ui.TextInput(
                    label="Subtítulo / Descrição (opcional)",
                    custom_id="subtitulo",
                    placeholder="Ex: Os membros com mais tempo em call.",
                    value=str(cfg.get("ranking_subtitulo", ""))[:256],
                    max_length=150,
                    required=False,
                    style=disnake.TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Cor do container/embed (hex, opcional)",
                    custom_id="cor",
                    placeholder="Ex: FF8C00  ou  #5865F2  (deixe vazio para cor primária)",
                    value=str(cfg.get("ranking_cor", "") or "")[:16],
                    max_length=10,
                    required=False,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        titulo    = inter.text_values.get("titulo", "").strip()
        subtitulo = inter.text_values.get("subtitulo", "").strip()
        cor_raw   = inter.text_values.get("cor", "").strip().lstrip("#")

        updates: dict = {}
        if titulo:
            updates["ranking_titulo"] = titulo
        if subtitulo is not None:
            updates["ranking_subtitulo"] = subtitulo

        if cor_raw:
            try:
                int(cor_raw, 16)
                updates["ranking_cor"] = cor_raw
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} Cor inválida. Use formato hex sem #, ex: `FF8C00`.", ephemeral=True
                )
                return
        else:
            updates["ranking_cor"] = None

        # Invalida msg existente para recriar com novo estilo
        updates["ranking_message_id"] = None
        helpers.salvar_config(updates)

        cog = inter.bot.get_cog("TempCallConfig")
        if cog:
            await cog._update_panel(inter, "personalizar")


def setup(bot: commands.Bot):
    bot.add_cog(TempCallConfig(bot))