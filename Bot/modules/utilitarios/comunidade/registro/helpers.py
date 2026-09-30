"""
modules/utilitarios/comunidade/registro/helpers.py
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY = "comunidade_registro"
_DB_PATH = "database/utilitarios/comunidade/registro"
REGISTRADORES_JSON = f"{_DB_PATH}/registradores.json"

BUTTON_STYLE_MAP = {
    "gray":  disnake.ButtonStyle.gray,
    "grey":  disnake.ButtonStyle.gray,
    "green": disnake.ButtonStyle.green,
    "red":   disnake.ButtonStyle.red,
    "blue":  disnake.ButtonStyle.blurple,
}


# ─── JSON ─────────────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("modo", "manual")
    dados.setdefault("cargo_registrador", None)
    dados.setdefault("cargo_lider", None)
    dados.setdefault("canal_logs", None)
    dados.setdefault("paginas", {
        "1": {"cargos": []},
        "2": {"cargos": []},
        "3": {"cargos": []},
        "4": {"cargos": []},
        "5": {"cargos": []},
    })
    dados.setdefault("cargo_remover", [])
    dados.setdefault("cargo_adicionar", [])
    # Mensagem — mesmo formato do MsgAuto editor_data
    dados.setdefault("mensagem", {})
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, {}, data)


# ─── Log JSON ─────────────────────────────────────────────────────────────────

def registrar_log(
    registrador_id: int,
    registrador_nome: str,
    registrado_id: int,
    registrado_nome: str,
    cargos_recebidos: list[int],
):
    os.makedirs(_DB_PATH, exist_ok=True)
    dados = load_json(REGISTRADORES_JSON)
    rid = str(registrador_id)
    if rid not in dados:
        dados[rid] = {"nome": registrador_nome, "total": 0, "registrados": []}
    dados[rid]["nome"] = registrador_nome
    dados[rid]["total"] = dados[rid].get("total", 0) + 1
    dados[rid].setdefault("registrados", []).append({
        "id": registrado_id,
        "nome": registrado_nome,
        "cargos": cargos_recebidos,
    })
    save_json(REGISTRADORES_JSON, dados)


# ─── UI helpers ───────────────────────────────────────────────────────────────

def accent() -> dict:
    h = (db.get_document("custom_colors") or {}).get("primary")
    if h:
        return {"accent_colour": disnake.Colour(int(h.replace("#", ""), 16))}
    return {}


def get_color() -> Optional[disnake.Colour]:
    h = (db.get_document("custom_colors") or {}).get("primary")
    return disnake.Colour(int(h.replace("#", ""), 16)) if h else None


def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


# ─── Builder do painel de registro (enviado ao usuário) ───────────────────────

def build_registro_components(
    config: dict,
    pagina_atual: int,
    cargos_selecionados: dict,
    guild: disnake.Guild,
    registrado_id: Optional[int] = None,
    registrador_id: Optional[int] = None,
) -> list:
    paginas = config.get("paginas", {})
    # páginas com cargos
    pags_com_cargos = [int(k) for k in sorted(paginas.keys()) if paginas[k].get("cargos")]
    total_paginas = len(pags_com_cargos) if pags_com_cargos else 1

    pagina_cfg = paginas.get(str(pagina_atual), {})
    cargos_ids = pagina_cfg.get("cargos", [])

    is_manual = config.get("modo") == "manual"

    if is_manual and registrado_id:
        header_txt = f"### Registrando <@{registrado_id}>\n-# Página {pagina_atual} de {total_paginas}"
    else:
        header_txt = f"### Registro\n-# Página {pagina_atual} de {total_paginas}"

    # Botões de cargo
    cargo_buttons = []
    selected_on_page = cargos_selecionados.get(pagina_atual, [])
    for cargo_id in cargos_ids:
        role = guild.get_role(int(cargo_id))
        if not role:
            continue
        is_sel = int(cargo_id) in selected_on_page
        cargo_buttons.append(
            disnake.ui.Button(
                label=role.name,
                style=disnake.ButtonStyle.green if is_sel else disnake.ButtonStyle.gray,
                custom_id=f"Registro_ToggleCargo:{pagina_atual}:{cargo_id}",
                emoji=emoji.correct if is_sel else None,
            )
        )

    cargo_rows = []
    for i in range(0, len(cargo_buttons), 5):
        cargo_rows.append(disnake.ui.ActionRow(*cargo_buttons[i:i + 5]))

    # Navegação
    nav = []
    if is_manual:
        nav.append(disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.red, custom_id="Registro_Cancelar", emoji=emoji.wrong))
    if pagina_atual > 1:
        nav.append(disnake.ui.Button(label="← Anterior", style=disnake.ButtonStyle.gray, custom_id=f"Registro_PagAnterior:{pagina_atual}"))

    proxima = pagina_atual + 1
    proxima_tem_cargos = bool(paginas.get(str(proxima), {}).get("cargos")) and proxima <= 5
    if proxima_tem_cargos:
        nav.append(disnake.ui.Button(label="Próxima →", style=disnake.ButtonStyle.blurple, custom_id=f"Registro_ProxPagina:{pagina_atual}"))
    else:
        nav.append(disnake.ui.Button(label="Finalizar ✓", style=disnake.ButtonStyle.green, custom_id="Registro_Finalizar", emoji=emoji.correct))

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(header_txt),
            disnake.ui.Separator(),
            *cargo_rows,
            disnake.ui.Separator(),
            disnake.ui.ActionRow(*nav),
            **accent(),
        )
    ]