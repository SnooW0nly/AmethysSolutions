import aiohttp
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


DISCORD_API_BASE = "https://discord.com/api/v10"


async def validate_user_token(token: str) -> dict | None:
    """Valida token e retorna dados do usuário (sem verificar senha)."""
    headers = {"Authorization": token}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DISCORD_API_BASE}/users/@me", headers=headers) as resp:
            if resp.status == 401:
                return None
            if resp.status == 200:
                data = await resp.json()
                if data.get("bot"):
                    raise ValueError("bot_token")
                return data
            return None


def _error_components(text: str) -> list:
    return [disnake.ui.Container(disnake.ui.TextDisplay(text))]


class TokensPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _get_accent() -> dict:
        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        if hex_color:
            return {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))}
        return {}

    @staticmethod
    def _tokens_list() -> list[dict]:
        doc = db.get_document("tokens") or {}
        return doc.get("list", [])

    @staticmethod
    def _save_tokens(tokens: list[dict]):
        db.save_document("tokens", {"list": tokens})

    @classmethod
    def panel(cls, inter: disnake.MessageInteraction) -> dict:
        tokens = cls._tokens_list()
        accent = cls._get_accent()

        accounts_text = "\n".join(
            f"{emoji.members} **{t['username']}** (`{t['user_id']}`)"
            for t in tokens
        ) if tokens else f"-# {emoji.warn} Nenhum token cadastrado ainda."

        options = [
            disnake.SelectOption(label=t["username"], value=t["user_id"],
                                 description=f"ID: {t['user_id']}", emoji=emoji.members)
            for t in tokens
        ] if tokens else [
            disnake.SelectOption(label="Nenhuma conta", value="__empty__",
                                 description="Adicione um token primeiro")
        ]

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.members} Tokens de Conta\n"
                    f"-# Painel > Configurações > **Tokens**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Gerencie os tokens de conta do Discord.\n"
                    "**Atenção:** Contas com **2FA (autenticação de dois fatores) ativo NÃO funcionarão** para alterar a URL do servidor.\n"
                    "Apenas contas sem 2FA podem ser usadas na proteção de URL."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"### Contas cadastradas\n{accounts_text}"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(custom_id="Tokens_Select_Action",
                                            placeholder="Selecione uma conta para gerenciar",
                                            options=options, disabled=not tokens)
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Adicionar Token", style=disnake.ButtonStyle.green,
                                      emoji=emoji.plus, custom_id="Tokens_Add"),
                ),
                **accent,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.back, custom_id="Configuracoes_Back")
            ),
        ]
        return {"components": components}

    @classmethod
    def manage_panel(cls, inter: disnake.MessageInteraction, user_id: str) -> dict:
        tokens = cls._tokens_list()
        token_data = next((t for t in tokens if t["user_id"] == user_id), None)
        accent = cls._get_accent()
        if not token_data:
            return cls.panel(inter)

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.members} Gerenciar Conta\n"
                    f"-# Painel > Configurações > Tokens > **{token_data['username']}**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"### Informações da conta\n"
                    f"{emoji.members} **Usuário:** {token_data['username']}\n"
                    f"{emoji.members} **ID:** `{token_data['user_id']}`\n"
                    f"-# Token e senha ocultados por segurança."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Atualizar Token/Senha", style=disnake.ButtonStyle.blurple,
                                      emoji=emoji.edit, custom_id=f"Tokens_Update_{user_id}"),
                    disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red,
                                      emoji=emoji.delete, custom_id=f"Tokens_Remove_{user_id}"),
                ),
                **accent,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.back, custom_id="Tokens_Back")
            ),
        ]
        return {"components": components}

    @staticmethod
    def add_modal() -> disnake.ui.Modal:
        return disnake.ui.Modal(
            title="Adicionar Token de Conta",
            custom_id="Tokens_Modal_Add",
            components=[
                disnake.ui.TextInput(
                    label="Token da Conta",
                    placeholder="Cole aqui o token de conta do Discord...",
                    custom_id="token_value",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=50, max_length=120,
                ),
                disnake.ui.TextInput(
                    label="Senha da Conta",
                    placeholder="Digite a senha da conta Discord (necessária para alterar URL)",
                    custom_id="password_value",
                    style=disnake.TextInputStyle.short,
                    min_length=6, max_length=100, required=True,
                ),
            ],
        )

    @staticmethod
    def update_modal(user_id: str) -> disnake.ui.Modal:
        return disnake.ui.Modal(
            title="Atualizar Token de Conta",
            custom_id=f"Tokens_Modal_Update_{user_id}",
            components=[
                disnake.ui.TextInput(
                    label="Novo Token da Conta",
                    placeholder="Cole aqui o novo token de conta...",
                    custom_id="token_value",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=50, max_length=120,
                ),
                disnake.ui.TextInput(
                    label="Nova Senha da Conta",
                    placeholder="Digite a nova senha da conta Discord",
                    custom_id="password_value",
                    style=disnake.TextInputStyle.short,
                    min_length=6, max_length=100, required=True,
                ),
            ],
        )

    @staticmethod
    async def _send_ephemeral_error(inter: disnake.ModalInteraction, text: str):
        await inter.followup.send(
            components=_error_components(text),
            flags=disnake.MessageFlags(ephemeral=True, is_components_v2=True),
        )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if cid == "Tokens_Add":
            await inter.response.send_modal(self.add_modal())
        elif cid == "Tokens_Back":
            await message.wait(inter, send=False)
            await inter.edit_original_message(**self.panel(inter),
                                              flags=disnake.MessageFlags(is_components_v2=True))
        elif cid == "Configuracoes_Back":
            from modules.settings.cog import Settings
            await message.wait(inter, send=False)
            settings_cog = self.bot.cogs.get("Settings")
            if settings_cog:
                await inter.edit_original_message(components=settings_cog.settings_components(inter),
                                                  flags=disnake.MessageFlags(is_components_v2=True))
        elif cid.startswith("Tokens_Update_"):
            user_id = cid.removeprefix("Tokens_Update_")
            await inter.response.send_modal(self.update_modal(user_id))
        elif cid.startswith("Tokens_Remove_"):
            user_id = cid.removeprefix("Tokens_Remove_")
            tokens = self._tokens_list()
            removed = next((t for t in tokens if t["user_id"] == user_id), None)
            tokens = [t for t in tokens if t["user_id"] != user_id]
            self._save_tokens(tokens)
            await message.wait(inter, send=False)
            panel = self.panel(inter)
            name = removed["username"] if removed else user_id
            panel["components"].insert(0, disnake.ui.ActionRow(
                disnake.ui.Button(label=f"✅ Conta {name} removida com sucesso!",
                                  style=disnake.ButtonStyle.grey, disabled=True, custom_id="__feedback__")
            ))
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Tokens_Select_Action":
            return
        if inter.values[0] == "__empty__":
            await inter.response.defer()
            return
        user_id = inter.values[0]
        await message.wait(inter, send=False)
        panel = self.manage_panel(inter, user_id)
        await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if cid == "Tokens_Modal_Add":
            token = inter.text_values["token_value"].strip()
            password = inter.text_values["password_value"].strip()
            await inter.response.defer(ephemeral=True)
            try:
                user_data = await validate_user_token(token)
            except ValueError:
                await self._send_ephemeral_error(inter,
                    f"### {emoji.warn} Token inválido\nO token informado pertence a um **bot**.\n-# Apenas tokens de conta são aceitos.")
                return
            if not user_data:
                await self._send_ephemeral_error(inter,
                    f"### {emoji.warn} Token inválido\nNão foi possível autenticar o token.\n-# Verifique se está correto.")
                return
            username = f"{user_data['username']}#{user_data['discriminator']}" if user_data.get("discriminator", "0") != "0" else user_data["username"]
            user_id = str(user_data["id"])
            tokens = self._tokens_list()
            existing = next((t for t in tokens if t["user_id"] == user_id), None)
            if existing:
                existing["token"] = token
                existing["password"] = password
                existing["username"] = username
            else:
                tokens.append({"user_id": user_id, "username": username, "token": token, "password": password})
            self._save_tokens(tokens)
            panel = self.panel(inter)
            panel["components"].insert(0, disnake.ui.ActionRow(
                disnake.ui.Button(label=f"✅ Conta {username} adicionada com sucesso!",
                                  style=disnake.ButtonStyle.grey, disabled=True, custom_id="__feedback__")
            ))
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        elif cid.startswith("Tokens_Modal_Update_"):
            user_id = cid.removeprefix("Tokens_Modal_Update_")
            token = inter.text_values["token_value"].strip()
            password = inter.text_values["password_value"].strip()
            await inter.response.defer(ephemeral=True)
            try:
                user_data = await validate_user_token(token)
            except ValueError:
                await self._send_ephemeral_error(inter,
                    f"### {emoji.warn} Token inválido\nToken de bot não é permitido.")
                return
            if not user_data:
                await self._send_ephemeral_error(inter,
                    f"### {emoji.warn} Token inválido\nNão foi possível autenticar.")
                return
            new_user_id = str(user_data["id"])
            username = f"{user_data['username']}#{user_data['discriminator']}" if user_data.get("discriminator", "0") != "0" else user_data["username"]
            tokens = self._tokens_list()
            if new_user_id != user_id:
                tokens = [t for t in tokens if t["user_id"] != user_id]
            target = next((t for t in tokens if t["user_id"] == new_user_id), None)
            if target:
                target["token"] = token
                target["password"] = password
                target["username"] = username
            else:
                tokens.append({"user_id": new_user_id, "username": username, "token": token, "password": password})
            self._save_tokens(tokens)
            panel = self.manage_panel(inter, new_user_id)
            panel["components"].insert(0, disnake.ui.ActionRow(
                disnake.ui.Button(label=f"✅ Token de {username} atualizado!",
                                  style=disnake.ButtonStyle.grey, disabled=True, custom_id="__feedback__")
            ))
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    bot.add_cog(TokensPanel(bot))