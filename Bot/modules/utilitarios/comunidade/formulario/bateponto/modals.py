"""
modules/utilitarios/comunidade/formulario/bateponto/modals.py

Modais para o sistema de Bate Ponto.
"""
from __future__ import annotations

import disnake
from functions.emoji import emoji
from .helpers import (
    criar_bateponto, get_bateponto, salvar_bateponto,
)

class CriarBatePontoModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Nome do Sistema",
                placeholder="Ex: Bate Ponto Staff",
                custom_id="nome",
                min_length=3,
                max_length=50,
            ),
        ]
        super().__init__(title="Criar Bate Ponto", custom_id="BP_ModalCriar", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        nome = inter.text_values["nome"]
        bp_id = criar_bateponto(nome)
        
        from ..helpers import get_mode
        from .panels import painel_editor_bp_components, painel_editor_bp_embed
        
        mode = get_mode()
        if mode == "embed":
            embed, comps = painel_editor_bp_embed(bp_id)
            await inter.response.edit_message(embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=painel_editor_bp_components(bp_id))

class EditarEmbedBPModal(disnake.ui.Modal):
    def __init__(self, bp_id: str):
        bp = get_bateponto(bp_id)
        components = [
            disnake.ui.TextInput(
                label="Título do Embed",
                placeholder="Ex: Sistema de Bate Ponto",
                custom_id="titulo",
                value=bp.get("embed_titulo", ""),
                max_length=256,
            ),
            disnake.ui.TextInput(
                label="Descrição do Embed",
                placeholder="Ex: Clique no botão abaixo para iniciar ou finalizar seu turno.",
                custom_id="descricao",
                value=bp.get("embed_descricao", ""),
                style=disnake.TextInputStyle.paragraph,
                max_length=2000,
            ),
            disnake.ui.TextInput(
                label="Cor do Embed (Hex)",
                placeholder="Ex: #00FF00",
                custom_id="cor",
                value=bp.get("embed_cor") or "",
                min_length=7,
                max_length=7,
                required=False,
            ),
        ]
        super().__init__(title="Editar Aparência", custom_id=f"BP_ModalEmbed:{bp_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        bp_id = self.custom_id.split(":")[1]
        bp = get_bateponto(bp_id)
        if not bp: return

        bp["embed_titulo"] = inter.text_values["titulo"]
        bp["embed_descricao"] = inter.text_values["descricao"]
        bp["embed_cor"] = inter.text_values["cor"] or None
        
        salvar_bateponto(bp_id, bp)
        
        from ..helpers import get_mode
        from .panels import painel_editor_bp_components, painel_editor_bp_embed
        
        mode = get_mode()
        if mode == "embed":
            embed, comps = painel_editor_bp_embed(bp_id)
            await inter.response.edit_message(embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=painel_editor_bp_components(bp_id))

class EditarBotaoBPModal(disnake.ui.Modal):
    def __init__(self, bp_id: str, tipo: str):
        bp = get_bateponto(bp_id)
        self.tipo = tipo # 'entrada' ou 'saida'
        prefix = f"botao_{tipo}"
        
        components = [
            disnake.ui.TextInput(
                label="Texto do Botão",
                placeholder="Ex: Bater Ponto",
                custom_id="label",
                value=bp.get(f"{prefix}_label", ""),
                max_length=80,
            ),
            disnake.ui.TextInput(
                label="Emoji do Botão",
                placeholder="Ex: ⏰",
                custom_id="emoji",
                value=bp.get(f"{prefix}_emoji", ""),
                max_length=50,
            ),
            disnake.ui.TextInput(
                label="Estilo (green, red, blurple, grey)",
                placeholder="Ex: green",
                custom_id="estilo",
                value=bp.get(f"{prefix}_estilo", ""),
                max_length=20,
            ),
        ]
        super().__init__(title=f"Editar Botão ({tipo.capitalize()})", custom_id=f"BP_ModalBotao:{tipo}:{bp_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        bp_id = self.custom_id.split(":")[2]
        bp = get_bateponto(bp_id)
        if not bp: return

        prefix = f"botao_{self.tipo}"
        bp[f"{prefix}_label"] = inter.text_values["label"]
        bp[f"{prefix}_emoji"] = inter.text_values["emoji"]
        bp[f"{prefix}_estilo"] = inter.text_values["estilo"].lower()
        
        salvar_bateponto(bp_id, bp)
        
        from ..helpers import get_mode
        from .panels import painel_editor_bp_components, painel_editor_bp_embed
        from .logic import build_bp_anunciar_panel
        
        await inter.response.edit_message(components=build_bp_anunciar_panel(bp_id))

class EditarMsgSucessoBPModal(disnake.ui.Modal):
    def __init__(self, bp_id: str):
        bp = get_bateponto(bp_id)
        components = [
            disnake.ui.TextInput(
                label="Mensagem de Sucesso",
                placeholder="Ex: ✅ Ponto registrado!",
                custom_id="mensagem",
                value=bp.get("mensagem_sucesso", ""),
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
            ),
        ]
        super().__init__(title="Editar Sucesso", custom_id=f"BP_ModalSucesso:{bp_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        bp_id = self.custom_id.split(":")[1]
        bp = get_bateponto(bp_id)
        if not bp: return

        bp["mensagem_sucesso"] = inter.text_values["mensagem"]
        salvar_bateponto(bp_id, bp)
        
        from .logic import build_bp_anunciar_panel
        await inter.response.edit_message(components=build_bp_anunciar_panel(bp_id))

class EditarCanaisBPModal(disnake.ui.Modal):
    def __init__(self, bp_id: str):
        bp = get_bateponto(bp_id)
        components = [
            disnake.ui.TextInput(
                label="ID do Canal do Painel",
                placeholder="Onde o botão de bater ponto ficará",
                custom_id="canal_painel",
                value=str(bp.get("canal_painel_id") or ""),
                max_length=20,
            ),
            disnake.ui.TextInput(
                label="ID do Canal de Logs",
                placeholder="Onde os registros de entrada/saída serão enviados",
                custom_id="canal_logs",
                value=str(bp.get("canal_logs_id") or ""),
                max_length=20,
            ),
        ]
        super().__init__(title="Editar Canais", custom_id=f"BP_ModalCanais:{bp_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        bp_id = self.custom_id.split(":")[1]
        bp = get_bateponto(bp_id)
        if not bp: return

        try:
            bp["canal_painel_id"] = int(inter.text_values["canal_painel"])
            bp["canal_logs_id"] = int(inter.text_values["canal_logs"])
        except ValueError:
            await inter.response.send_message("IDs de canal inválidos!", ephemeral=True)
            return

        salvar_bateponto(bp_id, bp)
        
        from ..helpers import get_mode
        from .panels import painel_editor_bp_components, painel_editor_bp_embed
        
        mode = get_mode()
        if mode == "embed":
            embed, comps = painel_editor_bp_embed(bp_id)
            await inter.response.edit_message(embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=painel_editor_bp_components(bp_id))
