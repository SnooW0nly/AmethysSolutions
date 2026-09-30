"""
modules/utilitarios/comunidade/formulario/cog.py

Cog principal do Sistema de Formulários.
Gerencia todos os botões, selects, modais e a lógica de roteamento.
"""
from __future__ import annotations

import io
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from .helpers import (
    carregar_config, get_formulario, salvar_formulario, deletar_formulario,
    build_formulario_embed, build_formulario_components, get_colors, get_mode,
    FIELD_TYPES,
)
from .panels import (
    painel_principal_components, painel_principal_embed,
    painel_selecionar_components, painel_editor_components,
    painel_campos_components, painel_aparencia_components,
    painel_config_geral_components, painel_canais_components,
    painel_cargos_components, painel_respostas_components,
    painel_msg_aprovacao_components,
)
from .modals import (
    CriarFormularioModal, EditarEmbedFormularioModal, EditarBotaoModal,
    EditarMsgSucessoModal, EditarLimiteModal, AdicionarCampoModal,
    EditarCampoModal, painel_selecionar_tipo_campo_components,
    build_response_modal, RejeicaoModal,
    EditarMsgAprovadoModal, EditarMsgReprovadoModal,
)
from .response_handler import (
    carregar_respostas, processar_aprovacao, processar_rejeicao,
    get_resposta, _build_resposta_embed,
)
from .publish import publicar_formulario, exportar_csv
from .staff_manager import (
    painel_staff_principal_components, painel_staff_lista_components,
    painel_staff_membro_components, painel_ranking_components,
    painel_config_pontuacao_components,
    toggle_staff_ativo, remover_staff, get_membro_staff,
    carregar_config_pontuacao, salvar_config_pontuacao,
    resetar_pontos_periodo,
)
from .staff_modals import (
    AdicionarStaffModal, EditarStaffModal, AjustePontosModal,
    EditarAcaoPontosModal, ConfigMultiplicadoresModal,
)
from .bateponto.panels import (
    painel_principal_bp_components, painel_principal_bp_embed,
    painel_selecionar_bp_components, painel_selecionar_bp_embed,
    painel_editor_bp_components, painel_editor_bp_embed,
)
from .bateponto.modals import (
    CriarBatePontoModal, EditarEmbedBPModal, EditarCanaisBPModal,
)
from .bateponto.logic import publicar_bateponto, processar_bateponto
from .bateponto.helpers import deletar_bateponto


class FormularioCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Renderizador de painel respeitando o modo ─────────────────────────────

    async def _render_painel(self, inter: disnake.MessageInteraction):
        mode = get_mode()
        if mode == "embed":
            embed, comps = painel_principal_embed()
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(components=painel_principal_components())

    async def _render_painel_bp(self, inter: disnake.MessageInteraction):
        mode = get_mode()
        if mode == "embed":
            embed, comps = painel_principal_bp_embed()
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(components=painel_principal_bp_components())

    async def _wait_and_render(self, inter: disnake.MessageInteraction):
        if inter.response.is_done():
            return
        mode = get_mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

    # ── Painel público (Painel → Comunidade) ──────────────────────────────────

    @staticmethod
    def Painel() -> list:
        return painel_principal_components()

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        return painel_principal_embed()

        # ── Listener de botões ────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _form_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Bate Ponto ───────────────────────────────────────────────────────
        if cid.startswith("BP_"):
            if cid.startswith("BP_Acao:"):
                _, acao, bp_id = cid.split(":")
                await processar_bateponto(inter, acao, bp_id)
                return

            if cid == "BP_Criar":
                await inter.response.send_modal(CriarBatePontoModal())
                return

            if cid.startswith("BP_EditarAparencia:"):
                bp_id = cid.split(":")[1]
                await inter.response.send_modal(EditarEmbedBPModal(bp_id))
                return

            if cid.startswith("BP_EditarCanais:"):
                bp_id = cid.split(":")[1]
                await inter.response.send_modal(EditarCanaisBPModal(bp_id))
                return

            if cid.startswith("BP_Publicar:"):
                bp_id = cid.split(":")[1]
                await publicar_bateponto(inter, bp_id)
                return

            await self._wait_and_render(inter)

            mode = get_mode()
            if cid == "BP_Principal":
                await self._render_painel_bp(inter)
            elif cid == "BP_VoltarPrincipal":
                await self._render_painel_bp(inter)
            elif cid == "BP_Gerenciar":
                if mode == "embed":
                    embed, comps = painel_selecionar_bp_embed("Gerenciar Bate Ponto", "BP_SelecionarEditar", "BP_VoltarPrincipal")
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_selecionar_bp_components("Gerenciar Bate Ponto", "BP_SelecionarEditar", "BP_VoltarPrincipal"))
            elif cid.startswith("BP_Toggle:"):
                bp_id = cid.split(":")[1]
                bp = get_bateponto(bp_id)
                if bp:
                    bp["ativado"] = not bp.get("ativado", False)
                    salvar_bateponto(bp_id, bp)
                if mode == "embed":
                    embed, comps = painel_editor_bp_embed(bp_id)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_editor_bp_components(bp_id))
            elif cid.startswith("BP_Apagar:"):
                bp_id = cid.split(":")[1]
                deletar_bateponto(bp_id)
                await self._render_painel_bp(inter)
            elif cid.startswith("BP_LimparCargosPermitidos:"):
                bp_id = cid.split(":")[1]
                bp = get_bateponto(bp_id)
                if bp:
                    bp["cargos_permitidos"] = []
                    salvar_bateponto(bp_id, bp)
                if mode == "embed":
                    embed, comps = painel_editor_bp_embed(bp_id)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_editor_bp_components(bp_id))
            elif cid.startswith("BP_LimparCargosNotificar:"):
                bp_id = cid.split(":")[1]
                bp = get_bateponto(bp_id)
                if bp:
                    bp["cargos_notificar"] = []
                    salvar_bateponto(bp_id, bp)
                if mode == "embed":
                    embed, comps = painel_editor_bp_embed(bp_id)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_editor_bp_components(bp_id))

            return

        if not cid.startswith("Form_"):
            return

        # ── Botões de resposta pública ────────────────────────────────────────
        if cid.startswith("Form_Responder:"):
            form_id = cid.split(":", 1)[1]
            await self._handle_responder(inter, form_id)
            return

        if cid.startswith("Form_Aprovar:"):
            _, form_id, resp_id = cid.split(":")
            await processar_aprovacao(inter, form_id, resp_id)
            return

        if cid.startswith("Form_Rejeitar:"):
            _, form_id, resp_id = cid.split(":")
            await inter.response.send_modal(RejeicaoModal(form_id, resp_id))
            return

        # ── Botões que abrem modal direto ─────────────────────────────────────
        if cid == "Form_Criar":
            await inter.response.send_modal(CriarFormularioModal())
            return

        if cid.startswith("Form_EditarEmbed:"):
            form_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarEmbedFormularioModal(form_id))
            return

        if cid.startswith("Form_EditarBotao:"):
            form_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarBotaoModal(form_id))
            return

        if cid.startswith("Form_EditarMsgSucesso:"):
            form_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarMsgSucessoModal(form_id))
            return

        if cid.startswith("Form_EditarMsgAprovado:"):
            form_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarMsgAprovadoModal(form_id))
            return

        if cid.startswith("Form_EditarMsgReprovado:"):
            form_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarMsgReprovadoModal(form_id))
            return

        if cid.startswith("Form_EditarLimite:"):
            form_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarLimiteModal(form_id))
            return

        if cid.startswith("Form_AdicionarCampo:"):
            form_id = cid.split(":", 1)[1]
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_selecionar_tipo_campo_components(form_id)
            )
            return

        # Publicar e ExportarCSV já fazem defer internamente — não chamar _wait_and_render
        if cid.startswith("Form_Publicar:"):
            form_id = cid.split(":", 1)[1]
            await publicar_formulario(inter, form_id)
            try:
                await inter.edit_original_message(components=painel_editor_components(form_id))
            except Exception:
                pass
            return

        if cid.startswith("Form_ExportarCSV:"):
            form_id = cid.split(":", 1)[1]
            await exportar_csv(inter, form_id)
            return

        # Salvar/Descartar do editor são tratados exclusivamente em _form_editor_anunciar_listener
        if cid.startswith("Form_SalvarEditorAnunciar:") or cid.startswith("Form_DescartarEditorAnunciar:"):
            return

        # ── Botões com defer → edit ───────────────────────────────────────────
        await self._wait_and_render(inter)

        # Navegação
        if cid == "Form_VoltarPrincipal":
            await self._render_painel(inter)

        elif cid == "Form_Gerenciar":
            await inter.edit_original_message(
                components=painel_selecionar_components(
                    "Gerenciar Formulários", "Form_SelecionarFormEditar", "Form_VoltarPrincipal"
                )
            )

        elif cid == "Form_VerRespostas":
            await inter.edit_original_message(
                components=painel_selecionar_components(
                    "Ver Respostas", "Form_SelecionarFormRespostas", "Form_VoltarPrincipal"
                )
            )

        elif cid.startswith("Form_Editor:"):
            form_id = cid.split(":", 1)[1]
            await inter.edit_original_message(components=painel_editor_components(form_id))

        elif cid.startswith("Form_EditarCampos:"):
            form_id = cid.split(":", 1)[1]
            await inter.edit_original_message(components=painel_campos_components(form_id))

        elif cid.startswith("Form_EditarAparencia:"):
            form_id = cid.split(":", 1)[1]
            await self._abrir_editor_anunciar(inter, form_id)

        elif cid.startswith("Form_EditarConfig:"):
            form_id = cid.split(":", 1)[1]
            await inter.edit_original_message(components=painel_config_geral_components(form_id))

        elif cid.startswith("Form_EditarCanais:"):
            form_id = cid.split(":", 1)[1]
            await inter.edit_original_message(components=painel_canais_components(form_id))

        elif cid.startswith("Form_EditarCargos:"):
            form_id = cid.split(":", 1)[1]
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        elif cid.startswith("Form_EditarMsgAprovacao:"):
            form_id = cid.split(":", 1)[1]
            await inter.edit_original_message(components=painel_msg_aprovacao_components(form_id))

        elif cid.startswith("Form_AbrirEditorAnunciar:"):
            form_id = cid.split(":", 1)[1]
            await self._abrir_editor_anunciar(inter, form_id)

        # Toggle ativo
        elif cid.startswith("Form_Toggle:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["ativado"] = not form.get("ativado", False)
                salvar_formulario(form_id, form)
                await self._sync_published_message(form)
            await inter.edit_original_message(components=painel_editor_components(form_id))

        # Toggle aprovação
        elif cid.startswith("Form_ToggleAprovacao:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["requer_aprovacao"] = not form.get("requer_aprovacao", False)
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_config_geral_components(form_id))

        # Toggle anônimo
        elif cid.startswith("Form_ToggleAnonimo:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["anonimo"] = not form.get("anonimo", False)
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_config_geral_components(form_id))

        # Apagar formulário
        elif cid.startswith("Form_Apagar:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                # Tentar deletar a mensagem publicada
                await self._delete_published_message(form)
                deletar_formulario(form_id)
            await self._render_painel(inter)

        # Preview
        elif cid.startswith("Form_Preview:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                embed = build_formulario_embed(form)
                components = build_formulario_components(form)
                await inter.followup.send(
                    content=f"-# Preview do formulário **{form.get('nome')}**",
                    embed=embed,
                    components=components,
                    ephemeral=True,
                )

        # Limpar cargos
        elif cid.startswith("Form_LimparCargosPermitidos:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["cargos_permitidos"] = []
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        elif cid.startswith("Form_LimparCargosNotificar:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["cargos_notificar"] = []
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        elif cid.startswith("Form_LimparCargoAprovacao:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["cargo_aprovacao_id"] = None
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        # Paginação de respostas
        elif cid.startswith("Form_RespPrev:") or cid.startswith("Form_RespNext:"):
            parts = cid.split(":")
            form_id = parts[1]
            page = int(parts[2])
            page = page - 1 if cid.startswith("Form_RespPrev:") else page + 1
            respostas = carregar_respostas(form_id)
            await inter.edit_original_message(
                components=painel_respostas_components(form_id, respostas, page)
            )

        # ── Listener de dropdowns ─────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _form_dropdown_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid.startswith("BP_"):
            await self._wait_and_render(inter)
            mode = get_mode()
            if cid == "BP_SelecionarEditar":
                bp_id = inter.values[0]
                if bp_id == "__none__": return
                if mode == "embed":
                    embed, comps = painel_editor_bp_embed(bp_id)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_editor_bp_components(bp_id))
            elif cid.startswith("BP_SetCargosPermitidos:"):
                bp_id = cid.split(":")[1]
                bp = get_bateponto(bp_id)
                if bp:
                    bp["cargos_permitidos"] = [int(v) for v in inter.values]
                    salvar_bateponto(bp_id, bp)
                if mode == "embed":
                    embed, comps = painel_editor_bp_embed(bp_id)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_editor_bp_components(bp_id))
            elif cid.startswith("BP_SetCargosNotificar:"):
                bp_id = cid.split(":")[1]
                bp = get_bateponto(bp_id)
                if bp:
                    bp["cargos_notificar"] = [int(v) for v in inter.values]
                    salvar_bateponto(bp_id, bp)
                if mode == "embed":
                    embed, comps = painel_editor_bp_embed(bp_id)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=painel_editor_bp_components(bp_id))
            return

        if not cid.startswith("Form_"):
            return

        # Branches que abrem modal devem responder ANTES de qualquer defer/wait
        if cid == "Form_SelecionarTipoCampo":
            val = inter.values[0]  # "form_id:tipo"
            form_id, tipo = val.rsplit(":", 1)
            await inter.response.send_modal(AdicionarCampoModal(form_id, tipo))
            return

        if cid.startswith("Form_SelecionarCampoEditar:"):
            form_id = cid.split(":", 1)[1]
            campo_id = inter.values[0]
            if campo_id == "__none__":
                return
            await inter.response.send_modal(EditarCampoModal(form_id, campo_id))
            return

        await self._wait_and_render(inter)

        # Selecionar formulário para editar
        if cid == "Form_SelecionarFormEditar":
            form_id = inter.values[0]
            if form_id == "__none__":
                return
            await inter.edit_original_message(components=painel_editor_components(form_id))

        # Selecionar formulário para ver respostas
        elif cid == "Form_SelecionarFormRespostas":
            form_id = inter.values[0]
            if form_id == "__none__":
                return
            respostas = carregar_respostas(form_id)
            await inter.edit_original_message(
                components=painel_respostas_components(form_id, respostas, 0)
            )

        # Selecionar campo para remover
        elif cid.startswith("Form_SelecionarCampoRemover:"):
            form_id = cid.split(":", 1)[1]
            campo_id = inter.values[0]
            if campo_id == "__none__":
                return
            form = get_formulario(form_id)
            if form:
                form["campos"] = [c for c in form.get("campos", []) if c["id"] != campo_id]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_campos_components(form_id))

        # Modo de exibição
        elif cid.startswith("Form_SetDisplayMode:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["display_mode"] = inter.values[0]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_config_geral_components(form_id))

        # Modo de envio
        elif cid.startswith("Form_SetSendMode:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["send_mode"] = inter.values[0]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_config_geral_components(form_id))

        # Canal do painel
        elif cid.startswith("Form_SetCanalPainel:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["canal_painel_id"] = inter.values[0]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_canais_components(form_id))

        # Canal de respostas
        elif cid.startswith("Form_SetCanalRespostas:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["canal_respostas_id"] = inter.values[0]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_canais_components(form_id))

        # Canal de tópicos
        elif cid.startswith("Form_SetCanalTopicos:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["canal_topicos_id"] = inter.values[0]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_canais_components(form_id))

        # Cargos permitidos
        elif cid.startswith("Form_SetCargosPermitidos:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["cargos_permitidos"] = [int(v) for v in inter.values]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        # Cargos de notificação
        elif cid.startswith("Form_SetCargosNotificar:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["cargos_notificar"] = [int(v) for v in inter.values]
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        # Cargo concedido na aprovação
        elif cid.startswith("Form_SetCargoAprovacao:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if form:
                form["cargo_aprovacao_id"] = int(inter.values[0]) if inter.values else None
                salvar_formulario(form_id, form)
            await inter.edit_original_message(components=painel_cargos_components(form_id))

        # Ver resposta individual
        elif cid.startswith("Form_VerResposta:"):
            form_id = cid.split(":", 1)[1]
            resp_id = inter.values[0]
            if resp_id == "__none__":
                return
            form = get_formulario(form_id)
            resposta = get_resposta(form_id, resp_id)
            if form and resposta:
                embed = _build_resposta_embed(form, resposta)
                comps = []
                if form.get("requer_aprovacao") and not resposta.get("aprovado") and not resposta.get("rejeitado"):
                    from .response_handler import _build_aprovacao_components
                    comps = _build_aprovacao_components(form, resposta)
                await inter.followup.send(embed=embed, components=comps or None, ephemeral=True)

    # ── Listener de modais ────────────────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def _form_modal_listener(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not (cid.startswith("FormModal_") or cid.startswith("FormResposta_")):
            return

        # Resposta do usuário via modal
        if cid.startswith("FormResposta_Modal:"):
            form_id = cid.split(":", 1)[1]
            form = get_formulario(form_id)
            if not form:
                return await inter.response.send_message(
                    f"{emoji.wrong} Formulário não encontrado.", ephemeral=True
                )
            from .response_handler import processar_resposta_modal
            await processar_resposta_modal(inter, form, None)
            return

        # Rejeição com motivo
        if cid.startswith("FormModal_Rejeitar:"):
            parts = cid.split(":")
            form_id, resp_id = parts[1], parts[2]
            motivo = inter.text_values.get("motivo", "")
            await processar_rejeicao(inter, form_id, resp_id, motivo)
            return

    @commands.Cog.listener("on_modal_submit")
    async def _form_anunciar_modal_listener(self, inter: disnake.ModalInteraction):
        """
        Quando um modal do Anúncios (Anunciar_Modal_*) é submetido no contexto
        do editor de aparência do formulário, após o processamento do Anúncios
        a mensagem é re-editada com o painel do formulário.
        """
        cid = inter.custom_id
        # Modais do Anúncios começam com prefixos específicos
        _ANUNCIAR_MODAL_PREFIXES = (
            "Anunciar_Modal_",
        )
        if not any(cid.startswith(p) for p in _ANUNCIAR_MODAL_PREFIXES):
            return

        from functions.database import database as _db
        anunciar_doc = _db.get_document("messages_anunciar") or {}
        form_id = anunciar_doc.get("_form_editor_form_id")
        if not form_id:
            return

        # Aguarda o processamento do modal pelo listener do Anúncios,
        # depois sobrescreve com o painel correto do formulário
        import asyncio

        async def _corrigir_painel_modal():
            await asyncio.sleep(0.5)
            try:
                await inter.edit_original_message(
                    components=self._build_form_anunciar_panel(form_id)
                )
            except Exception:
                pass

        asyncio.create_task(_corrigir_painel_modal())

    # ── Handler de resposta pública ───────────────────────────────────────────

    async def _handle_responder(self, inter: disnake.MessageInteraction, form_id: str) -> None:
        form = get_formulario(form_id)
        if not form:
            await inter.response.send_message(f"{emoji.wrong} Formulário não encontrado.", ephemeral=True)
            return

        if not form.get("ativado"):
            await inter.response.send_message(f"{emoji.wrong} Este formulário está desativado.", ephemeral=True)
            return

        # Verificação de cargos
        cargos_perm = form.get("cargos_permitidos", [])
        if cargos_perm:
            user_roles = [r.id for r in getattr(inter.author, "roles", [])]
            if not any(int(c) in user_roles for c in cargos_perm):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para preencher este formulário.", ephemeral=True
                )
                return

        # Verificar limite
        from .response_handler import verificar_limite, verificar_ja_respondeu
        ok, msg = verificar_limite(form)
        if not ok:
            await inter.response.send_message(msg, ephemeral=True)
            return

        if verificar_ja_respondeu(form, inter.author.id):
            await inter.response.send_message(
                f"{emoji.warn} Você já enviou uma resposta para este formulário.", ephemeral=True
            )
            return

        display_mode = form.get("display_mode", "modal")

        if display_mode == "modal":
            modal = build_response_modal(form)
            if modal:
                await inter.response.send_modal(modal)
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} Este formulário não tem campos configurados.", ephemeral=True
                )

        elif display_mode == "channel":
            canal_id = form.get("canal_painel_id")
            canal_mention = f"<#{canal_id}>" if canal_id else "o canal configurado"
            await inter.response.send_message(
                f"{emoji.textc} Acesse {canal_mention} para preencher este formulário.",
                ephemeral=True,
            )

        elif display_mode == "topic":
            # Criar tópico privado para o usuário
            canal_id = form.get("canal_topicos_id") or form.get("canal_painel_id")
            if not canal_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Nenhum canal configurado para criação de tópicos.", ephemeral=True
                )
                return
            await inter.response.defer(ephemeral=True)
            try:
                canal = self.bot.get_channel(int(canal_id)) or await self.bot.fetch_channel(int(canal_id))
                if isinstance(canal, disnake.TextChannel):
                    thread = await canal.create_thread(
                        name=f"{form.get('nome', 'Form')[:30]} — {inter.author.display_name}",
                        type=disnake.ChannelType.private_thread,
                        invitable=False,
                    )
                    await thread.add_user(inter.author)

                    # Enviar as perguntas no tópico
                    primary_hex, _ = get_colors()
                    cor = int(primary_hex.replace("#", ""), 16) if primary_hex else 0x5865F2
                    embed = disnake.Embed(
                        title=form.get("embed_titulo") or form["nome"],
                        description=form.get("embed_descricao", "Responda às perguntas abaixo:"),
                        color=cor,
                    )
                    campos = form.get("campos", [])
                    for i, c in enumerate(campos):
                        req = "🔴 Obrigatório" if c.get("required") else "🟡 Opcional"
                        embed.add_field(
                            name=f"{i+1}. {c['label']}",
                            value=f"`{FIELD_TYPES.get(c['tipo'],{}).get('label',c['tipo'])}` — {req}",
                            inline=False,
                        )
                    await thread.send(
                        content=f"{inter.author.mention} — Preencha cada campo respondendo neste tópico.",
                        embed=embed,
                    )
                    await inter.followup.send(
                        f"{emoji.correct} Tópico criado: {thread.mention}", ephemeral=True
                    )
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro ao criar tópico: `{e}`", ephemeral=True)

    # ── Helpers internos ──────────────────────────────────────────────────────

    async def _sync_published_message(self, form: dict) -> None:
        """Atualiza a mensagem publicada do formulário (botão ativo/inativo)."""
        canal_id = form.get("canal_painel_id")
        msg_id = form.get("message_id")
        if not canal_id or not msg_id:
            return
        try:
            canal = self.bot.get_channel(int(canal_id)) or await self.bot.fetch_channel(int(canal_id))
            msg = await canal.fetch_message(int(msg_id))
            embed = build_formulario_embed(form)
            components = build_formulario_components(form)
            await msg.edit(embed=embed, components=components)
        except Exception:
            pass

    async def _delete_published_message(self, form: dict) -> None:
        """Remove a mensagem publicada ao deletar o formulário."""
        canal_id = form.get("canal_painel_id")
        msg_id = form.get("message_id")
        if not canal_id or not msg_id:
            return
        try:
            canal = self.bot.get_channel(int(canal_id)) or await self.bot.fetch_channel(int(canal_id))
            msg = await canal.fetch_message(int(msg_id))
            await msg.delete()
        except Exception:
            pass

    # ── Painel de aparência do formulário (editor limitado) ───────────────────

    @staticmethod
    def _build_form_anunciar_panel(form_id: str) -> list:
        """
        Painel de aparência completo do formulário.
        Inclui: mensagem/embed/container/imagem (via módulo Anúncios)
                + configuração do botão do formulário.
        """
        from commands.admin.anunciar.anunciar import Anunciar
        from functions.database import database as _db
        from .helpers import get_formulario, estilo_para_disnake

        cfg = _db.get_document("messages_anunciar") or {}
        msg = cfg.get("message", {}) or {}

        has_container = Anunciar._safe_get(msg, "container") is not None
        has_message   = bool(Anunciar._safe_get(msg, "content"))
        has_embed     = any([
            Anunciar._safe_get(msg, "embed.title"),
            Anunciar._safe_get(msg, "embed.description"),
            Anunciar._safe_get(msg, "embed.color"),
            Anunciar._safe_get(msg, "embed.footer"),
        ])
        has_image = any([
            Anunciar._safe_get(msg, "externalImage"),
            Anunciar._safe_get(msg, "embed.banner"),
            Anunciar._safe_get(msg, "embed.thumbnail"),
        ])
        others_exist = has_embed

        # Dados do botão do formulário
        form = get_formulario(form_id) or {}
        btn_label  = form.get("botao_label") or "Preencher Formulário"
        btn_emoji_val = form.get("botao_emoji") or f"{emoji.edit}"
        btn_estilo = form.get("botao_estilo", "blurple")
        msg_suc    = (form.get("mensagem_sucesso") or "")[:60]

        def _row(label, define_id, delete_id, icon_define, has_value, define_disabled=False):
            return disnake.ui.ActionRow(
                disnake.ui.Button(
                    style=disnake.ButtonStyle.red,
                    custom_id=delete_id,
                    emoji=emoji.delete,
                    disabled=not has_value,
                ),
                disnake.ui.Button(
                    label=f"Definir {label}",
                    style=disnake.ButtonStyle.secondary,
                    custom_id=define_id,
                    emoji=icon_define,
                    disabled=define_disabled,
                ),
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Formulários > **Aparência**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                # ── Seção: mensagem publicada ──────────────────────────────
                disnake.ui.TextDisplay(
                    f"**{emoji.embed} Mensagem publicada**\n"
                    f"-# Conteúdo exibido no canal onde o formulário é publicado."
                ),
                _row("Mensagem",  "Anunciar_DefinirMensagem",  "Anunciar_ApagarMensagem",  emoji.message,  has_message),
                _row("Container", "Anunciar_DefinirContainer", "Anunciar_ApagarContainer", emoji.commands, has_container, define_disabled=others_exist),
                _row("Embed",     "Anunciar_DefinirEmbed",     "Anunciar_ApagarEmbed",     emoji.embed,    has_embed,     define_disabled=has_container),
                _row("Imagens",   "Anunciar_DefinirImagem",    "Anunciar_ApagarImagem",    emoji.image,    has_image),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                # ── Seção: botão do formulário ─────────────────────────────
                disnake.ui.TextDisplay(
                    f"**{emoji.wand} Botão do formulário**\n"
                    f"-# Label: `{btn_label}`  ·  Emoji: {btn_emoji_val}  ·  Estilo: `{btn_estilo}`"
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar Botão",
                        style=disnake.ButtonStyle.secondary,
                        emoji=emoji.wand,
                        custom_id=f"Form_EditarBotao:{form_id}",
                    ),
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                # ── Seção: mensagem de sucesso ─────────────────────────────
                disnake.ui.TextDisplay(
                    f"**{emoji.correct} Mensagem de sucesso**\n"
                    f"-# `{msg_suc or 'Não definida'}`"
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar Mensagem de Sucesso",
                        style=disnake.ButtonStyle.secondary,
                        emoji=emoji.correct,
                        custom_id=f"Form_EditarMsgSucesso:{form_id}",
                    ),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Salvar e Voltar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.correct,
                    custom_id=f"Form_SalvarEditorAnunciar:{form_id}",
                ),
                disnake.ui.Button(
                    label="Descartar",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id=f"Form_DescartarEditorAnunciar:{form_id}",
                ),
            ),
        ]

    async def _abrir_editor_anunciar(
        self, inter: disnake.MessageInteraction, form_id: str
    ) -> None:
        """
        Abre o editor de aparência limitado do formulário.
        Carrega os dados do formulário no DB do Anúncios, exibe apenas
        as seções de content/embed/container/imagem (sem botões/selects).
        """
        from functions.database import database as _db

        form = get_formulario(form_id)
        if not form:
            await inter.followup.send(f"{emoji.wrong} Formulário não encontrado.", ephemeral=True)
            return

        editor_data = form.get("anunciar_editor") or {}

        anunciar_doc = _db.get_document("messages_anunciar") or {}
        anunciar_doc.setdefault("message", {})
        anunciar_doc["_form_editor_backup"] = anunciar_doc.get("message", {}).copy()
        anunciar_doc["_form_editor_form_id"] = form_id
        anunciar_doc["message"] = {
            "content":       editor_data.get("content"),
            "container":     editor_data.get("container"),
            "externalImage": editor_data.get("externalImage"),
            "embed": editor_data.get("embed") or {
                "title": None, "description": None,
                "color": None, "footer": None,
                "banner": None, "thumbnail": None,
            },
            # Botões e selects são gerenciados separadamente no formulário
            "buttons": [],
            "selects": [],
            "send_mode": "auto",
            "component_order": ["buttons", "selects"],
        }
        _db.save_document("messages_anunciar", {}, anunciar_doc)

        await inter.edit_original_message(
            components=self._build_form_anunciar_panel(form_id)
        )

    @commands.Cog.listener("on_button_click")
    async def _form_editor_anunciar_listener(self, inter: disnake.MessageInteraction):
        """Listener separado para os botões de salvar/descartar do editor do Anúncios."""
        cid = inter.component.custom_id

        if cid.startswith("Form_SalvarEditorAnunciar:"):
            form_id = cid.split(":", 1)[1]
            await self._wait_and_render(inter)

            from functions.database import database as _db
            anunciar_doc = _db.get_document("messages_anunciar") or {}
            msg_data = anunciar_doc.get("message") or {}

            # Lê os dados editados e salva de volta no formulário
            form = get_formulario(form_id)
            if form:
                form["anunciar_editor"] = {
                    "content":       msg_data.get("content"),
                    "container":     msg_data.get("container"),
                    "externalImage": msg_data.get("externalImage"),
                    "embed":         msg_data.get("embed") or {},
                }
                # Também atualiza embed_titulo/embed_descricao/embed_cor para compatibilidade
                embed = msg_data.get("embed") or {}
                if embed.get("title"):
                    form["embed_titulo"] = embed["title"]
                if embed.get("description"):
                    form["embed_descricao"] = embed["description"]
                if embed.get("color"):
                    form["embed_cor"] = embed["color"]
                salvar_formulario(form_id, form)

            # Restaura o backup do Anúncios
            backup = anunciar_doc.pop("_form_editor_backup", None)
            anunciar_doc.pop("_form_editor_form_id", None)
            if backup is not None:
                anunciar_doc["message"] = backup
            _db.save_document("messages_anunciar", {}, anunciar_doc)

            await inter.edit_original_message(components=painel_editor_components(form_id))

        elif cid.startswith("Form_DescartarEditorAnunciar:"):
            form_id = cid.split(":", 1)[1]
            await self._wait_and_render(inter)

            from functions.database import database as _db
            anunciar_doc = _db.get_document("messages_anunciar") or {}
            backup = anunciar_doc.pop("_form_editor_backup", None)
            anunciar_doc.pop("_form_editor_form_id", None)
            if backup is not None:
                anunciar_doc["message"] = backup
            _db.save_document("messages_anunciar", {}, anunciar_doc)

            await inter.edit_original_message(components=painel_editor_components(form_id))

    @commands.Cog.listener("on_button_click")
    async def _form_anunciar_apagar_listener(self, inter: disnake.MessageInteraction):
        """
        Intercepta os botões de apagar do Anúncios (Anunciar_Apagar*) quando estamos
        no contexto do editor de aparência de um formulário.
        Executa a lógica de apagar diretamente e re-renderiza o painel do formulário,
        evitando que o listener do Anúncios sobrescreva com seu próprio painel.
        """
        cid = inter.component.custom_id

        _APAGAR_MAP = {
            "Anunciar_ApagarMensagem":  "content",
            "Anunciar_ApagarContainer": "container",
            "Anunciar_ApagarEmbed":     "embed",
            "Anunciar_ApagarImagem":    "externalImage",
        }
        if cid not in _APAGAR_MAP:
            return

        from functions.database import database as _db
        anunciar_doc = _db.get_document("messages_anunciar") or {}
        form_id = anunciar_doc.get("_form_editor_form_id")
        if not form_id:
            # Não estamos no contexto do editor de formulário — o Anúncios trata normalmente
            return

        # Tomamos conta da interação para evitar double-defer pelo listener do Anúncios
        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        campo = _APAGAR_MAP[cid]
        msg = anunciar_doc.get("message", {})

        if campo == "embed":
            # Apagar embed limpa todos os sub-campos
            for key in (msg.get("embed") or {}):
                msg["embed"][key] = None
        elif campo == "externalImage":
            msg["externalImage"] = None
            # Também limpa banner e thumbnail do embed
            embed_cfg = msg.get("embed") or {}
            embed_cfg["banner"] = None
            embed_cfg["thumbnail"] = None
        else:
            msg[campo] = None

        anunciar_doc["message"] = msg
        _db.save_document("messages_anunciar", {}, anunciar_doc)

        await inter.edit_original_message(
            components=self._build_form_anunciar_panel(form_id)
        )



    # ── Listener de botões — Staff Manager ───────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _staff_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Staff_"):
            return

        # Navegação principal
        if cid == "Staff_Principal":
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_staff_principal_components()
            )
            return

        if cid == "Staff_VerLista":
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_staff_lista_components(0)
            )
            return

        if cid == "Staff_Ranking":
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_ranking_components(por_periodo=False)
            )
            return

        if cid == "Staff_RankingPeriodo":
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_ranking_components(por_periodo=True)
            )
            return

        if cid == "Staff_RankingTotal":
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_ranking_components(por_periodo=False)
            )
            return

        if cid == "Staff_ConfigPontuacao":
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_config_pontuacao_components()
            )
            return

        # Toggle sistema de pontuação
        if cid == "Staff_ToggleSistemaPontos":
            await self._wait_and_render(inter)
            cfg = carregar_config_pontuacao()
            cfg["ativo"] = not cfg.get("ativo", True)
            salvar_config_pontuacao(cfg)
            await inter.edit_original_message(
                components=painel_config_pontuacao_components()
            )
            return

        if cid == "Staff_ToggleMostrarPontos":
            await self._wait_and_render(inter)
            cfg = carregar_config_pontuacao()
            cfg["mostrar_pontos_usuario"] = not cfg.get("mostrar_pontos_usuario", True)
            salvar_config_pontuacao(cfg)
            await inter.edit_original_message(
                components=painel_config_pontuacao_components()
            )
            return

        if cid == "Staff_SetCanalRanking":
            await self._wait_and_render(inter)
            from .helpers import get_colors
            _, ck = get_colors()
            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Staff > Config Pontuação > **Canal de Ranking**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay("Selecione o canal onde o ranking automático será exibido."),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.ActionRow(
                            disnake.ui.ChannelSelect(
                                custom_id="Staff_SetCanalRankingSelect",
                                placeholder="Selecione o canal...",
                                channel_types=[disnake.ChannelType.text],
                                min_values=1, max_values=1,
                            )
                        ),
                        **ck,
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                          style=disnake.ButtonStyle.grey,
                                          custom_id="Staff_ConfigPontuacao"),
                    ),
                ]
            )
            return

        if cid == "Staff_ConfigMultiplicadores":
            await inter.response.send_modal(ConfigMultiplicadoresModal())
            return

        # Resetar período
        if cid == "Staff_ResetarPeriodo":
            await self._wait_and_render(inter)
            count = resetar_pontos_periodo()
            await inter.edit_original_message(
                components=painel_staff_principal_components()
            )
            await inter.followup.send(
                f"{emoji.correct} Pontos do período resetados para `{count}` membro(s).",
                ephemeral=True,
            )
            return

        # Adicionar staff → modal
        if cid == "Staff_Adicionar":
            await inter.response.send_modal(AdicionarStaffModal())
            return

        # Ajuste manual (sem membro específico)
        if cid == "Staff_AjusteManual":
            await inter.response.send_modal(AjustePontosModal())
            return

        # Ações em membro específico
        if cid.startswith("Staff_ToggleAtivo:"):
            uid = int(cid.split(":", 1)[1])
            await self._wait_and_render(inter)
            toggle_staff_ativo(uid)
            await inter.edit_original_message(
                components=painel_staff_membro_components(uid)
            )
            return

        if cid.startswith("Staff_EditarMembro:"):
            uid = int(cid.split(":", 1)[1])
            await inter.response.send_modal(EditarStaffModal(uid))
            return

        if cid.startswith("Staff_AjustePontosMembro:"):
            uid = int(cid.split(":", 1)[1])
            await inter.response.send_modal(AjustePontosModal(uid))
            return

        if cid.startswith("Staff_RemoverMembro:"):
            uid = int(cid.split(":", 1)[1])
            await self._wait_and_render(inter)
            remover_staff(uid)
            await inter.edit_original_message(
                components=painel_staff_lista_components(0)
            )
            await inter.followup.send(
                f"{emoji.correct} Staff <@{uid}> removido (marcado como inativo).",
                ephemeral=True,
            )
            return

        # Paginação da lista
        if cid.startswith("Staff_ListaPrev:") or cid.startswith("Staff_ListaNext:"):
            parts = cid.split(":")
            page  = int(parts[1])
            page  = page - 1 if cid.startswith("Staff_ListaPrev:") else page + 1
            await self._wait_and_render(inter)
            await inter.edit_original_message(
                components=painel_staff_lista_components(page)
            )
            return

    # ── Listener de dropdowns — Staff Manager ────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _staff_dropdown_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Staff_"):
            return

        await self._wait_and_render(inter)

        if cid == "Staff_SelecionarMembro":
            val = inter.values[0]
            if val == "__none__":
                return
            uid = int(val)
            await inter.edit_original_message(
                components=painel_staff_membro_components(uid)
            )

        elif cid == "Staff_SetResetPeriod":
            cfg = carregar_config_pontuacao()
            cfg["reset_period"] = inter.values[0]
            salvar_config_pontuacao(cfg)
            await inter.edit_original_message(
                components=painel_config_pontuacao_components()
            )

        elif cid == "Staff_EditarAcao":
            acao_key = inter.values[0]
            await inter.response.send_modal(EditarAcaoPontosModal(acao_key))
            return

        elif cid == "Staff_SetCanalRankingSelect":
            cfg = carregar_config_pontuacao()
            cfg["canal_ranking_id"] = inter.values[0]
            salvar_config_pontuacao(cfg)
            await inter.edit_original_message(
                components=painel_config_pontuacao_components()
            )

    # ── Listener de modais — Staff Manager ───────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def _staff_modal_listener(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("StaffModal_"):
            return

        if cid == "StaffModal_Adicionar":
            # handled inside modal callback
            pass

        elif cid.startswith("StaffModal_Editar:"):
            pass  # handled inside modal callback

        elif cid.startswith("StaffModal_AjustePontos:"):
            pass  # handled inside modal callback

        elif cid.startswith("StaffModal_EditarAcao:"):
            pass  # handled inside modal callback

        elif cid == "StaffModal_ConfigMultiplicadores":
            pass  # handled inside modal callback


def setup(bot: commands.Bot):
    bot.add_cog(FormularioCog(bot))