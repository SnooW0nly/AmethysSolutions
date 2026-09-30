import disnake
from functions.database import database
import time
from functions.emoji import emoji
import datetime
import os
import hashlib
import aiohttp

class Sincronizacao:
    @staticmethod
    async def LogBackup(bot: disnake.Client, resumo: dict, auto: bool = False):
        definicoes = database.get_document("canais")
        canal_id = definicoes.get("canal_de_logs_do_sistema")
        if not canal_id:
            return

        try:
            canal = await bot.fetch_channel(int(canal_id))
        except Exception as e:
            print(f"[Backup] Erro ao buscar canal de logs: {e}")
            return

        agora = int(time.time())

        mode = database.get_document("custom_mode").get("mode")

        try:
            if mode == "embed":
                colors = database.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                primary_color = None
                if primary_color_hex:
                    primary_color = int(primary_color_hex.replace("#", ""), 16)

                embed = disnake.Embed(
                    title=f"{emoji.save} Backup realizado com sucesso!",
                    description="As configurações do servidor, incluindo canais, cargos, permissões, informações dos membros, mensagens, emojis e stickers, foram salvas na nuvem. Se por acaso seu servidor enfrentar problemas no futuro, será possível restaurá-lo completamente com apenas um comando.",
                    color=primary_color if primary_color else disnake.Color.green()
                )
                embed.add_field(
                    name="Resumo do Backup",
                    value=f"{emoji.textc} **Canais:** `{resumo.get('canais', 0)}`\n"
                          f"{emoji.dir} **Categorias:** `{resumo.get('categorias', 0)}`\n"
                          f"{emoji.role} **Cargos:** `{resumo.get('cargos', 0)}`\n"
                          f"{emoji.members} **Membros:** `{resumo.get('membros', 0)}`\n"
                          f"{emoji.reaction} **Emojis:** `{resumo.get('emojis', 0)}`\n"
                          f"{emoji.flag} **Figurinhas:** `{resumo.get('stickers', 0)}`\n"
                          f"{emoji.message if hasattr(emoji, 'message') else '💬'} **Mensagens:** `{resumo.get('mensagens', 0)}`\n"
                )
                footer_text = f"Data: {datetime.datetime.fromtimestamp(agora).strftime('%d/%m/%Y às %H:%M:%S')}"
                if auto:
                    footer_text += " | Backup Automático"
                embed.set_footer(text=footer_text)
                await canal.send(embed=embed)
            else:
                colors = database.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                container_kwargs = {}
                if primary_color_hex:
                    primary_color = int(primary_color_hex.replace("#", ""), 16)
                    container_kwargs["accent_colour"] = disnake.Colour(primary_color)

                await canal.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"## {emoji.save} Backup realizado com sucesso!\n\n"
                                f"As configurações do servidor, incluindo canais, cargos, permissões, informações dos membros, mensagens, emojis e stickers, foram salvas na nuvem. Se por acaso seu servidor enfrentar problemas no futuro, será possível restaurá-lo completamente com apenas um comando.\n"
                            ),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(
                                f"{emoji.textc} **Canais:** `{resumo.get('canais', 0)}`\n"
                                f"{emoji.dir} **Categorias:** `{resumo.get('categorias', 0)}`\n"
                                f"{emoji.role} **Cargos:** `{resumo.get('cargos', 0)}`\n"
                                f"{emoji.members} **Membros:** `{resumo.get('membros', 0)}`\n"
                                f"{emoji.reaction} **Emojis:** `{resumo.get('emojis', 0)}`\n"
                                f"{emoji.flag} **Figurinhas:** `{resumo.get('stickers', 0)}`\n"
                                f"{emoji.message if hasattr(emoji, 'message') else '💬'} **Mensagens:** `{resumo.get('mensagens', 0)}`\n"
                            ),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(
                                f"{emoji.calendar} **Data:** <t:{agora}:f> (<t:{agora}:R>)\n"
                                f"{f'{emoji.reload} **Backup Automático:** `Sim`\n' if auto else ''}"
                            ),
                            **container_kwargs,
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        except Exception as e:
            print(f"[Backup] Erro ao enviar mensagem de log com componentes: {e}")

    @staticmethod
    async def BackupGuild(guild: disnake.Guild, bot: disnake.Client = None, auto: bool = False):
        data = {}

        definicoes_backup = database.obter("database/backup_configs.json")
        excluded = definicoes_backup.get("backup_auto_exclude", []) if auto else []

        data['guild'] = {
            'id': guild.id,
            'nome': guild.name,
            'icon_url': str(guild.icon.url) if guild.icon else None,
            'banner_url': str(guild.banner.url) if guild.banner else None,
        }

        if 'roles' not in excluded:
            data['roles'] = [
                {
                    'id': role.id,
                    'name': role.name,
                    'color': role.color.value,
                    'position': role.position,
                }
                for role in guild.roles
            ]
        else:
            data['roles'] = []

        if 'categories' not in excluded:
            data['categories'] = [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'position': cat.position,
                    'overwrites': {
                        str(target.id): {
                            'allow': overwrite.pair()[0].value,
                            'deny': overwrite.pair()[1].value
                        }
                        for target, overwrite in cat.overwrites.items()
                    }
                }
                for cat in guild.categories
            ]
        else:
            data['categories'] = []

        if 'channels' not in excluded:
            data['channels'] = [
                {
                    'id': channel.id,
                    'name': channel.name,
                    'type': str(channel.type),
                    'category_id': channel.category_id,
                    'position': channel.position,
                    'overwrites': {
                        str(target.id): {
                            'allow': overwrite.pair()[0].value,
                            'deny': overwrite.pair()[1].value
                        }
                        for target, overwrite in channel.overwrites.items()
                    }
                }
                for channel in guild.channels if channel.type != disnake.ChannelType.category
            ]
        else:
            data['channels'] = []

        data['members'] = []
        if 'members' not in excluded:
            for member in guild.members:
                data['members'].append({
                    'id': member.id,
                    'roles': [role.id for role in member.roles if not role.is_default()]
                })

        emoji_dir = os.path.join('database', 'backups', 'emojis')
        os.makedirs(emoji_dir, exist_ok=True)
        data['emojis'] = []
        if 'emojis' not in excluded:
            for emoji in guild.emojis:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(str(emoji.url)) as resp:
                            if resp.status == 200:
                                img_bytes = await resp.read()
                                hash_digest = hashlib.sha256(img_bytes).hexdigest()
                                ext = '.gif' if emoji.animated else '.png'
                                filename = f"{hash_digest}{ext}"
                                file_path = os.path.join(emoji_dir, filename)
                                if not os.path.isfile(file_path):
                                    with open(file_path, 'wb') as f:
                                        f.write(img_bytes)
                                data['emojis'].append({
                                    'id': emoji.id,
                                    'name': emoji.name,
                                    'animated': emoji.animated,
                                    'file': f"emojis/{filename}",
                                })
                except Exception as e:
                    print(f"[Backup] Erro ao salvar emoji {emoji.name}: {e}")

        sticker_dir = os.path.join('database', 'backups', 'stickers')
        os.makedirs(sticker_dir, exist_ok=True)
        data['stickers'] = []
        if 'stickers' not in excluded:
            for sticker in getattr(guild, 'stickers', []):
                try:
                    if not hasattr(sticker, 'url') or not sticker.url:
                        continue
                    async with aiohttp.ClientSession() as session:
                        async with session.get(str(sticker.url)) as resp:
                            if resp.status == 200:
                                img_bytes = await resp.read()
                                hash_digest = hashlib.sha256(img_bytes).hexdigest()
                                ext = '.png'
                                filename = f"{hash_digest}{ext}"
                                file_path = os.path.join(sticker_dir, filename)
                                if not os.path.isfile(file_path):
                                    with open(file_path, 'wb') as f:
                                        f.write(img_bytes)
                                data['stickers'].append({
                                    'id': sticker.id,
                                    'name': sticker.name,
                                    'format': str(sticker.format),
                                    'file': f"stickers/{filename}",
                                })
                except Exception as e:
                    print(f"[Backup] Erro ao salvar sticker {sticker.name}: {e}")

        data['messages'] = {}
        total_msgs = 0
        if 'messages' not in excluded:
            for channel in guild.text_channels:
                try:
                    messages = []
                    async for msg in channel.history(limit=100):
                        messages.append({
                            "content": msg.content,
                            "author": {
                                "id": str(msg.author.id),
                                "name": msg.author.display_name,
                                "avatar": msg.author.display_avatar.url if msg.author.display_avatar else None
                            },
                            "timestamp": msg.created_at.isoformat(),
                            "reference": str(msg.reference.message_id) if msg.reference else None,
                            "embeds": [e.to_dict() for e in msg.embeds] if msg.embeds else []
                        })
                        total_msgs += 1
                    data['messages'][str(channel.id)] = messages
                except Exception as e:
                    print(f"[Backup] Erro ao salvar mensagens do canal {channel.name}: {e}")

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_dir = 'database/backups'
        os.makedirs(backup_dir, exist_ok=True)

        if auto == True:
            backup_path = os.path.join(backup_dir, f'Backup_Auto_{timestamp}.json')
        else:
            backup_path = os.path.join(backup_dir, f'Backup_{timestamp}.json')
        database.salvar(backup_path, data)

        resumo = {
            'nome': guild.name,
            'icon_url': str(guild.icon.url) if guild.icon else 'Nenhum',
            'banner_url': str(guild.banner.url) if guild.banner else 'Nenhum',
            'canais': len(data['channels']),
            'categorias': len(data['categories']),
            'cargos': len(data['roles']),
            'emojis': len(data['emojis']),
            'stickers': len(data['stickers']),
            'membros': len(data.get('members', [])),
            'mensagens': total_msgs
        }

        if bot is not None:
            await Sincronizacao.LogBackup(bot, resumo, auto=auto)

        return resumo
