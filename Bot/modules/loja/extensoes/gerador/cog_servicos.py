"""
cog_servicos.py — Gerenciamento completo de serviços e grupos do Gerador
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from commands.admin.anunciar.builder import Builder

from .helpers import (
    load_config, save_config,
    list_services, list_groups,
    create_service, update_service, delete_service,
    create_group, delete_group,
    get_service, get_stock_count,
)


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _embed_color() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"color": int(hex_.replace("#", ""), 16)}
    return {}


def _mode() -> str:
    return db.get_document("custom_mode").get("mode")


# ──────────────────────────────────────────────────────────
#  Painéis de listagem
# ──────────────────────────────────────────────────────────

def build_services_panel(mode: str) -> dict:
    servicos = list_services()

    if not servicos:
        options = [disnake.SelectOption(label="Nenhum serviço criado", value="__none__")]
        disabled = True
    else:
        options = []
        for sid, svc in list(servicos.items())[:25]:
            stock = get_stock_count(sid)
            fake = svc.get("stock_fake", {}).get("enabled", False)
            stock_label = "♾ Fake" if fake else str(stock)
            ativo_emoji = "✅" if svc.get("ativo", True) else "❌"
            options.append(disnake.SelectOption(
                label=svc["nome"][:80],
                value=sid,
                description=f"{ativo_emoji} Estoque: {stock_label}",
            ))
        disabled = False

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder=f"[{len(servicos)}] Selecione um serviço",
                custom_id="Gerador_Servicos_Select",
                options=options,
                disabled=disabled,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Serviço", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id="Gerador_Servicos_Criar"),
            disnake.ui.Button(label="Ver Grupos", emoji=emoji.members, style=disnake.ButtonStyle.grey,
                              custom_id="Gerador_PainelGrupos"),
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title="Gerenciar Serviços",
            description=f"-# Painel > Gerador > **Serviços**\n\nSelecione um serviço para configurar ou crie um novo.",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerador > **Serviços**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Selecione um serviço para configurar ou crie um novo.\n**Total:** `{len(servicos)}`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_groups_panel(mode: str) -> dict:
    grupos = list_groups()
    servicos = list_services()

    if not grupos:
        options = [disnake.SelectOption(label="Nenhum grupo criado", value="__none__")]
        disabled = True
    else:
        options = []
        for gid, grp in list(grupos.items())[:25]:
            count = sum(1 for s in servicos.values() if s.get("grupo_id") == gid)
            options.append(disnake.SelectOption(
                label=grp["nome"][:80],
                value=gid,
                description=f"Serviços: {count}",
            ))
        disabled = False

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder=f"[{len(grupos)}] Selecione um grupo",
                custom_id="Gerador_Grupos_Select",
                options=options,
                disabled=disabled,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Grupo", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id="Gerador_Grupos_Criar"),
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title="Grupos de Serviços",
            description="-# Painel > Gerador > **Grupos**\n\nAgrupe serviços (ex: Free, VIP, Premium).",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelServicos")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerador > **Grupos**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Agrupe serviços em categorias (ex: Free, VIP, Premium)."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelServicos")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_service_detail(mode: str, service_id: str) -> dict:
    svc = get_service(service_id)
    if not svc:
        return build_services_panel(mode)

    cfg = load_config()
    grupos = cfg.get("grupos", {})
    grupo = grupos.get(svc.get("grupo_id", ""), {})
    grupo_nome = grupo.get("nome", "Sem grupo")

    stock = get_stock_count(service_id)
    fake = svc.get("stock_fake", {}).get("enabled", False)
    stock_label = "♾ FAKE (infinito)" if fake else str(stock)
    ativo = svc.get("ativo", True)

    aliases = ", ".join(svc.get("alias", []))
    cargos_perm = svc.get("cargos_permitidos", [])
    cargos_bloq = svc.get("cargos_bloqueados", [])
    enviar_dm = svc.get("enviar_dm")
    cooldown = svc.get("cooldown_segundos")
    max_dia = svc.get("max_por_dia")

    body = (
        f"{'✅' if ativo else '❌'} **Ativo:** `{'Sim' if ativo else 'Não'}`\n"
        f"{emoji.cardbox} **Estoque:** `{stock_label}`\n"
        f"{emoji.members} **Grupo:** `{grupo_nome}`\n"
        f"{emoji.route} **Aliases:** `{aliases or svc['nome']}`\n"
        f"{emoji.member} **Cargos permitidos:** `{len(cargos_perm)} configurados`\n"
        f"{emoji.wrong} **Cargos bloqueados:** `{len(cargos_bloq)} configurados`\n"
        f"{emoji.information} **Destino:** `{'DM' if enviar_dm is True else 'Canal' if enviar_dm is False else 'Herda global'}`\n"
        f"{emoji.clock} **Cooldown:** `{cooldown if cooldown is not None else 'Herda global'}`\n"
        f"{emoji.warn} **Máx/dia:** `{max_dia if max_dia is not None else 'Herda global'}`"
    )

    row1 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Editar Básico", emoji=emoji.edit, style=disnake.ButtonStyle.blurple,
                          custom_id=f"Gerador_Servico_EditarBasico:{service_id}"),
        disnake.ui.Button(label="Estoque", emoji=emoji.cardbox, style=disnake.ButtonStyle.blurple,
                          custom_id=f"Gerador_Servico_Estoque:{service_id}"),
        disnake.ui.Button(label="Mensagem", emoji=emoji.message, style=disnake.ButtonStyle.blurple,
                          custom_id=f"Gerador_Servico_Mensagem:{service_id}"),
    )
    row2 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Permissões", emoji=emoji.role, style=disnake.ButtonStyle.grey,
                          custom_id=f"Gerador_Servico_Permissoes:{service_id}"),
        disnake.ui.Button(label="Configurações", emoji=emoji.settings2, style=disnake.ButtonStyle.grey,
                          custom_id=f"Gerador_Servico_Config:{service_id}"),
        disnake.ui.Button(label="Stock Fake", emoji=emoji.infinity,
                          style=disnake.ButtonStyle.red if not fake else disnake.ButtonStyle.green,
                          custom_id=f"Gerador_Servico_ToggleFake:{service_id}"),
    )
    row3 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Ativar" if not ativo else "Desativar",
                          emoji=emoji.on if not ativo else emoji.off,
                          style=disnake.ButtonStyle.green if not ativo else disnake.ButtonStyle.red,
                          custom_id=f"Gerador_Servico_ToggleAtivo:{service_id}"),
        disnake.ui.Button(label="Apagar Serviço", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                          custom_id=f"Gerador_Servico_Apagar:{service_id}"),
    )

    if mode == "embed":
        embed = disnake.Embed(
            title=f"Serviço: {svc['nome']}",
            description=f"-# Painel > Gerador > Serviços > **{svc['nome']}**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": [row1, row2, row3, disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelServicos")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerador > Serviços > **{svc['nome']}**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                row1, row2, row3,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Gerador_PainelServicos")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_service_config_panel(mode: str, service_id: str) -> dict:
    """Painel de configurações específicas do serviço (sobrescrever globals)."""
    svc = get_service(service_id)
    if not svc:
        return build_services_panel(mode)

    enviar_dm = svc.get("enviar_dm")
    apagar = svc.get("apagar_trigger")
    mostrar = svc.get("mostrar_quem_gerou")
    cooldown = svc.get("cooldown_segundos")
    max_dia = svc.get("max_por_dia")

    body = (
        f"**Configurações específicas — substituem o padrão global.**\n\n"
        f"{emoji.member} **Destino:** `{'DM' if enviar_dm is True else 'Canal' if enviar_dm is False else 'Herda global'}`\n"
        f"{emoji.delete} **Apagar trigger:** `{'Sim' if apagar is True else 'Não' if apagar is False else 'Herda global'}`\n"
        f"{emoji.member} **Mostrar quem gerou:** `{'Sim' if mostrar is True else 'Não' if mostrar is False else 'Herda global'}`\n"
        f"{emoji.clock} **Cooldown:** `{cooldown if cooldown is not None else 'Herda global'}`\n"
        f"{emoji.warn} **Máx/dia:** `{max_dia if max_dia is not None else 'Herda global'}`"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label=f"Destino: {'Canal→DM' if enviar_dm is False else 'DM→Canal' if enviar_dm is True else 'Definir destino'}",
                emoji=emoji.member, style=disnake.ButtonStyle.grey,
                custom_id=f"Gerador_SvcConfig_ToggleDM:{service_id}"),
            disnake.ui.Button(
                label=f"Apagar: {'Não→Sim' if apagar is False else 'Sim→Não' if apagar is True else 'Definir'}",
                emoji=emoji.delete, style=disnake.ButtonStyle.grey,
                custom_id=f"Gerador_SvcConfig_ToggleApagar:{service_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Cooldown", emoji=emoji.clock, style=disnake.ButtonStyle.blurple,
                              custom_id=f"Gerador_SvcConfig_Cooldown:{service_id}"),
            disnake.ui.Button(label="Limite Diário", emoji=emoji.warn, style=disnake.ButtonStyle.blurple,
                              custom_id=f"Gerador_SvcConfig_MaxDia:{service_id}"),
            disnake.ui.Button(label="Resetar p/ Global", emoji=emoji.reload, style=disnake.ButtonStyle.red,
                              custom_id=f"Gerador_SvcConfig_Reset:{service_id}"),
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title=f"Config: {svc['nome']}",
            description=f"-# Painel > Gerador > {svc['nome']} > **Configurações**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Servico_Detalhe:{service_id}")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerador > {svc['nome']} > **Configurações**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Gerador_Servico_Detalhe:{service_id}")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_permissions_panel(mode: str, service_id: str) -> dict:
    svc = get_service(service_id)
    if not svc:
        return build_services_panel(mode)

    cargos_perm = svc.get("cargos_permitidos", [])
    cargos_bloq = svc.get("cargos_bloqueados", [])
    canais_perm = svc.get("canais_permitidos", [])
    canais_bloq = svc.get("canais_bloqueados", [])

    body = (
        f"{emoji.role} **Cargos permitidos:** `{len(cargos_perm)}` (vazio = todos)\n"
        f"{emoji.wrong} **Cargos bloqueados:** `{len(cargos_bloq)}`\n"
        f"{emoji.textc} **Canais permitidos:** `{len(canais_perm)}` (vazio = todos)\n"
        f"{emoji.wrong} **Canais bloqueados:** `{len(canais_bloq)}`"
    )

    def _defaults_role(ids, guild_id=None):
        return [disnake.SelectDefaultValue(id=int(i), type=disnake.SelectDefaultValueType.role) for i in ids if i]

    def _defaults_channel(ids):
        return [disnake.SelectDefaultValue(id=int(i), type=disnake.SelectDefaultValueType.channel) for i in ids if i]

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Cargos PERMITIDOS (vazio = todos)",
                custom_id=f"Gerador_Perm_CargosPerm:{service_id}",
                min_values=0, max_values=25,
                default_values=_defaults_role(cargos_perm) or None,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Cargos BLOQUEADOS",
                custom_id=f"Gerador_Perm_CargosBloq:{service_id}",
                min_values=0, max_values=25,
                default_values=_defaults_role(cargos_bloq) or None,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Canais PERMITIDOS (vazio = todos)",
                custom_id=f"Gerador_Perm_CanaisPerm:{service_id}",
                channel_types=[disnake.ChannelType.text],
                min_values=0, max_values=25,
                default_values=_defaults_channel(canais_perm) or None,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Canais BLOQUEADOS",
                custom_id=f"Gerador_Perm_CanaisBloq:{service_id}",
                channel_types=[disnake.ChannelType.text],
                min_values=0, max_values=25,
                default_values=_defaults_channel(canais_bloq) or None,
            )
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title=f"Permissões: {svc['nome']}",
            description=f"-# Painel > Gerador > {svc['nome']} > **Permissões**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Servico_Detalhe:{service_id}")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerador > {svc['nome']} > **Permissões**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Gerador_Servico_Detalhe:{service_id}")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Modais
# ──────────────────────────────────────────────────────────

class CriarServicoModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Serviço",
            custom_id="Gerador_Servico_CriarModal",
            components=[
                disnake.ui.TextInput(label="Nome do serviço (ex: Netflix)", custom_id="nome",
                                     required=True, max_length=50),
                disnake.ui.TextInput(label="palavras-chave (sep. por vírgula)",
                                     custom_id="aliases", required=False, max_length=200,
                                     placeholder="netflix, net, nflx"),
                disnake.ui.TextInput(label="Descrição (opcional)", custom_id="descricao",
                                     style=disnake.TextInputStyle.paragraph, required=False, max_length=500),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome = inter.text_values["nome"].strip()
        aliases_raw = inter.text_values.get("aliases", "").strip()
        descricao = inter.text_values.get("descricao", "").strip()

        aliases = [a.strip().lower() for a in aliases_raw.split(",") if a.strip()] if aliases_raw else [nome.lower()]
        if nome.lower() not in aliases:
            aliases.insert(0, nome.lower())

        sid = create_service(nome)
        update_service(sid, {"alias": aliases, "descricao": descricao})

        mode = _mode()
        panel = build_service_detail(mode, sid)
        if mode == "embed":
            await (embed_message.wait if mode == "embed" else message.wait)(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class EditarServicoBasicoModal(disnake.ui.Modal):
    def __init__(self, service_id: str):
        self.service_id = service_id
        svc = get_service(service_id) or {}
        super().__init__(
            title="Editar Serviço",
            custom_id=f"Gerador_Servico_EditBasicoModal:{service_id}",
            components=[
                disnake.ui.TextInput(label="Nome", custom_id="nome", value=svc.get("nome", ""),
                                     required=True, max_length=50),
                disnake.ui.TextInput(label="Aliases (sep por vírgula)", custom_id="aliases",
                                     value=", ".join(svc.get("alias", [])), required=False, max_length=200),
                disnake.ui.TextInput(label="Descrição", custom_id="descricao",
                                     style=disnake.TextInputStyle.paragraph,
                                     value=svc.get("descricao", ""), required=False, max_length=500),
                disnake.ui.TextInput(label="URL da imagem (thumbnail/banner)", custom_id="imagem_url",
                                     value=svc.get("imagem_url", ""), required=False, max_length=300),
                disnake.ui.TextInput(label="Cor hex (ex: #FF5733)", custom_id="cor_hex",
                                     value=svc.get("cor_hex", ""), required=False, max_length=7),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome = inter.text_values["nome"].strip()
        aliases_raw = inter.text_values.get("aliases", "")
        aliases = [a.strip().lower() for a in aliases_raw.split(",") if a.strip()] if aliases_raw else [nome.lower()]
        if nome.lower() not in aliases:
            aliases.insert(0, nome.lower())

        update_service(self.service_id, {
            "nome": nome,
            "alias": aliases,
            "descricao": inter.text_values.get("descricao", "").strip(),
            "imagem_url": inter.text_values.get("imagem_url", "").strip(),
            "cor_hex": inter.text_values.get("cor_hex", "").strip(),
        })

        mode = _mode()
        panel = build_service_detail(mode, self.service_id)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class CriarGrupoModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Grupo",
            custom_id="Gerador_Grupo_CriarModal",
            components=[
                disnake.ui.TextInput(label="Nome do grupo (ex: Free, VIP)", custom_id="nome",
                                     required=True, max_length=50),
                disnake.ui.TextInput(label="Descrição (opcional)", custom_id="descricao",
                                     style=disnake.TextInputStyle.paragraph, required=False, max_length=300),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome = inter.text_values["nome"].strip()
        descricao = inter.text_values.get("descricao", "").strip()
        gid = create_group(nome)
        cfg = load_config()
        cfg["grupos"][gid]["descricao"] = descricao
        save_config(cfg)

        mode = _mode()
        panel = build_groups_panel(mode)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class SvcConfigCooldownModal(disnake.ui.Modal):
    def __init__(self, service_id: str):
        self.service_id = service_id
        svc = get_service(service_id) or {}
        super().__init__(
            title="Cooldown do Serviço",
            custom_id=f"Gerador_SvcConfig_CooldownModal:{service_id}",
            components=[
                disnake.ui.TextInput(
                    label="Segundos (0 =sem cdwn, vazio=herda global)",
                    custom_id="cooldown",
                    value=str(svc.get("cooldown_segundos", "")) if svc.get("cooldown_segundos") is not None else "",
                    required=False, max_length=6,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        val_raw = inter.text_values.get("cooldown", "").strip()
        val = int(val_raw) if val_raw.isdigit() else None
        update_service(self.service_id, {"cooldown_segundos": val})
        mode = _mode()
        panel = build_service_config_panel(mode, self.service_id)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class SvcConfigMaxDiaModal(disnake.ui.Modal):
    def __init__(self, service_id: str):
        self.service_id = service_id
        svc = get_service(service_id) or {}
        super().__init__(
            title="Limite Diário do Serviço",
            custom_id=f"Gerador_SvcConfig_MaxDiaModal:{service_id}",
            components=[
                disnake.ui.TextInput(
                    label="Máx/dia (0 = ilimitado, vazio = herda global)",
                    custom_id="max_dia",
                    value=str(svc.get("max_por_dia", "")) if svc.get("max_por_dia") is not None else "",
                    required=False, max_length=5,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        val_raw = inter.text_values.get("max_dia", "").strip()
        val = int(val_raw) if val_raw.isdigit() else None
        update_service(self.service_id, {"max_por_dia": val})
        mode = _mode()
        panel = build_service_config_panel(mode, self.service_id)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class StockFakeMensagemModal(disnake.ui.Modal):
    def __init__(self, service_id: str):
        self.service_id = service_id
        svc = get_service(service_id) or {}
        fake = svc.get("stock_fake", {})
        super().__init__(
            title="Mensagem do Stock Fake",
            custom_id=f"Gerador_SvcFakeMsgModal:{service_id}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem entregue (use {user} para mencionar)",
                    custom_id="msg_fake",
                    style=disnake.TextInputStyle.paragraph,
                    value=fake.get("mensagem_fake") or "✅ {user} aqui está o seu acesso!\n\n`FAKE_ACCOUNT_DATA`",
                    required=True, max_length=1000,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        msg = inter.text_values["msg_fake"]
        svc = get_service(self.service_id) or {}
        fake = svc.get("stock_fake", {})
        fake["mensagem_fake"] = msg
        update_service(self.service_id, {"stock_fake": fake})
        mode = _mode()
        panel = build_service_detail(mode, self.service_id)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class GeradorServicosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_panel(self, inter, panel: dict):
        mode = _mode()
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
            await inter.edit_original_message(**panel, flags=flags)

    async def _wait_and_send(self, inter, panel: dict):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        await self._send_panel(inter, panel)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid == "Gerador_PainelServicos":
            await self._wait_and_send(inter, build_services_panel(_mode()))

        elif cid == "Gerador_PainelGrupos":
            await self._wait_and_send(inter, build_groups_panel(_mode()))

        elif cid == "Gerador_Servicos_Criar":
            await inter.response.send_modal(CriarServicoModal())

        elif cid == "Gerador_Grupos_Criar":
            await inter.response.send_modal(CriarGrupoModal())

        elif cid.startswith("Gerador_Servico_Detalhe:"):
            sid = cid.split(":", 1)[1]
            await self._wait_and_send(inter, build_service_detail(_mode(), sid))

        elif cid.startswith("Gerador_Servico_EditarBasico:"):
            sid = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarServicoBasicoModal(sid))

        elif cid.startswith("Gerador_Servico_ToggleAtivo:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid)
            if svc:
                update_service(sid, {"ativo": not svc.get("ativo", True)})
            await self._wait_and_send(inter, build_service_detail(_mode(), sid))

        elif cid.startswith("Gerador_Servico_ToggleFake:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid) or {}
            fake = svc.get("stock_fake", {})
            current = fake.get("enabled", False)
            if not current:
                # Ativar → pedir mensagem
                fake["enabled"] = True
                update_service(sid, {"stock_fake": fake})
                await inter.response.send_modal(StockFakeMensagemModal(sid))
                return
            else:
                fake["enabled"] = False
                update_service(sid, {"stock_fake": fake})
            await self._wait_and_send(inter, build_service_detail(_mode(), sid))

        elif cid.startswith("Gerador_Servico_Apagar:"):
            sid = cid.split(":", 1)[1]
            delete_service(sid)
            await self._wait_and_send(inter, build_services_panel(_mode()))

        elif cid.startswith("Gerador_Servico_Permissoes:"):
            sid = cid.split(":", 1)[1]
            await self._wait_and_send(inter, build_permissions_panel(_mode(), sid))

        elif cid.startswith("Gerador_Servico_Config:"):
            sid = cid.split(":", 1)[1]
            await self._wait_and_send(inter, build_service_config_panel(_mode(), sid))

        # Config por serviço
        elif cid.startswith("Gerador_SvcConfig_ToggleDM:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid) or {}
            current = svc.get("enviar_dm")
            # ciclo: None → True → False → None
            next_val = True if current is None else (False if current is True else None)
            update_service(sid, {"enviar_dm": next_val})
            await self._wait_and_send(inter, build_service_config_panel(_mode(), sid))

        elif cid.startswith("Gerador_SvcConfig_ToggleApagar:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid) or {}
            current = svc.get("apagar_trigger")
            next_val = True if current is None else (False if current is True else None)
            update_service(sid, {"apagar_trigger": next_val})
            await self._wait_and_send(inter, build_service_config_panel(_mode(), sid))

        elif cid.startswith("Gerador_SvcConfig_Cooldown:"):
            sid = cid.split(":", 1)[1]
            await inter.response.send_modal(SvcConfigCooldownModal(sid))

        elif cid.startswith("Gerador_SvcConfig_MaxDia:"):
            sid = cid.split(":", 1)[1]
            await inter.response.send_modal(SvcConfigMaxDiaModal(sid))

        elif cid.startswith("Gerador_SvcConfig_Reset:"):
            sid = cid.split(":", 1)[1]
            update_service(sid, {
                "enviar_dm": None, "apagar_trigger": None,
                "mostrar_quem_gerou": None, "cooldown_segundos": None, "max_por_dia": None
            })
            await self._wait_and_send(inter, build_service_config_panel(_mode(), sid))

        elif cid.startswith("Gerador_Grupo_Apagar:"):
            gid = cid.split(":", 1)[1]
            delete_group(gid)
            await self._wait_and_send(inter, build_groups_panel(_mode()))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""
        mode = _mode()

        if cid == "Gerador_Servicos_Select":
            sid = inter.values[0]
            if sid == "__none__":
                return
            await self._wait_and_send(inter, build_service_detail(mode, sid))

        elif cid == "Gerador_Grupos_Select":
            gid = inter.values[0]
            if gid == "__none__":
                return
            # Mostrar info do grupo com opção de deletar
            cfg = load_config()
            grp = cfg["grupos"].get(gid, {})
            servicos = {k: v for k, v in list_services().items() if v.get("grupo_id") == gid}
            body = (
                f"**Nome:** `{grp.get('nome', '')}`\n"
                f"**Descrição:** {grp.get('descricao') or '`Sem descrição`'}\n"
                f"**Serviços vinculados:** `{len(servicos)}`"
            )
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            if mode == "embed":
                embed = disnake.Embed(title=f"Grupo: {grp.get('nome')}", description=body, **_embed_color())
                await inter.edit_original_message(embed=embed, components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Apagar Grupo", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                          custom_id=f"Gerador_Grupo_Apagar:{gid}"),
                        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                          custom_id="Gerador_PainelGrupos"),
                    )
                ])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Grupo: **{grp.get('nome')}**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(body),
                        disnake.ui.Separator(),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Apagar Grupo", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                              custom_id=f"Gerador_Grupo_Apagar:{gid}"),
                        ),
                        **_accent(),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                          custom_id="Gerador_PainelGrupos")
                    ),
                ], flags=disnake.MessageFlags(is_components_v2=True))

        # Permissões
        elif cid.startswith("Gerador_Perm_CargosPerm:"):
            sid = cid.split(":", 1)[1]
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            update_service(sid, {"cargos_permitidos": [int(v) for v in inter.values]})
            await self._send_panel(inter, build_permissions_panel(mode, sid))

        elif cid.startswith("Gerador_Perm_CargosBloq:"):
            sid = cid.split(":", 1)[1]
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            update_service(sid, {"cargos_bloqueados": [int(v) for v in inter.values]})
            await self._send_panel(inter, build_permissions_panel(mode, sid))

        elif cid.startswith("Gerador_Perm_CanaisPerm:"):
            sid = cid.split(":", 1)[1]
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            update_service(sid, {"canais_permitidos": [int(v) for v in inter.values]})
            await self._send_panel(inter, build_permissions_panel(mode, sid))

        elif cid.startswith("Gerador_Perm_CanaisBloq:"):
            sid = cid.split(":", 1)[1]
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            update_service(sid, {"canais_bloqueados": [int(v) for v in inter.values]})
            await self._send_panel(inter, build_permissions_panel(mode, sid))
