import disnake
from disnake.ext import commands
import aiohttp

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from functions.utils import utils
from . import helpers
from . import config_credenciais
from . import config_mensagem
from . import auth_logs
from . import update_api
from .config_definicoes import DefinicoesView_components, DefinicoesView_embed
from .manage_tasks import ManageTasksView_components, ManageTasksView_embed, ManageTasksSelectView_components, TaskDetailsView_components, ManageTasksSelectView_embed, TaskDetailsView_embed
from .create_task_modal import CreateTaskModal


class Cloud(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channel_send_lock: set = set()  # evita envio duplicado de mensagem de verificação
        # Definir instância do bot para uso global no WebSocket
        update_api.set_bot_instance(bot)
        # Garantir callbacks do WebSocket registrados mesmo se conexão já estiver ativa
        try:
            update_api.register_websocket_callbacks()
        except Exception as e:
            print(f"[Cloud Cog] Falha ao registrar callbacks do WebSocket: {e}")

    async def _definir_preferencias(self, inter: disnake.MessageInteraction):
        await inter.response.send_message("Lógica para definir preferências a ser implementada.", ephemeral=True)

    async def _view_database(self, inter: disnake.MessageInteraction):
        """Mostra preview da database no painel e permite baixar como .txt ephemeral"""
        try:
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            bot_token = cloud_config.get("token")

            if not bot_id or not bot_token:
                await inter.followup.send(f"{emoji.wrong} Bot não configurado.", ephemeral=True)
                return

            from .cloud_config import get_cloud_url
            import aiohttp

            cloud_url = get_cloud_url()
            data_url = f"{cloud_url}/api/bot/database/{bot_id}/data"

            # Buscar dados autenticado com o token do bot
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    data_url,
                    headers={"Authorization": f"Bot {bot_token}"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        await inter.followup.send(f"{emoji.wrong} Erro ao buscar database (HTTP {resp.status}).", ephemeral=True)
                        return
                    payload = await resp.json()

            if not payload.get("success"):
                await inter.followup.send(f"{emoji.wrong} {payload.get('message', 'Erro desconhecido')}", ephemeral=True)
                return

            data_inner = payload["data"]
            stats = data_inner["stats"]
            members = data_inner["members"] or []
            gifts = data_inner["gifts"] or []

            # ── Preview text ──────────────────────────────────────────────────
            total_m    = stats["total_members"]
            verified_m = stats["verified_members"]
            total_g    = stats["total_gifts"]
            active_g   = stats["active_gifts"]
            used_g     = stats["used_gifts"]

            # Últimos 3 membros verificados para preview
            verified_members = [m for m in members if m.get("verified_at")]
            verified_members_sorted = sorted(verified_members, key=lambda m: m.get("verified_at", ""), reverse=True)
            preview_members = verified_members_sorted[:3]

            preview_lines = []
            for m in preview_members:
                name = m.get("username", "N/A")
                uid  = m.get("id", "N/A")
                preview_lines.append(f"`{name}` — `{uid}`")
            members_preview = "\n".join(preview_lines) if preview_lines else "_Nenhum membro verificado_"

            # Últimos 3 gifts para preview
            gifts_sorted = sorted(gifts, key=lambda g: g.get("created_at", ""), reverse=True)
            preview_gifts = gifts_sorted[:3]
            gift_lines = []
            for g in preview_gifts:
                gid    = g.get("id", "N/A")
                status = g.get("status", "N/A")
                count  = g.get("members_count", 0)
                gift_lines.append(f"`{gid}` — {status} — {count} membros")
            gifts_preview = "\n".join(gift_lines) if gift_lines else "_Nenhum gift_"

            mode = db.get_document("custom_mode").get("mode")
            custom_colors = db.get_document("custom_colors") or {}
            primary_color_hex = custom_colors.get("primary", "#5c5ef0")
            accent = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            if mode == "embed":
                embed = disnake.Embed(
                    title="Database — Preview",
                    color=accent,
                )
                embed.add_field(
                    name=f"{emoji.members} Membros",
                    value=f"Total: `{total_m}` | Verificados: `{verified_m}`",
                    inline=False
                )
                embed.add_field(
                    name=f"{emoji.gift} Gifts",
                    value=f"Total: `{total_g}` | Ativos: `{active_g}` | Usados: `{used_g}`",
                    inline=False
                )
                embed.add_field(
                    name="Últimos verificados",
                    value=members_preview,
                    inline=False
                )
                embed.add_field(
                    name="Últimos gifts",
                    value=gifts_preview,
                    inline=False
                )
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Baixar Database (.txt)", style=disnake.ButtonStyle.green, emoji=emoji.download if hasattr(emoji, 'download') else "📥", custom_id="Cloud_DownloadDatabase"),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back"),
                    )
                ]
                await inter.edit_original_message(content=None, embed=embed, components=components)

            else:
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > AmyCloud > **Database**"
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.TextDisplay(
                        f"{emoji.members} **Membros:** `{total_m}` total — `{verified_m}` verificados\n"
                        f"{emoji.gift} **Gifts:** `{total_g}` total — `{active_g}` ativos — `{used_g}` usados"
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.TextDisplay(
                        f"**Últimos verificados:**\n{members_preview}\n\n"
                        f"**Últimos gifts:**\n{gifts_preview}"
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Baixar Database (.txt)", style=disnake.ButtonStyle.green, custom_id="Cloud_DownloadDatabase"),
                    ),
                    accent_colour=accent
                )
                buttons = disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back"),
                )
                await inter.edit_original_message(content=None, components=[container, buttons])

        except Exception as e:
            print(f"Erro ao exibir database: {e}")
            import traceback
            traceback.print_exc()
            try:
                await inter.followup.send(f"{emoji.wrong} Erro ao carregar database: {str(e)}", ephemeral=True)
            except Exception:
                pass

    async def _download_database(self, inter: disnake.MessageInteraction):
        """Busca dados da database e envia como .txt ephemeral"""
        try:
            await inter.response.defer(ephemeral=True)

            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            bot_token = cloud_config.get("token")

            if not bot_id or not bot_token:
                await inter.followup.send(f"{emoji.wrong} Bot não configurado.", ephemeral=True)
                return

            from .cloud_config import get_cloud_url
            import aiohttp
            import io
            from datetime import datetime

            cloud_url = get_cloud_url()
            data_url = f"{cloud_url}/api/bot/database/{bot_id}/data"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    data_url,
                    headers={"Authorization": f"Bot {bot_token}"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        await inter.followup.send(f"{emoji.wrong} Erro ao buscar database (HTTP {resp.status}).", ephemeral=True)
                        return
                    payload = await resp.json()

            if not payload.get("success"):
                await inter.followup.send(f"{emoji.wrong} {payload.get('message', 'Erro desconhecido')}", ephemeral=True)
                return

            data_inner = payload["data"]
            stats   = data_inner["stats"]
            members = data_inner["members"] or []
            gifts   = data_inner["gifts"] or []
            bot_info = data_inner["bot"]

            line  = "═" * 80
            thin  = "─" * 80
            now   = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            sb = []

            # ── BOT INFO ──────────────────────────────────────────────────────
            sb.append(line)
            sb.append(f"  BOT INFO — Exportado em {now}")
            sb.append(line)
            sb.append(f"  Client ID     : {bot_info.get('client_id', 'N/A')}")
            sb.append(f"  Main Server   : {bot_info.get('main_server_id') or 'N/A'}")
            sb.append("")
            sb.append("  ── Membros ──")
            sb.append(f"  Total         : {stats['total_members']}")
            sb.append(f"  Verificados   : {stats['verified_members']}")
            sb.append("")
            sb.append("  ── Gifts ──")
            sb.append(f"  Total         : {stats['total_gifts']}")
            sb.append(f"  Ativos        : {stats['active_gifts']}")
            sb.append(f"  Usados        : {stats['used_gifts']}")
            sb.append(f"  Expirados     : {stats['expired_gifts']}")
            sb.append(line)
            sb.append("")

            # ── MEMBERS ───────────────────────────────────────────────────────
            sb.append(line)
            sb.append(f"  MEMBERS — Total: {len(members)}")
            sb.append(line)
            sb.append("")

            if not members:
                sb.append("  Nenhum membro registrado.")
            else:
                for i, m in enumerate(members, 1):
                    sb.append(f"  [{i:04d}] {thin}")
                    sb.append(f"  ID            : {m.get('id', 'N/A')}")
                    sb.append(f"  Username      : {m.get('username', 'N/A')}")
                    if m.get('discriminator') and m['discriminator'] not in ('', '0'):
                        sb.append(f"  Discriminator : #{m['discriminator']}")
                    sb.append(f"  Email         : {m.get('email') or 'N/A'}")
                    sb.append(f"  IP            : {m.get('ip') or 'N/A'}")
                    sb.append(f"  Verificado em : {m.get('verified_at') or 'N/A'}")
                    sb.append(f"  Access Token  : {m.get('access_token') or 'N/A'}")
                    sb.append(f"  Refresh Token : {m.get('refresh_token') or 'N/A'}")
                    sb.append(f"  Guild ID      : {m.get('guild_id') or 'N/A'}")
                    if m.get('unverified_at'):
                        sb.append(f"  Desverificado : {m['unverified_at']}")
                        sb.append(f"  Motivo        : {m.get('reason') or 'N/A'}")
                    sb.append("")

            sb.append(line)
            sb.append(f"  FIM MEMBERS — {len(members)} exportados")
            sb.append(line)
            sb.append("")

            # ── GIFTS ─────────────────────────────────────────────────────────
            sb.append(line)
            sb.append(f"  GIFTS — Total: {len(gifts)}")
            sb.append(line)
            sb.append("")

            if not gifts:
                sb.append("  Nenhum gift registrado.")
            else:
                for i, g in enumerate(gifts, 1):
                    sb.append(f"  [{i:04d}] {thin}")
                    sb.append(f"  ID            : {g.get('id', 'N/A')}")
                    sb.append(f"  Status        : {g.get('status', 'N/A')}")
                    sb.append(f"  Membros       : {g.get('members_count', 0)}")
                    sb.append(f"  Max Usos      : {g.get('max_uses', 0)}")
                    sb.append(f"  Usos          : {g.get('used_count', 0)}")
                    sb.append(f"  Criado por    : {g.get('created_by') or 'N/A'}")
                    sb.append(f"  Criado em     : {g.get('created_at') or 'N/A'}")
                    if g.get('last_used') and g['last_used'] != '0001-01-01T00:00:00Z':
                        sb.append(f"  Último uso    : {g['last_used']}")
                        sb.append(f"  Último Guild  : {g.get('last_guild_id') or 'N/A'}")
                    sb.append("")

            sb.append(line)
            sb.append(f"  FIM GIFTS — {len(gifts)} exportados")
            sb.append(line)

            txt_content = "\n".join(sb)
            file_bytes = io.BytesIO(txt_content.encode("utf-8"))
            filename = f"database_{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file = disnake.File(file_bytes, filename=filename)

            await inter.followup.send(
                f"{emoji.correct} Database exportada com sucesso! `{stats['total_members']}` membros e `{stats['total_gifts']}` gifts.",
                file=file,
                ephemeral=True
            )

        except Exception as e:
            print(f"Erro ao baixar database: {e}")
            import traceback
            traceback.print_exc()
            try:
                await inter.followup.send(f"{emoji.wrong} Erro ao exportar database: {str(e)}", ephemeral=True)
            except Exception:
                pass

    async def _gerenciar_gift(self, inter: disnake.MessageInteraction):
        """Mostra container ou embed com opções de gerenciamento de gifts"""
        try:
            mode = db.get_document("custom_mode").get("mode")

            if mode == "embed":
                await embed_message.wait(inter)
                primary_color_hex = db.get_document("custom_colors").get("primary")
                embed = disnake.Embed(
                    title=f"Painel > AmyCloud > Gerenciar Gifts",
                    description="Use os botões abaixo para gerenciar os gifts.",
                )
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Criar Gift", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="CloudGift_Create"),
                        disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.grey, emoji=emoji.settings, custom_id="CloudGift_Manage"),
                        disnake.ui.Button(label="Excluir Gifts", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="CloudGift_Delete"),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back")
                    )
                ]
                await inter.edit_original_response(content=None, embed=embed, components=components)
            else:
                await message.wait(inter)
                primary_color_hex = db.get_document("custom_colors").get("primary")
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Gerenciar Gifts**"),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Criar Gift", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="CloudGift_Create"),
                        disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.grey, emoji=emoji.settings, custom_id="CloudGift_Manage"),
                        disnake.ui.Button(label="Excluir Gifts", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="CloudGift_Delete"),
                    ),
                    **container_kwargs
                )
                
                buttons = disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back")
                )
                
                await inter.edit_original_response(content=None, components=[container, buttons])
            
        except Exception as e:
            print(f"Erro ao mostrar gerenciamento de gifts: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro ao carregar gerenciamento de gifts.", ephemeral=True)
                else:
                    await inter.edit_original_response("Erro ao carregar gerenciamento de gifts.")
            except:
                await inter.followup.send("Erro ao carregar gerenciamento de gifts.", ephemeral=True)

    async def _show_delete_options(self, inter: disnake.MessageInteraction):
        """Mostra as opções de deleção de gifts"""
        try:
            mode = db.get_document("custom_mode").get("mode")
            primary_color_hex = db.get_document("custom_colors").get("primary")
            
            buttons = disnake.ui.ActionRow(
                disnake.ui.Button(label="Excluir da Lista", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id="CloudGift_DeleteFromList"),
                disnake.ui.Button(label="Excluir por Código", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="CloudGift_DeleteByCode"),
                disnake.ui.Button(label="Excluir Todos", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="CloudGift_DeleteAll"),
            )
            back_button = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudGift_Back")
            )

            if mode == "embed":
                await embed_message.wait(inter)
                embed = disnake.Embed(
                    title=f"Painel > AmyCloud > Excluir Gifts",
                    description="Selecione um método para excluir os gifts.",
                )
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                await inter.edit_original_response(content=None, embed=embed, components=[buttons, back_button])
            else:
                await message.wait(inter)
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Excluir Gifts**"),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.TextDisplay("Selecione um método para excluir os gifts."),
                    buttons,
                    **container_kwargs
                )
                
                await inter.edit_original_response(content=None, components=[container, back_button])
            
        except Exception as e:
            print(f"Erro ao mostrar opções de deleção de gifts: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro ao carregar opções de deleção.", ephemeral=True)
                else:
                    await inter.edit_original_response("Erro ao carregar opções de deleção.")
            except:
                await inter.followup.send("Erro ao carregar opções de deleção.", ephemeral=True)

    async def _create_gift_modal(self, inter: disnake.MessageInteraction):
        """Mostra modal para criar gift"""
        try:
            from .create_gift_modal import CreateGiftModal
            modal = CreateGiftModal(self.bot)
            await inter.response.send_modal(modal)
        except Exception as e:
            print(f"Erro ao mostrar modal de criar gift: {e}")
            await inter.response.send_message("Erro ao carregar modal de criar gift.", ephemeral=True)

    async def _manage_gifts_select(self, inter: disnake.MessageInteraction):
        """Mostra select menu para gerenciar gifts"""
        try:
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)
            
            await self._load_gifts_for_manage(inter)
        except Exception as e:
            print(f"Erro ao mostrar select de gerenciar gifts: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro ao carregar gerenciamento de gifts.", ephemeral=True)
                else:
                    await inter.edit_original_response("Erro ao carregar gerenciamento de gifts.")
            except:
                await inter.followup.send("Erro ao carregar gerenciamento de gifts.", ephemeral=True)

    async def _handle_manage_gift_select(self, inter: disnake.MessageInteraction):
        """Handler para seleção de gift para gerenciar"""
        try:
            selected_value = inter.values[0]
            # Modais precisam ser enviados diretamente na resposta, sem defer
            await self._manage_gift_modal(inter, selected_value)
                
        except disnake.errors.HTTPException as e:
            if "already been acknowledged" in str(e):
                # Se já foi reconhecido, tentar enviar via followup
                try:
                    await inter.followup.send("Por favor, selecione novamente.", ephemeral=True)
                except:
                    pass
            else:
                print(f"Erro ao processar seleção de gift para gerenciar: {e}")
                try:
                    await inter.followup.send("Erro ao processar seleção.", ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Erro ao processar seleção de gift para gerenciar: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro ao processar seleção.", ephemeral=True)
                else:
                    await inter.followup.send("Erro ao processar seleção.", ephemeral=True)
            except:
                pass

    async def _handle_delete_gift_select(self, inter: disnake.MessageInteraction):
        """Handler para seleção de gift para deletar"""
        try:
            selected_value = inter.values[0]
            # Modais precisam ser enviados diretamente na resposta, sem defer
            await self._delete_gift_modal(inter, selected_value)
                
        except disnake.errors.HTTPException as e:
            if "already been acknowledged" in str(e):
                # Se já foi reconhecido, tentar enviar via followup
                try:
                    await inter.followup.send("Por favor, selecione novamente.", ephemeral=True)
                except:
                    pass
            else:
                print(f"Erro ao processar seleção de gift para deletar: {e}")
                try:
                    await inter.followup.send("Erro ao processar seleção.", ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Erro ao processar seleção de gift para deletar: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro ao processar seleção.", ephemeral=True)
                else:
                    await inter.followup.send("Erro ao processar seleção.", ephemeral=True)
            except:
                pass

    async def _load_gifts_for_manage(self, inter: disnake.MessageInteraction):
        """Carrega gifts para gerenciar"""
        try:
            mode = db.get_document("custom_mode").get("mode")
            primary_color_hex = db.get_document("custom_colors").get("primary")

            # Obter configuração do cloud
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            
            if not bot_id:
                if mode == "embed":
                    embed = disnake.Embed(
                        title=f"{emoji.wrong} Erro",
                        description="Bot não configurado.",
                        color=disnake.Color.red()
                    )
                    await inter.edit_original_response(embed=embed)
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay("Bot não configurado."),
                    )
                    await inter.edit_original_response(components=[container])
                return
            
            # Fazer requisição para obter gifts (funciona via WS ou HTTP fallback)
            from .update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            response = await ws_manager.get_gifts(bot_id)
            
            if not response.get("success"):
                error_message = f"Erro ao carregar gifts: {response.get('message', 'Erro desconhecido')}"
                if mode == "embed":
                    embed = disnake.Embed(
                        title=f"{emoji.wrong} Erro",
                        description=error_message,
                        color=disnake.Color.red()
                    )
                    await inter.edit_original_response(embed=embed)
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay(error_message),
                    )
                    await inter.edit_original_response(components=[container])
                return
            
            gifts = response.get("data", {}).get("gifts", [])
            
            if not gifts:
                back_button = disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="CloudGift_Back"
                )
                if mode == "embed":
                    embed = disnake.Embed(
                        title=f"Painel > AmyCloud > Gerenciamento de Gifts",
                        description="Nenhum gift encontrado para este bot.",
                    )
                    if primary_color_hex:
                        embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    await inter.edit_original_response(embed=embed, components=[disnake.ui.ActionRow(back_button)])
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Gerenciamento de Gifts**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay("Nenhum gift encontrado para este bot."),
                    )
                    await inter.edit_original_response(components=[container, disnake.ui.ActionRow(back_button)])
                return
            
            gifts_to_display = gifts[:125]
            
            gift_chunks = [gifts_to_display[i:i + 25] for i in range(0, len(gifts_to_display), 25)]
            
            selects_components = []
            for i, chunk in enumerate(gift_chunks):
                select = disnake.ui.StringSelect(
                    placeholder=f"Selecione um gift para gerenciar ({i*25 + 1}-{i*25 + len(chunk)})...",
                    custom_id=f"manage_gift_select_{i}",
                    min_values=1,
                    max_values=1
                )
                for gift in chunk:
                    status_emoji = "✅" if gift.get("status") == "active" else "❌"
                    select.add_option(
                        label=f"{status_emoji} {gift.get('id', 'Unknown')[:8]}...",
                        value=gift.get("id"),
                        description=f"{gift.get('members_count', 0)} membros - {gift.get('status', 'unknown')}"
                    )
                selects_components.append(disnake.ui.ActionRow(select))

            back_button = disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="CloudGift_Back"
            )

            if mode == "embed":
                embed = disnake.Embed(
                    title=f"Painel > AmyCloud > Gerenciamento de Gifts",
                    description="Selecione um gift da lista abaixo para gerenciar.",
                )
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                components = selects_components + [disnake.ui.ActionRow(back_button)]
                await inter.edit_original_response(embed=embed, components=components)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                container_children = [
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Gerenciamento de Gifts**"),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                ]
                container_children.extend(selects_components)
                container = disnake.ui.Container(*container_children, **container_kwargs)
                
                await inter.edit_original_response(components=[container, disnake.ui.ActionRow(back_button)])
            
        except Exception as e:
            print(f"Erro ao carregar gifts para gerenciar: {e}")
            try:
                error_message = f"Erro ao carregar gifts: {str(e)}"
                if db.get_document("custom_mode").get("mode") == "embed":
                    embed = disnake.Embed(title=f"{emoji.wrong} Erro", description=error_message, color=disnake.Color.red())
                    await inter.edit_original_response(embed=embed)
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay(error_message),
                    )
                    await inter.edit_original_response(components=[container])
            except:
                await inter.followup.send(f"{emoji.wrong} Erro ao carregar gifts: {str(e)}", ephemeral=True)

    async def _delete_gifts_select(self, inter: disnake.MessageInteraction):
        """Mostra select menu para deletar gifts"""
        try:
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

            await self._load_gifts_for_delete(inter)
        except Exception as e:
            print(f"Erro ao mostrar select de deletar gifts: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro ao carregar seleção de gifts para deletar.", ephemeral=True)
                else:
                    await inter.edit_original_response("Erro ao carregar seleção de gifts para deletar.")
            except:
                await inter.followup.send("Erro ao carregar seleção de gifts para deletar.", ephemeral=True)

    async def _load_gifts_for_delete(self, inter: disnake.MessageInteraction):
        """Carrega gifts para deletar"""
        try:
            mode = db.get_document("custom_mode").get("mode")
            primary_color_hex = db.get_document("custom_colors").get("primary")

            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            
            if not bot_id:
                if mode == "embed":
                    embed = disnake.Embed(title=f"{emoji.wrong} Erro", description="Bot não configurado.", color=disnake.Color.red())
                    await inter.edit_original_response(embed=embed)
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay("Bot não configurado."),
                    )
                    await inter.edit_original_response(components=[container])
                return
            
            from .update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            # Funciona via WS ou HTTP fallback automaticamente
            
            response = await ws_manager.get_gifts(bot_id)
            
            if not response.get("success"):
                error_message = f"Erro ao carregar gifts: {response.get('message', 'Erro desconhecido')}"
                if mode == "embed":
                    embed = disnake.Embed(title=f"{emoji.wrong} Erro", description=error_message, color=disnake.Color.red())
                    await inter.edit_original_response(embed=embed)
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay(error_message),
                    )
                    await inter.edit_original_response(components=[container])
                return
            
            gifts = response.get("data", {}).get("gifts", [])
            
            if not gifts:
                back_button = disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="CloudGift_Back"
                )
                if mode == "embed":
                    embed = disnake.Embed(
                        title=f"Painel > AmyCloud > Deletar Gifts",
                        description="Nenhum gift encontrado para este bot."
                    )
                    if primary_color_hex:
                        embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    await inter.edit_original_response(embed=embed, components=[disnake.ui.ActionRow(back_button)])
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Deletar Gifts**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay("Nenhum gift encontrado para este bot."),
                    )
                    await inter.edit_original_response(components=[container, disnake.ui.ActionRow(back_button)])
                return
            
            gifts_to_display = gifts[:125]
            
            gift_chunks = [gifts_to_display[i:i + 25] for i in range(0, len(gifts_to_display), 25)]
            
            selects_components = []
            for i, chunk in enumerate(gift_chunks):
                select = disnake.ui.StringSelect(
                    placeholder=f"Selecione um gift para deletar ({i*25 + 1}-{i*25 + len(chunk)})...",
                    custom_id=f"delete_gift_select_{i}",
                    min_values=1,
                    max_values=1
                )
                for gift in chunk:
                    status_emoji = "✅" if gift.get("status") == "active" else "❌"
                    select.add_option(
                        label=f"{status_emoji} {gift.get('id', 'Unknown')[:8]}...",
                        value=gift.get("id"),
                        description=f"{gift.get('members_count', 0)} membros - {gift.get('status', 'unknown')}"
                    )
                selects_components.append(disnake.ui.ActionRow(select))

            back_button = disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="CloudGift_Back"
            )
            
            if mode == "embed":
                embed = disnake.Embed(
                    title=f"Painel > AmyCloud > Deletar Gifts",
                    description="Selecione um gift da lista abaixo para deletar."
                )
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                components = selects_components + [disnake.ui.ActionRow(back_button)]
                await inter.edit_original_response(embed=embed, components=components)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                container_children = [
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Deletar Gifts**"),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                ]
                container_children.extend(selects_components)
                container = disnake.ui.Container(*container_children, **container_kwargs)
                
                await inter.edit_original_response(components=[container, disnake.ui.ActionRow(back_button)])
            
        except Exception as e:
            print(f"Erro ao carregar gifts para deletar: {e}")
            try:
                error_message = f"Erro ao carregar gifts: {str(e)}"
                if db.get_document("custom_mode").get("mode") == "embed":
                    embed = disnake.Embed(title=f"{emoji.wrong} Erro", description=error_message, color=disnake.Color.red())
                    await inter.edit_original_response(embed=embed)
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay(error_message),
                    )
                    await inter.edit_original_response(components=[container])
            except:
                await inter.followup.send(f"{emoji.wrong} Erro ao carregar gifts: {str(e)}", ephemeral=True)

    async def _manage_gift_modal(self, inter: disnake.MessageInteraction, gift_id: str):
        """Mostra modal para editar gift"""
        try:
            from .edit_gift_modal import EditGiftModal
            modal = EditGiftModal(self.bot, gift_id)
            await inter.response.send_modal(modal)
            
        except Exception as e:
            print(f"Erro ao mostrar modal de editar gift: {e}")
            await inter.response.send_message("Erro ao abrir modal de edição.", ephemeral=True)

    async def _delete_gift_modal(self, inter: disnake.MessageInteraction, gift_id: str):
        """Mostra modal para confirmar deleção de gift"""
        try:
            from .delete_gift_modal import DeleteGiftModal
            modal = DeleteGiftModal(self.bot, gift_id)
            await inter.response.send_modal(modal)
            
        except Exception as e:
            print(f"Erro ao mostrar modal de deletar gift: {e}")
            await inter.response.send_message("Erro ao abrir modal de confirmação.", ephemeral=True)

    async def process_log_channel(self, inter: disnake.ModalInteraction, channel_id_str: str):
        try:
            channel_id = int(channel_id_str)
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                if not inter.response.is_done():
                    await inter.response.send_message(f"{emoji.wrong} Canal não encontrado. ID: {channel_id}\n\n**Verifique se:**\n• O canal existe\n• O bot tem acesso ao canal\n• O ID está correto", ephemeral=True)
                return
                
            if not isinstance(channel, disnake.TextChannel):
                if not inter.response.is_done():
                    await inter.response.send_message(f"{emoji.wrong} O canal encontrado não é um canal de texto. Tipo: {type(channel).__name__}", ephemeral=True)
                return
                
        except (ValueError, TypeError):
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.wrong} ID do canal inválido. Use apenas números.", ephemeral=True)
            return

        # Salvar configuração
        cloud_config = db.get_document("cloud_data") or {}
        cloud_config["log_channel_id"] = channel_id
        db.save_document("cloud_data", cloud_config)

        # Atualizar o painel principal diretamente
        await self.display_cloud_panel(inter)


    def CloudComponents(self, inter: disnake.MessageInteraction, status_text: str) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        cloud_conf = db.get_document("cloud_data") or {}
        is_configured = bool(cloud_conf.get("client_id"))
        # Credentials can only be configured if verified role and logs are set
        verified_role_id = (db.get_document("cargos") or {}).get("cargo_verificado")
        has_verified_role = bool(verified_role_id)
        has_log_channel = bool(cloud_conf.get("log_channel_id"))
        can_configure_credentials = has_verified_role and has_log_channel

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > **AmyCloud**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(status_text),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Gerenciar Tarefas", style=disnake.ButtonStyle.green, emoji=emoji.reload, custom_id="Cloud_ManageTasks", disabled=not is_configured),
                    disnake.ui.Button(label="Editar Credenciais", style=disnake.ButtonStyle.grey, emoji=emoji.robot, custom_id="Cloud_ConfigurarCredenciais", disabled=not can_configure_credentials),
                    disnake.ui.Button(label="Preferencias", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id="Cloud_Definicoes", disabled=not is_configured),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Gerenciar Mensagens", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id="Cloud_DefinirMensagens", disabled=not is_configured),
                    disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.grey, emoji=emoji.gift, custom_id="Cloud_GerenciarGift", disabled=not is_configured),
                    disnake.ui.Button(label="Definir Logs", style=disnake.ButtonStyle.grey, emoji=emoji.textc, custom_id="Cloud_DefinirLogs"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Ver Database", style=disnake.ButtonStyle.grey, emoji=emoji.database if hasattr(emoji, 'database') else emoji.search, custom_id="Cloud_ViewDatabase", disabled=not is_configured),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PainelInicial"),
            )
        ]

    def CloudEmbed(self, inter: disnake.Interaction, status_text: str):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title=f"AmyCloud",
            description=status_text,
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color
        
        cloud_conf = db.get_document("cloud_data") or {}
        is_configured = bool(cloud_conf.get("client_id"))
        # Credentials can only be configured if verified role and logs are set
        verified_role_id = (db.get_document("cargos") or {}).get("cargo_verificado")
        has_verified_role = bool(verified_role_id)
        has_log_channel = bool(cloud_conf.get("log_channel_id"))
        can_configure_credentials = has_verified_role and has_log_channel

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Gerenciar Tarefas", style=disnake.ButtonStyle.green, emoji=emoji.reload, custom_id="Cloud_ManageTasks", disabled=not is_configured),
                disnake.ui.Button(label="Editar Credenciais", style=disnake.ButtonStyle.grey, emoji=emoji.robot, custom_id="Cloud_ConfigurarCredenciais", disabled=not can_configure_credentials),
                disnake.ui.Button(label="Preferencias", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id="Cloud_Definicoes", disabled=not is_configured),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Gerenciar Mensagens", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id="Cloud_DefinirMensagens", disabled=not is_configured),
                disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.grey, emoji=emoji.gift, custom_id="Cloud_GerenciarGift", disabled=not is_configured),
                disnake.ui.Button(label="Definir Logs", style=disnake.ButtonStyle.grey, emoji=emoji.textc, custom_id="Cloud_DefinirLogs"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ver Database", style=disnake.ButtonStyle.grey, emoji=emoji.database if hasattr(emoji, 'database') else emoji.search, custom_id="Cloud_ViewDatabase", disabled=not is_configured),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PainelInicial"),
            )
        ]
        return embed, components

    async def display_cloud_panel(self, inter):
        mode = db.get_document("custom_mode").get("mode")
        if hasattr(inter, 'response') and not inter.response.is_done():
            try:
                await inter.response.defer()
            except Exception:
                pass
        status_text = await helpers.get_status_text(inter)
        if mode == "embed":
            embed, components = self.CloudEmbed(inter, status_text)
            if hasattr(inter, "edit_original_message"):
                await inter.edit_original_message(content=None, embed=embed, components=components)
            elif hasattr(inter, "message") and hasattr(inter.message, "edit"):
                await inter.message.edit(content=None, embed=embed, components=components)
        else:
            components = self.CloudComponents(inter, status_text)
            if hasattr(inter, "edit_original_message"):
                await inter.edit_original_message(content=None, components=components)
            elif hasattr(inter, "message") and hasattr(inter.message, "edit"):
                await inter.message.edit(content=None, components=components)

    @commands.Cog.listener("on_message_interaction")
    async def on_message_interaction(self, inter: disnake.MessageInteraction):
        # Este listener é genérico. Movi a lógica específica para on_dropdown.
        # Se houver outras interações de mensagem (não botões/dropdowns) no futuro,
        # a lógica pode ser adicionada aqui.
        pass

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("Cloud"):
            return
        
        # Defer a interação imediatamente para evitar timeout (exceto para modais que já respondem)
        # Verificar se é um caso que precisa de defer (não modais)
        needs_defer = inter.component.custom_id not in [
            "CloudTasks_Create",
            "Cloud_SetCredentialsModal",
            "Cloud_DefinirLogs",
            "CloudGift_Create",
            "CloudGift_DeleteByCode",
            "CloudGift_DeleteAll",
            "CloudMsgEdit_EditButton",
            "CloudMsgEdit_EditContent",
            "CloudSend_External",
            "Cloud_DownloadDatabase",
        ]
        
        if needs_defer and not inter.response.is_done():
            try:
                await inter.response.defer()
            except (disnake.errors.InteractionResponded, disnake.errors.NotFound, disnake.errors.HTTPException):
                pass  # Já foi respondido ou interação expirou
            
        match inter.component.custom_id:
            case "Cloud_ManageTasks":
                cloud_conf = db.get_document("cloud_data") or {}
                if not bool(cloud_conf.get("client_id")):
                    if inter.response.is_done():
                        await inter.followup.send(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    else:
                        await inter.response.send_message(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    return
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    await embed_message.wait(inter)
                    embed, components = ManageTasksView_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await message.wait(inter)
                    components = await ManageTasksView_components(inter)
                    await inter.edit_original_message(content=None, components=components)
            case "CloudTasks_Create":
                await inter.response.send_modal(CreateTaskModal(self.bot))
            case "CloudTasks_Manage":
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    await embed_message.wait(inter)
                    embed, components = ManageTasksSelectView_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await message.wait(inter)
                    components = ManageTasksSelectView_components(inter)
                    await inter.edit_original_message(content=None, components=components)
            case "CloudTasks_Back":
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    await embed_message.wait(inter)
                    embed, components = ManageTasksView_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await message.wait(inter)
                    components = await ManageTasksView_components(inter)
                    await inter.edit_original_message(components=components)
            case "Cloud_ConfigurarCredenciais":
                await config_credenciais.show_panel(inter)
            case "Cloud_CopyAuthURL":
                from .cloud_config import get_auth_callback_url
                auth_url = get_auth_callback_url()
                if inter.response.is_done():
                    await inter.followup.send(f"{auth_url}", ephemeral=True)
                else:
                    await inter.response.send_message(f"{auth_url}", ephemeral=True)
            case "Cloud_SetCredentialsModal":
                cloud_config = db.get_document("cloud_data") or {}
                bot_token = cloud_config.get("token", "")
                client_secret = cloud_config.get("client_secret", "")
                await inter.response.send_modal(config_credenciais.CredentialModal(self.bot, bot_token=bot_token, client_secret=client_secret))
            case "Cloud_MainPanel":
                await self.display_cloud_panel(inter)
            case "Cloud_Back":
                await self.display_cloud_panel(inter)
            case "Cloud_Definicoes":
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    await embed_message.wait(inter)
                    embed, components = DefinicoesView_embed(inter)
                    await inter.edit_original_message(embed=embed, components=components)
                else:
                    await message.wait(inter)
                    components = DefinicoesView_components(inter)
                    await inter.edit_original_message(components=components)
            case "Cloud_Preferencias":
                cloud_conf = db.get_document("cloud_data") or {}
                if not bool(cloud_conf.get("client_id")):
                    if inter.response.is_done():
                        await inter.followup.send(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    else:
                        await inter.response.send_message(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    return
                await self._definir_preferencias(inter)
            case "Cloud_DefinirMensagens":
                cloud_conf = db.get_document("cloud_data") or {}
                if not bool(cloud_conf.get("client_id")):
                    if inter.response.is_done():
                        await inter.followup.send(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    else:
                        await inter.response.send_message(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    return
                await config_mensagem.show_panel(inter)
            case "Cloud_DefinirLogs":
                cloud_config = db.get_document("cloud_data") or {}
                current_log_channel_id = str(cloud_config.get("log_channel_id", ""))
                
                modal = helpers.LogChannelModal(self.bot, current_channel_id=current_log_channel_id)
                await inter.response.send_modal(modal)
            case "Cloud_GerenciarGift":
                cloud_conf = db.get_document("cloud_data") or {}
                if not bool(cloud_conf.get("client_id")):
                    if inter.response.is_done():
                        await inter.followup.send(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    else:
                        await inter.response.send_message(f"{emoji.off} AmyCloud não está configurado. Use 'Editar Credenciais' primeiro.", ephemeral=True)
                    return
                await self._gerenciar_gift(inter)
            case "CloudGift_Create":
                await self._create_gift_modal(inter)
            case "CloudGift_Manage":
                await self._manage_gifts_select(inter)
            case "CloudGift_Delete":
                await self._show_delete_options(inter)
            case "CloudGift_DeleteFromList":
                await self._delete_gifts_select(inter)
            case "CloudGift_DeleteByCode":
                from .delete_gift_modal import DeleteGiftByCodeModal
                await inter.response.send_modal(DeleteGiftByCodeModal(self.bot))
            case "CloudGift_DeleteAll":
                from .delete_gift_modal import DeleteAllGiftsModal
                await inter.response.send_modal(DeleteAllGiftsModal(self.bot))
            case "CloudGift_Back":
                await self._gerenciar_gift(inter)
            case "Cloud_ViewDatabase":
                await self._view_database(inter)
            case "Cloud_DownloadDatabase":
                await self._download_database(inter)
            case "Cloud_GetAuthLink":
                cloud_config = db.get_document("cloud_data") or {}
                client_id = cloud_config.get("client_id")

                if not client_id:
                    if inter.response.is_done():
                        await inter.followup.send("O bot da cloud não foi configurado.", ephemeral=True)
                    else:
                        await inter.response.send_message("O bot da cloud não foi configurado.", ephemeral=True)
                    return

                from .cloud_config import get_auth_callback_url
                redirect_uri = get_auth_callback_url()
                state = f"{client_id}-{inter.guild.id}"
                auth_url = (
                    f"https://discord.com/api/oauth2/authorize?client_id={client_id}"
                    f"&redirect_uri={redirect_uri}&response_type=code&scope=identify%20email%20guilds.join"
                    f"&state={state}"
                )

                view = disnake.ui.View()
                view.add_item(disnake.ui.Button(label="Verificar", style=disnake.ButtonStyle.link, url=auth_url))
                if inter.response.is_done():
                    await inter.followup.send(
                        "Clique no botão abaixo para ser verificado:",
                        view=view,
                        ephemeral=True
                    )
                else:
                    await inter.response.send_message(
                        "Clique no botão abaixo para ser verificado:",
                        view=view,
                        ephemeral=True
                    )
            case "CloudMsgEdit_CycleStyle":
                cloud_config = db.get_document("cloud_data") or {}
                message_config = cloud_config.setdefault("message_verify", {})
                
                styles = ["embed", "content", "container"]
                current_style = message_config.get("message_style", "embed")
                try:
                    current_index = styles.index(current_style)
                    new_style = styles[(current_index + 1) % len(styles)]
                except ValueError:
                    new_style = "embed"
                
                message_config["message_style"] = new_style
                db.save_document("cloud_data", cloud_config)
                await config_mensagem.show_panel(inter)

            case "CloudMsgEdit_EditButton":
                cloud_config = db.get_document("cloud_data") or {}
                button_data = cloud_config.get("message_verify", {}).get("button", {})
                await inter.response.send_modal(config_mensagem.EditButtonModal(data=button_data))

            case "CloudMsgEdit_EditContent":
                cloud_config = db.get_document("cloud_data") or {}
                message_config = cloud_config.get("message_verify", {})
                style = message_config.get("message_style", "embed")

                try:
                    if style == "embed":
                        embed_data = message_config.get("embed", {})
                        await inter.response.send_modal(config_mensagem.EditEmbedModal(data=embed_data))
                    elif style == "content":
                        content_data = message_config.get("content", {})
                        await inter.response.send_modal(config_mensagem.EditContentModal(data=content_data))
                    else:  # container
                        container_data = message_config.get("container", {})
                        await inter.response.send_modal(config_mensagem.EditContainerModal(data=container_data))
                except disnake.errors.NotFound:
                    try:
                        await inter.followup.send("A interação expirou. Clique novamente no botão.", ephemeral=True)
                    except Exception:
                        pass
                    return

            case "CloudMsgEdit_Send":
                await config_mensagem.show_send_panel(inter, self.bot)

            case "CloudMsgEdit_Preview":
                # This should send an ephemeral message with the preview
                if not inter.response.is_done():
                    await inter.response.defer(ephemeral=True)
                cloud_config = db.get_document("cloud_data") or {}
                message_config = cloud_config.get("message_verify", {})
                style = message_config.get("message_style", "embed")
                
                send_kwargs = {}
                
                if style == "embed":
                    embed_data = message_config.get("embed", {})
                    if not embed_data:
                        embed_data = {"title": "Título de Exemplo", "description": "Descrição de exemplo."}
                    normalized_data = utils.normalize_embed_data(embed_data)
                    embed = disnake.Embed.from_dict(normalized_data)
                    send_kwargs["embed"] = embed
                elif style == "content": # content
                    content_data = message_config.get("content", {})
                    send_kwargs["content"] = content_data.get("content", "Conteúdo de exemplo.")
                    # Previewing with imag69e might be complex, skipping for now.
                elif style == "container":
                    data = message_config.get("container", {})
                    container = config_mensagem.ContainerUtils.montar_container(
                        conteudo=data.get("content"), 
                        imagem_url=data.get("image_url"), 
                        cor_hex=data.get("color"),
                        thumbnail_url=data.get("thumbnail_url")
                    )
                    send_kwargs["components"] = [container]
                    send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)


                button_data = message_config.get("button", {})
                style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
                button = disnake.ui.Button(
                    label=button_data.get("label", "Verificar"),
                    style=style_map.get(button_data.get("style", "green")),
                    emoji=config_mensagem.get_validated_emoji(button_data.get("emoji")),
                    custom_id="do_nothing"
                )
                
                view = disnake.ui.View()
                view.add_item(button)

                if style != "container":
                    send_kwargs["view"] = view
                else:
                    if "components" not in send_kwargs:
                        send_kwargs["components"] = []
                    send_kwargs["components"].append(disnake.ui.ActionRow(button))
                
                if style == "container":
                    await inter.followup.send(**send_kwargs, ephemeral=True)
                else:
                    await inter.followup.send(**send_kwargs, ephemeral=True)
            case "CloudSend_External":
                await inter.response.send_modal(config_mensagem.ExternalSendModal(self.bot))
            
            # Handler para botão de localização
            # case _ if inter.component.custom_id.startswith("auth_location_"):
            #     await auth_logs.handle_location_button(inter)


    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("Cloud") and \
           not inter.component.custom_id.startswith("manage_gift_select") and \
           not inter.component.custom_id.startswith("delete_gift_select"):
            return

        custom_id = inter.component.custom_id
        
        if custom_id == "CloudTasks_Select":
            # Fazer defer primeiro para evitar erro de interação já reconhecida
            try:
                if not inter.response.is_done():
                    await inter.response.defer()
            except disnake.errors.HTTPException:
                pass  # Já foi respondido, continuar
            
            try:
                if not inter.values:
                    try:
                        await inter.followup.send("Nenhuma task selecionada.", ephemeral=True)
                    except:
                        pass
                    return
                
                task_id = inter.values[0]
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    try:
                        await embed_message.wait(inter, followup=True)
                    except:
                        pass
                    embed, components = TaskDetailsView_embed(inter, task_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    try:
                        await message.wait(inter, followup=True)
                    except:
                        pass
                    components = TaskDetailsView_components(inter, task_id)
                    await inter.edit_original_message(components=components)
            except Exception as e:
                print(f"Erro no handler CloudTasks_Select: {e}")
                try:
                    await inter.followup.send(f"Erro ao processar seleção: {str(e)}", ephemeral=True)
                except:
                    pass

        elif custom_id.startswith("manage_gift_select"):
            await self._handle_manage_gift_select(inter)

        elif custom_id.startswith("delete_gift_select"):
            await self._handle_delete_gift_select(inter)

        elif custom_id == "CloudDefinicoes_Select":
            # Fazer defer primeiro para evitar erro de interação já reconhecida
            try:
                if not inter.response.is_done():
                    await inter.response.defer()
            except disnake.errors.HTTPException:
                pass  # Já foi respondido, continuar

            setting_key = inter.values[0]
            
            cloud_config = db.get_document("cloud_data") or {}
            definitions = cloud_config.setdefault("definitions", {})
            setting = definitions.setdefault(setting_key, {})
            setting["enabled"] = not setting.get("enabled", False)
            
            db.save_document("cloud_data", cloud_config)

            from .update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            # Tentar enviar definições para a API silenciosamente (sem avisos)
            try:
                if ws_manager.is_connected():
                    await ws_manager.update_definitions(definitions)
            except Exception as e:
                print(f"[Cloud Cog] Erro ao enviar definições: {e}")
            
            # Atualizar a mensagem com o novo estado das preferências
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = DefinicoesView_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                components = DefinicoesView_components(inter)
                await inter.edit_original_message(components=components)

        if inter.component.custom_id == "CloudSend_ChannelSelect":
            lock_key = inter.id
            if lock_key in self._channel_send_lock:
                return
            self._channel_send_lock.add(lock_key)
            try:
                if not inter.response.is_done():
                    await inter.response.defer(ephemeral=True)
            except disnake.errors.HTTPException:
                pass
            
            try:
                channel_id = int(inter.values[0])
                channel = self.bot.get_channel(channel_id)
            except (ValueError, IndexError):
                channel = None

            if not channel:
                if db.get_document("custom_mode").get("mode") == "embed":
                    await inter.edit_original_message(content=f"{emoji.wrong} Canal não encontrado.", embed=None, components=[])
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong}\n-# **Erro**"),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay("Canal não encontrado."),
                    )
                    await inter.edit_original_message(components=[container])
                self._channel_send_lock.discard(lock_key)
                return

            cloud_config = db.get_document("cloud_data") or {}
            message_config = cloud_config.get("message_verify", {})
            
            success, error_message = await config_mensagem._send_verification_message(channel, message_config)
            self._channel_send_lock.discard(lock_key)
            
            if success:
                if db.get_document("custom_mode").get("mode") == "embed":
                    await inter.edit_original_message(content=f"{emoji.correct} Mensagem de verificação enviada para {channel.mention}.", embed=None, components=[])
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.correct} Mensagem de verificação enviada para {channel.mention}."),
                    )
                    await inter.edit_original_message(components=[container])
            else:
                if db.get_document("custom_mode").get("mode") == "embed":
                    await inter.edit_original_message(content=f"{emoji.wrong} {error_message}", embed=None, components=[])
                else:
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} {error_message}"),
                    )
                    await inter.edit_original_message(components=[container])


def setup(bot: commands.Bot):

    bot.add_cog(Cloud(bot))