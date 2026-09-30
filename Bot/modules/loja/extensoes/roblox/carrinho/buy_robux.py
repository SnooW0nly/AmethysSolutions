import disnake
import aiohttp
from disnake.ext import commands
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message
from .config import get_roblox_config, calcular_preco_robux, calcular_robux_bruto, calcular_robux_sem_taxa, MESSAGES
from .roblox_orders import create_order, get_user_active_order
from .ticket_manager import RobloxTicketManager

# Importa utilitários das preferências da loja
from modules.loja.preferences.utils import check_store_hours, get_terms, check_maintenance


async def fetch_roblox_user(username: str) -> Optional[dict]:
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    users = data.get("data", [])
                    if users:
                        return users[0]
    except Exception:
        pass
    return None


async def fetch_roblox_avatar_thumbnail(roblox_user_id: int) -> Optional[str]:
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={roblox_user_id}&size=150x150&format=Png&isCircular=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("data", [])
                    if items:
                        return items[0].get("imageUrl")
    except Exception:
        pass
    return None


def _build_decline_message(mode: str, primary_color_hex: Optional[str]):
    """Monta a mensagem de usuário incorreto respeitando o modo."""
    text = "📃 Usuário incorreto. Reinicie o processo com seu nick correto."
    if mode == "embed":
        embed = disnake.Embed(description=text)
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)
        return {"embeds": [embed], "components": []}
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(text),
                    **container_kwargs,
                )
            ],
            "flags": disnake.MessageFlags(is_components_v2=True),
        }


def _build_blocked_message(mode: str, primary_color_hex: Optional[str], reason: str):
    """Monta mensagem de bloqueio (manutenção / fora de horário) respeitando o modo."""
    if mode == "embed":
        embed = disnake.Embed(description=reason)
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)
        return {"embed": embed, "components": []}
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(reason),
                    **container_kwargs,
                )
            ],
            "flags": disnake.MessageFlags(is_components_v2=True),
        }


def _build_terms_message(
    mode: str,
    primary_color_hex: Optional[str],
    terms_text: str,
    confirm_custom_id: str,
    order_type: str,
    roblox_actual_name: str,
    robux_qty: int,
    robux_bruto: int,
    preco_total: float,
    gamepass_name: str = "",
    thumbnail_url: Optional[str] = None,
    roblox_user_id: int = 0,
    cobrir_taxa: bool = True,
):
    """
    Monta a mensagem de termos para o usuário aceitar antes de criar o ticket.
    confirm_custom_id é o custom_id original do botão de confirmação (ConfirmRobux ou ConfirmGamepass).
    """
    # Botões de aceitar / recusar termos
    # Codificamos o confirm_custom_id dentro do custom_id do botão de aceite
    # para saber para onde redirecionar após aceite.
    # Usamos prefixo RobloxCart_AcceptTerms: + confirm_custom_id
    accept_id = f"RobloxCart_AcceptTerms:{confirm_custom_id}"
    if len(accept_id) > 100:
        accept_id = accept_id[:97] + "..."

    action_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Aceitar e Continuar",
            style=disnake.ButtonStyle.green,
            emoji=emoji.correct,
            custom_id=accept_id,
        ),
        disnake.ui.Button(
            label="Recusar",
            style=disnake.ButtonStyle.red,
            emoji=emoji.wrong,
            custom_id="RobloxCart_DeclineTerms",
        ),
    )

    profile_url = f"https://www.roblox.com/users/{roblox_user_id}/profile"

    taxa_label = "Sim (loja cobre)" if cobrir_taxa else "Não (você paga a taxa no Roblox)"

    if order_type == "robux":
        resumo = (
            f"**Resumo do pedido:**\n"
            f"-# Robux solicitados: `{robux_qty} R$`\n"
            f"-# Robux brutos (gamepass): `{robux_bruto} R$`\n"
            f"-# Cobre taxa (30%): {taxa_label}\n"
            f"-# Valor total: `R$ {preco_total:.2f}`"
        )
    else:
        resumo = (
            f"**Resumo do pedido:**\n"
            f"-# Gamepass: `{gamepass_name}`\n"
            f"-# Robux da gamepass: `{robux_qty} R$`\n"
            f"-# Robux brutos: `{robux_bruto} R$`\n"
            f"-# Valor total: `R$ {preco_total:.2f}`"
        )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            title="📜 Termos da Loja",
            description=(
                f"Leia e aceite os termos antes de prosseguir.\n\n"
                f"**Roblox:** [{roblox_actual_name}]({profile_url})\n\n"
                f"{resumo}\n\n"
                f"─────────────────────\n"
                f"{terms_text}"
            ),
        )
        if embed_color:
            embed.color = embed_color
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        return {"embed": embed, "components": [action_row]}
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        header_content = (
            f"## 📜 Termos da Loja\n"
            f"Leia e aceite os termos antes de prosseguir.\n\n"
            f"**[{roblox_actual_name}]({profile_url})**"
        )

        inner_items = []
        if thumbnail_url:
            inner_items.append(
                disnake.ui.Section(
                    disnake.ui.TextDisplay(header_content),
                    accessory=disnake.ui.Thumbnail(media=thumbnail_url),
                )
            )
        else:
            inner_items.append(disnake.ui.TextDisplay(header_content))

        inner_items += [
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(resumo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(f"**Termos:**\n{terms_text}"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            action_row,
        ]

        return {
            "components": [disnake.ui.Container(*inner_items, **container_kwargs)],
            "flags": disnake.MessageFlags(is_components_v2=True),
        }


class RobuxBuyModal(disnake.ui.Modal):
    def __init__(self):
        config = get_roblox_config()
        min_robux = config["min_robux"]
        max_robux = config["max_robux"]
        delivery_method = config.get("delivery_method", "gamepass")

        components_list = [
            disnake.ui.TextInput(
                label="Seu nick no Roblox",
                custom_id="roblox_nick",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=30,
                placeholder="Ex: robuxuniverse",
            ),
            disnake.ui.TextInput(
                label=f"Quantidade de Robux ({min_robux} - {max_robux})",
                custom_id="robux_qty",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=10,
                placeholder="Ex: 1000",
            ),
            disnake.ui.TextInput(
                label="Cobrir taxa do Roblox (30%)?",
                custom_id="cobrir_taxa",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=3,
                placeholder="SIM ou NÃO",
                value="SIM",
            ),
        ]

        # Se entrega via grupo, pede o link/nome do grupo que o comprador vai entrar
        if delivery_method == "group":
            components_list.append(
                disnake.ui.TextInput(
                    label="Confirme: já entrou no grupo da loja?",
                    custom_id="group_confirm",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=3,
                    placeholder="SIM",
                )
            )

        super().__init__(
            title="Comprar Robux",
            custom_id="RobloxCart_RobuxModal",
            components=components_list,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        config = get_roblox_config()

        async def _edit(**kwargs):
            try:
                await inter.edit_original_response(**kwargs)
            except Exception:
                try:
                    await inter.followup.send(ephemeral=True, **kwargs)
                except Exception:
                    pass

        if not config["enabled"]:
            await _edit(content=MESSAGES["system_disabled"])
            return

        if not config["robux_sale_enabled"]:
            await _edit(content=MESSAGES["robux_disabled"])
            return

        # ── Verificar manutenção ──
        is_maintenance, maint_msg = check_maintenance(inter.user.id, inter.guild)
        if is_maintenance:
            await _edit(content=maint_msg)
            return

        # ── Verificar horário ──
        is_open, hours_msg = check_store_hours()
        if not is_open:
            await _edit(content=hours_msg)
            return

        valores = inter.resolved_values
        roblox_nick = str(valores.get("roblox_nick", "")).strip()
        robux_qty_str = str(valores.get("robux_qty", "")).strip()
        cobrir_taxa_raw = str(valores.get("cobrir_taxa", "SIM")).strip().upper()
        cobrir_taxa = cobrir_taxa_raw not in ("NAO", "NÃO", "NO", "N", "0", "FALSE", "NÃO")

        try:
            robux_qty = int(robux_qty_str)
        except Exception:
            await _edit(content=MESSAGES["invalid_quantity"].format(min=config["min_robux"], max=config["max_robux"]))
            return

        if robux_qty < config["min_robux"] or robux_qty > config["max_robux"]:
            await _edit(content=MESSAGES["invalid_quantity"].format(min=config["min_robux"], max=config["max_robux"]))
            return

        roblox_user = await fetch_roblox_user(roblox_nick)
        if not roblox_user:
            await _edit(content=MESSAGES["user_not_found"])
            return

        roblox_user_id = roblox_user.get("id")
        roblox_display_name = roblox_user.get("displayName", roblox_nick)
        roblox_actual_name = roblox_user.get("name", roblox_nick)

        robux_bruto = calcular_robux_bruto(robux_qty) if cobrir_taxa else calcular_robux_sem_taxa(robux_qty)
        preco_total = calcular_preco_robux(robux_bruto, config["preco_por_mil"])
        taxa_label = "Sim (loja cobre)" if cobrir_taxa else "Não (você paga a taxa no Roblox)"

        delivery_method = config.get("delivery_method", "gamepass")
        delivery_method_label = "🎮 Gamepass" if delivery_method == "gamepass" else f"{emoji.group} Group Funds"

        thumbnail_url = await fetch_roblox_avatar_thumbnail(roblox_user_id)
        profile_url = f"https://www.roblox.com/users/{roblox_user_id}/profile"

        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        confirm_custom_id = f"RobloxCart_ConfirmRobux:{roblox_user_id}:{roblox_actual_name}:{robux_qty}:{robux_bruto}:{preco_total}:{int(cobrir_taxa)}"

        action_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Sim, este sou eu", style=disnake.ButtonStyle.green, emoji=emoji.correct, custom_id=confirm_custom_id),
            disnake.ui.Button(label="Não, não sou eu", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="RobloxCart_DeclineUser"),
            disnake.ui.Button(label="Ver perfil", style=disnake.ButtonStyle.link, url=profile_url),
        )

        if mode == "embed":
            embed_color = None
            if primary_color_hex:
                embed_color = int(primary_color_hex.replace("#", ""), 16)
            embed = disnake.Embed(
                title="Este é você?",
                description=(
                    f"Confirme que este é o seu perfil no Roblox antes de prosseguir.\n\n"
                    f"**Usuário:** [{roblox_actual_name}]({profile_url})\n"
                    f"**Display:** `{roblox_display_name}`\n"
                    f"**ID:** `{roblox_user_id}`\n\n"
                    f"**Resumo do pedido:**\n"
                    f"-# Robux solicitados: `{robux_qty} R$`\n"
                    f"-# Robux brutos: `{robux_bruto} R$`\n"
                    f"-# Cobre taxa (30%): {taxa_label}\n"
                    f"-# Entrega: `{delivery_method_label}`\n"
                    f"-# Valor total: `R$ {preco_total:.2f}`"
                ),
            )
            if embed_color:
                embed.color = embed_color
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            await _edit(embed=embed, components=[action_row])
        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            inner_items = []
            if thumbnail_url:
                inner_items.append(
                    disnake.ui.Section(
                        disnake.ui.TextDisplay(
                            f"## Este é você?\n"
                            f"Confirme que este é o seu perfil antes de prosseguir.\n\n"
                            f"**[{roblox_actual_name}]({profile_url})**\n"
                            f"-# Display: `{roblox_display_name}` · ID: `{roblox_user_id}`"
                        ),
                        accessory=disnake.ui.Thumbnail(media=thumbnail_url),
                    )
                )
            else:
                inner_items.append(
                    disnake.ui.TextDisplay(
                        f"## Este é você?\n"
                        f"Confirme que este é o seu perfil antes de prosseguir.\n\n"
                        f"**[{roblox_actual_name}]({profile_url})**\n"
                        f"-# Display: `{roblox_display_name}` · ID: `{roblox_user_id}`"
                    )
                )

            inner_items += [
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"**Resumo do pedido:**\n"
                    f"-# Robux solicitados: `{robux_qty} R$`\n"
                    f"-# Robux brutos: `{robux_bruto} R$`\n"
                    f"-# Cobre taxa (30%): {taxa_label}\n"
                    f"-# Entrega: `{delivery_method_label}`\n"
                    f"-# Valor total: `R$ {preco_total:.2f}`"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                action_row,
            ]

            components = [disnake.ui.Container(*inner_items, **container_kwargs)]
            await _edit(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
            )


class GamepassBuyModal(disnake.ui.Modal):
    def __init__(self):
        config = get_roblox_config()
        min_robux = config["min_robux"]
        max_robux = config["max_robux"]
        super().__init__(
            title="Comprar Gamepass",
            custom_id="RobloxCart_GamepassModal",
            components=[
                disnake.ui.TextInput(
                    label="Seu nick no Roblox",
                    custom_id="roblox_nick",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=30,
                    placeholder="Ex: robuxuniverse",
                ),
                disnake.ui.TextInput(
                    label="Nome da gamepass desejada",
                    custom_id="gamepass_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=80,
                    placeholder="Ex: 2x EXP | Dark Blade",
                ),
                disnake.ui.TextInput(
                    label=f"Robux da gamepass ({min_robux} - {max_robux})",
                    custom_id="gamepass_robux",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                    placeholder="Ex: 1000",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        config = get_roblox_config()

        async def _edit(**kwargs):
            try:
                await inter.edit_original_response(**kwargs)
            except Exception:
                try:
                    await inter.followup.send(ephemeral=True, **kwargs)
                except Exception:
                    pass

        if not config["enabled"]:
            await _edit(content=MESSAGES["system_disabled"])
            return

        if not config["gamepass_sale_enabled"]:
            await _edit(content=MESSAGES["gamepass_disabled"])
            return

        # ── Verificar manutenção ──
        is_maintenance, maint_msg = check_maintenance(inter.user.id, inter.guild)
        if is_maintenance:
            await _edit(content=maint_msg)
            return

        # ── Verificar horário ──
        is_open, hours_msg = check_store_hours()
        if not is_open:
            await _edit(content=hours_msg)
            return

        valores = inter.resolved_values
        roblox_nick = str(valores.get("roblox_nick", "")).strip()
        gamepass_name = str(valores.get("gamepass_name", "")).strip()
        robux_qty_str = str(valores.get("gamepass_robux", "")).strip()

        try:
            robux_qty = int(robux_qty_str)
        except Exception:
            await _edit(
                content=MESSAGES["invalid_quantity"].format(min=config["min_robux"], max=config["max_robux"]),
            )
            return

        if robux_qty < config["min_robux"] or robux_qty > config["max_robux"]:
            await _edit(
                content=MESSAGES["invalid_quantity"].format(min=config["min_robux"], max=config["max_robux"]),
            )
            return

        roblox_user = await fetch_roblox_user(roblox_nick)
        if not roblox_user:
            await _edit(content=MESSAGES["user_not_found"])
            return

        roblox_user_id = roblox_user.get("id")
        roblox_display_name = roblox_user.get("displayName", roblox_nick)
        roblox_actual_name = roblox_user.get("name", roblox_nick)

        robux_bruto = calcular_robux_bruto(robux_qty)
        preco_total = calcular_preco_robux(robux_qty, config["preco_por_mil"])

        thumbnail_url = await fetch_roblox_avatar_thumbnail(roblox_user_id)
        profile_url = f"https://www.roblox.com/users/{roblox_user_id}/profile"

        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        safe_gamepass_name = gamepass_name.replace(":", "_").replace(";", "_")[:60]
        confirm_custom_id = f"RobloxCart_ConfirmGamepass:{roblox_user_id}:{roblox_actual_name}:{robux_qty}:{robux_bruto}:{preco_total}:{safe_gamepass_name}"

        if len(confirm_custom_id) > 100:
            confirm_custom_id = confirm_custom_id[:97] + "..."

        action_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Sim, este sou eu", style=disnake.ButtonStyle.green, emoji=emoji.correct, custom_id=confirm_custom_id),
            disnake.ui.Button(label="Não, não sou eu", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="RobloxCart_DeclineUser"),
            disnake.ui.Button(label="Ver perfil", style=disnake.ButtonStyle.link, url=profile_url),
        )

        if mode == "embed":
            embed_color = None
            if primary_color_hex:
                embed_color = int(primary_color_hex.replace("#", ""), 16)
            embed = disnake.Embed(
                title="Este é você?",
                description=(
                    f"Confirme que este é o seu perfil no Roblox antes de prosseguir.\n\n"
                    f"**Usuário:** [{roblox_actual_name}]({profile_url})\n"
                    f"**Display:** `{roblox_display_name}`\n"
                    f"**ID:** `{roblox_user_id}`\n\n"
                    f"**Resumo do pedido:**\n"
                    f"-# Gamepass: `{gamepass_name}`\n"
                    f"-# Robux da gamepass: `{robux_qty} R$`\n"
                    f"-# Robux brutos: `{robux_bruto} R$`\n"
                    f"-# Valor total: `R$ {preco_total:.2f}`"
                ),
            )
            if embed_color:
                embed.color = embed_color
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            await _edit(
                embed=embed,
                components=[action_row],
            )
        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            inner_items = []
            if thumbnail_url:
                inner_items.append(
                    disnake.ui.Section(
                        disnake.ui.TextDisplay(
                            f"## Este é você?\n"
                            f"Confirme que este é o seu perfil antes de prosseguir.\n\n"
                            f"**[{roblox_actual_name}]({profile_url})**\n"
                            f"-# Display: `{roblox_display_name}` · ID: `{roblox_user_id}`"
                        ),
                        accessory=disnake.ui.Thumbnail(media=thumbnail_url),
                    )
                )
            else:
                inner_items.append(
                    disnake.ui.TextDisplay(
                        f"## Este é você?\n"
                        f"Confirme que este é o seu perfil antes de prosseguir.\n\n"
                        f"**[{roblox_actual_name}]({profile_url})**\n"
                        f"-# Display: `{roblox_display_name}` · ID: `{roblox_user_id}`"
                    )
                )

            inner_items += [
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"**Resumo do pedido:**\n"
                    f"-# Gamepass: `{gamepass_name}`\n"
                    f"-# Robux da gamepass: `{robux_qty} R$`\n"
                    f"-# Robux brutos: `{robux_bruto} R$`\n"
                    f"-# Valor total: `R$ {preco_total:.2f}`"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                action_row,
            ]

            components = [disnake.ui.Container(*inner_items, **container_kwargs)]
            await _edit(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
            )


class CalcularPrecoModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Calcular Preço de Robux",
            custom_id="RobloxCart_CalcularModal",
            components=[
                disnake.ui.TextInput(
                    label="Quantos Robux deseja calcular?",
                    custom_id="robux_qty",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                    placeholder="Ex: 1000",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        config = get_roblox_config()

        robux_qty_str = str(inter.resolved_values.get("robux_qty", "")).strip()
        try:
            robux_qty = int(robux_qty_str)
        except Exception:
            await inter.followup.send(f"{emoji.wrong} Insira um número válido.", ephemeral=True)
            return

        if robux_qty < 1:
            await inter.followup.send(f"{emoji.wrong} A quantidade deve ser maior que 0.", ephemeral=True)
            return

        preco_total = calcular_preco_robux(robux_qty, config["preco_por_mil"])
        robux_bruto = calcular_robux_bruto(robux_qty)

        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        if mode == "embed":
            embed_color = None
            if primary_color_hex:
                embed_color = int(primary_color_hex.replace("#", ""), 16)
            embed = disnake.Embed(
                title="🧮 Calculadora de Preços",
                description=(
                    f"**Cálculo realizado:**\n\n"
                    f"-# Robux solicitados: `{robux_qty} R$`\n"
                    f"-# Taxa Roblox (30%): `{robux_qty * 0.30:.0f} R$`\n"
                    f"-# Robux brutos necessários: `{robux_bruto} R$`\n"
                    f"-# Preço por 1000 Robux: `R$ {config['preco_por_mil']:.2f}`\n\n"
                    f"**💰 Valor total: `R$ {preco_total:.2f}`**"
                ),
            )
            if embed_color:
                embed.color = embed_color
            await inter.followup.send(embed=embed, ephemeral=True)
        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"## 🧮 Calculadora de Preços\n\n"
                        f"-# Robux solicitados: `{robux_qty} R$`\n"
                        f"-# Taxa Roblox (30%): `{robux_qty * 0.30:.0f} R$`\n"
                        f"-# Robux brutos necessários: `{robux_bruto} R$`\n"
                        f"-# Preço por 1000 Robux: `R$ {config['preco_por_mil']:.2f}`\n\n"
                        f"**💰 Valor total: `R$ {preco_total:.2f}`**"
                    ),
                    **container_kwargs,
                )
            ]
            await inter.followup.send(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True,
            )


async def _handle_confirm_robux(
    inter: disnake.MessageInteraction,
    bot: commands.Bot,
    parts: list,
):
    """
    Lógica compartilhada de confirmação de Robux.
    Chamada tanto do botão ConfirmRobux direto quanto do botão AcceptTerms
    que embute um ConfirmRobux no custom_id.
    """
    if len(parts) < 6:
        await inter.response.send_message(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
        return

    try:
        roblox_user_id = int(parts[1])
        roblox_actual_name = parts[2]
        robux_qty = int(parts[3])
        robux_bruto = int(parts[4])
        preco_total = float(parts[5])
        cobrir_taxa = bool(int(parts[6])) if len(parts) > 6 else True
    except Exception:
        await inter.response.send_message(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
        return

    existing = get_user_active_order(inter.user.id, inter.guild.id)
    if existing:
        await inter.response.send_message(
            f"{emoji.wrong} Você já tem um pedido ativo (`{existing['order_id']}`). Finalize ou cancele antes de abrir um novo.",
            ephemeral=True,
        )
        return

    mode = db.get_document("custom_mode").get("mode")
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    if mode == "embed":
        await inter.response.edit_message(
            content=f"{emoji.loading} Criando seu carrinho, aguarde...",
            embeds=[],
            components=[],
        )
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        await inter.response.edit_message(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.loading} Criando seu carrinho, aguarde..."),
                    **container_kwargs,
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )

    order_id = create_order(
        user_id=inter.user.id,
        guild_id=inter.guild.id,
        order_type="robux",
        roblox_username=roblox_actual_name,
        roblox_user_id=roblox_user_id,
        quantity=robux_qty,
        robux_bruto=robux_bruto,
        total_price=preco_total,
        extra={"cobrir_taxa": cobrir_taxa},
    )

    await RobloxTicketManager.create_ticket(
        bot=bot,
        inter=inter,
        order_id=order_id,
        order_type="robux",
    )


async def _handle_confirm_gamepass(
    inter: disnake.MessageInteraction,
    bot: commands.Bot,
    parts: list,
):
    """
    Lógica compartilhada de confirmação de Gamepass.
    Chamada tanto do botão ConfirmGamepass direto quanto do botão AcceptTerms.
    """
    if len(parts) < 7:
        await inter.response.send_message(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
        return

    try:
        roblox_user_id = int(parts[1])
        roblox_actual_name = parts[2]
        robux_qty = int(parts[3])
        robux_bruto = int(parts[4])
        preco_total = float(parts[5])
        gamepass_name = parts[6].replace("_", " ")
    except Exception:
        await inter.response.send_message(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
        return

    existing = get_user_active_order(inter.user.id, inter.guild.id)
    if existing:
        await inter.response.send_message(
            f"{emoji.wrong} Você já tem um pedido ativo (`{existing['order_id']}`). Finalize ou cancele antes de abrir um novo.",
            ephemeral=True,
        )
        return

    mode = db.get_document("custom_mode").get("mode")
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    if mode == "embed":
        await inter.response.edit_message(
            content=f"{emoji.loading} Criando seu carrinho, aguarde...",
            embeds=[],
            components=[],
        )
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        await inter.response.edit_message(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.loading} Criando seu carrinho, aguarde..."),
                    **container_kwargs,
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )

    order_id = create_order(
        user_id=inter.user.id,
        guild_id=inter.guild.id,
        order_type="gamepass",
        roblox_username=roblox_actual_name,
        roblox_user_id=roblox_user_id,
        quantity=robux_qty,
        robux_bruto=robux_bruto,
        total_price=preco_total,
        extra={"gamepass_name": gamepass_name},
    )

    await RobloxTicketManager.create_ticket(
        bot=bot,
        inter=inter,
        order_id=order_id,
        order_type="gamepass",
    )


class BuyRobuxHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        # ── Seletor de tipo (quando ambos Robux e Gamepass estão ativos) ──
        if custom_id == "Roblox_SelecionarTipo":
            config = get_roblox_config()
            if not config["enabled"]:
                await inter.response.send_message(MESSAGES["system_disabled"], ephemeral=True)
                return

            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            mode = db.get_document("custom_mode").get("mode")

            btn_robux = config.get("btn_robux", {})
            btn_gamepass = config.get("btn_gamepass", {})

            def style_from_str(s):
                return {
                    "blurple": disnake.ButtonStyle.blurple,
                    "green": disnake.ButtonStyle.green,
                    "red": disnake.ButtonStyle.red,
                    "grey": disnake.ButtonStyle.grey,
                    "gray": disnake.ButtonStyle.grey,
                }.get(str(s).lower(), disnake.ButtonStyle.blurple)

            def parse_emoji(e):
                if not e:
                    return None
                if isinstance(e, str) and e.startswith("<"):
                    try:
                        return disnake.PartialEmoji.from_str(e)
                    except Exception:
                        return None
                return e

            action_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=btn_robux.get("label", "Comprar Robux"),
                    style=style_from_str(btn_robux.get("style", "blurple")),
                    emoji=parse_emoji(btn_robux.get("emoji", "💎")),
                    custom_id="Roblox_ComprarRobux",
                ),
                disnake.ui.Button(
                    label=btn_gamepass.get("label", "Comprar Gamepass"),
                    style=style_from_str(btn_gamepass.get("style", "blurple")),
                    emoji=parse_emoji(btn_gamepass.get("emoji", "🎮")),
                    custom_id="Roblox_ComprarGamepass",
                ),
            )

            body_text = "Selecione o que deseja comprar:"

            if mode == "embed":
                embed_color = None
                if primary_color_hex:
                    embed_color = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(description=body_text)
                if embed_color:
                    embed.color = embed_color
                await inter.response.send_message(embed=embed, components=[action_row], ephemeral=True)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                components = [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(body_text),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        action_row,
                        **container_kwargs,
                    )
                ]
                await inter.response.send_message(
                    components=components,
                    flags=disnake.MessageFlags(is_components_v2=True),
                    ephemeral=True,
                )
            return

        # ── Abrir modais de compra ──
        elif custom_id == "Roblox_ComprarRobux":
            config = get_roblox_config()
            if not config["enabled"]:
                await inter.response.send_message(MESSAGES["system_disabled"], ephemeral=True)
                return
            if not config["robux_sale_enabled"]:
                await inter.response.send_message(MESSAGES["robux_disabled"], ephemeral=True)
                return
            await inter.response.send_modal(RobuxBuyModal())

        elif custom_id == "Roblox_ComprarGamepass":
            config = get_roblox_config()
            if not config["enabled"]:
                await inter.response.send_message(MESSAGES["system_disabled"], ephemeral=True)
                return
            if not config["gamepass_sale_enabled"]:
                await inter.response.send_message(MESSAGES["gamepass_disabled"], ephemeral=True)
                return
            await inter.response.send_modal(GamepassBuyModal())

        elif custom_id == "Roblox_CalcularPreco":
            await inter.response.send_modal(CalcularPrecoModal())

        # ── Recusar usuário ──
        elif custom_id == "RobloxCart_DeclineUser":
            mode = db.get_document("custom_mode").get("mode")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            kwargs = _build_decline_message(mode, primary_color_hex)
            await inter.response.edit_message(**kwargs)

        # ── Recusar termos ──
        elif custom_id == "RobloxCart_DeclineTerms":
            mode = db.get_document("custom_mode").get("mode")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            kwargs = _build_blocked_message(
                mode, primary_color_hex,
                f"{emoji.wrong} Você recusou os termos. A compra foi cancelada."
            )
            await inter.response.edit_message(**kwargs)

        # ── Aceitar termos → redirecionar para o confirm original ──
        elif custom_id.startswith("RobloxCart_AcceptTerms:"):
            # Extrai o confirm_custom_id original embutido
            inner_id = custom_id[len("RobloxCart_AcceptTerms:"):]
            parts = inner_id.split(":")

            if parts[0] == "RobloxCart_ConfirmRobux":
                await _handle_confirm_robux(inter, self.bot, parts)
            elif parts[0] == "RobloxCart_ConfirmGamepass":
                await _handle_confirm_gamepass(inter, self.bot, parts)
            else:
                await inter.response.send_message(f"{emoji.wrong} Tipo de pedido desconhecido.", ephemeral=True)

        # ── Confirmar usuário Robux (sem termos) ──
        elif custom_id.startswith("RobloxCart_ConfirmRobux:"):
            parts = custom_id.split(":")

            # Verificar termos ANTES de criar o ticket
            terms_enabled, terms_text = get_terms()
            if terms_enabled and terms_text:
                # Precisamos montar a mensagem de termos
                try:
                    roblox_user_id = int(parts[1])
                    roblox_actual_name = parts[2]
                    robux_qty = int(parts[3])
                    robux_bruto = int(parts[4])
                    preco_total = float(parts[5])
                    cobrir_taxa = bool(int(parts[6])) if len(parts) > 6 else True
                except Exception:
                    await inter.response.send_message(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
                    return

                mode = db.get_document("custom_mode").get("mode")
                colors = db.get_document("custom_colors") or {}
                primary_color_hex = colors.get("primary")
                thumbnail_url = await fetch_roblox_avatar_thumbnail(roblox_user_id)

                kwargs = _build_terms_message(
                    mode=mode,
                    primary_color_hex=primary_color_hex,
                    terms_text=terms_text,
                    confirm_custom_id=custom_id,
                    order_type="robux",
                    roblox_actual_name=roblox_actual_name,
                    robux_qty=robux_qty,
                    robux_bruto=robux_bruto,
                    preco_total=preco_total,
                    thumbnail_url=thumbnail_url,
                    roblox_user_id=roblox_user_id,
                    cobrir_taxa=cobrir_taxa,
                )
                await inter.response.edit_message(**kwargs)
                return

            await _handle_confirm_robux(inter, self.bot, parts)

        # ── Confirmar usuário Gamepass (sem termos) ──
        elif custom_id.startswith("RobloxCart_ConfirmGamepass:"):
            parts = custom_id.split(":")

            # Verificar termos ANTES de criar o ticket
            terms_enabled, terms_text = get_terms()
            if terms_enabled and terms_text:
                try:
                    roblox_user_id = int(parts[1])
                    roblox_actual_name = parts[2]
                    robux_qty = int(parts[3])
                    robux_bruto = int(parts[4])
                    preco_total = float(parts[5])
                    gamepass_name = parts[6].replace("_", " ") if len(parts) > 6 else ""
                except Exception:
                    await inter.response.send_message(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
                    return

                mode = db.get_document("custom_mode").get("mode")
                colors = db.get_document("custom_colors") or {}
                primary_color_hex = colors.get("primary")
                thumbnail_url = await fetch_roblox_avatar_thumbnail(roblox_user_id)

                kwargs = _build_terms_message(
                    mode=mode,
                    primary_color_hex=primary_color_hex,
                    terms_text=terms_text,
                    confirm_custom_id=custom_id,
                    order_type="gamepass",
                    roblox_actual_name=roblox_actual_name,
                    robux_qty=robux_qty,
                    robux_bruto=robux_bruto,
                    preco_total=preco_total,
                    gamepass_name=gamepass_name,
                    thumbnail_url=thumbnail_url,
                    roblox_user_id=roblox_user_id,
                )
                await inter.response.edit_message(**kwargs)
                return

            await _handle_confirm_gamepass(inter, self.bot, parts)


def setup(bot: commands.Bot):
    bot.add_cog(BuyRobuxHandler(bot))