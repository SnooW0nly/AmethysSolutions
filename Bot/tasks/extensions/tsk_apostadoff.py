"""
tsk_apostadoff.py — Task de envio contínuo de filas e expiração de partidas
"""
import asyncio
import time
import disnake
from disnake.ext import tasks
from functions.database import database as db

APOSTADOFF_PARTIDAS_KEY  = "apostadoff_partidas"
APOSTADOFF_FILAS_CFG_KEY = "apostadoff_filas_cfg"
APOSTADOFF_FILAS_KEY     = "apostadoff_filas"
APOSTADOFF_MED_KEY       = "apostadoff_mediadores"
APOSTADOFF_DB_KEY        = "apostadoff_config"
TEMPO_MAXIMO             = 3600  # 1 hora


class ApostadoFFTask:
    def __init__(self, bot):
        self.bot = bot
        # tipo → {canal_id(str) → set[int]}  (múltiplas msgs por canal)
        self._fila_messages: dict[str, dict[str, set]] = {}
        self.task_expirar.start()
        self.task_filas.start()

    def cog_unload(self):
        self.task_expirar.cancel()
        self.task_filas.cancel()

    # ── Task: expirar partidas ────────────────────────────────────────────────
    @tasks.loop(minutes=5)
    async def task_expirar(self):
        partidas = db.get_document(APOSTADOFF_PARTIDAS_KEY) or {}
        agora    = time.time()
        mudou    = False

        for canal_id, partida in list(partidas.items()):
            if agora - partida.get("created_at", agora) <= TEMPO_MAXIMO:
                continue

            # Recolocar mediador em serviço
            orientador = partida.get("orientador")
            if orientador:
                mediadores = db.get_document(APOSTADOFF_MED_KEY) or []
                if orientador not in mediadores:
                    mediadores.append(orientador)
                    db.save_document(APOSTADOFF_MED_KEY, mediadores)

            del partidas[canal_id]
            mudou = True

            try:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    await canal.send("⏰ Partida expirada por inatividade. Canal deletado em 5s.")
                    await asyncio.sleep(5)
                    await canal.delete()
            except Exception as e:
                print(f"[ApostadoFF][expirar] Erro ao deletar canal {canal_id}: {e}")

        if mudou:
            db.save_document(APOSTADOFF_PARTIDAS_KEY, partidas)

    @task_expirar.before_loop
    async def before_expirar(self):
        await self.bot.wait_until_ready()

    # ── Task: envio/atualização contínua de filas ─────────────────────────────
    @tasks.loop(seconds=30)
    async def task_filas(self):
        """
        Para cada tipo de fila com canais configurados:
        - Edita todas as mensagens ativas no canal
        - Se alguma foi deletada → remove do tracking e do DB
        - Sempre envia uma nova fila vazia a cada tick
        Permite múltiplas filas simultâneas por canal.
        """
        global_cfg:  dict = db.get_document(APOSTADOFF_DB_KEY)        or {}

        # Sistema desativado globalmente → não faz nada
        if not global_cfg.get("ativo", False):
            return

        filas_cfg:   dict = db.get_document(APOSTADOFF_FILAS_CFG_KEY) or {}
        filas_dados: dict = db.get_document(APOSTADOFF_FILAS_KEY)     or {}
        usar_v2 = bool(global_cfg.get("usar_v2", False))

        from modules.utilitarios.apostadoff import paineis as _paineis

        filas_salvas = False  # controle para salvar o DB apenas se necessário

        for tipo, fila_cfg in filas_cfg.items():
            if not fila_cfg.get("ativo", False):
                continue

            canais_ids = fila_cfg.get("canais", [])
            if not canais_ids:
                continue

            modo  = fila_cfg.get("modo", "Clássico")
            valor = fila_cfg.get("valor", "10,00")

            if tipo not in self._fila_messages:
                self._fila_messages[tipo] = {}

            for canal_id in canais_ids:
                canal = self.bot.get_channel(int(canal_id))
                if not canal:
                    continue

                canal_key = str(canal_id)
                if canal_key not in self._fila_messages[tipo]:
                    self._fila_messages[tipo][canal_key] = set()

                msg_ids: set = self._fila_messages[tipo][canal_key]

                # ── Editar todas as mensagens ativas ──────────────────────────
                ids_mortos = set()

                for mid in list(msg_ids):
                    dado = filas_dados.get(str(mid))
                    if not dado:
                        ids_mortos.add(mid)
                        continue

                    # Montar jogadores — suporta 1v1 (user1/user2) e times (A/B)
                    tamanho = tipo.split("_")[0] if "_" in tipo else tipo
                    jogadores = []
                    if tamanho == "1v1":
                        if dado.get("user1"):
                            j = {"id": dado["user1"]}
                            if dado.get("user1_gel"):
                                j["tipo_gel"] = dado["user1_gel"]
                            jogadores.append(j)
                        if dado.get("user2"):
                            j = {"id": dado["user2"]}
                            if dado.get("user2_gel"):
                                j["tipo_gel"] = dado["user2_gel"]
                            jogadores.append(j)
                    else:
                        times = dado.get("times", {"A": [], "B": []})
                        for uid in times.get("A", []):
                            jogadores.append({"id": uid, "time": "A"})
                        for uid in times.get("B", []):
                            jogadores.append({"id": uid, "time": "B"})

                    embed, components = _paineis.get_fila_embed(
                        tipo, valor, modo, jogadores, fila_cfg, str(mid)
                    )

                    try:
                        msg = await canal.fetch_message(int(mid))
                        if usar_v2:
                            await msg.edit(
                                components=components,
                                flags=disnake.MessageFlags(is_components_v2=True)
                            )
                        else:
                            await msg.edit(embed=embed, components=components)
                    except Exception:
                        # Mensagem deletada → remove do tracking e do DB
                        ids_mortos.add(mid)
                        filas_dados.pop(str(mid), None)
                        filas_salvas = True

                # Remove msgs mortas do set local
                msg_ids -= ids_mortos

                # ── Sempre envia uma nova fila vazia a cada tick ───────────────
                try:
                    embed_p, components_p = _paineis.get_fila_embed(
                        tipo, valor, modo, [], fila_cfg, "MSGID"
                    )
                    if usar_v2:
                        msg = await canal.send(
                            components=components_p,
                            flags=disnake.MessageFlags(is_components_v2=True)
                        )
                    else:
                        msg = await canal.send(embed=embed_p, components=components_p)

                    # Registrar no DB
                    tamanho_reg = tipo.split("_")[0] if "_" in tipo else tipo
                    novo_dado = {
                        "tipo": tipo, "valor": valor, "modo": modo,
                        "canal_id": canal_key,
                        "user1": None, "user1_gel": None,
                        "user2": None, "user2_gel": None,
                    }
                    if tamanho_reg != "1v1":
                        novo_dado["times"] = {"A": [], "B": []}
                    filas_dados[str(msg.id)] = novo_dado
                    filas_salvas = True

                    # Editar para corrigir custom_ids com msg_id real
                    embed2, components2 = _paineis.get_fila_embed(
                        tipo, valor, modo, [], fila_cfg, str(msg.id)
                    )
                    try:
                        if usar_v2:
                            await msg.edit(
                                components=components2,
                                flags=disnake.MessageFlags(is_components_v2=True)
                            )
                        else:
                            await msg.edit(embed=embed2, components=components2)
                    except Exception:
                        pass

                    msg_ids.add(msg.id)

                except Exception as e:
                    print(f"[ApostadoFF][task_filas] Erro ao enviar fila {tipo} em {canal_id}: {e}")

        if filas_salvas:
            db.save_document(APOSTADOFF_FILAS_KEY, filas_dados)

    @task_filas.before_loop
    async def before_task_filas(self):
        await self.bot.wait_until_ready()


def setup(bot):
    return ApostadoFFTask(bot)