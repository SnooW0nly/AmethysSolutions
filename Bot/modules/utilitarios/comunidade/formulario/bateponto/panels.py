"""
modules/utilitarios/comunidade/formulario/bateponto/panels.py

Todos os painéis de configuração para o sistema de Bate Ponto (modos components e embed).
"""
from __future__ import annotations

import disnake
from functions.emoji import emoji
from .helpers import (
    carregar_config, get_bateponto, get_colors,
    listar_batepontos_select, estilo_para_disnake,
)

# ─── Painel principal ─────────────────────────────────────────────────────────

def painel_principal_bp_components() -> list:
    config = carregar_config()
    sistemas = config.get("sistemas", {})
    total = len(sistemas)
    ativos = sum(1 for s in sistemas.values() if s.get("ativado"))
    primary_hex, ck = get_colors()

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                "-# Painel > Comunidade > **Sistema de Bate Ponto**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Gerencie a jornada de trabalho de sua staff com facilidade. "
                "Registre entrada, saída, pausas e gere relatórios automáticos."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.time} **Sistemas criados:** `{total}`\n"
                f"{emoji.on} **Sistemas ativos:** `{ativos}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Bate Ponto", emoji=emoji.plus,
                                  style=disnake.ButtonStyle.green, custom_id="BP_Criar"),
                disnake.ui.Button(label="Gerenciar", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.blurple, custom_id="BP_Gerenciar",
                                  disabled=total == 0),
                disnake.ui.Button(label="Ver Logs", emoji=emoji.receipt,
                                  style=disnake.ButtonStyle.grey, custom_id="BP_VerLogs",
                                  disabled=total == 0),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Form_VoltarPrincipal"),
        ),
    ]

def painel_principal_bp_embed() -> tuple[disnake.Embed, list]:
    config = carregar_config()
    sistemas = config.get("sistemas", {})
    total = len(sistemas)
    ativos = sum(1 for s in sistemas.values() if s.get("ativado"))
    primary_hex, _ = get_colors()

    embed = disnake.Embed(
        title="Sistema de Bate Ponto",
        description=(
            "Gerencie a jornada de trabalho de sua staff com facilidade. "
            "Registre entrada, saída, pausas e gere relatórios automáticos.\n\n"
            f"{emoji.time} **Sistemas criados:** `{total}`\n"
            f"{emoji.on} **Sistemas ativos:** `{ativos}`"
        ),
    )
    if primary_hex:
        embed.color = int(primary_hex.replace("#", ""), 16)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Bate Ponto", emoji=emoji.plus,
                              style=disnake.ButtonStyle.green, custom_id="BP_Criar"),
            disnake.ui.Button(label="Gerenciar", emoji=emoji.edit,
                              style=disnake.ButtonStyle.blurple, custom_id="BP_Gerenciar",
                              disabled=total == 0),
            disnake.ui.Button(label="Ver Logs", emoji=emoji.receipt,
                              style=disnake.ButtonStyle.grey, custom_id="BP_VerLogs",
                              disabled=total == 0),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Form_VoltarPrincipal"),
        ),
    ]
    return embed, components

# ─── Seletor de Bate Ponto ───────────────────────────────────────────────────

def painel_selecionar_bp_components(titulo: str, custom_id_select: str, custom_id_voltar: str = "BP_VoltarPrincipal") -> list:
    primary_hex, ck = get_colors()
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Bate Ponto > **{titulo}**"
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=custom_id_select,
                    placeholder="Selecione um sistema de bate-ponto...",
                    options=listar_batepontos_select(),
                )
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=custom_id_voltar),
        ),
    ]

def painel_selecionar_bp_embed(titulo: str, custom_id_select: str, custom_id_voltar: str = "BP_VoltarPrincipal") -> tuple[disnake.Embed, list]:
    primary_hex, _ = get_colors()
    embed = disnake.Embed(
        title=f"Bate Ponto > {titulo}",
        description="Selecione um sistema de bate-ponto na lista abaixo para continuar.",
    )
    if primary_hex:
        embed.color = int(primary_hex.replace("#", ""), 16)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=custom_id_select,
                placeholder="Selecione um sistema de bate-ponto...",
                options=listar_batepontos_select(),
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=custom_id_voltar),
        ),
    ]
    return embed, components

# ─── Editor principal do Bate Ponto ──────────────────────────────────────────

def _build_bp_status_info(bp: dict) -> str:
    ativado = bp.get("ativado", False)
    canal_painel = bp.get("canal_painel_id")
    canal_logs = bp.get("canal_logs_id")
    cargos_perm = bp.get("cargos_permitidos", [])
    cargos_noti = bp.get("cargos_notificar", [])

    canal_painel_str = f"<#{canal_painel}>" if canal_painel else "`Não definido`"
    canal_logs_str = f"<#{canal_logs}>" if canal_logs else "`Não definido`"
    cargos_perm_str = ", ".join(f"<@&{c}>" for c in cargos_perm) if cargos_perm else "`Todos`"
    cargos_noti_str = ", ".join(f"<@&{c}>" for c in cargos_noti) if cargos_noti else "`Nenhum`"

    return (
        f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativo' if ativado else 'Inativo'}`\n"
        f"{emoji.textc} **Canal do painel:** {canal_painel_str}\n"
        f"{emoji.receipt} **Canal de logs:** {canal_logs_str}\n"
        f"{emoji.role} **Cargos permitidos:** {cargos_perm_str}\n"
        f"{emoji.warn} **Notificar cargos:** {cargos_noti_str}\n"
    )

def painel_editor_bp_components(bp_id: str) -> list:
    bp = get_bateponto(bp_id)
    if not bp:
        return painel_principal_bp_components()

    primary_hex, ck = get_colors()
    nome = bp.get("nome", "Sem nome")
    status_info = _build_bp_status_info(bp)
    pode_publicar = bool(bp.get("canal_painel_id") and bp.get("canal_logs_id"))

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Bate Ponto > **{nome}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(status_info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", emoji=emoji.power, style=disnake.ButtonStyle.grey,
                                  custom_id=f"BP_Toggle:{bp_id}"),
                disnake.ui.Button(label="Aparência", emoji=emoji.colors, style=disnake.ButtonStyle.blurple,
                                  custom_id=f"BP_AbrirEditorAnunciar:{bp_id}"),
                disnake.ui.Button(label="Canais", emoji=emoji.textc, style=disnake.ButtonStyle.grey,
                                  custom_id=f"BP_PainelCanais:{bp_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Publicar", emoji=emoji.arrow, style=disnake.ButtonStyle.green,
                                  custom_id=f"BP_Publicar:{bp_id}", disabled=not pode_publicar),
                disnake.ui.Button(label="Resetar Tudo", emoji=emoji.time, style=disnake.ButtonStyle.grey,
                                  custom_id=f"BP_Resetar:{bp_id}"),
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id=f"BP_Apagar:{bp_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id=f"BP_SetCargosPermitidos:{bp_id}",
                    placeholder="Cargos permitidos para bater ponto...",
                    min_values=1, max_values=10,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id=f"BP_SetCargosNotificar:{bp_id}",
                    placeholder="Cargos para notificar nos logs...",
                    min_values=1, max_values=10,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Limpar Permissões", emoji=emoji.delete,
                                  style=disnake.ButtonStyle.grey, custom_id=f"BP_LimparCargosPermitidos:{bp_id}"),
                disnake.ui.Button(label="Limpar Notificações", emoji=emoji.delete,
                                  style=disnake.ButtonStyle.grey, custom_id=f"BP_LimparCargosNotificar:{bp_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="BP_Gerenciar"),
        ),
    ]

def painel_editor_bp_embed(bp_id: str) -> tuple[disnake.Embed, list]:
    bp = get_bateponto(bp_id)
    if not bp:
        return painel_principal_bp_embed()

    primary_hex, _ = get_colors()
    nome = bp.get("nome", "Sem nome")
    status_info = _build_bp_status_info(bp)
    pode_publicar = bool(bp.get("canal_painel_id") and bp.get("canal_logs_id"))

    embed = disnake.Embed(
        title=f"Bate Ponto > {nome}",
        description=status_info,
    )
    if primary_hex:
        embed.color = int(primary_hex.replace("#", ""), 16)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="", emoji=emoji.power, style=disnake.ButtonStyle.grey,
                              custom_id=f"BP_Toggle:{bp_id}"),
            disnake.ui.Button(label="Aparência", emoji=emoji.colors, style=disnake.ButtonStyle.blurple,
                              custom_id=f"BP_AbrirEditorAnunciar:{bp_id}"),
            disnake.ui.Button(label="Canais", emoji=emoji.textc, style=disnake.ButtonStyle.grey,
                              custom_id=f"BP_PainelCanais:{bp_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Publicar", emoji=emoji.arrow, style=disnake.ButtonStyle.green,
                              custom_id=f"BP_Publicar:{bp_id}", disabled=not pode_publicar),
            disnake.ui.Button(label="Resetar Tudo", emoji=emoji.time, style=disnake.ButtonStyle.grey,
                              custom_id=f"BP_Resetar:{bp_id}"),
            disnake.ui.Button(label="Apagar", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id=f"BP_Apagar:{bp_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                custom_id=f"BP_SetCargosPermitidos:{bp_id}",
                placeholder="Cargos permitidos para bater ponto...",
                min_values=1, max_values=10,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                custom_id=f"BP_SetCargosNotificar:{bp_id}",
                placeholder="Cargos para notificar nos logs...",
                min_values=1, max_values=10,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Limpar Permissões", emoji=emoji.delete,
                              style=disnake.ButtonStyle.grey, custom_id=f"BP_LimparCargosPermitidos:{bp_id}"),
            disnake.ui.Button(label="Limpar Notificações", emoji=emoji.delete,
                              style=disnake.ButtonStyle.grey, custom_id=f"BP_LimparCargosNotificar:{bp_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="BP_Gerenciar"),
        ),
    ]
    return embed, components

# ─── Painéis de Canais ───────────────────────────────────────────────────────

def painel_canais_bp_components(bp_id: str) -> list:
    bp = get_bateponto(bp_id)
    primary_hex, ck = get_colors()
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Bate Ponto > **Configurar Canais**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Selecione os canais para o painel de bater ponto e para os logs de registro."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id=f"BP_SetCanalPainel:{bp_id}",
                    placeholder="Selecione o canal do painel...",
                    channel_types=[disnake.ChannelType.text],
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id=f"BP_SetCanalLogs:{bp_id}",
                    placeholder="Selecione o canal de logs...",
                    channel_types=[disnake.ChannelType.text],
                )
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"BP_Editor:{bp_id}"),
        ),
    ]

def painel_canais_bp_embed(bp_id: str) -> tuple[disnake.Embed, list]:
    primary_hex, _ = get_colors()
    embed = disnake.Embed(
        title="Bate Ponto > Configurar Canais",
        description="Selecione os canais para o painel de bater ponto e para os logs de registro nos seletores abaixo.",
    )
    if primary_hex:
        embed.color = int(primary_hex.replace("#", ""), 16)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                custom_id=f"BP_SetCanalPainel:{bp_id}",
                placeholder="Selecione o canal do painel...",
                channel_types=[disnake.ChannelType.text],
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                custom_id=f"BP_SetCanalLogs:{bp_id}",
                placeholder="Selecione o canal de logs...",
                channel_types=[disnake.ChannelType.text],
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"BP_Editor:{bp_id}"),
        ),
    ]
    return embed, components
