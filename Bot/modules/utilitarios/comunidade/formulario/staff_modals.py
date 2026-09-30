"""
modules/utilitarios/comunidade/formulario/staff_modals.py

Modais do sistema de Staff Manager e Pontuação.
"""
from __future__ import annotations

import disnake
from functions.emoji import emoji
from .staff_manager import (
    adicionar_staff, get_membro_staff, ajustar_pontos_manual,
    carregar_config_pontuacao, salvar_config_pontuacao,
    ACOES_PADRAO,
)


class AdicionarStaffModal(disnake.ui.Modal):
    def __init__(self, user_id: int = 0, nome: str = ""):
        self._user_id = user_id
        components = [
            disnake.ui.TextInput(
                label="ID do Usuário Discord",
                custom_id="user_id",
                placeholder="Ex: 123456789012345678",
                value=str(user_id) if user_id else "",
                max_length=20,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Nome / Apelido",
                custom_id="nome",
                placeholder="Nome para exibição no sistema",
                value=nome,
                max_length=50,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Cargo / Título (Opcional)",
                custom_id="cargo_titulo",
                placeholder="Ex: Moderador Sênior, Suporte Jr.",
                max_length=50,
                required=False,
            ),
            disnake.ui.TextInput(
                label="Observações (Opcional)",
                custom_id="observacoes",
                placeholder="Notas internas sobre o membro...",
                style=disnake.TextInputStyle.paragraph,
                max_length=200,
                required=False,
            ),
        ]
        super().__init__(title="Adicionar Staff", components=components, custom_id="StaffModal_Adicionar")

    async def callback(self, inter: disnake.ModalInteraction):
        from .staff_manager import painel_staff_lista_components, adicionar_staff
        try:
            uid = int(inter.text_values["user_id"].strip())
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} ID de usuário inválido.", ephemeral=True
            )
            return

        nome       = inter.text_values["nome"].strip()
        cargo      = inter.text_values.get("cargo_titulo", "").strip()
        obs        = inter.text_values.get("observacoes", "").strip()

        adicionar_staff(uid, nome, cargo, obs)
        await inter.response.send_message(
            f"{emoji.correct} <@{uid}> adicionado ao staff com sucesso!", ephemeral=True
        )


class EditarStaffModal(disnake.ui.Modal):
    def __init__(self, user_id: int):
        self._user_id = user_id
        membro = get_membro_staff(user_id) or {}
        components = [
            disnake.ui.TextInput(
                label="Nome / Apelido",
                custom_id="nome",
                value=membro.get("nome", ""),
                max_length=50,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Cargo / Título (Opcional)",
                custom_id="cargo_titulo",
                value=membro.get("cargo_titulo", ""),
                max_length=50,
                required=False,
            ),
            disnake.ui.TextInput(
                label="Observações (Opcional)",
                custom_id="observacoes",
                value=membro.get("observacoes", ""),
                style=disnake.TextInputStyle.paragraph,
                max_length=200,
                required=False,
            ),
        ]
        super().__init__(
            title="Editar Staff",
            components=components,
            custom_id=f"StaffModal_Editar:{user_id}",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .staff_manager import painel_staff_membro_components
        nome  = inter.text_values["nome"].strip()
        cargo = inter.text_values.get("cargo_titulo", "").strip()
        obs   = inter.text_values.get("observacoes", "").strip()
        adicionar_staff(self._user_id, nome, cargo, obs)

        from functions.message import message as msg_helper, embed_message
        from .helpers import get_mode
        mode = get_mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await msg_helper.wait(inter, send=False)

        await inter.edit_original_message(
            components=painel_staff_membro_components(self._user_id)
        )


class AjustePontosModal(disnake.ui.Modal):
    def __init__(self, user_id: int = 0):
        self._user_id = user_id
        membro = get_membro_staff(user_id) if user_id else None
        nome_label = f" — {membro['nome']}" if membro else ""
        components = [
            disnake.ui.TextInput(
                label="ID do Usuário" if not user_id else f"Usuário{nome_label}",
                custom_id="user_id",
                placeholder="ID do Discord",
                value=str(user_id) if user_id else "",
                max_length=20,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Pontos (+/-)",
                custom_id="pontos",
                placeholder="Ex: 50 ou -20",
                max_length=6,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Motivo (Opcional)",
                custom_id="motivo",
                placeholder="Descreva o motivo do ajuste...",
                style=disnake.TextInputStyle.paragraph,
                max_length=200,
                required=False,
            ),
        ]
        super().__init__(
            title="Ajuste Manual de Pontos",
            components=components,
            custom_id=f"StaffModal_AjustePontos:{user_id}",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            uid    = int(inter.text_values["user_id"].strip())
            pontos = int(inter.text_values["pontos"].strip())
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Valores inválidos.", ephemeral=True
            )
            return

        motivo = inter.text_values.get("motivo", "").strip()
        total  = ajustar_pontos_manual(uid, pontos, motivo, inter.author.id)
        sinal  = "+" if pontos >= 0 else ""
        await inter.response.send_message(
            f"{emoji.correct} Ajuste de `{sinal}{pontos}pts` aplicado a <@{uid}>. "
            f"Total agora: **{total}pts**.",
            ephemeral=True,
        )


class EditarAcaoPontosModal(disnake.ui.Modal):
    def __init__(self, acao_key: str):
        self._acao = acao_key
        info = ACOES_PADRAO.get(acao_key, {})
        cfg  = carregar_config_pontuacao()
        pts_atual = cfg.get("acoes", {}).get(acao_key, info.get("pontos", 0))

        components = [
            disnake.ui.TextInput(
                label=f"Pontos para: {info.get('label', acao_key)}",
                custom_id="pontos",
                value=str(pts_atual),
                placeholder="Número de pontos (pode ser negativo)",
                max_length=6,
                required=True,
            ),
        ]
        super().__init__(
            title="Editar Pontuação da Ação",
            components=components,
            custom_id=f"StaffModal_EditarAcao:{acao_key}",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .staff_manager import painel_config_pontuacao_components
        from functions.message import message as msg_helper, embed_message
        from .helpers import get_mode

        try:
            pontos = int(inter.text_values["pontos"].strip())
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Valor inválido.", ephemeral=True
            )
            return

        cfg = carregar_config_pontuacao()
        cfg.setdefault("acoes", {})[self._acao] = pontos
        salvar_config_pontuacao(cfg)

        mode = get_mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await msg_helper.wait(inter, send=False)

        await inter.edit_original_message(
            components=painel_config_pontuacao_components()
        )


class ConfigMultiplicadoresModal(disnake.ui.Modal):
    def __init__(self):
        cfg  = carregar_config_pontuacao()
        mult = cfg.get("multiplicadores", {})
        # Formata como: cargo_id=1.5\ncargo_id=2.0
        valor_atual = "\n".join(f"{k}={v}" for k, v in mult.items())
        components = [
            disnake.ui.TextInput(
                label="Multiplicadores por Cargo",
                custom_id="multiplicadores",
                value=valor_atual,
                placeholder="cargo_id=1.5\ncargo_id=2.0\n(um por linha, ID=multiplicador)",
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
                required=False,
            ),
        ]
        super().__init__(
            title="Multiplicadores de Cargo",
            components=components,
            custom_id="StaffModal_ConfigMultiplicadores",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        from .staff_manager import painel_config_pontuacao_components
        from functions.message import message as msg_helper, embed_message
        from .helpers import get_mode

        raw = inter.text_values.get("multiplicadores", "").strip()
        mult = {}
        erros = []
        for linha in raw.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            try:
                k, v = linha.split("=", 1)
                mult[k.strip()] = float(v.strip())
            except Exception:
                erros.append(linha)

        cfg = carregar_config_pontuacao()
        cfg["multiplicadores"] = mult
        salvar_config_pontuacao(cfg)

        msg_extra = f"\n⚠️ Linhas inválidas ignoradas: `{', '.join(erros)}`" if erros else ""

        mode = get_mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await msg_helper.wait(inter, send=False)

        await inter.edit_original_message(
            components=painel_config_pontuacao_components()
        )
        if msg_extra:
            await inter.followup.send(
                f"{emoji.warn} Multiplicadores salvos com avisos:{msg_extra}", ephemeral=True
            )