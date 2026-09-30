import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from functions.perms import perms


# ─── Features do painel disponíveis ──────────────────────────────────────────

PANEL_FEATURES = {
    "loja":           "Configurar Loja",
    "ticket":         "Gerenciar Ticket",
    "cloud":          "AMYCloud",
    "personalizacao": "Personalização",
    "automacoes":     "Automações",
    "protection":     "Proteção do Servidor",
    "sorteios":       "Sorteios",
    "configuracoes":  "Configurações",
}

ALL_FEATURES = list(PANEL_FEATURES.keys())


# ─── DB helpers para permissões granulares ────────────────────────────────────

def get_user_features(user_id: str) -> list[str] | None:
    """
    None  → sem entrada no DB = acesso total (comportamento padrão).
    []    → bloqueado de tudo.
    [...]  → acesso apenas às features listadas.
    """
    doc = db.get_document("user_permissions") or {}
    return doc.get("permissions", {}).get(str(user_id))


def set_user_features(user_id: str, features: list[str]):
    doc = db.get_document("user_permissions") or {}
    permissions = doc.get("permissions", {})
    permissions[str(user_id)] = features
    db.save_document("user_permissions", {"permissions": permissions})


def delete_user_features(user_id: str):
    doc = db.get_document("user_permissions") or {}
    permissions = doc.get("permissions", {})
    permissions.pop(str(user_id), None)
    db.save_document("user_permissions", {"permissions": permissions})


# ─── Estado temporário em memória (toggle de features) ───────────────────────

# chave: (admin_id, target_user_id) → set de features habilitadas
_pending_config: dict[tuple, set] = {}


# ─── Cog ─────────────────────────────────────────────────────────────────────

class GerenciarPermissoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Helpers estáticos ──────────────────────────────────────────────────

    @staticmethod
    def get_perms_users():
        return perms.get_all_users()

    @staticmethod
    def get_owner_id():
        return perms.get_owner_id()

    # ── Texto da lista de usuários ─────────────────────────────────────────

    @staticmethod
    def _users_text() -> str:
        perms_users = GerenciarPermissoes.get_perms_users()
        if not perms_users:
            return f"{emoji.wrong} Nenhum usuário com acesso."
        lines = ""
        for uid in perms_users:
            features = get_user_features(uid)
            if features is None:
                acesso = "Acesso total"
            elif not features:
                acesso = "Sem acesso"
            else:
                acesso = ", ".join(
                    PANEL_FEATURES[f] for f in features if f in PANEL_FEATURES
                )
            lines += f"{emoji.members} <@{uid}> — *{acesso}*\n"
        return lines

    # ── Painel principal (components) ─────────────────────────────────────

    @staticmethod
    def panel(inter: disnake.MessageInteraction, bot=None):
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        owner_id = GerenciarPermissoes.get_owner_id()
        is_owner = str(inter.user.id) == str(owner_id)

        action_row_buttons = [
            disnake.ui.Button(
                label="Adicionar",
                style=disnake.ButtonStyle.green,
                emoji=emoji.plus,
                custom_id="Permissoes_Adicionar",
            ),
        ]
        if is_owner:
            action_row_buttons.append(
                disnake.ui.Button(
                    label="Remover",
                    style=disnake.ButtonStyle.danger,
                    emoji=emoji.minus,
                    custom_id="Permissoes_Remover",
                )
            )

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Configurações > **Gerenciar Permissões**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"**Usuários com Acesso:**\n{GerenciarPermissoes._users_text()}"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(*action_row_buttons),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Configuracoes",
                )
            ),
        ]
        return {"components": components}

    # ── Painel principal (embed) ───────────────────────────────────────────

    @staticmethod
    def panel_embed(inter: disnake.MessageInteraction, bot=None):
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title="Gerenciar Permissões",
            description=(
                f"-# Painel > Configurações > **Gerenciar Permissões**\n\n"
                f"**Usuários com Acesso:**\n{GerenciarPermissoes._users_text()}"
            ),
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        owner_id = GerenciarPermissoes.get_owner_id()
        is_owner = str(inter.user.id) == str(owner_id)

        row_buttons = [
            disnake.ui.Button(
                label="Adicionar",
                style=disnake.ButtonStyle.green,
                emoji=emoji.plus,
                custom_id="Permissoes_Adicionar",
            ),
        ]
        if is_owner:
            row_buttons.append(
                disnake.ui.Button(
                    label="Remover",
                    style=disnake.ButtonStyle.danger,
                    emoji=emoji.minus,
                    custom_id="Permissoes_Remover",
                )
            )

        components = [
            disnake.ui.ActionRow(*row_buttons),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Configuracoes",
                )
            ),
        ]
        return embed, components

    # ── Painel de configuração granular de features ────────────────────────

    def _build_feature_config_panel(
        self,
        inter,
        target_user_id: str,
        enabled_features: set,
        primary_color_hex: str = None,
    ):
        """
        8 botões do painel como toggles.
        Verde = liberado | Cinza = bloqueado.
        """
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        # 2 linhas de 4 botões cada
        feature_items = list(PANEL_FEATURES.items())
        rows = []
        for i in range(0, len(feature_items), 4):
            chunk = feature_items[i : i + 4]
            buttons = []
            for feat_key, feat_label in chunk:
                is_on = feat_key in enabled_features
                buttons.append(
                    disnake.ui.Button(
                        label=feat_label,
                        style=disnake.ButtonStyle.green if is_on else disnake.ButtonStyle.grey,
                        custom_id=f"Permissoes_Toggle_{target_user_id}_{feat_key}",
                    )
                )
            rows.append(disnake.ui.ActionRow(*buttons))

        # Linha de ação final
        rows.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Selecionar Todos",
                    style=disnake.ButtonStyle.primary,
                    custom_id=f"Permissoes_SelectAll_{target_user_id}",
                ),
                disnake.ui.Button(
                    label="Limpar Tudo",
                    style=disnake.ButtonStyle.secondary,
                    custom_id=f"Permissoes_ClearAll_{target_user_id}",
                ),
                disnake.ui.Button(
                    label="Confirmar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.plus,
                    custom_id=f"Permissoes_Confirmar_{target_user_id}",
                ),
                disnake.ui.Button(
                    label="Cancelar",
                    style=disnake.ButtonStyle.danger,
                    emoji=emoji.minus,
                    custom_id="Permissoes_CancelarConfig",
                ),
            )
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Permissões > **Configurar Acesso** de <@{target_user_id}>\n\n"
                    f"Clique nos botões para **liberar** ou **bloquear** cada seção.\n"
                    f"🟢 Verde = com acesso  |  ⬜ Cinza = sem acesso"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **container_kwargs,
            )
        ]

    # ── Helper: refresh do painel após ação ───────────────────────────────

    async def _refresh_panel(self, inter, is_modal: bool = False):
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")

        if mode == "embed":
            if not is_modal:
                await embed_message.wait(inter, send=False)
            emb, comps = self.panel_embed(inter)
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            if not is_modal:
                await message.wait(inter, send=False)
            panel = self.panel(inter, self.bot)
            await inter.edit_original_message(
                **panel, flags=disnake.MessageFlags(is_components_v2=True)
            )

    # Prefixos reconhecidos por este cog.
    # Qualquer custom_id fora deste conjunto é ignorado imediatamente,
    # sem responder nem tocar na interação — evita conflito com outros cogs.
    _BUTTON_PREFIXES: tuple[str, ...] = (
        "Permissoes_Adicionar",
        "Permissoes_Remover",
        "Permissoes_Toggle_",
        "Permissoes_SelectAll_",
        "Permissoes_ClearAll_",
        "Permissoes_Confirmar_",
        "Permissoes_CancelarConfig",
        "Permissoes_Voltar",
        "Painel_Configuracoes",
    )

    _MODAL_IDS: tuple[str, ...] = (
        "Permissoes_Adicionar_Modal",
        "Permissoes_Remover_Modal",
    )

    # ── Listener de botões ─────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # Guard: ignora interações que não pertencem a este cog
        if not cid or not any(cid.startswith(p) for p in self._BUTTON_PREFIXES):
            return

        # ── Abrir modal de adicionar ───────────────────────────────────────
        if cid == "Permissoes_Adicionar":
            await inter.response.send_modal(
                title="Adicionar Usuário",
                custom_id="Permissoes_Adicionar_Modal",
                components=[
                    disnake.ui.Label(
                        text="Selecione o Usuário",
                        component=disnake.ui.UserSelect(
                            custom_id="user_select",
                            placeholder="Selecione um usuário para adicionar...",
                        ),
                        description="Escolha o usuário que receberá permissão de administrador do bot.",
                    )
                ],
            )

        # ── Abrir modal de remover (SOMENTE OWNER) ────────────────────────
        elif cid == "Permissoes_Remover":
            owner_id = self.get_owner_id()
            if str(inter.user.id) != str(owner_id):
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas o **dono do bot** pode remover usuários das permissões.",
                    ephemeral=True,
                )
                return

            if not self.get_perms_users():
                await inter.response.send_message(
                    f"{emoji.wrong} Não há usuários com permissão para remover.",
                    ephemeral=True,
                )
                return

            await inter.response.send_modal(
                title="Remover Usuário",
                custom_id="Permissoes_Remover_Modal",
                components=[
                    disnake.ui.Label(
                        text="Selecione o Usuário",
                        component=disnake.ui.UserSelect(
                            custom_id="user_select",
                            placeholder="Selecione um usuário para remover...",
                        ),
                        description="Escolha o usuário que terá a permissão removida.",
                    )
                ],
            )

        # ── Toggle de feature individual ──────────────────────────────────
        elif cid.startswith("Permissoes_Toggle_"):
            parts = cid.split("_")
            target_user_id = parts[2]
            feature_key    = "_".join(parts[3:])

            key     = (str(inter.user.id), target_user_id)
            current = _pending_config.get(key, set(ALL_FEATURES))

            if feature_key in current:
                current.discard(feature_key)
            else:
                current.add(feature_key)
            _pending_config[key] = current

            colors = db.get_document("custom_colors") or {}
            panel  = self._build_feature_config_panel(
                inter, target_user_id, current, colors.get("primary")
            )
            await inter.response.edit_message(
                components=panel,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        # ── Selecionar todos ──────────────────────────────────────────────
        elif cid.startswith("Permissoes_SelectAll_"):
            target_user_id = cid.replace("Permissoes_SelectAll_", "")
            key            = (str(inter.user.id), target_user_id)
            _pending_config[key] = set(ALL_FEATURES)

            colors = db.get_document("custom_colors") or {}
            panel  = self._build_feature_config_panel(
                inter, target_user_id, _pending_config[key], colors.get("primary")
            )
            await inter.response.edit_message(
                components=panel,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        # ── Limpar tudo ───────────────────────────────────────────────────
        elif cid.startswith("Permissoes_ClearAll_"):
            target_user_id = cid.replace("Permissoes_ClearAll_", "")
            key            = (str(inter.user.id), target_user_id)
            _pending_config[key] = set()

            colors = db.get_document("custom_colors") or {}
            panel  = self._build_feature_config_panel(
                inter, target_user_id, _pending_config[key], colors.get("primary")
            )
            await inter.response.edit_message(
                components=panel,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        # ── Confirmar configuração ────────────────────────────────────────
        elif cid.startswith("Permissoes_Confirmar_"):
            target_user_id = cid.replace("Permissoes_Confirmar_", "")
            key            = (str(inter.user.id), target_user_id)
            features       = list(_pending_config.pop(key, set(ALL_FEATURES)))

            set_user_features(target_user_id, features)

            if target_user_id not in self.get_perms_users():
                perms.add_user(target_user_id)

            await message.wait(inter, send=False)
            await self._refresh_panel(inter, is_modal=False)

        # ── Cancelar configuração ─────────────────────────────────────────
        elif cid == "Permissoes_CancelarConfig":
            for k in list(_pending_config.keys()):
                if k[0] == str(inter.user.id):
                    _pending_config.pop(k, None)

            await message.wait(inter, send=False)
            await self._refresh_panel(inter, is_modal=False)

        # ── Voltar ao painel de permissões ────────────────────────────────
        elif cid == "Permissoes_Voltar":
            await self._refresh_panel(inter, is_modal=False)

    # ── Listener de modais ─────────────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):

        # Guard: ignora modais que não pertencem a este cog
        if inter.custom_id not in self._MODAL_IDS:
            return

        # ── Adicionar usuário → abre tela de config de features ───────────
        if inter.custom_id == "Permissoes_Adicionar_Modal":
            valores            = inter.resolved_values
            user_select_values = valores.get("user_select", [])

            if not user_select_values:
                await inter.response.send_message(
                    f"{emoji.wrong} Você precisa selecionar um usuário!",
                    ephemeral=True,
                )
                return

            selected_user = (
                user_select_values[0]
                if isinstance(user_select_values, list)
                else user_select_values
            )
            target_user_id = str(
                selected_user.id if hasattr(selected_user, "id") else selected_user
            )

            existing = get_user_features(target_user_id)
            initial  = set(existing) if existing is not None else set(ALL_FEATURES)
            _pending_config[(str(inter.user.id), target_user_id)] = initial

            colors = db.get_document("custom_colors") or {}
            panel  = self._build_feature_config_panel(
                inter, target_user_id, initial, colors.get("primary")
            )
            await inter.response.edit_message(
                components=panel,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        # ── Remover usuário ───────────────────────────────────────────────
        elif inter.custom_id == "Permissoes_Remover_Modal":
            owner_id = self.get_owner_id()
            if str(inter.user.id) != str(owner_id):
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas o **dono do bot** pode remover usuários.",
                    ephemeral=True,
                )
                return

            valores            = inter.resolved_values
            user_select_values = valores.get("user_select", [])

            if not user_select_values:
                await inter.response.send_message(
                    f"{emoji.wrong} Você precisa selecionar um usuário!",
                    ephemeral=True,
                )
                return

            selected_user = (
                user_select_values[0]
                if isinstance(user_select_values, list)
                else user_select_values
            )
            target_user_id = str(
                selected_user.id if hasattr(selected_user, "id") else selected_user
            )

            if target_user_id not in self.get_perms_users():
                await inter.response.send_message(
                    f"{emoji.wrong} Este usuário não possui permissão!",
                    ephemeral=True,
                )
                return

            if target_user_id == str(owner_id):
                await inter.response.send_message(
                    f"{emoji.wrong} O dono do bot tem permissão automática e não pode ser removido!",
                    ephemeral=True,
                )
                return

            perms.remove_user(target_user_id)
            delete_user_features(target_user_id)

            await self._refresh_panel(inter, is_modal=True)


def setup(bot: commands.Bot):
    bot.add_cog(GerenciarPermissoes(bot))