import disnake
import asyncio
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import pytz

from modules.automations.repost import helpers
from functions.database import database as db

class RepostTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.repost_task.is_running():
            self.repost_task.start()

    def cog_unload(self):
        self.repost_task.cancel()
    
    def restart_task(self):
        """Reinicia a task de repostagem."""
        self.repost_task.restart()

    @tasks.loop(minutes=5)
    async def repost_task(self):
        try:
            config = helpers.carregar_config()
            if not config.get("ativado", False):
                return

            proxima_repostagem_str = config.get("proxima_repostagem")
            if not proxima_repostagem_str:
                return
                
            agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
            proxima_repostagem_dt = datetime.fromisoformat(proxima_repostagem_str)
            if proxima_repostagem_dt.tzinfo is None:
                proxima_repostagem_dt = pytz.timezone('America/Sao_Paulo').localize(proxima_repostagem_dt)

            if agora >= proxima_repostagem_dt:
                total_produtos, total_repostados, total_removidos = await self._executar_repostagem()
                
                # Agendar próxima repostagem
                config = helpers.carregar_config()
                intervalo_horas = config.get("intervalo_horas", 24)
                nova_proxima_repostagem = agora + timedelta(hours=intervalo_horas)
                config["proxima_repostagem"] = nova_proxima_repostagem.isoformat()
                helpers.salvar_config(config)
                
                await helpers.enviar_log_sucesso(self.bot, total_produtos, total_repostados, total_removidos, intervalo_horas, nova_proxima_repostagem)

        except Exception as e:
            print(f"[REPOST TASK] Erro: {e}")
            import traceback; traceback.print_exc()
            await helpers.enviar_log_erro(self.bot, f"Erro na task de repostagem automática: {str(e)}")

    @repost_task.before_loop
    async def before_repost_task(self):
        await self.bot.wait_until_ready()

    async def _executar_repostagem(self) -> tuple[int, int, int]:
        """Executa a repostagem de todos os produtos. Retorna (total_produtos, total_repostados, total_removidos)"""
        try:
            products = db.get_document("loja_products") or {}
            total_produtos = len(products)
            total_repostados = 0
            total_removidos = 0

            # Obter instância do SendProduct para usar métodos corretos
            send_cog = self.bot.get_cog("SendProduct")
            
            if not send_cog:
                # Criar instância temporária se não existir
                from modules.loja.products.product.send import SendProduct
                send_cog = SendProduct(self.bot)

            for product_id, product in products.items():
                try:
                    messages = product.get("messages") or []
                    if not messages:
                        continue

                    new_messages = []
                    for m in messages:
                        try:
                            guild_id = m.get("guild_id")
                            channel_id = m.get("channel_id")
                            message_id = m.get("message_id")
                            mode = m.get("mode")
                            formatted_desc = m.get("formatted_desc", True)  # Padrão: formatada
                            image_size = m.get("image_size", "normal")  # Padrão: normal

                            if not (guild_id and channel_id and message_id):
                                total_removidos += 1
                                continue

                            guild = self.bot.get_guild(int(guild_id))
                            if not guild:
                                total_removidos += 1
                                continue

                            channel = guild.get_channel(int(channel_id))
                            if not channel:
                                total_removidos += 1
                                continue

                            # Tentar deletar mensagem antiga
                            try:
                                old_msg = await channel.fetch_message(int(message_id))
                                await old_msg.delete()
                                await asyncio.sleep(0.5)
                            except disnake.NotFound:
                                # Mensagem já foi deletada - tentar repostar mesmo assim
                                pass
                            except disnake.HTTPException as e:
                                # Erro ao deletar - tentar repostar mesmo assim
                                print(f"[REPOST] Erro ao deletar mensagem {message_id}: {e}")
                                pass

                            # Repostar mensagem usando métodos do SendProduct
                            new_msg = await self._repostar_mensagem(send_cog, channel, product, product_id, mode, guild, formatted_desc, image_size)
                            if new_msg:
                                # Atualizar entrada na database
                                new_messages.append({
                                    "message_id": new_msg.id,
                                    "channel_id": channel.id,
                                    "guild_id": guild.id,
                                    "mode": mode,
                                    "formatted_desc": formatted_desc,
                                    "image_size": image_size,
                                    "created_at": int(disnake.utils.utcnow().timestamp())
                                })
                                print(f"[REPOST] ✅ Produto {product_id}: Mensagem antiga {message_id} → Nova {new_msg.id}")
                                total_repostados += 1
                            else:
                                # Falhou ao repostar - marcar como removido
                                print(f"[REPOST] ❌ Produto {product_id}: Falhou ao repostar mensagem {message_id}")
                                total_removidos += 1

                        except Exception as e:
                            print(f"[REPOST] Erro ao processar mensagem {m.get('message_id')}: {e}")
                            total_removidos += 1
                            continue

                    # Atualizar lista de mensagens do produto (sempre, mesmo se vazio)
                    products[product_id]["messages"] = new_messages
                    print(f"[REPOST] 📝 Preparando para salvar produto {product_id}:")
                    for nm in new_messages:
                        print(f"[REPOST]    - message_id: {nm.get('message_id')} (tipo: {type(nm.get('message_id'))})")
                    # Salvar após cada produto processado para evitar perda de dados
                    db.save_document("loja_products", products)
                    print(f"[REPOST] 💾 Produto {product_id} salvo com {len(new_messages)} mensagem(ns)")

                except Exception as e:
                    print(f"[REPOST] Erro ao processar produto {product_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            return total_produtos, total_repostados, total_removidos

        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro ao executar repostagem: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, 0, 0

    async def _repostar_mensagem(self, send_cog, channel: disnake.TextChannel, product: dict, product_id: str, mode: str, guild: disnake.Guild, formatted_desc: bool = True, image_size: str = "normal") -> disnake.Message | None:
        """Reposta uma mensagem de produto no canal especificado usando métodos do SendProduct"""
        try:
            if mode == "legacy":
                # Modo legacy usa embed + componentes v1 (sem flag is_components_v2)
                embed = send_cog._build_legacy_embed(product, guild, formatted_desc=formatted_desc)
                components = send_cog._create_buy_button(product_id)
                return await channel.send(embed=embed, components=components)
            
            elif mode in ("container_outside", "container_inside"):
                # Processar banner com tamanho correto
                banner_url = product.get("info", {}).get("banner")
                gallery = None
                files = []
                if banner_url:
                    try:
                        gallery, files = send_cog._build_banner_gallery(banner_url, image_size)
                    except Exception as banner_error:
                        # Se falhar ao processar banner, continuar sem ele
                        print(f"[REPOST] Erro ao processar banner, enviando sem imagem: {banner_error}")
                        gallery = None
                        files = []
                
                # Calcular wrap_len baseado no tamanho
                wrap_len = None
                if formatted_desc:
                    if image_size == "small":
                        wrap_len = 47
                    elif image_size == "medium":
                        wrap_len = 64
                    else:
                        wrap_len = 82
                
                # Usar método do SendProduct que respeita preferências e botões customizados
                image_inside = (mode == "container_inside")
                comps = send_cog._build_container(
                    product, 
                    image_inside=image_inside, 
                    product_id=product_id, 
                    formatted_desc=formatted_desc,
                    banner_gallery=gallery,
                    wrap_len=wrap_len
                )
                return await channel.send(components=comps, files=files, flags=disnake.MessageFlags(is_components_v2=True))
            
            return None

        except Exception as e:
            print(f"[REPOST] Erro ao repostar mensagem no canal {channel.id}: {e}")
            import traceback
            traceback.print_exc()
            return None


def setup(bot: commands.Bot):
    bot.add_cog(RepostTaskCog(bot))
