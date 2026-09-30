from disnake.ext import commands
import disnake, os

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .helper import EconomyHelper
from .guard import EconomyGuard
from . import paineis as p

ECONOMY_COMMANDS = p.ECONOMY_COMMANDS
CMD_LABELS       = p.CMD_LABELS
CMD_EMOJIS       = p.CMD_EMOJIS
EVENT_TARGETS    = p.EVENT_TARGETS


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS GLOBAIS
# ─────────────────────────────────────────────────────────────────────────────

def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


async def _safe_defer(inter: disnake.MessageInteraction):
    """Defer seguro — não explode se a interaction já foi respondida."""
    if inter.response.is_done():
        return
    try:
        await inter.response.defer(with_message=False)
    except disnake.errors.HTTPException:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# COG PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._load_economy_commands()

    def _load_economy_commands(self):
        path = os.path.join(os.path.dirname(__file__), "commands")
        if not os.path.exists(path):
            os.makedirs(path)
            return
        for f in os.listdir(path):
            if f.endswith(".py") and not f.startswith("__"):
                mod = f"modules.utilitarios.economia.commands.{f[:-3]}"
                try:
                    self.bot.load_extension(mod)
                    print(f"[ECONOMIA] '{f[:-3]}' carregado.")
                except Exception as e:
                    print(f"[ECONOMIA] Erro '{f[:-3]}': {e}")

    # ── Atalhos para manter compatibilidade com código externo que chame cog.economy_components()
    def economy_components(self, inter=None) -> list:
        return p.economy_components(inter)

    def economy_embed(self, inter=None):
        return p.economy_embed(inter)

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — DROPDOWN (único, unificado)
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def on_economy_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Navegação principal ───────────────────────────────────────────────
        if cid == "Economia_Select":
            choice = inter.values[0]
            if choice == "voltar":
                painel = self.bot.get_cog("PainelCommand")
                if not painel:
                    await inter.response.send_message("⚠️ Painel não encontrado.", ephemeral=True)
                    return
                if _mode() == "embed":
                    await inter.response.defer(with_message=False)
                    embed, comps = painel.PainelEmbed(inter, None)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.response.edit_message(
                        components=painel.PainelComponents(inter, None)
                    )
            return

        # ── Select de comando ─────────────────────────────────────────────────
        if cid == "Economia_Cmd_Select":
            cmd = inter.values[0][4:]  # remove "cmd_"
            await inter.response.edit_message(components=p.cmd_config_components(cmd))
            return

        # ── Remover item da loja ──────────────────────────────────────────────
        if cid == "Economia_Shop_Remove_Select":
            v = inter.values[0]
            if v.startswith("remove_item_"):
                if EconomyHelper.remove_shop_item(v[12:]):
                    await inter.response.send_message(f"{emoji.success} Item removido.", ephemeral=True)
                    await inter.edit_original_message(components=p.shop_config_components(inter))
                else:
                    await inter.response.send_message(f"{emoji.wrong} Item não encontrado.", ephemeral=True)
            return

        # ── Remover evento ────────────────────────────────────────────────────
        if cid == "Eco_Events_Remove":
            v = inter.values[0]
            if v.startswith("rm_ev_"):
                if EconomyHelper.remove_event(v[6:]):
                    await inter.response.send_message(f"{emoji.success} Evento removido.", ephemeral=True)
                    await inter.edit_original_message(components=p.events_components(inter))
                else:
                    await inter.response.send_message(f"{emoji.wrong} Evento não encontrado.", ephemeral=True)
            return

        # ── Remover multiplicador de cargo ────────────────────────────────────
        if cid == "Eco_Mult_RemoveRole":
            v = inter.values[0]
            if v.startswith("rm_role_"):
                EconomyHelper.remove_role_multiplier(int(v[8:]))
                await inter.response.send_message(f"{emoji.success} Multiplicador de cargo removido.", ephemeral=True)
                await inter.edit_original_message(
                    components=p.multipliers_components(inter, inter.guild)
                )
            return

        # ── Remover emprego custom ────────────────────────────────────────────
        if cid == "Eco_Jobs_Remove":
            v = inter.values[0]
            if v.startswith("rm_job_"):
                jid = v[7:]
                if EconomyHelper.remove_custom_job(jid):
                    await inter.response.send_message(f"{emoji.success} Emprego `{jid}` removido.", ephemeral=True)
                    await inter.edit_original_message(components=p.jobs_config_components(inter))
                else:
                    await inter.response.send_message(f"{emoji.wrong} Emprego não encontrado.", ephemeral=True)
            return

        # ── Selecionar emprego para editar ────────────────────────────────────
        if cid == "Eco_Jobs_Edit_Select":
            v = inter.values[0]
            if v.startswith("edit_job_"):
                jid = v[9:]
                await inter.response.edit_message(components=p.job_edit_components(jid))
            return

        # ── Select de emprego do usuário (admin) ──────────────────────────────
        if cid.startswith("Eco_User_JobSelect_"):
            uid    = int(cid[19:])
            v      = inter.values[0]
            job_id = v.split("_", 1)[1] if "_" in v else v
            EconomyHelper.set_user_job(uid, job_id)
            job = EconomyHelper.get_job(job_id)
            await inter.response.send_message(
                f"{emoji.success} Emprego de `{uid}` alterado para **{job['emoji']} {job['name']}**.",
                ephemeral=True,
            )
            await inter.edit_original_message(components=p.user_profile_components(uid, inter.guild))
            return

        # ── Guard — navegação ─────────────────────────────────────────────────
        if cid == "Guard_Nav":
            value = inter.values[0]
            await _safe_defer(inter)
            if value == "ratelimit":
                await inter.edit_original_message(components=p.guard_ratelimit_components())
            elif value == "blacklist":
                await inter.edit_original_message(components=p.guard_blacklist_components())
            elif value == "channels":
                await inter.edit_original_message(components=p.guard_channels_components())
            elif value == "voltar":
                await inter.edit_original_message(components=p.economy_components(inter))
            return

        # ── Guard — blacklist select ──────────────────────────────────────────
        if cid == "Guard_BL_Action":
            value = inter.values[0]
            if value == "add_user":
                await inter.response.send_modal(p.modal_guard_bl_add_user())
            elif value == "remove_user":
                await inter.response.send_modal(p.modal_guard_bl_remove_user())
            elif value == "add_role":
                await inter.response.send_modal(p.modal_guard_bl_add_role())
            elif value == "remove_role":
                await inter.response.send_modal(p.modal_guard_bl_remove_role())
            elif value == "clear_users":
                EconomyGuard.blacklist_clear_users()
                await _safe_defer(inter)
                await inter.edit_original_message(components=p.guard_blacklist_components())
            elif value == "clear_roles":
                EconomyGuard.blacklist_clear_roles()
                await _safe_defer(inter)
                await inter.edit_original_message(components=p.guard_blacklist_components())
            return

        # ── Guard — canais select ─────────────────────────────────────────────
        if cid == "Guard_CH_Action":
            value = inter.values[0]
            if value == "allow":
                await inter.response.send_modal(p.modal_guard_ch_allow())
            elif value == "unallow":
                await inter.response.send_modal(p.modal_guard_ch_unallow())
            elif value == "block":
                await inter.response.send_modal(p.modal_guard_ch_block())
            elif value == "unblock":
                await inter.response.send_modal(p.modal_guard_ch_unblock())
            elif value == "clear_allowed":
                EconomyGuard.channels_clear_allowed()
                await _safe_defer(inter)
                await inter.edit_original_message(components=p.guard_channels_components())
            elif value == "clear_blocked":
                EconomyGuard.channels_clear_blocked()
                await _safe_defer(inter)
                await inter.edit_original_message(components=p.guard_channels_components())
            return

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — BUTTON (único, unificado)
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def on_economy_button(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Navegação ─────────────────────────────────────────────────────────
        if cid == "Economia_Toggle":
            EconomyHelper.toggle_economy()
            await inter.response.edit_message(components=p.economy_components(inter))

        elif cid == "Economia_Toggle_Logs":
            EconomyHelper.toggle_logs()
            await inter.response.edit_message(components=p.economy_components(inter))

        elif cid == "Economia_Comandos":
            await inter.response.edit_message(components=p.comandos_components(inter))

        elif cid == "Economia_Shop_Config":
            await inter.response.edit_message(components=p.shop_config_components(inter))

        elif cid == "Economia_Users":
            await inter.response.edit_message(components=p.users_components(inter))

        elif cid == "Economia_Events":
            await inter.response.edit_message(components=p.events_components(inter))

        elif cid == "Economia_Multipliers":
            await inter.response.edit_message(components=p.multipliers_components(inter, inter.guild))

        elif cid == "Economia_Jobs_Config":
            await inter.response.edit_message(components=p.jobs_config_components(inter))

        # ── Guard — entry point ───────────────────────────────────────────────
        elif cid == "Economia_Guard":
            await _safe_defer(inter)
            await inter.edit_original_message(components=p.guard_main_components())

        # ── Guard — botão voltar (subpainéis → guard main) ────────────────────
        elif cid == "Guard_Back":
            await _safe_defer(inter)
            await inter.edit_original_message(components=p.guard_main_components())

        # ── Guard — ratelimit botões ──────────────────────────────────────────
        elif cid == "Guard_RL_Toggle":
            EconomyGuard.set_ratelimit_enabled(not EconomyGuard.get_ratelimit().get("enabled", False))
            await _safe_defer(inter)
            await inter.edit_original_message(components=p.guard_ratelimit_components())

        elif cid == "Guard_RL_SetSeconds":
            await inter.response.send_modal(p.modal_guard_rl_seconds())

        elif cid == "Guard_RL_AddBypass":
            await inter.response.send_modal(p.modal_guard_rl_add_bypass())

        elif cid == "Guard_RL_RemoveBypass":
            await inter.response.send_modal(p.modal_guard_rl_remove_bypass())

        # ── Empregos — edição ─────────────────────────────────────────────────
        elif cid.startswith("Eco_Jobs_EditFull_"):
            jid = cid[18:]
            job = EconomyHelper.get_all_jobs().get(jid, {})
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Editar Emprego: {job.get('name', jid)}",
                custom_id=f"Modal_Jobs_EditFull_{jid}",
                components=[
                    disnake.ui.TextInput(label="Nome",        custom_id="job_name",      max_length=40,  value=job.get("name", "")),
                    disnake.ui.TextInput(label="Emoji",       custom_id="job_emoji",     max_length=10,  value=job.get("emoji", "💼")),
                    disnake.ui.TextInput(label="Descrição",   custom_id="job_desc",      max_length=120, value=job.get("description", "")),
                    disnake.ui.TextInput(label="Chance % aceitar",       custom_id="accept_chance", max_length=3,  value=str(job.get("accept_chance", 50))),
                    disnake.ui.TextInput(label="Pay Min,Max (ex: 100,500)", custom_id="pay_range", max_length=20, value=f"{job.get('min_pay',0)},{job.get('max_pay',0)}"),
                ],
            ))

        elif cid.startswith("Eco_Jobs_EditPay_"):
            jid = cid[17:]
            job = EconomyHelper.get_all_jobs().get(jid, {})
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Salário: {job.get('name', jid)}",
                custom_id=f"Modal_Jobs_EditPay_{jid}",
                components=[
                    disnake.ui.TextInput(label="Salário mínimo", custom_id="min_pay", max_length=10, value=str(job.get("min_pay", 0))),
                    disnake.ui.TextInput(label="Salário máximo", custom_id="max_pay", max_length=10, value=str(job.get("max_pay", 0))),
                ],
            ))

        elif cid.startswith("Eco_Jobs_EditChance_"):
            jid = cid[20:]
            job = EconomyHelper.get_all_jobs().get(jid, {})
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Chance: {job.get('name', jid)}",
                custom_id=f"Modal_Jobs_EditChance_{jid}",
                components=[
                    disnake.ui.TextInput(label="Chance de aceitar (1-100%)", custom_id="accept_chance", max_length=3, value=str(job.get("accept_chance", 50))),
                ],
            ))

        elif cid.startswith("Eco_Jobs_EditEmoji_"):
            jid = cid[19:]
            job = EconomyHelper.get_all_jobs().get(jid, {})
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Emoji: {job.get('name', jid)}",
                custom_id=f"Modal_Jobs_EditEmoji_{jid}",
                components=[
                    disnake.ui.TextInput(label="Emoji do emprego", custom_id="emoji", max_length=10, value=job.get("emoji", "💼")),
                ],
            ))

        elif cid.startswith("Eco_Jobs_EditLevel_"):
            jid = cid[19:]
            job = EconomyHelper.get_all_jobs().get(jid, {})
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Nível: {job.get('name', jid)}",
                custom_id=f"Modal_Jobs_EditLevel_{jid}",
                components=[
                    disnake.ui.TextInput(label="Nível mínimo necessário (0=qualquer)", custom_id="level", max_length=5, value=str(job.get("level_required", 0))),
                ],
            ))

        elif cid == "Eco_Jobs_ResetDefaults":
            await inter.response.send_message(
                "Isso vai **restaurar todos os empregos padrão** (os custom não são afetados). Confirmar?",
                ephemeral=True,
                components=[disnake.ui.ActionRow(
                    disnake.ui.Button(label="✅ Confirmar", style=disnake.ButtonStyle.red, custom_id="Eco_Jobs_ConfirmReset")
                )],
            )

        elif cid == "Eco_Jobs_ConfirmReset":
            EconomyHelper.reset_default_jobs()
            await inter.response.edit_message(content=f"{emoji.success} Empregos padrão restaurados.", components=[])

        # ── Configurações modais principais ───────────────────────────────────
        elif cid == "Economia_Config_Moeda":
            s = EconomyHelper.get_economy_settings()
            await inter.response.send_modal(disnake.ui.Modal(
                title="Configurar Moeda", custom_id="Modal_Eco_Moeda",
                components=[
                    disnake.ui.TextInput(label="Nome da moeda",  custom_id="nome",      max_length=20, value=s.get("currency_name","Coin")),
                    disnake.ui.TextInput(label="Emoji da moeda", custom_id="emoji_str", max_length=10, value=s.get("currency_emoji","🪙")),
                ],
            ))

        elif cid == "Economia_Config_Reset":
            s = EconomyHelper.get_economy_settings()
            await inter.response.send_modal(disnake.ui.Modal(
                title="Reset de Coins", custom_id="Modal_Eco_Reset",
                components=[
                    disnake.ui.TextInput(label="Intervalo em segundos (0=nunca)", custom_id="reset_time", max_length=10, value=str(s.get("reset_time", 0))),
                ],
            ))

        elif cid == "Economia_Config_LogChannel":
            await inter.response.send_modal(disnake.ui.Modal(
                title="Canal de Logs", custom_id="Modal_Eco_LogChannel",
                components=[
                    disnake.ui.TextInput(label="ID do canal", custom_id="channel_id", max_length=20),
                ],
            ))

        # ── Reset geral ───────────────────────────────────────────────────────
        elif cid == "Economia_Reset_All":
            await inter.response.send_message(
                "⚠️ **Isso vai zerar os coins de TODOS os usuários!** Confirme:",
                ephemeral=True,
                components=[disnake.ui.ActionRow(
                    disnake.ui.Button(label="✅ Confirmar", style=disnake.ButtonStyle.red, custom_id="Economia_Reset_Confirm")
                )],
            )

        elif cid == "Economia_Reset_Confirm":
            EconomyHelper.reset_all_coins()
            await inter.response.edit_message(content=f"{emoji.success} Todos os coins foram zerados.", components=[])

        # ── Loja ──────────────────────────────────────────────────────────────
        elif cid == "Economia_Shop_Add":
            await inter.response.send_modal(disnake.ui.Modal(
                title="Adicionar Item à Loja", custom_id="Modal_Shop_Add",
                components=[
                    disnake.ui.TextInput(label="ID único (sem espaços)", custom_id="item_id",    max_length=30),
                    disnake.ui.TextInput(label="Nome",                   custom_id="item_name",  max_length=40),
                    disnake.ui.TextInput(label="Preço",                  custom_id="item_price", max_length=10),
                    disnake.ui.TextInput(label="Descrição",              custom_id="item_desc",  max_length=80),
                    disnake.ui.TextInput(label="Emoji",                  custom_id="item_emoji", max_length=10, required=False),
                ],
            ))

        # ── Multiplicadores ───────────────────────────────────────────────────
        elif cid == "Eco_Mult_SetGlobal":
            s = EconomyHelper.get_economy_settings()
            await inter.response.send_modal(disnake.ui.Modal(
                title="Multiplicador Global", custom_id="Modal_Mult_Global",
                components=[
                    disnake.ui.TextInput(label="Valor (ex: 1.5 = +50%)", custom_id="mult", max_length=6, value=str(s.get("multiplier",1.0))),
                ],
            ))

        elif cid == "Eco_Mult_AddRole":
            await inter.response.send_modal(disnake.ui.Modal(
                title="Multiplicador por Cargo", custom_id="Modal_Mult_Role",
                components=[
                    disnake.ui.TextInput(label="ID do cargo",                     custom_id="role_id", max_length=20),
                    disnake.ui.TextInput(label="Multiplicador (ex: 2.0 = dobro)", custom_id="mult",    max_length=6),
                ],
            ))

        # ── Eventos ───────────────────────────────────────────────────────────
        elif cid == "Eco_Events_Create":
            await inter.response.send_modal(disnake.ui.Modal(
                title="Criar Evento", custom_id="Modal_Event_Create",
                components=[
                    disnake.ui.TextInput(label="Nome do evento",                        custom_id="name",        max_length=40),
                    disnake.ui.TextInput(label=f"Alvo ({'/'.join(EVENT_TARGETS)})",     custom_id="target",      max_length=20, value="global"),
                    disnake.ui.TextInput(label="Multiplicador (ex: 2.0 = dobro)",       custom_id="multiplier",  max_length=6,  value="2.0"),
                    disnake.ui.TextInput(label="Duração em horas (0 = permanente)",     custom_id="duration",    max_length=8,  value="0"),
                    disnake.ui.TextInput(label="Descrição (opcional)",                  custom_id="description", max_length=100, required=False),
                ],
            ))

        # ── Busca de usuário ──────────────────────────────────────────────────
        elif cid == "Eco_User_Search":
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Buscar Usuário", custom_id="Modal_User_Search",
                components=[
                    disnake.ui.TextInput(label="ID do usuário", custom_id="user_id", max_length=20),
                ],
            ))

        # ── Ações em usuário ──────────────────────────────────────────────────
        elif cid.startswith("Eco_User_SetCoins_"):
            uid = int(cid.split("_")[-1])
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Setar Coins", custom_id=f"Modal_User_SetCoins_{uid}",
                components=[
                    disnake.ui.TextInput(label="Novo valor de coins", custom_id="amount", max_length=12, value=str(EconomyHelper.get_user_coins(uid))),
                ],
            ))

        elif cid.startswith("Eco_User_AddCoins_"):
            uid = int(cid.split("_")[-1])
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Adicionar Coins", custom_id=f"Modal_User_AddCoins_{uid}",
                components=[
                    disnake.ui.TextInput(label="Quantidade a adicionar", custom_id="amount", max_length=12),
                ],
            ))

        elif cid.startswith("Eco_User_RemCoins_"):
            uid = int(cid.split("_")[-1])
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Remover Coins", custom_id=f"Modal_User_RemCoins_{uid}",
                components=[
                    disnake.ui.TextInput(label="Quantidade a remover", custom_id="amount", max_length=12),
                ],
            ))

        elif cid.startswith("Eco_User_ResetCD_"):
            uid  = int(cid.split("_")[-1])
            data = db.obter("database/utilitarios/economia/cooldowns.json")
            data.pop(str(uid), None)
            db.salvar("database/utilitarios/economia/cooldowns.json", data)
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.success} Cooldowns do usuário `{uid}` resetados.", ephemeral=True)
            else:
                await inter.edit_original_message(content=f"{emoji.success} Cooldowns do usuário `{uid}` resetados.", components=p.user_profile_components(uid, inter.guild))

        elif cid.startswith("Eco_User_ResetStreak_"):
            uid = int(cid.split("_")[-1])
            EconomyHelper.reset_streak(uid, "daily")
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.success} Streak resetado.", ephemeral=True)
            else:
                await inter.edit_original_message(content=f"{emoji.success} Streak resetado.", components=p.user_profile_components(uid, inter.guild))

        elif cid.startswith("Eco_User_ClearInv_"):
            uid  = int(cid.split("_")[-1])
            data = db.obter("database/utilitarios/economia/inventory.json")
            data.pop(str(uid), None)
            db.salvar("database/utilitarios/economia/inventory.json", data)
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.success} Inventário zerado.", ephemeral=True)
            else:
                await inter.edit_original_message(content=f"{emoji.success} Inventário zerado.", components=p.user_profile_components(uid, inter.guild))

        elif cid.startswith("Eco_User_SetJob_"):
            uid      = int(cid.split("_")[-1])
            all_jobs = EconomyHelper.get_all_jobs()
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_message(
                "Selecione o emprego:",
                ephemeral=True,
                components=[disnake.ui.ActionRow(disnake.ui.StringSelect(
                    custom_id=f"Eco_User_JobSelect_{uid}",
                    placeholder="Escolher emprego…",
                    options=[
                        disnake.SelectOption(
                            label=j["name"], value=f"{uid}_{jid}", emoji=j["emoji"],
                            description=f"Chance: {j['accept_chance']}% · Pay: {j['min_pay']:,}–{j['max_pay']:,}",
                        )
                        for jid, j in all_jobs.items()
                    ],
                ))],
            )

        # ── Toggle de comando ─────────────────────────────────────────────────
        elif cid.startswith("EcoCmd_Toggle_") and "_Streak_" not in cid:
            cmd = cid[14:]
            EconomyHelper.toggle_command_status(cmd)
            await inter.response.edit_message(components=p.cmd_config_components(cmd))

        elif cid.startswith("EcoCmd_Toggle_Streak_"):
            cmd = cid[21:]
            EconomyHelper.set_cmd_setting(cmd, "streak_bonus", not EconomyHelper.get_cmd_setting(cmd, "streak_bonus"))
            await inter.response.edit_message(components=p.cmd_config_components(cmd))

        # ── Modais de configuração de comando ─────────────────────────────────
        elif cid.startswith("EcoCmd_Reward_"):
            cmd = cid[14:]
            cfg = EconomyHelper.get_economy_settings().get(cmd, {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Recompensa — {CMD_LABELS.get(cmd,cmd)}", custom_id=f"Modal_EcoCmd_Reward_{cmd}",
                components=[
                    disnake.ui.TextInput(label="Mínimo", custom_id="min_r", value=str(cfg.get("min_reward",0)), max_length=10),
                    disnake.ui.TextInput(label="Máximo", custom_id="max_r", value=str(cfg.get("max_reward",0)), max_length=10),
                ],
            ))

        elif cid.startswith("EcoCmd_Cooldown_"):
            cmd = cid[16:]
            cfg = EconomyHelper.get_economy_settings().get(cmd, {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Cooldown — {CMD_LABELS.get(cmd,cmd)}", custom_id=f"Modal_EcoCmd_Cooldown_{cmd}",
                components=[
                    disnake.ui.TextInput(label="Cooldown em segundos", custom_id="cooldown", value=str(cfg.get("cooldown",3600)), max_length=10, placeholder="3600=1h 86400=24h"),
                ],
            ))

        elif cid == "EcoCmd_Crime_Chance":
            cfg = EconomyHelper.get_economy_settings().get("crime", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Crime — Chance", custom_id="Modal_EcoCmd_Crime_Chance",
                components=[
                    disnake.ui.TextInput(label="Chance de sucesso (%)", custom_id="chance", value=str(cfg.get("success_chance",60)), max_length=3),
                ],
            ))

        elif cid == "EcoCmd_Crime_Fine":
            cfg = EconomyHelper.get_economy_settings().get("crime", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Crime — Multa", custom_id="Modal_EcoCmd_Crime_Fine",
                components=[
                    disnake.ui.TextInput(label="Multa mínima", custom_id="fine_min", value=str(cfg.get("fine_min",100)), max_length=10),
                    disnake.ui.TextInput(label="Multa máxima", custom_id="fine_max", value=str(cfg.get("fine_max",400)), max_length=10),
                ],
            ))

        elif cid == "EcoCmd_Rob_Chance":
            cfg = EconomyHelper.get_economy_settings().get("rob", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Roubo — Chance", custom_id="Modal_EcoCmd_Rob_Chance",
                components=[
                    disnake.ui.TextInput(label="Chance de sucesso (%)", custom_id="chance", value=str(cfg.get("success_chance",40)), max_length=3),
                ],
            ))

        elif cid == "EcoCmd_Rob_Steal":
            cfg = EconomyHelper.get_economy_settings().get("rob", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Roubo — % Roubado", custom_id="Modal_EcoCmd_Rob_Steal",
                components=[
                    disnake.ui.TextInput(label="% mínimo", custom_id="min_pct", value=str(cfg.get("min_steal_percent",10)), max_length=3),
                    disnake.ui.TextInput(label="% máximo", custom_id="max_pct", value=str(cfg.get("max_steal_percent",40)), max_length=3),
                ],
            ))

        elif cid == "EcoCmd_Rob_Fine":
            cfg = EconomyHelper.get_economy_settings().get("rob", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Roubo — Multa", custom_id="Modal_EcoCmd_Rob_Fine",
                components=[
                    disnake.ui.TextInput(label="% multa ao falhar",    custom_id="fine_pct", value=str(cfg.get("fine_percent",25)),       max_length=3),
                    disnake.ui.TextInput(label="Saldo mínimo do alvo", custom_id="min_bal",  value=str(cfg.get("min_target_balance",200)), max_length=10),
                ],
            ))

        elif cid.startswith("EcoCmd_Bets_"):
            cmd = cid[12:]
            cfg = EconomyHelper.get_economy_settings().get(cmd, {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title=f"Apostas — {CMD_LABELS.get(cmd,cmd)}", custom_id=f"Modal_EcoCmd_Bets_{cmd}",
                components=[
                    disnake.ui.TextInput(label="Aposta mínima", custom_id="min_bet", value=str(cfg.get("min_bet",10)),   max_length=10),
                    disnake.ui.TextInput(label="Aposta máxima", custom_id="max_bet", value=str(cfg.get("max_bet",1000)), max_length=10),
                ],
            ))

        elif cid == "EcoCmd_Slots_Mult":
            cfg = EconomyHelper.get_economy_settings().get("slots", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Slots — Multiplicadores", custom_id="Modal_EcoCmd_Slots_Mult",
                components=[
                    disnake.ui.TextInput(label="Jackpot mult",  custom_id="jackpot", value=str(cfg.get("jackpot_multiplier",15.0)),    max_length=6),
                    disnake.ui.TextInput(label="3 iguais mult", custom_id="three_m", value=str(cfg.get("three_match_multiplier",5.0)), max_length=6),
                    disnake.ui.TextInput(label="2 iguais mult", custom_id="two_m",   value=str(cfg.get("two_match_multiplier",1.5)),   max_length=6),
                ],
            ))

        elif cid == "EcoCmd_Pay_Tax":
            cfg = EconomyHelper.get_economy_settings().get("pay", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Pay — Taxa", custom_id="Modal_EcoCmd_Pay_Tax",
                components=[
                    disnake.ui.TextInput(label="Taxa %", custom_id="tax", value=str(cfg.get("tax_percent",0)), max_length=3),
                ],
            ))

        elif cid == "EcoCmd_Pay_Limit":
            cfg = EconomyHelper.get_economy_settings().get("pay", {})
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Pay — Limite Diário", custom_id="Modal_EcoCmd_Pay_Limit",
                components=[
                    disnake.ui.TextInput(label="Máximo por dia (0=ilimitado)", custom_id="max_day", value=str(cfg.get("max_per_day",0)), max_length=10),
                ],
            ))

        # ── Empregos ──────────────────────────────────────────────────────────
        elif cid == "Eco_Jobs_Add":
            if inter.response.is_done():
                await inter.edit_original_message(content="Você já interagiu com este botão.")
                return
            await inter.response.send_modal(disnake.ui.Modal(
                title="Adicionar Emprego", custom_id="Modal_Jobs_Add",
                components=[
                    disnake.ui.TextInput(label="ID único (sem espaços)",                custom_id="job_id",    max_length=30),
                    disnake.ui.TextInput(label="Nome",                                  custom_id="job_name",  max_length=40),
                    disnake.ui.TextInput(label="Emoji",                                 custom_id="job_emoji", max_length=10, value="💼"),
                    disnake.ui.TextInput(label="Descrição",                             custom_id="job_desc",  max_length=80),
                    disnake.ui.TextInput(label="Chance% · Pay Min · Pay Max (vírgula)", custom_id="job_stats", max_length=30, placeholder="60,200,500"),
                ],
            ))

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — MODAL SUBMIT
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_modal_submit")
    async def on_economy_modal(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id

        # ── Moeda ─────────────────────────────────────────────────────────────
        if cid == "Modal_Eco_Moeda":
            EconomyHelper.set_currency_name(inter.text_values["nome"].strip())
            EconomyHelper.set_currency_emoji(inter.text_values["emoji_str"].strip() or "🪙")
            await inter.response.send_message(f"{emoji.success} Moeda configurada.", ephemeral=True)
            await inter.edit_original_message(components=p.economy_components(inter))

        elif cid == "Modal_Eco_Reset":
            try:
                EconomyHelper.set_reset_time(int(inter.text_values["reset_time"]))
                await inter.response.send_message(f"{emoji.success} Tempo de reset salvo.", ephemeral=True)
                await inter.edit_original_message(components=p.economy_components(inter))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Número inválido.", ephemeral=True)

        elif cid == "Modal_Eco_LogChannel":
            try:
                EconomyHelper.set_log_channel(int(inter.text_values["channel_id"]))
                await inter.response.send_message(f"{emoji.success} Canal de logs configurado.", ephemeral=True)
                await inter.edit_original_message(components=p.economy_components(inter))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        # ── Multiplicadores ───────────────────────────────────────────────────
        elif cid == "Modal_Mult_Global":
            try:
                v = float(inter.text_values["mult"])
                if v <= 0: raise ValueError
                EconomyHelper.set_global_multiplier(v)
                await inter.response.send_message(f"{emoji.success} Multiplicador global: `{v}x`", ephemeral=True)
                await inter.edit_original_message(components=p.multipliers_components(inter, inter.guild))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido (ex: 1.5).", ephemeral=True)

        elif cid == "Modal_Mult_Role":
            try:
                rid  = int(inter.text_values["role_id"])
                mult = float(inter.text_values["mult"])
                if mult <= 0: raise ValueError
                EconomyHelper.set_role_multiplier(rid, mult)
                await inter.response.send_message(f"{emoji.success} Multiplicador `{mult}x` para <@&{rid}>.", ephemeral=True)
                await inter.edit_original_message(components=p.multipliers_components(inter, inter.guild))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        # ── Eventos ───────────────────────────────────────────────────────────
        elif cid == "Modal_Event_Create":
            try:
                name   = inter.text_values["name"].strip()
                target = inter.text_values["target"].strip().lower()
                mult   = float(inter.text_values["multiplier"])
                dur    = float(inter.text_values["duration"])
                desc   = inter.text_values.get("description","").strip()
                if target not in EVENT_TARGETS:
                    raise ValueError(f"Alvo inválido. Use: {', '.join(EVENT_TARGETS)}")
                if mult <= 0:
                    raise ValueError("Multiplicador inválido.")
                ev      = EconomyHelper.add_event(name, target, mult, dur, desc)
                dur_str = "permanente" if dur == 0 else EconomyHelper.format_cooldown(int(dur * 3600))
                await inter.response.send_message(
                    f"{emoji.success} Evento **{name}** criado! `{mult}x` em `{target}` por `{dur_str}`.",
                    ephemeral=True,
                )
                await inter.edit_original_message(components=p.events_components(inter))
            except ValueError as e:
                await inter.response.send_message(f"{emoji.wrong} {e}", ephemeral=True)

        # ── Busca de usuário ──────────────────────────────────────────────────
        elif cid == "Modal_User_Search":
            try:
                uid = int(inter.text_values["user_id"])
                await inter.response.send_message(
                    content=f"👤 Perfil do usuário `{uid}`:",
                    ephemeral=True,
                    components=p.user_profile_components(uid, inter.guild),
                )
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        # ── Ações coins do usuário ────────────────────────────────────────────
        elif cid.startswith("Modal_User_SetCoins_"):
            uid = int(cid[20:])
            try:
                EconomyHelper.set_user_coins(uid, int(inter.text_values["amount"]))
                await inter.response.send_message(f"{emoji.success} Coins setados.", ephemeral=True)
                await inter.edit_original_message(components=p.user_profile_components(uid, inter.guild))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido.", ephemeral=True)

        elif cid.startswith("Modal_User_AddCoins_"):
            uid = int(cid[20:])
            try:
                amt = int(inter.text_values["amount"])
                EconomyHelper.set_user_coins(uid, EconomyHelper.get_user_coins(uid) + amt)
                await inter.response.send_message(f"{emoji.success} `{amt:,}` coins adicionados.", ephemeral=True)
                await inter.edit_original_message(components=p.user_profile_components(uid, inter.guild))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido.", ephemeral=True)

        elif cid.startswith("Modal_User_RemCoins_"):
            uid = int(cid[20:])
            try:
                amt = int(inter.text_values["amount"])
                ok  = EconomyHelper.remove_user_coins(uid, amt)
                if ok:
                    await inter.response.send_message(f"{emoji.success} `{amt:,}` coins removidos.", ephemeral=True)
                    await inter.edit_original_message(components=p.user_profile_components(uid, inter.guild))
                else:
                    await inter.response.send_message(f"{emoji.wrong} Saldo insuficiente.", ephemeral=True)
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido.", ephemeral=True)

        # ── Loja ──────────────────────────────────────────────────────────────
        elif cid == "Modal_Shop_Add":
            try:
                iid   = inter.text_values["item_id"].strip().lower().replace(" ","_")
                name  = inter.text_values["item_name"].strip()
                price = int(inter.text_values["item_price"])
                desc  = inter.text_values["item_desc"].strip()
                em_s  = inter.text_values.get("item_emoji","📦").strip() or "📦"
                EconomyHelper.add_shop_item(iid, name, price, desc, em_s)
                await inter.response.send_message(f"{emoji.success} **{name}** adicionado à loja por `{price:,}`!", ephemeral=True)
                await inter.edit_original_message(components=p.shop_config_components(inter))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Preço inválido.", ephemeral=True)

        # ── Empregos — adicionar ──────────────────────────────────────────────
        elif cid == "Modal_Jobs_Add":
            try:
                jid    = inter.text_values["job_id"].strip().lower().replace(" ","_")
                name   = inter.text_values["job_name"].strip()
                em_s   = inter.text_values["job_emoji"].strip() or "💼"
                desc   = inter.text_values["job_desc"].strip()
                stats  = inter.text_values["job_stats"].split(",")
                if len(stats) != 3: raise ValueError
                chance, min_p, max_p = int(stats[0]), int(stats[1]), int(stats[2])
                EconomyHelper.add_custom_job(jid, name, em_s, desc, chance, min_p, max_p)
                await inter.response.send_message(f"{emoji.success} Emprego **{em_s} {name}** adicionado!", ephemeral=True)
                await inter.edit_original_message(components=p.jobs_config_components(inter))
            except (ValueError, IndexError):
                await inter.response.send_message(f"{emoji.wrong} Stats inválidos. Use formato: `chance,min,max` ex: `60,200,500`", ephemeral=True)

        # ── Empregos — edição completa ────────────────────────────────────────
        elif cid.startswith("Modal_Jobs_EditFull_"):
            jid = cid[20:]
            try:
                name   = inter.text_values["job_name"].strip()
                em_s   = inter.text_values["job_emoji"].strip() or "💼"
                desc   = inter.text_values["job_desc"].strip()
                chance = int(inter.text_values["accept_chance"])
                pay    = inter.text_values["pay_range"].split(",")
                if len(pay) != 2: raise ValueError
                min_p, max_p = int(pay[0]), int(pay[1])
                if not 1 <= chance <= 100: raise ValueError
                EconomyHelper.edit_job(jid, name=name, emoji=em_s, description=desc, accept_chance=chance, min_pay=min_p, max_pay=max_p)
                await inter.response.send_message(f"{emoji.success} Emprego **{em_s} {name}** atualizado!", ephemeral=True)
                await inter.edit_original_message(components=p.job_edit_components(jid))
            except (ValueError, IndexError):
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid.startswith("Modal_Jobs_EditPay_"):
            jid = cid[19:]
            try:
                min_p = int(inter.text_values["min_pay"])
                max_p = int(inter.text_values["max_pay"])
                if min_p > max_p or min_p < 0: raise ValueError
                EconomyHelper.edit_job(jid, min_pay=min_p, max_pay=max_p)
                await inter.response.send_message(f"{emoji.success} Salário: `{min_p:,}`–`{max_p:,}`", ephemeral=True)
                await inter.edit_original_message(components=p.job_edit_components(jid))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid.startswith("Modal_Jobs_EditChance_"):
            jid = cid[22:]
            try:
                chance = int(inter.text_values["accept_chance"])
                if not 1 <= chance <= 100: raise ValueError
                EconomyHelper.edit_job(jid, accept_chance=chance)
                await inter.response.send_message(f"{emoji.success} Chance: `{chance}%`", ephemeral=True)
                await inter.edit_original_message(components=p.job_edit_components(jid))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor entre 1 e 100.", ephemeral=True)

        elif cid.startswith("Modal_Jobs_EditEmoji_"):
            jid  = cid[21:]
            em_s = inter.text_values["emoji"].strip() or "💼"
            EconomyHelper.edit_job(jid, emoji=em_s)
            await inter.response.send_message(f"{emoji.success} Emoji atualizado: {em_s}", ephemeral=True)
            await inter.edit_original_message(components=p.job_edit_components(jid))

        elif cid.startswith("Modal_Jobs_EditLevel_"):
            jid = cid[21:]
            try:
                level = int(inter.text_values["level"])
                if level < 0: raise ValueError
                EconomyHelper.edit_job(jid, level_required=level)
                await inter.response.send_message(f"{emoji.success} Nível mínimo: `{level}`", ephemeral=True)
                await inter.edit_original_message(components=p.job_edit_components(jid))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido.", ephemeral=True)

        # ── Recompensas / Cooldowns ───────────────────────────────────────────
        elif cid.startswith("Modal_EcoCmd_Reward_"):
            cmd = cid[20:]
            try:
                mn, mx = int(inter.text_values["min_r"]), int(inter.text_values["max_r"])
                if mn > mx or mn < 0: raise ValueError
                EconomyHelper.set_cmd_setting(cmd,"min_reward",mn)
                EconomyHelper.set_cmd_setting(cmd,"max_reward",mx)
                await inter.response.send_message(f"{emoji.success} Recompensa: `{mn:,}`–`{mx:,}`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components(cmd))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid.startswith("Modal_EcoCmd_Cooldown_"):
            cmd = cid[22:]
            try:
                cd = int(inter.text_values["cooldown"])
                EconomyHelper.set_cmd_setting(cmd,"cooldown",cd)
                await inter.response.send_message(f"{emoji.success} Cooldown: `{EconomyHelper.format_cooldown(cd)}`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components(cmd))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Número inválido.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Crime_Chance":
            try:
                c = int(inter.text_values["chance"])
                if not 1<=c<=100: raise ValueError
                EconomyHelper.set_cmd_setting("crime","success_chance",c)
                await inter.response.send_message(f"{emoji.success} Chance crime: `{c}%`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("crime"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor entre 1 e 100.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Crime_Fine":
            try:
                mn,mx = int(inter.text_values["fine_min"]), int(inter.text_values["fine_max"])
                EconomyHelper.set_cmd_setting("crime","fine_min",mn)
                EconomyHelper.set_cmd_setting("crime","fine_max",mx)
                await inter.response.send_message(f"{emoji.success} Multa crime: `{mn:,}`–`{mx:,}`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("crime"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Rob_Chance":
            try:
                c = int(inter.text_values["chance"])
                if not 1<=c<=100: raise ValueError
                EconomyHelper.set_cmd_setting("rob","success_chance",c)
                await inter.response.send_message(f"{emoji.success} Chance roubo: `{c}%`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("rob"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor entre 1 e 100.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Rob_Steal":
            try:
                mn,mx = int(inter.text_values["min_pct"]), int(inter.text_values["max_pct"])
                EconomyHelper.set_cmd_setting("rob","min_steal_percent",mn)
                EconomyHelper.set_cmd_setting("rob","max_steal_percent",mx)
                await inter.response.send_message(f"{emoji.success} % roubo: `{mn}%`–`{mx}%`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("rob"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Rob_Fine":
            try:
                fp,mb = int(inter.text_values["fine_pct"]), int(inter.text_values["min_bal"])
                EconomyHelper.set_cmd_setting("rob","fine_percent",fp)
                EconomyHelper.set_cmd_setting("rob","min_target_balance",mb)
                await inter.response.send_message(f"{emoji.success} Multa: `{fp}%` · Saldo mín: `{mb:,}`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("rob"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid.startswith("Modal_EcoCmd_Bets_"):
            cmd = cid[18:]
            try:
                mn,mx = int(inter.text_values["min_bet"]), int(inter.text_values["max_bet"])
                EconomyHelper.set_cmd_setting(cmd,"min_bet",mn)
                EconomyHelper.set_cmd_setting(cmd,"max_bet",mx)
                await inter.response.send_message(f"{emoji.success} Apostas: `{mn:,}`–`{mx:,}`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components(cmd))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Slots_Mult":
            try:
                j,t,tw = float(inter.text_values["jackpot"]), float(inter.text_values["three_m"]), float(inter.text_values["two_m"])
                EconomyHelper.set_cmd_setting("slots","jackpot_multiplier",j)
                EconomyHelper.set_cmd_setting("slots","three_match_multiplier",t)
                EconomyHelper.set_cmd_setting("slots","two_match_multiplier",tw)
                await inter.response.send_message(f"{emoji.success} Multiplicadores de slots atualizados.", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("slots"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valores inválidos.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Pay_Tax":
            try:
                t = int(inter.text_values["tax"])
                if not 0<=t<=100: raise ValueError
                EconomyHelper.set_cmd_setting("pay","tax_percent",t)
                await inter.response.send_message(f"{emoji.success} Taxa: `{t}%`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("pay"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor entre 0 e 100.", ephemeral=True)

        elif cid == "Modal_EcoCmd_Pay_Limit":
            try:
                l = int(inter.text_values["max_day"])
                EconomyHelper.set_cmd_setting("pay","max_per_day",l)
                await inter.response.send_message(f"{emoji.success} Limite diário: `{'Ilimitado' if l==0 else f'{l:,}'}`", ephemeral=True)
                await inter.edit_original_message(components=p.cmd_config_components("pay"))
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Número inválido.", ephemeral=True)

        # ── Guard — modais ────────────────────────────────────────────────────
        elif cid == "Modal_Guard_RL_Seconds":
            try:
                s = float(inter.text_values["seconds"])
                if s < 0.5: raise ValueError
                EconomyGuard.set_ratelimit_seconds(s)
                await inter.response.send_message(f"{emoji.success} Intervalo definido: `{s}s`", ephemeral=True)
                await inter.edit_original_message(components=p.guard_ratelimit_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido. Mínimo: `0.5`", ephemeral=True)

        elif cid == "Modal_Guard_RL_AddBypass":
            try:
                rid = int(inter.text_values["role_id"])
                EconomyGuard.add_bypass_role(rid)
                await inter.response.send_message(f"{emoji.success} <@&{rid}> adicionado ao bypass.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_ratelimit_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_RL_RemoveBypass":
            try:
                rid = int(inter.text_values["role_id"])
                EconomyGuard.remove_bypass_role(rid)
                await inter.response.send_message(f"{emoji.success} <@&{rid}> removido do bypass.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_ratelimit_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_BL_AddUser":
            try:
                uid = int(inter.text_values["user_id"])
                EconomyGuard.blacklist_add_user(uid)
                await inter.response.send_message(f"{emoji.success} <@{uid}> adicionado à blacklist.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_blacklist_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_BL_RemoveUser":
            try:
                uid = int(inter.text_values["user_id"])
                EconomyGuard.blacklist_remove_user(uid)
                await inter.response.send_message(f"{emoji.success} <@{uid}> removido da blacklist.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_blacklist_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_BL_AddRole":
            try:
                rid = int(inter.text_values["role_id"])
                EconomyGuard.blacklist_add_role(rid)
                await inter.response.send_message(f"{emoji.success} <@&{rid}> adicionado à blacklist.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_blacklist_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_BL_RemoveRole":
            try:
                rid = int(inter.text_values["role_id"])
                EconomyGuard.blacklist_remove_role(rid)
                await inter.response.send_message(f"{emoji.success} <@&{rid}> removido da blacklist.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_blacklist_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_CH_Allow":
            try:
                cid_ch = int(inter.text_values["channel_id"])
                EconomyGuard.channel_allow(cid_ch)
                await inter.response.send_message(f"{emoji.success} <#{cid_ch}> adicionado aos canais permitidos.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_channels_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_CH_Unallow":
            try:
                cid_ch = int(inter.text_values["channel_id"])
                EconomyGuard.channel_unallow(cid_ch)
                await inter.response.send_message(f"{emoji.success} <#{cid_ch}> removido dos canais permitidos.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_channels_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_CH_Block":
            try:
                cid_ch = int(inter.text_values["channel_id"])
                EconomyGuard.channel_block(cid_ch)
                await inter.response.send_message(f"{emoji.success} <#{cid_ch}> adicionado aos canais bloqueados.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_channels_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)

        elif cid == "Modal_Guard_CH_Unblock":
            try:
                cid_ch = int(inter.text_values["channel_id"])
                EconomyGuard.channel_unblock(cid_ch)
                await inter.response.send_message(f"{emoji.success} <#{cid_ch}> removido dos canais bloqueados.", ephemeral=True)
                await inter.edit_original_message(components=p.guard_channels_components())
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} ID inválido.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(EconomyCog(bot))