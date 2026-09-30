import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import pytz

from modules.automations.msg_auto import helpers
from commands.admin.anunciar.builder import Builder


class MsgAutoTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Inicia a task aqui em vez do on_ready, porque o on_ready pode não
        # disparar se o Cog for carregado depois que o bot já está pronto.
        # O before_loop garante que espera o bot estar pronto antes de executar.
        self.msg_auto_task.start()

    def cog_unload(self):
        self.msg_auto_task.cancel()

    @tasks.loop(minutes=1)
    async def msg_auto_task(self):
        #print("[MsgAutoTask] ✅ Task executando...")
        config = helpers.carregar_config()
        #print(f"[MsgAutoTask] ativado={config.get('ativado')} | qtd mensagens={len(config.get('mensagens', {}))}")
        if not config.get("ativado", False):
            return

        agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
        mensagens = config.get("mensagens", {})

        for msg_id, msg_data in mensagens.items():
            try:
                channel_id = msg_data.get("channel_id")
                intervalo = msg_data.get("intervalo_minutos")
                ultima_enviada_str = msg_data.get("ultima_enviada")
                editor_data = msg_data.get("editor_data", {})

                #print(f"[MsgAutoTask] Processando msg_id={msg_id} | channel_id={channel_id} | intervalo={intervalo}")

                # Verifica se tem algum conteúdo configurado
                embed_data = editor_data.get("embed")
                has_embed = bool(embed_data and isinstance(embed_data, dict) and any(embed_data.get(k) for k in ["title", "description", "color", "footer", "banner", "thumbnail"]))
                has_content = bool(
                    editor_data.get("content")
                    or has_embed
                    or editor_data.get("container")
                    or editor_data.get("externalImage")
                    or editor_data.get("botoes")
                    or editor_data.get("selects")
                )
                if not has_content:
                    #print(f"[MsgAutoTask] msg_id={msg_id} sem conteúdo, pulando.")
                    continue

                if not all([channel_id, intervalo]):
                    #print(f"[MsgAutoTask] msg_id={msg_id} sem channel_id ou intervalo, pulando.")
                    continue

                ultima_enviada = (
                    datetime.fromisoformat(ultima_enviada_str).astimezone(pytz.timezone('America/Sao_Paulo'))
                    if ultima_enviada_str else None
                )

                if ultima_enviada:
                    proximo_envio = ultima_enviada + timedelta(minutes=intervalo)
                    if agora < proximo_envio:
                        #print(f"[MsgAutoTask] msg_id={msg_id} ainda não é hora. Próximo envio: {proximo_envio}")
                        continue

                canal = self.bot.get_channel(int(channel_id))
                if not canal or not hasattr(canal, "send"):
                    #print(f"[MsgAutoTask] msg_id={msg_id} canal {channel_id} não encontrado.")
                    continue

                # Apagar mensagem anterior
                last_message_id = msg_data.get("last_message_id")
                if last_message_id:
                    try:
                        old_message = await canal.fetch_message(int(last_message_id))
                        await old_message.delete()
                    except (disnake.NotFound, disnake.Forbidden):
                        pass

                # Montar dados para o builder
                data_to_build = editor_data.copy()
                if "botoes" in data_to_build and data_to_build["botoes"]:
                    data_to_build["buttons"] = data_to_build.pop("botoes")
                else:
                    data_to_build.pop("botoes", None)
                    data_to_build["buttons"] = []

                built_message = await Builder.build_from_cfg({"message": data_to_build})
                print(f"[MsgAutoTask] msg_id={msg_id} built mode={built_message.get('mode')}")

                # Injeta áudio, se configurado
                audio_file = await helpers.build_audio_file(msg_id)
                if audio_file:
                    built_message.setdefault("files", [])
                    if not isinstance(built_message["files"], list):
                        built_message["files"] = [built_message["files"]]
                    built_message["files"].append(audio_file)

                # Envia diretamente no canal
                new_message = None
                if built_message["mode"] == "v2":
                    new_message = await canal.send(
                        components=built_message["components"],
                        flags=built_message["flags"],
                        allowed_mentions=disnake.AllowedMentions.none(),
                    )
                else:
                    kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
                    if built_message.get("content"):
                        kwargs["content"] = built_message["content"]
                    if built_message.get("embed"):
                        kwargs["embed"] = built_message["embed"]
                    if built_message.get("components"):
                        kwargs["components"] = built_message["components"]
                    if built_message.get("files"):
                        kwargs["files"] = built_message["files"]
                    new_message = await canal.send(**kwargs)

                print(f"[MsgAutoTask] msg_id={msg_id} enviado! message_id={new_message.id if new_message else None}")

                # Atualizar configuração com novo estado
                config = helpers.carregar_config()
                current_msg_data = config.get("mensagens", {}).get(msg_id)
                if current_msg_data:
                    current_msg_data["ultima_enviada"] = agora.isoformat()
                    if new_message:
                        current_msg_data["last_message_id"] = new_message.id
                    helpers.salvar_config(config)

            except Exception as e:
                import traceback
                #print(f"[MsgAutoTask] Erro ao processar msg_id={msg_id}: {e}\n{traceback.format_exc()}")
                continue

    @msg_auto_task.before_loop
    async def before_msg_auto_task(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(MsgAutoTask(bot))
