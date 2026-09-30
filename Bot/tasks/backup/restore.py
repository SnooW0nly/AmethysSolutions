import disnake
import os
import io
import asyncio
import aiohttp
from datetime import datetime
from functions.message import message, embed_message
from functions.emoji import emoji as amethys
import hashlib
from functions.database import database

class Restore:
    @staticmethod
    def get_types_set(tipo: str) -> set:
        if tipo == "all":
            return {"channels", "roles", "emojis", "stickers", "messages", "members"}
        return set(tipo.split(","))

    @staticmethod
    def _get_overwrite(target_id, perms, guild):
        target = guild.get_role(int(target_id)) or guild.get_member(int(target_id))
        if not target:
            return None, None
        overwrite = disnake.PermissionOverwrite.from_pair(
            disnake.Permissions(perms['allow']),
            disnake.Permissions(perms['deny'])
        )
        return target, overwrite

    @staticmethod
    async def _create_category(cat, guild):
        new_cat = await guild.create_category(name=cat['name'], position=cat['position'])
        for target_id, perms in cat.get('overwrites', {}).items():
            target, overwrite = Restore._get_overwrite(target_id, perms, guild)
            if target:
                await new_cat.set_permissions(target, overwrite=overwrite)
        return new_cat

    @staticmethod
    async def _create_channel(ch, guild, cat_map):
        category_id = cat_map.get(ch['category_id']) if ch['category_id'] and ch['category_id'] in cat_map else None
        ch_type = getattr(disnake.ChannelType, ch['type'].split('.')[-1].lower(), disnake.ChannelType.text)
        if ch_type == disnake.ChannelType.text:
            new_channel = await guild.create_text_channel(
                name=ch['name'],
                category=guild.get_channel(category_id) if category_id else None,
                position=ch['position']
            )
        elif ch_type == disnake.ChannelType.voice:
            new_channel = await guild.create_voice_channel(
                name=ch['name'],
                category=guild.get_channel(category_id) if category_id else None,
                position=ch['position']
            )
        else:
            return None
        for target_id, perms in ch.get('overwrites', {}).items():
            target, overwrite = Restore._get_overwrite(target_id, perms, guild)
            if target:
                await new_channel.set_permissions(target, overwrite=overwrite)
        return new_channel

    @staticmethod
    async def _hash_url(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    return hashlib.sha256(img_bytes).hexdigest()
        return None

    @staticmethod
    def _hash_file(file_path):
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    @staticmethod
    async def RestoreGuildBackup(
        guild: disnake.Guild,
        data: dict,
        tipo: str,
        inter: disnake.Interaction = None,
        painel_callback=None,
        mode: str = "default"
    ) -> bool:
        tipos_set = Restore.get_types_set(tipo)

        # Roles
        old_id_to_new_role = {}
        role_name_to_new_role = {}
        if "roles" in tipos_set:
            for role in list(guild.roles):
                if not role.is_default():
                    try:
                        await role.delete(reason="[Sync] Backup restore - wipe roles")
                    except Exception:
                        pass
            created_roles = {}
            bot_member = guild.me
            bot_top_role = bot_member.top_role
            max_position = bot_top_role.position
            for role in sorted(data.get('roles', []), key=lambda r: r['position']):
                if role['name'] != '@everyone':
                    try:
                        existing_role = next((r for r in guild.roles if r.name == role['name']), None)
                        if existing_role:
                            new_role = existing_role
                        else:
                            new_role = await guild.create_role(
                                name=role['name'],
                                color=disnake.Color(role['color'])
                            )
                        created_roles[role['name']] = new_role
                        old_id_to_new_role[role['id']] = new_role
                        role_name_to_new_role[role['name']] = new_role

                    except Exception:
                        pass
            for role in sorted(data.get('roles', []), key=lambda r: r['position']):
                if role['name'] != '@everyone' and role['name'] in created_roles:
                    try:
                        pos = role['position']
                        if pos >= max_position:
                            pos = max_position - 1
                        await created_roles[role['name']].edit(position=pos)
                    except Exception:
                        pass
        
        else:
            all_roles_data = data.get('roles', [])
            for r in guild.roles:
                role_data = next((rd for rd in all_roles_data if rd['name'] == r.name), None)
                if role_data:
                    old_id_to_new_role[role_data['id']] = r
                    role_name_to_new_role[r.name] = r

        # Members
        if "members" in tipos_set and data.get('members'):
            if not old_id_to_new_role and data.get('roles'):
                all_roles_data = data.get('roles', [])
                for r in guild.roles:
                    role_data = next((rd for rd in all_roles_data if rd['name'] == r.name), None)
                    if role_data:
                        old_id_to_new_role[role_data['id']] = r
            
            if not role_name_to_new_role:
                for r in guild.roles:
                    role_name_to_new_role[r.name] = r

            all_roles_data_by_id = {r['id']: r for r in data.get('roles', [])}

            for member_data in data.get('members', []):
                try:
                    member = guild.get_member(member_data['id'])
                    if not member:
                        try:
                            member = await guild.fetch_member(member_data['id'])
                        except disnake.NotFound:
                            continue
                    if not member:
                        continue

                    roles_to_add = []
                    for old_role_id in member_data.get('roles', []):
                        if old_role_id in old_id_to_new_role:
                            new_role = old_id_to_new_role[old_role_id]
                            if new_role not in member.roles:
                                roles_to_add.append(new_role)
                        else:
                            old_role_data = all_roles_data_by_id.get(old_role_id)
                            if old_role_data:
                                new_role = role_name_to_new_role.get(old_role_data['name'])
                                if new_role and new_role not in member.roles:
                                    roles_to_add.append(new_role)
                    
                    if roles_to_add:
                        await member.add_roles(*roles_to_add, reason="[Sync] Backup restore - members")
                except Exception as e:
                    print(f"[Restore] Error restoring roles for member {member_data.get('id')}: {e}")

        # Categories
        cat_map = {}
        canal_nome_para_id = {}
        if "channels" in tipos_set:
            for cat in data.get('categories', []):
                try:
                    new_cat = await Restore._create_category(cat, guild)
                    cat_map[cat['id']] = new_cat.id
                except Exception:
                    pass

        # Channels
        if "channels" in tipos_set:
            for ch in data.get('channels', []):
                try:
                    new_channel = await Restore._create_channel(ch, guild, cat_map)
                    if new_channel:
                        canal_nome_para_id[ch['name']] = new_channel.id
                except Exception:
                    pass

        # Emojis
        if "emojis" in tipos_set:
            existing_emoji_hashes = set()
            for e in guild.emojis:
                try:
                    hash_digest = await Restore._hash_url(e.url)
                    if hash_digest:
                        existing_emoji_hashes.add(hash_digest)
                except Exception:
                    pass
            for emoji in data.get('emojis', []):
                try:
                    file_path = os.path.join('database', 'backups', emoji['file'])
                    if not os.path.isfile(file_path):
                        continue
                    hash_digest = Restore._hash_file(file_path)
                    if hash_digest in existing_emoji_hashes or any(e.name == emoji['name'] for e in guild.emojis):
                        continue
                    with open(file_path, 'rb') as f:
                        img = f.read()
                    await guild.create_custom_emoji(name=emoji['name'], image=img)
                    existing_emoji_hashes.add(hash_digest)
                except Exception:
                    pass

        # Stickers
        if "stickers" in tipos_set and hasattr(guild, 'stickers'):
            existing_sticker_hashes = set()
            for s in getattr(guild, 'stickers', []):
                try:
                    if not hasattr(s, 'url') or not s.url:
                        continue
                    hash_digest = await Restore._hash_url(s.url)
                    if hash_digest:
                        existing_sticker_hashes.add(hash_digest)
                except Exception as e:
                    print(f"[Restore] Erro ao calcular hash do sticker existente: {getattr(s, 'name', None)}: {e}")
            for sticker in data.get('stickers', []):
                try:
                    file_path = os.path.join('database', 'backups', sticker['file'])
                    if not os.path.isfile(file_path):
                        print(f"[Restore] Sticker file not found: {file_path}")
                        continue
                    hash_digest = Restore._hash_file(file_path)
                    if hash_digest in existing_sticker_hashes or any(s.name == sticker['name'] for s in getattr(guild, 'stickers', [])):
                        print(f"[Restore] Sticker já existe (hash ou nome): {sticker['name']}")
                        continue
                    with open(file_path, 'rb') as f:
                        img = f.read()
                    sticker_format_str = sticker.get('format', '').lower()
                    if 'lottie' in sticker_format_str:
                        filename = f"{sticker['name']}.json"
                    elif 'apng' in sticker_format_str:
                        filename = f"{sticker['name']}.png"
                    else:
                        filename = f"{sticker['name']}.png"
                    await guild.create_sticker(
                        name=sticker['name'],
                        file=disnake.File(io.BytesIO(img), filename=filename),
                        emoji="🏮"
                    )
                    print(f"[Restore] Sticker restaurado: {sticker['name']} ({filename})")
                    existing_sticker_hashes.add(hash_digest)
                except Exception as e:
                    print(f"[Restore] Erro ao restaurar sticker {sticker.get('name')}: {e}")

        # Messages
        if "messages" in tipos_set or tipo == 'all' or 'channels' in tipos_set:
            messages_data = data.get('messages', {})
            async with aiohttp.ClientSession() as session:
                for channel_id, messages in messages_data.items():
                    ch_info = next((c for c in data.get('channels', []) if str(c['id']) == channel_id), None)
                    channel = None
                    if ch_info and 'canal_nome_para_id' in locals():
                        new_id = canal_nome_para_id.get(ch_info['name'])
                        if new_id:
                            channel = guild.get_channel(new_id)
                    if not channel:
                        try:
                            channel = guild.get_channel(int(channel_id))
                        except Exception:
                            pass
                    if not channel or not isinstance(channel, disnake.TextChannel):
                        continue
                    if not messages:
                        continue
                    try:
                        webhooks = await channel.webhooks()
                        webhook = None
                        for wh in webhooks:
                            if wh.user == guild.me:
                                webhook = wh
                                break
                        if not webhook:
                            webhook = await channel.create_webhook(name="Restore")
                        for i, msg in enumerate(messages):
                            try:
                                async def baixar_attachment(url):
                                    async with session.get(url) as resp:
                                        if resp.status == 200:
                                            data_bytes = io.BytesIO(await resp.read())
                                            filename = url.split('/')[-1]
                                            return disnake.File(data_bytes, filename=filename)
                                        return None
                                files = []
                                if msg.get('attachments'):
                                    files = [f for f in await asyncio.gather(*[baixar_attachment(url) for url in msg['attachments']]) if f]
                                await webhook.send(
                                    msg.get('content', ''),
                                    username=msg['author'].get('name', 'Desconhecido'),
                                    avatar_url=msg['author'].get('avatar'),
                                    embeds=[disnake.Embed.from_dict(utils.normalize_embed_data(e)) for e in msg.get('embeds', [])] if msg.get('embeds') else [],
                                    files=files if files else [],
                                    wait=True
                                )
                                if (i + 1) % 30 == 0:
                                    await asyncio.sleep(1)
                            except Exception:
                                pass
                    except Exception:
                        pass

        # Feedback
        if inter:
            if mode == "embed":
                await embed_message.success(inter, f"Backup restaurado com sucesso! (Tipo: {tipo})")
            else:
                await message.success(inter, f"Backup restaurado com sucesso! (Tipo: {tipo})")
            await asyncio.sleep(2)
            if painel_callback:
                await painel_callback()
            try:
                user = getattr(inter, 'user', None)
                if user:
                    dm = await user.create_dm()
                    guild_name = data.get('guild', {}).get('nome', guild.name)
                    restored = Restore.get_types_set(tipo)
                    def get_count(key):
                        if key == 'messages':
                            return sum(len(msgs) for msgs in data.get('messages', {}).values())
                        return len(data.get(key, []))
                    agora = int(datetime.now().timestamp())

                    if mode == "embed":
                        colors = database.get_document("custom_colors")
                        primary_color_hex = colors.get("primary")
                        primary_color = None
                        if primary_color_hex:
                            primary_color = int(primary_color_hex.replace("#", ""), 16)

                        embed = disnake.Embed(
                            title=f"{amethys.sync} Backup Restaurado com Sucesso!",
                            description=f"O backup `{tipo}` foi restaurado no servidor: **{guild_name}**.\n"
                                        f"Veja abaixo o que foi restaurado:",
                            color=primary_color if primary_color else disnake.Color.green()
                        )
                        embed.add_field(
                            name="Itens Restaurados",
                            value=f"{amethys.textc} **Canais:** `{get_count('channels')}`\n"
                                  f"{amethys.dir} **Categorias:** `{get_count('categories')}`\n"
                                  f"{amethys.role} **Cargos:** `{get_count('roles')}`\n"
                                  f"{amethys.members} **Membros:** `{get_count('members')}`\n"
                                  f"{amethys.reaction} **Emojis:** `{get_count('emojis')}`\n"
                                  f"{amethys.flag} **Figurinhas:** `{get_count('stickers')}`\n"
                                  f"{amethys.message if hasattr(amethys, 'message') else '💬'} **Mensagens:** `{get_count('messages')}`\n"
                        )
                        embed.set_footer(text=f"Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
                        await dm.send(embed=embed)
                    else:
                        await dm.send(
                            components=[
                                disnake.ui.Container(
                                    disnake.ui.TextDisplay(
                                        f"# {amethys.sync}\n"
                                        f"Backup `{tipo}` restaurado com sucesso!\n\n"
                                        f"O backup foi restaurado no servidor: **{guild_name}**.\n"
                                        f"Veja abaixo o que foi restaurado:\n"
                                    ),
                                    disnake.ui.Separator(),
                                    disnake.ui.TextDisplay(
                                        f"{amethys.textc} **Canais:** `{get_count('channels')}`\n"
                                        f"{amethys.dir} **Categorias:** `{get_count('categories')}`\n"
                                        f"{amethys.role} **Cargos:** `{get_count('roles')}`\n"
                                        f"{amethys.members} **Membros:** `{get_count('members')}`\n"
                                        f"{amethys.reaction} **Emojis:** `{get_count('emojis')}`\n"
                                        f"{amethys.flag} **Figurinhas:** `{get_count('stickers')}`\n"
                                        f"{amethys.message if hasattr(amethys, 'message') else '💬'} **Mensagens:** `{get_count('messages')}`\n"
                                    ),
                                    disnake.ui.Separator(),
                                    disnake.ui.TextDisplay(
                                        f"{amethys.calendar} **Data:** <t:{agora}:f> (<t:{agora}:R>)\n"
                                    ),
                                )
                            ],
                            flags=disnake.MessageFlags(is_components_v2=True)
                        )
            except Exception as e:
                print(f"[Restore] Não foi possível enviar DM para o usuário: {e}")

        return True
