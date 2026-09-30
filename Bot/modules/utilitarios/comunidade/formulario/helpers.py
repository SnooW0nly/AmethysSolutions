"""
modules/utilitarios/comunidade/formulario/helpers.py

Configuração, helpers de banco de dados e construtores de UI compartilhados.
"""
from __future__ import annotations

import uuid
import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY = "automations_formulario"

# ─── Tipos de campo disponíveis ───────────────────────────────────────────────

FIELD_TYPES = {
    "short":     {"label": "Texto Curto",     "emoji": emoji.edit,   "description": "Resposta em uma linha"},
    "paragraph": {"label": "Texto Longo",     "emoji": emoji.message,"description": "Resposta em múltiplas linhas"},
    "number":    {"label": "Número",          "emoji": emoji.time,   "description": "Apenas valores numéricos"},
    "email":     {"label": "E-mail",          "emoji": emoji.telegram,"description": "Formato email@dominio.com"},
    "url":       {"label": "URL / Link",      "emoji": emoji.route,  "description": "https://exemplo.com"},
    "choice":    {"label": "Escolha (Modal)", "emoji": emoji.pin,    "description": "Opções pré-definidas via modal"},
}

# Modos de envio de resposta
SEND_MODES = {
    "topic":   {"label": "Tópico Privado",    "emoji": emoji.dir,    "description": "Um tópico por resposta no canal"},
    "channel": {"label": "Canal de Respostas","emoji": emoji.textc,  "description": "Todas as respostas em um canal"},
    "dm":      {"label": "DM do Staff",       "emoji": emoji.member, "description": "Envia para cargos configurados"},
}

# Modos de exibição do formulário
DISPLAY_MODES = {
    "modal":   {"label": "Modal (Popup)",     "emoji": emoji.embed,  "description": "Abre um popup ao clicar no botão"},
    "channel": {"label": "Canal Dedicado",    "emoji": emoji.textc,  "description": "Canal de texto para perguntas"},
    "topic":   {"label": "Tópico Privado",    "emoji": emoji.dir,    "description": "Cria tópico privado para responder"},
}


# ─── Config ──────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("formularios", {})
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, data)


def criar_formulario(nome: str) -> str:
    """Cria um novo formulário e retorna seu ID."""
    config = carregar_config()
    form_id = str(uuid.uuid4())[:8]
    config["formularios"][form_id] = {
        "id": form_id,
        "nome": nome,
        "ativado": False,
        "display_mode": "modal",
        "send_mode": "channel",
        "canal_painel_id": None,
        "canal_respostas_id": None,
        "canal_topicos_id": None,
        "cargos_permitidos": [],
        "cargos_notificar": [],
        "requer_aprovacao": False,
        "anonimo": False,
        "limite_respostas": 0,
        "mensagem_sucesso": f"{emoji.correct} Sua resposta foi enviada com sucesso!",
        "embed_titulo": nome,
        "embed_descricao": f"Preencha o formulário **{nome}** clicando no botão abaixo.",
        "embed_cor": None,
        "botao_label": "Preencher Formulário",
        "botao_emoji": f"{emoji.edit}",
        "botao_estilo": "blurple",
        "campos": [],
        "message_id": None,
        "respostas_count": 0,
        "cargo_aprovacao_id": None,
        "msg_aprovado": f"{emoji.correct} Sua resposta ao formulário **{nome}** foi aprovada!",
        "msg_reprovado": f"{emoji.wrong} Sua resposta ao formulário **{nome}** foi reprovada.",
    }
    salvar_config(config)
    return form_id


def get_formulario(form_id: str) -> dict | None:
    config = carregar_config()
    return config.get("formularios", {}).get(form_id)


def salvar_formulario(form_id: str, data: dict) -> None:
    config = carregar_config()
    config["formularios"][form_id] = data
    salvar_config(config)


def deletar_formulario(form_id: str) -> None:
    config = carregar_config()
    config["formularios"].pop(form_id, None)
    salvar_config(config)


def criar_campo(
    tipo: str,
    label: str,
    placeholder: str = "",
    required: bool = True,
    opcoes: list[str] | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "tipo": tipo,
        "label": label,
        "placeholder": placeholder,
        "required": required,
        "opcoes": opcoes or [],
        "min_length": None,
        "max_length": None,
    }


# ─── UI helpers ───────────────────────────────────────────────────────────────

def accent(primary_hex: str | None) -> dict:
    if primary_hex:
        return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
    return {}


def color_int(primary_hex: str | None) -> int | None:
    if primary_hex:
        return int(primary_hex.replace("#", ""), 16)
    return None


def get_colors() -> tuple[str | None, dict]:
    primary_hex = db.get_document("custom_colors").get("primary")
    return primary_hex, accent(primary_hex)


def get_mode() -> str:
    return db.get_document("custom_mode").get("mode", "components")


def estilo_para_disnake(estilo: str) -> disnake.ButtonStyle:
    return {
        "green":   disnake.ButtonStyle.green,
        "red":     disnake.ButtonStyle.red,
        "gray":    disnake.ButtonStyle.gray,
        "grey":    disnake.ButtonStyle.gray,
        "blurple": disnake.ButtonStyle.blurple,
    }.get(estilo, disnake.ButtonStyle.blurple)


def build_formulario_embed(form: dict) -> disnake.Embed:
    """Monta o embed público do formulário."""
    primary_hex, _ = get_colors()
    cor = color_int(form.get("embed_cor") or primary_hex)
    embed = disnake.Embed(
        title=form.get("embed_titulo") or form["nome"],
        description=form.get("embed_descricao"),
        color=cor,
    )
    campos = form.get("campos", [])
    if campos:
        nomes = "\n".join(
            f"{'🔴' if c.get('required') else '🟡'} **{c['label']}** ({'obrigatório' if c.get('required') else 'opcional'}) - `{FIELD_TYPES.get(c['tipo'], {}).get('label', c['tipo'])}`"
            for c in campos
        )
        embed.add_field(name="Campos do formulário", value=nomes, inline=False)
    return embed


def build_formulario_components(form: dict) -> list[disnake.ui.ActionRow]:
    """Monta o(s) componente(s) públicos do formulário (botão)."""
    form_id = form["id"]
    estilo = estilo_para_disnake(form.get("botao_estilo", "blurple"))
    label = form.get("botao_label") or "Preencher Formulário"
    btn_emoji = form.get("botao_emoji")

    btn = disnake.ui.Button(
        label=label,
        emoji=btn_emoji,
        style=estilo,
        custom_id=f"Form_Responder:{form_id}",
        disabled=not form.get("ativado", False),
    )
    return [disnake.ui.ActionRow(btn)]


def listar_formularios_select(incluir_disabled: bool = False) -> list[disnake.SelectOption]:
    config = carregar_config()
    forms = config.get("formularios", {})
    options = []
    for fid, f in forms.items():
        status = f"{emoji.correct}" if f.get("ativado") else f"{emoji.wrong}"
        options.append(disnake.SelectOption(
            label=f.get("nome", "Sem nome")[:100],
            value=fid,
            description=f"{status} {DISPLAY_MODES.get(f.get('display_mode','modal'),{}).get('label','')}",
            emoji=emoji.embed,
        ))
    if not options:
        options.append(disnake.SelectOption(
            label="Nenhum formulário criado",
            value="__none__",
            emoji=emoji.wrong,
        ))
    return options