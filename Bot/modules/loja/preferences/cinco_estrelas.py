"""
Sistema de avaliação de 5 estrelas
Envia painel de avaliação na DM do usuário após finalizar uma compra.
Se comentário estiver on, abre modal para o usuário digitar antes de enviar.
O resultado vai para o canal_de_evento_de_compras.
"""

import disnake
from disnake.ext import commands
from datetime import datetime
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji


# ---------------------------------------------------------------------------
# Helpers de config
# ---------------------------------------------------------------------------

def _get_config() -> dict:
    prefs = db.get_document("loja_preferences") or {}
    return prefs.get("cinco_estrelas") or {}


def _save_config(data: dict) -> None:
    prefs = db.get_document("loja_preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    prefs["cinco_estrelas"] = data
    db.save_document("loja_preferences", prefs)


# ---------------------------------------------------------------------------
# Painel de preferências (chamado pelo cog.py de preferências)
# ---------------------------------------------------------------------------

class CincoEstrelasPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode", "components")
        return (
            CincoEstrelasPreferences._panel_embed(inter)
            if mode == "embed"
            else CincoEstrelasPreferences._panel_components(inter)
        )

    @staticmethod
    def _build_status_text(cfg: dict) -> str:
        enabled = cfg.get("enabled", False)
        comment = cfg.get("comment_enabled", False)

        status_icon = emoji.on if enabled else emoji.off
        comment_icon = emoji.on if comment else emoji.off

        return (
            f"{status_icon} **Sistema:** `{'Ativado' if enabled else 'Desativado'}`\n"
            f"{comment_icon} **Comentário:** `{'Ativado' if comment else 'Desativado'}`\n"
            f"-# Quando ativo, o usuário recebe um painel de avaliação na DM após a compra."
        )

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        cfg = _get_config()
        enabled = cfg.get("enabled", False)
        comment = cfg.get("comment_enabled", False)

        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Loja > Preferências > **5 Estrelas**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Configure o sistema de avaliação por estrelas. "
                        "Após cada compra finalizada, o usuário recebe um painel na DM "
                        "para avaliar de 1 a 5 estrelas. O resultado é enviado para o canal de eventos de compras."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(CincoEstrelasPreferences._build_status_text(cfg)),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Desativar Sistema" if enabled else "Ativar Sistema",
                            style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                            emoji=emoji.off if enabled else emoji.on,
                            custom_id="CincoEstrelas_Toggle",
                        ),
                        disnake.ui.Button(
                            label="Desativar Comentário" if comment else "Ativar Comentário",
                            style=disnake.ButtonStyle.red if comment else disnake.ButtonStyle.blurple,
                            emoji=emoji.off if comment else emoji.edit,
                            custom_id="CincoEstrelas_ToggleComment",
                        ),
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Loja_Preferencias",
                    )
                ),
            ]
        }

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        cfg = _get_config()
        enabled = cfg.get("enabled", False)
        comment = cfg.get("comment_enabled", False)

        embed = disnake.Embed(
            title="5 Estrelas — Avaliação",
            description=(
                "-# Painel > Loja > Preferências > **5 Estrelas**\n\n"
                "Configure o sistema de avaliação por estrelas. "
                "Após cada compra finalizada, o usuário recebe um painel na DM "
                "para avaliar de 1 a 5 estrelas.\n\n"
                + CincoEstrelasPreferences._build_status_text(cfg)
            ),
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desativar Sistema" if enabled else "Ativar Sistema",
                    style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                    emoji=emoji.off if enabled else emoji.on,
                    custom_id="CincoEstrelas_Toggle",
                ),
                disnake.ui.Button(
                    label="Desativar Comentário" if comment else "Ativar Comentário",
                    style=disnake.ButtonStyle.red if comment else disnake.ButtonStyle.blurple,
                    emoji=emoji.off if comment else emoji.edit,
                    custom_id="CincoEstrelas_ToggleComment",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Preferencias",
                )
            ),
        ]
        return {"embed": embed, "components": components}

    # ------------------------------------------------------------------
    # Listeners do painel de preferências
    # ------------------------------------------------------------------

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id == "CincoEstrelas_Toggle":
            cfg = _get_config()
            cfg["enabled"] = not cfg.get("enabled", False)
            _save_config(cfg)

            mode = db.get_document("custom_mode").get("mode", "components")
            await inter.response.defer()
            panel = CincoEstrelasPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(
                    **panel, flags=disnake.MessageFlags(is_components_v2=True)
                )

        elif custom_id == "CincoEstrelas_ToggleComment":
            cfg = _get_config()
            cfg["comment_enabled"] = not cfg.get("comment_enabled", False)
            _save_config(cfg)

            mode = db.get_document("custom_mode").get("mode", "components")
            await inter.response.defer()
            panel = CincoEstrelasPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(
                    **panel, flags=disnake.MessageFlags(is_components_v2=True)
                )

        # ------------------------------------------------------------------
        # Listener do painel de avaliação enviado na DM do usuário
        # custom_id: "CincoEstrelas_Rate:{user_id}:{stars}:{guild_id}:{safe_product}"
        # ------------------------------------------------------------------
        elif custom_id.startswith("CincoEstrelas_Rate:"):
            await _handle_star_rating(inter, self.bot)


# ---------------------------------------------------------------------------
# Envio do painel de avaliação para a DM do usuário
# ---------------------------------------------------------------------------

async def send_rating_dm(
    user: disnake.User,
    product_name: str,
    campo_name: str,
    guild_id: int,
) -> None:
    """
    Envia o painel de avaliação por estrelas na DM do usuário.
    Chamado após a entrega do produto em delivery.py.

    IMPORTANTE: emojis personalizados do servidor NÃO funcionam em `label`
    de botão enviado por DM. Por isso os botões usam `emoji=emoji.star` no
    parâmetro correto e um label numérico simples ("1" … "5").
    """
    cfg = _get_config()
    if not cfg.get("enabled", False):
        return

    try:
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except Exception:
                pass

        # Formato custom_id: CincoEstrelas_Rate:{user_id}:{stars}:{guild_id}:{safe_product}
        # safe_product truncado para manter o custom_id dentro de 100 chars
        safe_product = (product_name + " | " + campo_name)[:30].replace(":", "-")

        def star_btn(stars: int) -> disnake.ui.Button:
            # emoji= aceita PartialEmoji/custom emoji mesmo em DM
            # label fica como número para evitar problemas de renderização
            return disnake.ui.Button(
                label=str(stars),
                emoji=emoji.star,
                style=disnake.ButtonStyle.blurple,
                custom_id=f"CincoEstrelas_Rate:{user.id}:{stars}:{guild_id}:{safe_product}",
            )

        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.star} Como foi sua compra?",
                description=(
                    f"Obrigado por comprar **{product_name} | {campo_name}**!\n\n"
                    "Selecione quantas estrelas você dá para esta compra:"
                ),
                color=color or disnake.Color.gold(),
            )
            await user.send(
                embed=embed,
                components=[
                    disnake.ui.ActionRow(
                        star_btn(1), star_btn(2), star_btn(3), star_btn(4), star_btn(5)
                    )
                ],
            )
        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            await user.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.star} Como foi sua compra?\n"
                            f"-# **{product_name} | {campo_name}**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            "Obrigado pela sua compra! Selecione quantas estrelas você dá:"
                        ),
                        disnake.ui.ActionRow(
                            star_btn(1), star_btn(2), star_btn(3), star_btn(4), star_btn(5)
                        ),
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    except disnake.Forbidden:
        pass  # DM fechada — ignorar silenciosamente
    except Exception as e:
        print(f"[5 ESTRELAS] Erro ao enviar DM de avaliação: {e}")


# ---------------------------------------------------------------------------
# Handler do clique nas estrelas
# ---------------------------------------------------------------------------

async def _handle_star_rating(
    inter: disnake.MessageInteraction,
    bot: commands.Bot,
) -> None:
    """
    Processa o clique em uma estrela.
    Se comentário estiver ativo → abre modal.
    Se não → registra direto e desabilita os botões na DM.
    """
    parts = inter.component.custom_id.split(":")
    # partes: CincoEstrelas_Rate | user_id | stars | guild_id | safe_product
    if len(parts) < 5:
        await inter.response.send_message("Erro ao processar avaliação.", ephemeral=True)
        return

    user_id = int(parts[1])
    stars = int(parts[2])
    guild_id = int(parts[3])
    safe_product = parts[4]

    # Segurança: só o próprio usuário pode clicar
    if inter.user.id != user_id:
        await inter.response.send_message(
            "Somente o comprador pode avaliar esta compra.", ephemeral=True
        )
        return

    cfg = _get_config()
    comment_enabled = cfg.get("comment_enabled", False)

    if comment_enabled:
        # Abrir modal para comentário
        await inter.response.send_modal(
            StarRatingModal(
                stars=stars,
                guild_id=guild_id,
                safe_product=safe_product,
                user_id=user_id,
            )
        )
    else:
        # Registrar avaliação sem comentário
        await inter.response.defer()
        await _send_rating_to_log(
            bot=bot,
            guild_id=guild_id,
            user=inter.user,
            stars=stars,
            safe_product=safe_product,
            comment=None,
        )
        await _disable_rating_buttons(inter)


# ---------------------------------------------------------------------------
# Modal de comentário
# ---------------------------------------------------------------------------

class StarRatingModal(disnake.ui.Modal):
    def __init__(
        self,
        stars: int,
        guild_id: int,
        safe_product: str,
        user_id: int,
    ):
        self.stars = stars
        self.guild_id = guild_id
        self.safe_product = safe_product
        self.user_id = user_id

        # label do TextInput não aceita custom emoji — usa unicode simples
        star_display = "★" * stars + "☆" * (5 - stars)

        components = [
            disnake.ui.TextInput(
                label=f"Avaliação: {star_display}",
                custom_id="comment",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Escreva seu comentário sobre a compra...",
                min_length=3,
                max_length=500,
                required=True,
            )
        ]
        super().__init__(title="Deixe seu comentário", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        comment = inter.text_values.get("comment", "").strip()

        await inter.response.defer()

        await _send_rating_to_log(
            bot=inter.bot,
            guild_id=self.guild_id,
            user=inter.user,
            stars=self.stars,
            safe_product=self.safe_product,
            comment=comment,
        )
        await _disable_rating_buttons_modal(inter)


# ---------------------------------------------------------------------------
# Envio para o canal de logs de eventos de compras
# ---------------------------------------------------------------------------

async def _send_rating_to_log(
    bot: commands.Bot,
    guild_id: int,
    user: disnake.User,
    stars: int,
    safe_product: str,
    comment: Optional[str],
) -> None:
    """Envia a avaliação para o canal_de_evento_de_compras."""
    try:
        canais = db.get_document("canais") or {}
        channel_id = canais.get("canal_de_evento_de_compras")
        if not channel_id:
            print("[5 ESTRELAS] Canal de evento de compras não configurado.")
            return

        channel = bot.get_channel(int(channel_id))
        if not channel:
            print(f"[5 ESTRELAS] Canal {channel_id} não encontrado.")
            return

        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except Exception:
                pass

        # emoji.star funciona normalmente em canais do servidor
        star_display = f"{emoji.star} " * stars + "✩ " * (5 - stars)
        product_display = safe_product.replace("-", ":")
        now = datetime.now().strftime("%d/%m/%Y às %H:%M")

        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.star} Nova Avaliação",
                color=color or disnake.Color.gold(),
                timestamp=datetime.utcnow(),
            )
            embed.add_field(name="Usuário", value=f"{user.mention} (`{user.id}`)", inline=False)
            embed.add_field(name="Produto", value=product_display, inline=False)
            embed.add_field(name="Avaliação", value=f"{star_display}**({stars}/5)**", inline=False)
            if comment:
                embed.add_field(name="Comentário", value=comment, inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=now)
            await channel.send(embed=embed)

        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            text_lines = (
                f"# {emoji.star} Nova Avaliação\n"
                f"-# {now}\n\n"
                f"**Usuário:** {user.mention} (`{user.id}`)\n"
                f"**Produto:** {product_display}\n"
                f"**Avaliação:** {star_display}**({stars}/5)**"
            )
            if comment:
                text_lines += f"\n\n**Comentário:**\n> {comment}"

            await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(text_lines),
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        print(f"[5 ESTRELAS] Avaliação de {user.name} ({stars}★) enviada para o canal de eventos.")

        # Atualizar ranking público após avaliação 5 estrelas
        try:
            from tasks.loja.tsk_ranking_publico import RankingPublicoTask
            RankingPublicoTask.trigger_update(bot)
        except Exception as e:
            print(f"[5 ESTRELAS] Erro ao atualizar ranking público: {e}")

    except Exception as e:
        print(f"[5 ESTRELAS] Erro ao enviar avaliação para o log: {e}")
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Helpers de botões desabilitados — reutilizado nos dois disable functions
# ---------------------------------------------------------------------------

def _build_disabled_row() -> disnake.ui.ActionRow:
    """
    Reconstrói a linha de botões desabilitados.
    Usa emoji= com o custom emoji do bot (funciona em DM) e label numérico.
    """
    return disnake.ui.ActionRow(
        *[
            disnake.ui.Button(
                label=str(i),
                emoji=emoji.star,
                style=disnake.ButtonStyle.grey,
                custom_id=f"CincoEstrelas_Done_{i}",
                disabled=True,
            )
            for i in range(1, 6)
        ]
    )


async def _disable_rating_buttons(inter: disnake.MessageInteraction) -> None:
    """Desabilita todos os botões de estrela na DM após avaliação sem comentário."""
    try:
        disabled_row = _build_disabled_row()

        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except Exception:
                pass

        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.correct} Avaliação Enviada!",
                description="Obrigado pela sua avaliação! Ela foi registrada com sucesso.",
                color=color or disnake.Color.green(),
            )
            await inter.edit_original_message(embed=embed, components=[disabled_row])
        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.correct} Avaliação Enviada!\n"
                            "-# Obrigado pela sua avaliação! Ela foi registrada com sucesso."
                        ),
                        disabled_row,
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
    except Exception as e:
        print(f"[5 ESTRELAS] Erro ao desabilitar botões: {e}")


async def _disable_rating_buttons_modal(inter: disnake.ModalInteraction) -> None:
    """Desabilita os botões após avaliação via modal (com comentário)."""
    try:
        disabled_row = _build_disabled_row()

        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except Exception:
                pass

        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.correct} Avaliação Enviada!",
                description="Obrigado pela sua avaliação e comentário! Tudo foi registrado com sucesso.",
                color=color or disnake.Color.green(),
            )
            await inter.edit_original_message(embed=embed, components=[disabled_row])
        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.correct} Avaliação Enviada!\n"
                            "-# Obrigado pela sua avaliação e comentário! Tudo foi registrado."
                        ),
                        disabled_row,
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
    except Exception as e:
        print(f"[5 ESTRELAS] Erro ao desabilitar botões (modal): {e}")


def setup(bot: commands.Bot):
    bot.add_cog(CincoEstrelasPreferences(bot))