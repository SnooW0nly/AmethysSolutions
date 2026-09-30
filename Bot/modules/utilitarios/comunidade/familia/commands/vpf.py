"""
modules/utilitarios/comunidade/familia/commands/vpf.py

Comandos de prefixo do dono/representante da família:
  vpf         — painel de gerenciamento (só dono)
  addvpf      — adicionar membro (dono ou representante)
  rmvpf       — remover membro  (dono ou representante)

Todos os botões/modais do painel VPF também estão aqui.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message

from .. import helpers
from ..helpers import (
    accent, color, _mode, _primary_hex,
    load_json, save_json, FAMILIAS_JSON,
    MAX_REPRESENTANTES,
)


# ══════════════════════════════════════════════════════════════════════════════
# BUILDERS DO PAINEL VPF
# ══════════════════════════════════════════════════════════════════════════════

def _build_vpf_panel(fid: str, fdata: dict) -> list:
    ph   = _primary_hex()
    nome = fdata["nome"]
    reps = fdata.get("representantes", [])
    mbrs = fdata.get("membros", [])
    tempo = helpers.get_familia_tempo_efetivo(fid, fdata)

    resumo = (
        f"{emoji.group} **Membros:** `{len(mbrs)}`\n"
        f"{emoji.role} **Representantes:** `{len(reps)}/{MAX_REPRESENTANTES}`\n"
        f"⏱️ **Tempo total:** {helpers.formatar_tempo(tempo)}"
    )

    cargo_id = fdata.get("cargo_id")
    voz_id   = fdata.get("canal_voz_id")

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.group} Família: {nome}\n"
                f"-# Minha Família"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(resumo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Criar Cargo", emoji=emoji.role,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Familia_VPF_CriarCargo",
                    disabled=bool(cargo_id),
                ),
                disnake.ui.Button(
                    label="Criar Call", emoji=emoji.commands,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Familia_VPF_CriarCall",
                    disabled=bool(voz_id),
                ),
                disnake.ui.Button(
                    label="Editar Família", emoji=emoji.edit,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Familia_VPF_EditarFamilia",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Membros", emoji=emoji.group,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Familia_VPF_GerenciarMembros",
                ),
                disnake.ui.Button(
                    label="Representantes", emoji=emoji.shield,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Familia_VPF_GerenciarReps",
                ),
            ),
            **accent(ph),
        ),
    ]


def _build_vpf_editar(fid: str) -> list:
    ph = _primary_hex()
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.edit} Editar Família\n"
                "-# Minha Família > **Editar**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Edite as informações da sua família."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Nome", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Familia_VPF_EditNome:{fid}"),
                disnake.ui.Button(label="Editar Cor", emoji=emoji.colors,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Familia_VPF_EditCor:{fid}"),
                disnake.ui.Button(label="Editar Emoji", emoji=emoji.sparkles,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Familia_VPF_EditEmoji:{fid}"),
                disnake.ui.Button(label="Limite de Usuários", emoji=emoji.group,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Familia_VPF_EditLimite:{fid}"),
            ),
            **accent(ph),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id="Familia_VPF_VoltarPainel"),
        ),
    ]


def _build_vpf_membros(fid: str, fdata: dict) -> list:
    ph      = _primary_hex()
    membros = fdata.get("membros", [])
    dono_id = fdata.get("dono_id")

    if membros:
        lista = "\n".join(
            f"{'👑' if uid == dono_id else '👤'} <@{uid}>"
            for uid in membros[:20]
        )
        if len(membros) > 20:
            lista += f"\n-# ... e mais {len(membros) - 20}"
    else:
        lista = "_Nenhum membro._"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.group} Membros da Família\n"
                f"-# Total: `{len(membros)}`"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(lista),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Membro", emoji=emoji.plus,
                                  style=disnake.ButtonStyle.green,
                                  custom_id=f"Familia_VPF_AddMembro:{fid}"),
                disnake.ui.Button(label="Remover Membro", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id=f"Familia_VPF_RmMembro:{fid}",
                                  disabled=len(membros) <= 1),
            ),
            **accent(ph),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id="Familia_VPF_VoltarPainel"),
        ),
    ]


def _build_vpf_reps(fid: str, fdata: dict) -> list:
    ph   = _primary_hex()
    reps = fdata.get("representantes", [])

    if reps:
        lista = "\n".join(f"⭐ <@{uid}>" for uid in reps)
    else:
        lista = "_Nenhum representante._"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.shield} Representantes\n"
                f"-# `{len(reps)}/{MAX_REPRESENTANTES}` slots usados"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(lista),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Rep", emoji=emoji.plus,
                                  style=disnake.ButtonStyle.green,
                                  custom_id=f"Familia_VPF_AddRep:{fid}",
                                  disabled=len(reps) >= MAX_REPRESENTANTES),
                disnake.ui.Button(label="Remover Rep", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id=f"Familia_VPF_RmRep:{fid}",
                                  disabled=not bool(reps)),
            ),
            **accent(ph),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id="Familia_VPF_VoltarPainel"),
        ),
    ]


def _build_rm_membro_select(fid: str, fdata: dict) -> list:
    ph      = _primary_hex()
    dono_id = fdata.get("dono_id")
    membros = [uid for uid in fdata.get("membros", []) if uid != dono_id]
    if not membros:
        return []
    options = [
        disnake.SelectOption(label=f"ID: {uid}", value=str(uid))
        for uid in membros[:25]
    ]
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Remover Membro\nSelecione o membro a remover."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione o membro...",
                    custom_id=f"Familia_VPF_ConfirmarRm:{fid}",
                    options=options,
                )
            ),
            **accent(ph),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"Familia_VPF_VoltarMembros:{fid}"),
        ),
    ]


def _build_rm_rep_select(fid: str, fdata: dict) -> list:
    ph   = _primary_hex()
    reps = fdata.get("representantes", [])
    if not reps:
        return []
    options = [
        disnake.SelectOption(label=f"ID: {uid}", value=str(uid))
        for uid in reps[:25]
    ]
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Remover Representante\nSelecione o representante a remover."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione o representante...",
                    custom_id=f"Familia_VPF_ConfirmarRmRep:{fid}",
                    options=options,
                )
            ),
            **accent(ph),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"Familia_VPF_VoltarReps:{fid}"),
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# MODAIS VPF
# ══════════════════════════════════════════════════════════════════════════════

class VPFEditNomeModal(disnake.ui.Modal):
    def __init__(self, fid: str, fdata: dict):
        self.fid = fid
        super().__init__(
            title="Editar Nome da Família",
            custom_id=f"Familia_VPF_EditNomeModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="Novo nome",
                    custom_id="nome",
                    style=disnake.TextInputStyle.short,
                    required=True, max_length=32,
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
        fdata     = helpers.get_familia(self.fid)
        if not fdata:
            return
        guild      = inter.guild
        nome_antigo = fdata["nome"]

        for channel_key, name_func in [
            ("canal_voz_id",  lambda n: f"🏠 {n}"),
            ("canal_texto_id", lambda n: f"chat-{n.lower().replace(' ', '-')}"),
        ]:
            ch_id = fdata.get(channel_key)
            if ch_id:
                ch = guild.get_channel(int(ch_id))
                if ch:
                    try:
                        await ch.edit(name=name_func(novo_nome))
                    except Exception:
                        pass

        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = guild.get_role(int(cargo_id))
            if role:
                try:
                    await role.edit(name=novo_nome)
                except Exception:
                    pass

        familias = load_json(FAMILIAS_JSON)
        familias[self.fid]["nome"] = novo_nome
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            inter.bot, "Nome de Família Editado",
            f"**Anterior:** {nome_antigo}\n**Novo:** {novo_nome}\n"
            f"**Dono:** <@{fdata.get('dono_id')}>",
        )

        cog = inter.bot.get_cog("VPFCommand")
        if cog:
            fdata_updated = helpers.get_familia(self.fid)
            await inter.edit_original_message(
                components=_build_vpf_editar(self.fid)
            )


class VPFEditCorModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        super().__init__(
            title="Editar Cor do Cargo",
            custom_id=f"Familia_VPF_EditCorModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="Cor em HEX",
                    custom_id="cor",
                    style=disnake.TextInputStyle.short,
                    required=True, max_length=7,
                    placeholder="Ex: #FF5733",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        raw = inter.text_values["cor"].strip().lstrip("#")
        try:
            if len(raw) not in (3, 6):
                raise ValueError
            int(raw, 16)
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} Cor inválida.", ephemeral=True)
            return

        fdata = helpers.get_familia(self.fid)
        if not fdata:
            return
        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = inter.guild.get_role(int(cargo_id))
            if role:
                try:
                    await role.edit(colour=disnake.Colour(int(raw, 16)))
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro: {e}", ephemeral=True)
                    return

        await inter.followup.send(f"{emoji.correct} Cor atualizada!", ephemeral=True)
        await inter.edit_original_message(components=_build_vpf_editar(self.fid))


class VPFEditEmojiModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        super().__init__(
            title="Editar Emoji do Cargo",
            custom_id=f"Familia_VPF_EditEmojiModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="Emoji",
                    custom_id="emoji_val",
                    style=disnake.TextInputStyle.short,
                    required=True, max_length=64,
                    placeholder="Ex: 🏠 ou <:custom:123456>",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        emoji_val = inter.text_values["emoji_val"].strip()
        fdata     = helpers.get_familia(self.fid)
        if not fdata:
            return
        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = inter.guild.get_role(int(cargo_id))
            if role:
                try:
                    em = disnake.PartialEmoji.from_str(emoji_val)
                    await role.edit(unicode_emoji=str(em) if em.is_unicode_emoji() else None)
                except Exception as e:
                    await inter.followup.send(
                        f"{emoji.warn} Emoji não aplicado (servidor pode não ter boost suficiente): {e}",
                        ephemeral=True,
                    )
                    await inter.edit_original_message(components=_build_vpf_editar(self.fid))
                    return

        await inter.followup.send(f"{emoji.correct} Emoji atualizado!", ephemeral=True)
        await inter.edit_original_message(components=_build_vpf_editar(self.fid))


class VPFEditLimiteModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        super().__init__(
            title="Limite de Usuários na Call",
            custom_id=f"Familia_VPF_EditLimiteModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="Limite (0 = sem limite)",
                    custom_id="limite",
                    style=disnake.TextInputStyle.short,
                    required=True, max_length=3,
                    placeholder="Ex: 10 (0 para sem limite)",
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
            limite = max(0, int(inter.text_values["limite"].strip()))
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} Valor inválido.", ephemeral=True)
            return

        fdata = helpers.get_familia(self.fid)
        if not fdata:
            return
        voz_id = fdata.get("canal_voz_id")
        if voz_id:
            ch = inter.guild.get_channel(int(voz_id))
            if ch and isinstance(ch, disnake.VoiceChannel):
                try:
                    await ch.edit(user_limit=limite)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro: {e}", ephemeral=True)
                    return

        await inter.followup.send(
            f"{emoji.correct} Limite atualizado para `{'sem limite' if limite == 0 else limite}`!",
            ephemeral=True,
        )
        await inter.edit_original_message(components=_build_vpf_editar(self.fid))


class VPFAddMembroModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        super().__init__(
            title="Adicionar Membro",
            custom_id=f"Familia_VPF_AddMembroModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="ID do membro",
                    custom_id="membro_id",
                    style=disnake.TextInputStyle.short,
                    required=True, max_length=20,
                    placeholder="ID numérico do membro",
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
            uid = int(inter.text_values["membro_id"].strip())
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} ID inválido.", ephemeral=True)
            return

        fdata = helpers.get_familia(self.fid)
        if not fdata:
            return

        if uid in fdata.get("membros", []):
            await inter.followup.send(f"{emoji.warn} Este membro já está na família.", ephemeral=True)
            await inter.edit_original_message(components=_build_vpf_membros(self.fid, fdata))
            return

        _, outra = helpers.get_familia_by_membro(uid)
        if outra:
            await inter.followup.send(
                f"{emoji.wrong} Este membro já pertence à família **{outra['nome']}**.", ephemeral=True
            )
            return

        guild  = inter.guild
        member = guild.get_member(uid)
        if not member:
            try:
                member = await guild.fetch_member(uid)
            except Exception:
                pass
        if not member:
            await inter.followup.send(f"{emoji.wrong} Membro não encontrado.", ephemeral=True)
            return

        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = guild.get_role(int(cargo_id))
            if role:
                try:
                    await member.add_roles(role, reason=f"Adicionado à família {fdata['nome']}")
                except Exception:
                    pass

        familias = load_json(FAMILIAS_JSON)
        familias[self.fid].setdefault("membros", []).append(uid)
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            inter.bot, "Membro Adicionado à Família",
            f"**Família:** {fdata['nome']}\n**Membro:** {member.mention} (`{member}`)",
        )
        await inter.followup.send(f"{emoji.correct} {member.mention} adicionado!", ephemeral=True)
        fdata_upd = helpers.get_familia(self.fid)
        await inter.edit_original_message(components=_build_vpf_membros(self.fid, fdata_upd))


class VPFAddRepModal(disnake.ui.Modal):
    def __init__(self, fid: str):
        self.fid = fid
        super().__init__(
            title="Adicionar Representante",
            custom_id=f"Familia_VPF_AddRepModal:{fid}",
            components=[
                disnake.ui.TextInput(
                    label="ID do representante",
                    custom_id="rep_id",
                    style=disnake.TextInputStyle.short,
                    required=True, max_length=20,
                    placeholder="Deve ser membro da família",
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
            uid = int(inter.text_values["rep_id"].strip())
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} ID inválido.", ephemeral=True)
            return

        fdata = helpers.get_familia(self.fid)
        if not fdata:
            return

        if uid not in fdata.get("membros", []):
            await inter.followup.send(
                f"{emoji.wrong} Este usuário não é membro da família.", ephemeral=True
            )
            return

        if uid in fdata.get("representantes", []):
            await inter.followup.send(f"{emoji.warn} Já é representante.", ephemeral=True)
            return

        if uid == fdata.get("dono_id"):
            await inter.followup.send(f"{emoji.wrong} O dono não pode ser representante.", ephemeral=True)
            return

        if len(fdata.get("representantes", [])) >= MAX_REPRESENTANTES:
            await inter.followup.send(
                f"{emoji.wrong} Limite de {MAX_REPRESENTANTES} representantes atingido.", ephemeral=True
            )
            return

        familias = load_json(FAMILIAS_JSON)
        familias[self.fid].setdefault("representantes", []).append(uid)
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            inter.bot, "Representante Adicionado",
            f"**Família:** {fdata['nome']}\n**Representante:** <@{uid}>",
        )
        await inter.followup.send(f"{emoji.correct} Representante adicionado!", ephemeral=True)
        fdata_upd = helpers.get_familia(self.fid)
        await inter.edit_original_message(components=_build_vpf_reps(self.fid, fdata_upd))


# ══════════════════════════════════════════════════════════════════════════════
# COG
# ══════════════════════════════════════════════════════════════════════════════

class VPFCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Comandos de prefixo ───────────────────────────────────────────────────

    @commands.command(name="vpf")
    async def cmd_vpf(self, ctx: commands.Context):
        """Painel de gerenciamento da família (apenas dono)."""
        fid, fdata = helpers.get_familia_by_dono(ctx.author.id)
        if not fdata:
            await ctx.reply(
                f"{emoji.wrong} Você não é dono de nenhuma família.",
                delete_after=8,
            )
            return
        comps = _build_vpf_panel(fid, fdata)
        await ctx.send(
            components=comps,
            flags=disnake.MessageFlags(is_components_v2=True),
            ephemeral=True,
        )

    @commands.command(name="addvpf")
    async def cmd_addvpf(self, ctx: commands.Context, membro: disnake.Member = None):
        """Adicionar membro à família (dono ou representante)."""
        fid, fdata = helpers.get_familia_by_membro(ctx.author.id)
        if not fdata:
            await ctx.reply(
                f"{emoji.wrong} Você não pertence a nenhuma família.",
                delete_after=8,
            )
            return

        if not helpers.pode_gerenciar(ctx.author.id, fdata):
            await ctx.reply(
                f"{emoji.wrong} Apenas o dono ou representantes podem adicionar membros.",
                delete_after=8,
            )
            return

        if membro is None:
            ref = ctx.message.reference
            if ref and ref.resolved and isinstance(ref.resolved, disnake.Message):
                author = ref.resolved.author
                membro = author if isinstance(author, disnake.Member) else None
            if membro is None:
                await ctx.reply(
                    f"{emoji.wrong} Mencione um membro ou responda à mensagem dele.",
                    delete_after=10,
                )
                return

        if membro.bot:
            await ctx.reply(f"{emoji.wrong} Não é possível adicionar um bot.", delete_after=8)
            return

        if membro.id in fdata.get("membros", []):
            await ctx.reply(f"{emoji.warn} {membro.mention} já é membro da família.", delete_after=8)
            return

        _, outra = helpers.get_familia_by_membro(membro.id)
        if outra:
            await ctx.reply(
                f"{emoji.wrong} {membro.mention} já pertence à família **{outra['nome']}**.",
                delete_after=8,
            )
            return

        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = ctx.guild.get_role(int(cargo_id))
            if role:
                try:
                    await membro.add_roles(role, reason=f"Adicionado à família {fdata['nome']}")
                except Exception:
                    pass

        familias = load_json(FAMILIAS_JSON)
        familias[fid].setdefault("membros", []).append(membro.id)
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            ctx.bot, "Membro Adicionado à Família",
            f"**Família:** {fdata['nome']}\n"
            f"**Membro:** {membro.mention} (`{membro}`)\n"
            f"**Adicionado por:** {ctx.author.mention}",
        )
        await ctx.reply(f"{emoji.correct} {membro.mention} adicionado à família **{fdata['nome']}**!")

    @commands.command(name="rmvpf")
    async def cmd_rmvpf(self, ctx: commands.Context, membro: disnake.Member = None):
        """Remover membro da família (dono ou representante)."""
        fid, fdata = helpers.get_familia_by_membro(ctx.author.id)
        if not fdata:
            await ctx.reply(
                f"{emoji.wrong} Você não pertence a nenhuma família.",
                delete_after=8,
            )
            return

        if not helpers.pode_gerenciar(ctx.author.id, fdata):
            await ctx.reply(
                f"{emoji.wrong} Apenas o dono ou representantes podem remover membros.",
                delete_after=8,
            )
            return

        if membro is None:
            ref = ctx.message.reference
            if ref and ref.resolved and isinstance(ref.resolved, disnake.Message):
                author = ref.resolved.author
                membro = author if isinstance(author, disnake.Member) else None
            if membro is None:
                await ctx.reply(
                    f"{emoji.wrong} Mencione um membro ou responda à mensagem dele.",
                    delete_after=10,
                )
                return

        if membro.id not in fdata.get("membros", []):
            await ctx.reply(f"{emoji.wrong} {membro.mention} não é membro desta família.", delete_after=8)
            return

        if membro.id == fdata.get("dono_id"):
            await ctx.reply(f"{emoji.wrong} Não é possível remover o dono da família.", delete_after=8)
            return

        cargo_id = fdata.get("cargo_id")
        if cargo_id:
            role = ctx.guild.get_role(int(cargo_id))
            if role and role in membro.roles:
                try:
                    await membro.remove_roles(role, reason=f"Removido da família {fdata['nome']}")
                except Exception:
                    pass

        familias = load_json(FAMILIAS_JSON)
        membros  = familias[fid].get("membros", [])
        if membro.id in membros:
            membros.remove(membro.id)
        reps = familias[fid].get("representantes", [])
        if membro.id in reps:
            reps.remove(membro.id)
        familias[fid]["membros"]       = membros
        familias[fid]["representantes"] = reps
        save_json(FAMILIAS_JSON, familias)

        await helpers.enviar_log(
            ctx.bot, "Membro Removido da Família",
            f"**Família:** {fdata['nome']}\n"
            f"**Membro:** {membro.mention} (`{membro}`)\n"
            f"**Removido por:** {ctx.author.mention}",
        )
        await ctx.reply(f"{emoji.correct} {membro.mention} removido da família **{fdata['nome']}**!")

    # ── Button listener VPF ───────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _vpf_button(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Familia_VPF_"):
            return

        # Modais — sem wait
        if cid.startswith("Familia_VPF_EditNome:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid) or {}
            await inter.response.send_modal(VPFEditNomeModal(fid, fdata))
            return
        if cid.startswith("Familia_VPF_EditCor:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(VPFEditCorModal(fid))
            return
        if cid.startswith("Familia_VPF_EditEmoji:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(VPFEditEmojiModal(fid))
            return
        if cid.startswith("Familia_VPF_EditLimite:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(VPFEditLimiteModal(fid))
            return
        if cid.startswith("Familia_VPF_AddMembro:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(VPFAddMembroModal(fid))
            return
        if cid.startswith("Familia_VPF_AddRep:"):
            fid = cid.split(":", 1)[1]
            await inter.response.send_modal(VPFAddRepModal(fid))
            return

        # Com wait
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        # Voltar ao painel principal VPF
        if cid == "Familia_VPF_VoltarPainel":
            fid, fdata = helpers.get_familia_by_dono(inter.author.id)
            if fdata:
                await inter.edit_original_message(components=_build_vpf_panel(fid, fdata))
            return

        if cid == "Familia_VPF_EditarFamilia":
            fid, fdata = helpers.get_familia_by_dono(inter.author.id)
            if fdata:
                await inter.edit_original_message(components=_build_vpf_editar(fid))
            return

        if cid == "Familia_VPF_GerenciarMembros":
            fid, fdata = helpers.get_familia_by_dono(inter.author.id)
            if fdata:
                await inter.edit_original_message(components=_build_vpf_membros(fid, fdata))
            return

        if cid == "Familia_VPF_GerenciarReps":
            fid, fdata = helpers.get_familia_by_dono(inter.author.id)
            if fdata:
                await inter.edit_original_message(components=_build_vpf_reps(fid, fdata))
            return

        if cid.startswith("Familia_VPF_VoltarMembros:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid)
            if fdata:
                await inter.edit_original_message(components=_build_vpf_membros(fid, fdata))
            return

        if cid.startswith("Familia_VPF_VoltarReps:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid)
            if fdata:
                await inter.edit_original_message(components=_build_vpf_reps(fid, fdata))
            return

        if cid.startswith("Familia_VPF_RmMembro:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid)
            if fdata:
                comps = _build_rm_membro_select(fid, fdata)
                if comps:
                    await inter.edit_original_message(components=comps)
            return

        if cid.startswith("Familia_VPF_RmRep:"):
            fid   = cid.split(":", 1)[1]
            fdata = helpers.get_familia(fid)
            if fdata:
                comps = _build_rm_rep_select(fid, fdata)
                if comps:
                    await inter.edit_original_message(components=comps)
            return

        # ── Criar Cargo (se foi deletado) ─────────────────────────────────────
        if cid == "Familia_VPF_CriarCargo":
            fid, fdata = helpers.get_familia_by_dono(inter.author.id)
            if not fdata:
                return
            cargo_id = fdata.get("cargo_id")
            if cargo_id and inter.guild.get_role(int(cargo_id)):
                await inter.followup.send("O cargo já existe.", ephemeral=True)
                return

            separador_id = fdata.get("cargo_separador_id")
            separador    = inter.guild.get_role(int(separador_id)) if separador_id else None
            try:
                new_role = await inter.guild.create_role(
                    name=fdata["nome"], reason=f"Recriação de cargo da família {fdata['nome']}"
                )
                if separador:
                    try:
                        await inter.guild.edit_role_positions({new_role: max(1, separador.position - 1)})
                    except Exception:
                        pass
                for uid in fdata.get("membros", []):
                    m = inter.guild.get_member(uid)
                    if m:
                        try:
                            await m.add_roles(new_role)
                        except Exception:
                            pass
                familias = load_json(FAMILIAS_JSON)
                familias[fid]["cargo_id"] = new_role.id
                save_json(FAMILIAS_JSON, familias)
                await inter.followup.send(f"{emoji.correct} Cargo {new_role.mention} criado!", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro: {e}", ephemeral=True)
                return

            fdata_upd = helpers.get_familia(fid)
            await inter.edit_original_message(components=_build_vpf_panel(fid, fdata_upd))
            return

        # ── Criar Call (se foi deletada) ──────────────────────────────────────
        if cid == "Familia_VPF_CriarCall":
            fid, fdata = helpers.get_familia_by_dono(inter.author.id)
            if not fdata:
                return
            voz_id = fdata.get("canal_voz_id")
            if voz_id and inter.guild.get_channel(int(voz_id)):
                await inter.followup.send("A call já existe.", ephemeral=True)
                return

            cat_id = fdata.get("categoria_id")
            cat    = inter.guild.get_channel(int(cat_id)) if cat_id else None
            if not isinstance(cat, disnake.CategoryChannel):
                await inter.followup.send(f"{emoji.wrong} Categoria não encontrada.", ephemeral=True)
                return

            cargo_id = fdata.get("cargo_id")
            role     = inter.guild.get_role(int(cargo_id)) if cargo_id else None
            overwrites = {
                inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False, connect=False),
                inter.guild.me:           disnake.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True),
            }
            if role:
                overwrites[role] = disnake.PermissionOverwrite(view_channel=True, connect=True, speak=True)

            try:
                new_voz = await inter.guild.create_voice_channel(
                    name=f"🏠 {fdata['nome']}", category=cat,
                    overwrites=overwrites, reason=f"Recriação da call da família {fdata['nome']}",
                )
                familias = load_json(FAMILIAS_JSON)
                familias[fid]["canal_voz_id"] = new_voz.id
                save_json(FAMILIAS_JSON, familias)
                await inter.followup.send(f"{emoji.correct} Call {new_voz.mention} criada!", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro: {e}", ephemeral=True)
                return

            fdata_upd = helpers.get_familia(fid)
            await inter.edit_original_message(components=_build_vpf_panel(fid, fdata_upd))
            return

    # ── Dropdown listener VPF ─────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _vpf_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Familia_VPF_"):
            return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid.startswith("Familia_VPF_ConfirmarRm:"):
            fid   = cid.split(":", 1)[1]
            uid   = int(inter.values[0])
            fdata = helpers.get_familia(fid)
            if not fdata:
                return
            if uid == fdata.get("dono_id"):
                await inter.followup.send(f"{emoji.wrong} Não é possível remover o dono.", ephemeral=True)
                return

            guild    = inter.guild
            cargo_id = fdata.get("cargo_id")
            if cargo_id:
                role = guild.get_role(int(cargo_id))
                member = guild.get_member(uid)
                if role and member and role in member.roles:
                    try:
                        await member.remove_roles(role)
                    except Exception:
                        pass

            familias = load_json(FAMILIAS_JSON)
            membros  = familias[fid].get("membros", [])
            if uid in membros:
                membros.remove(uid)
            reps = familias[fid].get("representantes", [])
            if uid in reps:
                reps.remove(uid)
            familias[fid]["membros"]        = membros
            familias[fid]["representantes"] = reps
            save_json(FAMILIAS_JSON, familias)

            await helpers.enviar_log(
                inter.bot, "Membro Removido da Família",
                f"**Família:** {fdata['nome']}\n**Membro:** <@{uid}>\n"
                f"**Removido por:** {inter.author.mention}",
            )
            await inter.followup.send(f"{emoji.correct} Membro removido!", ephemeral=True)
            fdata_upd = helpers.get_familia(fid)
            await inter.edit_original_message(components=_build_vpf_membros(fid, fdata_upd))
            return

        if cid.startswith("Familia_VPF_ConfirmarRmRep:"):
            fid   = cid.split(":", 1)[1]
            uid   = int(inter.values[0])
            fdata = helpers.get_familia(fid)
            if not fdata:
                return

            familias = load_json(FAMILIAS_JSON)
            reps     = familias[fid].get("representantes", [])
            if uid in reps:
                reps.remove(uid)
            familias[fid]["representantes"] = reps
            save_json(FAMILIAS_JSON, familias)

            await helpers.enviar_log(
                inter.bot, "Representante Removido",
                f"**Família:** {fdata['nome']}\n**Representante:** <@{uid}>",
            )
            await inter.followup.send(f"{emoji.correct} Representante removido!", ephemeral=True)
            fdata_upd = helpers.get_familia(fid)
            await inter.edit_original_message(components=_build_vpf_reps(fid, fdata_upd))
            return


def setup(bot: commands.Bot):
    bot.add_cog(VPFCommand(bot))