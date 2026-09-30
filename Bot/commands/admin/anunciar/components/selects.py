import disnake
from disnake.ext import commands

from ..anunciar import Anunciar
from functions.message import message
from functions.database import database
from functions.emoji import emoji
from functions.utils import utils
from .buttons import Buttons

MAX_SELECTS = 3
MAX_OPTIONS = 25

ACTION_LABELS = {
    "disabled":   "Desativado",
    "message":    "Mensagem Efêmera",
    "addrole":    "Dar Cargo (Toggle)",
    "removerole": "Remover Cargo",
}


class Selects(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── DB helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_cfg() -> dict:
        return database.get_document("messages_anunciar")

    @staticmethod
    def _save_cfg(cfg: dict) -> None:
        database.save_document("messages_anunciar", {}, cfg)

    @staticmethod
    def _get_selects(cfg: dict) -> list:
        return cfg.get("message", {}).get("selects", [])

    @staticmethod
    def _find_select(cfg: dict, select_id: str) -> dict | None:
        return next((s for s in Selects._get_selects(cfg) if s.get("id") == select_id), None)

    @staticmethod
    def _find_option(select: dict, option_id: str) -> dict | None:
        return next((o for o in select.get("options", []) if o.get("id") == option_id), None)

    # ─── UI builders ─────────────────────────────────────────────────────────

    @staticmethod
    def panel() -> list:
        """Painel principal de gerenciamento de select menus."""
        cfg    = Selects._get_cfg()
        selects = Selects._get_selects(cfg)

        options = []
        for s in selects:
            n_opts = len(s.get("options", []))
            options.append(disnake.SelectOption(
                label=s.get("placeholder") or "Sem placeholder",
                value=s.get("id"),
                emoji=emoji.route,
                description=f"{n_opts} opção(ões) • min {s.get('min_values',1)} / max {s.get('max_values',1)}"
            ))

        if not options:
            options.append(disnake.SelectOption(
                label="Nenhum select registrado", value="none", emoji=emoji.warn
            ))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Anunciar > Select Menus"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure os select menus da mensagem.\n"
                    "Selecione um item abaixo para editar opções e ações."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"**Selects registrados:** `{len(selects)}`\n"
                    f"-# Limite de `{MAX_SELECTS}` selects por mensagem."
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione um select para configurar",
                        custom_id="Anunciar_Select_SelecionarSelect",
                        options=options,
                        disabled=len(selects) == 0,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar select",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id="Anunciar_Select_AdicionarSelect",
                        disabled=len(selects) >= MAX_SELECTS,
                    ),
                    disnake.ui.Button(
                        label="Apagar todos",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Anunciar_ApagarSelects",
                        disabled=len(selects) == 0,
                    ),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial"
                )
            ),
        ]

    @staticmethod
    def select_detail(select_id: str) -> list:
        """Painel de detalhes de um select específico."""
        cfg = Selects._get_cfg()
        sel = Selects._find_select(cfg, select_id)
        if not sel:
            return []

        options = sel.get("options", [])
        opt_items = []
        for o in options:
            proc_emoji = Buttons.processar_emoji(o.get("emoji")) if o.get("emoji") else None
            a_type = (o.get("action") or {}).get("type", "disabled")
            opt_items.append(disnake.SelectOption(
                label=o.get("label") or "Sem label",
                value=o.get("id"),
                emoji=proc_emoji,
                description=o.get("description") or f"Ação: {ACTION_LABELS.get(a_type, a_type)}"
            ))

        if not opt_items:
            opt_items.append(
                disnake.SelectOption(label="Nenhuma opção registrada", value="none", emoji=emoji.warn)
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Anunciar > Selects > {sel.get('placeholder') or 'Sem placeholder'}"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"**Placeholder:** `{sel.get('placeholder') or 'Nenhum'}`\n"
                    f"**Valores mínimos:** `{sel.get('min_values', 1)}`  "
                    f"**Valores máximos:** `{sel.get('max_values', 1)}`\n"
                    f"**Opções configuradas:** `{len(options)}`"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione uma opção para configurar",
                        custom_id=f"Anunciar_Select_SelecionarOpcao_{select_id}",
                        options=opt_items,
                        disabled=len(options) == 0,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar select",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id=f"Anunciar_Select_EditarSelect_{select_id}",
                    ),
                    disnake.ui.Button(
                        label="Adicionar opção",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id=f"Anunciar_Select_AdicionarOpcao_{select_id}",
                        disabled=len(options) >= MAX_OPTIONS,
                    ),
                    disnake.ui.Button(
                        label="Apagar select",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id=f"Anunciar_Select_ApagarSelect_{select_id}",
                    ),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", emoji=emoji.back, custom_id="Anunciar_DefinirSelects"
                )
            ),
        ]

    @staticmethod
    def option_detail(select_id: str, option_id: str, inter: disnake.MessageInteraction = None) -> list:
        """Painel de configuração de uma opção específica."""
        cfg = Selects._get_cfg()
        sel = Selects._find_select(cfg, select_id)
        if not sel:
            return []
        opt = Selects._find_option(sel, option_id)
        if not opt:
            return []

        action     = opt.get("action") or {}
        a_type     = action.get("type", "disabled")
        proc_emoji = Buttons.processar_emoji(opt.get("emoji")) if opt.get("emoji") else None

        # Row extra dependendo da ação configurada
        extra_row = None
        if a_type in ("addrole", "removerole"):
            role_id = action.get("role")
            role    = inter.guild.get_role(int(role_id)) if (inter and role_id) else None
            extra_row = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione o cargo",
                    custom_id=f"Anunciar_Select_OpcaoCargo_{select_id}_{option_id}",
                    default_values=[role] if role else [],
                )
            )
        elif a_type == "message":
            extra_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Editar mensagem efêmera",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id=f"Anunciar_Select_EditarMensagem_{select_id}_{option_id}",
                )
            )

        inner = [
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Anunciar > Selects > Opção > {opt.get('label') or 'Sem label'}"
            ),
            disnake.ui.Separator(),
            disnake.ui.Section(
                disnake.ui.TextDisplay(
                    f"**Label:** `{opt.get('label') or 'Nenhum'}`\n"
                    f"**Descrição:** `{opt.get('description') or 'Nenhuma'}`\n"
                    f"**Emoji:** {proc_emoji if proc_emoji else '`Nenhum`'}\n"
                    f"**Ação atual:** `{ACTION_LABELS.get(a_type, a_type)}`"
                ),
                accessory=disnake.ui.Button(
                    label=opt.get("label") or "\u200b",
                    emoji=proc_emoji,
                    disabled=True,
                    style=disnake.ButtonStyle.secondary,
                ),
            ),
            disnake.ui.Separator(),
        ]

        if extra_row:
            inner.append(extra_row)

        inner.append(
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Anunciar_Select_AlterarAcaoOpcao_{select_id}_{option_id}",
                    placeholder="Selecione a ação desta opção",
                    options=[
                        disnake.SelectOption(
                            label="Mensagem Efêmera", emoji=emoji.message, value="message",
                            default=a_type == "message",
                            description="Envia uma mensagem efêmera ao usuário.",
                        ),
                        disnake.SelectOption(
                            label="Dar Cargo (Toggle)", emoji=emoji.plus, value="addrole",
                            default=a_type == "addrole",
                            description="Adiciona ou remove o cargo ao usuário.",
                        ),
                        disnake.SelectOption(
                            label="Remover Cargo", emoji=emoji.minus, value="removerole",
                            default=a_type == "removerole",
                            description="Remove o cargo do usuário.",
                        ),
                        disnake.SelectOption(
                            label="Desativado", emoji=emoji.wrong, value="disabled",
                            default=a_type == "disabled",
                            description="Esta opção não executa nenhuma ação.",
                        ),
                    ],
                )
            )
        )

        inner.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Editar opção",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id=f"Anunciar_Select_EditarOpcao_{select_id}_{option_id}",
                ),
                disnake.ui.Button(
                    label="Apagar opção",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id=f"Anunciar_Select_ApagarOpcao_{select_id}_{option_id}",
                ),
            )
        )

        return [
            disnake.ui.Container(*inner),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    emoji=emoji.back,
                    custom_id=f"Anunciar_Select_ConfigurarSelect_{select_id}",
                )
            ),
        ]

    # ─── Modals ──────────────────────────────────────────────────────────────

    class CriarSelectModal(disnake.ui.Modal):
        def __init__(self, select_id: str = None):
            self.select_id = select_id
            cfg = Selects._get_cfg()
            sel = Selects._find_select(cfg, select_id) if select_id else None

            super().__init__(
                title="Configurar Select Menu",
                custom_id="Anunciar_Select_CriarSelectModal",
                components=[
                    disnake.ui.TextInput(
                        label="Placeholder",
                        custom_id="placeholder",
                        placeholder="Selecione uma opção...",
                        required=True,
                        max_length=150,
                        value=sel.get("placeholder", "") if sel else "",
                    ),
                    disnake.ui.TextInput(
                        label="Valores mínimos (1–25)",
                        custom_id="min_values",
                        placeholder="1",
                        required=False,
                        max_length=2,
                        value=str(sel.get("min_values", 1)) if sel else "1",
                    ),
                    disnake.ui.TextInput(
                        label="Valores máximos (1–25)",
                        custom_id="max_values",
                        placeholder="1",
                        required=False,
                        max_length=2,
                        value=str(sel.get("max_values", 1)) if sel else "1",
                    ),
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            cfg         = Selects._get_cfg()
            placeholder = inter.text_values.get("placeholder", "").strip()

            try:
                min_v = max(1, min(25, int(inter.text_values.get("min_values") or "1")))
            except ValueError:
                min_v = 1
            try:
                max_v = max(min_v, min(25, int(inter.text_values.get("max_values") or "1")))
            except ValueError:
                max_v = min_v

            if self.select_id:
                sel = Selects._find_select(cfg, self.select_id)
                if sel:
                    sel["placeholder"] = placeholder
                    sel["min_values"]  = min_v
                    sel["max_values"]  = max_v
                    Selects._save_cfg(cfg)
                await inter.response.edit_message(
                    components=Selects.select_detail(self.select_id)
                )
            else:
                new_id = utils.gerar_id()
                cfg.setdefault("message", {}).setdefault("selects", []).append({
                    "id":         new_id,
                    "placeholder": placeholder,
                    "min_values": min_v,
                    "max_values": max_v,
                    "options":    [],
                })
                Selects._save_cfg(cfg)
                await inter.response.edit_message(
                    components=Selects.select_detail(new_id)
                )

    class CriarOpcaoModal(disnake.ui.Modal):
        def __init__(self, select_id: str, option_id: str = None):
            self.select_id = select_id
            self.option_id = option_id
            cfg = Selects._get_cfg()
            sel = Selects._find_select(cfg, select_id)
            opt = Selects._find_option(sel, option_id) if (sel and option_id) else None

            super().__init__(
                title="Configurar Opção do Select",
                custom_id="Anunciar_Select_CriarOpcaoModal",
                components=[
                    disnake.ui.TextInput(
                        label="Label",
                        custom_id="label",
                        placeholder="Nome da opção",
                        required=True,
                        max_length=100,
                        value=opt.get("label", "") if opt else "",
                    ),
                    disnake.ui.TextInput(
                        label="Descrição (opcional)",
                        custom_id="description",
                        placeholder="Texto descritivo da opção",
                        required=False,
                        max_length=100,
                        value=opt.get("description", "") if opt else "",
                    ),
                    disnake.ui.TextInput(
                        label="Emoji (opcional)",
                        custom_id="emoji_input",
                        placeholder="Emoji unicode ou <:nome:id>",
                        required=False,
                        max_length=64,
                        value=opt.get("emoji", "") if opt else "",
                    ),
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            cfg = Selects._get_cfg()
            sel = Selects._find_select(cfg, self.select_id)
            if not sel:
                await message.error(inter, "Select não encontrado.", send=True)
                return

            label       = inter.text_values.get("label", "").strip()
            description = inter.text_values.get("description", "").strip() or None
            emoji_raw   = inter.text_values.get("emoji_input", "").strip() or None

            if self.option_id:
                opt = Selects._find_option(sel, self.option_id)
                if not opt:
                    await message.error(inter, "Opção não encontrada.", send=True)
                    return
                opt["label"]       = label
                opt["description"] = description
                opt["emoji"]       = emoji_raw
                Selects._save_cfg(cfg)
                await inter.response.edit_message(
                    components=Selects.option_detail(self.select_id, self.option_id, inter)
                )
            else:
                new_opt_id = utils.gerar_id()
                sel.setdefault("options", []).append({
                    "id":          new_opt_id,
                    "label":       label,
                    "description": description,
                    "emoji":       emoji_raw,
                    "action":      {"type": "disabled"},
                })
                Selects._save_cfg(cfg)
                await inter.response.edit_message(
                    components=Selects.option_detail(self.select_id, new_opt_id, inter)
                )

    class EditarMensagemOpcaoModal(disnake.ui.Modal):
        def __init__(self, select_id: str, option_id: str):
            self.select_id = select_id
            self.option_id = option_id
            cfg = Selects._get_cfg()
            sel = Selects._find_select(cfg, select_id)
            opt = Selects._find_option(sel, option_id) if sel else None
            current = ((opt or {}).get("action") or {}).get("message", "") or ""

            super().__init__(
                title="Mensagem Efêmera da Opção",
                custom_id="Anunciar_Select_EditarMensagemOpcaoModal",
                components=[
                    disnake.ui.TextInput(
                        label="Mensagem",
                        custom_id="message",
                        placeholder="Texto enviado ao usuário ao selecionar esta opção",
                        required=True,
                        style=disnake.TextInputStyle.paragraph,
                        value=current,
                    )
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            cfg = Selects._get_cfg()
            sel = Selects._find_select(cfg, self.select_id)
            if not sel:
                return
            opt = Selects._find_option(sel, self.option_id)
            if not opt:
                return
            opt["action"] = {
                "type":    "message",
                "message": inter.text_values.get("message", "").strip(),
            }
            Selects._save_cfg(cfg)
            await inter.response.edit_message(
                components=Selects.option_detail(self.select_id, self.option_id, inter)
            )

    # ─── Listeners ───────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "Anunciar_DefinirSelects":
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=Selects.panel())

        elif cid == "Anunciar_Select_AdicionarSelect":
            await inter.response.send_modal(Selects.CriarSelectModal())

        elif cid == "Anunciar_ApagarSelects":
            await message.wait(inter, send=False)
            cfg = Selects._get_cfg()
            cfg.get("message", {})["selects"] = []
            Selects._save_cfg(cfg)
            await inter.edit_original_message(components=Anunciar.create_buttons())

        elif cid.startswith("Anunciar_Select_EditarSelect_"):
            select_id = cid.removeprefix("Anunciar_Select_EditarSelect_")
            await inter.response.send_modal(Selects.CriarSelectModal(select_id=select_id))

        elif cid.startswith("Anunciar_Select_ApagarSelect_"):
            await message.wait(inter, send=False)
            select_id = cid.removeprefix("Anunciar_Select_ApagarSelect_")
            cfg = Selects._get_cfg()
            cfg["message"]["selects"] = [
                s for s in Selects._get_selects(cfg) if s.get("id") != select_id
            ]
            Selects._save_cfg(cfg)
            await inter.edit_original_message(components=Selects.panel())

        elif cid.startswith("Anunciar_Select_AdicionarOpcao_"):
            select_id = cid.removeprefix("Anunciar_Select_AdicionarOpcao_")
            await inter.response.send_modal(Selects.CriarOpcaoModal(select_id=select_id))

        elif cid.startswith("Anunciar_Select_ConfigurarSelect_"):
            await message.wait(inter, send=False)
            select_id = cid.removeprefix("Anunciar_Select_ConfigurarSelect_")
            await inter.edit_original_message(components=Selects.select_detail(select_id))

        elif cid.startswith("Anunciar_Select_ApagarOpcao_"):
            await message.wait(inter, send=False)
            rest = cid.removeprefix("Anunciar_Select_ApagarOpcao_")
            select_id, option_id = rest.split("_", 1)
            cfg = Selects._get_cfg()
            sel = Selects._find_select(cfg, select_id)
            if sel:
                sel["options"] = [o for o in sel.get("options", []) if o.get("id") != option_id]
                Selects._save_cfg(cfg)
            await inter.edit_original_message(components=Selects.select_detail(select_id))

        elif cid.startswith("Anunciar_Select_EditarOpcao_"):
            rest = cid.removeprefix("Anunciar_Select_EditarOpcao_")
            select_id, option_id = rest.split("_", 1)
            await inter.response.send_modal(
                Selects.CriarOpcaoModal(select_id=select_id, option_id=option_id)
            )

        elif cid.startswith("Anunciar_Select_EditarMensagem_"):
            rest = cid.removeprefix("Anunciar_Select_EditarMensagem_")
            select_id, option_id = rest.split("_", 1)
            await inter.response.send_modal(
                Selects.EditarMensagemOpcaoModal(select_id=select_id, option_id=option_id)
            )

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "Anunciar_Select_SelecionarSelect":
            select_id = inter.values[0] if inter.values else None
            if not select_id or select_id == "none":
                return
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=Selects.select_detail(select_id))

        elif cid.startswith("Anunciar_Select_SelecionarOpcao_"):
            select_id = cid.removeprefix("Anunciar_Select_SelecionarOpcao_")
            option_id = inter.values[0] if inter.values else None
            if not option_id or option_id == "none":
                return
            await message.wait(inter, send=False)
            await inter.edit_original_message(
                components=Selects.option_detail(select_id, option_id, inter)
            )

        elif cid.startswith("Anunciar_Select_AlterarAcaoOpcao_"):
            rest      = cid.removeprefix("Anunciar_Select_AlterarAcaoOpcao_")
            select_id, option_id = rest.split("_", 1)
            cfg       = Selects._get_cfg()
            sel       = Selects._find_select(cfg, select_id)
            if not sel:
                return
            opt = Selects._find_option(sel, option_id)
            if not opt:
                return

            selected = inter.values[0] if inter.values else None
            action   = opt.setdefault("action", {})

            if selected == "message":
                if not action.get("message"):
                    await inter.response.send_modal(
                        Selects.EditarMensagemOpcaoModal(select_id=select_id, option_id=option_id)
                    )
                    return
                action["type"] = "message"
            elif selected == "addrole":
                existing_role = action.get("role")
                action.clear()
                action["type"] = "addrole"
                if existing_role:
                    action["role"] = existing_role
            elif selected == "removerole":
                existing_role = action.get("role")
                action.clear()
                action["type"] = "removerole"
                if existing_role:
                    action["role"] = existing_role
            elif selected == "disabled":
                action.clear()
                action["type"] = "disabled"

            Selects._save_cfg(cfg)
            await inter.response.edit_message(
                components=Selects.option_detail(select_id, option_id, inter)
            )

        elif cid.startswith("Anunciar_Select_OpcaoCargo_"):
            rest      = cid.removeprefix("Anunciar_Select_OpcaoCargo_")
            select_id, option_id = rest.split("_", 1)
            cfg       = Selects._get_cfg()
            sel       = Selects._find_select(cfg, select_id)
            if not sel:
                return
            opt = Selects._find_option(sel, option_id)
            if not opt:
                return
            action = opt.setdefault("action", {})
            if inter.values:
                action["role"] = int(inter.values[0])
            Selects._save_cfg(cfg)
            await inter.response.edit_message(
                components=Selects.option_detail(select_id, option_id, inter)
            )

        # ── Runtime: usuário interage com um select numa mensagem postada ──
        elif cid.startswith("Anunciar_RuntimeAction_Select_"):
            select_id = cid.removeprefix("Anunciar_RuntimeAction_Select_")
            cfg       = Selects._get_cfg()
            sel       = Selects._find_select(cfg, select_id)
            if not sel:
                await message.error(inter, "Select não encontrado. Pode ter sido deletado.", send=True)
                return

            selected_ids = inter.values or []

            for opt_id in selected_ids:
                opt    = Selects._find_option(sel, opt_id)
                if not opt:
                    continue
                action = opt.get("action") or {}
                a_type = action.get("type", "disabled")

                if a_type == "message":
                    text = action.get("message") or "Mensagem não configurada."
                    if inter.response.is_done():
                        await inter.followup.send(text, ephemeral=True)
                    else:
                        await inter.response.send_message(text, ephemeral=True)
                    return

                elif a_type in ("addrole", "removerole"):
                    role_id = action.get("role")
                    if not role_id:
                        await message.error(inter, "Nenhum cargo configurado para esta opção.", send=True)
                        return
                    role   = inter.guild.get_role(int(role_id))
                    if not role:
                        await message.error(inter, "Cargo configurado não encontrado.", send=True)
                        return
                    member = (
                        inter.user if isinstance(inter.user, disnake.Member)
                        else await inter.guild.fetch_member(inter.user.id)
                    )
                    me: disnake.Member = inter.guild.me  # type: ignore
                    if not me.guild_permissions.manage_roles:
                        await message.error(inter, "Não tenho permissão para gerenciar cargos.", send=True)
                        return
                    if role >= me.top_role:
                        await message.error(inter, "Meu cargo é menor que o cargo alvo.", send=True)
                        return

                    try:
                        if a_type == "addrole":
                            if role in member.roles:
                                await member.remove_roles(role, reason="Anunciar Select: toggle remove")
                                resp = f"Cargo removido: {role.mention}"
                            else:
                                await member.add_roles(role, reason="Anunciar Select: toggle add")
                                resp = f"Cargo adicionado: {role.mention}"
                        else:
                            if role in member.roles:
                                await member.remove_roles(role, reason="Anunciar Select: remove")
                                resp = f"Cargo removido: {role.mention}"
                            else:
                                resp = f"Você não possui o cargo {role.mention}."

                        if inter.response.is_done():
                            await inter.followup.send(resp, ephemeral=True)
                        else:
                            await inter.response.send_message(resp, ephemeral=True)
                    except disnake.Forbidden:
                        await message.error(inter, "Permissões insuficientes.", send=True)
                    return

            # Nenhuma opção reconhecida — ack silencioso
            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)