"""
modules/utilitarios/comunidade/registro/cog.py
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from .helpers import (
    carregar_config, salvar_config, accent, get_color, _mode,
    BUTTON_STYLE_MAP, build_registro_components, registrar_log,
    load_json, REGISTRADORES_JSON,
)
from commands.admin.anunciar.builder import Builder


# ══════════════════════════════════════════════════════════════════════════════
# MODAIS — Páginas (com RoleSelect via disnake.ui.Label, igual RestockNotify)
# ══════════════════════════════════════════════════════════════════════════════

class PaginaModal(disnake.ui.Modal):
    """5 RoleSelects num modal, igual ao RestockNotifyChannelModal mas com cargos."""
    def __init__(self, num: int):
        self.num = num
        cfg = carregar_config()
        pag = cfg.get("paginas", {}).get(str(num), {})
        cargos_atuais = pag.get("cargos", [])

        components = []
        for i in range(5):
            components.append(
                disnake.ui.Label(
                    text=f"Cargo {i + 1} da Página {num}",
                    component=disnake.ui.RoleSelect(
                        placeholder=f"Cargo {i + 1} (opcional)",
                        custom_id=f"cargo_{i + 1}",
                        required=False,
                    ),
                    description="Selecione o cargo que aparecerá nesta posição.",
                )
            )

        super().__init__(
            title=f"Configurar Página {num}",
            custom_id=f"Registro_PaginaModal:{num}",
            components=components,
        )


class CargosExtraModal(disnake.ui.Modal):
    """Modal com 5 RoleSelects para configurar cargos a adicionar ou remover."""
    def __init__(self, tipo: str):
        # tipo: "adicionar" | "remover"
        self.tipo = tipo
        label_map = {"adicionar": "Adicionar ao registrar", "remover": "Remover ao registrar"}
        components = []
        for i in range(5):
            components.append(
                disnake.ui.Label(
                    text=f"Cargo {i + 1}",
                    
                    component=disnake.ui.RoleSelect(
                        placeholder=f"Cargo {i + 1} (opcional)",
                        custom_id=f"cargo_{i + 1}",
                        required=False,
                    ),
                    description=label_map.get(tipo, ""),
                )
            )
        super().__init__(
            title=f"Cargos para {tipo.capitalize()}",
            custom_id=f"Registro_CargosExtraModal:{tipo}",
            components=components,
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAINEL BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _painel_components(inter=None) -> list:
    cfg = carregar_config()
    modo = cfg.get("modo", "manual")
    cargo_reg_id = cfg.get("cargo_registrador")
    cargo_lider_id = cfg.get("cargo_lider")
    canal_logs_id = cfg.get("canal_logs")
    modo_label = "Manual" if modo == "manual" else "Automático"

    cargo_reg_txt = f"<@&{cargo_reg_id}>" if cargo_reg_id else "`Não configurado`"
    cargo_lider_txt = f"<@&{cargo_lider_id}>" if cargo_lider_id else "`Não configurado`"
    logs_txt = f"<#{canal_logs_id}>" if canal_logs_id else "`Não configurado`"

    resumo = (
        f"{emoji.on if modo == 'automatico' else emoji.off} **Modo:** `{modo_label}`\n"
        f"{emoji.role} **Cargo Registrador:** {cargo_reg_txt}\n"
        f"{emoji.role} **Cargo Líder:** {cargo_lider_txt}\n"
        f"{emoji.textc} **Logs:** {logs_txt}"
    )

    # Linha 1: toggle modo, páginas
    linha1 = [
        disnake.ui.Button(
            label=f"Modo: {modo_label}",
            style=disnake.ButtonStyle.blurple if modo == "automatico" else disnake.ButtonStyle.gray,
            emoji=emoji.power,
            custom_id="Registro_ToggleModo",
        ),
        disnake.ui.Button(
            label="Páginas",
            style=disnake.ButtonStyle.gray,
            emoji=emoji.commands,
            custom_id="Registro_Paginas",
        ),
    ]
    # Modo automático: botão personalizar mensagem
    if modo == "automatico":
        linha1.append(disnake.ui.Button(
            label="Personalizar Mensagem",
            style=disnake.ButtonStyle.blurple,
            emoji=emoji.message,
            custom_id="Registro_PersonalizarMensagem",
        ))

    # Linha 2: staffs e logs — cada um edita o painel pro select
    linha2 = [
        disnake.ui.Button(label="Cargo Registrador", style=disnake.ButtonStyle.gray, emoji=emoji.role, custom_id="Registro_SetCargoRegistrador"),
        disnake.ui.Button(label="Cargo Líder",        style=disnake.ButtonStyle.gray, emoji=emoji.role, custom_id="Registro_SetCargoLider"),
        disnake.ui.Button(label="Logs",               style=disnake.ButtonStyle.gray, emoji=emoji.textc, custom_id="Registro_SetLogs"),
    ]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Comunidade > **Sistema de Registro**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Configure o sistema de registro de membros do servidor."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(resumo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(*linha1),
            disnake.ui.ActionRow(*linha2),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Comunidade_VoltarFeature"),
        ),
    ]


def _painel_embed(inter=None) -> tuple:
    cfg = carregar_config()
    modo = cfg.get("modo", "manual")
    cargo_reg_id = cfg.get("cargo_registrador")
    cargo_lider_id = cfg.get("cargo_lider")
    canal_logs_id = cfg.get("canal_logs")
    modo_label = "Manual" if modo == "manual" else "Automático"

    embed = disnake.Embed(
        title="Sistema de Registro",
        description=(
            f"-# Painel > Comunidade > **Sistema de Registro**\n\n"
            f"**Modo:** `{modo_label}`\n"
            f"**Cargo Registrador:** {f'<@&{cargo_reg_id}>' if cargo_reg_id else '`Não configurado`'}\n"
            f"**Cargo Líder:** {f'<@&{cargo_lider_id}>' if cargo_lider_id else '`Não configurado`'}\n"
            f"**Logs:** {f'<#{canal_logs_id}>' if canal_logs_id else '`Não configurado`'}"
        ),
        color=get_color(),
    )

    linha1 = [
        disnake.ui.Button(label=f"Modo: {modo_label}", style=disnake.ButtonStyle.blurple if modo == "automatico" else disnake.ButtonStyle.gray, emoji=emoji.power, custom_id="Registro_ToggleModo"),
        disnake.ui.Button(label="Páginas", style=disnake.ButtonStyle.gray, emoji=emoji.commands, custom_id="Registro_Paginas"),
    ]
    if modo == "automatico":
        linha1.append(disnake.ui.Button(label="Personalizar Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id="Registro_PersonalizarMensagem"))

    components = [
        disnake.ui.ActionRow(*linha1),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Cargo Registrador", style=disnake.ButtonStyle.gray, emoji=emoji.role, custom_id="Registro_SetCargoRegistrador"),
            disnake.ui.Button(label="Cargo Líder",        style=disnake.ButtonStyle.gray, emoji=emoji.role, custom_id="Registro_SetCargoLider"),
            disnake.ui.Button(label="Logs",               style=disnake.ButtonStyle.gray, emoji=emoji.textc, custom_id="Registro_SetLogs"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Comunidade_VoltarFeature"),
        ),
    ]
    return embed, components


def _paginas_panel() -> list:
    cfg = carregar_config()
    paginas = cfg.get("paginas", {})
    cargo_rem = cfg.get("cargo_remover", [])
    cargo_add = cfg.get("cargo_adicionar", [])

    linhas = []
    for num in range(1, 6):
        pag = paginas.get(str(num), {})
        cargos = pag.get("cargos", [])
        cargos_str = " ".join(f"<@&{c}>" for c in cargos) if cargos else "`Nenhum`"
        linhas.append(f"**Página {num}:** {cargos_str}")

    rem_str = " ".join(f"<@&{c}>" for c in cargo_rem) if cargo_rem else "`Nenhum`"
    add_str = " ".join(f"<@&{c}>" for c in cargo_add) if cargo_add else "`Nenhum`"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Comunidade > Registro > **Páginas**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Configure os cargos de cada página.\n"
                "Cada página exibe até 5 cargos selecionáveis para o usuário."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("\n".join(linhas)),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.minus} **Cargos Remover ao registrar:** {rem_str}\n"
                f"{emoji.plus} **Cargos Adicionar ao registrar:** {add_str}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Página 1", style=disnake.ButtonStyle.gray, custom_id="Registro_EditarPagina:1"),
                disnake.ui.Button(label="Página 2", style=disnake.ButtonStyle.gray, custom_id="Registro_EditarPagina:2"),
                disnake.ui.Button(label="Página 3", style=disnake.ButtonStyle.gray, custom_id="Registro_EditarPagina:3"),
                disnake.ui.Button(label="Página 4", style=disnake.ButtonStyle.gray, custom_id="Registro_EditarPagina:4"),
                disnake.ui.Button(label="Página 5", style=disnake.ButtonStyle.gray, custom_id="Registro_EditarPagina:5"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cargo Remover", style=disnake.ButtonStyle.red,   emoji=emoji.minus, custom_id="Registro_CargosRemover"),
                disnake.ui.Button(label="Cargo Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus,  custom_id="Registro_CargosAdicionar"),
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Registro_VoltarPainel"),
        ),
    ]


# ── Painel "Personalizar Mensagem" — idêntico ao editor do MsgAuto ─────────────

def _msg_editor_panel(cfg: dict) -> list:
    """Editor de mensagem do registro, igual ao PainelEditor do MsgAuto."""
    editor = cfg.get("mensagem", {})
    has_message   = bool(editor.get("content"))
    embed_data    = editor.get("embed", {})
    has_embed     = any(embed_data.get(k) for k in ("title", "description", "footer"))
    has_image     = bool(editor.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
    has_container = bool(editor.get("container"))
    botoes        = editor.get("botoes", [])
    has_buttons   = isinstance(botoes, list) and len(botoes) > 0
    limite_botoes = isinstance(botoes, list) and len(botoes) >= 5
    other_disabled = has_container

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Comunidade > Registro > **Personalizar Mensagem**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                "Esta mensagem será enviada no canal quando o modo **Automático** estiver ativo.\n"
                "O botão de registro será adicionado automaticamente abaixo."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Registro_Msg_ApagarContent", disabled=not has_message or other_disabled),
                disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.message, custom_id="Registro_Msg_DefinirMensagem", disabled=other_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Registro_Msg_ApagarEmbed", disabled=not has_embed or other_disabled),
                disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id="Registro_Msg_DefinirEmbed", disabled=other_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Registro_Msg_ApagarImagens", disabled=not has_image),
                disnake.ui.Button(label="Definir Imagens", style=disnake.ButtonStyle.grey, emoji=emoji.image, custom_id="Registro_Msg_DefinirImagens"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Registro_Msg_ApagarContainer", disabled=not has_container),
                disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="Registro_Msg_DefinirContainer", disabled=(has_message or has_embed) and not has_container),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Registro_Msg_ApagarBotao", disabled=not has_buttons),
                disnake.ui.Button(label="Personalizar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Registro_Msg_PersonalizarBotao"),
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="Registro_Msg_Visualizar", disabled=not (has_message or has_embed or has_container or has_image)),
            disnake.ui.Button(label="Enviar Painel no Canal", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id="Registro_Msg_EnviarPainel"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Registro_VoltarPainel"),
        ),
    ]


# ─── Modais do editor de mensagem (idênticos ao MsgAuto) ──────────────────────

class RegistroMsgModal(disnake.ui.Modal):
    """Definir texto da mensagem."""
    def __init__(self, editor: dict):
        super().__init__(
            title="Definir Mensagem",
            custom_id="Registro_MsgModal_Mensagem",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem", custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Texto que aparecerá na mensagem",
                    value=editor.get("content", ""), max_length=2000, required=True,
                )
            ],
        )


class RegistroEmbedModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        embed = editor.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="Registro_MsgModal_Embed",
            components=[
                disnake.ui.TextInput(label="Título",    custom_id="embed_title",       style=disnake.TextInputStyle.short,     required=False, value=embed.get("title", "")),
                disnake.ui.TextInput(label="Descrição", custom_id="embed_description", style=disnake.TextInputStyle.paragraph, required=True,  value=embed.get("description", ""), placeholder="Descrição do embed"),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="embed_color",       style=disnake.TextInputStyle.short,     required=False, value=embed.get("color", ""), placeholder="#FFFFFF"),
                disnake.ui.TextInput(label="Footer",    custom_id="embed_footer",      style=disnake.TextInputStyle.short,     required=False, value=embed.get("footer", "")),
            ],
        )


class RegistroImagensModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        embed = editor.get("embed", {})
        has_embed = bool(embed.get("title") or embed.get("description"))
        comps = [
            disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage", style=disnake.TextInputStyle.short, required=False, value=editor.get("externalImage", "")),
        ]
        if has_embed:
            comps += [
                disnake.ui.TextInput(label="URL do Banner do Embed",     custom_id="banner",    style=disnake.TextInputStyle.short, required=False, value=embed.get("banner", "")),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed",  custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed.get("thumbnail", "")),
            ]
        super().__init__(title="Definir Imagens", custom_id="Registro_MsgModal_Imagens", components=comps)


class RegistroContainerModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        super().__init__(
            title="Definir Container",
            custom_id="Registro_MsgModal_Container",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container", custom_id="container",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}",
                    required=True, value=editor.get("container", ""),
                )
            ],
        )


class RegistroBotaoModal(disnake.ui.Modal):
    """Personalizar o botão de registro (nome, emoji, cor)."""
    def __init__(self, editor: dict):
        btn = editor.get("botao", {})
        super().__init__(
            title="Personalizar Botão de Registro",
            custom_id="Registro_MsgModal_Botao",
            components=[
                disnake.ui.TextInput(label="Nome do botão",  custom_id="nome",      style=disnake.TextInputStyle.short, required=True,  max_length=80,  value=btn.get("nome", "Registrar")),
                disnake.ui.TextInput(label="Emoji (opcional)", custom_id="emoji_btn", style=disnake.TextInputStyle.short, required=False, max_length=64,  value=btn.get("emoji", "")),
                disnake.ui.TextInput(label="Cor (gray/green/red/blue)", custom_id="cor", style=disnake.TextInputStyle.short, required=False, max_length=10, value=btn.get("cor", "gray"), placeholder="gray, green, red, blue"),
            ],
        )


# ── Modal Enviar Painel (ChannelSelect) ───────────────────────────────────────

class EnviarPainelModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Enviar Painel de Registro",
            custom_id="Registro_EnviarPainelModal",
            components=[
                disnake.ui.Label(
                    text="Canal de destino",
                    component=disnake.ui.ChannelSelect(
                        placeholder="Selecione o canal onde o painel será enviado",
                        custom_id="canal_destino",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1, max_values=1,
                    ),
                    description="O painel de registro com o botão será enviado neste canal.",
                ),
            ],
        )


# ══════════════════════════════════════════════════════════════════════════════
# SESSÕES em memória
# ══════════════════════════════════════════════════════════════════════════════

_sessoes: dict[int, dict] = {}


# ══════════════════════════════════════════════════════════════════════════════
# COG
# ══════════════════════════════════════════════════════════════════════════════

class RegistroCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def Painel(self) -> list:
        return _painel_components()

    def PainelEmbed(self) -> tuple:
        return _painel_embed()

    # ─── edit helper ──────────────────────────────────────────────────────────

    async def _edit_painel(self, inter: disnake.MessageInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, comps = _painel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_painel_components(inter),
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    # ─── log ──────────────────────────────────────────────────────────────────

    async def _enviar_log(self, guild, registrador, registrado, cargos_add):
        cfg = carregar_config()
        canal_id = cfg.get("canal_logs")
        if not canal_id:
            return
        canal = guild.get_channel(int(canal_id))
        if not canal:
            return
        cargos_txt = " ".join(r.mention for r in cargos_add) if cargos_add else "`Nenhum`"
        mode = _mode()
        if mode == "embed":
            embed = disnake.Embed(
                title="📋 Novo Registro",
                description=(
                    f"**Registrado:** {registrado.mention} (`{registrado}`)\n"
                    f"**Registrador:** {registrador.mention} (`{registrador}`)\n"
                    f"**Cargos recebidos:** {cargos_txt}"
                ),
                color=get_color() or disnake.Colour.green(),
            )
            await canal.send(embed=embed)
        else:
            await canal.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"## 📋 Novo Registro\n"
                            f"{emoji.role} **Registrado:** {registrado.mention} (`{registrado}`)\n"
                            f"{emoji.role} **Registrador:** {registrador.mention} (`{registrador}`)\n"
                            f"{emoji.plus} **Cargos recebidos:** {cargos_txt}"
                        ),
                        **accent(),
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    # ─── finalizar ────────────────────────────────────────────────────────────

    async def _finalizar(self, inter: disnake.MessageInteraction, sessao: dict, msg_id: int):
        cfg = carregar_config()
        guild = inter.guild
        is_manual = cfg.get("modo") == "manual"

        alvo = guild.get_member(sessao["registrado_id"])
        registrador = inter.author if is_manual else inter.author

        if not alvo:
            await inter.response.send_message(f"{emoji.wrong} Membro não encontrado.", ephemeral=True)
            _sessoes.pop(msg_id, None)
            return

        todos_ids: list[int] = []
        for ids in sessao.get("cargos_selecionados", {}).values():
            todos_ids.extend(ids)
        todos_ids.extend(int(x) for x in cfg.get("cargo_adicionar", []) if x)

        cargos_add: list[disnake.Role] = []
        for rid in set(todos_ids):
            role = guild.get_role(rid)
            if role and role not in alvo.roles:
                try:
                    await alvo.add_roles(role, reason="Registro")
                    cargos_add.append(role)
                except Exception:
                    pass

        for rid in (int(x) for x in cfg.get("cargo_remover", []) if x):
            role = guild.get_role(rid)
            if role and role in alvo.roles:
                try:
                    await alvo.remove_roles(role, reason="Registro")
                except Exception:
                    pass

        _sessoes.pop(msg_id, None)

        try:
            await self._enviar_log(guild, registrador, alvo, cargos_add)
        except Exception:
            pass
        try:
            registrar_log(registrador.id, str(registrador), alvo.id, str(alvo), [r.id for r in cargos_add])
        except Exception:
            pass

        cargos_txt = " ".join(r.mention for r in cargos_add) if cargos_add else "Nenhum"
        await inter.response.edit_message(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"## {emoji.correct} Registro concluído!\n"
                        f"{alvo.mention} foi registrado com sucesso.\n"
                        f"-# Cargos adicionados: {cargos_txt}"
                    ),
                    **accent(),
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )

    # ══════════════════════════════════════════════════════════════════════════
    # BUTTON LISTENER
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def _btn(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Registro_"):
            return

        # ── Toggle modo ───────────────────────────────────────────────────────
        if cid == "Registro_ToggleModo":
            cfg = carregar_config()
            cfg["modo"] = "automatico" if cfg["modo"] == "manual" else "manual"
            salvar_config(cfg)
            await self._edit_painel(inter)
            return

        # ── Páginas ───────────────────────────────────────────────────────────
        if cid == "Registro_Paginas":
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_paginas_panel(),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid.startswith("Registro_EditarPagina:"):
            num = int(cid.split(":")[1])
            cfg = carregar_config()
            editor = cfg.get("paginas", {}).get(str(num), {})
            await inter.response.send_modal(PaginaModal(num))
            return

        if cid == "Registro_CargosRemover":
            await inter.response.send_modal(CargosExtraModal("remover"))
            return

        if cid == "Registro_CargosAdicionar":
            await inter.response.send_modal(CargosExtraModal("adicionar"))
            return

        # ── Staff — editar painel para select ────────────────────────────────
        if cid == "Registro_SetCargoRegistrador":
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_select_staff_panel("registrador"),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Registro_SetCargoLider":
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_select_staff_panel("lider"),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Registro_SetLogs":
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_select_logs_panel(),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        # ── Voltar ────────────────────────────────────────────────────────────
        if cid == "Registro_VoltarPainel":
            await self._edit_painel(inter)
            return

        # ── Personalizar Mensagem (editor idêntico ao MsgAuto) ────────────────
        if cid == "Registro_PersonalizarMensagem":
            await message.wait(inter, send=False)
            cfg = carregar_config()
            await inter.edit_original_message(
                components=_msg_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        # ── Editor de mensagem — botões de ação ───────────────────────────────
        if cid == "Registro_Msg_DefinirMensagem":
            cfg = carregar_config()
            await inter.response.send_modal(RegistroMsgModal(cfg.get("mensagem", {})))
            return

        if cid == "Registro_Msg_DefinirEmbed":
            cfg = carregar_config()
            await inter.response.send_modal(RegistroEmbedModal(cfg.get("mensagem", {})))
            return

        if cid == "Registro_Msg_DefinirImagens":
            cfg = carregar_config()
            await inter.response.send_modal(RegistroImagensModal(cfg.get("mensagem", {})))
            return

        if cid == "Registro_Msg_DefinirContainer":
            cfg = carregar_config()
            await inter.response.send_modal(RegistroContainerModal(cfg.get("mensagem", {})))
            return

        if cid == "Registro_Msg_PersonalizarBotao":
            cfg = carregar_config()
            await inter.response.send_modal(RegistroBotaoModal(cfg.get("mensagem", {})))
            return

        if cid == "Registro_Msg_EnviarPainel":
            await inter.response.send_modal(EnviarPainelModal())
            return

        if cid == "Registro_Msg_Visualizar":
            await inter.response.defer(ephemeral=True)
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            data = editor.copy()
            btn = data.get("botao", {})
            btn_nome  = btn.get("nome", "Registrar")
            btn_emoji_raw = btn.get("emoji", "")
            btn_cor   = btn.get("cor", "gray")
            btn_style = BUTTON_STYLE_MAP.get(btn_cor, disnake.ButtonStyle.gray)
            try:
                btn_emoji = disnake.PartialEmoji.from_str(btn_emoji_raw) if btn_emoji_raw else None
            except Exception:
                btn_emoji = btn_emoji_raw or None

            registro_btn = disnake.ui.Button(label=btn_nome, style=btn_style, emoji=btn_emoji, custom_id="Registro_IniciarAuto_Preview", disabled=True)

            if data.get("botoes") or data.get("buttons"):
                data.setdefault("buttons", data.pop("botoes", []))
            else:
                data["buttons"] = []

            built = Builder.build_from_cfg({"message": data})
            await _send_built_with_btn(inter, built, registro_btn, ephemeral=True)
            return

        if cid in ("Registro_Msg_ApagarContent", "Registro_Msg_ApagarEmbed",
                   "Registro_Msg_ApagarImagens", "Registro_Msg_ApagarContainer",
                   "Registro_Msg_ApagarBotao"):
            field_map = {
                "Registro_Msg_ApagarContent":   "content",
                "Registro_Msg_ApagarEmbed":     "embed",
                "Registro_Msg_ApagarContainer": "container",
                "Registro_Msg_ApagarBotao":     "botao",
            }
            await message.wait(inter, send=False)
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            if cid == "Registro_Msg_ApagarImagens":
                editor.pop("externalImage", None)
                editor.get("embed", {}).pop("banner", None)
                editor.get("embed", {}).pop("thumbnail", None)
            else:
                field = field_map.get(cid)
                if field:
                    editor.pop(field, None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await inter.edit_original_message(
                components=_msg_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        # ════════════════════════════════════════════════════════════════════
        # FLUXO DE REGISTRO
        # ════════════════════════════════════════════════════════════════════

        if cid == "Registro_IniciarAuto":
            cfg = carregar_config()
            paginas = cfg.get("paginas", {})
            primeira = next((int(k) for k in sorted(paginas.keys()) if paginas[k].get("cargos")), 1)
            sessao = {"pagina": primeira, "cargos_selecionados": {}, "registrado_id": inter.author.id, "registrador_id": None}
            comps = build_registro_components(cfg, primeira, {}, inter.guild, registrado_id=inter.author.id)
            await inter.response.send_message(
                components=comps,
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            sent = await inter.original_message()
            _sessoes[sent.id] = sessao
            return

        if cid.startswith("Registro_ToggleCargo:"):
            parts = cid.split(":")
            pagina, cargo_id = int(parts[1]), int(parts[2])
            msg_id = inter.message.id
            sessao = _sessoes.get(msg_id)
            if not sessao:
                await inter.response.send_message(f"{emoji.wrong} Sessão expirada.", ephemeral=True)
                return
            cfg = carregar_config()
            is_manual = cfg.get("modo") == "manual"
            autor_ok = (is_manual and inter.author.id == sessao.get("registrador_id")) or \
                       (not is_manual and inter.author.id == sessao.get("registrado_id"))
            if not autor_ok:
                await inter.response.send_message(f"{emoji.wrong} Você não pode interagir com este registro.", ephemeral=True)
                return
            pag_cargos = sessao.setdefault("cargos_selecionados", {}).setdefault(pagina, [])
            if cargo_id in pag_cargos:
                pag_cargos.remove(cargo_id)
            else:
                pag_cargos.append(cargo_id)
            _sessoes[msg_id] = sessao
            comps = build_registro_components(cfg, pagina, sessao["cargos_selecionados"], inter.guild,
                                              registrado_id=sessao.get("registrado_id"),
                                              registrador_id=sessao.get("registrador_id"))
            await inter.response.edit_message(components=comps, flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid.startswith("Registro_ProxPagina:"):
            pagina_atual = int(cid.split(":")[1])
            msg_id = inter.message.id
            sessao = _sessoes.get(msg_id)
            if not sessao:
                await inter.response.send_message(f"{emoji.wrong} Sessão expirada.", ephemeral=True)
                return
            cfg = carregar_config()
            _check_perm(inter, sessao, cfg)
            nova = pagina_atual + 1
            sessao["pagina"] = nova
            _sessoes[msg_id] = sessao
            comps = build_registro_components(cfg, nova, sessao.get("cargos_selecionados", {}), inter.guild,
                                              registrado_id=sessao.get("registrado_id"),
                                              registrador_id=sessao.get("registrador_id"))
            await inter.response.edit_message(components=comps, flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid.startswith("Registro_PagAnterior:"):
            pagina_atual = int(cid.split(":")[1])
            msg_id = inter.message.id
            sessao = _sessoes.get(msg_id)
            if not sessao:
                await inter.response.send_message(f"{emoji.wrong} Sessão expirada.", ephemeral=True)
                return
            cfg = carregar_config()
            nova = max(1, pagina_atual - 1)
            sessao["pagina"] = nova
            _sessoes[msg_id] = sessao
            comps = build_registro_components(cfg, nova, sessao.get("cargos_selecionados", {}), inter.guild,
                                              registrado_id=sessao.get("registrado_id"),
                                              registrador_id=sessao.get("registrador_id"))
            await inter.response.edit_message(components=comps, flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid == "Registro_Cancelar":
            msg_id = inter.message.id
            _sessoes.pop(msg_id, None)
            await inter.response.edit_message(
                components=[disnake.ui.Container(disnake.ui.TextDisplay(f"## {emoji.wrong} Registro cancelado."), **accent())],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Registro_Finalizar":
            msg_id = inter.message.id
            sessao = _sessoes.get(msg_id)
            if not sessao:
                await inter.response.send_message(f"{emoji.wrong} Sessão expirada.", ephemeral=True)
                return
            await self._finalizar(inter, sessao, msg_id)
            return

    # ══════════════════════════════════════════════════════════════════════════
    # DROPDOWN LISTENER
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def _dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Registro_"):
            return

        if cid == "Registro_SelectCargoRegistrador":
            await message.wait(inter, send=False)
            cfg = carregar_config()
            cfg["cargo_registrador"] = inter.values[0] if inter.values else None
            salvar_config(cfg)
            await self._edit_painel(inter)
            return

        if cid == "Registro_SelectCargoLider":
            await message.wait(inter, send=False)
            cfg = carregar_config()
            cfg["cargo_lider"] = inter.values[0] if inter.values else None
            salvar_config(cfg)
            await self._edit_painel(inter)
            return

        if cid == "Registro_SelectLogs":
            await message.wait(inter, send=False)
            cfg = carregar_config()
            cfg["canal_logs"] = inter.values[0] if inter.values else None
            salvar_config(cfg)
            await self._edit_painel(inter)
            return

    # ══════════════════════════════════════════════════════════════════════════
    # MODAL LISTENER
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_modal_submit")
    async def _modal(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("Registro_"):
            return

        # ── Páginas (RoleSelect) ───────────────────────────────────────────────
        if cid.startswith("Registro_PaginaModal:"):
            num = int(cid.split(":")[1])
            cargos = []
            for i in range(1, 6):
                vals = inter.resolved_values.get(f"cargo_{i}")
                if isinstance(vals, (list, tuple)):
                    vals = vals[0] if vals else None
                if vals:
                    cargos.append(str(vals.id) if hasattr(vals, "id") else str(vals))
            cfg = carregar_config()
            cfg["paginas"][str(num)] = {"cargos": cargos}
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_paginas_panel(),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        # ── Cargos extra (RoleSelect) ──────────────────────────────────────────
        if cid.startswith("Registro_CargosExtraModal:"):
            tipo = cid.split(":")[1]
            cargos = []
            for i in range(1, 6):
                vals = inter.resolved_values.get(f"cargo_{i}")
                if isinstance(vals, (list, tuple)):
                    vals = vals[0] if vals else None
                if vals:
                    cargos.append(str(vals.id) if hasattr(vals, "id") else str(vals))
            cfg = carregar_config()
            cfg[f"cargo_{tipo}"] = cargos
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_paginas_panel(),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        # ── Editor de mensagem ─────────────────────────────────────────────────
        if cid == "Registro_MsgModal_Mensagem":
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["content"] = inter.text_values["content"]
            editor.pop("container", None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=_msg_editor_panel(cfg), flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid == "Registro_MsgModal_Embed":
            def _hex(v):
                if not v: return None
                v = v.strip().lstrip("#")
                if len(v) not in (3, 6): return None
                try: int(v, 16)
                except ValueError: return None
                return f"#{v.upper()}"
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["embed"] = {
                "title":       inter.text_values.get("embed_title"),
                "description": inter.text_values.get("embed_description"),
                "color":       _hex(inter.text_values.get("embed_color")),
                "footer":      inter.text_values.get("embed_footer"),
            }
            editor.pop("container", None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=_msg_editor_panel(cfg), flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid == "Registro_MsgModal_Imagens":
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["externalImage"] = inter.text_values.get("externalImage") or None
            if "banner" in inter.text_values:
                editor.setdefault("embed", {})["banner"] = inter.text_values.get("banner") or None
            if "thumbnail" in inter.text_values:
                editor.setdefault("embed", {})["thumbnail"] = inter.text_values.get("thumbnail") or None
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=_msg_editor_panel(cfg), flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid == "Registro_MsgModal_Container":
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["container"] = inter.text_values["container"]
            editor.pop("content", None)
            editor.pop("embed", None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=_msg_editor_panel(cfg), flags=disnake.MessageFlags(is_components_v2=True))
            return

        if cid == "Registro_MsgModal_Botao":
            cor = inter.text_values.get("cor", "gray").strip().lower()
            if cor not in BUTTON_STYLE_MAP:
                cor = "gray"
            cfg = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["botao"] = {
                "nome":  inter.text_values.get("nome", "Registrar").strip(),
                "emoji": inter.text_values.get("emoji_btn", "").strip(),
                "cor":   cor,
            }
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=_msg_editor_panel(cfg), flags=disnake.MessageFlags(is_components_v2=True))
            return

        # ── Enviar painel (ChannelSelect) ─────────────────────────────────────
        if cid == "Registro_EnviarPainelModal":
            vals = inter.resolved_values.get("canal_destino")
            if isinstance(vals, (list, tuple)):
                vals = vals[0] if vals else None
            if not vals:
                await inter.response.send_message(f"{emoji.wrong} Canal inválido.", ephemeral=True)
                return
            channel_id = vals.id if hasattr(vals, "id") else int(vals)
            channel = inter.guild.get_channel(channel_id)
            if not channel:
                await inter.response.send_message(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
                return
            try:
                cfg = carregar_config()
                editor = cfg.get("mensagem", {})
                btn = editor.get("botao", {})
                btn_nome = btn.get("nome", "Registrar")
                btn_emoji_raw = btn.get("emoji", "")
                btn_cor = btn.get("cor", "gray")
                btn_style = BUTTON_STYLE_MAP.get(btn_cor, disnake.ButtonStyle.gray)
                try:
                    btn_emoji = disnake.PartialEmoji.from_str(btn_emoji_raw) if btn_emoji_raw else None
                except Exception:
                    btn_emoji = btn_emoji_raw or None

                registro_btn = disnake.ui.Button(label=btn_nome, style=btn_style, emoji=btn_emoji, custom_id="Registro_IniciarAuto")

                data = editor.copy()
                data["buttons"] = data.pop("botoes", [])

                built = Builder.build_from_cfg({"message": data})
                sent = await _send_built_with_btn(channel, built, registro_btn)
                await message.wait(inter, send=False)
                cfg2 = carregar_config()
                await inter.edit_original_message(
                    components=_msg_editor_panel(cfg2),
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
                await inter.followup.send(
                    f"{emoji.correct} Painel enviado em {channel.mention}!",
                    ephemeral=True,
                )
            except Exception as e:
                await inter.response.send_message(f"{emoji.wrong} Erro ao enviar: {e}", ephemeral=True)
            return


# ── Select panels (edita o painel para selectmenu) ────────────────────────────

def _select_staff_panel(tipo: str) -> list:
    label_map = {"registrador": "Cargo Registrador", "lider": "Cargo Líder"}
    cid_map   = {"registrador": "Registro_SelectCargoRegistrador", "lider": "Registro_SelectCargoLider"}
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Comunidade > Registro > **{label_map[tipo]}**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"Selecione o cargo de **{label_map[tipo]}**."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder=f"Selecione o {label_map[tipo]}...",
                    custom_id=cid_map[tipo],
                    min_values=0, max_values=1,
                )
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Registro_VoltarPainel"),
        ),
    ]


def _select_logs_panel() -> list:
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Comunidade > Registro > **Canal de Logs**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Selecione o canal onde os logs de registro serão enviados."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal de logs...",
                    custom_id="Registro_SelectLogs",
                    channel_types=[disnake.ChannelType.text],
                    min_values=0, max_values=1,
                )
            ),
            **accent(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Registro_VoltarPainel"),
        ),
    ]


# ── Helper permissão ──────────────────────────────────────────────────────────

def _check_perm(inter: disnake.MessageInteraction, sessao: dict, cfg: dict) -> bool:
    is_manual = cfg.get("modo") == "manual"
    if is_manual:
        return inter.author.id == sessao.get("registrador_id")
    return inter.author.id == sessao.get("registrado_id")


# ── Helper send built + botão de registro ─────────────────────────────────────

async def _send_built_with_btn(target, built: dict, registro_btn: disnake.ui.Button, ephemeral: bool = False):
    """Envia a mensagem buildada e adiciona o botão de registro no final."""
    kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
    if ephemeral and isinstance(target, disnake.Interaction):
        kwargs["ephemeral"] = True

    if built["mode"] == "v2":
        comps = list(built["components"]) + [disnake.ui.ActionRow(registro_btn)]
        kwargs["components"] = comps
        kwargs["flags"] = built.get("flags", disnake.MessageFlags(is_components_v2=True))
    else:
        if built.get("content"):
            kwargs["content"] = built["content"]
        if built.get("embed"):
            kwargs["embed"] = built["embed"]
        comps = list(built.get("components") or []) + [disnake.ui.ActionRow(registro_btn)]
        kwargs["components"] = comps
        if built.get("files"):
            kwargs["files"] = built["files"]

    if isinstance(target, disnake.Interaction):
        return await target.followup.send(**kwargs)
    else:
        return await target.send(**kwargs)


def setup(bot: commands.Bot):
    bot.add_cog(RegistroCog(bot))