"""
modules/utilitarios/comunidade/formulario/modals.py

Todos os modais de configuração e preenchimento de formulários.
"""
from __future__ import annotations

import disnake
from functions.emoji import emoji
from .helpers import (
    get_formulario, salvar_formulario, criar_campo, FIELD_TYPES,
)


# ─── Modais de configuração ───────────────────────────────────────────────────

class CriarFormularioModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Novo Formulário",
            custom_id="FormModal_Criar",
            components=[
                disnake.ui.TextInput(
                    label="Nome do Formulário",
                    custom_id="nome",
                    placeholder="Ex: Candidatura para Staff",
                    max_length=80,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .helpers import criar_formulario
        from .panels import painel_editor_components
        from functions.message import message, embed_message
        from functions.database import database as db

        nome = inter.text_values.get("nome", "").strip()
        mode = db.get_document("custom_mode").get("mode", "components")

        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form_id = criar_formulario(nome)
        await inter.edit_original_message(components=painel_editor_components(form_id))


class EditarEmbedFormularioModal(disnake.ui.Modal):
    def __init__(self, form_id: str):
        self.form_id = form_id
        form = get_formulario(form_id) or {}

        super().__init__(
            title="Editar Aparência do Formulário",
            custom_id=f"FormModal_EditarEmbed:{form_id}",
            components=[
                disnake.ui.TextInput(
                    label="Título do Embed",
                    custom_id="titulo",
                    value=form.get("embed_titulo") or form.get("nome", ""),
                    max_length=256,
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Descrição do Embed",
                    custom_id="descricao",
                    value=form.get("embed_descricao", ""),
                    style=disnake.TextInputStyle.paragraph,
                    max_length=2000,
                    required=False,
                ),
                disnake.ui.TextInput(
                    label="Cor do Embed (Hex, ex: #5865F2)",
                    custom_id="cor",
                    value=form.get("embed_cor", ""),
                    max_length=7,
                    required=False,
                    placeholder="#5865F2",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .panels import painel_aparencia_components
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return await inter.edit_original_message(content="Formulário não encontrado.")

        form["embed_titulo"] = inter.text_values.get("titulo") or form.get("nome")
        form["embed_descricao"] = inter.text_values.get("descricao") or ""
        cor = inter.text_values.get("cor", "").strip()
        form["embed_cor"] = cor if cor.startswith("#") else None
        salvar_formulario(self.form_id, form)
        await inter.edit_original_message(components=painel_aparencia_components(self.form_id))


class EditarBotaoModal(disnake.ui.Modal):
    def __init__(self, form_id: str):
        self.form_id = form_id
        form = get_formulario(form_id) or {}

        super().__init__(
            title="Editar Botão do Formulário",
            custom_id=f"FormModal_EditarBotao:{form_id}",
            components=[
                disnake.ui.TextInput(
                    label="Label do Botão",
                    custom_id="label",
                    value=form.get("botao_label", "Preencher Formulário"),
                    max_length=80,
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Emoji do Botão (opcional)",
                    custom_id="btn_emoji",
                    value=form.get("botao_emoji", ""),
                    max_length=100,
                    required=False,
                    placeholder="✏️ ou <:emoji:123456>",
                ),
                disnake.ui.TextInput(
                    label="Estilo (green, red, gray, blurple)",
                    custom_id="estilo",
                    value=form.get("botao_estilo", "blurple"),
                    max_length=10,
                    required=True,
                    placeholder="blurple",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return await inter.edit_original_message(content="Formulário não encontrado.")

        estilo_raw = inter.text_values.get("estilo", "blurple").lower().strip()
        estilos_validos = ["green", "red", "gray", "grey", "blurple"]
        estilo = estilo_raw if estilo_raw in estilos_validos else "blurple"

        form["botao_label"] = inter.text_values.get("label") or "Preencher Formulário"
        form["botao_emoji"] = inter.text_values.get("btn_emoji") or None
        form["botao_estilo"] = estilo
        salvar_formulario(self.form_id, form)

        from .cog import FormularioCog
        await inter.edit_original_message(components=FormularioCog._build_form_anunciar_panel(self.form_id))


class EditarMsgSucessoModal(disnake.ui.Modal):
    def __init__(self, form_id: str):
        self.form_id = form_id
        form = get_formulario(form_id) or {}
        super().__init__(
            title="Mensagem de Sucesso",
            custom_id=f"FormModal_MsgSucesso:{form_id}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem exibida após envio",
                    custom_id="mensagem",
                    value=form.get("mensagem_sucesso", "✅ Sua resposta foi enviada com sucesso!"),
                    style=disnake.TextInputStyle.paragraph,
                    max_length=500,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return
        form["mensagem_sucesso"] = inter.text_values.get("mensagem", "")
        salvar_formulario(self.form_id, form)

        from .cog import FormularioCog
        await inter.edit_original_message(components=FormularioCog._build_form_anunciar_panel(self.form_id))


class EditarLimiteModal(disnake.ui.Modal):
    def __init__(self, form_id: str):
        self.form_id = form_id
        form = get_formulario(form_id) or {}
        super().__init__(
            title="Limite de Respostas",
            custom_id=f"FormModal_Limite:{form_id}",
            components=[
                disnake.ui.TextInput(
                    label="Número máximo de respostas (0 = ilimitado)",
                    custom_id="limite",
                    value=str(form.get("limite_respostas", 0)),
                    max_length=5,
                    required=True,
                    placeholder="0",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .panels import painel_config_geral_components
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return
        try:
            limite = max(0, int(inter.text_values.get("limite", "0")))
        except ValueError:
            limite = 0
        form["limite_respostas"] = limite
        salvar_formulario(self.form_id, form)
        await inter.edit_original_message(components=painel_config_geral_components(self.form_id))


# ─── Modais de campo ──────────────────────────────────────────────────────────

class AdicionarCampoModal(disnake.ui.Modal):
    def __init__(self, form_id: str, tipo: str):
        self.form_id = form_id
        self.tipo = tipo
        tipo_info = FIELD_TYPES.get(tipo, {})
        super().__init__(
            title=f"Adicionar Campo: {tipo_info.get('label', tipo)}",
            custom_id=f"FormModal_AdicionarCampo:{form_id}:{tipo}",
            components=[
                disnake.ui.TextInput(
                    label="Label / Pergunta",
                    custom_id="label",
                    placeholder="Ex: Qual é seu maior ponto forte?",
                    max_length=45,
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Placeholder (texto de ajuda, opcional)",
                    custom_id="placeholder",
                    placeholder="Ex: Descreva com exemplos práticos...",
                    max_length=100,
                    required=False,
                ),
                disnake.ui.TextInput(
                    label="Obrigatório? (sim/não)",
                    custom_id="required",
                    value="sim",
                    max_length=3,
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Opções separadas por vírgula (só p/ Escolha)",
                    custom_id="opcoes",
                    placeholder="Opção A, Opção B, Opção C",
                    max_length=500,
                    required=False,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .panels import painel_campos_components
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return

        campos = form.get("campos", [])
        if len(campos) >= 5:
            await inter.followup.send(f"{emoji.wrong} Limite de 5 campos atingido.", ephemeral=True)
            return

        label = inter.text_values.get("label", "").strip()
        placeholder = inter.text_values.get("placeholder", "").strip()
        required_raw = inter.text_values.get("required", "sim").strip().lower()
        required = required_raw in ["sim", "s", "yes", "y", "true", "1"]
        opcoes_raw = inter.text_values.get("opcoes", "").strip()
        opcoes = [o.strip() for o in opcoes_raw.split(",") if o.strip()] if opcoes_raw else []

        campo = criar_campo(
            tipo=self.tipo,
            label=label,
            placeholder=placeholder,
            required=required,
            opcoes=opcoes,
        )
        campos.append(campo)
        form["campos"] = campos
        salvar_formulario(self.form_id, form)
        await inter.edit_original_message(components=painel_campos_components(self.form_id))


class EditarCampoModal(disnake.ui.Modal):
    def __init__(self, form_id: str, campo_id: str):
        self.form_id = form_id
        self.campo_id = campo_id

        form = get_formulario(form_id) or {}
        campo = next((c for c in form.get("campos", []) if c["id"] == campo_id), {})
        tipo_info = FIELD_TYPES.get(campo.get("tipo", "short"), {})

        super().__init__(
            title=f"Editar Campo: {campo.get('label', '')[:30]}",
            custom_id=f"FormModal_EditarCampo:{form_id}:{campo_id}",
            components=[
                disnake.ui.TextInput(
                    label="Label / Pergunta",
                    custom_id="label",
                    value=campo.get("label", ""),
                    max_length=45,
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Placeholder (texto de ajuda, opcional)",
                    custom_id="placeholder",
                    value=campo.get("placeholder", ""),
                    max_length=100,
                    required=False,
                ),
                disnake.ui.TextInput(
                    label="Obrigatório? (sim/não)",
                    custom_id="required",
                    value="sim" if campo.get("required", True) else "não",
                    max_length=3,
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Opções (separadas por vírgula, só p/ Escolha)",
                    custom_id="opcoes",
                    value=", ".join(campo.get("opcoes", [])),
                    max_length=500,
                    required=False,
                    placeholder="Opção A, Opção B, Opção C",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .panels import painel_campos_components
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return

        for campo in form.get("campos", []):
            if campo["id"] == self.campo_id:
                campo["label"] = inter.text_values.get("label", campo["label"]).strip()
                campo["placeholder"] = inter.text_values.get("placeholder", "").strip()
                req_raw = inter.text_values.get("required", "sim").strip().lower()
                campo["required"] = req_raw in ["sim", "s", "yes", "y", "true", "1"]
                opcoes_raw = inter.text_values.get("opcoes", "").strip()
                campo["opcoes"] = [o.strip() for o in opcoes_raw.split(",") if o.strip()]
                break

        salvar_formulario(self.form_id, form)
        await inter.edit_original_message(components=painel_campos_components(self.form_id))


# ─── Modal de preenchimento pelo usuário ─────────────────────────────────────

def build_response_modal(form: dict) -> disnake.ui.Modal | None:
    """
    Constrói o modal de preenchimento público.
    Discord permite máx. 5 componentes num modal.
    Campos de tipo 'choice' não entram no modal (são tratados em outro fluxo).
    """
    form_id = form["id"]
    campos_modal = [c for c in form.get("campos", []) if c.get("tipo") != "choice"][:5]

    if not campos_modal:
        return None

    components = []
    for campo in campos_modal:
        tipo = campo.get("tipo", "short")
        style = (
            disnake.TextInputStyle.paragraph
            if tipo == "paragraph"
            else disnake.TextInputStyle.short
        )
        components.append(
            disnake.ui.TextInput(
                label=campo["label"][:45],
                custom_id=campo["id"],
                placeholder=campo.get("placeholder", "")[:100] or None,
                required=campo.get("required", True),
                style=style,
                max_length=1000 if tipo == "paragraph" else 200,
                min_length=1 if campo.get("required") else 0,
            )
        )

    class _ResponseModal(disnake.ui.Modal):
        def __init__(self_inner):
            super().__init__(
                title=(form.get("nome") or "Formulário")[:45],
                custom_id=f"FormResposta_Modal:{form_id}",
                components=components,
            )

        async def callback(self_inner, inter: disnake.ModalInteraction):
            from .response_handler import processar_resposta_modal
            await processar_resposta_modal(inter, form, self_inner)

    return _ResponseModal()


class EditarMsgAprovadoModal(disnake.ui.Modal):
    def __init__(self, form_id: str):
        self.form_id = form_id
        form = get_formulario(form_id) or {}
        super().__init__(
            title="Mensagem de Aprovação",
            custom_id=f"FormModal_MsgAprovado:{form_id}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem enviada ao usuário quando aprovado",
                    custom_id="mensagem",
                    value=form.get("msg_aprovado", "✅ Sua resposta ao formulário **{nome}** foi aprovada!"),
                    style=disnake.TextInputStyle.paragraph,
                    max_length=500,
                    required=True,
                    placeholder="Use {nome} e {aprovador} como variáveis",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .panels import painel_msg_aprovacao_components
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return
        form["msg_aprovado"] = inter.text_values.get("mensagem", "")
        salvar_formulario(self.form_id, form)
        await inter.edit_original_message(components=painel_msg_aprovacao_components(self.form_id))


class EditarMsgReprovadoModal(disnake.ui.Modal):
    def __init__(self, form_id: str):
        self.form_id = form_id
        form = get_formulario(form_id) or {}
        super().__init__(
            title="Mensagem de Reprovação",
            custom_id=f"FormModal_MsgReprovado:{form_id}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem enviada ao usuário quando reprovado",
                    custom_id="mensagem",
                    value=form.get("msg_reprovado", f"{emoji.wrong} Sua resposta ao formulário **{nome}** foi reprovada."),
                    style=disnake.TextInputStyle.paragraph,
                    max_length=500,
                    required=True,
                    placeholder="Use {nome} e {reprovador} como variáveis",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .panels import painel_msg_aprovacao_components
        from functions.message import message, embed_message
        from functions.database import database as db

        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        form = get_formulario(self.form_id)
        if not form:
            return
        form["msg_reprovado"] = inter.text_values.get("mensagem", "")
        salvar_formulario(self.form_id, form)
        await inter.edit_original_message(components=painel_msg_aprovacao_components(self.form_id))


# ─── Modal de aprovação/rejeição ──────────────────────────────────────────────

class RejeicaoModal(disnake.ui.Modal):
    def __init__(self, form_id: str, resposta_id: str):
        self.form_id = form_id
        self.resposta_id = resposta_id
        super().__init__(
            title="Rejeitar Resposta",
            custom_id=f"FormModal_Rejeitar:{form_id}:{resposta_id}",
            components=[
                disnake.ui.TextInput(
                    label="Motivo da rejeição (enviado ao usuário)",
                    custom_id="motivo",
                    style=disnake.TextInputStyle.paragraph,
                    max_length=500,
                    required=False,
                    placeholder="Descreva o motivo da rejeição...",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .response_handler import processar_rejeicao
        await processar_rejeicao(inter, self.form_id, self.resposta_id,
                                  inter.text_values.get("motivo", ""))


# ─── Select de tipo de campo ──────────────────────────────────────────────────

def painel_selecionar_tipo_campo_components(form_id: str) -> list:
    from .helpers import get_colors, FIELD_TYPES
    primary_hex, ck = get_colors()

    options = [
        disnake.SelectOption(
            label=v["label"],
            value=f"{form_id}:{k}",
            emoji=v["emoji"],
            description=v["description"],
        )
        for k, v in FIELD_TYPES.items()
    ]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                "-# Formulários > Campos > **Selecionar Tipo**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Selecione o tipo de campo que deseja adicionar ao formulário."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Form_SelecionarTipoCampo",
                    placeholder="Selecione o tipo de campo...",
                    options=options,
                )
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", emoji=emoji.back,
                style=disnake.ButtonStyle.grey,
                custom_id=f"Form_EditarCampos:{form_id}",
            ),
        ),
    ]