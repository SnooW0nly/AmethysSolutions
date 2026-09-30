import io
import asyncio
import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from . import helpers


# ──────────────────────────────────────────
#  MODALS
# ──────────────────────────────────────────

class CriarKeysModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Keys",
            custom_id="Keys_CriarModal",
            components=[
                disnake.ui.TextInput(
                    label="Quantidade",
                    custom_id="quantidade",
                    placeholder="Ex: 50",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=4,
                ),
                disnake.ui.TextInput(
                    label="Prefixo e Sufixo (separados por vírgula)",
                    custom_id="prefixo_sufixo",
                    placeholder="Ex: KEY,Subs",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value="KEY,Subs",
                ),
                disnake.ui.TextInput(
                    label="Usos por key (-1 = ilimitado)",
                    custom_id="usos",
                    placeholder="Ex: 1",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value="1",
                ),
                disnake.ui.TextInput(
                    label="Expira em horas (0 = nunca)",
                    custom_id="expira_horas",
                    placeholder="Ex: 72",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value="0",
                ),
                disnake.ui.TextInput(
                    label="Categoria",
                    custom_id="categoria",
                    placeholder="Ex: vip, mensal, teste",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value="default",
                ),
            ],
        )


class ConfigCanaisModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        super().__init__(
            title="Configurar Mensagens do Sistema",
            custom_id="Keys_ConfigMsgModal",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem de sucesso",
                    custom_id="msg_sucesso",
                    placeholder="Ex: 🎉 Key resgatada! Bem-vindo(a).",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    value=config.get("msg_sucesso", ""),
                    max_length=300,
                ),
                disnake.ui.TextInput(
                    label="Mensagem de key inválida",
                    custom_id="msg_invalida",
                    placeholder="Ex: ❌ Key inválida. Tente novamente.",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=config.get("msg_invalida", ""),
                    max_length=200,
                ),
                disnake.ui.TextInput(
                    label="Mensagem de key expirada",
                    custom_id="msg_expirada",
                    placeholder="Ex: ⏰ Esta key expirou.",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=config.get("msg_expirada", ""),
                    max_length=200,
                ),
                disnake.ui.TextInput(
                    label="Mensagem de limite atingido",
                    custom_id="msg_limite",
                    placeholder="Ex: 🚫 Limite de usos atingido.",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=config.get("msg_limite", ""),
                    max_length=200,
                ),
            ],
        )


# ──────────────────────────────────────────
#  COG
# ──────────────────────────────────────────

class KeysCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._coletores: dict[int, asyncio.Task] = {}

    # ── Helpers de cor ────────────────────

    @staticmethod
    def _container_kwargs() -> dict:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        kwargs = {}
        if primary_color_hex:
            kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        return kwargs

    # ── PAINÉIS ESTÁTICOS ─────────────────

    @staticmethod
    def Painel() -> list:
        ckw = KeysCog._container_kwargs()
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        stats = helpers.estatisticas()

        canal_resgate = config.get("canal_resgate")
        canal_logs = config.get("canal_logs")
        cargo = config.get("cargo_resgate")

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.message} **Canal de resgate:** {f'<#{canal_resgate}>' if canal_resgate else '`Não configurado`'}\n"
            f"{emoji.role} **Cargo pós resgate:** {f'<@&{cargo}>' if cargo else '`Não configurado`'}\n"
            f"{emoji.textc} **Canal de logs:** {f'<#{canal_logs}>' if canal_logs else '`Não configurado`'}\n"
        )

        stats_txt = (
            f"{emoji.plus} **Keys disponíveis:** `{stats['disponiveis']}`\n"
            f"{emoji.correct} **Keys usadas:** `{stats['usadas']}`\n"
            f"{emoji.delete} **Keys expiradas:** `{stats['expiradas']}`\n"
            f"{emoji.commands} **Total:** `{stats['total']}`"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Automações > **Sistema de Keys**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure o sistema de resgate de keys do servidor."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.Section(
                    disnake.ui.TextDisplay(resumo),
                    accessory=disnake.ui.Button(
                        label="On" if ativado else "Off",
                        style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.red,
                        emoji=emoji.power,
                        custom_id="Keys_ToggleAtivo",
                    ),
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(stats_txt),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Canal Resgate", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id="Keys_SetCanalResgate"),
                    disnake.ui.Button(label="Canal Logs", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id="Keys_SetCanalLogs"),
                    disnake.ui.Button(label="Cargo", style=disnake.ButtonStyle.secondary, emoji=emoji.role, custom_id="Keys_SetCargo"),
                    disnake.ui.Button(label="Mensagens", style=disnake.ButtonStyle.secondary, emoji=emoji.edit, custom_id="Keys_ConfigMensagens"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Criar Keys", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Keys_CriarKeys"),
                    disnake.ui.Button(label="Gerenciar Keys", style=disnake.ButtonStyle.secondary, emoji=emoji.commands, custom_id="Keys_GerenciarKeys"),
                    disnake.ui.Button(label="Limpar Expiradas", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Keys_LimparExpiradas", disabled=stats["expiradas"] == 0),
                    disnake.ui.Button(label="Resetar Tudo", style=disnake.ButtonStyle.red, emoji=emoji.warn, custom_id="Keys_ResetarTudo", disabled=stats["total"] == 0),
                ),
                **ckw,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Keys_VoltarAutomacoes"),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        stats = helpers.estatisticas()

        canal_resgate = config.get("canal_resgate")
        canal_logs = config.get("canal_logs")
        cargo = config.get("cargo_resgate")

        embed = disnake.Embed(title="🔑 Sistema de Keys")
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        embed.add_field(
            name="⚙️ Configurações",
            value=(
                f"{emoji.on if ativado else emoji.off} Status: **{'Ativado' if ativado else 'Desativado'}**\n"
                f"Canal de resgate: {f'<#{canal_resgate}>' if canal_resgate else '`Não configurado`'}\n"
                f"Cargo pós resgate: {f'<@&{cargo}>' if cargo else '`Não configurado`'}\n"
                f"Canal de logs: {f'<#{canal_logs}>' if canal_logs else '`Não configurado`'}"
            ),
            inline=False,
        )
        embed.add_field(
            name="📊 Estatísticas",
            value=(
                f"Disponíveis: `{stats['disponiveis']}` | Usadas: `{stats['usadas']}`\n"
                f"Expiradas: `{stats['expiradas']}` | Total: `{stats['total']}`"
            ),
            inline=False,
        )

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="On" if ativado else "Off",
                    style=disnake.ButtonStyle.green if ativado else disnake.ButtonStyle.red,
                    emoji=emoji.power,
                    custom_id="Keys_ToggleAtivo",
                ),
                disnake.ui.Button(label="Canal Resgate", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id="Keys_SetCanalResgate"),
                disnake.ui.Button(label="Canal Logs", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id="Keys_SetCanalLogs"),
                disnake.ui.Button(label="Cargo", style=disnake.ButtonStyle.secondary, emoji=emoji.role, custom_id="Keys_SetCargo"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Keys", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Keys_CriarKeys"),
                disnake.ui.Button(label="Gerenciar Keys", style=disnake.ButtonStyle.secondary, emoji=emoji.commands, custom_id="Keys_GerenciarKeys"),
                disnake.ui.Button(label="Mensagens", style=disnake.ButtonStyle.secondary, emoji=emoji.edit, custom_id="Keys_ConfigMensagens"),
                disnake.ui.Button(label="Limpar Expiradas", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Keys_LimparExpiradas"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Keys_VoltarAutomacoes"),
            ),
        ]
        return embed, components

    @staticmethod
    def PainelGerenciar(pagina: int = 0) -> list:
        ckw = KeysCog._container_kwargs()
        todas = helpers.listar_keys()

        if not todas:
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Sistema de Keys > **Gerenciar**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(f"{emoji.warn} Não há keys cadastradas."),
                    **ckw,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Keys_VoltarPainel"),
                ),
            ]

        por_pagina = 23
        inicio = pagina * por_pagina
        fim = min(inicio + por_pagina, len(todas))
        pagina_keys = todas[inicio:fim]

        opcoes = [
            disnake.SelectOption(
                label=key[:90],
                value=key,
                description=f"Usos: {meta.get('usos_realizados',0)}/{meta.get('usos_maximos',1)} | Cat: {meta.get('categoria','default')}",
                emoji=emoji.delete,
            )
            for key, meta in pagina_keys
        ]
        if pagina > 0:
            opcoes.append(disnake.SelectOption(label="◀️ Página anterior", value=f"__prev__{pagina - 1}__"))
        if fim < len(todas):
            opcoes.append(disnake.SelectOption(label="▶️ Próxima página", value=f"__next__{pagina + 1}__"))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Sistema de Keys > **Gerenciar** (página {pagina + 1})"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Selecione uma key para **deletá-la**.\n-# Exibindo {inicio+1}–{fim} de {len(todas)} keys."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione a key para deletar",
                        custom_id="Keys_DeletarSelect",
                        options=opcoes,
                    )
                ),
                **ckw,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Keys_VoltarPainel"),
            ),
        ]

    @staticmethod
    def PainelSetCanal(tipo: str) -> list:
        ckw = KeysCog._container_kwargs()
        label = "resgate" if tipo == "resgate" else "logs"
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Sistema de Keys > **Canal de {label.capitalize()}**"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder=f"Selecione o canal de {label}...",
                        custom_id=f"Keys_CanalSelect_{tipo}",
                        min_values=1, max_values=1,
                        channel_types=[disnake.ChannelType.text],
                    )
                ),
                **ckw,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Keys_VoltarPainel"),
            ),
        ]

    @staticmethod
    def PainelSetCargo() -> list:
        ckw = KeysCog._container_kwargs()
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Sistema de Keys > **Cargo Pós Resgate**"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione o cargo que será dado ao resgatar...",
                        custom_id="Keys_CargoSelect",
                        min_values=1, max_values=1,
                    )
                ),
                **ckw,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Keys_VoltarPainel"),
            ),
        ]

    # ── PAINEL DE RESGATE (publicado no canal) ─────

    @staticmethod
    def _painel_resgate_msg(config: dict) -> dict:
        """Monta kwargs para enviar o painel de resgate no canal."""
        msg_sucesso = config.get("msg_sucesso") or "🎉 Key resgatada com sucesso! Seu acesso foi liberado."
        msg_invalida = config.get("msg_invalida") or f"{emoji.wrong} Key inválida. Verifique e tente novamente."
        msg_expirada = config.get("msg_expirada") or "⏰ Esta key expirou."
        msg_limite = config.get("msg_limite") or "🚫 Esta key atingiu o limite de usos."

        mode = db.get_document("custom_mode").get("mode")

        if mode == "embed":
            embed = disnake.Embed(
                title="🔑 Resgate sua Key",
                description=(
                    "Insira sua key **no chat** para liberar seu acesso.\n"
                    "Keys adquiridas de revendedores não são nossa responsabilidade."
                ),
                color=0x5865F2,
            )
            embed.add_field(name="📌 Como usar", value="1. Digite sua key no chat\n2. Aguarde a confirmação\n3. Aproveite!")
            embed.add_field(name="🔒 Formato", value="`KEY-XXXX-XXXX-XXXX-XXXX-Subs`")
            embed.set_footer(text="Sistema de Keys")
            return {"embed": embed}
        else:
            ckw = KeysCog._container_kwargs()
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        "# 🔑 Resgate sua Key\n"
                        "-# Insira sua key no chat para liberar seu acesso."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Digite sua key diretamente **neste canal**.\n"
                        "Keys adquiridas de revendedores não são de nossa responsabilidade."
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.TextDisplay(f"**Formato:** `KEY-XXXX-XXXX-XXXX-XXXX-Subs`"),
                    **ckw,
                )
            ]
            return {"components": components, "flags": disnake.MessageFlags(is_components_v2=True)}

    # ── COLETOR DE MENSAGENS ──────────────

    async def _iniciar_coletor(self, canal: disnake.TextChannel, config: dict):
        canal_id = canal.id
        await self._parar_coletor(canal_id)

        canal_logs_id = config.get("canal_logs")
        canal_logs = self.bot.get_channel(int(canal_logs_id)) if canal_logs_id else None
        apagar = config.get("apagar_tentativas", True)

        async def _loop():
            def check(m: disnake.Message):
                return not m.author.bot and m.channel.id == canal_id

            while True:
                try:
                    msg: disnake.Message = await self.bot.wait_for("message", check=check, timeout=None)
                    cfg = helpers.carregar_config()
                    if not cfg.get("ativado"):
                        break

                    key_str = msg.content.strip()
                    sucesso, motivo = helpers.resgatar_key(key_str, str(msg.author.id))

                    # Monta resposta
                    textos = {
                        "ok": cfg.get("msg_sucesso") or "🎉 Key resgatada com sucesso! Seu acesso foi liberado.",
                        "nao_encontrada": cfg.get("msg_invalida") or f"{emoji.wrong} Key inválida. Verifique e tente novamente.",
                        "expirada": cfg.get("msg_expirada") or "⏰ Esta key expirou.",
                        "limite_atingido": cfg.get("msg_limite") or "🚫 Esta key atingiu o limite de usos.",
                        "inativa": "🔒 Esta key foi desativada.",
                        "ja_resgatada": "🔄 Você já resgatou esta key anteriormente.",
                    }
                    texto_resposta = textos.get(motivo if not sucesso else "ok", "❓ Erro desconhecido.")

                    # Atribui cargo em caso de sucesso
                    if sucesso:
                        cargo_id = cfg.get("cargo_resgate")
                        if cargo_id:
                            cargo = msg.guild.get_role(int(cargo_id))
                            if cargo:
                                try:
                                    await msg.author.add_roles(cargo, reason="Key resgatada")
                                except disnake.Forbidden:
                                    pass

                    resposta = await msg.reply(texto_resposta, delete_after=10)

                    # Log
                    if canal_logs:
                        cor = 0x57F287 if sucesso else 0xED4245
                        titulo = f"{emoji.correct} Key Resgatada" if sucesso else f"{emoji.wrong} Tentativa Falhou"
                        log = disnake.Embed(title=titulo, color=cor)
                        log.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
                        log.add_field(name="👤 Usuário", value=msg.author.mention, inline=True)
                        log.add_field(name="🆔 ID", value=f"`{msg.author.id}`", inline=True)
                        log.add_field(name="🔑 Key", value=f"||`{key_str}`||", inline=False)
                        if not sucesso:
                            log.add_field(name="📌 Motivo", value=f"`{motivo}`", inline=True)
                        await canal_logs.send(embed=log)

                    # Apaga tentativa
                    if apagar:
                        await asyncio.sleep(1)
                        try:
                            await msg.delete()
                        except Exception:
                            pass

                except asyncio.CancelledError:
                    break
                except Exception:
                    continue

        task = asyncio.create_task(_loop())
        self._coletores[canal_id] = task

    async def _parar_coletor(self, canal_id: int):
        task = self._coletores.pop(canal_id, None)
        if task:
            task.cancel()

    async def _publicar_canal_resgate(self, canal: disnake.TextChannel):
        config = helpers.carregar_config()
        try:
            await canal.purge(limit=20)
        except disnake.Forbidden:
            pass
        kwargs = self._painel_resgate_msg(config)
        await canal.send(**kwargs)
        await self._iniciar_coletor(canal, config)

    @commands.Cog.listener()
    async def on_ready(self):
        config = helpers.carregar_config()
        if config.get("ativado") and config.get("canal_resgate"):
            canal = self.bot.get_channel(int(config["canal_resgate"]))
            if canal:
                await self._iniciar_coletor(canal, config)

    # ── LISTENERS ────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Keys_"):
            return

        if cid == "Keys_VoltarAutomacoes":
            await inter.response.defer(ephemeral=True)
            mode = db.get_document("custom_mode").get("mode")
            from modules.automations.cog import AutomationModulesCog
            if mode == "embed":
                embed, components = AutomationModulesCog.PainelEmbed()
                await inter.delete_original_message()
                await inter.followup.send(embed=embed, components=components, ephemeral=True)
            else:
                from functions.message import message
                await message.wait(inter, send=False)
                components = AutomationModulesCog.PainelComponents()
                await inter.delete_original_message()
                await inter.followup.send(components=components, ephemeral=True)
            return

        if cid == "Keys_VoltarPainel":
            await inter.response.defer()
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            return

        if cid == "Keys_ToggleAtivo":
            await inter.response.defer()
            config = helpers.carregar_config()
            novo = not config.get("ativado", False)
            config["ativado"] = novo
            helpers.salvar_config(config)

            if novo:
                canal_id = config.get("canal_resgate")
                if canal_id:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        await self._publicar_canal_resgate(canal)
            else:
                canal_id = config.get("canal_resgate")
                if canal_id:
                    await self._parar_coletor(int(canal_id))

            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            return

        if cid == "Keys_SetCanalResgate":
            await inter.response.defer()
            await inter.edit_original_message(components=self.PainelSetCanal("resgate"))
            return

        if cid == "Keys_SetCanalLogs":
            await inter.response.defer()
            await inter.edit_original_message(components=self.PainelSetCanal("logs"))
            return

        if cid == "Keys_SetCargo":
            await inter.response.defer()
            await inter.edit_original_message(components=self.PainelSetCargo())
            return

        if cid == "Keys_ConfigMensagens":
            await inter.response.send_modal(ConfigCanaisModal())
            return

        if cid == "Keys_CriarKeys":
            await inter.response.send_modal(CriarKeysModal())
            return

        if cid == "Keys_GerenciarKeys":
            await inter.response.defer()
            await inter.edit_original_message(components=self.PainelGerenciar(0))
            return

        if cid == "Keys_LimparExpiradas":
            await inter.response.defer()
            deletadas = helpers.deletar_keys_expiradas()
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            await inter.followup.send(f"♻️ **{deletadas}** keys expiradas removidas.", ephemeral=True)
            return

        if cid == "Keys_ResetarTudo":
            await inter.response.defer()
            total = helpers.resetar_todas_keys()
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            await inter.followup.send(f"💣 **{total}** keys deletadas. Banco resetado.", ephemeral=True)
            return

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Keys_"):
            return

        if cid == "Keys_CanalSelect_resgate":
            await inter.response.defer()
            config = helpers.carregar_config()
            config["canal_resgate"] = inter.values[0]
            helpers.salvar_config(config)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            return

        if cid == "Keys_CanalSelect_logs":
            await inter.response.defer()
            config = helpers.carregar_config()
            config["canal_logs"] = inter.values[0]
            helpers.salvar_config(config)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            return

        if cid == "Keys_CargoSelect":
            await inter.response.defer()
            config = helpers.carregar_config()
            config["cargo_resgate"] = inter.values[0]
            helpers.salvar_config(config)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            return

        if cid == "Keys_DeletarSelect":
            await inter.response.defer()
            valor = inter.values[0]
            if valor.startswith("__prev__") or valor.startswith("__next__"):
                pagina = int(valor.replace("__prev__", "").replace("__next__", "").replace("__", ""))
                await inter.edit_original_message(components=self.PainelGerenciar(pagina))
                return
            helpers.deletar_key(valor)
            await inter.edit_original_message(components=self.PainelGerenciar(0))
            await inter.followup.send(f"{emoji.correct} Key `{valor}` deletada.", ephemeral=True)
            return

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("Keys_"):
            return

        if cid == "Keys_CriarModal":
            await inter.response.defer(ephemeral=True)
            try:
                quantidade = int(inter.text_values.get("quantidade", "1"))
                ps = inter.text_values.get("prefixo_sufixo", "KEY,Subs").split(",")
                prefixo = ps[0].strip() if ps else "KEY"
                sufixo = ps[1].strip() if len(ps) > 1 else "Subs"
                usos = int(inter.text_values.get("usos", "1"))
                exp_h = int(inter.text_values.get("expira_horas", "0"))
                categoria = (inter.text_values.get("categoria") or "default").strip()
            except (ValueError, TypeError):
                await inter.edit_original_response(content=f"{emoji.wrong} Valores inválidos no formulário.")
                return

            novas = helpers.criar_keys(
                quantidade=quantidade,
                prefixo=prefixo,
                sufixo=sufixo,
                usos_maximos=usos,
                expira_em_horas=exp_h if exp_h > 0 else None,
                categoria=categoria,
                criado_por=str(inter.author),
            )

            arquivo = io.BytesIO("\n".join(novas).encode())
            await inter.edit_original_response(
                content=f"{emoji.correct} **{len(novas)}** key(s) criadas! Categoria: `{categoria}`",
                file=disnake.File(arquivo, filename=f"keys_{categoria}_{len(novas)}.txt"),
            )
            try:
                dm_arq = io.BytesIO("\n".join(novas).encode())
                await inter.author.send(
                    content=f"🔑 **{len(novas)}** keys — categoria `{categoria}`:",
                    file=disnake.File(dm_arq, filename=f"keys_{categoria}_{len(novas)}.txt"),
                )
            except disnake.Forbidden:
                pass
            return

        if cid == "Keys_ConfigMsgModal":
            await inter.response.defer()
            config = helpers.carregar_config()
            for campo in ("msg_sucesso", "msg_invalida", "msg_expirada", "msg_limite"):
                valor = inter.text_values.get(campo, "").strip()
                if valor:
                    config[campo] = valor
            helpers.salvar_config(config)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
            return


def setup(bot: commands.Bot):
    bot.add_cog(KeysCog(bot))