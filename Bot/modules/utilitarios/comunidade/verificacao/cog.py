"""
modules/utilitarios/comunidade/verificacao/cog.py

Sistema de Verificação — Amethys Bot
Painel de config + Editor de mensagem (idêntico ao Registro) + Fluxo completo.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from commands.admin.anunciar.builder import Builder

from . import helpers
from .helpers import (
    carregar_config, salvar_config,
    accent, color, _mode,
    load_json, save_json,
    PENDENTES_JSON, CODIGOS_JSON,
    gerar_texto_captcha, gerar_opcoes_captcha,
    criar_sessao_captcha, validar_sessao_captcha,
    limpar_sessao_captcha, validar_codigo,
    _captcha_gen, enviar_log,
)

BUTTON_STYLE_MAP = {
    "gray":  disnake.ButtonStyle.gray,
    "grey":  disnake.ButtonStyle.gray,
    "green": disnake.ButtonStyle.green,
    "red":   disnake.ButtonStyle.red,
    "blue":  disnake.ButtonStyle.blurple,
}


# ─── Editor de mensagem (Personalizar Painel) ─────────────────────────────────

def _editor_panel(cfg: dict) -> list:
    """Editor de mensagem do painel de verificação, idêntico ao do Registro."""
    editor        = cfg.get("mensagem", {})
    has_message   = bool(editor.get("content"))
    embed_data    = editor.get("embed", {})
    has_embed     = any(embed_data.get(k) for k in ("title", "description", "footer"))
    has_image     = bool(editor.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
    has_container = bool(editor.get("container"))
    other_disabled = has_container

    cod_ativo = cfg.get("codigo_ativo", False)
    cap_ativo = cfg.get("captcha_ativo", False)

    primary_hex = db.get_document("custom_colors").get("primary")

    # Botões de personalizar — sempre tem Verificar, condicionais os outros
    btn_row_btns = [
        disnake.ui.Button(label="Botão Verificar", style=disnake.ButtonStyle.grey,
                          emoji=emoji.edit, custom_id="Verif_Msg_PersonalizarBotaoVerif"),
    ]
    if cod_ativo:
        btn_row_btns.append(disnake.ui.Button(
            label="Botão Código", style=disnake.ButtonStyle.grey,
            emoji=emoji.edit, custom_id="Verif_Msg_PersonalizarBotaoCodigo",
        ))
    if cap_ativo:
        btn_row_btns.append(disnake.ui.Button(
            label="Botão Captcha", style=disnake.ButtonStyle.grey,
            emoji=emoji.edit, custom_id="Verif_Msg_PersonalizarBotaoCaptcha",
        ))

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.shield}\n"
                "-# Painel > Verificação > **Personalizar Painel**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                "Personalize a mensagem e os botões do painel enviado no canal."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="Verif_Msg_ApagarContent",
                                  disabled=not has_message or other_disabled),
                disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.message, custom_id="Verif_Msg_DefinirMensagem",
                                  disabled=other_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="Verif_Msg_ApagarEmbed",
                                  disabled=not has_embed or other_disabled),
                disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.embed, custom_id="Verif_Msg_DefinirEmbed",
                                  disabled=other_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="Verif_Msg_ApagarImagens", disabled=not has_image),
                disnake.ui.Button(label="Definir Imagens", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.image, custom_id="Verif_Msg_DefinirImagens"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="Verif_Msg_ApagarContainer", disabled=not has_container),
                disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.commands, custom_id="Verif_Msg_DefinirContainer",
                                  disabled=(has_message or has_embed) and not has_container),
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("-# Personalizar botões"),
            disnake.ui.ActionRow(*btn_row_btns),
            **accent(primary_hex),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey,
                              emoji=emoji.search, custom_id="Verif_Msg_Visualizar",
                              disabled=not (has_message or has_embed or has_container or has_image)),
            disnake.ui.Button(label="Enviar Painel no Canal", style=disnake.ButtonStyle.green,
                              emoji=emoji.arrow, custom_id="Verif_Msg_EnviarPainel"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                              emoji=emoji.back, custom_id="Verif_VoltarPainel"),
        ),
    ]


# ─── Botões do painel público ─────────────────────────────────────────────────

def _build_painel_publico_btns(cfg: dict) -> list[disnake.ui.Button]:
    editor    = cfg.get("mensagem", {})
    cod_ativo = cfg.get("codigo_ativo", False)
    cap_ativo = cfg.get("captcha_ativo", False)

    def _btn(key, default_label, default_emoji, default_style, custom_id):
        b      = editor.get(key, {})
        label  = b.get("nome", default_label) or default_label
        raw_em = b.get("emoji", "")
        cor    = b.get("cor", "")
        style  = BUTTON_STYLE_MAP.get(cor, default_style)
        try:
            em = disnake.PartialEmoji.from_str(raw_em) if raw_em else default_emoji
        except Exception:
            em = default_emoji
        return disnake.ui.Button(label=label, emoji=em, style=style, custom_id=custom_id)

    btns = [_btn("botao_verificar", "Verificar", emoji.correct,
                 disnake.ButtonStyle.green, "Verif_IniciarVerificacao")]
    if cod_ativo:
        btns.append(_btn("botao_codigo", "Código", emoji.commands,
                         disnake.ButtonStyle.blurple, "Verif_VerificarCodigo"))
    if cap_ativo:
        btns.append(_btn("botao_captcha", "Captcha", emoji.shield,
                         disnake.ButtonStyle.grey, "Verif_IniciarCaptcha"))
    return btns


async def _send_built_with_btns(target, built: dict, btns: list[disnake.ui.Button], ephemeral: bool = False):
    kwargs: dict = {"allowed_mentions": disnake.AllowedMentions.none()}
    if ephemeral and isinstance(target, disnake.Interaction):
        kwargs["ephemeral"] = True

    btn_row = disnake.ui.ActionRow(*btns)

    if built["mode"] == "v2":
        comps = list(built["components"]) + [btn_row]
        kwargs["components"] = comps
        kwargs["flags"] = built.get("flags", disnake.MessageFlags(is_components_v2=True))
    else:
        if built.get("content"):
            kwargs["content"] = built["content"]
        if built.get("embed"):
            kwargs["embed"] = built["embed"]
        comps = list(built.get("components") or []) + [btn_row]
        kwargs["components"] = comps
        if built.get("files"):
            kwargs["files"] = built["files"]

    if isinstance(target, disnake.Interaction):
        return await target.followup.send(**kwargs)
    else:
        return await target.send(**kwargs)


# ─── Modais do editor ─────────────────────────────────────────────────────────

class VerifMsgModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        super().__init__(
            title="Definir Mensagem",
            custom_id="Verif_MsgModal_Mensagem",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem", custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Texto que aparecerá na mensagem",
                    value=editor.get("content", ""), max_length=2000, required=True,
                )
            ],
        )


class VerifEmbedModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        embed = editor.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="Verif_MsgModal_Embed",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="embed_title",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=embed.get("title", "")),
                disnake.ui.TextInput(label="Descrição", custom_id="embed_description",
                                     style=disnake.TextInputStyle.paragraph, required=True,
                                     value=embed.get("description", ""),
                                     placeholder="Descrição do embed"),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="embed_color",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=embed.get("color", ""), placeholder="#FFFFFF"),
                disnake.ui.TextInput(label="Footer", custom_id="embed_footer",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=embed.get("footer", "")),
            ],
        )


class VerifImagensModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        embed     = editor.get("embed", {})
        has_embed = bool(embed.get("title") or embed.get("description"))
        comps = [
            disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage",
                                 style=disnake.TextInputStyle.short, required=False,
                                 value=editor.get("externalImage", "")),
        ]
        if has_embed:
            comps += [
                disnake.ui.TextInput(label="URL do Banner do Embed", custom_id="banner",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=embed.get("banner", "")),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed", custom_id="thumbnail",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=embed.get("thumbnail", "")),
            ]
        super().__init__(title="Definir Imagens", custom_id="Verif_MsgModal_Imagens", components=comps)


class VerifContainerModal(disnake.ui.Modal):
    def __init__(self, editor: dict):
        super().__init__(
            title="Definir Container",
            custom_id="Verif_MsgModal_Container",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container", custom_id="container",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}",
                    required=True, value=editor.get("container", ""),
                )
            ],
        )


class VerifBotaoModal(disnake.ui.Modal):
    def __init__(self, editor: dict, tipo: str):
        key  = f"botao_{tipo}"
        btn  = editor.get(key, {})
        defaults = {"verificar": ("Verificar", "green"), "codigo": ("Código", "blue"), "captcha": ("Captcha", "gray")}
        def_nome, def_cor = defaults.get(tipo, ("Verificar", "green"))
        super().__init__(
            title=f"Personalizar Botão — {def_nome}",
            custom_id=f"Verif_MsgModal_Botao_{tipo}",
            components=[
                disnake.ui.TextInput(label="Nome do botão", custom_id="nome",
                                     style=disnake.TextInputStyle.short, required=True,
                                     max_length=80, value=btn.get("nome", def_nome)),
                disnake.ui.TextInput(label="Emoji (opcional)", custom_id="emoji_btn",
                                     style=disnake.TextInputStyle.short, required=False,
                                     max_length=64, value=btn.get("emoji", "")),
                disnake.ui.TextInput(label="Cor (gray/green/red/blue)", custom_id="cor",
                                     style=disnake.TextInputStyle.short, required=False,
                                     max_length=10, value=btn.get("cor", def_cor),
                                     placeholder="gray, green, red, blue"),
            ],
        )


class VerifEnviarPainelModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Enviar Painel de Verificação",
            custom_id="Verif_EnviarPainelModal",
            components=[
                disnake.ui.Label(
                    text="Canal de destino",
                    component=disnake.ui.ChannelSelect(
                        placeholder="Selecione o canal onde o painel será enviado",
                        custom_id="canal_destino",
                        channel_types=[disnake.ChannelType.text],
                    ),
                    description="O painel com os botões de verificação será enviado neste canal.",
                ),
            ],
        )


# ─── Cog ─────────────────────────────────────────────────────────────────────

class VerificacaoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Painel de config ──────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        config      = carregar_config()
        primary_hex = db.get_document("custom_colors").get("primary")
        cod_ativo   = config.get("codigo_ativo", False)
        cap_ativo   = config.get("captcha_ativo", False)
        cap_modo    = config.get("captcha_modo", "modal")
        logs_id     = config.get("logs_canal")
        verificados = config.get("cargo_verificado", [])
        responsaveis = config.get("cargo_responsavel", [])
        expulsar    = config.get("expulsar_recusado", False)

        logs_txt  = f"<#{logs_id}>" if logs_id else "`Não configurado`"
        verif_txt = ", ".join(f"<@&{r}>" for r in verificados)  if verificados  else "`Nenhum`"
        resp_txt  = ", ".join(f"<@&{r}>" for r in responsaveis) if responsaveis else "`Nenhum`"

        resumo = (
            f"{emoji.on if cod_ativo else emoji.off} **Modo Código:** `{'Ativado' if cod_ativo else 'Desativado'}`\n"
            f"{emoji.on if cap_ativo else emoji.off} **Modo Captcha:** `{'Ativado' if cap_ativo else 'Desativado'}`\n"
        )
        if cap_ativo:
            resumo += f"{emoji.commands} **Modo do Captcha:** `{'Modal' if cap_modo == 'modal' else 'Botão'}`\n"
        resumo += (
            f"{emoji.on if expulsar else emoji.off} **Expulsar se recusado:** `{'Sim' if expulsar else 'Não'}`\n"
            f"{emoji.textc} **Logs:** {logs_txt}\n"
            f"{emoji.role} **Cargo verificado:** {verif_txt}\n"
            f"{emoji.role} **Cargo responsável:** {resp_txt}"
        )

        row1_btns = [
            disnake.ui.Button(label="Código", emoji=emoji.power,
                              style=disnake.ButtonStyle.green if cod_ativo else disnake.ButtonStyle.grey,
                              custom_id="Verif_ToggleCodigo"),
            disnake.ui.Button(label="Captcha", emoji=emoji.power,
                              style=disnake.ButtonStyle.green if cap_ativo else disnake.ButtonStyle.grey,
                              custom_id="Verif_ToggleCaptcha"),
        ]
        if cap_ativo:
            row1_btns.append(disnake.ui.Button(
                label=f"Captcha: {'Modal' if cap_modo == 'modal' else 'Botão'}",
                emoji=emoji.edit, style=disnake.ButtonStyle.blurple,
                custom_id="Verif_ToggleCaptchaModo",
            ))
        row1_btns.append(disnake.ui.Button(
            label="Expulsar", emoji=emoji.power,
            style=disnake.ButtonStyle.red if expulsar else disnake.ButtonStyle.grey,
            custom_id="Verif_ToggleExpulsar",
        ))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.shield}\n"
                    "-# Painel > Comunidade > **Verificação**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*row1_btns),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Logs", emoji=emoji.textc,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Verif_ConfigLogs"),
                    disnake.ui.Button(label="Cargo Verificado", emoji=emoji.role,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Verif_ConfigVerificado"),
                    disnake.ui.Button(label="Cargo Responsável", emoji=emoji.role,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Verif_ConfigResponsavel"),
                    disnake.ui.Button(label="Personalizar Painel", emoji=emoji.message,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Verif_PersonalizarPainel"),
                ),
                **accent(primary_hex),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Comunidade_VoltarFeature"),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        config      = carregar_config()
        primary_hex = db.get_document("custom_colors").get("primary")
        cod_ativo   = config.get("codigo_ativo", False)
        cap_ativo   = config.get("captcha_ativo", False)
        cap_modo    = config.get("captcha_modo", "modal")
        logs_id     = config.get("logs_canal")
        verificados = config.get("cargo_verificado", [])
        responsaveis = config.get("cargo_responsavel", [])
        expulsar    = config.get("expulsar_recusado", False)

        logs_txt  = f"<#{logs_id}>" if logs_id else "`Não configurado`"
        verif_txt = ", ".join(f"<@&{r}>" for r in verificados)  if verificados  else "`Nenhum`"
        resp_txt  = ", ".join(f"<@&{r}>" for r in responsaveis) if responsaveis else "`Nenhum`"

        embed = disnake.Embed(title="Sistema de Verificação")
        if primary_hex:
            embed.color = color(primary_hex)
        value = (
            f"{emoji.on if cod_ativo else emoji.off} **Modo Código:** `{'Ativado' if cod_ativo else 'Desativado'}`\n"
            f"{emoji.on if cap_ativo else emoji.off} **Modo Captcha:** `{'Ativado' if cap_ativo else 'Desativado'}`\n"
        )
        if cap_ativo:
            value += f"{emoji.commands} **Modo do Captcha:** `{'Modal' if cap_modo == 'modal' else 'Botão'}`\n"
        value += (
            f"{emoji.on if expulsar else emoji.off} **Expulsar se recusado:** `{'Sim' if expulsar else 'Não'}`\n"
            f"{emoji.textc} **Logs:** {logs_txt}\n"
            f"{emoji.role} **Cargo verificado:** {verif_txt}\n"
            f"{emoji.role} **Cargo responsável:** {resp_txt}"
        )
        embed.add_field(name="Configurações", value=value, inline=False)

        row1_btns = [
            disnake.ui.Button(label="Código", emoji=emoji.power,
                              style=disnake.ButtonStyle.green if cod_ativo else disnake.ButtonStyle.grey,
                              custom_id="Verif_ToggleCodigo"),
            disnake.ui.Button(label="Captcha", emoji=emoji.power,
                              style=disnake.ButtonStyle.green if cap_ativo else disnake.ButtonStyle.grey,
                              custom_id="Verif_ToggleCaptcha"),
        ]
        if cap_ativo:
            row1_btns.append(disnake.ui.Button(
                label=f"Captcha: {'Modal' if cap_modo == 'modal' else 'Botão'}",
                emoji=emoji.edit, style=disnake.ButtonStyle.blurple,
                custom_id="Verif_ToggleCaptchaModo",
            ))
        row1_btns.append(disnake.ui.Button(
            label="Expulsar", emoji=emoji.power,
            style=disnake.ButtonStyle.red if expulsar else disnake.ButtonStyle.grey,
            custom_id="Verif_ToggleExpulsar",
        ))

        components = [
            disnake.ui.ActionRow(*row1_btns),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Logs", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Verif_ConfigLogs"),
                disnake.ui.Button(label="Cargo Verificado", emoji=emoji.role,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Verif_ConfigVerificado"),
                disnake.ui.Button(label="Cargo Responsável", emoji=emoji.role,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Verif_ConfigResponsavel"),
                disnake.ui.Button(label="Personalizar Painel", emoji=emoji.message,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Verif_PersonalizarPainel"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Comunidade_VoltarFeature"),
            ),
        ]
        return embed, components

    # ── Painel de cargos ──────────────────────────────────────────────────────

    @staticmethod
    def _painel_cargos(tipo: str, primary_hex: str | None, mode: str):
        config = carregar_config()
        lista  = config.get(f"cargo_{tipo}", [])
        txt    = ", ".join(f"<@&{r}>" for r in lista) if lista else "`Nenhum`"
        titulo = "Cargo Verificado" if tipo == "verificado" else "Cargo Responsável"

        select_row = disnake.ui.ActionRow(
            disnake.ui.RoleSelect(placeholder=f"Adicionar cargo...",
                                  custom_id=f"Verif_Select_{tipo}")
        )
        btn_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Remover cargo", emoji=emoji.minus,
                              style=disnake.ButtonStyle.red,
                              custom_id=f"Verif_RemoverCargo_{tipo}", disabled=not bool(lista)),
            disnake.ui.Button(label="Limpar tudo", emoji=emoji.wrong,
                              style=disnake.ButtonStyle.red,
                              custom_id=f"Verif_LimparCargos_{tipo}", disabled=not bool(lista)),
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Verif_VoltarPainel"),
        )

        if mode == "embed":
            emb = disnake.Embed(title=titulo, description=f"**Configurados:** {txt}")
            if primary_hex:
                emb.color = color(primary_hex)
            return emb, [select_row, btn_row]
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.role} {titulo}\n**Configurados:** {txt}"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                select_row, btn_row,
                **accent(primary_hex),
            )
        ]

    @staticmethod
    def _painel_remover_cargo(tipo: str, primary_hex: str | None, mode: str):
        config  = carregar_config()
        lista   = config.get(f"cargo_{tipo}", [])
        titulo  = "Cargo Verificado" if tipo == "verificado" else "Cargo Responsável"
        options = [disnake.SelectOption(label=f"ID: {r}", value=str(r)) for r in lista]
        select_row = disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Selecione o cargo para remover...",
                custom_id=f"Verif_ConfirmarRemover_{tipo}",
                options=options or [disnake.SelectOption(label="(vazio)", value="noop")],
                disabled=not bool(options),
            )
        )
        btn_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"Verif_VoltarCargos_{tipo}"),
        )
        if mode == "embed":
            emb = disnake.Embed(title=f"Remover {titulo}", description="Selecione qual cargo remover.")
            if primary_hex:
                emb.color = color(primary_hex)
            return emb, [select_row, btn_row]
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.minus} Remover {titulo}"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                select_row, btn_row,
                **accent(primary_hex),
            )
        ]

    # ── Render helpers ────────────────────────────────────────────────────────

    async def _render_painel(self, inter, mode: str):
        if mode == "embed":
            emb, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=self.Painel())

    async def _render_cargos(self, inter, tipo: str, mode: str, primary_hex: str | None):
        result = self._painel_cargos(tipo, primary_hex, mode)
        if mode == "embed":
            emb, comps = result
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=result)

    # ── Listener de botões ────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _btn(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Verif_"):
            return

        # Sem wait: modais e fluxo público
        if cid == "Verif_VerificarCodigo":
            await inter.response.send_modal(CodigoModal(self.bot))
            return
        if cid == "Verif_IniciarCaptcha":
            await self._iniciar_captcha(inter)
            return
        if cid.startswith("Verif_CaptchaBtn_"):
            await self._checar_captcha_botao(inter, cid)
            return
        if cid == "Verif_IniciarVerificacao":
            await self._iniciar_indicacao(inter)
            return
        if cid.startswith("Verif_Aprovar_") or cid.startswith("Verif_Recusar_"):
            await self._handle_moderacao(inter, cid)
            return

        # Botões do editor que abrem modal (sem wait)
        if cid == "Verif_Msg_DefinirMensagem":
            await inter.response.send_modal(VerifMsgModal(carregar_config().get("mensagem", {})))
            return
        if cid == "Verif_Msg_DefinirEmbed":
            await inter.response.send_modal(VerifEmbedModal(carregar_config().get("mensagem", {})))
            return
        if cid == "Verif_Msg_DefinirImagens":
            await inter.response.send_modal(VerifImagensModal(carregar_config().get("mensagem", {})))
            return
        if cid == "Verif_Msg_DefinirContainer":
            await inter.response.send_modal(VerifContainerModal(carregar_config().get("mensagem", {})))
            return
        if cid.startswith("Verif_Msg_PersonalizarBotao"):
            suffix   = cid.replace("Verif_Msg_PersonalizarBotao", "").lower()
            tipo_map = {"verif": "verificar", "codigo": "codigo", "captcha": "captcha"}
            tipo_key = tipo_map.get(suffix, "verificar")
            await inter.response.send_modal(VerifBotaoModal(carregar_config().get("mensagem", {}), tipo_key))
            return
        if cid == "Verif_Msg_EnviarPainel":
            await inter.response.send_modal(VerifEnviarPainelModal())
            return

        # Com wait: config e editor
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        primary_hex = db.get_document("custom_colors").get("primary")

        if cid == "Verif_PersonalizarPainel":
            cfg = carregar_config()
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Verif_Msg_Visualizar":
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            data   = editor.copy()
            data["buttons"] = data.pop("botoes", [])
            built  = await Builder.build_from_cfg({"message": data})
            btns   = _build_painel_publico_btns(cfg)
            for b in btns:
                b.disabled = True
            await _send_built_with_btns(inter, built, btns, ephemeral=True)
            return

        if cid in ("Verif_Msg_ApagarContent", "Verif_Msg_ApagarEmbed",
                   "Verif_Msg_ApagarImagens", "Verif_Msg_ApagarContainer"):
            field_map = {
                "Verif_Msg_ApagarContent":   "content",
                "Verif_Msg_ApagarEmbed":     "embed",
                "Verif_Msg_ApagarContainer": "container",
            }
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            if cid == "Verif_Msg_ApagarImagens":
                editor.pop("externalImage", None)
                editor.get("embed", {}).pop("banner", None)
                editor.get("embed", {}).pop("thumbnail", None)
            else:
                editor.pop(field_map.get(cid, ""), None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        for toggle_cid, key in [
            ("Verif_ToggleCodigo",   "codigo_ativo"),
            ("Verif_ToggleCaptcha",  "captcha_ativo"),
            ("Verif_ToggleExpulsar", "expulsar_recusado"),
        ]:
            if cid == toggle_cid:
                cfg = carregar_config()
                cfg[key] = not cfg.get(key, False)
                salvar_config(cfg)
                await self._render_painel(inter, mode)
                return

        if cid == "Verif_ToggleCaptchaModo":
            cfg = carregar_config()
            cfg["captcha_modo"] = "botao" if cfg.get("captcha_modo", "modal") == "modal" else "modal"
            salvar_config(cfg)
            await self._render_painel(inter, mode)
            return

        if cid == "Verif_VoltarPainel":
            await self._render_painel(inter, mode)
            return

        if cid == "Verif_ConfigLogs":
            select_row = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(placeholder="Selecione o canal de logs...",
                                         custom_id="Verif_SelectLogs",
                                         channel_types=[disnake.ChannelType.text])
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey, custom_id="Verif_VoltarPainel"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Canal de Logs", description="Selecione o canal de logs.")
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.textc} Canal de Logs\n-# Painel > Verificação > **Logs**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row, **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

        if cid in ("Verif_ConfigVerificado", "Verif_ConfigResponsavel"):
            tipo = "verificado" if cid == "Verif_ConfigVerificado" else "responsavel"
            await self._render_cargos(inter, tipo, mode, primary_hex)
            return

        if cid in ("Verif_RemoverCargo_verificado", "Verif_RemoverCargo_responsavel"):
            tipo   = cid.split("_")[-1]
            result = self._painel_remover_cargo(tipo, primary_hex, mode)
            if mode == "embed":
                emb, comps = result
                await inter.edit_original_message(content=None, embed=emb, components=comps)
            else:
                await inter.edit_original_message(components=result)
            return

        if cid in ("Verif_LimparCargos_verificado", "Verif_LimparCargos_responsavel"):
            tipo = cid.split("_")[-1]
            cfg  = carregar_config()
            cfg[f"cargo_{tipo}"] = []
            salvar_config(cfg)
            await self._render_cargos(inter, tipo, mode, primary_hex)
            return

        if cid in ("Verif_VoltarCargos_verificado", "Verif_VoltarCargos_responsavel"):
            tipo = cid.split("_")[-1]
            await self._render_cargos(inter, tipo, mode, primary_hex)
            return

    # ── Listener de dropdowns ─────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Verif_"):
            return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        primary_hex = db.get_document("custom_colors").get("primary")

        if cid == "Verif_SelectLogs":
            cfg = carregar_config()
            cfg["logs_canal"] = inter.values[0]
            salvar_config(cfg)
            await self._render_painel(inter, mode)
            return

        if cid in ("Verif_Select_verificado", "Verif_Select_responsavel"):
            tipo  = cid.split("_")[-1]
            cfg   = carregar_config()
            lista = cfg.get(f"cargo_{tipo}", [])
            val   = inter.values[0]
            if val not in lista:
                lista.append(val)
            cfg[f"cargo_{tipo}"] = lista
            salvar_config(cfg)
            await self._render_cargos(inter, tipo, mode, primary_hex)
            return

        if cid in ("Verif_ConfirmarRemover_verificado", "Verif_ConfirmarRemover_responsavel"):
            tipo  = cid.split("_")[-1]
            cfg   = carregar_config()
            lista = cfg.get(f"cargo_{tipo}", [])
            val   = inter.values[0]
            if val in lista:
                lista.remove(val)
            cfg[f"cargo_{tipo}"] = lista
            salvar_config(cfg)
            await self._render_cargos(inter, tipo, mode, primary_hex)
            return

        if cid == "Verif_SelectResponsavel" or cid.startswith("Verif_SelectResponsavel_"):
            await self._submeter_indicacao(inter)
            return

    # ── Listener de modais ────────────────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def _modal(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("Verif_"):
            return

        def _hex(v: str) -> str | None:
            if not v:
                return None
            v = v.strip().lstrip("#")
            if len(v) not in (3, 6):
                return None
            try:
                int(v, 16)
            except ValueError:
                return None
            return f"#{v.upper()}"

        if cid == "Verif_MsgModal_Mensagem":
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["content"] = inter.text_values["content"]
            editor.pop("container", None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Verif_MsgModal_Embed":
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["embed"] = {
                "title":       inter.text_values.get("embed_title"),
                "description": inter.text_values.get("embed_description"),
                "color":       _hex(inter.text_values.get("embed_color", "")),
                "footer":      inter.text_values.get("embed_footer"),
            }
            editor.pop("container", None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Verif_MsgModal_Imagens":
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["externalImage"] = inter.text_values.get("externalImage") or None
            if "banner" in inter.text_values:
                editor.setdefault("embed", {})["banner"] = inter.text_values.get("banner") or None
            if "thumbnail" in inter.text_values:
                editor.setdefault("embed", {})["thumbnail"] = inter.text_values.get("thumbnail") or None
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Verif_MsgModal_Container":
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            editor["container"] = inter.text_values["container"]
            editor.pop("content", None)
            editor.pop("embed", None)
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid.startswith("Verif_MsgModal_Botao_"):
            tipo = cid.replace("Verif_MsgModal_Botao_", "")
            cor  = inter.text_values.get("cor", "").strip().lower()
            if cor not in BUTTON_STYLE_MAP:
                cor = {"verificar": "green", "codigo": "blue", "captcha": "gray"}.get(tipo, "gray")
            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            editor[f"botao_{tipo}"] = {
                "nome":  inter.text_values.get("nome", "").strip(),
                "emoji": inter.text_values.get("emoji_btn", "").strip(),
                "cor":   cor,
            }
            cfg["mensagem"] = editor
            salvar_config(cfg)
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=_editor_panel(cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        if cid == "Verif_EnviarPainelModal":
            vals = inter.resolved_values.get("canal_destino")
            if isinstance(vals, (list, tuple)):
                vals = vals[0] if vals else None
            if not vals:
                await inter.response.send_message(f"{emoji.wrong} Canal inválido.", ephemeral=True)
                return
            channel_id = vals.id if hasattr(vals, "id") else int(vals)
            channel    = inter.guild.get_channel(channel_id)
            if not channel:
                await inter.response.send_message(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
                return

            await inter.response.defer(ephemeral=True)

            cfg    = carregar_config()
            editor = cfg.get("mensagem", {})
            data   = editor.copy()
            data["buttons"] = data.pop("botoes", [])

            try:
                built = await Builder.build_from_cfg({"message": data})
                btns  = _build_painel_publico_btns(cfg)
                await _send_built_with_btns(channel, built, btns)
                cfg2 = carregar_config()
                await inter.edit_original_message(
                    components=_editor_panel(cfg2),
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
                await inter.followup.send(
                    f"{emoji.correct} Painel enviado em {channel.mention}!", ephemeral=True
                )
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro ao enviar: {e}", ephemeral=True)
            return

    # ── Fluxo: Indicação ──────────────────────────────────────────────────────

    async def _iniciar_indicacao(self, inter: disnake.MessageInteraction):
        config       = carregar_config()
        responsaveis = config.get("cargo_responsavel", [])

        if not responsaveis:
            await inter.response.send_message(
                f"{emoji.wrong} Cargo responsável não configurado.", ephemeral=True
            )
            return

        # Defer para poder fazer guild.chunk() antes de responder
        await inter.response.defer(ephemeral=True)

        # Força o carregamento completo dos membros no cache
        if not inter.guild.chunked:
            await inter.guild.chunk(cache=True)

        cargo_ids_int = {int(cid) for cid in responsaveis}
        membros_resp: list[disnake.Member] = []
        seen_ids: set[int] = set()
        for cargo_id in cargo_ids_int:
            role = inter.guild.get_role(cargo_id)
            if role is None:
                continue
            for m in role.members:
                if m.id == inter.author.id or m.bot:
                    continue
                if m.id not in seen_ids:
                    seen_ids.add(m.id)
                    membros_resp.append(m)

        if not membros_resp:
            await inter.followup.send(
                f"{emoji.wrong} Nenhum responsável encontrado.", ephemeral=True
            )
            return

        CHUNK  = 25
        chunks = [membros_resp[i:i+CHUNK] for i in range(0, min(len(membros_resp), 125), CHUNK)]
        rows   = []
        for idx, chunk in enumerate(chunks):
            options = [
                disnake.SelectOption(label=m.display_name[:100], value=str(m.id),
                                     description=f"@{m.name}"[:100])
                for m in chunk
            ]
            cid_sel = "Verif_SelectResponsavel" if idx == 0 else f"Verif_SelectResponsavel_{idx}"
            rows.append(disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder=f"Selecione quem você conhece ({idx*CHUNK+1}–{idx*CHUNK+len(chunk)})...",
                    custom_id=cid_sel, options=options,
                    min_values=1, max_values=min(len(options), 10),
                )
            ))

        primary_hex = db.get_document("custom_colors").get("primary")
        mode        = _mode()

        if mode == "embed":
            emb = disnake.Embed(title="Verificação — Indicação",
                                description="Selecione **quem você conhece** no servidor.")
            if primary_hex:
                emb.color = color(primary_hex)
            await inter.followup.send(embed=emb, components=rows, ephemeral=True)
        else:
            await inter.followup.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            "# Verificação — Indicação\n"
                            "Selecione **quem você conhece** no servidor.\n"
                            "-# A equipe irá aprovar ou recusar."
                        ),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        *rows, **accent(primary_hex),
                    )
                ],
                ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True),
            )

    async def _submeter_indicacao(self, inter: disnake.MessageInteraction):
        selecionados = inter.values
        config       = carregar_config()
        logs_id      = config.get("logs_canal")
        mode         = _mode()
        primary_hex  = db.get_document("custom_colors").get("primary")

        if not logs_id:
            await inter.edit_original_message(
                content=f"{emoji.wrong} Canal de logs não configurado.", components=[], embeds=[]
            )
            return

        canal = self.bot.get_channel(int(logs_id))
        if not canal:
            await inter.edit_original_message(
                content=f"{emoji.wrong} Canal de logs não encontrado.", components=[], embeds=[]
            )
            return

        import time as _t
        autor       = inter.author
        mencoes     = ", ".join(f"<@{uid}>" for uid in selecionados)
        pendente_id = f"{autor.id}_{int(_t.time())}"

        pendentes = load_json(PENDENTES_JSON)
        pendentes[pendente_id] = {
            "user_id":    autor.id,
            "user_nome":  autor.display_name,
            "conhecidos": selecionados,
        }
        save_json(PENDENTES_JSON, pendentes)

        mod_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Aprovar", emoji=emoji.correct,
                              style=disnake.ButtonStyle.green,
                              custom_id=f"Verif_Aprovar_{pendente_id}"),
            disnake.ui.Button(label="Recusar", emoji=emoji.wrong,
                              style=disnake.ButtonStyle.red,
                              custom_id=f"Verif_Recusar_{pendente_id}"),
        )
        desc = f"**Usuário:** {autor.mention} (`{autor.id}`)\n**Conhece:** {mencoes}"

        if mode == "embed":
            emb = disnake.Embed(title="Nova Verificação Pendente", description=desc)
            if primary_hex:
                emb.color = color(primary_hex)
            await canal.send(embed=emb, components=[mod_row])
        else:
            await canal.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.shield} Nova Verificação Pendente\n{desc}"),
                        **accent(primary_hex),
                    ),
                    mod_row,
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        await inter.edit_original_message(
            content=f"{emoji.correct} Solicitação enviada! Aguarde a equipe.",
            components=[], embeds=[],
        )

    # ── Fluxo: Moderação ──────────────────────────────────────────────────────

    async def _handle_moderacao(self, inter: disnake.MessageInteraction, cid: str):
        config       = carregar_config()
        responsaveis = config.get("cargo_responsavel", [])
        if responsaveis:
            roles = [str(r.id) for r in getattr(inter.author, "roles", [])]
            if not any(r in roles for r in responsaveis):
                await inter.response.send_message("Sem permissão.", ephemeral=True)
                return

        await inter.response.defer(ephemeral=True)
        aprovando   = cid.startswith("Verif_Aprovar_")
        pendente_id = cid.replace("Verif_Aprovar_", "").replace("Verif_Recusar_", "")

        pendentes = load_json(PENDENTES_JSON)
        pendente  = pendentes.pop(pendente_id, None)
        if not pendente:
            await inter.followup.send("Verificação não encontrada.", ephemeral=True)
            return
        save_json(PENDENTES_JSON, pendentes)

        user_id   = pendente.get("user_id")
        user_nome = pendente.get("user_nome", "?")
        expulsar  = config.get("expulsar_recusado", False)
        member    = inter.guild.get_member(int(user_id))

        if aprovando:
            if member:
                for cargo_id in config.get("cargo_verificado", []):
                    cargo = inter.guild.get_role(int(cargo_id))
                    if cargo:
                        try:
                            await member.add_roles(cargo, reason="Verificação aprovada")
                        except Exception:
                            pass
                try:
                    await member.send(
                        f"{emoji.correct} Sua verificação foi **aprovada** em **{inter.guild.name}**!"
                    )
                except Exception:
                    pass
            try:
                await inter.message.edit(components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Aprovado", style=disnake.ButtonStyle.green,
                                          custom_id="noop",emoji=emoji.correct, disabled=True),
                    )
                ])
            except Exception:
                pass
            await inter.followup.send(f"{emoji.correct} {user_nome} verificado.", ephemeral=True)
            await enviar_log(self.bot, "Verificação Aprovada",
                             f"**Usuário:** <@{user_id}>\n**Aprovado por:** {inter.author.mention}")
        else:
            if member:
                dm = f"{emoji.wrong} Sua verificação foi **recusada** em **{inter.guild.name}**."
                if expulsar:
                    dm += "\nVocê será expulso do servidor."
                try:
                    await member.send(dm)
                except Exception:
                    pass
                if expulsar:
                    try:
                        await member.kick(reason="Verificação recusada")
                    except Exception:
                        pass
            try:
                await inter.message.edit(components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Recusado", style=disnake.ButtonStyle.red,
                                          custom_id="noop",emoji=emoji.wrong, disabled=True),
                    )
                ])
            except Exception:
                pass
            await inter.followup.send(f"{emoji.wrong} {user_nome} recusado.", ephemeral=True)
            await enviar_log(self.bot, "Verificação Recusada",
                             f"**Usuário:** <@{user_id}>\n**Recusado por:** {inter.author.mention}\n"
                             f"**Expulso:** {'Sim' if expulsar else 'Não'}", erro=True)

    # ── Fluxo: Captcha ────────────────────────────────────────────────────────

    async def _iniciar_captcha(self, inter: disnake.MessageInteraction):
        config      = carregar_config()
        cap_modo    = config.get("captcha_modo", "modal")
        primary_hex = db.get_document("custom_colors").get("primary")
        mode        = _mode()

        texto = gerar_texto_captcha()
        criar_sessao_captcha(inter.author.id, texto)
        buf  = _captcha_gen.generate(texto, primary_hex)
        file = disnake.File(buf, filename="captcha.png")

        if cap_modo == "modal":
            btn_row = disnake.ui.ActionRow(
                disnake.ui.Button(label="Inserir código", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Verif_CaptchaBtn_abrirmodal")
            )
            if mode == "embed":
                emb = disnake.Embed(title="Captcha", description="Digite o texto da imagem.")
                if primary_hex:
                    emb.color = color(primary_hex)
                emb.set_image(url="attachment://captcha.png")
                await inter.response.send_message(embed=emb, file=file, components=[btn_row], ephemeral=True)
            else:
                await inter.response.send_message(
                    file=file,
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay("# Captcha\nDigite o texto da imagem."),
                            disnake.ui.MediaGallery(
                                disnake.ui.MediaGalleryItem(media="attachment://captcha.png")
                            ),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            btn_row, **accent(primary_hex),
                        )
                    ],
                    ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True),
                )
        else:
            opcoes = gerar_opcoes_captcha(texto, total=25)
            rows   = []
            for i in range(0, 25, 5):
                chunk = opcoes[i:i+5]
                rows.append(disnake.ui.ActionRow(*[
                    disnake.ui.Button(label=opt, style=disnake.ButtonStyle.grey,
                                      custom_id=f"Verif_CaptchaBtn_{opt}")
                    for opt in chunk
                ]))
            if mode == "embed":
                emb = disnake.Embed(title="Captcha", description="Clique no botão que corresponde ao texto.")
                if primary_hex:
                    emb.color = color(primary_hex)
                emb.set_image(url="attachment://captcha.png")
                await inter.response.send_message(embed=emb, file=file, components=rows, ephemeral=True)
            else:
                await inter.response.send_message(
                    file=file,
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay("# Captcha\nClique no botão que corresponde ao texto."),
                            disnake.ui.MediaGallery(
                                disnake.ui.MediaGalleryItem(media="attachment://captcha.png")
                            ),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            *rows, **accent(primary_hex),
                        )
                    ],
                    ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True),
                )

    async def _checar_captcha_botao(self, inter: disnake.MessageInteraction, cid: str):
        if cid == "Verif_CaptchaBtn_abrirmodal":
            await inter.response.send_modal(CaptchaModal(self.bot))
            return
        resposta = cid.replace("Verif_CaptchaBtn_", "")
        ok       = validar_sessao_captcha(inter.author.id, resposta)
        await self._concluir_captcha(inter, ok, modal=False)

    async def _concluir_captcha(self, inter, ok: bool, modal: bool = True):
        config = carregar_config()
        if ok:
            for cargo_id in config.get("cargo_verificado", []):
                cargo = inter.guild.get_role(int(cargo_id))
                if cargo:
                    try:
                        await inter.author.add_roles(cargo, reason="Verificação por captcha")
                    except Exception:
                        pass
            msg = f"{emoji.correct} Captcha correto! Você foi verificado."
            await enviar_log(self.bot, "Verificação por Captcha",
                             f"**Usuário:** {inter.author.mention} — Método: Captcha ({'Modal' if modal else 'Botão'})")
        else:
            msg = f"{emoji.wrong} Captcha incorreto. Tente novamente."
            await enviar_log(self.bot, "Captcha Incorreto",
                             f"**Usuário:** {inter.author.mention}", erro=True)
        try:
            await inter.edit_original_message(content=msg, components=[], embeds=[])
        except Exception:
            await inter.response.send_message(msg, ephemeral=True)


# ─── Modais de verificação pública ───────────────────────────────────────────

class CodigoModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(
            title="Verificação por Código",
            custom_id="Verif_CodigoModal",
            components=[
                disnake.ui.TextInput(label="Código de verificação",
                                     placeholder="Digite o código fornecido...",
                                     custom_id="codigo", style=disnake.TextInputStyle.short,
                                     required=True, min_length=1, max_length=32)
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        codigo = inter.text_values.get("codigo", "").strip()
        valido, dono_id, entry = validar_codigo(codigo)
        await inter.response.defer(ephemeral=True)
        config = carregar_config()

        if valido:
            for cargo_id in config.get("cargo_verificado", []):
                cargo = inter.guild.get_role(int(cargo_id))
                if cargo:
                    try:
                        await inter.author.add_roles(cargo, reason="Código de verificação")
                    except Exception:
                        pass
            await inter.followup.send(f"{emoji.correct} Código válido! Você foi verificado.", ephemeral=True)
            await enviar_log(self.bot, "Verificação por Código",
                             f"**Usuário:** {inter.author.mention}\n"
                             f"**Código:** `{entry.get('nome', codigo)}`\n**Criador:** <@{dono_id}>")
        else:
            try:
                await inter.author.send(
                    f"{emoji.wrong} O código `{codigo}` é **inválido ou esgotado** em **{inter.guild.name}**."
                )
            except Exception:
                pass
            await inter.followup.send(f"{emoji.wrong} Código inválido ou esgotado.", ephemeral=True)
            await enviar_log(self.bot, "Código Inválido",
                             f"**Usuário:** {inter.author.mention}\n**Código:** `{codigo}`", erro=True)


class CaptchaModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(
            title="Captcha",
            custom_id="Verif_CaptchaModal",
            components=[
                disnake.ui.TextInput(label="Digite o texto da imagem",
                                     placeholder="Ex: A8K3NZ", custom_id="resposta",
                                     style=disnake.TextInputStyle.short,
                                     required=True, min_length=1, max_length=10)
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        resposta = inter.text_values.get("resposta", "").strip()
        ok       = validar_sessao_captcha(inter.author.id, resposta)
        cog: VerificacaoCog | None = inter.bot.get_cog("VerificacaoCog")
        if cog:
            await inter.response.defer(ephemeral=True)
            await cog._concluir_captcha(inter, ok, modal=True)
        else:
            await inter.response.send_message("Erro interno.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(VerificacaoCog(bot))