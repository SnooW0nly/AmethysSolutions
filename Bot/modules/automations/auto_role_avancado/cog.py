"""
modules/automations/auto_role_avancado/cog.py

Sistema de Auto Rolê Avançado — Amethys Bot

Gatilhos suportados:
  - Impulsos ao servidor
  - Total de mensagens enviadas
  - Tempo em call (minutos) — integra com TempCall
  - Dias no servidor
  - Convites válidos — integra com InviteTracker
  - Reações dadas
  - Possui determinado cargo

Fluxo de criação de regra (multi-step):
  1. Botão "Nova Regra" (emoji.plus) → seleção de tipo de gatilho
  2. Tipo selecionado → tela rica com RoleSelect para escolher o cargo a conceder
  3. Cargo selecionado → Modal com nome, threshold, opções avançadas
  4. Salvo → volta ao painel com a nova regra listada

Gerenciamento de regras:
  - "Ver Regras" → lista completa com select por regra
  - Selecionar regra → tela de detalhe com Editar / Ativar-Desativar / Remover
"""
from __future__ import annotations

import asyncio
import base64
from typing import Optional

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from . import helpers
from .helpers import (
    carregar_config, salvar_config,
    TIPOS_GATILHO,
    nova_regra, regra_por_id, remover_regra,
    resumo_regras,
    aplicar_regras_membro,
    incrementar_mensagens, incrementar_reacoes,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de UI
# ──────────────────────────────────────────────────────────────────────────────

def _accent(primary_hex: str | None) -> dict:
    if primary_hex:
        return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
    return {}


def _cor(primary_hex: str | None) -> Optional[disnake.Colour]:
    if primary_hex:
        return disnake.Colour(int(primary_hex.replace("#", ""), 16))
    return None


def _primary_hex() -> str | None:
    return db.get_document("custom_colors").get("primary")


def _mode() -> str:
    return db.get_document("custom_mode").get("mode", "components")


def _encode(text: str) -> str:
    """Codifica texto em base64 url-safe para uso em custom_ids."""
    return base64.urlsafe_b64encode(text.encode()).decode()


def _decode(text: str) -> str:
    """Decodifica base64 url-safe."""
    try:
        return base64.urlsafe_b64decode(text.encode()).decode()
    except Exception:
        return text


# ──────────────────────────────────────────────────────────────────────────────
# Informações ricas por tipo de gatilho
# ──────────────────────────────────────────────────────────────────────────────

_TIPO_INFO = {
    "impulsos": {
        "emoji":       "🚀",
        "titulo":      "Impulsos ao Servidor",
        "descricao":   "Concede cargo quando o membro impulsiona o servidor.",
        "exemplos":    "**Exemplos de uso:** 1 impulso → Apoiador · 2 → Super Apoiador · 14 → Nível Máximo",
        "valor_label": "Quantidade mínima de impulsos",
        "valor_hint":  "Ex: `1` · `2` · `7` · `14` (máximo por membro)",
        "unidade":     "impulso(s)",
    },
    "mensagens": {
        "emoji":       "💬",
        "titulo":      "Total de Mensagens",
        "descricao":   "Concede cargo conforme o membro acumula mensagens enviadas no servidor.",
        "exemplos":    "**Exemplos de uso:** 100 → Participante · 1.000 → Ativo · 10.000 → Lendário",
        "valor_label": "Mínimo de mensagens enviadas",
        "valor_hint":  "Ex: `100` · `500` · `1000` · `5000` · `10000`",
        "unidade":     "mensagem(s)",
    },
    "tempo_call": {
        "emoji":       "🎙️",
        "titulo":      "Tempo em Call",
        "descricao":   "Concede cargo pelo tempo acumulado em canais de voz. Integra com o sistema TempCall.",
        "exemplos":    "**Exemplos de uso:** 60 min (1h) → Sociável · 600 min (10h) → Habitué · 3000 min (50h) → Call Master",
        "valor_label": "Mínimo de minutos em call",
        "valor_hint":  "Ex: `60` (1h) · `300` (5h) · `600` (10h) · `3000` (50h)",
        "unidade":     "minuto(s)",
    },
    "tempo_servidor": {
        "emoji":       "📅",
        "titulo":      "Dias no Servidor",
        "descricao":   "Concede cargo pela antiguidade do membro no servidor.",
        "exemplos":    "**Exemplos de uso:** 7 dias → Novato · 30 → Membro · 90 → Veterano · 365 → Aniversariante",
        "valor_label": "Mínimo de dias no servidor",
        "valor_hint":  "Ex: `7` (1 sem) · `30` (1 mês) · `90` (3 meses) · `365` (1 ano)",
        "unidade":     "dia(s)",
    },
    "convites": {
        "emoji":       "✉️",
        "titulo":      "Convites Válidos",
        "descricao":   "Concede cargo pelo número de convites válidos. Integra com o InviteTracker.",
        "exemplos":    "**Exemplos de uso:** 1 → Recruta · 10 → Recrutador · 50 → Elite · 100 → Top Recruta",
        "valor_label": "Mínimo de convites válidos",
        "valor_hint":  "Ex: `1` · `5` · `10` · `25` · `50` · `100`",
        "unidade":     "convite(s)",
    },
    "reacoes": {
        "emoji":       "❤️",
        "titulo":      "Reações Dadas",
        "descricao":   "Concede cargo pelo total de reações que o membro adicionou em mensagens.",
        "exemplos":    "**Exemplos de uso:** 50 → Expressivo · 500 → Reagente Nato · 2000 → Emoji Master",
        "valor_label": "Mínimo de reações dadas",
        "valor_hint":  "Ex: `10` · `50` · `200` · `1000` · `5000`",
        "unidade":     "reação(ões)",
    },
    "cargos_possuidos": {
        "emoji":       "🎖️",
        "titulo":      "Possui Determinado Cargo",
        "descricao":   "Concede um cargo automaticamente ao membro que já possui outro cargo específico.",
        "exemplos":    "**Exemplos de uso:** Possui @Comprador → recebe @Acesso VIP · Possui @Staff → recebe @Gerenciador",
        "valor_label": "ID do cargo necessário (pré-requisito)",
        "valor_hint":  "Cole o ID do cargo que o membro precisa TER para receber o novo cargo",
        "unidade":     "cargo pré-requisito",
    },
}

_TIPO_DESCRICAO_CURTA = {
    "impulsos":         "Boosts dados ao servidor (1, 2, 7, 14...)",
    "mensagens":        "Total de msgs enviadas (100, 500, 1k, 5k...)",
    "tempo_call":       "Minutos acumulados em call de voz",
    "tempo_servidor":   "Dias desde que entrou no servidor",
    "convites":         "Convites válidos rastreados pelo bot",
    "reacoes":          "Total de reações adicionadas",
    "cargos_possuidos": "Concede cargo ao ter outro cargo específico",
}


# ──────────────────────────────────────────────────────────────────────────────
# Modal passo 3 — threshold + opções avançadas
# ──────────────────────────────────────────────────────────────────────────────

class ConfigurarRegraModal(disnake.ui.Modal):
    """
    Passo 3 do fluxo de criação.
    Recebe tipo e cargo_id via custom_id codificado.
    """

    def __init__(self, tipo: str, cargo_id: int):
        self.tipo     = tipo
        self.cargo_id = cargo_id
        info          = _TIPO_INFO.get(tipo, {})

        super().__init__(
            title=f"Nova Regra · {info.get('titulo', tipo)[:35]}",
            custom_id=f"ARA_ModalConfigurar:{_encode(tipo)}:{cargo_id}",
            components=[
                disnake.ui.TextInput(
                    label="Nome da regra",
                    placeholder="Ex: Impulsionador Nível 1 · Mensageiro Ativo · Call Master",
                    custom_id="nome",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label=info.get("valor_label", "Valor mínimo (threshold)"),
                    placeholder=info.get("valor_hint", "Ex: 100"),
                    custom_id="valor",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=20,
                ),
                disnake.ui.TextInput(
                    label="Remover cargo se condição for perdida?",
                    placeholder="sim · não  (padrão: não — sobrescreve a config global)",
                    custom_id="remover_ao_perder",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=3,
                ),
                disnake.ui.TextInput(
                    label="Observação interna (opcional)",
                    placeholder="Anotação livre para identificar esta regra no painel",
                    custom_id="descricao",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=200,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome        = inter.text_values["nome"].strip()
        valor_raw   = inter.text_values["valor"].strip()
        remover_raw = inter.text_values.get("remover_ao_perder", "").strip().lower()
        descricao   = inter.text_values.get("descricao", "").strip()
        remover     = remover_raw in ("sim", "s", "yes", "y", "1", "true")

        try:
            valor = int(valor_raw)
            if valor < 0:
                raise ValueError
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} O valor `{valor_raw}` deve ser um número inteiro positivo.",
                ephemeral=True,
            )
            return

        role = inter.guild.get_role(self.cargo_id)
        if not role:
            await inter.response.send_message(
                f"{emoji.wrong} Cargo com ID `{self.cargo_id}` não encontrado neste servidor.",
                ephemeral=True,
            )
            return

        config = carregar_config()
        regra  = nova_regra(nome=nome, tipo=self.tipo, cargo_id=self.cargo_id, valor=valor)
        regra["remover_ao_perder"] = remover
        if descricao:
            regra["descricao"] = descricao
        config["regras"].append(regra)
        salvar_config(config)

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter)
            emb, comps = AutoRoleAvancadoCog.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await message.wait(inter)
            await inter.edit_original_message(content=None, components=AutoRoleAvancadoCog.Painel())


class EditarRegraModal(disnake.ui.Modal):
    """Modal para editar uma regra existente."""

    def __init__(self, regra: dict):
        self.regra_id = regra["id"]
        info          = _TIPO_INFO.get(regra.get("tipo", ""), {})

        super().__init__(
            title=f"Editar · {regra.get('nome', regra['id'])[:38]}",
            custom_id=f"ARA_ModalEditar:{regra['id']}",
            components=[
                disnake.ui.TextInput(
                    label="Nome da regra",
                    custom_id="nome",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=50,
                    value=regra.get("nome", ""),
                ),
                disnake.ui.TextInput(
                    label=info.get("valor_label", "Valor mínimo (threshold)"),
                    placeholder=info.get("valor_hint", ""),
                    custom_id="valor",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=20,
                    value=str(regra.get("valor", "")),
                ),
                disnake.ui.TextInput(
                    label="Remover cargo se condição for perdida?",
                    placeholder="sim · não",
                    custom_id="remover_ao_perder",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=3,
                    value="sim" if regra.get("remover_ao_perder") else "não",
                ),
                disnake.ui.TextInput(
                    label="Observação interna (opcional)",
                    custom_id="descricao",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=200,
                    value=regra.get("descricao", ""),
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome        = inter.text_values["nome"].strip()
        valor_raw   = inter.text_values["valor"].strip()
        remover_raw = inter.text_values.get("remover_ao_perder", "não").strip().lower()
        descricao   = inter.text_values.get("descricao", "").strip()
        remover     = remover_raw in ("sim", "s", "yes", "y", "1", "true")

        try:
            valor = int(valor_raw)
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Valor inválido: `{valor_raw}`", ephemeral=True
            )
            return

        config = carregar_config()
        for r in config["regras"]:
            if r.get("id") == self.regra_id:
                r["nome"]              = nome
                r["valor"]             = valor
                r["remover_ao_perder"] = remover
                r["descricao"]         = descricao
                break
        salvar_config(config)

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter)
            emb, comps = AutoRoleAvancadoCog.PainelDetalheRegraEmbed(self.regra_id)
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await message.wait(inter)
            await inter.edit_original_message(
                content=None, components=AutoRoleAvancadoCog.PainelDetalheRegra(self.regra_id)
            )


class EditarConfigModal(disnake.ui.Modal):
    """Modal para editar configurações globais."""

    def __init__(self, config: dict):
        super().__init__(
            title="Configurações Globais",
            custom_id="ARA_ModalConfig",
            components=[
                disnake.ui.TextInput(
                    label="Remover cargo ao perder condição? (global)",
                    placeholder="sim = remove · não = mantém (cada regra pode sobrescrever)",
                    custom_id="remover_ao_perder",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value="sim" if config.get("remover_ao_perder", False) else "não",
                    max_length=3,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        remover_raw = inter.text_values.get("remover_ao_perder", "não").strip().lower()
        config      = carregar_config()
        config["remover_ao_perder"] = remover_raw in ("sim", "s", "yes", "y", "1", "true")
        salvar_config(config)

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter)
            emb, comps = AutoRoleAvancadoCog.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await message.wait(inter)
            await inter.edit_original_message(content=None, components=AutoRoleAvancadoCog.Painel())


# ──────────────────────────────────────────────────────────────────────────────
# Cog principal
# ──────────────────────────────────────────────────────────────────────────────

class AutoRoleAvancadoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ══════════════════════════════════════════════════════════════════════════
    # PAINEL PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def Painel() -> list:
        config     = carregar_config()
        ativado    = config.get("ativado", False)
        logs_on    = config.get("logs_ativados", False)
        logs_canal = config.get("canal_logs_id")
        remover    = config.get("remover_ao_perder", False)
        regras     = config.get("regras", [])
        primary    = _primary_hex()

        ativas   = sum(1 for r in regras if r.get("ativo", True))
        inativas = len(regras) - ativas

        resumo_status = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_on else emoji.off} **Logs:** `{'Ativado' if logs_on else 'Desativado'}`"
            + (f" — <#{logs_canal}>" if logs_canal else "") + "\n"
            f"{emoji.role} **Regras:** `{ativas}` ativa(s)"
            + (f" · `{inativas}` desativada(s)" if inativas else "") + "\n"
            f"{emoji.minus if remover else emoji.plus} **Remover cargo ao perder condição:** `{'Sim' if remover else 'Não'}`"
        )

        children = [
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                "-# Painel > Automações > **Auto Rolê Avançado**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Conceda cargos automaticamente com base em impulsos, mensagens, "
                "tempo em call, dias no servidor, convites e muito mais."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(resumo_status),
        ]

        # Preview compacto das regras
        if regras:
            children.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
            children.append(disnake.ui.TextDisplay(
                f"-# **Regras configuradas:**\n{resumo_regras(config, max_exibir=5)}"
            ))

        children += [
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativado" if ativado else "Desativado",
                    style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.grey,
                    emoji=emoji.power,
                    custom_id="ARA_Toggle",
                ),
                disnake.ui.Button(
                    label="Nova Regra",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.plus,
                    custom_id="ARA_AbrirTipoGatilho",
                    disabled=not ativado,
                ),
                disnake.ui.Button(
                    label=f"Regras ({len(regras)})" if regras else "Regras",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.search,
                    custom_id="ARA_VerRegras",
                    disabled=not regras,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Logs",
                    style=disnake.ButtonStyle.green if logs_on else disnake.ButtonStyle.grey,
                    emoji=emoji.power,
                    custom_id="ARA_ToggleLogs",
                ),
                disnake.ui.Button(
                    label="Canal de Logs",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.textc,
                    custom_id="ARA_ConfigCanalLogs",
                ),
                disnake.ui.Button(
                    label="Config. Globais",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="ARA_ConfigGlobal",
                ),
                disnake.ui.Button(
                    label="Varrer Membros",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.reload,
                    custom_id="ARA_VerificarTodos",
                    disabled=not ativado or not regras,
                ),
            ),
        ]

        return [
            disnake.ui.Container(*children, **_accent(primary)),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="VoltarAutomações",
                )
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        config     = carregar_config()
        ativado    = config.get("ativado", False)
        logs_on    = config.get("logs_ativados", False)
        logs_canal = config.get("canal_logs_id")
        remover    = config.get("remover_ao_perder", False)
        regras     = config.get("regras", [])
        primary    = _primary_hex()

        ativas   = sum(1 for r in regras if r.get("ativo", True))
        inativas = len(regras) - ativas

        embed = disnake.Embed(
            title="🎖️ Auto Rolê Avançado",
            description=(
                "Conceda cargos automaticamente com base em impulsos, mensagens, "
                "tempo em call, dias no servidor, convites e muito mais."
            ),
        )
        if primary:
            embed.color = _cor(primary)

        embed.add_field(
            name="Configurações",
            value=(
                f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
                f"{emoji.on if logs_on else emoji.off} **Logs:** `{'Ativado' if logs_on else 'Desativado'}`"
                + (f" — <#{logs_canal}>" if logs_canal else "") + "\n"
                f"{emoji.role} **Regras:** `{ativas}` ativa(s)"
                + (f" · `{inativas}` desativada(s)" if inativas else "") + "\n"
                f"{emoji.minus if remover else emoji.plus} **Remover ao perder:** `{'Sim' if remover else 'Não'}`"
            ),
            inline=False,
        )
        if regras:
            embed.add_field(name="Regras", value=resumo_regras(config, max_exibir=6), inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativado" if ativado else "Desativado",
                    style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.grey,
                    emoji=emoji.power,
                    custom_id="ARA_Toggle",
                ),
                disnake.ui.Button(
                    label="Nova Regra",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.plus,
                    custom_id="ARA_AbrirTipoGatilho",
                    disabled=not ativado,
                ),
                disnake.ui.Button(
                    label=f"Regras ({len(regras)})" if regras else "Regras",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.search,
                    custom_id="ARA_VerRegras",
                    disabled=not regras,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Logs",
                    style=disnake.ButtonStyle.green if logs_on else disnake.ButtonStyle.grey,
                    emoji=emoji.power,
                    custom_id="ARA_ToggleLogs",
                ),
                disnake.ui.Button(
                    label="Canal de Logs",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.textc,
                    custom_id="ARA_ConfigCanalLogs",
                ),
                disnake.ui.Button(
                    label="Config. Globais",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="ARA_ConfigGlobal",
                ),
                disnake.ui.Button(
                    label="Varrer Membros",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.reload,
                    custom_id="ARA_VerificarTodos",
                    disabled=not ativado or not regras,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="VoltarAutomações",
                )
            ),
        ]
        return embed, components

    # ══════════════════════════════════════════════════════════════════════════
    # PASSO 1 — Selecionar tipo de gatilho
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def PainelSelecionarTipoGatilho() -> list:
        primary = _primary_hex()
        opcoes  = [
            disnake.SelectOption(
                label=f"{info['emoji']} {info['titulo']}",
                value=key,
                description=_TIPO_DESCRICAO_CURTA.get(key, ""),
            )
            for key, info in _TIPO_INFO.items()
        ]
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    "-# Auto Rolê Avançado > **Nova Regra · Passo 1 de 3**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"### {emoji.plus} Escolha o tipo de gatilho\n"
                    "-# O gatilho é o evento que será verificado para conceder o cargo ao membro."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ARA_SelectTipoGatilho",
                        placeholder="Selecione o tipo de gatilho...",
                        options=opcoes,
                        min_values=1,
                        max_values=1,
                    )
                ),
                **_accent(primary),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Cancelar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VoltarPainel",
                )
            ),
        ]

    @staticmethod
    def PainelSelecionarTipoGatilhoEmbed() -> tuple[disnake.Embed, list]:
        primary = _primary_hex()
        opcoes  = [
            disnake.SelectOption(
                label=f"{info['emoji']} {info['titulo']}",
                value=key,
                description=_TIPO_DESCRICAO_CURTA.get(key, ""),
            )
            for key, info in _TIPO_INFO.items()
        ]
        embed = disnake.Embed(
            title="Nova Regra · Passo 1 de 3",
            description=(
                "Escolha o **tipo de gatilho** — o evento que será verificado para "
                "decidir se o membro deve receber o cargo."
            ),
        )
        if primary:
            embed.color = _cor(primary)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ARA_SelectTipoGatilho",
                    placeholder="Selecione o tipo de gatilho...",
                    options=opcoes,
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Cancelar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VoltarPainel",
                )
            ),
        ]
        return embed, components

    # ══════════════════════════════════════════════════════════════════════════
    # PASSO 2 — Selecionar cargo a conceder (RoleSelect)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def PainelConfigurarCargo(tipo: str) -> list:
        primary  = _primary_hex()
        info     = _TIPO_INFO.get(tipo, {})
        tipo_enc = _encode(tipo)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    "-# Auto Rolê Avançado > Nova Regra > **Passo 2 de 3**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"### {info.get('emoji', '🎖️')} {info.get('titulo', tipo)}\n"
                    f"{info.get('descricao', '')}\n\n"
                    f"{info.get('exemplos', '')}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "-# Selecione abaixo o **cargo que será concedido** ao membro quando atingir a condição:"
                ),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        custom_id=f"ARA_SelectCargoConceder:{tipo_enc}",
                        placeholder="Selecione o cargo a conceder...",
                        min_values=1,
                        max_values=1,
                    )
                ),
                **_accent(primary),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_AbrirTipoGatilho",
                ),
            ),
        ]

    @staticmethod
    def PainelConfigurarCargoEmbed(tipo: str) -> tuple[disnake.Embed, list]:
        primary  = _primary_hex()
        info     = _TIPO_INFO.get(tipo, {})
        tipo_enc = _encode(tipo)

        embed = disnake.Embed(
            title=f"Nova Regra · Passo 2 de 3",
            description=(
                f"**{info.get('emoji', '')} {info.get('titulo', tipo)}**\n\n"
                f"{info.get('descricao', '')}\n\n"
                f"{info.get('exemplos', '')}\n\n"
                f"**Selecione o cargo que será concedido ao membro:**"
            ),
        )
        if primary:
            embed.color = _cor(primary)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id=f"ARA_SelectCargoConceder:{tipo_enc}",
                    placeholder="Selecione o cargo a conceder...",
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_AbrirTipoGatilho",
                ),
            ),
        ]
        return embed, components

    # ══════════════════════════════════════════════════════════════════════════
    # GERENCIAR REGRAS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def PainelVerRegras() -> list:
        config  = carregar_config()
        regras  = config.get("regras", [])
        primary = _primary_hex()

        if not regras:
            return AutoRoleAvancadoCog.Painel()

        linhas = []
        for i, r in enumerate(regras, 1):
            ativo    = "🟢" if r.get("ativo", True) else "🔴"
            info     = _TIPO_INFO.get(r.get("tipo", ""), {})
            tipo_str = f"{info.get('emoji', '')} {info.get('titulo', r.get('tipo', '?'))}"
            cargo    = f"<@&{r['cargo_id']}>" if r.get("cargo_id") else "`?`"
            valor    = r.get("valor", "?")
            unidade  = info.get("unidade", "")
            nome     = r.get("nome", r.get("id", "?"))
            remove   = " ✂️" if r.get("remover_ao_perder") else ""
            obs      = f"\n  ╰ *{r['descricao']}*" if r.get("descricao") else ""
            linhas.append(
                f"{ativo} **{i}. {nome}**{remove}\n"
                f"  ╰ {tipo_str} ≥ **{valor}** {unidade} → {cargo}{obs}"
            )

        texto = "\n".join(linhas)

        opcoes = [
            disnake.SelectOption(
                label=f"{'✅' if r.get('ativo', True) else '❌'} {r.get('nome', r.get('id')[:12])}",
                value=r["id"],
                description=(
                    f"{_TIPO_INFO.get(r.get('tipo',''), {}).get('emoji','')} "
                    f"≥ {r.get('valor','?')} "
                    f"{_TIPO_INFO.get(r.get('tipo',''), {}).get('unidade','')} · clique p/ gerenciar"
                )[:100],
                emoji="⚙️",
            )
            for r in regras[:25]
        ]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Auto Rolê Avançado > **Regras ({len(regras)})**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(texto),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("-# Selecione uma regra para **editar, ativar/desativar ou remover**:"),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ARA_GerenciarRegra",
                        placeholder="Selecione uma regra para gerenciar...",
                        options=opcoes,
                        min_values=1,
                        max_values=1,
                    )
                ),
                **_accent(primary),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Nova Regra",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.plus,
                    custom_id="ARA_AbrirTipoGatilho",
                ),
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VoltarPainel",
                ),
            ),
        ]

    @staticmethod
    def PainelVerRegrasEmbed() -> tuple[disnake.Embed, list]:
        config  = carregar_config()
        regras  = config.get("regras", [])
        primary = _primary_hex()

        embed = disnake.Embed(title=f"Regras do Auto Rolê Avançado ({len(regras)})")
        if primary:
            embed.color = _cor(primary)
        embed.description = resumo_regras(config, max_exibir=10) or "`Nenhuma regra`"

        opcoes = [
            disnake.SelectOption(
                label=f"{'✅' if r.get('ativo', True) else '❌'} {r.get('nome', r.get('id')[:12])}",
                value=r["id"],
                description=(
                    f"{_TIPO_INFO.get(r.get('tipo',''), {}).get('emoji','')} "
                    f"≥ {r.get('valor','?')} "
                    f"{_TIPO_INFO.get(r.get('tipo',''), {}).get('unidade','')} · clique p/ gerenciar"
                )[:100],
                emoji="⚙️",
            )
            for r in regras[:25]
        ]

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ARA_GerenciarRegra",
                    placeholder="Selecione uma regra para gerenciar...",
                    options=opcoes,
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Nova Regra",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.plus,
                    custom_id="ARA_AbrirTipoGatilho",
                ),
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VoltarPainel",
                ),
            ),
        ]
        return embed, components

    @staticmethod
    def PainelDetalheRegra(regra_id: str) -> list:
        """Tela de detalhe de uma regra — Editar / Toggle / Remover."""
        config  = carregar_config()
        regra   = regra_por_id(config, regra_id)
        primary = _primary_hex()

        if not regra:
            return AutoRoleAvancadoCog.PainelVerRegras()

        info     = _TIPO_INFO.get(regra.get("tipo", ""), {})
        ativo    = regra.get("ativo", True)
        cargo    = f"<@&{regra['cargo_id']}>" if regra.get("cargo_id") else "`?`"
        unidade  = info.get("unidade", "")
        remover  = "✂️ Sim — cargo removido ao perder condição" if regra.get("remover_ao_perder") else "🔒 Não — cargo mantido mesmo sem a condição"
        obs      = regra.get("descricao") or "*Sem observação*"
        regra_enc = _encode(regra_id)

        detalhe = (
            f"### {info.get('emoji', '🎖️')} {regra.get('nome', regra_id)}\n"
            f"{emoji.on if ativo else emoji.off} **Status:** `{'Ativa' if ativo else 'Desativada'}`\n\n"
            f"**Gatilho:** {info.get('titulo', regra.get('tipo', '?'))}\n"
            f"**Threshold:** `{regra.get('valor', '?')}` {unidade}\n"
            f"**Cargo concedido:** {cargo}\n"
            f"**Remover ao perder:** {remover}\n\n"
            f"**Observação:** {obs}"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    "-# Auto Rolê Avançado > Regras > **Detalhe**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(detalhe),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id=f"ARA_EditarRegra:{regra_enc}",
                    ),
                    disnake.ui.Button(
                        label="Desativar" if ativo else "Ativar",
                        style=disnake.ButtonStyle.grey if ativo else disnake.ButtonStyle.green,
                        emoji=emoji.power,
                        custom_id=f"ARA_ToggleRegra:{regra_enc}",
                    ),
                    disnake.ui.Button(
                        label="Remover Regra",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.minus,
                        custom_id=f"ARA_RemoverRegra:{regra_enc}",
                    ),
                ),
                **_accent(primary),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar às Regras",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VerRegras",
                ),
            ),
        ]

    @staticmethod
    def PainelDetalheRegraEmbed(regra_id: str) -> tuple[disnake.Embed, list]:
        config  = carregar_config()
        regra   = regra_por_id(config, regra_id)
        primary = _primary_hex()

        if not regra:
            return AutoRoleAvancadoCog.PainelVerRegrasEmbed()

        info      = _TIPO_INFO.get(regra.get("tipo", ""), {})
        ativo     = regra.get("ativo", True)
        cargo     = f"<@&{regra['cargo_id']}>" if regra.get("cargo_id") else "`?`"
        unidade   = info.get("unidade", "")
        remover   = "✂️ Sim" if regra.get("remover_ao_perder") else "🔒 Não"
        obs       = regra.get("descricao") or "*Sem observação*"
        regra_enc = _encode(regra_id)

        embed = disnake.Embed(
            title=f"{info.get('emoji', '🎖️')} {regra.get('nome', regra_id)}",
            description=f"{emoji.on if ativo else emoji.off} **{'Ativa' if ativo else 'Desativada'}**",
        )
        if primary:
            embed.color = _cor(primary)
        embed.add_field(name="Gatilho",           value=info.get("titulo", regra.get("tipo", "?")), inline=True)
        embed.add_field(name="Threshold",         value=f"`{regra.get('valor','?')}` {unidade}",   inline=True)
        embed.add_field(name="Cargo Concedido",   value=cargo,                                      inline=True)
        embed.add_field(name="Remover ao Perder", value=remover,                                    inline=True)
        embed.add_field(name="Observação",        value=obs,                                        inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Editar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id=f"ARA_EditarRegra:{regra_enc}",
                ),
                disnake.ui.Button(
                    label="Desativar" if ativo else "Ativar",
                    style=disnake.ButtonStyle.grey if ativo else disnake.ButtonStyle.green,
                    emoji=emoji.power,
                    custom_id=f"ARA_ToggleRegra:{regra_enc}",
                ),
                disnake.ui.Button(
                    label="Remover Regra",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.minus,
                    custom_id=f"ARA_RemoverRegra:{regra_enc}",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar às Regras",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VerRegras",
                ),
            ),
        ]
        return embed, components

    # ══════════════════════════════════════════════════════════════════════════
    # RENDER HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _render_painel(self, inter: disnake.MessageInteraction):
        mode = _mode()
        if mode == "embed":
            emb, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(content=None, components=self.Painel())

    async def _render_regras(self, inter: disnake.MessageInteraction):
        mode = _mode()
        if mode == "embed":
            emb, comps = self.PainelVerRegrasEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(content=None, components=self.PainelVerRegras())

    async def _render_detalhe(self, inter: disnake.MessageInteraction, regra_id: str):
        mode = _mode()
        if mode == "embed":
            emb, comps = self.PainelDetalheRegraEmbed(regra_id)
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(
                content=None, components=self.PainelDetalheRegra(regra_id)
            )

    # ══════════════════════════════════════════════════════════════════════════
    # BUTTON LISTENER
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def _ara_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("ARA_"):
            return

        # ── Abre modal direto (sem defer/wait) ────────────────────────────────
        if cid == "ARA_ConfigGlobal":
            await inter.response.send_modal(EditarConfigModal(carregar_config()))
            return

        if cid.startswith("ARA_EditarRegra:"):
            regra_id = _decode(cid.split(":", 1)[1])
            regra    = regra_por_id(carregar_config(), regra_id)
            if regra:
                await inter.response.send_modal(EditarRegraModal(regra))
            return

        # ── Com wait ─────────────────────────────────────────────────────────
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "ARA_VoltarPainel":
            await self._render_painel(inter)

        elif cid == "ARA_VerRegras":
            await self._render_regras(inter)

        elif cid == "ARA_Toggle":
            config = carregar_config()
            config["ativado"] = not config.get("ativado", False)
            salvar_config(config)
            await self._render_painel(inter)

        elif cid == "ARA_ToggleLogs":
            config = carregar_config()
            config["logs_ativados"] = not config.get("logs_ativados", False)
            salvar_config(config)
            await self._render_painel(inter)

        elif cid == "ARA_AbrirTipoGatilho":
            if mode == "embed":
                emb, comps = self.PainelSelecionarTipoGatilhoEmbed()
                await inter.edit_original_message(content=None, embed=emb, components=comps)
            else:
                await inter.edit_original_message(
                    content=None, components=self.PainelSelecionarTipoGatilho()
                )

        elif cid == "ARA_ConfigCanalLogs":
            primary    = _primary_hex()
            select_row = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="ARA_SelectCanalLogs",
                    placeholder="Selecione o canal de logs...",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="ARA_VoltarPainel",
                )
            )
            if mode == "embed":
                emb = disnake.Embed(
                    title="Canal de Logs",
                    description="Selecione o canal onde serão enviados os logs de concessão de cargos.",
                )
                if primary:
                    emb.color = _cor(primary)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(content=None, components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Auto Rolê Avançado > **Canal de Logs**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            "Selecione o canal onde serão enviados os logs de concessão de cargos.\n"
                            "-# Os logs mostram qual membro recebeu qual cargo e por qual regra."
                        ),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **_accent(primary),
                    ),
                    voltar,
                ])

        elif cid.startswith("ARA_ToggleRegra:"):
            regra_id = _decode(cid.split(":", 1)[1])
            config   = carregar_config()
            for r in config["regras"]:
                if r.get("id") == regra_id:
                    r["ativo"] = not r.get("ativo", True)
                    break
            salvar_config(config)
            await self._render_detalhe(inter, regra_id)

        elif cid.startswith("ARA_RemoverRegra:"):
            regra_id = _decode(cid.split(":", 1)[1])
            config   = carregar_config()
            if remover_regra(config, regra_id):
                salvar_config(config)
            await self._render_regras(inter)

        elif cid == "ARA_VerificarTodos":
            await inter.followup.send(
                f"{emoji.clock} Verificando todos os membros em segundo plano... Isso pode levar alguns instantes.",
                ephemeral=True,
            )
            asyncio.create_task(self._verificar_todos_membros(inter.guild))

    # ══════════════════════════════════════════════════════════════════════════
    # DROPDOWN LISTENER
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def _ara_dropdown_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("ARA_"):
            return

        # ── Passo 1 → 2: tipo selecionado, mostrar RoleSelect ─────────────────
        if cid == "ARA_SelectTipoGatilho":
            tipo = inter.values[0]
            mode = _mode()
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                emb, comps = self.PainelConfigurarCargoEmbed(tipo)
                await inter.edit_original_message(content=None, embed=emb, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(
                    content=None, components=self.PainelConfigurarCargo(tipo)
                )
            return

        # ── Passo 2 → 3: cargo selecionado, abrir modal ───────────────────────
        if cid.startswith("ARA_SelectCargoConceder:"):
            tipo_enc = cid.split(":", 1)[1]
            tipo     = _decode(tipo_enc)
            try:
                cargo_id = int(inter.values[0])
            except (ValueError, IndexError):
                await inter.response.send_message(
                    f"{emoji.wrong} Cargo inválido.", ephemeral=True
                )
                return
            await inter.response.send_modal(ConfigurarRegraModal(tipo, cargo_id))
            return

        # ── Com wait ─────────────────────────────────────────────────────────
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "ARA_SelectCanalLogs":
            config = carregar_config()
            config["canal_logs_id"] = str(inter.values[0])
            config["logs_ativados"] = True
            salvar_config(config)
            await self._render_painel(inter)

        elif cid == "ARA_GerenciarRegra":
            await self._render_detalhe(inter, inter.values[0])

    # ══════════════════════════════════════════════════════════════════════════
    # VERIFICAÇÃO EM MASSA
    # ══════════════════════════════════════════════════════════════════════════

    async def _verificar_todos_membros(self, guild: disnake.Guild):
        config = carregar_config()
        if not config.get("ativado", False):
            return
        for membro in guild.members:
            if membro.bot:
                continue
            try:
                await aplicar_regras_membro(membro, self.bot)
                await asyncio.sleep(0.3)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENERS DE EVENTOS
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_message")
    async def _ara_on_message(self, message_obj: disnake.Message):
        if message_obj.author.bot or not message_obj.guild:
            return
        config = carregar_config()
        if not config.get("ativado", False):
            return
        if not helpers.regras_por_tipo(config, "mensagens"):
            return
        incrementar_mensagens(message_obj.guild.id, message_obj.author.id)
        member = message_obj.author
        if not isinstance(member, disnake.Member):
            return
        asyncio.create_task(
            aplicar_regras_membro(member, self.bot, tipos_verificar=["mensagens"])
        )

    @commands.Cog.listener("on_reaction_add")
    async def _ara_on_reaction(self, reaction: disnake.Reaction, user: disnake.User):
        if user.bot or not reaction.message.guild:
            return
        config = carregar_config()
        if not config.get("ativado", False):
            return
        if not helpers.regras_por_tipo(config, "reacoes"):
            return
        incrementar_reacoes(reaction.message.guild.id, user.id)
        member = reaction.message.guild.get_member(user.id)
        if not member:
            return
        asyncio.create_task(
            aplicar_regras_membro(member, self.bot, tipos_verificar=["reacoes"])
        )

    @commands.Cog.listener("on_member_update")
    async def _ara_on_member_update(self, before: disnake.Member, after: disnake.Member):
        config = carregar_config()
        if not config.get("ativado", False):
            return
        tipos = []
        if before.premium_since != after.premium_since:
            tipos.append("impulsos")
        if set(after.roles) - set(before.roles):
            tipos.append("cargos_possuidos")
        if tipos:
            asyncio.create_task(
                aplicar_regras_membro(after, self.bot, tipos_verificar=tipos)
            )

    @commands.Cog.listener("on_member_join")
    async def _ara_on_join(self, member: disnake.Member):
        if member.bot:
            return
        config = carregar_config()
        if not config.get("ativado", False):
            return
        asyncio.create_task(
            aplicar_regras_membro(member, self.bot, tipos_verificar=["tempo_servidor"])
        )

    @commands.Cog.listener("on_voice_state_update")
    async def _ara_on_voice(
        self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState
    ):
        if member.bot:
            return
        config = carregar_config()
        if not config.get("ativado", False):
            return
        if not helpers.regras_por_tipo(config, "tempo_call"):
            return
        asyncio.create_task(
            aplicar_regras_membro(member, self.bot, tipos_verificar=["tempo_call"])
        )


def setup(bot: commands.Bot):
    bot.add_cog(AutoRoleAvancadoCog(bot))