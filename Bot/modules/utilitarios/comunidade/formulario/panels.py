"""
modules/utilitarios/comunidade/formulario/panels.py

Todos os painéis de configuração (modo components e modo embed).
"""
from __future__ import annotations

import disnake
from functions.emoji import emoji
from .helpers import (
    carregar_config, get_formulario, get_colors, get_mode,
    FIELD_TYPES, SEND_MODES, DISPLAY_MODES, listar_formularios_select,
    estilo_para_disnake,
)


# ─── Painel principal ─────────────────────────────────────────────────────────

def painel_principal_components() -> list:
    config = carregar_config()
    forms = config.get("formularios", {})
    total = len(forms)
    ativos = sum(1 for f in forms.values() if f.get("ativado"))
    primary_hex, ck = get_colors()

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                "-# Painel > Comunidade > **Sistema de Formulários**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Crie formulários personalizados com múltiplos campos, aprovação de respostas, "
                "tópicos privados e muito mais."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.embed} **Formulários criados:** `{total}`\n"
                f"{emoji.on} **Formulários ativos:** `{ativos}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Formulário", emoji=emoji.plus,
                                  style=disnake.ButtonStyle.green, custom_id="Form_Criar"),
                disnake.ui.Button(label="Gerenciar", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.blurple, custom_id="Form_Gerenciar",
                                  disabled=total == 0),
                disnake.ui.Button(label="Ver Respostas", emoji=emoji.receipt,
                                  style=disnake.ButtonStyle.grey, custom_id="Form_VerRespostas",
                                  disabled=total == 0),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Gerenciar Staff", emoji=emoji.shield_star,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_Principal"),
                disnake.ui.Button(label="Ranking Staff", emoji=emoji.coupon,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_Ranking"),
                disnake.ui.Button(label="Bate Ponto", emoji=emoji.time,
                                  style=disnake.ButtonStyle.grey, custom_id="BP_Principal"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Comunidade_VoltarFeature"),
        ),
    ]


def painel_principal_embed() -> tuple[disnake.Embed, list]:
    config = carregar_config()
    forms = config.get("formularios", {})
    total = len(forms)
    ativos = sum(1 for f in forms.values() if f.get("ativado"))
    primary_hex, _ = get_colors()

    embed = disnake.Embed(
        title="Sistema de Formulários",
        description=(
            "Crie formulários personalizados com múltiplos campos, "
            "aprovação de respostas, tópicos privados e muito mais.\n\n"
            f"{emoji.embed} **Formulários criados:** `{total}`\n"
            f"{emoji.on} **Formulários ativos:** `{ativos}`"
        ),
    )
    if primary_hex:
        embed.color = int(primary_hex.replace("#", ""), 16)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Formulário", emoji=emoji.plus,
                              style=disnake.ButtonStyle.green, custom_id="Form_Criar"),
            disnake.ui.Button(label="Gerenciar", emoji=emoji.edit,
                              style=disnake.ButtonStyle.blurple, custom_id="Form_Gerenciar",
                              disabled=total == 0),
            disnake.ui.Button(label="Ver Respostas", emoji=emoji.receipt,
                              style=disnake.ButtonStyle.grey, custom_id="Form_VerRespostas",
                              disabled=total == 0),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Gerenciar Staff", emoji=emoji.shield_star,
                              style=disnake.ButtonStyle.grey, custom_id="Staff_Principal"),
            disnake.ui.Button(label="Ranking Staff", emoji=emoji.coupon,
                              style=disnake.ButtonStyle.grey, custom_id="Staff_Ranking"),
            disnake.ui.Button(label="Bate Ponto", emoji=emoji.time,
                              style=disnake.ButtonStyle.grey, custom_id="BP_Principal"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Comunidade_VoltarFeature"),
        ),
    ]
    return embed, components


# ─── Seletor de formulário ────────────────────────────────────────────────────

def painel_selecionar_components(titulo: str, custom_id_select: str, custom_id_voltar: str = "Form_VoltarPrincipal") -> list:
    primary_hex, ck = get_colors()
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > **{titulo}**"
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=custom_id_select,
                    placeholder="Selecione um formulário...",
                    options=listar_formularios_select(),
                )
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=custom_id_voltar),
        ),
    ]


# ─── Editor principal do formulário ──────────────────────────────────────────

def painel_editor_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    ativado = form.get("ativado", False)
    campos = form.get("campos", [])
    display_mode = form.get("display_mode", "modal")
    send_mode = form.get("send_mode", "channel")
    canal_painel = form.get("canal_painel_id")
    canal_respostas = form.get("canal_respostas_id")
    canal_topicos = form.get("canal_topicos_id")
    requer_aprov = form.get("requer_aprovacao", False)
    anonimo = form.get("anonimo", False)
    cargos_perm = form.get("cargos_permitidos", [])
    cargos_noti = form.get("cargos_notificar", [])

    display_info = DISPLAY_MODES.get(display_mode, {})
    send_info = SEND_MODES.get(send_mode, {})

    canal_painel_str = f"<#{canal_painel}>" if canal_painel else "`Não definido`"
    canal_resp_str = f"<#{canal_respostas}>" if canal_respostas else "`Não definido`"
    canal_top_str = f"<#{canal_topicos}>" if canal_topicos else "`Não definido`"
    cargos_perm_str = ", ".join(f"<@&{c}>" for c in cargos_perm) if cargos_perm else "`Todos`"
    cargos_noti_str = ", ".join(f"<@&{c}>" for c in cargos_noti) if cargos_noti else "`Nenhum`"

    status_info = (
        f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativo' if ativado else 'Inativo'}`\n"
        f"{display_info.get('emoji', '')} **Modo de exibição:** `{display_info.get('label', display_mode)}`\n"
        f"{send_info.get('emoji', '')} **Modo de envio:** `{send_info.get('label', send_mode)}`\n"
        f"{emoji.textc} **Canal do painel:** {canal_painel_str}\n"
    )
    if send_mode == "channel":
        status_info += f"{emoji.textc} **Canal de respostas:** {canal_resp_str}\n"
    elif send_mode == "topic":
        status_info += f"{emoji.dir} **Canal de tópicos:** {canal_top_str}\n"

    status_info += (
        f"{emoji.role} **Cargos permitidos:** {cargos_perm_str}\n"
        f"{emoji.warn} **Notificar cargos:** {cargos_noti_str}\n"
        f"{emoji.correct if requer_aprov else emoji.wrong} **Aprovação manual:** `{'Sim' if requer_aprov else 'Não'}`\n"
        f"{emoji.member} **Anônimo:** `{'Sim' if anonimo else 'Não'}`\n"
        f"{emoji.pin} **Campos configurados:** `{len(campos)}`"
    )

    pode_publicar = bool(canal_painel and campos)

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > **{nome}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(status_info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", emoji=emoji.power, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Form_Toggle:{form_id}"),
                disnake.ui.Button(label="Campos", emoji=emoji.pin, style=disnake.ButtonStyle.blurple,
                                  custom_id=f"Form_EditarCampos:{form_id}"),
                disnake.ui.Button(label="Aparência", emoji=emoji.colors, style=disnake.ButtonStyle.blurple,
                                  custom_id=f"Form_EditarAparencia:{form_id}"),
                disnake.ui.Button(label="Configurações", emoji=emoji.settings2, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Form_EditarConfig:{form_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Canais", emoji=emoji.textc, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Form_EditarCanais:{form_id}"),
                disnake.ui.Button(label="Cargos", emoji=emoji.role, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Form_EditarCargos:{form_id}"),
                disnake.ui.Button(label="Publicar", emoji=emoji.arrow, style=disnake.ButtonStyle.green,
                                  custom_id=f"Form_Publicar:{form_id}", disabled=not pode_publicar),
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id=f"Form_Apagar:{form_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Form_Gerenciar"),
            disnake.ui.Button(label="Preview", emoji=emoji.search,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_Preview:{form_id}",
                              disabled=not campos),
        ),
    ]


# ─── Painel de campos ─────────────────────────────────────────────────────────

def painel_campos_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    campos = form.get("campos", [])
    nome = form.get("nome", "Sem nome")
    pode_adicionar = len(campos) < 5

    campo_resumo = ""
    if campos:
        for i, c in enumerate(campos):
            tipo_info = FIELD_TYPES.get(c.get("tipo", "short"), {})
            req = "🔴" if c.get("required") else "🟡"
            campo_resumo += f"{req} `{i+1}.` **{c['label']}** — {tipo_info.get('label', c.get('tipo'))}\n"
    else:
        campo_resumo = "Nenhum campo configurado ainda."

    opcoes_campo = [
        disnake.SelectOption(label=f"{i+1}. {c['label']}", value=c["id"],
                             emoji=FIELD_TYPES.get(c.get("tipo","short"), {}).get("emoji", emoji.pin),
                             description=FIELD_TYPES.get(c.get("tipo","short"), {}).get("label", ""))
        for i, c in enumerate(campos)
    ] or [disnake.SelectOption(label="Nenhum campo", value="__none__")]

    container_items = [
        disnake.ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Formulários > {nome} > **Campos** `{len(campos)}/5`"
        ),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(campo_resumo),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar Campo", emoji=emoji.plus,
                              style=disnake.ButtonStyle.green, custom_id=f"Form_AdicionarCampo:{form_id}",
                              disabled=not pode_adicionar),
        ),
    ]

    if campos:
        container_items += [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Form_SelecionarCampoEditar:{form_id}",
                    placeholder="Selecione um campo para editar...",
                    options=opcoes_campo,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Form_SelecionarCampoRemover:{form_id}",
                    placeholder="Selecione um campo para remover...",
                    options=opcoes_campo,
                )
            ),
        ]

    return [
        disnake.ui.Container(*container_items, **ck),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_Editor:{form_id}"),
        ),
    ]


# ─── Painel de aparência ──────────────────────────────────────────────────────

def painel_aparencia_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    titulo = form.get("embed_titulo") or nome
    desc = (form.get("embed_descricao") or "")[:60]
    desc_display = f"`{desc}...`" if len(form.get("embed_descricao", "")) > 60 else f"`{desc}`"
    btn_label = form.get("botao_label", "Preencher Formulário")
    btn_emoji_val = form.get("botao_emoji", f"{emoji.edit}")
    btn_estilo = form.get("botao_estilo", "blurple")
    mensagem_suc = (form.get("mensagem_sucesso") or "")[:60]

    # Indicador de conteúdo do editor Anúncios
    editor_data = form.get("anunciar_editor", {})
    has_content = bool(editor_data.get("content"))
    has_embed = any(editor_data.get("embed", {}).get(k) for k in ("title", "description"))
    has_container = bool(editor_data.get("container"))
    has_image = bool(editor_data.get("externalImage") or editor_data.get("embed", {}).get("banner"))
    editor_status = []
    if has_content: editor_status.append("Mensagem")
    if has_embed: editor_status.append("Embed")
    if has_container: editor_status.append("Container")
    if has_image: editor_status.append("Imagem")
    editor_str = ", ".join(editor_status) if editor_status else "`Padrão (título + descrição)`"

    info = (
        f"{emoji.embed} **Editor de aparência:** {editor_str}\n"
        f"{emoji.correct} **Mensagem de sucesso:** `{mensagem_suc[:50]}`\n"
        f"{emoji.wand} **Label do botão:** `{btn_label}`\n"
        f"{emoji.colors} **Emoji do botão:** {btn_emoji_val}\n"
        f"{emoji.route} **Estilo do botão:** `{btn_estilo}`\n"
        f"-# O editor de aparência usa o mesmo sistema do módulo Anúncios."
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > {nome} > **Aparência**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editor de Aparência", emoji=emoji.embed,
                                  style=disnake.ButtonStyle.blurple, custom_id=f"Form_AbrirEditorAnunciar:{form_id}"),
                disnake.ui.Button(label="Editar Botão", emoji=emoji.wand,
                                  style=disnake.ButtonStyle.blurple, custom_id=f"Form_EditarBotao:{form_id}"),
                disnake.ui.Button(label="Mensagem Sucesso", emoji=emoji.correct,
                                  style=disnake.ButtonStyle.grey, custom_id=f"Form_EditarMsgSucesso:{form_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_Editor:{form_id}"),
        ),
    ]


# ─── Painel de configurações gerais ──────────────────────────────────────────

def painel_config_geral_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    display_mode = form.get("display_mode", "modal")
    send_mode = form.get("send_mode", "channel")
    requer_aprov = form.get("requer_aprovacao", False)
    anonimo = form.get("anonimo", False)
    limite = form.get("limite_respostas", 0)

    display_info = DISPLAY_MODES.get(display_mode, {})
    send_info = SEND_MODES.get(send_mode, {})

    info = (
        f"{display_info.get('emoji','')} **Modo exibição:** `{display_info.get('label', display_mode)}`\n"
        f"-# {display_info.get('description','')}\n\n"
        f"{send_info.get('emoji','')} **Modo envio:** `{send_info.get('label', send_mode)}`\n"
        f"-# {send_info.get('description','')}\n\n"
        f"{emoji.correct if requer_aprov else emoji.wrong} **Requer aprovação:** `{'Sim' if requer_aprov else 'Não'}`\n"
        f"{emoji.member} **Modo anônimo:** `{'Sim' if anonimo else 'Não'}`\n"
        f"{emoji.time} **Limite de respostas:** `{'Ilimitado' if not limite else limite}`"
    )

    display_options = [
        disnake.SelectOption(
            label=v["label"], value=k,
            emoji=v["emoji"], description=v["description"],
            default=(k == display_mode)
        )
        for k, v in DISPLAY_MODES.items()
    ]
    send_options = [
        disnake.SelectOption(
            label=v["label"], value=k,
            emoji=v["emoji"], description=v["description"],
            default=(k == send_mode)
        )
        for k, v in SEND_MODES.items()
    ]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > {nome} > **Configurações**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Form_SetDisplayMode:{form_id}",
                    placeholder="Modo de exibição do formulário...",
                    options=display_options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Form_SetSendMode:{form_id}",
                    placeholder="Modo de envio das respostas...",
                    options=send_options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Toggle Aprovação", emoji=emoji.correct,
                                  style=disnake.ButtonStyle.grey, custom_id=f"Form_ToggleAprovacao:{form_id}"),
                disnake.ui.Button(label="Toggle Anônimo", emoji=emoji.member,
                                  style=disnake.ButtonStyle.grey, custom_id=f"Form_ToggleAnonimo:{form_id}"),
                disnake.ui.Button(label="Limite Respostas", emoji=emoji.time,
                                  style=disnake.ButtonStyle.grey, custom_id=f"Form_EditarLimite:{form_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_Editor:{form_id}"),
        ),
    ]


# ─── Painel de canais ─────────────────────────────────────────────────────────

def painel_canais_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    send_mode = form.get("send_mode", "channel")
    canal_painel = form.get("canal_painel_id")
    canal_respostas = form.get("canal_respostas_id")
    canal_topicos = form.get("canal_topicos_id")

    painel_str = f"<#{canal_painel}>" if canal_painel else "`Não definido`"
    resp_str = f"<#{canal_respostas}>" if canal_respostas else "`Não definido`"
    top_str = f"<#{canal_topicos}>" if canal_topicos else "`Não definido`"

    info = f"{emoji.textc} **Canal do painel** (onde o formulário é publicado): {painel_str}\n"
    if send_mode == "channel":
        info += f"{emoji.textc} **Canal de respostas** (onde as respostas chegam): {resp_str}\n"
    elif send_mode == "topic":
        info += f"{emoji.dir} **Canal de tópicos** (onde os tópicos são criados): {top_str}\n"
    elif send_mode == "dm":
        info += f"-# As respostas serão enviadas na DM dos cargos de notificação.\n"

    container_items = [
        disnake.ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Formulários > {nome} > **Canais**"
        ),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(info),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(f"**Canal do Painel**"),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                custom_id=f"Form_SetCanalPainel:{form_id}",
                placeholder="Selecione o canal para publicar o formulário...",
                channel_types=[disnake.ChannelType.text],
                min_values=1, max_values=1,
            )
        ),
    ]

    if send_mode == "channel":
        container_items += [
            disnake.ui.TextDisplay(f"**Canal de Respostas**"),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id=f"Form_SetCanalRespostas:{form_id}",
                    placeholder="Selecione o canal de respostas...",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ),
        ]
    elif send_mode == "topic":
        container_items += [
            disnake.ui.TextDisplay(f"**Canal para Tópicos**"),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id=f"Form_SetCanalTopicos:{form_id}",
                    placeholder="Selecione o canal para criar os tópicos...",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ),
        ]

    return [
        disnake.ui.Container(*container_items, **ck),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_Editor:{form_id}"),
        ),
    ]


# ─── Painel de cargos ─────────────────────────────────────────────────────────

def painel_cargos_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    cargos_perm = form.get("cargos_permitidos", [])
    cargos_noti = form.get("cargos_notificar", [])
    cargo_aprov_id = form.get("cargo_aprovacao_id")

    perm_str = ", ".join(f"<@&{c}>" for c in cargos_perm) if cargos_perm else "`Todos os membros`"
    noti_str = ", ".join(f"<@&{c}>" for c in cargos_noti) if cargos_noti else "`Nenhum`"
    aprov_str = f"<@&{cargo_aprov_id}>" if cargo_aprov_id else "`Nenhum`"

    info = (
        f"{emoji.role} **Cargos que podem responder:**\n{perm_str}\n\n"
        f"{emoji.warn} **Cargos a notificar (nova resposta):**\n{noti_str}\n\n"
        f"{emoji.correct} **Cargo concedido na aprovação:**\n{aprov_str}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > {nome} > **Cargos**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("**Cargos com permissão para responder** (deixe vazio para todos)"),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id=f"Form_SetCargosPermitidos:{form_id}",
                    placeholder="Selecione os cargos permitidos...",
                    min_values=0, max_values=25,
                )
            ),
            disnake.ui.TextDisplay("**Cargos a notificar quando uma resposta chegar**"),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id=f"Form_SetCargosNotificar:{form_id}",
                    placeholder="Selecione os cargos a notificar...",
                    min_values=0, max_values=10,
                )
            ),
            disnake.ui.TextDisplay("**Cargo concedido automaticamente ao aprovar uma resposta** (deixe vazio para nenhum)"),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id=f"Form_SetCargoAprovacao:{form_id}",
                    placeholder="Selecione o cargo de aprovação...",
                    min_values=0, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Limpar Permitidos", emoji=emoji.delete,
                                  style=disnake.ButtonStyle.red, custom_id=f"Form_LimparCargosPermitidos:{form_id}",
                                  disabled=not cargos_perm),
                disnake.ui.Button(label="Limpar Notificações", emoji=emoji.delete,
                                  style=disnake.ButtonStyle.red, custom_id=f"Form_LimparCargosNotificar:{form_id}",
                                  disabled=not cargos_noti),
                disnake.ui.Button(label="Limpar Cargo Aprovação", emoji=emoji.delete,
                                  style=disnake.ButtonStyle.red, custom_id=f"Form_LimparCargoAprovacao:{form_id}",
                                  disabled=not cargo_aprov_id),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_Editor:{form_id}"),
            disnake.ui.Button(label="Mensagens de Aprovação", emoji=emoji.message,
                              style=disnake.ButtonStyle.blurple, custom_id=f"Form_EditarMsgAprovacao:{form_id}"),
        ),
    ]



# ─── Painel de mensagens de aprovação/rejeição ───────────────────────────────

def painel_msg_aprovacao_components(form_id: str) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    msg_aprov = form.get("msg_aprovado") or f"{emoji.correct} Sua resposta ao formulário **{nome}** foi aprovada!"
    msg_reprov = form.get("msg_reprovado") or f"{emoji.wrong} Sua resposta ao formulário **{nome}** foi reprovada."

    info = (
        f"{emoji.correct} **Mensagem de aprovação:**\n`{msg_aprov[:120]}`\n\n"
        f"{emoji.wrong} **Mensagem de reprovação:**\n`{msg_reprov[:120]}`\n\n"
        f"-# Variáveis disponíveis: `{{nome}}` (nome do formulário), `{{aprovador}}` / `{{reprovador}}` (quem avaliou)"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > {nome} > Cargos > **Mensagens de Aprovação**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Mensagem de Aprovação", emoji=emoji.correct,
                                  style=disnake.ButtonStyle.green, custom_id=f"Form_EditarMsgAprovado:{form_id}"),
                disnake.ui.Button(label="Editar Mensagem de Reprovação", emoji=emoji.wrong,
                                  style=disnake.ButtonStyle.red, custom_id=f"Form_EditarMsgReprovado:{form_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id=f"Form_EditarCargos:{form_id}"),
        ),
    ]



def painel_respostas_components(form_id: str, respostas: list, page: int = 0) -> list:
    form = get_formulario(form_id)
    if not form:
        return painel_principal_components()

    primary_hex, ck = get_colors()
    nome = form.get("nome", "Sem nome")
    total = len(respostas)
    por_pagina = 5
    inicio = page * por_pagina
    fim = min(inicio + por_pagina, total)
    pagina_respostas = respostas[inicio:fim]

    if not pagina_respostas:
        conteudo = "Nenhuma resposta recebida ainda."
    else:
        linhas = []
        for r in pagina_respostas:
            user_id = r.get("user_id", "?")
            ts = r.get("timestamp", "")
            status = f"{emoji.correct}" if r.get("aprovado") else (f"{emoji.wrong}" if r.get("rejeitado") else "⏳")
            ts_fmt = f"<t:{ts}:R>" if ts else ""
            linhas.append(f"{status} <@{user_id}> {ts_fmt}")
        conteudo = "\n".join(linhas)

    paginacao = f"Página `{page+1}` de `{max(1, (total + por_pagina - 1) // por_pagina)}`  |  `{total}` respostas no total"

    options_resp = [
        disnake.SelectOption(
            label=f"Resposta de {r.get('user_name','Desconhecido')[:30]}",
            value=r.get("id", ""),
            description=f"{f'{emoji.correct} Aprovada' if r.get('aprovado') else f'{emoji.wrong} Rejeitada' if r.get('rejeitado') else '⏳ Pendente'}",
        )
        for r in pagina_respostas
    ] or [disnake.SelectOption(label="Nenhuma resposta", value="__none__")]

    has_prev = page > 0
    has_next = fim < total

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Formulários > {nome} > **Respostas**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(paginacao),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(conteudo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Form_VerResposta:{form_id}",
                    placeholder="Ver detalhes de uma resposta...",
                    options=options_resp,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="◀", style=disnake.ButtonStyle.grey,
                                  custom_id=f"Form_RespPrev:{form_id}:{page}", disabled=not has_prev),
                disnake.ui.Button(label="▶", style=disnake.ButtonStyle.grey,
                                  custom_id=f"Form_RespNext:{form_id}:{page}", disabled=not has_next),
                disnake.ui.Button(label="Exportar CSV", emoji=emoji.receipt,
                                  style=disnake.ButtonStyle.blurple, custom_id=f"Form_ExportarCSV:{form_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Form_Gerenciar"),
        ),
    ]