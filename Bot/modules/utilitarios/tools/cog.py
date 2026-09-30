"""
cog.py — Módulo Tools (reformulado)
Correção: Builder.build_from_cfg é async → deve ser awaited.
Novo:     sistema de painéis customizáveis (criar / editar / publicar por canal).
"""

import re
import uuid
import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from . import paineis
from .functions import api

# ── imports do builder de mensagem (igual ao MensagemAuto) ────────────────────
from commands.admin.anunciar.builder import Builder
from commands.admin.anunciar.components.helper import Helper as AnunciarHelper
# ─────────────────────────────────────────────────────────────────────────────

TOOLS_DB_KEY      = "tools_config"
TOOLS_SESSION_KEY = "tools_sessions"

PLAN_RANK = {"free": 0, "booster": 1, "scarlet": 2}

V2_FLAGS = disnake.MessageFlags(is_components_v2=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de config / sessão
# ══════════════════════════════════════════════════════════════════════════════

def _get_config() -> dict:
    return db.get_document(TOOLS_DB_KEY) or {}


def _save_config(partial: dict):
    atual = _get_config()
    atual.update(partial)
    db.save_document(TOOLS_DB_KEY, atual)


def _get_msg_cfg() -> dict:
    return _get_config().get("mensagem", {}) or {}


def _save_msg_cfg(msg: dict):
    config = _get_config()
    config["mensagem"] = msg
    db.save_document(TOOLS_DB_KEY, config)


def _detect_plan(member: disnake.Member) -> str | None:
    config = _get_config()
    cargos = config.get("cargos", {})
    role_plan_map: dict[int, str] = {}
    for plano, cargo_id in cargos.items():
        try:
            role_plan_map[int(cargo_id)] = plano
        except (ValueError, TypeError):
            pass
    melhor_plano, melhor_rank = None, -1
    for role in member.roles:
        plano = role_plan_map.get(role.id)
        if plano and PLAN_RANK.get(plano, -1) > melhor_rank:
            melhor_plano = plano
            melhor_rank = PLAN_RANK[plano]
    return melhor_plano


def _member_has_painel_access(member: disnake.Member, painel_data: dict) -> bool:
    """Verifica se o membro tem o cargo configurado no painel para acessá-lo."""
    cargo_id = painel_data.get("cargo_id")
    if not cargo_id:
        # Sem cargo configurado, usa plano_min via _detect_plan
        plano = _detect_plan(member)
        if not plano:
            return False
        rank = PLAN_RANK.get(plano, -1)
        plano_min = painel_data.get("plano_min", "free")
        return rank >= PLAN_RANK.get(plano_min, 0)
    try:
        cid = int(cargo_id)
    except (ValueError, TypeError):
        return False
    return any(r.id == cid for r in member.roles)


def _get_paineis_para_plano(plano: str, member: disnake.Member | None = None) -> list[tuple[str, dict]]:
    """Retorna [(id, data)] dos painéis acessíveis pelo membro."""
    rank = PLAN_RANK.get(plano, 0)
    config = _get_config()
    resultado = []
    for pid, pdata in config.get("paineis", {}).items():
        cargo_id = pdata.get("cargo_id")
        if cargo_id and member:
            try:
                cid = int(cargo_id)
                if any(r.id == cid for r in member.roles):
                    resultado.append((pid, pdata))
            except (ValueError, TypeError):
                pass
        else:
            plano_min = pdata.get("plano_min", "free")
            if rank >= PLAN_RANK.get(plano_min, 0):
                resultado.append((pid, pdata))
    return resultado


def _get_session(user_id: str) -> dict | None:
    sessions = db.get_document(TOOLS_SESSION_KEY) or {}
    return sessions.get(str(user_id))


def _save_session(user_id: str, token: str, plano: str):
    sessions = db.get_document(TOOLS_SESSION_KEY) or {}
    sessions[str(user_id)] = {"token": token, "plano": plano}
    db.save_document(TOOLS_SESSION_KEY, sessions)


def _delete_session(user_id: str):
    sessions = db.get_document(TOOLS_SESSION_KEY) or {}
    sessions.pop(str(user_id), None)
    db.save_document(TOOLS_SESSION_KEY, sessions)


def _parse_dm_input(value: str) -> tuple[str | None, str | None]:
    value = value.strip()
    if value.lower().startswith("c:"):
        return None, value[2:].strip()
    return value, None


def _painel_get(painel_id: str) -> dict | None:
    return _get_config().get("paineis", {}).get(painel_id)


def _painel_save(painel_id: str, painel_data: dict):
    config = _get_config()
    config.setdefault("paineis", {})[painel_id] = painel_data
    db.save_document(TOOLS_DB_KEY, config)


def _painel_delete(painel_id: str):
    config = _get_config()
    config.get("paineis", {}).pop(painel_id, None)
    db.save_document(TOOLS_DB_KEY, config)


# ══════════════════════════════════════════════════════════════════════════════
# Builder de mensagem (corrigido: await)
# ══════════════════════════════════════════════════════════════════════════════

async def _build_msg(msg_data: dict, botao_cfg: dict, btn_custom_id: str = "Tools_VerificarAcesso") -> dict:
    """
    Constrói a mensagem usando o Builder do anunciar.
    CORRIGIDO: Builder.build_from_cfg é async → await obrigatório.
    """
    built = await Builder.build_from_cfg({"message": dict(msg_data)})

    label     = botao_cfg.get("label") or "Verificar Plano"
    emoji_raw = botao_cfg.get("emoji") or None

    btn_emoji = None
    if emoji_raw:
        m = re.match(r"<a?:(\w+):(\d+)>", emoji_raw)
        btn_emoji = disnake.PartialEmoji(name=m.group(1), id=int(m.group(2))) if m else emoji_raw

    access_btn = disnake.ui.Button(
        label=label,
        style=disnake.ButtonStyle.blurple,
        custom_id=btn_custom_id,
        emoji=btn_emoji,
    )

    if built.get("mode") == "v2":
        built["components"] = list(built.get("components", [])) + [disnake.ui.ActionRow(access_btn)]
    else:
        existing = list(built.get("components") or [])
        existing.append(disnake.ui.ActionRow(access_btn))
        built["components"] = existing

    return built


async def _send_built(channel: disnake.TextChannel, built: dict) -> disnake.Message:
    if built.get("mode") == "v2":
        return await channel.send(
            components=built["components"],
            flags=built["flags"],
            allowed_mentions=disnake.AllowedMentions.none(),
        )
    return await channel.send(
        content=built.get("content"),
        embed=built.get("embed"),
        components=built.get("components") or None,
        files=built.get("files") or None,
        allowed_mentions=disnake.AllowedMentions.none(),
    )


async def _edit_built(message: disnake.Message, built: dict):
    if built.get("mode") == "v2":
        await message.edit(
            components=built["components"],
            flags=built["flags"],
            allowed_mentions=disnake.AllowedMentions.none(),
        )
    else:
        await message.edit(
            content=built.get("content"),
            embed=built.get("embed"),
            components=built.get("components") or None,
            allowed_mentions=disnake.AllowedMentions.none(),
        )


# ══════════════════════════════════════════════════════════════════════════════
# Modals
# ══════════════════════════════════════════════════════════════════════════════

class CargoModal(disnake.ui.Modal):
    def __init__(self, plano: str):
        self.plano = plano
        super().__init__(
            title=f"Configurar Cargo — {plano.capitalize()}",
            custom_id=f"Tools_CargoModal:{plano}",
            components=[
                disnake.ui.TextInput(
                    label=f"ID do Cargo ({plano.capitalize()})",
                    custom_id="cargo_id",
                    placeholder="Cole aqui o ID do cargo",
                    style=disnake.TextInputStyle.short,
                    max_length=30,
                    required=True
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cargo_id = inter.text_values["cargo_id"].strip()
        config   = _get_config()
        cargos   = config.get("cargos", {})
        cargos[self.plano] = cargo_id
        _save_config({"cargos": cargos})
        await inter.response.edit_message(
            content=None,
            components=paineis.get_tools_cargos(_get_config()),
            flags=V2_FLAGS
        )


class BotaoModal(disnake.ui.Modal):
    def __init__(self, config: dict):
        botao = config.get("botao", {})
        super().__init__(
            title="Personalizar Botão",
            custom_id="Tools_BotaoModal",
            components=[
                disnake.ui.TextInput(
                    label="Label do Botão",
                    custom_id="label",
                    placeholder="Ex: Verificar Plano",
                    style=disnake.TextInputStyle.short,
                    max_length=80,
                    required=True,
                    value=botao.get("label", "Verificar Plano")
                ),
                disnake.ui.TextInput(
                    label="Emoji do Botão (Opcional)",
                    custom_id="emoji_val",
                    placeholder="Ex: ✅ ou <:nome:id>",
                    style=disnake.TextInputStyle.short,
                    max_length=100,
                    required=False,
                    value=botao.get("emoji", "")
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        label     = inter.text_values["label"].strip()
        emoji_raw = inter.text_values["emoji_val"].strip() or None
        _save_config({"botao": {"label": label, "emoji": emoji_raw}})
        await inter.response.edit_message(
            content=None,
            components=paineis.get_tools_botao(_get_config()),
            flags=V2_FLAGS
        )


class LoginModal(disnake.ui.Modal):
    def __init__(self, plano: str):
        self.plano = plano
        super().__init__(
            title="Login",
            custom_id=f"Tools_LoginModal:{plano}",
            components=[
                disnake.ui.TextInput(
                    label="Token do Discord",
                    placeholder="Cole seu token aqui",
                    custom_id="token",
                    style=disnake.TextInputStyle.paragraph,
                    max_length=100,
                    required=True
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        token = inter.text_values["token"].strip()
        uid   = str(inter.author.id)

        await inter.response.defer(with_message=False)
        try:
            await api.login(uid, token, self.plano)
            _save_session(uid, token, self.plano)
            paineis_disp = _get_paineis_para_plano(self.plano, inter.author)
            await inter.edit_original_response(
                content=None,
                components=paineis.get_acesso_verificado(self.plano, paineis_disp),
                flags=V2_FLAGS
            )
        except Exception as e:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, str(e), "Tools_BackLogin"),
                flags=V2_FLAGS
            )


class AddStatusModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Status",
            custom_id="Tools_AddStatusModal",
            components=[
                disnake.ui.TextInput(label="Texto do status",       custom_id="text",      style=disnake.TextInputStyle.short,     max_length=128, required=True),
                disnake.ui.TextInput(label="Emoji (opcional)",      custom_id="emoji_val", style=disnake.TextInputStyle.short,     max_length=100, required=False),
                disnake.ui.TextInput(label="Delay em milissegundos",custom_id="delay",     style=disnake.TextInputStyle.short,     max_length=8,   required=False, placeholder="Ex: 5000 (mínimo: 1000)"),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        text      = inter.text_values["text"].strip()
        emoji_val = inter.text_values["emoji_val"].strip() or None
        raw_delay = inter.text_values["delay"].strip()
        delay     = max(1000, int(raw_delay)) if raw_delay.isdigit() else 5000

        await inter.response.defer(with_message=False)
        try:
            result   = await api.add_status(str(inter.author.id), text, emoji_val, delay)
            statuses = result.get("statuses", []) if result else []
            await inter.edit_original_response(
                content=None,
                components=paineis.get_status_config(statuses),
                flags=V2_FLAGS
            )
        except Exception as e:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, str(e), "Tools_BackStatusConfig"),
                flags=V2_FLAGS
            )


class EditStatusModal(disnake.ui.Modal):
    def __init__(self, index: int, current: dict):
        self.index = index
        super().__init__(
            title=f"Editar Status #{index + 1}",
            custom_id=f"Tools_EditStatusModal:{index}",
            components=[
                disnake.ui.TextInput(label="Texto do status",  custom_id="text",      style=disnake.TextInputStyle.short, max_length=128, required=True,  value=current.get("text", "")),
                disnake.ui.TextInput(label="Emoji (opcional)", custom_id="emoji_val", style=disnake.TextInputStyle.short, max_length=100, required=False, value=current.get("emoji", "") or ""),
                disnake.ui.TextInput(label="Delay em ms",      custom_id="delay",     style=disnake.TextInputStyle.short, max_length=8,   required=False, value=str(current.get("delay", 5000))),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        text      = inter.text_values["text"].strip()
        emoji_val = inter.text_values["emoji_val"].strip() or None
        raw_delay = inter.text_values["delay"].strip()
        delay     = max(1000, int(raw_delay)) if raw_delay.isdigit() else 5000

        await inter.response.defer(with_message=False)
        try:
            result   = await api.edit_status_by_index(str(inter.author.id), self.index, text, emoji_val, delay)
            statuses = result.get("statuses", []) if result else []
            await inter.edit_original_response(
                content=None,
                components=paineis.get_status_config(statuses),
                flags=V2_FLAGS
            )
        except Exception as e:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, str(e), "Tools_BackStatusConfig"),
                flags=V2_FLAGS
            )


class ClearDmModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Limpar DM",
            custom_id="Tools_ClearDmModal",
            components=[disnake.ui.TextInput(label="ID do Usuário ou Canal", custom_id="dm_input",
                                              placeholder="ID do usuário — ou prefixe com c: para ID do canal", max_length=30)]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        target_id, channel_id = _parse_dm_input(inter.text_values["dm_input"])
        await inter.response.defer(with_message=False)
        try:
            result = await api.clear_dm(str(inter.author.id), target_id=target_id, channel_id=channel_id)
            msg    = result.get("message", "DM limpa!") if result else "DM limpa!"
            panel  = paineis.get_resultado(True, msg, "Tools_BackPainelAtual")
        except Exception as e:
            panel = paineis.get_resultado(False, str(e), "Tools_BackPainelAtual")
        await inter.edit_original_response(content=None,
            components=panel, flags=V2_FLAGS)


class ClearDmMediaModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Limpar Mídia da DM",
            custom_id="Tools_ClearDmMediaModal",
            components=[disnake.ui.TextInput(label="ID do Usuário ou Canal", custom_id="dm_input",
                                              placeholder="ID do usuário — ou prefixe com c: para ID do canal", max_length=30)]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        target_id, channel_id = _parse_dm_input(inter.text_values["dm_input"])
        await inter.response.defer(with_message=False)
        try:
            result = await api.clear_dm_media(str(inter.author.id), target_id=target_id, channel_id=channel_id)
            msg    = result.get("message", "Mídia limpa!") if result else "Mídia limpa!"
            panel  = paineis.get_resultado(True, msg, "Tools_BackPainelAtual")
        except Exception as e:
            panel = paineis.get_resultado(False, str(e), "Tools_BackPainelAtual")
        await inter.edit_original_response(content=None,
            components=panel, flags=V2_FLAGS)


class ClearMessagesModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Limpar Mensagens",
            custom_id="Tools_ClearMessagesModal",
            components=[disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id",
                                              placeholder="ID do canal", max_length=20)]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        channel_id = inter.text_values["channel_id"].strip()
        await inter.response.defer(with_message=False)
        try:
            result = await api.clear_messages(str(inter.author.id), channel_id)
            msg    = result.get("message", "Iniciado em background!") if result else "Iniciado!"
            panel  = paineis.get_resultado(True, msg, "Tools_BackPainelAtual")
        except Exception as e:
            panel = paineis.get_resultado(False, str(e), "Tools_BackPainelAtual")
        await inter.edit_original_response(content=None,
            components=panel, flags=V2_FLAGS)


class GuildIdModal(disnake.ui.Modal):
    def __init__(self, title: str, custom_id: str, back_id: str = "Tools_BackPainelAtual"):
        self._back = back_id
        super().__init__(
            title=title,
            custom_id=custom_id,
            components=[disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id",
                                              placeholder="ID do servidor", max_length=20)]
        )


class SendDmAllModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Enviar DM para Todos",
            custom_id="Tools_SendDmAllModal",
            components=[
                disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", placeholder="ID do servidor", max_length=20),
                disnake.ui.TextInput(label="Mensagem", custom_id="message", placeholder="Mensagem a enviar",
                                     style=disnake.TextInputStyle.paragraph, max_length=2000)
            ]
        )


class StartFarmModal(disnake.ui.Modal):
    def __init__(self, title: str, custom_id: str):
        super().__init__(
            title=title,
            custom_id=custom_id,
            components=[
                disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", placeholder="ID do servidor", max_length=20),
                disnake.ui.TextInput(label="ID do Canal",    custom_id="channel_id", placeholder="ID do canal", max_length=20)
            ]
        )


class ConnectVoiceModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Conectar à Voz",
            custom_id="Tools_ConnectVoiceModal",
            components=[
                disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", placeholder="ID do servidor", max_length=20),
                disnake.ui.TextInput(label="ID do Canal de Voz", custom_id="channel_id", placeholder="ID do canal de voz", max_length=20)
            ]
        )


class SpamCallModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Spam Call",
            custom_id="Tools_SpamCallModal",
            components=[disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id",
                                              placeholder="ID do servidor", max_length=20)]
        )


# Modals de mensagem global
class DefinirContentModal(disnake.ui.Modal):
    def __init__(self):
        msg = _get_msg_cfg()
        super().__init__(
            title="Definir Mensagem",
            custom_id="Tools_Mensagem_DefinirContentModal",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo da mensagem",
                    custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    max_length=2000,
                    required=True,
                    value=msg.get("content", "")
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        msg = _get_msg_cfg()
        msg["content"] = inter.text_values["content"]
        msg.pop("container", None)
        _save_msg_cfg(msg)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_tools_mensagem(_get_config()),
            flags=V2_FLAGS
        )


class DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self):
        embed = _get_msg_cfg().get("embed") or {}
        super().__init__(
            title="Definir Embed",
            custom_id="Tools_Mensagem_DefinirEmbedModal",
            components=[
                disnake.ui.TextInput(label="Título",     custom_id="title",       max_length=256, required=True,  value=embed.get("title", ""), placeholder="Título do embed"),
                disnake.ui.TextInput(label="Descrição",  custom_id="description", style=disnake.TextInputStyle.paragraph, max_length=4000, required=False, value=embed.get("description", "")),
                disnake.ui.TextInput(label="Cor (Hex)",  custom_id="color",       max_length=7,   required=False, value=embed.get("color", ""), placeholder="#5865F2"),
                disnake.ui.TextInput(label="Footer",     custom_id="footer",      max_length=2048,required=False, value=embed.get("footer", "")),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        def _hex(v):
            if not v: return None
            v = v.strip().lstrip("#")
            if len(v) not in (3, 6): return None
            try: int(v, 16); return f"#{v.upper()}"
            except ValueError: return None

        msg = _get_msg_cfg()
        msg.setdefault("embed", {})
        msg["embed"]["title"]       = inter.text_values.get("title") or None
        msg["embed"]["description"] = inter.text_values.get("description") or None
        msg["embed"]["color"]       = _hex(inter.text_values.get("color", ""))
        msg["embed"]["footer"]      = inter.text_values.get("footer") or None
        msg.pop("container", None)
        _save_msg_cfg(msg)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_tools_mensagem(_get_config()),
            flags=V2_FLAGS
        )


class DefinirImagensModal(disnake.ui.Modal):
    def __init__(self):
        msg   = _get_msg_cfg()
        embed = msg.get("embed") or {}
        has_embed = any(embed.get(k) for k in ("title", "description"))
        components = [
            disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage",
                                  style=disnake.TextInputStyle.short, required=False,
                                  value=msg.get("externalImage") or ""),
        ]
        if has_embed:
            components += [
                disnake.ui.TextInput(label="URL do Banner do Embed",    custom_id="banner",    style=disnake.TextInputStyle.short, required=False, value=embed.get("banner") or ""),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed", custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed.get("thumbnail") or ""),
            ]
        super().__init__(title="Definir Imagens", custom_id="Tools_Mensagem_DefinirImagensModal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        msg = _get_msg_cfg()
        msg["externalImage"] = inter.text_values.get("externalImage") or None
        if "banner"    in inter.text_values: msg.setdefault("embed", {})["banner"]    = inter.text_values.get("banner") or None
        if "thumbnail" in inter.text_values: msg.setdefault("embed", {})["thumbnail"] = inter.text_values.get("thumbnail") or None
        _save_msg_cfg(msg)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_tools_mensagem(_get_config()),
            flags=V2_FLAGS
        )


class DefinirContainerModal(disnake.ui.Modal):
    def __init__(self):
        msg = _get_msg_cfg()
        super().__init__(
            title="Definir Container",
            custom_id="Tools_Mensagem_DefinirContainerModal",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container",
                    custom_id="container",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Se precisar de ajuda, digite /ajuda aqui",
                    required=True,
                    value=msg.get("container") or "",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        if inter.text_values["container"].strip() == "/ajuda":
            return await inter.response.send_message(
                components=AnunciarHelper.helper("example"),
                ephemeral=True,
                flags=V2_FLAGS
            )
        msg = _get_msg_cfg()
        msg["container"] = inter.text_values["container"]
        msg.pop("content", None)
        msg.pop("embed", None)
        _save_msg_cfg(msg)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_tools_mensagem(_get_config()),
            flags=V2_FLAGS
        )


# ── Modals de mensagem de painel específico ────────────────────────────────────

class PainelMsgContentModal(disnake.ui.Modal):
    def __init__(self, painel_id: str):
        self.painel_id = painel_id
        pdata = _painel_get(painel_id) or {}
        msg   = pdata.get("mensagem", {}) or {}
        super().__init__(
            title="Mensagem do Painel — Conteúdo",
            custom_id=f"Tools_PainelMsg_ContentModal:{painel_id}",
            components=[
                disnake.ui.TextInput(label="Conteúdo", custom_id="content",
                                      style=disnake.TextInputStyle.paragraph, max_length=2000,
                                      required=True, value=msg.get("content", ""))
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        pdata = _painel_get(self.painel_id) or {}
        msg   = pdata.get("mensagem", {}) or {}
        msg["content"] = inter.text_values["content"]
        msg.pop("container", None)
        pdata["mensagem"] = msg
        _painel_save(self.painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_msg_painel(self.painel_id, pdata),
            flags=V2_FLAGS
        )


class PainelMsgEmbedModal(disnake.ui.Modal):
    def __init__(self, painel_id: str):
        self.painel_id = painel_id
        pdata = _painel_get(painel_id) or {}
        embed = (pdata.get("mensagem") or {}).get("embed") or {}
        super().__init__(
            title="Mensagem do Painel — Embed",
            custom_id=f"Tools_PainelMsg_EmbedModal:{painel_id}",
            components=[
                disnake.ui.TextInput(label="Título",     custom_id="title",       max_length=256,  required=True,  value=embed.get("title", "")),
                disnake.ui.TextInput(label="Descrição",  custom_id="description", style=disnake.TextInputStyle.paragraph, max_length=4000, required=False, value=embed.get("description", "")),
                disnake.ui.TextInput(label="Cor (Hex)",  custom_id="color",       max_length=7,    required=False, value=embed.get("color", ""), placeholder="#5865F2"),
                disnake.ui.TextInput(label="Footer",     custom_id="footer",      max_length=2048, required=False, value=embed.get("footer", "")),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        def _hex(v):
            if not v: return None
            v = v.strip().lstrip("#")
            if len(v) not in (3, 6): return None
            try: int(v, 16); return f"#{v.upper()}"
            except ValueError: return None

        pdata = _painel_get(self.painel_id) or {}
        msg   = pdata.setdefault("mensagem", {})
        msg.setdefault("embed", {})
        msg["embed"]["title"]       = inter.text_values.get("title") or None
        msg["embed"]["description"] = inter.text_values.get("description") or None
        msg["embed"]["color"]       = _hex(inter.text_values.get("color", ""))
        msg["embed"]["footer"]      = inter.text_values.get("footer") or None
        msg.pop("container", None)
        _painel_save(self.painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_msg_painel(self.painel_id, pdata),
            flags=V2_FLAGS
        )


class PainelMsgContainerModal(disnake.ui.Modal):
    def __init__(self, painel_id: str):
        self.painel_id = painel_id
        pdata = _painel_get(painel_id) or {}
        msg   = pdata.get("mensagem", {}) or {}
        super().__init__(
            title="Mensagem do Painel — Container",
            custom_id=f"Tools_PainelMsg_ContainerModal:{painel_id}",
            components=[
                disnake.ui.TextInput(label="Conteúdo do container", custom_id="container",
                                      style=disnake.TextInputStyle.paragraph, required=True,
                                      value=msg.get("container", ""), placeholder="Digite /ajuda para exemplos")
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        if inter.text_values["container"].strip() == "/ajuda":
            return await inter.response.send_message(
                components=AnunciarHelper.helper("example"), ephemeral=True, flags=V2_FLAGS
            )
        pdata = _painel_get(self.painel_id) or {}
        msg   = pdata.setdefault("mensagem", {})
        msg["container"] = inter.text_values["container"]
        msg.pop("content", None)
        msg.pop("embed", None)
        _painel_save(self.painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_msg_painel(self.painel_id, pdata),
            flags=V2_FLAGS
        )


class PainelNomeModal(disnake.ui.Modal):
    def __init__(self, painel_id: str):
        self.painel_id = painel_id
        pdata = _painel_get(painel_id) or {}
        super().__init__(
            title="Editar Nome do Painel",
            custom_id=f"Tools_Painel_NomeModal:{painel_id}",
            components=[
                disnake.ui.TextInput(
                    label="Nome do Painel",
                    custom_id="nome",
                    max_length=50,
                    required=True,
                    value=pdata.get("nome", ""),
                    placeholder="Ex: Ferramentas de Perfil"
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        pdata = _painel_get(self.painel_id) or {}
        pdata["nome"] = inter.text_values["nome"].strip()
        _painel_save(self.painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_painel(self.painel_id, pdata),
            flags=V2_FLAGS
        )


class PainelCargoModal(disnake.ui.Modal):
    def __init__(self, painel_id: str):
        self.painel_id = painel_id
        pdata = _painel_get(painel_id) or {}
        super().__init__(
            title="Cargo de Acesso do Painel",
            custom_id=f"Tools_Painel_CargoModal:{painel_id}",
            components=[
                disnake.ui.TextInput(
                    label="ID do Cargo",
                    custom_id="cargo_id",
                    placeholder="Cole aqui o ID do cargo",
                    style=disnake.TextInputStyle.short,
                    max_length=30,
                    required=True,
                    value=pdata.get("cargo_id", "")
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        pdata = _painel_get(self.painel_id) or {}
        pdata["cargo_id"] = inter.text_values["cargo_id"].strip()
        _painel_save(self.painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_cargo_painel(self.painel_id, pdata),
            flags=V2_FLAGS
        )


class PainelBotaoModal(disnake.ui.Modal):
    def __init__(self, painel_id: str):
        self.painel_id = painel_id
        pdata = _painel_get(painel_id) or {}
        botao = pdata.get("botao", {}) or {}
        super().__init__(
            title="Botão do Painel",
            custom_id=f"Tools_Painel_BotaoModal:{painel_id}",
            components=[
                disnake.ui.TextInput(
                    label="Label do Botão",
                    custom_id="label",
                    placeholder="Ex: Acessar Painel",
                    style=disnake.TextInputStyle.short,
                    max_length=80,
                    required=True,
                    value=botao.get("label", "Acessar Painel")
                ),
                disnake.ui.TextInput(
                    label="Emoji do Botão (Opcional)",
                    custom_id="emoji_val",
                    placeholder="Ex: ✅ ou <:nome:id>",
                    style=disnake.TextInputStyle.short,
                    max_length=100,
                    required=False,
                    value=botao.get("emoji", "") or ""
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        pdata = _painel_get(self.painel_id) or {}
        pdata["botao"] = {
            "label": inter.text_values["label"].strip(),
            "emoji": inter.text_values["emoji_val"].strip() or None,
        }
        _painel_save(self.painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_botao_painel(self.painel_id, pdata),
            flags=V2_FLAGS
        )


class NovoPainelModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Novo Painel",
            custom_id="Tools_NovoPainelModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome do Painel",
                    custom_id="nome",
                    max_length=50,
                    required=True,
                    placeholder="Ex: Painel de Perfil — Free"
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome      = inter.text_values["nome"].strip()
        painel_id = str(uuid.uuid4())[:12]
        pdata     = {
            "nome":       nome,
            "plano_min":  "free",
            "funcoes":    [],
            "mensagem":   {},
            "canal_id":   None,
            "mensagem_id": None,
            "cargo_id":   None,
            "botao":      {},
        }
        _painel_save(painel_id, pdata)
        await inter.response.edit_message(
            content=None,
            components=paineis.get_editor_painel(painel_id, pdata),
            flags=V2_FLAGS
        )


# ══════════════════════════════════════════════════════════════════════════════
# Cog principal
# ══════════════════════════════════════════════════════════════════════════════

class ToolsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Armazena painel_id atual por user para o botão "Voltar ao painel"
        self._user_painel_context: dict[int, str] = {}

    # ── Helpers internos ───────────────────────────────────────────────────────

    async def _get_statuses(self, user_id: str) -> list:
        try:
            config = await api.get_status_config(user_id)
            return config.get("statuses", []) if config else []
        except Exception:
            return []

    async def _get_voice_state(self, user_id: str) -> dict | None:
        try:
            return await api.voice_status(user_id)
        except Exception:
            return None

    def _require_session(self, inter: disnake.MessageInteraction) -> dict | None:
        """Retorna sessão ou edita a mensagem com tela de login e retorna None."""
        return _get_session(str(inter.author.id))

    async def _guard_session(self, inter: disnake.MessageInteraction) -> bool:
        """Verifica sessão; se não existir, exibe tela de login e retorna False."""
        if not _get_session(str(inter.author.id)):
            await inter.response.edit_message(
                content=None,
                components=paineis.get_painel_login(),
                flags=V2_FLAGS
            )
            return False
        return True

    async def _guard_plan(self, inter: disnake.MessageInteraction) -> str | None:
        """Verifica plano; se não existir, exibe tela sem plano e retorna None."""
        plano = _detect_plan(inter.author)
        if not plano:
            await inter.response.edit_message(
                content=None,
                components=paineis.get_sem_plano(),
                flags=V2_FLAGS
            )
        return plano

    async def _build_global_msg(self) -> dict:
        config    = _get_config()
        msg_data  = config.get("mensagem", {}) or {}
        botao_cfg = config.get("botao", {})
        return await _build_msg(msg_data, botao_cfg, "Tools_VerificarAcesso")

    async def _build_painel_msg(self, painel_id: str, painel_data: dict) -> dict:
        msg_data  = painel_data.get("mensagem", {}) or {}
        botao_cfg = painel_data.get("botao", {}) or {}
        return await _build_msg(msg_data, botao_cfg, f"Tools_AbrirPainel:{painel_id}")

    async def _render_painel_usuario(self, inter: disnake.MessageInteraction, painel_id: str, *, ephemeral: bool = False):
        """Renderiza o painel de um usuário carregando contexto dinâmico.
        
        ephemeral=True → send_message ephemeral (primeira abertura vinda de mensagem pública).
        ephemeral=False → edit_message (já dentro do ephemeral, só edita).
        """
        pdata = _painel_get(painel_id)
        if not pdata:
            if ephemeral:
                await inter.response.send_message(
                    components=paineis.get_resultado(False, "Painel não encontrado.", "Tools_BackLogin"),
                    ephemeral=True, flags=V2_FLAGS
                )
            else:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(False, "Painel não encontrado.", "Tools_BackLogin"),
                    flags=V2_FLAGS
                )
            return

        uid     = str(inter.author.id)
        funcoes = pdata.get("funcoes", [])
        extra   = {}

        if any(f in funcoes for f in ("status_start", "status_stop", "status_config")):
            extra["statuses"] = await self._get_statuses(uid)
        if any(f in funcoes for f in ("voice_connect", "voice_disconnect", "voice_status")):
            extra["voice_state"] = await self._get_voice_state(uid)

        self._user_painel_context[inter.author.id] = painel_id

        if ephemeral:
            await inter.response.send_message(
                components=paineis.get_painel_usuario(painel_id, pdata, inter.author, extra),
                ephemeral=True, flags=V2_FLAGS
            )
        else:
            await inter.response.edit_message(
                content=None,
                components=paineis.get_painel_usuario(painel_id, pdata, inter.author, extra),
                flags=V2_FLAGS
            )

    # ── Publicação de painel ───────────────────────────────────────────────────

    async def _publicar_painel(self, inter: disnake.MessageInteraction, painel_id: str):
        """Publica ou atualiza a mensagem de um painel no canal configurado."""
        await inter.response.defer(with_message=False)

        pdata = _painel_get(painel_id)
        if not pdata:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, "Painel não encontrado.", f"Tools_Painel_Voltar:{painel_id}"),
                flags=V2_FLAGS
            )
            return

        canal_id = pdata.get("canal_id")
        if not canal_id:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, "Defina um canal antes de publicar.", f"Tools_Painel_Voltar:{painel_id}"),
                flags=V2_FLAGS
            )
            return

        msg_data = pdata.get("mensagem", {}) or {}
        if not any([msg_data.get("content"), msg_data.get("embed"), msg_data.get("container")]):
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, "Configure a mensagem do painel antes de publicar.", f"Tools_Painel_Voltar:{painel_id}"),
                flags=V2_FLAGS
            )
            return

        channel = self.bot.get_channel(canal_id) or await self.bot.fetch_channel(canal_id)
        if not channel:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, "Canal não encontrado.", f"Tools_Painel_Voltar:{painel_id}"),
                flags=V2_FLAGS
            )
            return

        built = await self._build_painel_msg(painel_id, pdata)

        try:
            msg_id = pdata.get("mensagem_id")
            if msg_id:
                try:
                    existing = await channel.fetch_message(int(msg_id))
                    await _edit_built(existing, built)
                    pdata["mensagem_id"] = existing.id
                except disnake.NotFound:
                    sent = await _send_built(channel, built)
                    pdata["mensagem_id"] = sent.id
            else:
                sent = await _send_built(channel, built)
                pdata["mensagem_id"] = sent.id

            _painel_save(painel_id, pdata)
            await inter.edit_original_response(
                content=None,
                components=paineis.get_editor_painel(painel_id, pdata),
                flags=V2_FLAGS
            )
            from functions.message import message as msg_fn
            await msg_fn.success(inter, f"Painel publicado em {channel.mention}!", followup=True)
        except Exception as e:
            await inter.edit_original_response(
                content=None,
                components=paineis.get_resultado(False, f"Erro ao publicar: {e}", f"Tools_Painel_Voltar:{painel_id}"),
                flags=V2_FLAGS
            )

    async def _despublicar_painel(self, inter: disnake.MessageInteraction, painel_id: str):
        """Remove a mensagem publicada de um painel."""
        await inter.response.defer(with_message=False)
        pdata = _painel_get(painel_id)
        if not pdata:
            return

        canal_id = pdata.get("canal_id")
        msg_id   = pdata.get("mensagem_id")

        if canal_id and msg_id:
            try:
                channel = self.bot.get_channel(canal_id) or await self.bot.fetch_channel(canal_id)
                msg     = await channel.fetch_message(int(msg_id))
                await msg.delete()
            except Exception:
                pass

        pdata["mensagem_id"] = None
        _painel_save(painel_id, pdata)
        await inter.edit_original_response(
            content=None,
            components=paineis.get_editor_painel(painel_id, pdata),
            flags=V2_FLAGS
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Listener de botões / interações
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_message_interaction")
    async def handle_tools(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id

        # ── Navegação admin ────────────────────────────────────────────────────

        if cid == "Tools_PainelPrincipal":
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_main(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Toggle":
            config = _get_config()
            _save_config({"ativo": not config.get("ativo", False)})
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_main(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Cargos":
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_cargos(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_EditarCargoFree":
            await inter.response.send_modal(CargoModal("free"))

        elif cid == "Tools_EditarCargoBooster":
            await inter.response.send_modal(CargoModal("booster"))

        elif cid == "Tools_EditarCargoScarlet":
            await inter.response.send_modal(CargoModal("scarlet"))

        elif cid == "Tools_PersonalizarBotao":
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_botao(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_EditarBotao":
            await inter.response.send_modal(BotaoModal(_get_config()))

        elif cid == "Tools_PersonalizarMensagem":
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)

        # ── Mensagem global ────────────────────────────────────────────────────

        elif cid == "Tools_Mensagem_DefinirContent":
            await inter.response.send_modal(DefinirContentModal())

        elif cid == "Tools_Mensagem_ApagarContent":
            msg = _get_msg_cfg(); msg.pop("content", None); _save_msg_cfg(msg)
            await inter.response.edit_message(content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Mensagem_DefinirEmbed":
            await inter.response.send_modal(DefinirEmbedModal())

        elif cid == "Tools_Mensagem_ApagarEmbed":
            msg = _get_msg_cfg(); msg.pop("embed", None); _save_msg_cfg(msg)
            await inter.response.edit_message(content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Mensagem_DefinirImagens":
            await inter.response.send_modal(DefinirImagensModal())

        elif cid == "Tools_Mensagem_ApagarImagens":
            msg = _get_msg_cfg()
            msg["externalImage"] = None
            msg.setdefault("embed", {}).update({"banner": None, "thumbnail": None})
            _save_msg_cfg(msg)
            await inter.response.edit_message(content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Mensagem_DefinirContainer":
            await inter.response.send_modal(DefinirContainerModal())

        elif cid == "Tools_Mensagem_ApagarContainer":
            msg = _get_msg_cfg(); msg.pop("container", None); _save_msg_cfg(msg)
            await inter.response.edit_message(content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Mensagem_ApagarTudo":
            _save_msg_cfg({})
            await inter.response.edit_message(content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_Mensagem_Visualizar":
            built = await self._build_global_msg()
            kw = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
            if built.get("mode") == "v2":
                await inter.response.send_message(components=built["components"], flags=built["flags"], **kw)
            else:
                await inter.response.send_message(
                    content=built.get("content"), embed=built.get("embed"),
                    components=built.get("components") or None, **kw)

        elif cid == "Tools_Mensagem_EnviarNoCanal":
            # Mostra canal select para envio global
            await inter.response.edit_message(
                content=None,
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            f"-# Tools > Mensagem > **Enviar**"
                        ),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay("-# Selecione o canal onde a mensagem será enviada"),
                        disnake.ui.ActionRow(
                            disnake.ui.ChannelSelect(
                                custom_id="Tools_Mensagem_SelecionarCanal",
                                placeholder="Selecione o canal",
                                channel_types=[disnake.ChannelType.text],
                                min_values=1, max_values=1,
                            )
                        ),
                        **paineis._ck(),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Tools_PersonalizarMensagem")
                    ),
                ],
                flags=V2_FLAGS
            )

        elif cid == "Tools_Mensagem_ConfirmarEnvio":
            channel = inter.channel
            built   = await self._build_global_msg()
            sent    = await _send_built(channel, built)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)
            from functions.message import message as msg_fn
            await msg_fn.success(inter, f"Mensagem enviada em {channel.mention} (`{sent.id}`)",
                                 followup=True,
                                 component=[disnake.ui.ActionRow(disnake.ui.Button(label="Ir para a mensagem", url=sent.jump_url))])

        # ── Acesso público (membros) ────────────────────────────────────────────

        elif cid == "Tools_VerificarAcesso":
            config = _get_config()
            if not config.get("ativo", False):
                await inter.response.send_message(
                    components=paineis.get_sistema_inativo(), ephemeral=True, flags=V2_FLAGS)
                return
            if await api.check_blacklist(str(inter.author.id)):
                await inter.response.send_message(
                    components=paineis.get_painel_blacklist(), ephemeral=True, flags=V2_FLAGS)
                return
            plano = _detect_plan(inter.author)
            if not plano:
                await inter.response.send_message(
                    components=paineis.get_sem_plano(), ephemeral=True, flags=V2_FLAGS)
                return
            paineis_disp = _get_paineis_para_plano(plano, inter.author)
            await inter.response.send_message(
                components=paineis.get_acesso_verificado(plano, paineis_disp),
                ephemeral=True, flags=V2_FLAGS)

        elif cid == "Tools_LoginBtn":
            plano = _detect_plan(inter.author)
            if not plano:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_sem_plano(), flags=V2_FLAGS)
                return
            await inter.response.send_modal(LoginModal(plano))

        elif cid == "Tools_BackLogin":
            plano = _detect_plan(inter.author)
            if plano:
                paineis_disp = _get_paineis_para_plano(plano, inter.author)
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_acesso_verificado(plano, paineis_disp), flags=V2_FLAGS)
            else:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_sem_plano(), flags=V2_FLAGS)

        elif cid == "Tools_LogoutBtn":
            uid = str(inter.author.id)
            try: await api.logout(uid)
            except Exception: pass
            _delete_session(uid)
            plano = _detect_plan(inter.author)
            if plano:
                paineis_disp = _get_paineis_para_plano(plano, inter.author)
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_acesso_verificado(plano, paineis_disp), flags=V2_FLAGS)
            else:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(True, "Logout efetuado com sucesso!", "Tools_BackLogin"),
                    flags=V2_FLAGS)

        # ── Gerenciamento de painéis (admin) ───────────────────────────────────

        elif cid == "Tools_GerenciarPaineis":
            await inter.response.edit_message(
                content=None,
                components=paineis.get_gerenciar_paineis(_get_config()), flags=V2_FLAGS)

        elif cid == "Tools_CriarPainel":
            await inter.response.send_modal(NovoPainelModal())

        # ── Botão dinâmico de abrir painel (formato Tools_AbrirPainel:{id}) ────

        elif cid.startswith("Tools_AbrirPainel:"):
            # Este botão fica na mensagem PÚBLICA do canal.
            # Toda resposta deve ser ephemeral (send_message), nunca edit_message.
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id)
            if not pdata:
                await inter.response.send_message(
                    components=paineis.get_resultado(False, "Painel não encontrado.", "Tools_BackLogin"),
                    ephemeral=True, flags=V2_FLAGS)
                return
            if not _member_has_painel_access(inter.author, pdata):
                await inter.response.send_message(
                    components=paineis.get_sem_plano(),
                    ephemeral=True, flags=V2_FLAGS)
                return
            if not _get_session(str(inter.author.id)):
                await inter.response.send_message(
                    components=paineis.get_painel_login(),
                    ephemeral=True, flags=V2_FLAGS)
                return
            await self._render_painel_usuario(inter, painel_id, ephemeral=True)

        # ── Edição de painel (admin) ───────────────────────────────────────────

        elif cid.startswith("Tools_Painel_Voltar:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_EditarNome:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PainelNomeModal(painel_id))

        elif cid.startswith("Tools_Painel_EditarPlano:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_plano_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_EditarCargo:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_cargo_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_CargoModal:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PainelCargoModal(painel_id))

        elif cid.startswith("Tools_Painel_CargoRemover:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            pdata["cargo_id"] = None
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_cargo_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_EditarBotao:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_botao_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_BotaoModal:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PainelBotaoModal(painel_id))

        elif cid.startswith("Tools_Painel_EditarMsg:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_msg_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_EditarFuncoes:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_funcoes_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_DefinirCanal:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.edit_message(
                content=None,
                components=paineis.get_definir_canal_painel(painel_id), flags=V2_FLAGS)

        elif cid.startswith("Tools_Painel_Publicar:"):
            painel_id = cid.split(":", 1)[1]
            await self._publicar_painel(inter, painel_id)

        elif cid.startswith("Tools_Painel_Despublicar:"):
            painel_id = cid.split(":", 1)[1]
            await self._despublicar_painel(inter, painel_id)

        # ── Mensagem do painel específico ──────────────────────────────────────

        elif cid.startswith("Tools_PainelMsg_DefinirContent:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PainelMsgContentModal(painel_id))

        elif cid.startswith("Tools_PainelMsg_ApagarContent:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            pdata.setdefault("mensagem", {}).pop("content", None)
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_msg_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_PainelMsg_DefinirEmbed:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PainelMsgEmbedModal(painel_id))

        elif cid.startswith("Tools_PainelMsg_ApagarEmbed:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            pdata.setdefault("mensagem", {}).pop("embed", None)
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_msg_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_PainelMsg_DefinirImagens:"):
            painel_id = cid.split(":", 1)[1]
            # Reaproveita modal de imagens com contexto do painel
            pdata = _painel_get(painel_id) or {}
            msg   = pdata.get("mensagem", {}) or {}
            embed = msg.get("embed") or {}
            has_embed = any(embed.get(k) for k in ("title", "description"))
            components = [
                disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage",
                                      style=disnake.TextInputStyle.short, required=False,
                                      value=msg.get("externalImage") or ""),
            ]
            if has_embed:
                components += [
                    disnake.ui.TextInput(label="URL do Banner",    custom_id="banner",    style=disnake.TextInputStyle.short, required=False, value=embed.get("banner") or ""),
                    disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed.get("thumbnail") or ""),
                ]

            class _ImgModal(disnake.ui.Modal):
                def __init__(self_, pid):
                    self_.pid = pid
                    super().__init__(title="Definir Imagens", custom_id=f"_ImgModal:{pid}", components=components)
                async def callback(self_, inter2: disnake.ModalInteraction):
                    pd = _painel_get(self_.pid) or {}
                    m  = pd.setdefault("mensagem", {})
                    m["externalImage"] = inter2.text_values.get("externalImage") or None
                    if "banner"    in inter2.text_values: m.setdefault("embed", {})["banner"]    = inter2.text_values.get("banner") or None
                    if "thumbnail" in inter2.text_values: m.setdefault("embed", {})["thumbnail"] = inter2.text_values.get("thumbnail") or None
                    _painel_save(self_.pid, pd)
                    await inter2.response.edit_message(components=paineis.get_editor_msg_painel(self_.pid, pd), flags=V2_FLAGS)

            await inter.response.send_modal(_ImgModal(painel_id))

        elif cid.startswith("Tools_PainelMsg_ApagarImagens:"):
            painel_id = cid.split(":", 1)[1]
            pdata = _painel_get(painel_id) or {}
            m = pdata.setdefault("mensagem", {})
            m["externalImage"] = None
            m.setdefault("embed", {}).update({"banner": None, "thumbnail": None})
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_msg_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_PainelMsg_DefinirContainer:"):
            painel_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PainelMsgContainerModal(painel_id))

        elif cid.startswith("Tools_PainelMsg_ApagarContainer:"):
            painel_id = cid.split(":", 1)[1]
            pdata = _painel_get(painel_id) or {}
            pdata.setdefault("mensagem", {}).pop("container", None)
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_msg_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_PainelMsg_ApagarTudo:"):
            painel_id = cid.split(":", 1)[1]
            pdata = _painel_get(painel_id) or {}
            pdata["mensagem"] = {}
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_msg_painel(painel_id, pdata), flags=V2_FLAGS)

        elif cid.startswith("Tools_PainelMsg_Visualizar:"):
            painel_id = cid.split(":", 1)[1]
            pdata     = _painel_get(painel_id) or {}
            built     = await self._build_painel_msg(painel_id, pdata)
            kw = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
            if built.get("mode") == "v2":
                await inter.response.send_message(components=built["components"], flags=built["flags"], **kw)
            else:
                await inter.response.send_message(
                    content=built.get("content"), embed=built.get("embed"),
                    components=built.get("components") or None, **kw)

        # ── Funções de perfil (status) ─────────────────────────────────────────

        elif cid == "Tools_Perfil_StartStatus":
            try:
                result = await api.start_status(str(inter.author.id))
                msg    = result.get("message", "Status animado iniciado!") if result else "Status animado iniciado!"
                panel  = paineis.get_resultado(True, msg, "Tools_BackStatusConfig")
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), "Tools_BackStatusConfig")
            await inter.response.edit_message(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_Perfil_StopStatus":
            try:
                result = await api.stop_status(str(inter.author.id))
                msg    = result.get("message", "Status animado parado!") if result else "Status animado parado!"
                panel  = paineis.get_resultado(True, msg, "Tools_BackStatusConfig")
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), "Tools_BackStatusConfig")
            await inter.response.edit_message(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_Perfil_ConfigStatus":
            statuses = await self._get_statuses(str(inter.author.id))
            await inter.response.edit_message(
                content=None,
                components=paineis.get_status_config(statuses), flags=V2_FLAGS)

        elif cid == "Tools_Perfil_AddStatus":
            await inter.response.send_modal(AddStatusModal())

        elif cid == "Tools_Perfil_OpenRemoveSelect":
            statuses = await self._get_statuses(str(inter.author.id))
            if not statuses:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(False, "Nenhum status para remover.", "Tools_BackStatusConfig"),
                    flags=V2_FLAGS)
                return
            await inter.response.edit_message(
                content=None,
                components=paineis.get_status_remove_select(statuses), flags=V2_FLAGS)

        elif cid == "Tools_Perfil_OpenEditSelect":
            statuses = await self._get_statuses(str(inter.author.id))
            if not statuses:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(False, "Nenhum status para editar.", "Tools_BackStatusConfig"),
                    flags=V2_FLAGS)
                return
            await inter.response.edit_message(
                content=None,
                components=paineis.get_status_edit_select(statuses), flags=V2_FLAGS)

        elif cid == "Tools_Perfil_ClearStatus":
            try:
                await api.clear_status(str(inter.author.id))
                panel = paineis.get_status_config([])
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), "Tools_BackStatusConfig")
            await inter.response.edit_message(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_BackStatusConfig":
            statuses = await self._get_statuses(str(inter.author.id))
            await inter.response.edit_message(
                content=None,
                components=paineis.get_status_config(statuses), flags=V2_FLAGS)

        elif cid == "Tools_BackPainelAtual":
            painel_id = self._user_painel_context.get(inter.author.id)
            if painel_id:
                await self._render_painel_usuario(inter, painel_id)
            else:
                plano = _detect_plan(inter.author)
                if plano:
                    paineis_disp = _get_paineis_para_plano(plano, inter.author)
                    await inter.response.edit_message(
                        content=None,
                        components=paineis.get_acesso_verificado(plano, paineis_disp), flags=V2_FLAGS)

    # ══════════════════════════════════════════════════════════════════════════
    # Listener de dropdowns
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def handle_tools_dropdowns(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id

        # ── Canal global ───────────────────────────────────────────────────────
        if cid == "Tools_Mensagem_SelecionarCanal":
            try:
                channel = inter.guild.get_channel(int(inter.values[0])) or self.bot.get_channel(int(inter.values[0]))
            except (ValueError, TypeError):
                channel = None
            if channel is None or not hasattr(channel, "send"):
                from functions.message import message as msg_fn
                await msg_fn.error(inter, "Canal inválido.", followup=True)
                return
            built = await self._build_global_msg()
            sent  = await _send_built(channel, built)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_tools_mensagem(_get_config()), flags=V2_FLAGS)
            from functions.message import message as msg_fn
            await msg_fn.success(inter, f"Mensagem enviada em {channel.mention} (`{sent.id}`)",
                                 followup=True,
                                 component=[disnake.ui.ActionRow(disnake.ui.Button(label="Ir para a mensagem", url=sent.jump_url))])

        # ── Canal do painel específico ─────────────────────────────────────────
        elif cid.startswith("Tools_Painel_CanalSelect:"):
            painel_id = cid.split(":", 1)[1]
            canal_id  = int(inter.values[0])
            pdata     = _painel_get(painel_id) or {}
            pdata["canal_id"]    = canal_id
            pdata["mensagem_id"] = None  # Reset msg ao trocar canal
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_painel(painel_id, pdata), flags=V2_FLAGS)

        # ── Seletor de painel para editar ─────────────────────────────────────
        elif cid == "Tools_SelecionarPainelEditar":
            painel_id = inter.values[0]
            pdata     = _painel_get(painel_id)
            if not pdata:
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(False, "Painel não encontrado.", "Tools_GerenciarPaineis"),
                    flags=V2_FLAGS)
                return
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_painel(painel_id, pdata), flags=V2_FLAGS)

        # ── Seletor de painel para deletar ────────────────────────────────────
        elif cid == "Tools_SelecionarPainelDeletar":
            painel_id = inter.values[0]
            pdata     = _painel_get(painel_id)
            nome      = pdata.get("nome", painel_id) if pdata else painel_id

            # Remove msg publicada se houver
            if pdata and pdata.get("canal_id") and pdata.get("mensagem_id"):
                try:
                    ch  = self.bot.get_channel(pdata["canal_id"]) or await self.bot.fetch_channel(pdata["canal_id"])
                    msg = await ch.fetch_message(int(pdata["mensagem_id"]))
                    await msg.delete()
                except Exception:
                    pass

            _painel_delete(painel_id)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_gerenciar_paineis(_get_config()), flags=V2_FLAGS)

        # ── Plano mínimo do painel ────────────────────────────────────────────
        elif cid.startswith("Tools_Painel_PlanoSelect:"):
            painel_id = cid.split(":", 1)[1]
            novo_plano = inter.values[0]
            pdata      = _painel_get(painel_id) or {}
            pdata["plano_min"] = novo_plano
            # Limpa funções que não são mais acessíveis
            rank_novo = paineis.PLAN_RANK.get(novo_plano, 0)
            pdata["funcoes"] = [
                f for f in pdata.get("funcoes", [])
                if paineis.PLAN_RANK.get(paineis.FUNCTION_MIN_PLAN.get(f, "free"), 0) <= rank_novo
            ]
            _painel_save(painel_id, pdata)
            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_painel(painel_id, pdata), flags=V2_FLAGS)

        # ── Seleção de funções por categoria ──────────────────────────────────
        elif cid.startswith("Tools_Painel_FuncoesSelect:"):
            parts     = cid.split(":", 2)
            painel_id = parts[1]
            cat       = parts[2] if len(parts) > 2 else ""
            pdata     = _painel_get(painel_id) or {}

            # Remove funções desta categoria e adiciona as selecionadas
            funcoes_atuais = [f for f in pdata.get("funcoes", [])
                              if paineis.ALL_FUNCTIONS.get(f, {}).get("category") != cat]
            funcoes_atuais.extend(inter.values)
            pdata["funcoes"] = funcoes_atuais
            _painel_save(painel_id, pdata)

            await inter.response.edit_message(
                content=None,
                components=paineis.get_editor_funcoes_painel(painel_id, pdata), flags=V2_FLAGS)

        # ── Ações do painel de usuário (por categoria) ────────────────────────
        elif cid.startswith("Tools_Acao:"):
            parts     = cid.split(":")
            painel_id = parts[1]
            # cat     = parts[2]  # categoria (não necessário aqui)
            action    = inter.values[0]
            uid       = str(inter.author.id)

            await self._handle_user_action(inter, action, uid, painel_id)

        # ── Remove status específico ──────────────────────────────────────────
        elif re.match(r"^Tools_Perfil_remove_specific", cid):
            selected_index = int(inter.values[0])
            try:
                result   = await api.remove_status_by_index(str(inter.author.id), selected_index)
                statuses = result.get("statuses", []) if result else []
                panel    = paineis.get_status_config(statuses)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), "Tools_BackStatusConfig")
            await inter.response.edit_message(content=None,
                components=panel, flags=V2_FLAGS)

        # ── Edita status específico ────────────────────────────────────────────
        elif re.match(r"^Tools_Perfil_edit_specific", cid):
            selected_index = int(inter.values[0])
            statuses = await self._get_statuses(str(inter.author.id))
            if selected_index >= len(statuses):
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(False, "Status não encontrado.", "Tools_BackStatusConfig"),
                    flags=V2_FLAGS)
                return
            await inter.response.send_modal(EditStatusModal(selected_index, statuses[selected_index]))

    # ══════════════════════════════════════════════════════════════════════════
    # Handler de ações do usuário (ações das ferramentas)
    # ══════════════════════════════════════════════════════════════════════════

    async def _handle_user_action(self, inter: disnake.MessageInteraction, action: str, uid: str, painel_id: str):
        """Processa uma ação selecionada no painel de usuário."""
        back_id = "Tools_BackPainelAtual"

        # ── Perfil ──────────────────────────────────────────────────────────
        if action == "status_start":
            try:
                r = await api.start_status(uid)
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(True, r.get("message", "Status iniciado!") if r else "Status iniciado!", back_id),
                    flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)

        elif action == "status_stop":
            try:
                r = await api.stop_status(uid)
                await inter.response.edit_message(
                    content=None,
                    components=paineis.get_resultado(True, r.get("message", "Status parado!") if r else "Status parado!", back_id),
                    flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)

        elif action == "status_config":
            statuses = await self._get_statuses(uid)
            self._user_painel_context[inter.author.id] = painel_id
            await inter.response.edit_message(content=None,
                components=paineis.get_status_config(statuses), flags=V2_FLAGS)

        # ── Limpeza ─────────────────────────────────────────────────────────
        elif action == "clear_dm":
            await inter.response.send_modal(ClearDmModal())

        elif action == "clear_dm_media":
            await inter.response.send_modal(ClearDmMediaModal())

        elif action == "clear_messages":
            await inter.response.send_modal(ClearMessagesModal())

        elif action in ("close_dms", "clear_all_dms", "open_dms", "leave_group_dms",
                        "open_history_dms", "nuke_all_dms", "clear_voice_msgs", "remove_friends"):
            api_map = {
                "close_dms":         (api.close_dms,            "DMs fechadas!"),
                "clear_all_dms":     (api.clear_all_dms,        "Limpeza de DMs iniciada em background!"),
                "open_dms":          (api.open_dms,             "DMs abertas!"),
                "leave_group_dms":   (api.leave_group_dms,      "Saiu de todos os Group DMs!"),
                "open_history_dms":  (api.open_all_history_dms, "Histórico de DMs aberto!"),
                "nuke_all_dms":      (api.nuke_all_dms,         "Nuke de DMs iniciado!"),
                "clear_voice_msgs":  (api.clear_voice_msgs,     "Mensagens de voz removidas!"),
                "remove_friends":    (api.remove_friends,       "Remoção de amigos iniciada!"),
            }
            fn, default_msg = api_map[action]
            try:
                r = await fn(uid)
                msg = r.get("message", default_msg) if r else default_msg
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)

        # ── Raid ─────────────────────────────────────────────────────────────
        elif action == "kick_all":
            await inter.response.send_modal(GuildIdModal("Kickar Todos", "Tools_RaidModal_KickAll"))
        elif action == "ban_all":
            await inter.response.send_modal(GuildIdModal("Banir Todos", "Tools_RaidModal_BanAll"))
        elif action == "clear_server":
            await inter.response.send_modal(GuildIdModal("Limpar Servidor", "Tools_RaidModal_ClearServer"))
        elif action == "send_dm_all":
            await inter.response.send_modal(SendDmAllModal())
        elif action == "leave_servers":
            try:
                r = await api.leave_servers(uid)
                msg = r.get("message", "Saindo de todos os servidores!") if r else "Iniciado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)
        elif action == "delete_servers":
            try:
                r = await api.delete_owned_servers(uid)
                msg = r.get("message", "Deletando servidores!") if r else "Iniciado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)

        # ── Farms ────────────────────────────────────────────────────────────
        elif action == "farm_kosame_start":
            await inter.response.send_modal(StartFarmModal("Iniciar Farm Kosame", "Tools_FarmsModal_StartKosame"))
        elif action == "farm_kosame_stop":
            try:
                r = await api.stop_kosame(uid)
                msg = r.get("message", "Farm Kosame parado!") if r else "Parado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)
        elif action == "farm_zany_start":
            await inter.response.send_modal(StartFarmModal("Iniciar Farm Zany", "Tools_FarmsModal_StartZany"))
        elif action == "farm_zany_stop":
            try:
                r = await api.stop_zany(uid)
                msg = r.get("message", "Farm Zany parado!") if r else "Parado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)

        # ── Call / Voz ───────────────────────────────────────────────────────
        elif action == "voice_connect":
            await inter.response.send_modal(ConnectVoiceModal())
        elif action == "voice_disconnect":
            try:
                r = await api.disconnect_voice(uid)
                msg = r.get("message", "Desconectado!") if r else "Desconectado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)
        elif action == "voice_reconnect":
            try:
                r = await api.reconnect_voice(uid)
                msg = r.get("message", "Reconectado!") if r else "Reconectado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)
        elif action == "voice_status":
            try:
                r = await api.voice_status(uid)
                if r and r.get("connected"):
                    desc = (
                        f"{emoji.correct} Conectado — ⏱️ `{r.get('elapsedHuman', '—')}`\n"
                        f"> Canal: `{r.get('channelId', '?')}`\n"
                        f"> Servidor: `{r.get('guildId', '?')}`"
                    )
                else:
                    desc = f"{emoji.wrong} Desconectado"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, desc, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)
        elif action == "spam_call_start":
            await inter.response.send_modal(SpamCallModal())
        elif action == "spam_call_stop":
            try:
                r = await api.stop_spam_call(uid)
                msg = r.get("message", "Spam call parado!") if r else "Parado!"
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(True, msg, back_id), flags=V2_FLAGS)
            except Exception as e:
                await inter.response.edit_message(content=None,
                    components=paineis.get_resultado(False, str(e), back_id), flags=V2_FLAGS)

    # ══════════════════════════════════════════════════════════════════════════
    # Listener de modals (raid / farms / call)
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_modal_submit")
    async def handle_tools_modals(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        uid = str(inter.author.id)
        back_id = "Tools_BackPainelAtual"

        if cid == "Tools_RaidModal_KickAll":
            await inter.response.defer(with_message=False)
            try:
                r = await api.kick_all(uid, inter.text_values["guild_id"])
                panel = paineis.get_resultado(True, r.get("message", "Iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_RaidModal_BanAll":
            await inter.response.defer(with_message=False)
            try:
                r = await api.ban_all(uid, inter.text_values["guild_id"])
                panel = paineis.get_resultado(True, r.get("message", "Iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_RaidModal_ClearServer":
            await inter.response.defer(with_message=False)
            try:
                r = await api.clear_server(uid, inter.text_values["guild_id"])
                panel = paineis.get_resultado(True, r.get("message", "Iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_SendDmAllModal":
            await inter.response.defer(with_message=False)
            try:
                r = await api.send_dm_all(uid, inter.text_values["guild_id"], inter.text_values["message"])
                panel = paineis.get_resultado(True, r.get("message", "Iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_FarmsModal_StartKosame":
            await inter.response.defer(with_message=False)
            try:
                r = await api.start_kosame(uid, inter.text_values["guild_id"], inter.text_values["channel_id"])
                panel = paineis.get_resultado(True, r.get("message", "Farm Kosame iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_FarmsModal_StartZany":
            await inter.response.defer(with_message=False)
            try:
                r = await api.start_zany(uid, inter.text_values["guild_id"], inter.text_values["channel_id"])
                panel = paineis.get_resultado(True, r.get("message", "Farm Zany iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_ConnectVoiceModal":
            await inter.response.defer(with_message=False)
            try:
                r = await api.connect_voice(uid, inter.text_values["guild_id"], inter.text_values["channel_id"])
                if r and r.get("success"):
                    msg = f"Conectado ao canal `{r.get('channelId', '?')}`! Tempo: `{r.get('elapsedHuman', '0s')}`"
                else:
                    msg = r.get("message", "Conectado!") if r else "Conectado!"
                panel = paineis.get_resultado(True, msg, back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        elif cid == "Tools_SpamCallModal":
            await inter.response.defer(with_message=False)
            try:
                r = await api.start_spam_call(uid, inter.text_values["guild_id"])
                panel = paineis.get_resultado(True, r.get("message", "Spam call iniciado!") if r else "Iniciado!", back_id)
            except Exception as e:
                panel = paineis.get_resultado(False, str(e), back_id)
            await inter.edit_original_response(content=None,
                components=panel, flags=V2_FLAGS)

        # ── Modals dinâmicos de imagens de painel ─────────────────────────────
        elif cid.startswith("_ImgModal:"):
            # Tratado internamente no modal; aqui como fallback
            pass


def setup(bot: commands.Bot):
    bot.add_cog(ToolsCog(bot))