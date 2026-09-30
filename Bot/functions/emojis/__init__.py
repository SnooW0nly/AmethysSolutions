import os
import re
import sys
import asyncio
import aiohttp
import json
from .database import load_emojis, save_emojis
from .verify import verify_emojis_batch
from .upload import upload_emoji_async
from .delete import delete_emoji_async


class emojis:
    DB_PATH = "database/emojis/emojis.json"
    ASSETS_PATH = "database/emojis/assets"
    REQUEST_COOLDOWN = 0.3  # Cooldown mínimo entre requisições em segundos
    
    def __init__(self, bot_token: str, app_id: str):
        self.bot_token = bot_token
        self.app_id = app_id
        self.emojis_db = load_emojis()
        self._ensure_emojis_structure()
        # Recarregar após garantir estrutura
        if not self.emojis_db or len(self.emojis_db) == 0:
            self.emojis_db = load_emojis()
        try:
            loop = asyncio.get_running_loop()
            self._last_request_time = loop.time()
        except RuntimeError:
            self._last_request_time = 0

    def get(self, name: str) -> str | None:
        return self.emojis_db.get(name)

    def list(self) -> dict:
        return self.emojis_db

    def save(self):
        save_emojis(self.emojis_db)
    
    async def _apply_cooldown(self):
        """Aplica cooldown entre requisições para respeitar rate limits"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.REQUEST_COOLDOWN:
            wait_time = self.REQUEST_COOLDOWN - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request_time = asyncio.get_event_loop().time()

    def _ensure_emojis_structure(self):
        """Garante que emojis.json tenha a estrutura correta escaneando assets"""
        if not self.emojis_db or len(self.emojis_db) == 0:
            print("[Emojis] emojis.json vazio, escaneando pasta de assets...")
            
            if not os.path.exists(self.ASSETS_PATH):
                print(f"[Emojis] Pasta de assets não encontrada: {self.ASSETS_PATH}")
                return
            
            # Escanear todos os arquivos na pasta de assets
            emoji_files = {}
            try:
                for filename in os.listdir(self.ASSETS_PATH):
                    if filename.endswith(('.png', '.gif')):
                        # Remover extensão para obter o nome do emoji
                        emoji_name = os.path.splitext(filename)[0]
                        emoji_files[emoji_name] = ""
                
                if emoji_files:
                    self.emojis_db = emoji_files
                    self.save()
                    print(f"[Emojis] Estrutura criada com {len(self.emojis_db)} emojis encontrados em assets")
                else:
                    print("[Emojis] Nenhum arquivo de emoji encontrado em assets")
            except Exception as e:
                print(f"[Emojis] Erro ao escanear assets: {e}")

    def validate_name(self, name: str) -> bool:
        return 2 <= len(name) <= 32

    async def _list_guild_emojis_async(self, session: aiohttp.ClientSession):
        url = f"https://discord.com/api/v10/applications/{self.app_id}/emojis"
        headers = {"Authorization": f"Bot {self.bot_token}"}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("items", [])
        return []

    def emoji_name_exists(self, name: str, guild_emojis: list) -> bool:
        return any(e["name"] == name for e in guild_emojis)

    def get_emoji_id(self, name: str, guild_emojis: list) -> str | None:
        for emoji in guild_emojis:
            if emoji["name"] == name:
                return emoji["id"]
        return None

    async def validate_or_create_async(
        self, session: aiohttp.ClientSession, name: str, guild_emojis: list
    ) -> tuple[str | None, bool]:
        tag = self.emojis_db.get(name, "")
        create = False
        synced = False

        # Verificar se já existe um emoji com esse nome na guilda
        existing_emoji_id = self.get_emoji_id(name, guild_emojis)
        
        if not tag:
            # Se não tem tag no DB, verificar se já existe no Discord
            if existing_emoji_id:
                print(f"[Emojis] Emoji '{name}' já existe no Discord (ID: {existing_emoji_id}), sincronizando...")
                # Sincronizar com o emoji existente
                existing_emoji = next((e for e in guild_emojis if e["id"] == existing_emoji_id), None)
                if existing_emoji:
                    is_animated = existing_emoji.get("animated", False)
                    new_tag = f"<a:{name}:{existing_emoji_id}>" if is_animated else f"<:{name}:{existing_emoji_id}>"
                    self.emojis_db[name] = new_tag
                    return new_tag, False
            create = True
        else:
            # Extrair o ID da tag existente
            match = re.search(r"<a?:\w+:(\d+)>", tag)
            emoji_id = match.group(1) if match else None
            
            if emoji_id:
                # Verificar se o emoji ainda é válido
                await self._apply_cooldown()
                verify_results = await verify_emojis_batch(
                    self.app_id, self.bot_token, [emoji_id]
                )
                
                if not verify_results.get(emoji_id, False):
                    # Emoji inválido, verificar se existe outro com o mesmo nome
                    if existing_emoji_id and existing_emoji_id != emoji_id:
                        print(f"[Emojis] Emoji '{name}' inválido no DB, mas encontrado no Discord (ID: {existing_emoji_id}), sincronizando...")
                        # Sincronizar com o emoji existente
                        existing_emoji = next((e for e in guild_emojis if e["id"] == existing_emoji_id), None)
                        if existing_emoji:
                            is_animated = existing_emoji.get("animated", False)
                            new_tag = f"<a:{name}:{existing_emoji_id}>" if is_animated else f"<:{name}:{existing_emoji_id}>"
                            self.emojis_db[name] = new_tag
                            return new_tag, False
                    
                    # Deletar emoji inválido se existir
                    await self._apply_cooldown()
                    await delete_emoji_async(session, self.app_id, self.bot_token, emoji_id)
                    create = True
                    self.emojis_db[name] = ""
                elif existing_emoji_id and existing_emoji_id != emoji_id:
                    # Emoji válido no DB, mas existe outro com o mesmo nome no Discord
                    print(f"[Emojis] Emoji '{name}' duplicado no Discord, removendo duplicata...")
                    await self._apply_cooldown()
                    await delete_emoji_async(session, self.app_id, self.bot_token, existing_emoji_id)
            else:
                # Tag inválida no DB
                if existing_emoji_id:
                    print(f"[Emojis] Emoji '{name}' com tag inválida no DB, sincronizando com Discord (ID: {existing_emoji_id})...")
                    existing_emoji = next((e for e in guild_emojis if e["id"] == existing_emoji_id), None)
                    if existing_emoji:
                        is_animated = existing_emoji.get("animated", False)
                        new_tag = f"<a:{name}:{existing_emoji_id}>" if is_animated else f"<:{name}:{existing_emoji_id}>"
                        self.emojis_db[name] = new_tag
                        return new_tag, False
                create = True

        if create:
            if not self.validate_name(name):
                print(f"[Emojis] Nome '{name}' inválido (deve ter entre 2-32 caracteres)")
                return None, False

            # Verificar se precisa deletar emoji existente com o mesmo nome
            # (só chega aqui se não conseguiu sincronizar acima)
            if existing_emoji_id:
                print(f"[Emojis] Removendo emoji existente '{name}' antes de criar novo...")
                await self._apply_cooldown()
                await delete_emoji_async(
                    session, self.app_id, self.bot_token, existing_emoji_id
                )

            # Buscar arquivo do emoji
            gif_path = os.path.join(self.ASSETS_PATH, f"{name}.gif")
            png_path = os.path.join(self.ASSETS_PATH, f"{name}.png")
            path = gif_path if os.path.isfile(gif_path) else png_path

            if not os.path.isfile(path):
                print(f"[Emojis] Arquivo não encontrado para emoji '{name}'")
                return None, False

            try:
                await self._apply_cooldown()
                new_id = await upload_emoji_async(
                    session, name, path, self.app_id, self.bot_token
                )
                new_tag = (
                    f"<a:{name}:{new_id}>"
                    if path.endswith(".gif")
                    else f"<:{name}:{new_id}>"
                )
                self.emojis_db[name] = new_tag
                print(f"[Emojis] Emoji '{name}' criado com sucesso!")
                return new_tag, True
            except Exception as e:
                print(f"[Emojis] Erro ao criar emoji '{name}': {e}")
                return None, False
        
        return tag, False

    def _set_configured_True(self):
        try:
            path = "database/emojis/emojis_data.json"
            data = {
                "configured": "True",
                "lastToken": self.bot_token
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("[Emojis] emojis_data.json atualizado com sucesso")
        except Exception as e:
            print(f"[Emojis] Falha ao atualizar emojis_data.json: {e}")

    async def sync_all_async(self, progress_callback=None):
        total = len(self.emojis_db)
        success = 0
        added = 0

        print(f"[Emojis] Iniciando sincronização de {total} emojis...")

        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            await self._apply_cooldown()
            guild_emojis = await self._list_guild_emojis_async(session)
            print(f"[Emojis] {len(guild_emojis)} emojis encontrados no Discord")

            # Processar em lotes de 10 emojis por vez
            names = list(self.emojis_db.keys())
            batch_size = 10

            for i in range(0, len(names), batch_size):
                batch = names[i : i + batch_size]
                tasks = []
                
                for name in batch:
                    task = asyncio.create_task(self.validate_or_create_async(session, name, guild_emojis))
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for name, result in zip(batch, results):
                    if isinstance(result, Exception):
                        print(f"[Emojis] Erro ao processar '{name}': {result}")
                        continue

                    tag, was_added = result
                    if tag:
                        success += 1
                    if was_added:
                        added += 1

                    if progress_callback:
                        progress_callback(success, total)

                # Atualizar lista de emojis após cada lote se houve mudanças
                if added > 0:
                    await self._apply_cooldown()
                    guild_emojis = await self._list_guild_emojis_async(session)

        # Salvar todas as mudanças de uma vez
        self.save()

        print(f"[Emojis] Sincronização concluída: {success}/{total} emojis processados, {added} novos adicionados")

        if success == total:
            self._set_configured_True()
            print("[Emojis] Todos os emojis foram sincronizados com sucesso!")

            if added > 0:
                print(f"[Emojis] {added} novos emojis foram adicionados. Reiniciando bot...")
                return os.execv(sys.executable, ["python"] + sys.argv)
            else:
                print("[Emojis] Nenhum novo emoji foi adicionado.")

        return success, total

    def sync_all(self, progress_callback=None):
        """Versão síncrona para compatibilidade"""
        return asyncio.run(self.sync_all_async(progress_callback))