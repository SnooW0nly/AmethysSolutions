import disnake
from disnake.ext import commands
import re

from ..anunciar import Anunciar
from functions.message import message
from functions.database import database
from functions.emoji import emoji
from functions.utils import utils

class Buttons(commands.Cog):
    description_names = {
        "disabled": "Botão desabilitado",
        "action": "Botão de ação (cargos)",
        "message": "Botão de mensagem efêmera",
        "url": "Botão de URL",
        "audio": "Botão de áudio",
    }
    ACTION_DESCRIPTIONS = {
        "addrole": "Adiciona/remove um cargo definido ao usuário.",
        "removerole": "Remove um cargo definido ao usuário.",
        "message": "Envia uma mensagem efêmera.",
        "url": "Redireciona o usuário para uma URL.",
        "audio": "Envia um arquivo de áudio efêmero ao usuário.",
        "disabled": "Desabilita o botão.",
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    STYLE_MAPPING = {
        "gray": disnake.ButtonStyle.gray,
        "grey": disnake.ButtonStyle.gray,
        "green": disnake.ButtonStyle.green,
        "red": disnake.ButtonStyle.red,
        "blue": disnake.ButtonStyle.blurple,
        "url": disnake.ButtonStyle.url,
    }

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc or " " in parsed.netloc:
                return False
            if "." not in parsed.netloc:
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def _get_cfg():
        return database.get_document("messages_anunciar")

    @staticmethod
    def _save_cfg(cfg: dict):
        database.save_document("messages_anunciar", {}, cfg)

    @staticmethod
    def _find_button(cfg: dict, button_id: str):
        buttons = cfg.get("message", {}).get("buttons", [])
        return next((b for b in buttons if b.get("id") == button_id), None)

    @staticmethod
    def _style_from_str(style: str) -> disnake.ButtonStyle:
        return Buttons.STYLE_MAPPING.get(style or "gray", disnake.ButtonStyle.gray)

    @staticmethod
    def validar_emoji(emoji_input: str, bot: commands.Bot) -> bool:
        if not emoji_input or not emoji_input.strip():
            return True  # Empty is considered valid (optional)

        emoji_str = emoji_input.strip()

        # Handle shortnames from functions.emoji
        if hasattr(emoji, emoji_str):
            emoji_str = getattr(emoji, emoji_str)

        parsed_emoji = utils.get_emoji_from_string(emoji_str)

        if not parsed_emoji:
            return False

        # If it's a custom emoji (has an ID), check if the bot can access it
        if parsed_emoji.id:
            return bot.get_emoji(parsed_emoji.id) is not None

        # If no ID, it's a unicode emoji, which we consider valid if parsable
        return True

    @staticmethod
    def processar_emoji(emoji_input: str):
        if not emoji_input or not emoji_input.strip():
            return None
        
        emoji_str = emoji_input.strip()

        # Handle shortnames from functions.emoji
        if hasattr(emoji, emoji_str):
            emoji_str = getattr(emoji, emoji_str)
        
        return utils.get_emoji_from_string(emoji_str)

    class RegistrarBotao(disnake.ui.Modal):
        def __init__(self, action: str, id: str = None):
            cfg = Buttons._get_cfg()
            self.action = action
            self.id = id
            button = Buttons._find_button(cfg, id) if id else None

            super().__init__(
                title="Registrar botão",
                custom_id="Anunciar_Botao_RegistrarBotao",
                components=[
                    disnake.ui.TextInput(
                        label="Label",
                        custom_id="label",
                        placeholder="Label do botão (opcional)",
                        required=False,
                        value=button.get("label", "") if button else ""
                    ),
                    disnake.ui.TextInput(
                        label="Emoji",
                        custom_id="emoji",
                        placeholder="Emoji do botão (opcional)",
                        required=False,
                        value=button.get("button", {}).get("emoji", "") if button else ""
                    ),
                ]
            )

        async def callback(self, inter: disnake.ModalInteraction):
            cfg = Buttons._get_cfg()
            id = utils.gerar_id()
            action = self.action
            label_input = inter.text_values.get("label", "").strip()
            emoji_input = inter.text_values.get("emoji", "").strip()

            if not label_input and not emoji_input:
                await message.error(inter, "Você deve definir um label ou um emoji para o botão.", send=True)
                return

            if action == "create" and len(cfg.get("message", {}).get("buttons", [])) >= 5:
                await message.error(inter, "Você atingiu o limite de botões. (5)", send=True)
                return

            if emoji_input and not Buttons.validar_emoji(emoji_input, inter.bot):
                await inter.response.send_message(
                    f"{emoji.warn} Emoji inválido. Use Unicode, `<:nome:id>` válido do servidor, ou um nome da classe.",
                    ephemeral=True,
                )
                return

            if action == "create":
                cfg.setdefault("message", {}).setdefault("buttons", []).append({
                    "id": id,
                    "label": label_input,
                    "button": {
                        "type": "disabled",
                        "emoji": emoji_input if emoji_input else None,
                        "url": None,
                        "style": "gray",
                        "disabled": True,
                        "custom_id": None,
                        "action": {}
                    }
                })
            
            elif action == "edit":
                id = self.id
                button = Buttons._find_button(cfg, id)
                if not button: return
                button["label"] = label_input
                button["button"]["emoji"] = emoji_input if emoji_input else None
            
            Buttons._save_cfg(cfg)
            components = Buttons.Button.button(id)
            await inter.response.edit_message(components=components)

    class EditarURLModal(disnake.ui.Modal):
        def __init__(self, id: str):
            self.id = id
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, id)
            url_value = (button or {}).get("button", {}).get("url") if button else None

            super().__init__(
                title="Editar URL",
                custom_id="Anunciar_Botao_EditarURLModal",
                components=[
                    disnake.ui.TextInput(
                        label="URL",
                        custom_id="url",
                        placeholder="https://exemplo.com",
                        required=True,
                        value=url_value or ""
                    ),
                ]
            )

        async def callback(self, inter: disnake.ModalInteraction):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, self.id)
            if not button: return
            url = inter.text_values.get("url", "").strip()
            if not Buttons._is_valid_url(url):
                await inter.response.send_message(f"{emoji.wrong} URL inválida. Use http(s)://", ephemeral=True)
                return
            data = button.setdefault("button", {})
            data["type"] = "url"
            data["url"] = url
            data["action"] = {}
            data["disabled"] = False
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

    class EditarMensagemModal(disnake.ui.Modal):
        def __init__(self, id: str):
            self.id = id
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, id)
            msg_value = ((button or {}).get("button", {}).get("action", {}) or {}).get("message") if button else None

            super().__init__(
                title="Editar mensagem efêmera",
                custom_id="Anunciar_Botao_EditarMensagemModal",
                components=[
                    disnake.ui.TextInput(
                        label="Mensagem",
                        custom_id="message",
                        placeholder="Texto da mensagem efêmera",
                        required=True,
                        value=msg_value or "",
                        style=disnake.TextInputStyle.paragraph
                    ),
                ]
            )

        async def callback(self, inter: disnake.ModalInteraction):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, self.id)
            if not button: return
            text = inter.text_values.get("message", "").strip()
            data = button.setdefault("button", {})
            data["type"] = "message"
            data["url"] = None
            data["action"] = {"message": text}
            data["disabled"] = False
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

    class EditarAudioModal(disnake.ui.Modal):
        def __init__(self, id: str):
            self.id = id
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, id)
            audio_value = ((button or {}).get("button", {}).get("action", {}) or {}).get("audio_url") if button else None
            placeholder = audio_value or "https://exemplo.com/audio.mp3"

            super().__init__(
                title="Definir URL do áudio",
                custom_id="Anunciar_Botao_EditarAudioModal",
                components=[
                    disnake.ui.TextInput(
                        label="URL do arquivo de áudio",
                        custom_id="audio_url",
                        placeholder=placeholder,
                        required=False,
                        value="",
                        style=disnake.TextInputStyle.short,
                        max_length=500,
                    ),
                ]
            )

        async def callback(self, inter: disnake.ModalInteraction):
            import re
            AUDIO_URL_RE = re.compile(
                r"https?://\S+\.(?:mp3|ogg|wav|flac|m4a|webm)(?:\?[^\s]*)?",
                re.IGNORECASE,
            )
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, self.id)
            if not button: return

            url = inter.text_values.get("audio_url", "").strip()

            # Se o usuário deixou vazio, mantém a URL já salva (se houver)
            if not url:
                existing = ((button.get("button", {}).get("action") or {}).get("audio_url")) or ""
                if not existing:
                    await inter.response.send_message(
                        f"{emoji.wrong} Digite uma URL ou envie um arquivo de áudio no chat.",
                        ephemeral=True,
                    )
                    return
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))
                return

            if not AUDIO_URL_RE.match(url):
                await inter.response.send_message(
                    f"{emoji.wrong} URL inválida. Use um link direto para um arquivo de áudio (.mp3, .ogg, .wav, .flac, .m4a, .webm).",
                    ephemeral=True,
                )
                return

            data = button.setdefault("button", {})
            data["type"] = "audio"
            data["url"] = None
            data["action"] = {"audio_url": url, "audio_data": None, "audio_filename": None}
            data["disabled"] = False
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

    @staticmethod
    def buttons():
        cfg = Buttons._get_cfg()
        buttons = cfg.get("message", {}).get("buttons", [])
        
        options = []
        for b in buttons:
            label = b.get("label")
            emoji_raw = b.get("button", {}).get("emoji")
            processed_emoji = Buttons.processar_emoji(emoji_raw) if emoji_raw else None
            
            option_label = label or "Nenhum label"
            
            options.append(disnake.SelectOption(
                label=option_label,
                value=b.get("id"),
                emoji=processed_emoji,
                description=Buttons.description_names.get(b.get("button", {}).get("type", "disabled"), "Botão")
            ))

        if not options:
            options.append(disnake.SelectOption(label="Nenhum botão registrado", value="none", description="Nenhum botão registrado"))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Anunciar > Botões"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Configure os botões que irão aparecer na mensagem.\nPara configurar um botão, selecione-o na lista abaixo."),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Quantidade de botões registrados:** `{len(buttons)}`\n-# A quantidade de botões registrados é limitada a `5`."),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione o botão para configurar",
                        custom_id="Anunciar_Botao_SelecionarBotao",
                        options=options,
                        disabled=len(buttons) == 0
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar botão",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id="Anunciar_Botao_AdicionarBotao",
                        disabled=len(buttons) == 5
                    ),
                    disnake.ui.Button(
                        label="Apagar todos",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Anunciar_ApagarBotoes",
                        disabled=len(buttons) == 0
                    )
                )
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial")),
        ]

    class Button:
        @staticmethod
        def button(id: str):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, id)
            if not button: return None

            label = button.get("label", None)
            data = button.get("button", {})
            btn_type = data.get("type", "disabled")
            emoji_raw = data.get("emoji")
            emojiButton = Buttons.processar_emoji(emoji_raw) if emoji_raw else None
            url = data.get("url")
            style = Buttons._style_from_str(data.get("style"))
            style_str = data.get("style") or "gray"  # Usar string para comparação

            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Anunciar > Botões > {button.get('label')}"),
                    disnake.ui.Separator(),
                    disnake.ui.Section(
                        disnake.ui.TextDisplay(f"**Label do botão:** `{label or 'Nenhum label'}`\n**Emoji do botão:** {emojiButton if emojiButton else '`Nenhum emoji`'}"),
                        accessory=disnake.ui.Button(label=label, emoji=emojiButton, disabled=True, style=style, url=url)
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(f"**Tipo do botão:** `{Buttons.description_names.get(btn_type, 'Botão desabilitado')}`"),
                    disnake.ui.ActionRow(
                        disnake.ui.StringSelect(
                            placeholder="Selecione o estilo do botão",
                            custom_id=f"Anunciar_Botao_Estilo_{id}",
                            options=[
                                disnake.SelectOption(label="Cinza", value="gray", emoji=emoji.gray, default=style_str == "gray" or style_str == "grey"),
                                disnake.SelectOption(label="Verde", value="green", emoji=emoji.green, default=style_str == "green"),
                                disnake.SelectOption(label="Vermelho", value="red", emoji=emoji.red, default=style_str == "red"),
                                disnake.SelectOption(label="Azul", value="blue", emoji=emoji.blue, default=style_str == "blue"),
                            ]
                        )
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Editar botão", emoji=emoji.edit, custom_id=f"Anunciar_Botao_EditarBotao_{id}", style=disnake.ButtonStyle.blurple),
                        disnake.ui.Button(label="Editar ações", emoji=emoji.route, custom_id=f"Anunciar_Botao_EditarAcoes_{id}"),
                        disnake.ui.Button(label="Apagar botão", emoji=emoji.delete, custom_id=f"Anunciar_Botao_ApagarBotao_{id}", style=disnake.ButtonStyle.red)
                    )
                ),
                disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id=f"Anunciar_DefinirBotoes")),
            ]

        @staticmethod
        def acoes(id: str, inter: disnake.MessageInteraction):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, id)
            if not button: return None

            select_button = None
            data = button.get("button", {})
            current_type = data.get("type")
            action_data = data.get("action") or {}
            action_type = action_data.get("type")

            def action_select():
                return disnake.ui.StringSelect(
                    custom_id=f"Anunciar_Botao_AlterarAcoes_{id}",
                    placeholder="Selecione a ação para ativar",
                    options=[
                        disnake.SelectOption(label="Dar Cargo (Toggle)", emoji=emoji.plus, value="DarCargo", default=(current_type == "action" and action_type == "addrole"), description=Buttons.ACTION_DESCRIPTIONS["addrole"]),
                        disnake.SelectOption(label="Remover Cargo", emoji=emoji.minus, value="RemoverCargo", default=(current_type == "action" and action_type == "removerole"), description=Buttons.ACTION_DESCRIPTIONS["removerole"]),
                        disnake.SelectOption(label="Mensagem Efêmera", emoji=emoji.message, value="MensagemEferema", default=(current_type == "message"), description=Buttons.ACTION_DESCRIPTIONS["message"]),
                        disnake.SelectOption(label="Áudio", emoji=emoji.message, value="Audio", default=(current_type == "audio"), description=Buttons.ACTION_DESCRIPTIONS["audio"]),
                        disnake.SelectOption(label="URL", emoji=emoji.route, value="URL", default=(current_type == "url"), description=Buttons.ACTION_DESCRIPTIONS["url"]),
                        disnake.SelectOption(label="Desativado", emoji=emoji.wrong, value="Desativado", default=(current_type == "disabled"), description=Buttons.ACTION_DESCRIPTIONS["disabled"]),
                    ]
                )

            if current_type == "action":
                if action_type == "addrole" or action_type == "removerole":
                    role_id = action_data.get("role")
                    role = inter.guild.get_role(int(role_id)) if role_id else None
                    select_button = disnake.ui.RoleSelect(
                        placeholder="Selecione o cargo para adicionar" if action_type == "addrole" else "Selecione o cargo para remover",
                        custom_id=f"Anunciar_Botao_AdicionarCargo_{id}" if action_type == "addrole" else f"Anunciar_Botao_RemoverCargo_{id}",
                        default_values=[role] if role else []
                    )
                    
            elif current_type == "url":
                select_button = disnake.ui.Button(label="Editar URL", emoji=emoji.edit, custom_id=f"Anunciar_Botao_EditarURL_{id}", style=disnake.ButtonStyle.blurple)
            
            elif current_type == "message":
                select_button = disnake.ui.Button(label="Editar mensagem", emoji=emoji.edit, custom_id=f"Anunciar_Botao_EditarMensagem_{id}", style=disnake.ButtonStyle.blurple)

            elif current_type == "audio":
                audio_action = data.get("action") or {}
                audio_filename = audio_action.get("audio_filename") or audio_action.get("audio_url", "")
                audio_label = (audio_filename.split("/")[-1].split("?")[0] or "Nenhum áudio")[:40]
                select_button = disnake.ui.Button(label=f"Editar áudio: {audio_label}", emoji=emoji.edit, custom_id=f"Anunciar_Botao_AbrirPainelAudio_{id}", style=disnake.ButtonStyle.blurple)

            elif current_type == "disabled":
                select_button = disnake.ui.Button(label="Personalizar botão", emoji=emoji.edit, custom_id=f"Anunciar_Botao_EditarBotao_{id}", style=disnake.ButtonStyle.blurple, disabled=True)

            components_list = [
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Anunciar > Botões > {button.get('label')} > Ações"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Configure as ações que irão aparecer no botão.\nPara remover uma ação, desative o botão."),
                disnake.ui.Separator(),
            ]

            if select_button:
                components_list.append(disnake.ui.ActionRow(select_button))

            components_list.append(disnake.ui.ActionRow(action_select()))
            
            return [
                disnake.ui.Container(*components_list),
                disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id=f"Anunciar_Botao_ConfigurarBotao_{id}")),
            ]

    # ── Painel de áudio de botão ─────────────────────────────────────────────

    @staticmethod
    def _build_audio_panel(btn_id: str) -> list:
        cfg = Buttons._get_cfg()
        button = Buttons._find_button(cfg, btn_id)
        if not button:
            return []
        action = (button.get("button", {}).get("action") or {})
        audio_filename = action.get("audio_filename")
        audio_url      = action.get("audio_url")
        has_audio      = bool(audio_filename or audio_url)

        if audio_filename:
            status = f"\U0001f3b5 `{audio_filename}`  *(arquivo enviado)*"
        elif audio_url:
            fname = audio_url.split("/")[-1].split("?")[0] or audio_url
            status = f"\U0001f3b5 `{fname}`  *(URL)*"
        else:
            status = "`Nenhum áudio configurado`"

        label = button.get("label") or "botão"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Anunciar > Botões > {label} > Áudio"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure o áudio que será enviado quando o usuário clicar no botão.\n\n"
                    "**Como adicionar:**\n"
                    "- **Automático:** envie um arquivo de áudio neste chat "
                    "(`.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.webm`) e o bot configura sozinho.\n"
                    "- **Manual:** clique em **Definir URL** e cole o link direto.\n\n"
                    f"**Áudio atual:** {status}"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Definir URL",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id=f"Anunciar_Botao_EditarAudio_{btn_id}",
                    ),
                    disnake.ui.Button(
                        label="Remover áudio",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id=f"Anunciar_Botao_RemoverAudio_{btn_id}",
                        disabled=not has_audio,
                    ),
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    emoji=emoji.back,
                    custom_id=f"Anunciar_Botao_EditarAcoes_{btn_id}",
                )
            ),
        ]


    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_DefinirBotoes":
            await message.wait(inter, send=False)
            components = self.buttons()
            await inter.edit_original_message(components=components)
        
        elif inter.component.custom_id == "Anunciar_Botao_AdicionarBotao":
            modal = Buttons.RegistrarBotao(action="create")
            await inter.response.send_modal(modal)

        elif inter.component.custom_id.startswith("Anunciar_Botao_EditarBotao_"):
            modal = Buttons.RegistrarBotao(action="edit", id=inter.component.custom_id.replace("Anunciar_Botao_EditarBotao_", ""))
            await inter.response.send_modal(modal)

        elif inter.component.custom_id.startswith("Anunciar_Botao_ApagarBotao_"):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, inter.component.custom_id.replace("Anunciar_Botao_ApagarBotao_", ""))
            if not button: return
            cfg.setdefault("message", {}).setdefault("buttons", []).remove(button)
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons.buttons())

        elif inter.component.custom_id == "Anunciar_ApagarBotoes":
            await message.wait(inter, send=False)
            cfg = Buttons._get_cfg()
            cfg["message"]["buttons"] = []
            Buttons._save_cfg(cfg)
            components = Anunciar.create_buttons()
            await inter.edit_original_message(components=components)
        
        elif inter.component.custom_id.startswith("Anunciar_Botao_EditarAcoes_"):
            button = Buttons._find_button(Buttons._get_cfg(), inter.component.custom_id.replace("Anunciar_Botao_EditarAcoes_", ""))
            if not button: return
            await message.wait(inter, send=False)
            components = Buttons.Button.acoes(button["id"], inter)
            await inter.edit_original_message(components=components)

        elif inter.component.custom_id.startswith("Anunciar_Botao_ConfigurarBotao_"):
            button = Buttons._find_button(Buttons._get_cfg(), inter.component.custom_id.replace("Anunciar_Botao_ConfigurarBotao_", ""))
            if not button: return
            await message.wait(inter, send=False)
            components = Buttons.Button.button(button["id"])
            await inter.edit_original_message(components=components)

        elif inter.component.custom_id.startswith("Anunciar_Botao_EditarURL_"):
            btn_id = inter.component.custom_id.replace("Anunciar_Botao_EditarURL_", "")
            await inter.response.send_modal(Buttons.EditarURLModal(btn_id))

        elif inter.component.custom_id.startswith("Anunciar_Botao_EditarMensagem_"):
            btn_id = inter.component.custom_id.replace("Anunciar_Botao_EditarMensagem_", "")
            await inter.response.send_modal(Buttons.EditarMensagemModal(btn_id))

        elif inter.component.custom_id.startswith("Anunciar_Botao_EditarAudio_"):
            btn_id = inter.component.custom_id.replace("Anunciar_Botao_EditarAudio_", "")
            await inter.response.send_modal(Buttons.EditarAudioModal(btn_id))

        elif inter.component.custom_id.startswith("Anunciar_Botao_AbrirPainelAudio_"):
            btn_id = inter.component.custom_id.replace("Anunciar_Botao_AbrirPainelAudio_", "")
            db = database.get_document("messages_anunciar")
            meta = db.setdefault("_meta", {})
            meta["audio_btn_editing"]    = btn_id
            meta["audio_btn_panel_msg_id"] = inter.message.id
            meta["audio_btn_panel_ch_id"]  = inter.channel.id
            meta["audio_mode"]           = "button"  # impede o listener do audio.py de agir
            meta["panel_channel_id"]     = None       # garante que audio.py não interfere
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=Buttons._build_audio_panel(btn_id))

        elif inter.component.custom_id.startswith("Anunciar_Botao_RemoverAudio_"):
            btn_id = inter.component.custom_id.replace("Anunciar_Botao_RemoverAudio_", "")
            cfg    = Buttons._get_cfg()
            button = Buttons._find_button(cfg, btn_id)
            if not button: return
            data = button.setdefault("button", {})
            data["type"]   = "disabled"
            data["action"] = {}
            data["disabled"] = True
            # Limpa metadado de edição
            db = database.get_document("messages_anunciar")
            db.setdefault("_meta", {}).pop("audio_btn_editing", None)
            database.save_document("messages_anunciar", {}, db)
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons._build_audio_panel(btn_id))

        elif inter.component.custom_id.startswith("Anunciar_RuntimeAction_Botao_"):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, inter.component.custom_id.replace("Anunciar_RuntimeAction_Botao_", ""))
            if not button:
                # Verifica se é um botão do sistema de msg_auto antes de dar erro
                from modules.automations.msg_auto import helpers as msg_auto_helpers
                msg_auto_button = msg_auto_helpers.find_button_by_custom_id(inter.component.custom_id)
                if msg_auto_button:
                    return  # Deixa o sistema de msg_auto processar
                await message.error(inter, "Botão não encontrado. Talvez deletado?", send=True)
                return
            
            data = button.setdefault("button", {})
            btn_type = data.get("type")
            action = data.get("action") or {}

            if btn_type == "audio":
                import io, base64, aiohttp
                from urllib.parse import urlparse, unquote
                audio_b64      = (action or {}).get("audio_data")
                audio_filename = (action or {}).get("audio_filename")
                audio_url      = (action or {}).get("audio_url")

                if not audio_b64 and not audio_url:
                    await message.error(inter, "Nenhum áudio configurado para este botão.", send=True)
                    return

                await inter.response.defer(ephemeral=True)
                try:
                    if audio_b64 and audio_filename:
                        # Bytes salvos no banco — não expira
                        data_bytes = base64.b64decode(audio_b64)
                        fname = audio_filename
                    else:
                        # Fallback: tenta baixar da URL
                        async with aiohttp.ClientSession() as session:
                            async with session.get(audio_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                                resp.raise_for_status()
                                fname = unquote(urlparse(audio_url).path.split("/")[-1]) or "audio.mp3"
                                data_bytes = await resp.read()
                    audio_file = disnake.File(fp=io.BytesIO(data_bytes), filename=fname)
                    await inter.followup.send(file=audio_file, ephemeral=True)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro ao enviar o áudio: `{e}`", ephemeral=True)
                return

            if btn_type == "message":
                text = (action or {}).get("message") or "Mensagem não configurada."
                try:
                    # Para mensagens grandes (>1000 chars), sempre usar defer + followup
                    # Isso evita timeout e dá mais tempo ao Discord processar
                    if len(text) > 1000:
                        if not inter.response.is_done():
                            await inter.response.defer(ephemeral=True)
                        await inter.followup.send(text, ephemeral=True)
                    else:
                        # Para mensagens pequenas, tentar método direto primeiro
                        if inter.response.is_done():
                            await inter.followup.send(text, ephemeral=True)
                        else:
                            await inter.response.send_message(text, ephemeral=True)
                except disnake.HTTPException as e:
                    # Se houver erro, usar defer + followup como fallback
                    if getattr(e, "code", None) == 40060 or "Interaction has already been acknowledged" in str(e):
                        await inter.followup.send(text, ephemeral=True)
                    else:
                        # Para outros erros, tentar defer + followup
                        try:
                            if not inter.response.is_done():
                                await inter.response.defer(ephemeral=True)
                            await inter.followup.send(text, ephemeral=True)
                        except Exception:
                            await message.error(inter, "Erro ao enviar mensagem. Tente novamente.", send=True)
                return

            if btn_type == "action":
                action_type = action.get("type")
                role_id = action.get("role")
                if not role_id:
                    await message.error(inter, "Nenhum cargo configurado para este botão.", send=True)
                    return
                role = inter.guild.get_role(int(role_id)) if role_id else None
                if not role:
                    await message.error(inter, "Cargo configurado não encontrado.", send=True)
                    return

                member = inter.user if isinstance(inter.user, disnake.Member) else await inter.guild.fetch_member(inter.user.id)
                me: disnake.Member = inter.guild.me  # type: ignore
                if not me.guild_permissions.manage_roles:
                    await message.error(inter, "Não tenho permissão para gerenciar cargos.", send=True)
                    return
                if role >= me.top_role:
                    await message.error(inter, "Meu cargo é menor que o cargo alvo.", send=True)
                    return

                try:
                    if action_type == "addrole":
                        if role in member.roles:
                            await member.remove_roles(role, reason="Anunciar: toggle remove role")
                            await message.success(inter, f"Cargo removido: {role.mention}", send=True)
                        else:
                            await member.add_roles(role, reason="Anunciar: toggle add role")
                            await message.success(inter, f"Cargo adicionado: {role.mention}", send=True)
                    elif action_type == "removerole":
                        if role in member.roles:
                            await member.remove_roles(role, reason="Anunciar: remove role")
                            await message.success(inter, f"Cargo removido: {role.mention}", send=True)
                        else:
                            await message.error(inter, f"Você não possui o cargo {role.mention}.", send=True)
                    else:
                        await message.error(inter, "Ação não configurada para este botão.", send=True)
                except disnake.Forbidden:
                    await message.error(inter, "Permissões insuficientes para alterar cargos.", send=True)
                except Exception:
                    await message.error(inter, "Ocorreu um erro ao processar a ação.", send=True)

    @commands.Cog.listener("on_message")
    async def on_message(self, msg: disnake.Message):
        """Detecta arquivo de áudio enviado no chat para configurar botão."""
        import io, base64, aiohttp as _aiohttp
        AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav", ".flac", ".m4a", ".webm")

        if msg.author.bot or not msg.guild:
            return

        audio_att = next(
            (
                a for a in msg.attachments
                if a.filename.lower().endswith(AUDIO_EXTENSIONS)
                or (a.content_type or "").startswith("audio/")
            ),
            None,
        )
        if not audio_att:
            return

        db   = database.get_document("messages_anunciar")
        meta = db.get("_meta") or {}
        btn_id   = meta.get("audio_btn_editing")
        panel_ch = meta.get("audio_btn_panel_ch_id")

        # Só age se houver painel de botão de áudio aberto neste canal e modo correto
        if not btn_id or not panel_ch or int(panel_ch) != msg.channel.id:
            return
        if meta.get("audio_mode") != "button":
            return

        cfg    = Buttons._get_cfg()
        button = Buttons._find_button(cfg, btn_id)
        if not button:
            return

        # Baixa os bytes imediatamente enquanto a URL do CDN ainda é válida
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.get(
                    audio_att.url, timeout=_aiohttp.ClientTimeout(total=15)
                ) as resp:
                    resp.raise_for_status()
                    audio_bytes = await resp.read()
            audio_b64 = base64.b64encode(audio_bytes).decode()
        except Exception:
            audio_b64 = None

        data = button.setdefault("button", {})
        data["type"]    = "audio"
        data["url"]     = None
        data["disabled"] = False
        if audio_b64:
            data["action"] = {
                "audio_url":      None,
                "audio_data":     audio_b64,
                "audio_filename": audio_att.filename,
            }
        else:
            # Fallback: salva só a URL (pode expirar)
            data["action"] = {
                "audio_url":      audio_att.url,
                "audio_data":     None,
                "audio_filename": audio_att.filename,
            }
        Buttons._save_cfg(cfg)

        # Atualiza o painel
        panel_msg_id = meta.get("audio_btn_panel_msg_id")
        if panel_msg_id:
            try:
                panel_msg = await msg.channel.fetch_message(int(panel_msg_id))
                await panel_msg.edit(components=Buttons._build_audio_panel(btn_id))
            except Exception:
                pass

        # Confirma e limpa o chat
        try:
            await msg.reply(
                f"🎵 **Áudio detectado!** `{audio_att.filename}` foi configurado no botão.",
                delete_after=8,
            )
        except Exception:
            pass
        try:
            await msg.delete(delay=1)
        except Exception:
            pass

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_Botao_SelecionarBotao":
            ui = Buttons.Button.button(inter.values[0])
            if not ui:
                await inter.response.send_message("Botão não encontrado!", ephemeral=True)
            else:
                await inter.response.edit_message(components=ui)
        
        elif inter.component.custom_id.startswith("Anunciar_Botao_Estilo_"):
            cfg = Buttons._get_cfg()
            button = Buttons._find_button(cfg, inter.component.custom_id.replace("Anunciar_Botao_Estilo_", ""))
            if not button: return
            button.setdefault("button", {})["style"] = inter.values[0]
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons.Button.button(button["id"]))

        elif inter.component.custom_id.startswith("Anunciar_Botao_AlterarAcoes_"):
            cfg = Buttons._get_cfg()
            btn_id = inter.component.custom_id.removeprefix("Anunciar_Botao_AlterarAcoes_")
            button = Buttons._find_button(cfg, btn_id)
            if not button: return
            selected = inter.values[0] if inter.values else None
            data = button.setdefault("button", {})
            action = data.setdefault("action", {})

            if selected == "DarCargo":
                data.update(type="action", url=None, disabled=False)
                # Preservar role_id se já existir
                existing_role = action.get("role")
                data["action"] = {"type": "addrole"}
                if existing_role:
                    data["action"]["role"] = existing_role
                Buttons._save_cfg(cfg)
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

            elif selected == "RemoverCargo":
                data.update(type="action", url=None, disabled=False)
                # Preservar role_id se já existir
                existing_role = action.get("role")
                data["action"] = {"type": "removerole"}
                if existing_role:
                    data["action"]["role"] = existing_role
                Buttons._save_cfg(cfg)
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

            elif selected == "MensagemEferema":
                msg = (action or {}).get("message")
                if not msg:
                    await inter.response.send_modal(Buttons.EditarMensagemModal(btn_id))
                    return
                data.update(type="message", url=None, action={"message": msg}, disabled=False)
                Buttons._save_cfg(cfg)
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

            elif selected == "Audio":
                audio_url = (action or {}).get("audio_url")
                if not audio_url:
                    await inter.response.send_modal(Buttons.EditarAudioModal(btn_id))
                    return
                data.update(type="audio", url=None, action={"audio_url": audio_url}, disabled=False)
                Buttons._save_cfg(cfg)
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

            elif selected == "URL":
                if not data.get("url") or not Buttons._is_valid_url(data.get("url")):
                    await inter.response.send_modal(Buttons.EditarURLModal(btn_id))
                    return
                data.update(type="url", action={}, disabled=False)
                Buttons._save_cfg(cfg)
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

            elif selected == "Desativado":
                data.update(type="disabled", url=None, action={}, disabled=True)
                Buttons._save_cfg(cfg)
                await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))

        elif inter.component.custom_id.startswith(("Anunciar_Botao_AdicionarCargo_", "Anunciar_Botao_RemoverCargo_")):
            cfg = Buttons._get_cfg()
            if inter.component.custom_id.startswith("Anunciar_Botao_AdicionarCargo_"):
                prefix, tipo = "Anunciar_Botao_AdicionarCargo_", "addrole"
            else:
                prefix, tipo = "Anunciar_Botao_RemoverCargo_", "removerole"
            btn_id = inter.component.custom_id.removeprefix(prefix)
            button = Buttons._find_button(cfg, btn_id)
            if not button: return
            data = button.setdefault("button", {})
            action = data.setdefault("action", {})
            action["type"] = tipo
            if inter.values:
                action["role"] = int(inter.values[0])
            Buttons._save_cfg(cfg)
            await inter.response.edit_message(components=Buttons.Button.acoes(button["id"], inter))
        
        elif inter.component.custom_id.startswith("Anunciar_Botao_AlterarAcoes_"):
            button = Buttons._find_button(Buttons._get_cfg(), inter.component.custom_id.replace("Anunciar_Botao_AlterarAcoes_", ""))
            if not button: return
            await message.wait(inter, send=False)