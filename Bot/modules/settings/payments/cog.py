from disnake.ext import commands
import disnake
import json
from pathlib import Path
import aiohttp

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions import plan

# ── Configuração de provedores disponíveis ────────────────────────────────────
# configs/config_payments.json → {"all_providers": true/false}
# true  = todas as formas de pagamento disponíveis
# false = apenas Amethys Wallet e Pix Manual

def _all_providers_enabled() -> bool:
    """Lê configs/config_payments.json e retorna se todos os provedores estão ativos."""
    try:
        config_path = Path(__file__).parent
        # Subir até encontrar a pasta configs no início do projeto
        for _ in range(6):
            candidate = config_path / "configs" / "config_payments.json"
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return bool(data.get("all_providers", True))
            config_path = config_path.parent
    except Exception:
        pass
    return True  # fallback: liberar tudo se não achar o arquivo

_PROVIDERS_RESTRICTED = {"amethys_wallet", "pix_manual"}


class ConfigurarPagamentos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _providers():
        """Retorna todos os provedores com suas informações."""
        return {
            # ── PIX ──────────────────────────────────────────────────────────
            "pix_manual":   ("Pix Manual",        emoji.pix),
            "mercado_pago": ("Mercado Pago",       emoji.mercado_pago),
            "efibank":      ("Efi Bank",           emoji.efi_bank),
            "pushinpay":    ("Pushin Pay",         emoji.pushin_pay),
            "misticpay":    ("MisticPay",          emoji.pix),
            "livepix":      ("LivePix",            emoji.pix),
            "nubank_imap":  ("Nubank (IMAP)",      emoji.bank),
            "asaas":        ("Asaas",              emoji.card),
            "amethys_wallet": ("Amethys Wallet",   emoji.wallet),
            # ── Cartão ───────────────────────────────────────────────────────
            "stripe":       ("Stripe",             emoji.stripe),
            "paypal":       ("PayPal",             emoji.wallet),
            # ── Crypto ───────────────────────────────────────────────────────
            "coinbase":     ("Coinbase",           emoji.wallet),
            "nowpayments":  ("NowPayments",        emoji.wallet),
            # ── Em breve ─────────────────────────────────────────────────────
            "pagbank":      ("PagBank (Em breve)", emoji.pagbank),
            "picpay":       ("PicPay (Em breve)",  emoji.picpay),
            "inter":        ("Inter (Em breve)",   emoji.bank),
            "bitcoin":      ("Bitcoin (Em breve)", emoji.wallet),
            "litecoin":     ("Litecoin (Em breve)",emoji.wallet),
            "ethereum":     ("Ethereum (Em breve)",emoji.wallet),
        }

    @staticmethod
    def _providers_by_category():
        all_enabled = _all_providers_enabled()
        pix = ["pix_manual", "amethys_wallet"]
        if all_enabled:
            pix = [
                "pix_manual", "mercado_pago", "efibank", "pushinpay",
                "misticpay", "livepix", "nubank_imap", "asaas", "amethys_wallet",
            ]
        return {
            "pix":    pix,
            "cartao": ["stripe", "paypal", "asaas"] if all_enabled else [],
            "crypto": ["coinbase", "nowpayments"]   if all_enabled else [],
        }

    @staticmethod
    def _providers_coming_soon():
        """Provedores bloqueados (sem implementação ainda)."""
        return ["pagbank", "picpay", "inter", "bitcoin", "litecoin", "ethereum"]

    @staticmethod
    def _load_config() -> dict:
        return db.get_document("payment_configs") or {}

    @classmethod
    def _get_provider_status(cls, key: str, config: dict, pagamentos: dict) -> tuple[bool, bool, str]:
        """Retorna (enabled, configured, status_text)."""
        entry = config.get(key)
        if isinstance(entry, dict):
            enabled = bool(entry.get("enabled", False))
            if key == "mercado_pago":
                configured = bool(entry.get("access_token"))
            elif key == "efibank":
                cert_path = entry.get("cert_file")
                cert_ok = bool(cert_path) and Path(cert_path).exists()
                configured = bool(
                    (entry.get("client_id") or entry.get("client"))
                    and (entry.get("client_secret") or entry.get("token"))
                    and entry.get("pix_key")
                    and cert_ok
                )
            elif key in {"pagbank", "picpay", "pushinpay", "asaas", "stripe", "coinbase", "nowpayments"}:
                token_key = {
                    "pagbank":      "token_pagbank",
                    "picpay":       "token_picpay",
                    "pushinpay":    "token_pushinpay",
                    "asaas":        "token_asaas",
                    "stripe":       "token_stripe",
                    "coinbase":     "token_coinbase",
                    "nowpayments":  "token_nowpayments",
                }[key]
                configured = bool(entry.get(token_key))
            elif key == "paypal":
                configured = bool(entry.get("client_id") and entry.get("client_secret"))
            elif key in {"misticpay", "livepix"}:
                # livepix usa token_livepix; misticpay usa client_id/client_secret
                if key == "livepix":
                    configured = bool(entry.get("token_livepix"))
                else:
                    configured = bool(entry.get("client_id") and entry.get("client_secret"))
            elif key == "nubank_imap":
                configured = bool(
                    entry.get("email") and entry.get("password") and entry.get("pix_key")
                )
            elif key == "pix_manual":
                configured = bool(entry.get("pix_key") and entry.get("pix_key_type"))
            elif key == "amethys_wallet":
                configured = bool(entry.get("api_key"))
            else:
                configured = False
        elif isinstance(entry, bool):
            enabled = entry
            configured = False
        else:
            enabled = bool(pagamentos.get(key, False))
            configured = False

        if enabled:
            status_text = "Ativado"
        elif configured:
            status_text = "Desativado"
        else:
            status_text = "Não Configurado"

        return enabled, configured, status_text

    # ── Componentes / Embeds ──────────────────────────────────────────────────

    @classmethod
    def _accent(cls):
        colors = db.get_document("custom_colors") or {}
        hex_color = colors.get("primary")
        if hex_color:
            return {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))}
        return {}

    @classmethod
    def categoria_pagamentos_components(cls, inter) -> list:
        all_enabled = _all_providers_enabled()

        # ── Modo restrito: select direto com os 2 providers disponíveis ──────
        if not all_enabled:
            pagamentos = db.get_document("pagamentos") or {}
            config     = cls._load_config()
            providers  = cls._providers()
            direct_options = []
            direct_lines   = []
            for k in ("amethys_wallet", "pix_manual"):
                label, icon = providers[k]
                enabled, configured, status_text = cls._get_provider_status(k, config, pagamentos)
                direct_lines.append(f"{emoji.on if enabled else (emoji.settings2 if configured else emoji.wrong)} **{label}**")
                direct_options.append(disnake.SelectOption(label=f"Configurar {label}", value=k, emoji=icon, description=f"Status: {status_text}"))
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Configurações > **Formas de Pagamento**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("\n".join(direct_lines)),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.StringSelect(
                            custom_id="Configuracoes_Pagamentos_Select:pix",
                            placeholder="Selecione uma forma de pagamento para configurar",
                            options=direct_options,
                        )
                    ),
                    **cls._accent(),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Configuracoes")
                ),
            ]

        # ── Modo completo: seleção por categoria ─────────────────────────────
        cat_options = [disnake.SelectOption(label="Pix", value="pix", emoji=emoji.pix, description="Pagamento via Pix")]
        cat_text = f"{emoji.pix} **Pix**"
        cat_options += [
            disnake.SelectOption(label="Cartão", value="cartao", emoji=emoji.card,   description="Pagamento com cartão"),
            disnake.SelectOption(label="Crypto", value="crypto", emoji=emoji.wallet, description="Pagamento em criptomoedas"),
        ]
        cat_text += f"\n{emoji.card} **Cartão**\n{emoji.wallet} **Crypto**"
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Configurações > **Formas de Pagamento**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(cat_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Configuracoes_Pagamentos_Categoria_Select",
                        placeholder="Selecione o tipo de pagamento",
                        options=cat_options,
                    )
                ),
                **cls._accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Configuracoes")
            ),
        ]

    @classmethod
    def categoria_pagamentos_embed(cls, inter):
        colors = db.get_document("custom_colors") or {}
        hex_color = colors.get("primary")
        all_enabled = _all_providers_enabled()

        # ── Modo restrito: select direto com os 2 providers disponíveis ──────
        if not all_enabled:
            pagamentos = db.get_document("pagamentos") or {}
            config     = cls._load_config()
            providers  = cls._providers()
            direct_options = []
            direct_lines   = []
            for k in ("amethys_wallet", "pix_manual"):
                label, icon = providers[k]
                enabled, configured, status_text = cls._get_provider_status(k, config, pagamentos)
                direct_lines.append(f"{emoji.on if enabled else (emoji.settings2 if configured else emoji.wrong)} **{label}**")
                direct_options.append(disnake.SelectOption(label=f"Configurar {label}", value=k, emoji=icon, description=f"Status: {status_text}"))
            embed = disnake.Embed(
                title="Formas de Pagamento",
                description=(
                    f"-# Painel > Configurações > **Formas de Pagamento**\n\n"
                    + "\n".join(direct_lines)
                ),
            )
            if hex_color:
                embed.color = int(hex_color.replace("#", ""), 16)
            components = [
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Configuracoes_Pagamentos_Select:pix",
                        placeholder="Selecione uma forma de pagamento para configurar",
                        options=direct_options,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Configuracoes")
                ),
            ]
            return embed, components

        # ── Modo completo: seleção por categoria ─────────────────────────────
        embed = disnake.Embed(
            title="Formas de Pagamento",
            description=(
                f"-# Painel > Configurações > **Formas de Pagamento**\n\n"
                f"{emoji.pix} **Pix**\n{emoji.card} **Cartão**\n{emoji.wallet} **Crypto**"
            ),
        )
        if hex_color:
            embed.color = int(hex_color.replace("#", ""), 16)
        cat_options = [
            disnake.SelectOption(label="Pix",    value="pix",    emoji=emoji.pix),
            disnake.SelectOption(label="Cartão", value="cartao", emoji=emoji.card),
            disnake.SelectOption(label="Crypto", value="crypto", emoji=emoji.wallet),
        ]
        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Configuracoes_Pagamentos_Categoria_Select",
                    placeholder="Selecione o tipo de pagamento",
                    options=cat_options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Configuracoes")
            ),
        ]
        return embed, components

    @classmethod
    def pagamentos_components(cls, inter, categoria: str = None) -> list:
        if not categoria:
            return cls.categoria_pagamentos_components(inter)

        pagamentos = db.get_document("pagamentos") or {}
        config    = cls._load_config()
        providers = cls._providers()
        keys      = cls._providers_by_category().get(categoria, [])
        cat_name  = {"pix": "Pix", "cartao": "Cartão", "crypto": "Crypto"}.get(categoria, categoria)

        lines, options = [], []
        for k in keys:
            if k not in providers:
                continue
            label, icon = providers[k]
            enabled, configured, status_text = cls._get_provider_status(k, config, pagamentos)
            lines.append(f"{emoji.on if enabled else (emoji.settings2 if configured else emoji.wrong)} **{label}**")
            options.append(disnake.SelectOption(label=f"Configurar {label}", value=k, emoji=icon, description=f"Status: {status_text}"))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Configurações > **Formas de Pagamento** > **{cat_name}**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("\n".join(lines) or "Nenhum provedor disponível."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id=f"Configuracoes_Pagamentos_Select:{categoria}",
                        placeholder="Selecione uma forma de pagamento para configurar",
                        options=options,
                    )
                ),
                **cls._accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Configuracoes_Pagamentos")
            ),
        ]

    @classmethod
    def pagamentos_embed(cls, inter, categoria: str = None):
        if not categoria:
            return cls.categoria_pagamentos_embed(inter)

        pagamentos = db.get_document("pagamentos") or {}
        config    = cls._load_config()
        colors    = db.get_document("custom_colors") or {}
        providers = cls._providers()
        keys      = cls._providers_by_category().get(categoria, [])
        cat_name  = {"pix": "Pix", "cartao": "Cartão", "crypto": "Crypto"}.get(categoria, categoria)

        lines, options = [], []
        for k in keys:
            if k not in providers:
                continue
            label, icon = providers[k]
            enabled, configured, status_text = cls._get_provider_status(k, config, pagamentos)
            lines.append(f"{emoji.on if enabled else (emoji.settings2 if configured else emoji.wrong)} **{label}**")
            options.append(disnake.SelectOption(label=f"Configurar {label}", value=k, emoji=icon, description=f"Status: {status_text}"))

        embed = disnake.Embed(
            title=f"Formas de Pagamento - {cat_name}",
            description=(
                f"-# Painel > Configurações > **Formas de Pagamento** > **{cat_name}**\n\n"
                + "\n".join(lines)
            ),
        )
        hex_color = colors.get("primary")
        if hex_color:
            embed.color = int(hex_color.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"Configuracoes_Pagamentos_Select:{categoria}",
                    placeholder="Selecione uma forma de pagamento para configurar",
                    options=options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Configuracoes_Pagamentos")
            ),
        ]
        return embed, components

    # ── Listeners ─────────────────────────────────────────────────────────────

    async def display_payments_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
            embed, components = self.categoria_pagamentos_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter)
            await inter.edit_original_message(components=self.categoria_pagamentos_components(inter))

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Configuracoes_Pagamentos":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.categoria_pagamentos_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.categoria_pagamentos_components(inter))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Configuracoes_Pagamentos_Categoria_Select":
            categoria = inter.values[0]
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.pagamentos_embed(inter, categoria)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.pagamentos_components(inter, categoria))

        elif inter.component.custom_id.startswith("Configuracoes_Pagamentos_Select"):
            parts = inter.component.custom_id.split(":")
            categoria = parts[1] if len(parts) > 1 else None
            key = inter.values[0]

            if key in self._providers_coming_soon():
                await inter.response.send_message(
                    f"{emoji.information} Essa forma de pagamento estará disponível em breve.",
                    ephemeral=True
                )
                return

            if not _all_providers_enabled() and key not in _PROVIDERS_RESTRICTED:
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas **Amethys Wallet** e **Pix Manual** estão disponíveis nesta configuração.",
                    ephemeral=True
                )
                return

            if not plan.should_allow_payment_provider(key):
                await inter.response.send_message(
                    f"{emoji.wrong} O plano **Free** permite apenas a forma de pagamento **Amethys Wallet**.\n"
                    f"{emoji.arrow} Acesse https://amethys.lat para criar sua conta.",
                    ephemeral=True
                )
                return

            await inter.response.send_modal(PaymentProviderModal(key, categoria))


# ─────────────────────────────────────────────────────────────────────────────
# Modal de configuração
# ─────────────────────────────────────────────────────────────────────────────

class PaymentProviderModal(disnake.ui.Modal):
    def __init__(self, provider_key: str, categoria: str = None):
        self.provider_key = provider_key
        self.categoria    = categoria

        config = ConfigurarPagamentos._load_config()
        entry  = config.get(provider_key) or {}
        if isinstance(entry, bool):
            entry = {"enabled": bool(entry)}

        enabled = bool(entry.get("enabled", False))

        providers_dict = ConfigurarPagamentos._providers()
        label = providers_dict.get(provider_key, (provider_key.capitalize(), ""))[0]

        # ── Status (comum a todos) ────────────────────────────────────────────
        components = [
            disnake.ui.Label(
                text="Status do provedor",
                component=disnake.ui.StringSelect(
                    placeholder="Ativar ou desativar",
                    custom_id="payment_status",
                    required=True,
                    options=[
                        disnake.SelectOption(label="Ativado",    emoji=emoji.on,  value="enabled_True",  default=enabled),
                        disnake.SelectOption(label="Desativado", emoji=emoji.off, value="enabled_False", default=not enabled),
                    ],
                ),
                description="Define se o provedor estará ativo.",
            ),
        ]

        # ── Campos específicos por provedor ───────────────────────────────────

        if provider_key == "mercado_pago":
            components.append(disnake.ui.Label(
                text="Access Token",
                component=disnake.ui.TextInput(
                    placeholder="Cole o Access Token do MercadoPago",
                    custom_id="mp_access_token",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=str(entry.get("access_token") or ""),
                ),
                description="Access Token da sua conta Mercado Pago.",
            ))

        elif provider_key == "efibank":
            components += [
                disnake.ui.Label(text="Client ID", component=disnake.ui.TextInput(
                    placeholder="Client ID da Efi", custom_id="efi_client_id",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("client_id") or entry.get("client") or ""),
                ), description="Client ID da Efi Bank."),
                disnake.ui.Label(text="Client Secret", component=disnake.ui.TextInput(
                    placeholder="Client Secret da Efi", custom_id="efi_client_secret",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("client_secret") or entry.get("token") or ""),
                ), description="Client Secret da Efi Bank."),
                disnake.ui.Label(text="Chave Pix Aleatória", component=disnake.ui.TextInput(
                    placeholder="Chave Pix Aleatória", custom_id="efi_pix_key",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("pix_key") or ""),
                ), description="Chave Pix aleatória cadastrada na Efi."),
                disnake.ui.Label(text="Certificado .p12", component=disnake.ui.FileUpload(
                    custom_id="efi_cert_file", required=False,
                ), description="Arquivo de certificado .p12 da Efi."),
            ]

        elif provider_key == "pushinpay":
            components.append(disnake.ui.Label(text="Token PushinPay", component=disnake.ui.TextInput(
                placeholder="Token do PushinPay", custom_id="pushinpay_token",
                style=disnake.TextInputStyle.short, required=False,
                value=str(entry.get("token_pushinpay") or ""),
            ), description="Token de API do PushinPay."))

        elif provider_key == "misticpay":
            components += [
                disnake.ui.Label(text="Client ID", component=disnake.ui.TextInput(
                    placeholder="Client ID do MisticPay", custom_id="misticpay_client_id",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("client_id") or ""),
                ), description="Client ID do MisticPay."),
                disnake.ui.Label(text="Client Secret", component=disnake.ui.TextInput(
                    placeholder="Client Secret do MisticPay", custom_id="misticpay_client_secret",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("client_secret") or ""),
                ), description="Client Secret do MisticPay."),
            ]

        elif provider_key == "livepix":
            components.append(disnake.ui.Label(
                text="Token LivePix",
                component=disnake.ui.TextInput(
                    placeholder="Access Token / API Key da LivePix",
                    custom_id="livepix_token",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=str(entry.get("token_livepix") or ""),
                ),
                description="Token de acesso obtido no painel da LivePix.",
            ))

        elif provider_key == "nubank_imap":
            components += [
                disnake.ui.Label(text="Email do Gmail", component=disnake.ui.TextInput(
                    placeholder="seuemail@gmail.com", custom_id="nubank_email",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("email") or ""),
                ), description="Email Gmail cadastrado no Nubank para receber notificações."),
                disnake.ui.Label(text="Senha de App (16 dígitos)", component=disnake.ui.TextInput(
                    placeholder="xxxx xxxx xxxx xxxx", custom_id="nubank_password",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("password") or ""),
                ), description="Senha de app do Gmail (myaccount.google.com/apppasswords)."),
                disnake.ui.Label(text="Chave PIX", component=disnake.ui.TextInput(
                    placeholder="Sua chave PIX que recebe os pagamentos", custom_id="nubank_pix_key",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("pix_key") or ""),
                ), description="Chave PIX que receberá os pagamentos."),
                disnake.ui.Label(text="Tipo da Chave PIX", component=disnake.ui.StringSelect(
                    placeholder="Selecione o tipo", custom_id="nubank_pix_key_type",
                    required=False,
                    options=[
                        disnake.SelectOption(label="Email",     value="email",    default=entry.get("pix_key_type") == "email"),
                        disnake.SelectOption(label="CPF",       value="cpf",      default=entry.get("pix_key_type") == "cpf"),
                        disnake.SelectOption(label="CNPJ",      value="cnpj",     default=entry.get("pix_key_type") == "cnpj"),
                        disnake.SelectOption(label="Telefone",  value="telefone", default=entry.get("pix_key_type") == "telefone"),
                        disnake.SelectOption(label="Aleatória", value="aleatoria",default=entry.get("pix_key_type") == "aleatoria"),
                    ],
                ), description="Tipo da chave PIX informada."),
            ]

        elif provider_key == "asaas":
            components += [
                disnake.ui.Label(text="Token Asaas", component=disnake.ui.TextInput(
                    placeholder="Token de API do Asaas", custom_id="asaas_token",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("token_asaas") or ""),
                ), description="Token de API do Asaas."),
                disnake.ui.Label(text="Ambiente", component=disnake.ui.StringSelect(
                    placeholder="Produção ou Sandbox", custom_id="asaas_environment",
                    required=False,
                    options=[
                        disnake.SelectOption(label="Produção",         value="production", default=entry.get("environment", "production") == "production"),
                        disnake.SelectOption(label="Sandbox (Testes)", value="sandbox",    default=entry.get("environment") == "sandbox"),
                    ],
                ), description="Ambiente de execução (use Sandbox para testes)."),
            ]

        elif provider_key == "stripe":
            components.append(disnake.ui.Label(text="Secret Key", component=disnake.ui.TextInput(
                placeholder="sk_live_... ou sk_test_...", custom_id="stripe_token",
                style=disnake.TextInputStyle.short, required=False,
                value=str(entry.get("token_stripe") or ""),
            ), description="Secret Key do Stripe (começa com sk_live_ ou sk_test_)."))

        elif provider_key == "paypal":
            components += [
                disnake.ui.Label(text="Client ID", component=disnake.ui.TextInput(
                    placeholder="Client ID do PayPal", custom_id="paypal_client_id",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("client_id") or ""),
                ), description="Client ID obtido no PayPal Developer."),
                disnake.ui.Label(text="Client Secret", component=disnake.ui.TextInput(
                    placeholder="Client Secret do PayPal", custom_id="paypal_client_secret",
                    style=disnake.TextInputStyle.short, required=False,
                    value=str(entry.get("client_secret") or ""),
                ), description="Client Secret obtido no PayPal Developer."),
                disnake.ui.Label(text="Ambiente", component=disnake.ui.StringSelect(
                    placeholder="Produção ou Sandbox", custom_id="paypal_environment",
                    required=False,
                    options=[
                        disnake.SelectOption(label="Produção",         value="production", default=entry.get("environment", "production") == "production"),
                        disnake.SelectOption(label="Sandbox (Testes)", value="sandbox",    default=entry.get("environment") == "sandbox"),
                    ],
                ), description="Ambiente de execução."),
            ]

        elif provider_key == "coinbase":
            components.append(disnake.ui.Label(text="API Key Coinbase", component=disnake.ui.TextInput(
                placeholder="API Key do Coinbase Commerce", custom_id="coinbase_token",
                style=disnake.TextInputStyle.short, required=False,
                value=str(entry.get("token_coinbase") or ""),
            ), description="API Key do Coinbase Commerce."))

        elif provider_key == "nowpayments":
            components.append(disnake.ui.Label(text="API Key NOWPayments", component=disnake.ui.TextInput(
                placeholder="API Key do NOWPayments", custom_id="nowpayments_token",
                style=disnake.TextInputStyle.short, required=False,
                value=str(entry.get("token_nowpayments") or ""),
            ), description="API Key do NOWPayments."))

        elif provider_key == "pix_manual":
            components += [
                disnake.ui.Label(text="Chave PIX", component=disnake.ui.TextInput(
                    placeholder="Digite sua chave PIX", custom_id="pix_manual_key",
                    style=disnake.TextInputStyle.short, required=False, max_length=50,
                    value=str(entry.get("pix_key") or ""),
                ), description="Sua chave PIX para receber pagamentos."),
                disnake.ui.Label(text="Tipo da Chave PIX", component=disnake.ui.StringSelect(
                    placeholder="Selecione o tipo", custom_id="pix_manual_key_type",
                    required=False,
                    options=[
                        disnake.SelectOption(label="Email",     value="email",    emoji=emoji.mail2,  default=entry.get("pix_key_type") == "email"),
                        disnake.SelectOption(label="Telefone",  value="telefone", emoji=emoji.mobile, default=entry.get("pix_key_type") == "telefone"),
                        disnake.SelectOption(label="CPF",       value="cpf",      emoji=emoji.member, default=entry.get("pix_key_type") == "cpf"),
                        disnake.SelectOption(label="CNPJ",      value="cnpj",     emoji=emoji.store,  default=entry.get("pix_key_type") == "cnpj"),
                        disnake.SelectOption(label="Aleatória", value="aleatoria",emoji=emoji.link,   default=entry.get("pix_key_type") == "aleatoria"),
                    ],
                ), description="Tipo da chave PIX informada."),
            ]

        elif provider_key == "amethys_wallet":
            customer_pays_fee = bool(entry.get("customer_pays_fee", False))
            components += [
                disnake.ui.Label(
                    text="API Key — Amethys Wallet",
                    component=disnake.ui.TextInput(
                        placeholder="Cole sua API Key da Amethys Wallet (vp_...)",
                        custom_id="amethys_wallet_api_key",
                        style=disnake.TextInputStyle.short,
                        required=False,
                        value=str(entry.get("api_key") or ""),
                    ),
                    description="API Key obtida no painel em https://amethys.lat.",
                ),
                disnake.ui.Label(
                    text="Cliente pagar Taxa",
                    component=disnake.ui.StringSelect(
                        placeholder="Quem paga a taxa de serviço?",
                        custom_id="amethys_wallet_customer_pays_fee",
                        required=False,
                        options=[
                            disnake.SelectOption(label="Cliente paga a taxa",  emoji=emoji.on,  value="fee_True",  default=customer_pays_fee),
                            disnake.SelectOption(label="Loja paga a taxa",     emoji=emoji.off, value="fee_False", default=not customer_pays_fee),
                        ],
                    ),
                    description="Define se a taxa de serviço será repassada ao cliente.",
                ),
            ]

        super().__init__(
            title=f"Configurar {label}",
            components=components,
            custom_id=f"payment_provider_modal:{provider_key}",
        )

    # ── Callback do modal ─────────────────────────────────────────────────────

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values

        # Status
        sv = valores.get("payment_status")
        if isinstance(sv, (list, tuple)):
            sv = sv[0] if sv else None
        enabled = (sv == "enabled_True")

        error_text = None

        config = ConfigurarPagamentos._load_config()
        entry  = config.get(self.provider_key) or {}
        if isinstance(entry, bool):
            entry = {"enabled": bool(entry)}

        # ── Validação e persistência ──────────────────────────────────────────

        if self.provider_key == "mercado_pago":
            token = valores.get("mp_access_token")
            old   = str(entry.get("access_token") or "")
            final = old
            if token is not None:
                if token.strip() == "":
                    final = ""
                else:
                    try:
                        timeout = aiohttp.ClientTimeout(total=10)
                        async with aiohttp.ClientSession(timeout=timeout) as s:
                            async with s.get(
                                "https://api.mercadopago.com/users/me",
                                headers={"Authorization": f"Bearer {token.strip()}"},
                            ) as resp:
                                if resp.status == 200:
                                    final = token.strip()
                                else:
                                    error_text = "Token do Mercado Pago inválido ou expirado."
                                    enabled = False
                    except Exception:
                        error_text = "Erro ao validar token do Mercado Pago."
                        enabled = False
            entry["access_token"] = final
            if enabled and not final:
                enabled = False
                error_text = error_text or "Informe um Access Token válido."

        elif self.provider_key == "efibank":
            cid    = valores.get("efi_client_id")
            csec   = valores.get("efi_client_secret")
            pix    = valores.get("efi_pix_key")
            cert_f = valores.get("efi_cert_file")
            if isinstance(cert_f, (list, tuple)):
                cert_f = cert_f[0] if cert_f else None

            cert_path = entry.get("cert_file")
            cert_exists = bool(cert_path) and Path(cert_path).exists()

            if cert_f:
                try:
                    if not cert_f.filename.lower().endswith(".p12"):
                        error_text = "O arquivo deve ser um certificado .p12"
                    else:
                        base_dir = Path(__file__).resolve().parents[3] / "database" / "payments" / "certs" / "efibank"
                        base_dir.mkdir(parents=True, exist_ok=True)
                        save_path = base_dir / f"cert_{inter.author.id}.p12"
                        data = await cert_f.read()
                        save_path.write_bytes(data)
                        cert_path   = str(save_path)
                        cert_exists = True
                except Exception as exc:
                    error_text = f"Erro ao processar certificado: {exc}"

            if cid  is not None: entry["client_id"]     = cid
            if csec is not None: entry["client_secret"] = csec
            if pix  is not None: entry["pix_key"]       = pix
            if cert_path:        entry["cert_file"]     = cert_path

            ok = bool(
                (entry.get("client_id") or entry.get("client"))
                and (entry.get("client_secret") or entry.get("token"))
                and entry.get("pix_key")
                and cert_exists
            )
            if enabled and not ok:
                enabled = False
                error_text = error_text or "Preencha Client ID, Client Secret, Chave Pix e o certificado .p12."

        elif self.provider_key == "pushinpay":
            token = valores.get("pushinpay_token")
            entry["token_pushinpay"] = token.strip() if token else str(entry.get("token_pushinpay") or "")
            if enabled and not entry.get("token_pushinpay"):
                enabled = False
                error_text = "Informe o token do PushinPay."

        elif self.provider_key == "misticpay":
            cid   = valores.get("misticpay_client_id")
            csec  = valores.get("misticpay_client_secret")
            if cid  is not None: entry["client_id"]     = cid.strip()
            if csec is not None: entry["client_secret"] = csec.strip()
            if enabled and not (entry.get("client_id") and entry.get("client_secret")):
                enabled = False
                error_text = "Informe Client ID e Client Secret do MisticPay."

        elif self.provider_key == "livepix":
            token = valores.get("livepix_token")
            entry["token_livepix"] = token.strip() if token else str(entry.get("token_livepix") or "")
            if enabled and not entry.get("token_livepix"):
                enabled = False
                error_text = "Informe o Token da LivePix."

        elif self.provider_key == "nubank_imap":
            import re
            nubank_email    = valores.get("nubank_email")
            nubank_password = valores.get("nubank_password")
            nubank_pix_key  = valores.get("nubank_pix_key")
            nubank_pix_type = valores.get("nubank_pix_key_type")
            if isinstance(nubank_pix_type, (list, tuple)):
                nubank_pix_type = nubank_pix_type[0] if nubank_pix_type else None

            if nubank_email    is not None: entry["email"]        = nubank_email.strip()
            if nubank_password is not None: entry["password"]     = nubank_password.replace(" ", "")
            if nubank_pix_key  is not None: entry["pix_key"]      = nubank_pix_key.strip()
            if nubank_pix_type is not None: entry["pix_key_type"] = nubank_pix_type

            email_val = entry.get("email", "")
            pwd_val   = entry.get("password", "").replace(" ", "")

            if email_val and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email_val):
                error_text = "Email inválido! Use o formato: seuemail@gmail.com"
                enabled = False
            elif pwd_val and len(pwd_val) != 16:
                error_text = "A senha de app deve ter exatamente 16 dígitos."
                enabled = False
            elif enabled and not (entry.get("email") and entry.get("password") and entry.get("pix_key")):
                enabled = False
                error_text = "Preencha email, senha de app e chave PIX."

        elif self.provider_key == "asaas":
            token = valores.get("asaas_token")
            env   = valores.get("asaas_environment")
            if isinstance(env, (list, tuple)):
                env = env[0] if env else "production"
            entry["token_asaas"] = token.strip() if token else str(entry.get("token_asaas") or "")
            if env: entry["environment"] = env
            if enabled and not entry.get("token_asaas"):
                enabled = False
                error_text = "Informe o token do Asaas."

        elif self.provider_key == "stripe":
            token = valores.get("stripe_token")
            entry["token_stripe"] = token.strip() if token else str(entry.get("token_stripe") or "")
            if enabled and not entry.get("token_stripe"):
                enabled = False
                error_text = "Informe a Secret Key do Stripe."

        elif self.provider_key == "paypal":
            cid  = valores.get("paypal_client_id")
            csec = valores.get("paypal_client_secret")
            env  = valores.get("paypal_environment")
            if isinstance(env, (list, tuple)):
                env = env[0] if env else "production"
            if cid  is not None: entry["client_id"]     = cid.strip()
            if csec is not None: entry["client_secret"] = csec.strip()
            if env: entry["environment"] = env
            if enabled and not (entry.get("client_id") and entry.get("client_secret")):
                enabled = False
                error_text = "Informe Client ID e Client Secret do PayPal."

        elif self.provider_key == "coinbase":
            token = valores.get("coinbase_token")
            entry["token_coinbase"] = token.strip() if token else str(entry.get("token_coinbase") or "")
            if enabled and not entry.get("token_coinbase"):
                enabled = False
                error_text = "Informe a API Key do Coinbase."

        elif self.provider_key == "nowpayments":
            token = valores.get("nowpayments_token")
            entry["token_nowpayments"] = token.strip() if token else str(entry.get("token_nowpayments") or "")
            if enabled and not entry.get("token_nowpayments"):
                enabled = False
                error_text = "Informe a API Key do NOWPayments."

        elif self.provider_key == "pix_manual":
            import re
            pix_key  = valores.get("pix_manual_key")
            pix_type = valores.get("pix_manual_key_type")
            if isinstance(pix_type, (list, tuple)):
                pix_type = pix_type[0] if pix_type else None

            key      = (pix_key or entry.get("pix_key") or "").strip()
            key_type = pix_type or entry.get("pix_key_type")

            if key and key_type:
                valid = False
                if key_type == "email":
                    valid = bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", key))
                    if not valid: error_text = "Email inválido!"
                elif key_type == "telefone":
                    clean = re.sub(r"[^\d]", "", key)
                    valid = 10 <= len(clean) <= 11
                    if not valid: error_text = "Telefone inválido! Use 10 ou 11 dígitos."
                elif key_type == "cpf":
                    clean = re.sub(r"[^\d]", "", key)
                    valid = len(clean) == 11
                    if not valid: error_text = "CPF inválido! Use 11 dígitos."
                elif key_type == "cnpj":
                    clean = re.sub(r"[^\d]", "", key)
                    valid = len(clean) == 14
                    if not valid: error_text = "CNPJ inválido! Use 14 dígitos."
                elif key_type == "aleatoria":
                    valid = 8 <= len(key) <= 50
                    if not valid: error_text = "Chave aleatória deve ter entre 8 e 50 caracteres."

                if enabled and not valid:
                    enabled = False
            else:
                if enabled:
                    enabled = False
                    error_text = "Informe a chave PIX e o tipo."

            if pix_key  is not None: entry["pix_key"]      = pix_key.strip()
            if pix_type is not None: entry["pix_key_type"] = pix_type

        elif self.provider_key == "amethys_wallet":
            api_key_val = valores.get("amethys_wallet_api_key")
            if api_key_val is not None:
                entry["api_key"] = api_key_val.strip()
            if enabled and not entry.get("api_key"):
                enabled = False
                error_text = "Informe a API Key da Amethys Wallet."

            fee_val = valores.get("amethys_wallet_customer_pays_fee")
            if isinstance(fee_val, (list, tuple)):
                fee_val = fee_val[0] if fee_val else None
            if fee_val is not None:
                entry["customer_pays_fee"] = (fee_val == "fee_True")

        # ── Persistir ─────────────────────────────────────────────────────────
        entry["enabled"] = enabled
        config[self.provider_key] = entry
        db.save_document("payment_configs", config)

        pagamentos = db.get_document("pagamentos") or {}
        pagamentos[self.provider_key] = enabled
        db.save_document("pagamentos", {}, pagamentos)

        # ── Atualizar UI ───────────────────────────────────────────────────────
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = ConfigurarPagamentos.pagamentos_embed(inter, self.categoria)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=ConfigurarPagamentos.pagamentos_components(inter, self.categoria))

        if error_text:
            await message.error(inter, error_text, followup=True)


def setup(bot: commands.Bot):
    bot.add_cog(ConfigurarPagamentos(bot))