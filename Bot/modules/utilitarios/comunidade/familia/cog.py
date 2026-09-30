"""
modules/utilitarios/comunidade/familia/cog.py

Sistema de Família — Painel administrativo + todos os listeners admin.
"""
from __future__ import annotations

from datetime import datetime

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from . import helpers
from .helpers import (
    accent, color, _mode, _primary_hex,
    load_json, save_json, FAMILIAS_JSON,
)


# ══════════════════════════════════════════════════════════════════════════════
# MODAIS
# ══════════════════════════════════════════════════════════════════════════════

class CriarFamiliaModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Família",
            custom_id="Familia_CriarModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome da família",
                    custom_id="nome",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=32,
                    placeholder="Ex: Família Silva",
                ),
                disnake.ui.TextInput(
                    label="ID do dono",
                    custom_id="dono_id",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=20,
                    placeholder="ID numérico do membro",
                ),
                disnake.ui.Label(
                    text="Categoria dos canais",
                    component=disnake.ui.ChannelSelect(
                        placeholder="Selecione a categoria...",
                        custom_id="categoria",
                        channel_types=[disnake.ChannelType.category],
                        min_values=1, max_values=1,
                    ),
                    description="Onde a call (e chat) da família serão criados.",
                ),
                disnake.ui.Label(
                    text="Cargo separador",
                    component=disnake.ui.RoleSelect(
                        placeholder="Selecione o cargo separador...",
                        custom_id="cargo_separador",
                        min_values=1, max_values=1,
                    ),
                    description="O cargo da família ficará abaixo deste cargo.",
                ),
                disnake.ui.TextInput(
                    label="Criar chat de texto? (sim / não)",
                    custom_id="chat_texto",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=4,
                    placeholder="sim ou não",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        nome      = inter.text_values["nome"].strip()
        dono_raw  = inter.text_values["dono_id"].strip()
        chat_raw  = inter.text_values["chat_texto"].strip().lower()
        has_chat  = chat_raw in ("sim", "s", "yes", "y", "1")

        # Resolved selects
        def _resolve(val):
            if isinstance(val, (list, tuple)):
                return val[0] if val else None
            return val

        categoria = _resolve(inter.resolved_values.get("categoria"))
        separador = _resolve(inter.resolved_values.get("cargo_separador"))

        if not categoria or not separador:
            await inter.followup.send(
                f"{emoji.wrong} Categoria ou cargo separador inválidos.", ephemeral=True
            )
            return

        try:
            dono_id = int(dono_raw)
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} ID do dono inválido.", ephemeral=True)
            return

        guild = inter.guild

        # Verificar dono
        try:
            dono_member = guild.get_member(dono_id) or await guild.fetch_member(dono_id)
        except Exception:
            dono_member = None
        if not dono_member:
            await inter.followup.send(
                f"{emoji.wrong} Membro não encontrado com o ID `{dono_id}`.", ephemeral=True
            )
            return

        # Verificar se já tem família
        _, familia_existente = helpers.get_familia_by_membro(dono_id)
        if familia_existente:
            await inter.followup.send(
                f"{emoji.wrong} Este membro já faz parte da família **{familia_existente['nome']}**.",
                ephemeral=True,
            )
            return

        categoria_ch = guild.get_channel(categoria.id if hasattr(categoria, "id") else int(categoria))
        if not isinstance(categoria_ch, disnake.CategoryChannel):
            await inter.followup.send(f"{emoji.wrong} Categoria inválida.", ephemeral=True)
            return

        separador_role = guild.get_role(separador.id if hasattr(separador, "id") else int(separador))
        if not separador_role:
            await inter.followup.send(f"{emoji.wrong} Cargo separador não encontrado.", ephemeral=True)
            return

        # ── Criar cargo ───────────────────────────────────────────────────────
        try:
            familia_role = await guild.create_role(
                name=nome,
                reason=f"Sistema de Família: criação de {nome}",
            )
            new_pos = max(1, separador_role.position - 1)
            try:
                await guild.edit_role_positions({familia_role: new_pos})
            except Exception:
                pass
        except Exception as e:
            await inter.followup.send(f"{emoji.wrong} Erro ao criar cargo: {e}", ephemeral=True)
            return

        # ── Criar canal de voz ────────────────────────────────────────────────
        overwrites_voz = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False, connect=False),
            familia_role:       disnake.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            guild.me:           disnake.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True),
        }
        try:
            canal_voz = await guild.create_voice_channel(
                name=f"🏠 {nome}",
                category=categoria_ch,
                overwrites=overwrites_voz,
                reason=f"Família: {nome}",
            )
        except Exception as e:
            try:
                await familia_role.delete()
            except Exception:
                pass
            await inter.followup.send(f"{emoji.wrong} Erro ao criar call: {e}", ephemeral=True)
            return

        # ── Criar chat de texto (opcional) ────────────────────────────────────
        canal_texto = None
        if has_chat:
            try:
                overwrites_txt = {
                    guild.default_role: disnake.PermissionOverwrite(view_channel=False),
                    familia_role:       disnake.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    ),
                    guild.me:           disnake.PermissionOverwrite(view_channel=True, manage_channels=True),
                }
                nome_canal = nome.lower().replace(" ", "-")
                canal_texto = await guild.create_text_channel(
                    name=f"chat-{nome_canal}",
                    category=categoria_ch,
                    overwrites=overwrites_txt,
                    reason=f"Família: {nome}",
                )
            except Exception:
                pass

        # ── Dar cargo ao dono ─────────────────────────────────────────────────
        try:
            await dono_member.add_roles(familia_role, reason=f"Dono da família {nome}")
        except Exception:
            pass

        # ── Salvar ────────────────────────────────────────────────────────────
        familia_id   = helpers.gerar_familia_id()
        familia_data = {
            "nome":              nome,
            "dono_id":           dono_id,
            "categoria_id":      categoria_ch.id,
            "cargo_separador_id": separador_role.id,
            "cargo_id":          familia_role.id,
            "canal_voz_id":      canal_voz.id,
            "canal_texto_id":    canal_texto.id if canal_texto else None,
            "membros":           [dono_id],
            "representantes":    [],
            "tempo_total_segundos": 0,
            "ultima_atividade":  datetime.now().isoformat(),
            "criada_em":         datetime.now().isoformat(),
            "has_texto":         has_chat,
        }
        helpers.save_familia(familia_id, familia_data)

        # ── Log ───────────────────────────────────────────────────────────────
        await helpers.enviar_log(
            inter.bot,
            "Família Criada",
            f"**Nome:** {nome}\n"
            f"**Dono:** {dono_member.mention} (`{dono_member}`)\n"
            f"**Cargo:** {familia_role.mention}\n"
            f"**Call:** {canal_voz.mention}\n"
            f"**Chat:** {canal_texto.mention if canal_texto else '`Não criado`'}",
        )

        await inter.followup.send(
            f"{emoji.correct} Família **{nome}** criada com sucesso!", ephemeral=True
        )
        cog: FamiliaCog | None = inter.bot.get_cog("FamiliaCog")
        if cog:
            await cog._render_painel(inter, mode)


class InativiModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        super().__init__(
            title="Tempo de Inatividade",
            custom_id="Familia_InativiModal",
            components=[
                disnake.ui.TextInput(
                    label="Dias de inatividade (0 = desativado)",
                    custom_id="dias",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=4,
                    placeholder="Ex: 30 (0 para desativar)",
                    value=str(config.get("inatividade_dias", 0)),
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        try:
            dias = max(0, int(inter.text_values["dias"].strip()))
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} Valor inválido.", ephemeral=True)
            return

        config = helpers.carregar_config()
        config["inatividade_dias"] = dias
        helpers.salvar_config(config)

        cog: FamiliaCog | None = inter.bot.get_cog("FamiliaCog")
        if cog:
            await cog._render_painel(inter, mode)


class TrocarDonoModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        super().__init__(
            title="Trocar Dono da Família",
            custom_id=f"Familia_TrocarDonoModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="ID do novo dono",
                    custom_id="novo_dono_id",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=20,
                    placeholder="ID numérico do novo dono",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        try:
            novo_id = int(inter.text_values["novo_dono_id"].strip())
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} ID inválido.", ephemeral=True)
            return

        fdata = helpers.get_familia(self.fid)
        if not fdata:
            await inter.followup.send(f"{emoji.wrong} Família não encontrada.", ephemeral=True)
            return

        if novo_id not in fdata.get("membros", []):
            await inter.followup.send(
                f"{emoji.wrong} O novo dono precisa ser membro da família.", ephemeral=True
            )
            return

        old_dono = fdata.get("dono_id")
        familias = load_json(FAMILIAS_JSON)
        familias[self.fid]["dono_id"] = novo_id
        # Remover de representantes se era rep
        reps = familias[self.fid].get("representantes", [])
        if novo_id in reps:
            reps.remove(novo_id)
        familias[self.fid]["representantes"] = reps
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            inter.bot,
            "Troca de Dono",
            f"**Família:** {fdata['nome']}\n"
            f"**Dono anterior:** <@{old_dono}>\n"
            f"**Novo dono:** <@{novo_id}>",
        )
        await inter.followup.send(f"{emoji.correct} Dono atualizado!", ephemeral=True)
        cog: FamiliaCog | None = inter.bot.get_cog("FamiliaCog")
        if cog:
            await cog._render_mgmt_familia(inter, self.fid, mode)


class EditarNomeFamiliaModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        fdata = helpers.get_familia(fid) or {}
        super().__init__(
            title="Editar Nome da Família",
            custom_id=f"Familia_EditNomeAdminModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="Novo nome",
                    custom_id="nome",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=32,
                    value=fdata.get("nome", ""),
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        novo_nome = inter.text_values["nome"].strip()
        if not novo_nome:
            await inter.followup.send(f"{emoji.wrong} Nome inválido.", ephemeral=True)
            return

        fdata = helpers.get_familia(self.fid)
        if not fdata:
            await inter.followup.send(f"{emoji.wrong} Família não encontrada.", ephemeral=True)
            return

        nome_antigo = fdata["nome"]
        guild       = inter.guild

        # Atualizar cargo
        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = guild.get_role(int(cargo_id))
            if role:
                try:
                    await role.edit(name=novo_nome, reason="Família: renomear")
                except Exception:
                    pass

        # Atualizar call
        voz_id = fdata.get("canal_voz_id")
        if voz_id:
            ch = guild.get_channel(int(voz_id))
            if ch:
                try:
                    await ch.edit(name=f"🏠 {novo_nome}", reason="Família: renomear")
                except Exception:
                    pass

        # Atualizar chat
        texto_id = fdata.get("canal_texto_id")
        if texto_id:
            ch = guild.get_channel(int(texto_id))
            if ch:
                try:
                    nome_canal = novo_nome.lower().replace(" ", "-")
                    await ch.edit(name=f"chat-{nome_canal}", reason="Família: renomear")
                except Exception:
                    pass

        familias = load_json(FAMILIAS_JSON)
        familias[self.fid]["nome"] = novo_nome
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            inter.bot,
            "Nome da Família Editado",
            f"**Anterior:** {nome_antigo}\n**Novo:** {novo_nome}",
        )
        await inter.followup.send(f"{emoji.correct} Nome atualizado para **{novo_nome}**!", ephemeral=True)
        cog: FamiliaCog | None = inter.bot.get_cog("FamiliaCog")
        if cog:
            await cog._render_mgmt_familia(inter, self.fid, mode)


# ══════════════════════════════════════════════════════════════════════════════
# BUILDERS DE PAINEL
# ══════════════════════════════════════════════════════════════════════════════

def _build_painel_components() -> list:
    config      = helpers.carregar_config()
    ph          = _primary_hex()
    familias    = helpers.get_all_familias()
    n_familias  = len(familias)
    logs_id     = config.get("canal_logs_id")
    rank_id     = config.get("canal_rank_id")
    inativ      = config.get("inatividade_dias", 0)

    logs_txt  = f"<#{logs_id}>"   if logs_id  else "`Não configurado`"
    rank_txt  = f"<#{rank_id}>"   if rank_id  else "`Não configurado`"
    inativ_txt = f"`{inativ} dias`" if inativ   else "`Desativado`"

    resumo = (
        f"{emoji.textc} **Logs:** {logs_txt}\n"
        f"{emoji.textc} **Canal de Rank:** {rank_txt}\n"
        f"{emoji.time} **Inatividade:** {inativ_txt}\n"
        f"{emoji.group} **Famílias ativas:** `{n_familias}`"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.group} Sistema de Família\n"
                "-# Painel > Comunidade > **Sistema de Família**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Gerencie as famílias do servidor."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(resumo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Criar Família", emoji=emoji.plus,
                    style=disnake.ButtonStyle.green,
                    custom_id="Familia_CriarFamilia",
                ),
                disnake.ui.Button(
                    label="Gerenciar Famílias", emoji=emoji.commands,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Familia_GerenciarFamilias",
                    disabled=not bool(familias),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Canal de Logs", emoji=emoji.textc,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Familia_CanalLogs",
                ),
                disnake.ui.Button(
                    label="Canal de Rank", emoji=emoji.textc,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Familia_CanalRank",
                ),
                disnake.ui.Button(
                    label="Inatividade", emoji=emoji.time,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Familia_Inatividade",
                ),
            ),
            **accent(ph),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", emoji=emoji.back,
                style=disnake.ButtonStyle.grey,
                custom_id="Comunidade_VoltarFeature",
            ),
        ),
    ]


def _build_painel_embed() -> tuple[disnake.Embed, list]:
    config     = helpers.carregar_config()
    familias   = helpers.get_all_familias()
    n_familias = len(familias)
    logs_id    = config.get("canal_logs_id")
    rank_id    = config.get("canal_rank_id")
    inativ     = config.get("inatividade_dias", 0)

    embed = disnake.Embed(title="Sistema de Família", description="Gerencie as famílias do servidor.")
    c = color()
    if c:
        embed.color = c
    embed.add_field(name="Configurações", inline=False, value=(
        f"{emoji.textc} **Logs:** {f'<#{logs_id}>' if logs_id else '`Não configurado`'}\n"
        f"{emoji.textc} **Canal de Rank:** {f'<#{rank_id}>' if rank_id else '`Não configurado`'}\n"
        f"{emoji.time} **Inatividade:** {f'`{inativ} dias`' if inativ else '`Desativado`'}\n"
        f"{emoji.group} **Famílias ativas:** `{n_familias}`"
    ))

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Família", emoji=emoji.plus,
                              style=disnake.ButtonStyle.green, custom_id="Familia_CriarFamilia"),
            disnake.ui.Button(label="Gerenciar Famílias", emoji=emoji.commands,
                              style=disnake.ButtonStyle.blurple, custom_id="Familia_GerenciarFamilias",
                              disabled=not bool(familias)),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Canal de Logs", emoji=emoji.textc,
                              style=disnake.ButtonStyle.grey, custom_id="Familia_CanalLogs"),
            disnake.ui.Button(label="Canal de Rank", emoji=emoji.textc,
                              style=disnake.ButtonStyle.grey, custom_id="Familia_CanalRank"),
            disnake.ui.Button(label="Inatividade", emoji=emoji.time,
                              style=disnake.ButtonStyle.grey, custom_id="Familia_Inatividade"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Comunidade_VoltarFeature"),
        ),
    ]
    return embed, components


def _build_select_familias_components(ph: str | None, mode: str) -> list:
    familias = helpers.get_all_familias()
    options  = [
        disnake.SelectOption(
            label=fdata["nome"][:100],
            value=fid,
            description=f"Membros: {len(fdata.get('membros', []))} | Dono: {fdata.get('dono_id', '?')}",
        )
        for fid, fdata in list(familias.items())[:25]
    ]
    select_row = disnake.ui.ActionRow(
        disnake.ui.StringSelect(
            placeholder="Selecione uma família...",
            custom_id="Familia_SelectGerenciar",
            options=options,
        )
    )
    voltar = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back,
                          style=disnake.ButtonStyle.grey, custom_id="Familia_VoltarPainel"),
    )
    if mode == "embed":
        return None, (
            disnake.Embed(
                title="Gerenciar Famílias",
                description="Selecione uma família para gerenciar.",
                color=color() or disnake.Colour.blurple(),
            ),
            [select_row, voltar],
        )
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.commands} Gerenciar Famílias\n"
                "-# Painel > Comunidade > Família > **Selecionar**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Selecione uma família para gerenciar."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            select_row,
            **accent(ph),
        ),
        voltar,
    ], None


def _build_mgmt_familia(fid: str, ph: str | None, mode: str) -> list | tuple:
    fdata = helpers.get_familia(fid)
    if not fdata:
        return []

    nome       = fdata["nome"]
    dono_id    = fdata.get("dono_id")
    cat_id     = fdata.get("categoria_id")
    cargo_id   = fdata.get("cargo_id")
    voz_id     = fdata.get("canal_voz_id")
    texto_id   = fdata.get("canal_texto_id")
    membros    = fdata.get("membros", [])
    tempo      = helpers.get_familia_tempo_efetivo(fid, fdata)

    cat_txt    = f"<#{cat_id}>"   if cat_id   else "`-`"
    cargo_txt  = f"<@&{cargo_id}>" if cargo_id  else "`Não criado`"
    voz_txt    = f"<#{voz_id}>"   if voz_id   else "`Não criado`"
    texto_txt  = f"<#{texto_id}>" if texto_id  else "`Não criado`"

    info = (
        f"{emoji.role} **Cargo:** {cargo_txt}\n"
        f"{emoji.textc} **Categoria:** {cat_txt}\n"
        f"{emoji.voice if hasattr(emoji, 'voice') else emoji.commands} **Call:** {voz_txt}\n"
        f"{emoji.textc} **Chat:** {texto_txt}\n"
        f"{emoji.group} **Membros:** `{len(membros)}`\n"
        f"⏱️ **Tempo total:** {helpers.formatar_tempo(tempo)}"
    )

    row1 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Trocar Dono", emoji=emoji.role,
                          style=disnake.ButtonStyle.blurple,
                          custom_id=f"Familia_Mgmt_TrocarDono:{fid}"),
        disnake.ui.Button(label="Editar Nome", emoji=emoji.edit,
                          style=disnake.ButtonStyle.blurple,
                          custom_id=f"Familia_Mgmt_EditarNome:{fid}"),
        disnake.ui.Button(label="Trocar Categoria", emoji=emoji.textc,
                          style=disnake.ButtonStyle.grey,
                          custom_id=f"Familia_Mgmt_TrocarCategoria:{fid}"),
    )
    row2 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Criar Chat", emoji=emoji.plus,
                          style=disnake.ButtonStyle.grey,
                          custom_id=f"Familia_Mgmt_CriarChat:{fid}",
                          disabled=bool(texto_id)),
        disnake.ui.Button(label="Deletar Família", emoji=emoji.delete,
                          style=disnake.ButtonStyle.red,
                          custom_id=f"Familia_Mgmt_Deletar:{fid}"),
    )
    voltar = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back,
                          style=disnake.ButtonStyle.grey,
                          custom_id="Familia_VoltarSelectFamilias"),
    )

    if mode == "embed":
        emb = disnake.Embed(
            title=f"Família: {nome}",
            description=f"**Dono:** <@{dono_id}>\n\n{info}",
            color=color() or disnake.Colour.blurple(),
        )
        return emb, [row1, row2, voltar]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.group} {nome}\n"
                f"-# Painel > Comunidade > Família > **Gerenciar**\n"
                f"Dono: <@{dono_id}>"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            row1, row2,
            **accent(ph),
        ),
        voltar,
    ]


# ══════════════════════════════════════════════════════════════════════════════
# COG
# ══════════════════════════════════════════════════════════════════════════════

class FamiliaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list:
        return _build_painel_components()

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        return _build_painel_embed()

    # ── Render helpers ────────────────────────────────────────────────────────

    async def _render_painel(self, inter, mode: str):
        if mode == "embed":
            emb, comps = _build_painel_embed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=_build_painel_components())

    async def _render_select_familias(self, inter, mode: str):
        ph = _primary_hex()
        if mode == "embed":
            _, (emb, comps) = _build_select_familias_components(ph, mode)
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            comps, _ = _build_select_familias_components(ph, mode)
            await inter.edit_original_message(components=comps)

    async def _render_mgmt_familia(self, inter, fid: str, mode: str):
        ph     = _primary_hex()
        result = _build_mgmt_familia(fid, ph, mode)
        if mode == "embed":
            emb, comps = result
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=result)

    async def _render_channel_select(self, inter, tipo: str, mode: str):
        ph = _primary_hex()
        cid_select = f"Familia_SelectLogs" if tipo == "logs" else "Familia_SelectRank"
        titulo = "Canal de Logs" if tipo == "logs" else "Canal de Rank"
        desc   = (
            "Selecione o canal onde os logs do sistema serão enviados."
            if tipo == "logs" else
            "Selecione o canal onde o ranking de famílias será publicado automaticamente."
        )
        select_row = disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder=f"Selecione o canal de {tipo}...",
                custom_id=cid_select,
                channel_types=[disnake.ChannelType.text],
                min_values=1, max_values=1,
            )
        )
        voltar = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Familia_VoltarPainel"),
        )
        if mode == "embed":
            emb = disnake.Embed(title=titulo, description=desc, color=color() or disnake.Colour.blurple())
            await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
        else:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.textc} {titulo}\n"
                        f"-# Painel > Comunidade > Família > **{titulo}**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(desc),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    select_row,
                    **accent(ph),
                ),
                voltar,
            ])

    # ── Button listener ───────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _familia_button(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Familia_"):
            return

        # Modais — sem wait
        if cid == "Familia_CriarFamilia":
            await inter.response.send_modal(CriarFamiliaModal())
            return
        if cid == "Familia_Inatividade":
            await inter.response.send_modal(InativiModal())
            return
        if cid.startswith("Familia_Mgmt_TrocarDono:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(TrocarDonoModal(fid))
            return
        if cid.startswith("Familia_Mgmt_EditarNome:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(EditarNomeFamiliaModal(fid))
            return

        # Com wait
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        ph = _primary_hex()

        if cid == "Familia_GerenciarFamilias":
            await self._render_select_familias(inter, mode)
            return

        if cid == "Familia_CanalLogs":
            await self._render_channel_select(inter, "logs", mode)
            return

        if cid == "Familia_CanalRank":
            await self._render_channel_select(inter, "rank", mode)
            return

        if cid == "Familia_VoltarPainel":
            await self._render_painel(inter, mode)
            return

        if cid == "Familia_VoltarSelectFamilias":
            await self._render_select_familias(inter, mode)
            return

        if cid.startswith("Familia_VoltarMgmt:"):
            fid = cid.split(":", 1)[1]
            await self._render_mgmt_familia(inter, fid, mode)
            return

        # ── Trocar Categoria ─────────────────────────────────────────────────
        if cid.startswith("Familia_Mgmt_TrocarCategoria:"):
            fid = cid.split(":", 1)[1]
            select_row = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione a nova categoria...",
                    custom_id=f"Familia_SelectCategoria:{fid}",
                    channel_types=[disnake.ChannelType.category],
                    min_values=1, max_values=1,
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Familia_VoltarMgmt:{fid}"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Trocar Categoria",
                                    description="Selecione a nova categoria para os canais da família.",
                                    color=color() or disnake.Colour.blurple())
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.textc} Trocar Categoria\n"
                            "Selecione a nova categoria para os canais da família."
                        ),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row, **accent(ph),
                    ),
                    voltar,
                ])
            return

        # ── Criar Chat ────────────────────────────────────────────────────────
        if cid.startswith("Familia_Mgmt_CriarChat:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid)
            if not fdata:
                await inter.followup.send(f"{emoji.wrong} Família não encontrada.", ephemeral=True)
                return
            if fdata.get("canal_texto_id"):
                await inter.followup.send("O chat já existe.", ephemeral=True)
                return

            guild    = inter.guild
            cargo_id = fdata.get("cargo_id")
            cat_id   = fdata.get("categoria_id")
            role     = guild.get_role(int(cargo_id)) if cargo_id else None
            cat      = guild.get_channel(int(cat_id)) if cat_id else None

            if not isinstance(cat, disnake.CategoryChannel):
                await inter.followup.send(f"{emoji.wrong} Categoria não encontrada.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: disnake.PermissionOverwrite(view_channel=False),
                guild.me:           disnake.PermissionOverwrite(view_channel=True, manage_channels=True),
            }
            if role:
                overwrites[role] = disnake.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            try:
                nome_canal = fdata["nome"].lower().replace(" ", "-")
                canal_txt  = await guild.create_text_channel(
                    name=f"chat-{nome_canal}", category=cat,
                    overwrites=overwrites, reason=f"Família: chat criado por admin",
                )
                familias = load_json(FAMILIAS_JSON)
                familias[fid]["canal_texto_id"] = canal_txt.id
                familias[fid]["has_texto"] = True
                save_json(FAMILIAS_JSON, familias)
                await inter.followup.send(
                    f"{emoji.correct} Chat {canal_txt.mention} criado!", ephemeral=True
                )
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro: {e}", ephemeral=True)
                return

            await self._render_mgmt_familia(inter, fid, mode)
            return

        # ── Deletar Família ───────────────────────────────────────────────────
        if cid.startswith("Familia_Mgmt_Deletar:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid)
            if not fdata:
                await inter.followup.send(f"{emoji.wrong} Família não encontrada.", ephemeral=True)
                return

            await _deletar_familia_completa(inter.bot, inter.guild, fid, fdata)
            await inter.followup.send(f"{emoji.correct} Família deletada.", ephemeral=True)

            familias = helpers.get_all_familias()
            if familias:
                await self._render_select_familias(inter, mode)
            else:
                await self._render_painel(inter, mode)
            return

    # ── Dropdown listener ─────────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _familia_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Familia_"):
            return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "Familia_SelectGerenciar":
            fid = inter.values[0]
            await self._render_mgmt_familia(inter, fid, mode)
            return

        if cid == "Familia_SelectLogs":
            config = helpers.carregar_config()
            config["canal_logs_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Familia_SelectRank":
            config = helpers.carregar_config()
            config["canal_rank_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid.startswith("Familia_SelectCategoria:"):
            fid      = cid.split(":", 1)[1]
            fdata    = helpers.get_familia(fid)
            if not fdata:
                return
            nova_cat_val = inter.values[0] if inter.values else None
            if not nova_cat_val:
                return

            guild   = inter.guild
            nova_cat = guild.get_channel(int(nova_cat_val))
            if not isinstance(nova_cat, disnake.CategoryChannel):
                await inter.followup.send(f"{emoji.wrong} Categoria inválida.", ephemeral=True)
                return

            # Mover canais
            voz_id   = fdata.get("canal_voz_id")
            texto_id = fdata.get("canal_texto_id")
            if voz_id:
                ch = guild.get_channel(int(voz_id))
                if ch:
                    try:
                        await ch.edit(category=nova_cat, reason="Família: trocar categoria")
                    except Exception:
                        pass
            if texto_id:
                ch = guild.get_channel(int(texto_id))
                if ch:
                    try:
                        await ch.edit(category=nova_cat, reason="Família: trocar categoria")
                    except Exception:
                        pass

            familias = load_json(FAMILIAS_JSON)
            familias[fid]["categoria_id"] = nova_cat.id
            save_json(FAMILIAS_JSON, familias)

            await inter.followup.send(
                f"{emoji.correct} Categoria atualizada para **{nova_cat.name}**!", ephemeral=True
            )
            await self._render_mgmt_familia(inter, fid, mode)
            return


# ── Helper: deletar família completa ──────────────────────────────────────────

async def _deletar_familia_completa(
    bot,
    guild: disnake.Guild,
    fid: str,
    fdata: dict,
    motivo: str = "Família deletada pelo administrador",
):
    """Deleta cargo, canais e remove do JSON. Envia log."""
    nome     = fdata.get("nome", "?")
    cargo_id = fdata.get("cargo_id")
    voz_id   = fdata.get("canal_voz_id")
    texto_id = fdata.get("canal_texto_id")

    if cargo_id:
        role = guild.get_role(int(cargo_id))
        if role:
            try:
                await role.delete(reason=motivo)
            except Exception:
                pass

    if voz_id:
        ch = guild.get_channel(int(voz_id))
        if ch:
            try:
                await ch.delete(reason=motivo)
            except Exception:
                pass

    if texto_id:
        ch = guild.get_channel(int(texto_id))
        if ch:
            try:
                await ch.delete(reason=motivo)
            except Exception:
                pass

    helpers.delete_familia(fid)

    await helpers.enviar_log(
        bot,
        "Família Deletada",
        f"**Nome:** {nome}\n**Motivo:** {motivo}",
        erro=True,
    )


def setup(bot: commands.Bot):
    bot.add_cog(FamiliaCog(bot))