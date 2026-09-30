"""
Sistema de Ranking Público
===========================
- Painel de preferências acessível via Loja > Preferências > Ranking Público
- Admin configura: ativar/desativar, canal de envio, título customizado,
  quais métricas exibir (mais compras, maior valor, mais recente, 5 estrelas),
  quantidade de posições no ranking, intervalo de atualização, emoji de medalha.
- Admin envia/atualiza a mensagem do ranking no canal configurado.
- A task (tsk_ranking_publico.py) edita a mensagem existente em tempo real.
- Funciona nos dois modos: embed e components (v2).
"""

import disnake
from disnake.ext import commands
from datetime import datetime
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji

# ---------------------------------------------------------------------------
# Chave de persistência
# ---------------------------------------------------------------------------
_DOC_KEY = "ranking_publico"

# Métricas disponíveis
METRICAS = {
    "total_compras":   "Mais Compras",
    "total_gasto":     "Maior Valor Gasto",
    "ultima_compra":   "Compra mais Recente",
    "media_estrelas":  "Melhor Avaliação",
}

EMOJIS_POSICAO = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

# ---------------------------------------------------------------------------
# Helpers de config
# ---------------------------------------------------------------------------

def _get_config() -> dict:
    return db.get_document(_DOC_KEY) or {}


def _save_config(data: dict) -> None:
    db.save_document(_DOC_KEY, data)


def _metricas_ativas(cfg: dict) -> list[str]:
    return cfg.get("metricas", ["total_compras", "total_gasto"])


def _can_enable(cfg: dict) -> bool:
    return bool(cfg.get("channel_id") and _metricas_ativas(cfg))


# ---------------------------------------------------------------------------
# Builder do conteúdo do ranking (compartilhado entre preferências e task)
# ---------------------------------------------------------------------------

def build_ranking_content(cfg: dict, guild: Optional[disnake.Guild] = None, bot=None) -> str:
    """
    Monta o texto completo do ranking com base nas métricas ativas e
    nos dados de compras salvos em loja_purchases / loja_customers.
    Retorna uma string formatada pronta para exibição.
    """
    metricas = _metricas_ativas(cfg)
    top_n    = cfg.get("top_n", 5)
    titulo   = cfg.get("titulo", "🏆 Ranking de Clientes")

    # Coletar dados de compras
    purchases_doc = db.get_document("loja_purchases") or {}
    ratings_doc   = db.get_document("loja_ratings")   or {}  # {user_id: [stars, ...]}

    # Agregar por usuário
    stats: dict[str, dict] = {}
    for purchase in purchases_doc.values() if isinstance(purchases_doc, dict) else []:
        if not isinstance(purchase, dict):
            continue
        uid = str(purchase.get("user_id") or purchase.get("buyer_id") or "")
        if not uid:
            continue
        if uid not in stats:
            stats[uid] = {
                "total_compras": 0,
                "total_gasto":   0.0,
                "ultima_compra": 0,
                "nome":          purchase.get("username") or purchase.get("user_name") or f"<@{uid}>",
            }
        stats[uid]["total_compras"] += 1
        stats[uid]["total_gasto"]   += float(purchase.get("total") or purchase.get("price") or 0)
        ts = purchase.get("timestamp") or purchase.get("created_at") or 0
        if ts > stats[uid]["ultima_compra"]:
            stats[uid]["ultima_compra"] = ts
            stats[uid]["nome"]          = purchase.get("username") or purchase.get("user_name") or f"<@{uid}>"

    # Média de estrelas
    for uid, star_list in ratings_doc.items():
        if uid in stats and isinstance(star_list, list) and star_list:
            stats[uid]["media_estrelas"] = round(sum(star_list) / len(star_list), 1)
        elif uid in stats:
            stats[uid].setdefault("media_estrelas", 0.0)

    for uid in stats:
        stats[uid].setdefault("media_estrelas", 0.0)

    if not stats:
        return f"# {titulo}\n-# Nenhum dado de compras encontrado ainda."

    agora_ts = int(datetime.utcnow().timestamp())
    linhas   = [f"# {titulo}"]
    linhas.append(f"-# Atualizado <t:{agora_ts}:R>")

    for metrica in metricas:
        if metrica not in METRICAS:
            continue

        nome_metrica = METRICAS[metrica]
        reverse = metrica != "ultima_compra"  # "ultima_compra" → mais recente primeiro → sort desc
        reverse = True  # sempre desc

        ordenado = sorted(
            stats.items(),
            key=lambda kv: kv[1].get(metrica, 0),
            reverse=True,
        )[:top_n]

        if not ordenado:
            continue

        linhas.append(f"\n## {_metrica_emoji(metrica)} {nome_metrica}")

        for i, (uid, data) in enumerate(ordenado):
            medal = EMOJIS_POSICAO[i] if i < len(EMOJIS_POSICAO) else f"`{i+1}.`"
            valor = _formatar_valor(metrica, data.get(metrica, 0))
            nome  = data["nome"] if not nome_como_mention(cfg) else f"<@{uid}>"
            linhas.append(f"{medal} {nome} — {valor}")

    return "\n".join(linhas)


def nome_como_mention(cfg: dict) -> bool:
    return cfg.get("mencionar_usuarios", True)


def _metrica_emoji(metrica: str) -> str:
    return {
        "total_compras":  "🛒",
        "total_gasto":    "💰",
        "ultima_compra":  "🕐",
        "media_estrelas": "⭐",
    }.get(metrica, "📊")


def _formatar_valor(metrica: str, valor) -> str:
    if metrica == "total_compras":
        return f"`{int(valor)} compra(s)`"
    elif metrica == "total_gasto":
        return f"`R$ {float(valor):.2f}`"
    elif metrica == "ultima_compra":
        return f"<t:{int(valor)}:d>" if valor else "`—`"
    elif metrica == "media_estrelas":
        stars = "⭐" * round(float(valor))
        return f"`{float(valor):.1f}` {stars}"
    return f"`{valor}`"


# ---------------------------------------------------------------------------
# Envio / edição da mensagem pública do ranking
# ---------------------------------------------------------------------------

async def send_or_update_ranking(bot, cfg: dict, guild: disnake.Guild) -> Optional[int]:
    """
    Envia ou edita a mensagem do ranking no canal configurado.
    Retorna o message_id da mensagem enviada/editada, ou None em caso de erro.
    """
    channel_id = cfg.get("channel_id")
    if not channel_id:
        return None

    channel = guild.get_channel(int(channel_id))
    if not channel:
        return None

    mode   = (db.get_document("custom_mode") or {}).get("mode", "components")
    colors = db.get_document("custom_colors") or {}
    primary_hex = colors.get("primary")
    color = None
    if primary_hex:
        try:
            color = int(primary_hex.replace("#", ""), 16)
        except Exception:
            pass

    content = build_ranking_content(cfg, guild=guild, bot=bot)
    existing_msg_id = cfg.get("message_id")

    try:
        if existing_msg_id:
            try:
                msg = await channel.fetch_message(int(existing_msg_id))
                await _edit_ranking_message(msg, content, mode, color)
                return existing_msg_id
            except (disnake.NotFound, disnake.HTTPException):
                pass  # Mensagem deletada → enviar nova

        # Enviar nova mensagem
        msg = await _send_ranking_message(channel, content, mode, color)
        return msg.id

    except Exception as e:
        print(f"[RANKING PÚBLICO] Erro ao enviar/editar: {e}")
        return None


async def _send_ranking_message(channel, content: str, mode: str, color: Optional[int]):
    if mode == "embed":
        titulo_linha = content.split("\n")[0].lstrip("# ").strip()
        embed = disnake.Embed(
            title=titulo_linha,
            description="\n".join(content.split("\n")[1:]),
            color=color or 0x2F3136,
            timestamp=datetime.utcnow(),
        )
        return await channel.send(embed=embed)
    else:
        container_kwargs = {}
        if color:
            container_kwargs["accent_colour"] = disnake.Colour(color)
        return await channel.send(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(content),
                    **container_kwargs,
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )


async def _edit_ranking_message(msg: disnake.Message, content: str, mode: str, color: Optional[int]):
    if mode == "embed":
        titulo_linha = content.split("\n")[0].lstrip("# ").strip()
        embed = disnake.Embed(
            title=titulo_linha,
            description="\n".join(content.split("\n")[1:]),
            color=color or 0x2F3136,
            timestamp=datetime.utcnow(),
        )
        await msg.edit(embed=embed)
    else:
        container_kwargs = {}
        if color:
            container_kwargs["accent_colour"] = disnake.Colour(color)
        await msg.edit(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(content),
                    **container_kwargs,
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )


# ---------------------------------------------------------------------------
# Painel de Preferências
# ---------------------------------------------------------------------------

class RankingPublicoPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---- status text -------------------------------------------------------

    @staticmethod
    def _build_status_text(cfg: dict) -> str:
        enabled     = cfg.get("enabled", False)
        channel_id  = cfg.get("channel_id")
        metricas    = _metricas_ativas(cfg)
        top_n       = cfg.get("top_n", 5)
        intervalo   = cfg.get("intervalo_minutos", 5)
        mencionar   = cfg.get("mencionar_usuarios", True)

        status_icon = emoji.on if enabled else emoji.off
        canal_str   = f"<#{channel_id}>" if channel_id else "`Não configurado`"
        metricas_str = ", ".join(METRICAS.get(m, m) for m in metricas) or "`Nenhuma`"

        return "\n".join([
            f"{status_icon} **Status:** `{'Ativado' if enabled else 'Desativado'}`",
            f"-# Canal: {canal_str}",
            f"-# Métricas: {metricas_str}",
            f"-# Top posições: `{top_n}`",
            f"-# Atualização a cada: `{intervalo} minuto(s)`",
            f"-# Mencionar usuários: `{'Sim' if mencionar else 'Não'}`",
        ])

    # ---- panel (router) ----------------------------------------------------

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode", "components")
        return (
            RankingPublicoPreferences._panel_embed(inter)
            if mode == "embed"
            else RankingPublicoPreferences._panel_components(inter)
        )

    # ---- components (v2) ---------------------------------------------------

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        cfg     = _get_config()
        enabled = cfg.get("enabled", False)
        can_en  = _can_enable(cfg)

        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Loja > Preferências > **Ranking Público**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Exiba um ranking público dos melhores clientes da loja! "
                        "Configure as métricas, o canal e o intervalo de atualização automática."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(RankingPublicoPreferences._build_status_text(cfg)),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Desativar" if enabled else "Ativar",
                            style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                            emoji=emoji.off if enabled else emoji.on,
                            custom_id="RankingPublico_Toggle",
                            disabled=not can_en and not enabled,
                        ),
                        disnake.ui.Button(
                            label="Configurar Métricas",
                            style=disnake.ButtonStyle.blurple,
                            emoji=emoji.edit,
                            custom_id="RankingPublico_Metricas",
                        ),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Definir Canal",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.settings2,
                            custom_id="RankingPublico_SetCanal",
                        ),
                        disnake.ui.Button(
                            label="Configurações Gerais",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.receipt,
                            custom_id="RankingPublico_SetGeral",
                        ),
                        disnake.ui.Button(
                            label="Intervalo de Atualização",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.clock,
                            custom_id="RankingPublico_SetIntervalo",
                        ),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Publicar / Atualizar Agora",
                            style=disnake.ButtonStyle.blurple,
                            emoji=emoji.double_speech,
                            custom_id="RankingPublico_Publicar",
                            disabled=not enabled,
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

    # ---- embed mode --------------------------------------------------------

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        cfg     = _get_config()
        enabled = cfg.get("enabled", False)
        can_en  = _can_enable(cfg)

        embed = disnake.Embed(
            title="Ranking Público",
            description=(
                "-# Painel > Loja > Preferências > **Ranking Público**\n\n"
                "Exiba um ranking público dos melhores clientes da loja! "
                "Configure as métricas, o canal e o intervalo de atualização automática.\n\n"
                + RankingPublicoPreferences._build_status_text(cfg)
            ),
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desativar" if enabled else "Ativar",
                    style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                    emoji=emoji.off if enabled else emoji.on,
                    custom_id="RankingPublico_Toggle",
                    disabled=not can_en and not enabled,
                ),
                disnake.ui.Button(
                    label="Configurar Métricas",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="RankingPublico_Metricas",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Definir Canal",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.settings2,
                    custom_id="RankingPublico_SetCanal",
                ),
                disnake.ui.Button(
                    label="Configurações Gerais",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.receipt,
                    custom_id="RankingPublico_SetGeral",
                ),
                disnake.ui.Button(
                    label="Intervalo de Atualização",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.clock,
                    custom_id="RankingPublico_SetIntervalo",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Publicar / Atualizar Agora",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.double_speech,
                    custom_id="RankingPublico_Publicar",
                    disabled=not enabled,
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

    # =========================================================================
    # Listeners
    # =========================================================================

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ---- Toggle ativação ------------------------------------------------
        if cid == "RankingPublico_Toggle":
            cfg = _get_config()
            if not cfg.get("enabled", False) and not _can_enable(cfg):
                return await inter.response.send_message(
                    f"{emoji.wrong} Configure o canal e ao menos uma métrica antes de ativar!",
                    ephemeral=True,
                )
            cfg["enabled"] = not cfg.get("enabled", False)
            _save_config(cfg)
            await self._refresh_panel(inter)

        # ---- Definir canal --------------------------------------------------
        elif cid == "RankingPublico_SetCanal":
            await inter.response.send_modal(SetCanalRankingModal())

        # ---- Configurar Métricas --------------------------------------------
        elif cid == "RankingPublico_Metricas":
            await inter.response.defer()
            await self._show_metricas_panel(inter)

        # ---- Configurações Gerais (título, top_n, mencionar) ---------------
        elif cid == "RankingPublico_SetGeral":
            cfg = _get_config()
            await inter.response.send_modal(SetGeralRankingModal(cfg))

        # ---- Intervalo de atualização ---------------------------------------
        elif cid == "RankingPublico_SetIntervalo":
            cfg = _get_config()
            await inter.response.send_modal(SetIntervaloRankingModal(cfg))

        # ---- Publicar / Atualizar Agora -------------------------------------
        elif cid == "RankingPublico_Publicar":
            await inter.response.defer(ephemeral=True)
            cfg = _get_config()
            if not cfg.get("enabled", False):
                return await inter.followup.send(
                    f"{emoji.wrong} Ative o ranking antes de publicar.", ephemeral=True
                )
            guild = inter.guild
            if not guild:
                return await inter.followup.send(f"{emoji.wrong} Não foi possível obter o servidor.", ephemeral=True)

            msg_id = await send_or_update_ranking(self.bot, cfg, guild)
            if msg_id:
                cfg["message_id"] = msg_id
                _save_config(cfg)
                channel = guild.get_channel(int(cfg["channel_id"]))
                ch_mention = channel.mention if channel else f"<#{cfg['channel_id']}>"
                await inter.followup.send(
                    f"{emoji.correct} Ranking publicado/atualizado em {ch_mention}!",
                    ephemeral=True,
                )
            else:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao publicar o ranking. Verifique o canal configurado.",
                    ephemeral=True,
                )

        # ---- Toggle de uma métrica específica (na tela de métricas) --------
        elif cid.startswith("RankingPublico_ToggleMetrica:"):
            metrica = cid.split(":", 1)[1]
            cfg = _get_config()
            metricas = _metricas_ativas(cfg)
            if metrica in metricas:
                metricas.remove(metrica)
            else:
                metricas.append(metrica)
            cfg["metricas"] = metricas
            _save_config(cfg)
            await inter.response.defer()
            await self._show_metricas_panel(inter)

        # ---- Voltar da tela de métricas para o painel principal ------------
        elif cid == "RankingPublico_VoltarDasMetricas":
            await self._refresh_panel(inter)

    # =========================================================================
    # Helpers de UI internos
    # =========================================================================

    async def _refresh_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode", "components")
        if not inter.response.is_done():
            await inter.response.defer()
        panel = RankingPublicoPreferences.panel(inter)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

    async def _show_metricas_panel(self, inter: disnake.MessageInteraction):
        """Tela de seleção de quais métricas incluir no ranking."""
        cfg     = _get_config()
        ativas  = _metricas_ativas(cfg)
        mode    = db.get_document("custom_mode").get("mode", "components")
        colors  = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        lista_txt_linhas = []
        for key, nome in METRICAS.items():
            icone = emoji.on if key in ativas else emoji.off
            lista_txt_linhas.append(f"{icone} **{nome}** (`{key}`)")
        lista_txt = "\n".join(lista_txt_linhas)

        # Linha de botões para cada métrica (2 por row max 5 botões por row)
        rows = []
        metrica_items = list(METRICAS.items())
        for i in range(0, len(metrica_items), 3):
            chunk = metrica_items[i:i+3]
            rows.append(
                disnake.ui.ActionRow(*[
                    disnake.ui.Button(
                        label=("✓ " if key in ativas else "") + nome,
                        style=disnake.ButtonStyle.green if key in ativas else disnake.ButtonStyle.grey,
                        custom_id=f"RankingPublico_ToggleMetrica:{key}",
                    )
                    for key, nome in chunk
                ])
            )

        if mode != "embed":
            children = [
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > Preferências > Ranking Público > **Métricas**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Selecione quais métricas serão exibidas no ranking público. "
                    "Cada métrica gera uma seção separada com o seu próprio top de usuários."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(lista_txt),
                disnake.ui.Separator(),
                *rows,
            ]
            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(*children, **container_kwargs),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="RankingPublico_VoltarDasMetricas",
                        )
                    ),
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        else:
            embed = disnake.Embed(
                title="Configurar Métricas",
                description=(
                    "-# Painel > Loja > Preferências > Ranking Público > **Métricas**\n\n"
                    "Selecione quais métricas serão exibidas no ranking.\n\n"
                    + lista_txt
                ),
            )
            if primary_color_hex:
                embed.color = int(primary_color_hex.replace("#", ""), 16)
            comp_list = [*rows, disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="RankingPublico_VoltarDasMetricas",
                )
            )]
            await inter.edit_original_message(content=None, embed=embed, components=comp_list)


# ---------------------------------------------------------------------------
# Modais
# ---------------------------------------------------------------------------

class SetCanalRankingModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.Label(
                text="Canal do Ranking",
                component=disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal onde o ranking será exibido",
                    custom_id="ranking_canal_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="O bot enviará e atualizará a mensagem do ranking neste canal.",
            ),
        ]
        super().__init__(title="Canal do Ranking Público", components=components, custom_id="RankingPublico_CanalModal")

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            selected = inter.resolved_values.get("ranking_canal_select")
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                channel_id = int(selected)
            elif hasattr(selected, "id"):
                channel_id = int(selected.id)
            else:
                return await inter.response.send_message(f"{emoji.wrong} Canal inválido!", ephemeral=True)

            channel = inter.guild.get_channel(channel_id)
            if not channel:
                return await inter.response.send_message(f"{emoji.wrong} Canal não encontrado!", ephemeral=True)

            cfg = _get_config()
            # Canal mudou → resetar message_id para forçar nova mensagem
            if cfg.get("channel_id") != channel_id:
                cfg.pop("message_id", None)
            cfg["channel_id"] = channel_id
            _save_config(cfg)

            mode = db.get_document("custom_mode").get("mode", "components")
            panel = RankingPublicoPreferences.panel(inter)
            if mode == "embed":
                await inter.response.edit_message(content=None, **panel)
            else:
                await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.wrong} Erro: {str(e)}", ephemeral=True)


class SetGeralRankingModal(disnake.ui.Modal):
    def __init__(self, cfg: dict):
        components = [
            disnake.ui.TextInput(
                label="Título do Ranking",
                custom_id="titulo",
                value=cfg.get("titulo", "🏆 Ranking de Clientes"),
                max_length=80,
                required=True,
                placeholder="🏆 Ranking de Clientes",
            ),
            disnake.ui.TextInput(
                label="Quantidade de posições (Top N)",
                custom_id="top_n",
                value=str(cfg.get("top_n", 5)),
                max_length=2,
                required=True,
                placeholder="5",
            ),
            disnake.ui.TextInput(
                label="Mencionar usuários? (sim/não)",
                custom_id="mencionar",
                value="sim" if cfg.get("mencionar_usuarios", True) else "não",
                max_length=3,
                required=True,
                placeholder="sim",
            ),
        ]
        super().__init__(title="Configurações Gerais do Ranking", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        titulo   = inter.text_values.get("titulo", "🏆 Ranking de Clientes").strip()
        top_n_s  = inter.text_values.get("top_n", "5").strip()
        mencionar_s = inter.text_values.get("mencionar", "sim").strip().lower()

        try:
            top_n = int(top_n_s)
            if not (1 <= top_n <= 10):
                raise ValueError
        except ValueError:
            return await inter.response.send_message(
                f"{emoji.wrong} Top N deve ser um número entre 1 e 10.", ephemeral=True
            )

        mencionar = mencionar_s in ("sim", "s", "yes", "y", "true", "1")

        cfg = _get_config()
        cfg["titulo"]             = titulo
        cfg["top_n"]              = top_n
        cfg["mencionar_usuarios"] = mencionar
        _save_config(cfg)

        mode = db.get_document("custom_mode").get("mode", "components")
        panel = RankingPublicoPreferences.panel(inter)
        if mode == "embed":
            await inter.response.edit_message(content=None, **panel)
        else:
            await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


class SetIntervaloRankingModal(disnake.ui.Modal):
    def __init__(self, cfg: dict):
        components = [
            disnake.ui.TextInput(
                label="Intervalo de atualização (em minutos)",
                custom_id="intervalo",
                value=str(cfg.get("intervalo_minutos", 5)),
                max_length=4,
                required=True,
                placeholder="5",
            ),
        ]
        super().__init__(title="Intervalo de Atualização do Ranking", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        raw = inter.text_values.get("intervalo", "5").strip()
        try:
            intervalo = int(raw)
            if intervalo < 1:
                raise ValueError
        except ValueError:
            return await inter.response.send_message(
                f"{emoji.wrong} Insira um número de minutos válido (mínimo 1).", ephemeral=True
            )

        cfg = _get_config()
        cfg["intervalo_minutos"] = intervalo
        _save_config(cfg)

        mode = db.get_document("custom_mode").get("mode", "components")
        panel = RankingPublicoPreferences.panel(inter)
        if mode == "embed":
            await inter.response.edit_message(content=None, **panel)
        else:
            await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup(bot: commands.Bot):
    bot.add_cog(RankingPublicoPreferences(bot))