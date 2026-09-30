"""
cog.py — ApostadoFF: listener principal de interações
"""
import disnake
import asyncio
import time
import random
import string
import json
import os
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message
from . import paineis
from .functions import stats
from .functions import coins as _coins

# ── Constantes de DB ──────────────────────────────────────────────────────────
APOSTADOFF_DB_KEY        = "apostadoff_config"
APOSTADOFF_FILAS_KEY     = "apostadoff_filas"       # dados por msg_id
APOSTADOFF_FILAS_CFG_KEY = "apostadoff_filas_cfg"   # config por tipo
APOSTADOFF_PARTIDAS_KEY  = "apostadoff_partidas"    # partidas ativas por thread_id
APOSTADOFF_MED_KEY       = "apostadoff_mediadores"  # lista de mediadores em serviço
APOSTADOFF_ANA_KEY       = "apostadoff_analistas"   # lista de analistas em serviço

# Caminho do JSON modelo do servidor Apostado
SERVER_MODEL_PATH = "database/utilitarios/apostado/server_model.json"


# ── helpers de DB ─────────────────────────────────────────────────────────────
def _get_config() -> dict:
    return db.get_document(APOSTADOFF_DB_KEY) or {}

def _save_config(data: dict):
    atual = _get_config()
    atual.update(data)
    db.save_document(APOSTADOFF_DB_KEY, atual)

def _get_filas() -> dict:
    return db.get_document(APOSTADOFF_FILAS_KEY) or {}

def _save_filas(filas: dict):
    db.save_document(APOSTADOFF_FILAS_KEY, filas)

def _get_filas_cfg() -> dict:
    return db.get_document(APOSTADOFF_FILAS_CFG_KEY) or {}

def _save_filas_cfg(cfg: dict):
    db.save_document(APOSTADOFF_FILAS_CFG_KEY, cfg)

def _get_fila_cfg(tipo: str) -> dict:
    return _get_filas_cfg().get(tipo, {
        "ativo": False, "gelo_infinito": True, "gelo_normal": True,
        "canais": [], "modo": "Clássico", "valor": "10,00"
    })

def _save_fila_cfg(tipo: str, fila_cfg: dict):
    all_cfg = _get_filas_cfg()
    all_cfg[tipo] = fila_cfg
    _save_filas_cfg(all_cfg)

def _get_partidas() -> dict:
    return db.get_document(APOSTADOFF_PARTIDAS_KEY) or {}

def _save_partidas(partidas: dict):
    db.save_document(APOSTADOFF_PARTIDAS_KEY, partidas)

def _get_mediadores() -> list:
    return db.get_document(APOSTADOFF_MED_KEY) or []

def _save_mediadores(lst: list):
    db.save_document(APOSTADOFF_MED_KEY, lst)

def _get_analistas() -> list:
    return db.get_document(APOSTADOFF_ANA_KEY) or []

def _save_analistas(lst: list):
    db.save_document(APOSTADOFF_ANA_KEY, lst)

def _get_pix(user_id: str) -> dict | None:
    return db.get_document(f"apostadoff_pix_{user_id}")

def _usar_v2() -> bool:
    return bool(_get_config().get("usar_v2", False))

def _gen_protocol(n=5) -> str:
    return "".join(random.choices(string.digits, k=n))


# ── Enviar mensagem respeitando V2 ────────────────────────────────────────────
async def _send(canal, embed, components, content=""):
    """Envia mensagem em modo embed ou container conforme config."""
    usar_v2 = _usar_v2()
    if usar_v2:
        return await canal.send(
            content=content or None,
            components=components,
            flags=disnake.MessageFlags(is_components_v2=True)
        )
    else:
        return await canal.send(
            content=content or None,
            embed=embed,
            components=components
        )


async def _edit_msg(msg: disnake.Message, embed, components):
    """Edita mensagem respeitando V2."""
    usar_v2 = _usar_v2()
    if usar_v2:
        await msg.edit(
            components=components,
            flags=disnake.MessageFlags(is_components_v2=True)
        )
    else:
        await msg.edit(embed=embed, components=components)


# ── Check mediador ────────────────────────────────────────────────────────────
async def _check_mediador(inter: disnake.MessageInteraction) -> bool:
    config = _get_config()
    cargo_id = config.get("cargo_mediador")
    if not cargo_id:
        await inter.response.send_message("Cargo de mediador não configurado.", ephemeral=True)
        return False
    role = inter.guild.get_role(int(cargo_id))
    if not role or role not in inter.author.roles:
        await inter.response.send_message("Você não possui o cargo de mediador.", ephemeral=True)
        return False
    return True


# ── COG ───────────────────────────────────────────────────────────────────────
class ApostadoFFCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # tipo → {canal_id(str) → set[int]}  (múltiplas msgs por canal)
        self._fila_messages: dict[str, dict[str, set]] = {}

    # ── Listener principal ────────────────────────────────────────────────────
    @commands.Cog.listener("on_message_interaction")
    async def handle_apostadoff(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id
        if not cid:
            return

        # ── Painel principal ───────────────────────────────────────────────
        if cid == "ApostadoFF_PainelPrincipal":
            await inter.response.edit_message(
                components=paineis.get_painel_principal(_get_config()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_Toggle":
            config = _get_config()
            config["ativo"] = not config.get("ativo", False)
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_principal(config),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_ToggleV2":
            config = _get_config()
            config["usar_v2"] = not config.get("usar_v2", False)
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_principal(config),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_Canais":
            await inter.response.edit_message(
                components=paineis.get_painel_canais(_get_config(), inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_Taxa":
            await inter.response.edit_message(
                components=paineis.get_painel_taxa(_get_config()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_EditarTaxa":
            await inter.response.send_modal(paineis.TaxaModal())

        # ── Selects de config ──────────────────────────────────────────────
        elif cid == "ApostadoFF_SelectCategoria":
            config = _get_config()
            config["categoria_apostas"] = inter.values[0]
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_canais(config, inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, "Categoria atualizada!", followup=True)

        elif cid == "ApostadoFF_SelectCanalLogs":
            config = _get_config()
            config["canal_logs"] = inter.values[0]
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_canais(config, inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, "Canal de logs atualizado!", followup=True)

        # ── Painel Mediadores (admin) ──────────────────────────────────────
        elif cid == "ApostadoFF_PainelMediadores":
            await inter.response.edit_message(
                components=paineis.get_painel_mediadores_admin(
                    _get_config(), inter.guild, _coins.get_cfg()
                ),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_SelectCanalMediadores":
            config = _get_config()
            config["canal_mediadores"] = inter.values[0]
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_mediadores_admin(config, inter.guild, _coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, "Canal de mediadores atualizado!", followup=True)

        elif cid == "ApostadoFF_SelectCargoMediador":
            config = _get_config()
            config["cargo_mediador"] = inter.values[0]
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_mediadores_admin(config, inter.guild, _coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, "Cargo de mediador atualizado!", followup=True)

        elif cid == "ApostadoFF_MedEditarCoins":
            cfg_c = _coins.get_cfg()
            await inter.response.send_modal(
                paineis.MedCoinsModal(cfg_c.get("coins_por_ap_mediador", 10))
            )

        elif cid == "ApostadoFF_MedCargoUps":
            await inter.response.edit_message(
                components=paineis.get_painel_med_cargo_ups(_coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_MedCargoUpAdicionar":
            await inter.response.send_modal(paineis.MedCargoUpModal(idx=-1))

        elif cid.startswith("ApostadoFF_MedCargoUpEditar_"):
            idx   = int(cid.replace("ApostadoFF_MedCargoUpEditar_", ""))
            cfg_c = _coins.get_cfg()
            ups   = cfg_c.get("cargo_ups_mediador", [])
            up    = ups[idx] if idx < len(ups) else {}
            await inter.response.send_modal(paineis.MedCargoUpModal(idx=idx, up=up))

        elif cid == "ApostadoFF_MedCargoUpRemover":
            cfg_c = _coins.get_cfg()
            ups   = cfg_c.get("cargo_ups_mediador", [])
            if ups:
                ups.pop()
                cfg_c["cargo_ups_mediador"] = ups
                _coins.save_cfg(cfg_c)
            await inter.response.edit_message(
                components=paineis.get_painel_med_cargo_ups(cfg_c),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_EnviarPainelMediadores":
            await self._enviar_painel_mediadores(inter)

        # ── Entrar/sair/pix mediador ───────────────────────────────────────
        elif cid == "ApostadoFF_EntrarFilaMediador":
            await self._entrar_mediador(inter)

        elif cid == "ApostadoFF_SairFilaMediador":
            await self._sair_mediador(inter)

        elif cid == "ApostadoFF_ConfigPix":
            if not await _check_mediador(inter):
                return
            await inter.response.send_modal(paineis.PixModal(str(inter.author.id)))

        # ── Painel Analistas (admin) ───────────────────────────────────────
        elif cid == "ApostadoFF_PainelAnalistasAdmin":
            await inter.response.edit_message(
                components=paineis.get_painel_config_analistas(
                    _get_config(), inter.guild, _coins.get_cfg()
                ),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_SelectCanalAnalistas":
            config = _get_config()
            config["canal_analistas"] = inter.values[0]
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_config_analistas(config, inter.guild, _coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_SelectCargoAnalista":
            config = _get_config()
            config["cargo_analista"] = inter.values[0]
            _save_config(config)
            await inter.response.edit_message(
                components=paineis.get_painel_config_analistas(config, inter.guild, _coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_AnaEditarCoins":
            cfg_c = _coins.get_cfg()
            await inter.response.send_modal(
                paineis.AnaCoinsModal(cfg_c.get("coins_por_ap_analista", 5))
            )

        elif cid == "ApostadoFF_AnaCargoUps":
            await inter.response.edit_message(
                components=paineis.get_painel_ana_cargo_ups(_coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_AnaCargoUpAdicionar":
            await inter.response.send_modal(paineis.AnaCargoUpModal(idx=-1))

        elif cid.startswith("ApostadoFF_AnaCargoUpEditar_"):
            idx   = int(cid.replace("ApostadoFF_AnaCargoUpEditar_", ""))
            cfg_c = _coins.get_cfg()
            ups   = cfg_c.get("cargo_ups_analista", [])
            up    = ups[idx] if idx < len(ups) else {}
            await inter.response.send_modal(paineis.AnaCargoUpModal(idx=idx, up=up))

        elif cid == "ApostadoFF_AnaCargoUpRemover":
            cfg_c = _coins.get_cfg()
            ups   = cfg_c.get("cargo_ups_analista", [])
            if ups:
                ups.pop()
                cfg_c["cargo_ups_analista"] = ups
                _coins.save_cfg(cfg_c)
            await inter.response.edit_message(
                components=paineis.get_painel_ana_cargo_ups(cfg_c),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_EnviarPainelAnalistas":
            await self._enviar_painel_analistas(inter)

        # ── Analistas — entrar/sair de serviço ────────────────────────────
        elif cid == "ApostadoFF_EntrarFilaAnalista":
            await self._entrar_analista(inter)

        elif cid == "ApostadoFF_SairFilaAnalista":
            await self._sair_analista(inter)

        # ── Configurar Filas (novo sistema) ───────────────────────────────
        elif cid == "ApostadoFF_ConfigFilas":
            await inter.response.edit_message(
                components=paineis.get_painel_config_filas(_get_filas_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_AdminCriarFila":
            await inter.response.send_modal(paineis.CriarFilaAdminModal())

        elif cid == "ApostadoFF_SelecionarFilaGerenciar":
            tipo = inter.values[0]
            await inter.response.edit_message(
                components=paineis.get_painel_gerenciar_fila(tipo, _get_fila_cfg(tipo), inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid.startswith("ApostadoFF_GerenciarFila_"):
            tipo = cid.replace("ApostadoFF_GerenciarFila_", "")
            await inter.response.edit_message(
                components=paineis.get_painel_gerenciar_fila(tipo, _get_fila_cfg(tipo), inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid.startswith("ApostadoFF_FilaToggle_"):
            without_prefix = cid.replace("ApostadoFF_FilaToggle_", "")
            for campo_c in ("gelo_infinito", "gelo_normal", "ativo"):
                if without_prefix.endswith(f"_{campo_c}"):
                    tipo  = without_prefix[: -(len(campo_c) + 1)]
                    campo = campo_c
                    break
            else:
                tipo, campo = without_prefix, "ativo"
            fila_cfg = _get_fila_cfg(tipo)
            fila_cfg[campo] = not fila_cfg.get(campo, False)
            _save_fila_cfg(tipo, fila_cfg)
            await inter.response.edit_message(
                components=paineis.get_painel_gerenciar_fila(tipo, fila_cfg, inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid.startswith("ApostadoFF_FilaAddCanal_"):
            tipo = cid.replace("ApostadoFF_FilaAddCanal_", "")
            fila_cfg = _get_fila_cfg(tipo)
            canais = fila_cfg.get("canais", [])
            for c in inter.values:
                if c not in canais:
                    canais.append(c)
            fila_cfg["canais"] = canais
            _save_fila_cfg(tipo, fila_cfg)
            await inter.response.edit_message(
                components=paineis.get_painel_gerenciar_fila(tipo, fila_cfg, inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, f"{len(inter.values)} canal(is) adicionado(s)!", followup=True)

        elif cid.startswith("ApostadoFF_FilaLimparCanais_"):
            tipo = cid.replace("ApostadoFF_FilaLimparCanais_", "")
            fila_cfg = _get_fila_cfg(tipo)
            fila_cfg["canais"] = []
            _save_fila_cfg(tipo, fila_cfg)
            await inter.response.edit_message(
                components=paineis.get_painel_gerenciar_fila(tipo, fila_cfg, inter.guild),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid.startswith("ApostadoFF_FilaEnviar_"):
            tipo = cid.replace("ApostadoFF_FilaEnviar_", "")
            await self._enviar_fila_canais(inter, tipo)

        elif cid.startswith("ApostadoFF_FilaExcluir_"):
            tipo = cid.replace("ApostadoFF_FilaExcluir_", "")
            all_cfg = _get_filas_cfg()
            all_cfg.pop(tipo, None)
            _save_filas_cfg(all_cfg)
            await inter.response.edit_message(
                components=paineis.get_painel_config_filas(all_cfg),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, f"Fila `{tipo}` excluída.", followup=True)

        elif cid.startswith("ApostadoFF_FilaAparencia_"):
            tipo = cid.replace("ApostadoFF_FilaAparencia_", "")
            await inter.response.edit_message(
                components=paineis.get_painel_fila_aparencia(tipo, _get_fila_cfg(tipo)),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid.startswith("ApostadoFF_FilaEditarAparencia_"):
            tipo = cid.replace("ApostadoFF_FilaEditarAparencia_", "")
            await inter.response.send_modal(
                paineis.FilaAparenciaModal(tipo, _get_fila_cfg(tipo))
            )

        elif cid.startswith("ApostadoFF_FilaResetarAparencia_"):
            tipo = cid.replace("ApostadoFF_FilaResetarAparencia_", "")
            fila_cfg = _get_fila_cfg(tipo)
            fila_cfg.pop("aparencia", None)
            _save_fila_cfg(tipo, fila_cfg)
            await inter.response.edit_message(
                components=paineis.get_painel_fila_aparencia(tipo, fila_cfg),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await message.success(inter, "Aparência restaurada para o padrão!", followup=True)

        # ── Botões da fila (jogadores) ─────────────────────────────────────
        # custom_id: AF_Q_{tipo}_{msg_id}_{acao}
        elif cid.startswith("AF_Q_"):
            await self._handle_fila_botao(inter)

        # ── Confirmação / recusa na partida ────────────────────────────────
        elif cid.startswith("AF_P_confirmar_"):
            thread_id = cid.replace("AF_P_confirmar_", "")
            await self._handle_confirmar(inter, thread_id)

        elif cid.startswith("AF_P_recusar_"):
            thread_id = cid.replace("AF_P_recusar_", "")
            await self._handle_recusar(inter, thread_id)

        # ── Analista — veredicto no tópico ────────────────────────────────
        elif cid.startswith("AF_ANA_"):
            # custom_id: AF_ANA_{thread_id}_{veredicto}
            partes     = cid.split("_")
            thread_id  = partes[2]
            veredicto  = partes[3]  # limpo | hack | inconclusivo
            await self._handle_analista_veredicto(inter, thread_id, veredicto)

        # ── Coins — config ─────────────────────────────────────────────────
        elif cid == "ApostadoFF_CoinsConfig":
            await inter.response.edit_message(
                components=paineis.get_painel_coins_config(_coins.get_cfg()),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_CoinsEditar":
            await inter.response.send_modal(paineis.CoinsEditModal(_coins.get_cfg()))

        elif cid == "ApostadoFF_CoinsRanking":
            ranking = _coins.get_ranking()
            cfg_c   = _coins.get_cfg()
            await inter.response.edit_message(
                components=paineis.get_painel_coins_ranking(ranking, cfg_c, admin=True),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_CoinsSetUser":
            # Admin abre select de usuário para editar coins
            await inter.response.send_message(
                "Mencione o usuário e use `/coins set @usuario valor` ou "
                "clique em **Editar Coins** na carteira de um membro.",
                ephemeral=True
            )

        # ── Select de ações dentro da partida ─────────────────────────────
        elif cid.startswith("AF_P_acoes_"):
            thread_id = cid.replace("AF_P_acoes_", "")
            await self._handle_acoes_partida(inter, thread_id)

        # ── Call de voz ────────────────────────────────────────────────────
        elif cid.startswith("AF_P_criarcall_"):
            thread_id = cid.replace("AF_P_criarcall_", "")
            await self._criar_call(inter, thread_id)

        elif cid.startswith("AF_P_deletarcall_"):
            thread_id = cid.replace("AF_P_deletarcall_", "")
            await self._deletar_call(inter, thread_id)

        # ── Definir vencedor / pontuação ───────────────────────────────────
        elif cid.startswith("AF_P_setvencedor_"):
            thread_id = cid.replace("AF_P_setvencedor_", "")
            await self._handle_set_vencedor(inter, thread_id)

        elif cid.startswith("AF_P_setpontos_"):
            thread_id = cid.replace("AF_P_setpontos_", "")
            await self._handle_set_pontos(inter, thread_id)

        # ── Ranking ────────────────────────────────────────────────────────
        elif cid == "ApostadoFF_RankingAtualizar" or cid == "ApostadoFF_VerRanking":
            from .functions import stats as _stats_mod
            stats_data = db.get_document(_stats_mod.APOSTADOFF_STATS_KEY) or {}
            await inter.response.edit_message(
                components=paineis.get_painel_ranking(stats_data, admin=True),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_RankingEnviar":
            from .functions import stats as _stats_mod
            config    = _get_config()
            canal_id  = config.get("canal_logs")  # envia no canal de logs por padrão
            canal_rk  = config.get("canal_ranking") or canal_id
            if not canal_rk:
                await inter.response.send_message("Nenhum canal configurado.", ephemeral=True)
                return
            canal = inter.guild.get_channel(int(canal_rk))
            if not canal:
                await inter.response.send_message("Canal não encontrado.", ephemeral=True)
                return
            stats_data = db.get_document(_stats_mod.APOSTADOFF_STATS_KEY) or {}
            await canal.send(
                components=paineis.get_painel_ranking(stats_data),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            await inter.response.send_message(f"{emoji.correct} Ranking enviado em {canal.mention}!", ephemeral=True)

        # ── Carteira inline no perfil ──────────────────────────────────────
        elif cid.startswith("ApostadoFF_VerCarteira:"):
            uid = cid.split(":")[1]
            member = inter.guild.get_member(int(uid))
            if not member:
                await inter.response.send_message("Usuário não encontrado.", ephemeral=True)
                return
            from .functions import stats as _stats_mod
            stats_data  = db.get_document(_stats_mod.APOSTADOFF_STATS_KEY) or {}
            data_perfil = stats_data.get(uid, {"vitorias": 0, "derrotas": 0, "pontos": 0, "partidas": 0})
            cfg_c  = _coins.get_cfg()
            dados  = _coins.get_dados(uid)
            await inter.response.edit_message(
                components=paineis.get_painel_carteira_inline(member, dados, cfg_c, data_perfil),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid.startswith("ApostadoFF_FecharCarteira:"):
            uid = cid.split(":")[1]
            member = inter.guild.get_member(int(uid))
            if not member:
                await inter.response.send_message("Usuário não encontrado.", ephemeral=True)
                return
            from .functions import stats as _stats_mod
            stats_data = db.get_document(_stats_mod.APOSTADOFF_STATS_KEY) or {}
            data = stats_data.get(uid, {"vitorias": 0, "derrotas": 0, "pontos": 0, "partidas": 0})
            await inter.response.edit_message(
                components=paineis.get_painel_perfil(member, data),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        # ── Ver Anexo ──────────────────────────────────────────────────────
        elif cid.startswith("AF_P_veranexo_"):
            thread_id = cid.replace("AF_P_veranexo_", "")
            partidas  = _get_partidas()
            partida   = partidas.get(thread_id)
            if partida:
                await self._ver_anexo(inter, thread_id, partida)
            if not inter.author.guild_permissions.administrator:
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas administradores podem usar esta função.", ephemeral=True
                )
                return
            await inter.response.edit_message(
                components=paineis.get_painel_modelo_servidor(),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif cid == "ApostadoFF_ModeloServidorConfirmar":
            if not inter.author.guild_permissions.administrator:
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas administradores podem usar esta função.", ephemeral=True
                )
                return
            await inter.response.edit_message(
                components=paineis.get_painel_modelo_progresso("🔄 Iniciando... lendo modelo salvo."),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            asyncio.create_task(self._executar_modelo_servidor(inter))

    # ─────────────────────────────────────────────────────────────────────────
    # Enviar painel de mediadores
    # ─────────────────────────────────────────────────────────────────────────
    async def _enviar_painel_mediadores(self, inter: disnake.MessageInteraction):
        config   = _get_config()
        canal_id = config.get("canal_mediadores")
        if not canal_id:
            await inter.response.send_message("Canal de mediadores não configurado.", ephemeral=True)
            return
        canal = inter.guild.get_channel(int(canal_id))
        if not canal:
            await inter.response.send_message("Canal não encontrado.", ephemeral=True)
            return
        await canal.send(
            components=paineis.get_painel_mediadores(_get_mediadores()),
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        await inter.response.send_message(
            f"{emoji.correct} Painel enviado em {canal.mention}!", ephemeral=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Entrar / sair de serviço
    # ─────────────────────────────────────────────────────────────────────────
    async def _entrar_mediador(self, inter: disnake.MessageInteraction):
        if not await _check_mediador(inter):
            return
        uid = str(inter.author.id)
        pix = _get_pix(uid)
        if not pix:
            await inter.response.send_message(
                "🔔 Configure seu PIX antes de entrar em serviço. Clique em **Config PIX**.",
                ephemeral=True
            )
            return
        mediadores = _get_mediadores()
        if uid in mediadores:
            await inter.response.send_message("Você já está em serviço.", ephemeral=True)
            return
        mediadores.append(uid)
        _save_mediadores(mediadores)
        await inter.response.edit_message(
            components=paineis.get_painel_mediadores(mediadores),
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        await inter.followup.send(f"{emoji.correct} Você entrou em serviço!", ephemeral=True)

    async def _sair_mediador(self, inter: disnake.MessageInteraction):
        uid = str(inter.author.id)
        mediadores = _get_mediadores()
        if uid not in mediadores:
            await inter.response.send_message("Você não está em serviço.", ephemeral=True)
            return
        mediadores.remove(uid)
        _save_mediadores(mediadores)
        await inter.response.edit_message(
            components=paineis.get_painel_mediadores(mediadores),
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        await inter.followup.send(f"{emoji.correct} Você saiu de serviço!", ephemeral=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Enviar fila nos canais — envia UMA mensagem por canal, várias mensagens
    # se mais de um canal configurado
    # ─────────────────────────────────────────────────────────────────────────
    async def _enviar_fila_canais(self, inter: disnake.MessageInteraction, tipo: str):
        fila_cfg   = _get_fila_cfg(tipo)
        canais_ids = fila_cfg.get("canais", [])
        if not canais_ids:
            await inter.response.send_message("Nenhum canal configurado.", ephemeral=True)
            return

        modo  = fila_cfg.get("modo", "Clássico")
        valor = fila_cfg.get("valor", "10,00")
        usar_v2 = _usar_v2()
        filas = _get_filas()

        if tipo not in self._fila_messages:
            self._fila_messages[tipo] = {}

        enviados = 0
        await inter.response.defer(ephemeral=True)

        for canal_id in canais_ids:
            canal = inter.guild.get_channel(int(canal_id))
            if not canal:
                continue
            try:
                # Envia com MSGID provisório
                embed, components = paineis.get_fila_embed(tipo, valor, modo, [], fila_cfg, "MSGID")
                if usar_v2:
                    msg = await canal.send(
                        components=components,
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                else:
                    msg = await canal.send(embed=embed, components=components)

                # Edita imediatamente com msg_id real nos custom_ids
                embed2, components2 = paineis.get_fila_embed(tipo, valor, modo, [], fila_cfg, str(msg.id))
                await _edit_msg(msg, embed2, components2)

                # Registrar no DB
                tamanho_fila = tipo.split("_")[0] if "_" in tipo else tipo
                base_dado = {
                    "tipo": tipo, "valor": valor, "modo": modo,
                    "canal_id": str(canal_id),
                    "user1": None, "user1_gel": None,
                    "user2": None, "user2_gel": None,
                }
                if tamanho_fila != "1v1":
                    base_dado["times"] = {"A": [], "B": []}
                filas[str(msg.id)] = base_dado
                # Adicionar ao set de mensagens do canal
                canal_key = str(canal_id)
                if canal_key not in self._fila_messages[tipo]:
                    self._fila_messages[tipo][canal_key] = set()
                self._fila_messages[tipo][canal_key].add(msg.id)
                enviados += 1

            except Exception as e:
                print(f"[ApostadoFF] Erro ao enviar fila {tipo} em {canal_id}: {e}")

        _save_filas(filas)
        await inter.followup.send(f"{emoji.correct} Fila `{tipo}` enviada em {enviados} canal(is)!", ephemeral=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Atualizar embed de uma mensagem de fila específica
    # ─────────────────────────────────────────────────────────────────────────
    async def _atualizar_fila_msg(self, guild: disnake.Guild, msg_id: str, dado: dict):
        tipo     = dado["tipo"]
        valor    = dado["valor"]
        modo     = dado.get("modo", "Clássico")
        canal_id = dado.get("canal_id")
        fila_cfg = _get_fila_cfg(tipo)

        # Separar tamanho e plataforma
        tamanho = tipo.split("_")[0] if "_" in tipo else tipo
        eh_solo = tamanho == "1v1"

        jogadores = []
        if eh_solo:
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

        canal = guild.get_channel(int(canal_id)) if canal_id else None
        if not canal:
            return
        try:
            msg = await canal.fetch_message(int(msg_id))
            embed, components = paineis.get_fila_embed(tipo, valor, modo, jogadores, fila_cfg, msg_id)
            await _edit_msg(msg, embed, components)
        except Exception as e:
            print(f"[ApostadoFF] Erro ao atualizar fila msg {msg_id}: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Botões da fila: entrar / sair
    # custom_id: AF_Q_{tipo}_{msg_id}_{acao}
    # ─────────────────────────────────────────────────────────────────────────
    async def _handle_fila_botao(self, inter: disnake.MessageInteraction):
        parts = inter.data.custom_id.split("_")
        # custom_id: AF_Q_{tipo}_{plataforma}_{msg_id}_{acao}
        # Ex: AF_Q_1v1_mobile_123456_gel_inf
        #     AF_Q_2x2_emulador_123456_entrar_A
        #     AF_Q_4x4_ambos_123456_sair
        # parts[0]=AF, parts[1]=Q, parts[2]=tamanho, parts[3]=plataforma, parts[4]=msg_id, parts[5..]=acao
        if len(parts) < 6:
            return
        tamanho    = parts[2]              # 1v1 | 2x2 | 3x3 | 4x4
        plataforma = parts[3]             # mobile | emulador | ambos
        tipo       = f"{tamanho}_{plataforma}"
        msg_id     = parts[4]
        acao       = "_".join(parts[5:])  # gel_inf | gel_nor | sair | entrar_A | entrar_B | sel

        # StringSelect (1v1): custom_id termina em "_sel", ação real vem em inter.values[0]
        if acao == "sel":
            acao = (inter.values[0] if inter.values else "sair")

        if not _get_mediadores():
            await inter.response.send_message(
                f"{emoji.wrong} Não há orientadores presentes no momento!", ephemeral=True
            )
            return

        filas = _get_filas()
        dado  = filas.get(msg_id)
        if not dado:
            await inter.response.send_message(f"{emoji.wrong} Fila não encontrada.", ephemeral=True)
            return

        uid     = str(inter.author.id)
        eh_solo = tamanho == "1v1"

        # ── Sair ──────────────────────────────────────────────────────────
        if acao == "sair":
            saiu = False
            if eh_solo:
                if dado.get("user1") == uid:
                    dado["user1"] = None; dado["user1_gel"] = None; saiu = True
                elif dado.get("user2") == uid:
                    dado["user2"] = None; dado["user2_gel"] = None; saiu = True
            else:
                times = dado.get("times", {"A": [], "B": []})
                for t in ("A", "B"):
                    if uid in times[t]:
                        times[t].remove(uid); saiu = True; break
                dado["times"] = times
            if not saiu:
                await inter.response.send_message(f"{emoji.wrong} Você não está nesta fila.", ephemeral=True)
                return
            filas[msg_id] = dado
            _save_filas(filas)
            await inter.response.send_message(
                f"🎯 Saída confirmada da fila `{dado['valor']}`.", ephemeral=True
            )
            await self._atualizar_fila_msg(inter.guild, msg_id, dado)
            return

        # ── Verificar se já está na fila ──────────────────────────────────
        if eh_solo:
            if dado.get("user1") == uid or dado.get("user2") == uid:
                await inter.response.send_message(f"{emoji.wrong} Você já está nesta fila.", ephemeral=True)
                return
        else:
            times = dado.get("times", {"A": [], "B": []})
            if uid in times.get("A", []) or uid in times.get("B", []):
                await inter.response.send_message(f"{emoji.wrong} Você já está nesta fila.", ephemeral=True)
                return

        # ── 1v1: Gelo / entrar simples ────────────────────────────────────
        if eh_solo:
            if dado.get("user1") and dado.get("user2"):
                await inter.response.send_message(f"{emoji.wrong} A fila já está cheia.", ephemeral=True)
                return
            gel_map   = {"gel_inf": "Gelo Infinito", "gel_nor": "Gelo Normal", "entrar": None}
            gel_label = gel_map.get(acao)
            if dado.get("user1") and gel_label:
                gel_u1 = dado.get("user1_gel")
                if gel_u1 and gel_u1 != gel_label:
                    await inter.response.send_message(
                        f"{emoji.wrong} Modo incompatível (`{gel_u1}`). Escolha o mesmo modo.", ephemeral=True
                    )
                    return
            slot = "user1" if not dado.get("user1") else "user2"
            dado[slot] = uid
            if gel_label:
                dado[f"{slot}_gel"] = gel_label
            filas[msg_id] = dado
            _save_filas(filas)
            await inter.response.send_message(
                f"🔍 Você entrou na fila `{dado.get('modo', tipo)}`"
                + (f" ({gel_label})" if gel_label else "") + ".",
                ephemeral=True
            )
            await self._atualizar_fila_msg(inter.guild, msg_id, dado)
            if dado.get("user1") and dado.get("user2"):
                await self._criar_partida(inter, dado, msg_id)

        # ── Times: entrar_A / entrar_B ────────────────────────────────────
        else:
            slots_map = {"2x2": 2, "3x3": 3, "4x4": 4}
            n_slots   = slots_map.get(tamanho, 2)
            time_alvo = acao.split("_")[-1]  # "A" ou "B"
            if time_alvo not in ("A", "B"):
                await inter.response.send_message(f"{emoji.wrong} Ação inválida.", ephemeral=True)
                return
            times = dado.get("times", {"A": [], "B": []})
            if len(times.get(time_alvo, [])) >= n_slots:
                await inter.response.send_message(
                    f"{emoji.wrong} Time {time_alvo} já está cheio ({n_slots}/{n_slots}).", ephemeral=True
                )
                return
            times.setdefault(time_alvo, []).append(uid)
            dado["times"] = times
            filas[msg_id] = dado
            _save_filas(filas)
            await inter.response.send_message(
                f"🔍 Você entrou no **Time {time_alvo}** da fila `{dado.get('modo', tipo)}`.",
                ephemeral=True
            )
            await self._atualizar_fila_msg(inter.guild, msg_id, dado)
            total_a = len(times.get("A", []))
            total_b = len(times.get("B", []))
            if total_a == n_slots and total_b == n_slots:
                await self._criar_partida_times(inter, dado, msg_id, times, n_slots)

    # ─────────────────────────────────────────────────────────────────────────
    # Criar tópico privado da partida no canal da fila
    # ─────────────────────────────────────────────────────────────────────────
    async def _criar_partida(self, inter: disnake.MessageInteraction, dado: dict, msg_id: str):
        mediadores = _get_mediadores()
        if not mediadores:
            await inter.followup.send(f"{emoji.wrong} Nenhum mediador disponível.", ephemeral=True)
            return

        tipo  = dado["tipo"]
        valor = dado["valor"]
        user1 = dado["user1"]
        user2 = dado["user2"]

        # Pegar mediador (FIFO) e removê-lo da lista
        orientador_id = mediadores.pop(0)
        _save_mediadores(mediadores)

        # Atualizar painel de mediadores
        await self._atualizar_painel_mediadores(inter.guild)

        # Criar tópico privado no canal da fila
        # (inter.channel é o canal onde está a mensagem de fila)
        canal_fila = inter.channel
        nome_thread = f"{tipo}-{_gen_protocol(4)}"

        try:
            # Thread privada (apenas membros com permissão podem ver)
            thread = await canal_fila.create_thread(
                name=nome_thread,
                type=disnake.ChannelType.private_thread,
                auto_archive_duration=60,
                reason="Partida ApostadoFF"
            )
            # Adicionar membros ao tópico
            for uid in [user1, user2, orientador_id]:
                member = inter.guild.get_member(int(uid))
                if member:
                    try:
                        await thread.add_user(member)
                    except Exception:
                        pass
        except Exception as e:
            # Fallback: canal não suporta threads privadas, tenta pública
            print(f"[ApostadoFF] Thread privada falhou ({e}), tentando pública...")
            try:
                thread = await canal_fila.create_thread(
                    name=nome_thread,
                    type=disnake.ChannelType.public_thread,
                    auto_archive_duration=60,
                    reason="Partida ApostadoFF"
                )
                for uid in [user1, user2, orientador_id]:
                    member = inter.guild.get_member(int(uid))
                    if member:
                        try:
                            await thread.add_user(member)
                        except Exception:
                            pass
            except Exception as e2:
                print(f"[ApostadoFF] Falha ao criar thread: {e2}")
                await inter.followup.send(f"{emoji.wrong} Não foi possível criar o tópico da partida.", ephemeral=True)
                return

        # Salvar dados da partida indexados pelo ID do tópico
        partidas = _get_partidas()
        partidas[str(thread.id)] = {
            "tipo": tipo, "valor": valor,
            "user1": user1, "user1_gel": dado.get("user1_gel"),
            "user2": user2, "user2_gel": dado.get("user2_gel"),
            "orientador": orientador_id,
            "user1_confirmou": False, "user2_confirmou": False,
            "vencedor": None,
            "created_at": int(time.time()),
            "msg_id_fila": msg_id,
            "canal_fila_id": str(canal_fila.id),
        }
        _save_partidas(partidas)

        # Resetar slots da fila
        filas = _get_filas()
        dado_reset = {**dado, "user1": None, "user1_gel": None, "user2": None, "user2_gel": None}
        filas[msg_id] = dado_reset
        _save_filas(filas)

        # Remover do tracking local para que a task crie uma nova fila vazia em paralelo
        canal_fila_key = str(dado.get("canal_id", ""))
        if tipo in self._fila_messages and canal_fila_key in self._fila_messages[tipo]:
            self._fila_messages[tipo][canal_fila_key].discard(int(msg_id))

        await self._atualizar_fila_msg(inter.guild, msg_id, dado_reset)

        # Enviar embed de confirmação no tópico
        embed, components = paineis.get_confirmacao_embed(tipo, valor, str(thread.id))
        usar_v2 = _usar_v2()
        if usar_v2:
            await thread.send(
                content=f"<@{user1}> <@{user2}>",
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            await thread.send(
                content=f"<@{user1}> <@{user2}>",
                embed=embed, components=components
            )

    async def _criar_partida_times(self, inter: disnake.MessageInteraction, dado: dict, msg_id: str, times: dict, n_slots: int):
        """Cria tópico de partida para filas de times (2x2, 3x3, 4x4)."""
        mediadores = _get_mediadores()
        if not mediadores:
            await inter.followup.send(f"{emoji.wrong} Nenhum mediador disponível.", ephemeral=True)
            return

        tipo  = dado["tipo"]
        valor = dado["valor"]
        todos_uids = times.get("A", []) + times.get("B", [])

        orientador_id = mediadores.pop(0)
        _save_mediadores(mediadores)
        await self._atualizar_painel_mediadores(inter.guild)

        canal_fila  = inter.channel
        nome_thread = f"{tipo.split('_')[0]}-{_gen_protocol(4)}"

        try:
            thread = await canal_fila.create_thread(
                name=nome_thread, type=disnake.ChannelType.private_thread,
                auto_archive_duration=60, reason="Partida ApostadoFF"
            )
        except Exception:
            try:
                thread = await canal_fila.create_thread(
                    name=nome_thread, type=disnake.ChannelType.public_thread,
                    auto_archive_duration=60, reason="Partida ApostadoFF"
                )
            except Exception as e2:
                await inter.followup.send(f"{emoji.wrong} Não foi possível criar o tópico: {e2}", ephemeral=True)
                return

        for uid in todos_uids + [orientador_id]:
            member = inter.guild.get_member(int(uid))
            if member:
                try:
                    await thread.add_user(member)
                except Exception:
                    pass

        partidas = _get_partidas()
        partidas[str(thread.id)] = {
            "tipo": tipo, "valor": valor,
            "user1": todos_uids[0] if todos_uids else None,
            "user2": todos_uids[1] if len(todos_uids) > 1 else None,
            "times": times, "todos_uids": todos_uids,
            "orientador": orientador_id,
            "user1_confirmou": False, "user2_confirmou": False,
            "vencedor": None,
            "created_at": int(time.time()),
            "msg_id_fila": msg_id, "canal_fila_id": str(canal_fila.id),
        }
        _save_partidas(partidas)

        # Resetar fila
        filas = _get_filas()
        dado_reset = {**dado, "times": {"A": [], "B": []}, "user1": None, "user2": None}
        filas[msg_id] = dado_reset
        _save_filas(filas)
        await self._atualizar_fila_msg(inter.guild, msg_id, dado_reset)

        pix = _get_pix(orientador_id)
        mencoes = " ".join(f"<@{u}>" for u in todos_uids)
        embed, components = paineis.get_partida_painel(
            tipo=tipo, valor=valor, thread_id=str(thread.id),
            user1=todos_uids[0] if todos_uids else "?",
            user2=todos_uids[-1] if todos_uids else "?",
            orientador=orientador_id, pix_orientador=pix
        )
        usar_v2 = _usar_v2()
        if usar_v2:
            await thread.send(content=mencoes, components=components,
                              flags=disnake.MessageFlags(is_components_v2=True))
        else:
            await thread.send(content=mencoes, embed=embed, components=components)

    async def _atualizar_painel_mediadores(self, guild: disnake.Guild):
        """Edita o painel de mediadores no canal configurado."""
        config   = _get_config()
        canal_id = config.get("canal_mediadores")
        if not canal_id:
            return
        canal = guild.get_channel(int(canal_id))
        if not canal:
            return
        try:
            async for msg in canal.history(limit=30):
                if msg.author.id == guild.me.id:
                    await msg.edit(
                        components=paineis.get_painel_mediadores(_get_mediadores()),
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                    break
        except Exception as e:
            print(f"[ApostadoFF] Erro ao atualizar painel mediadores: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Confirmar / Recusar presença
    # ─────────────────────────────────────────────────────────────────────────
    async def _handle_confirmar(self, inter: disnake.MessageInteraction, thread_id: str):
        partidas = _get_partidas()
        partida  = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return

        uid   = str(inter.author.id)
        user1 = partida["user1"]
        user2 = partida["user2"]

        if uid not in (user1, user2):
            await inter.response.send_message(f"{emoji.wrong} Você não é jogador desta partida.", ephemeral=True)
            return

        campo = "user1_confirmou" if uid == user1 else "user2_confirmou"
        if partida.get(campo):
            await inter.response.send_message(f"{emoji.wrong} Você já confirmou.", ephemeral=True)
            return

        partida[campo] = True
        _save_partidas(partidas)

        await inter.response.send_message(f"{emoji.correct} Presença confirmada!", ephemeral=True)
        await inter.channel.send(f"👋 {inter.author.mention} confirmou o jogo!")

        # Ambos confirmaram?
        if partida.get("user1_confirmou") and partida.get("user2_confirmou"):
            proto = _gen_protocol(5)
            tipo  = partida["tipo"]

            # Renomear tópico — Thread usa .edit(name=...)
            try:
                await inter.channel.edit(name=f"{tipo}-{proto}")
            except Exception as e:
                print(f"[ApostadoFF] Erro ao renomear thread: {e}")

            # Limpar mensagens antigas
            try:
                msgs = [m async for m in inter.channel.history(limit=15)]
                await inter.channel.delete_messages(msgs)
            except Exception:
                pass

            await asyncio.sleep(1)
            await self._enviar_painel_partida(inter.channel, thread_id, partida)

    async def _handle_recusar(self, inter: disnake.MessageInteraction, thread_id: str):
        partidas = _get_partidas()
        partida  = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return

        uid = str(inter.author.id)
        if uid not in (partida["user1"], partida["user2"]):
            await inter.response.send_message(f"{emoji.wrong} Você não é jogador desta partida.", ephemeral=True)
            return

        orientador = partida["orientador"]
        # Recolocar mediador em serviço
        mediadores = _get_mediadores()
        if orientador not in mediadores:
            mediadores.append(orientador)
            _save_mediadores(mediadores)
        await self._atualizar_painel_mediadores(inter.guild)

        embed_aviso = disnake.Embed(
            description=f"**Olá <@{orientador}>, {inter.author.mention} acaba de deixar a fila!**",
            color=disnake.Color.orange()
        ).set_author(name="Abandono de fila...") \
         .set_footer(text=f"{inter.author} saiu!", icon_url=inter.author.display_avatar.url)

        await inter.channel.send(embeds=[embed_aviso])
        await inter.response.send_message("Tópico sendo deletado em 5 segundos...")
        await asyncio.sleep(5)

        partidas.pop(thread_id, None)
        _save_partidas(partidas)

        try:
            await inter.channel.delete()
        except Exception:
            pass

    async def _enviar_painel_partida(self, thread: disnake.Thread, thread_id: str, partida: dict):
        orientador = partida["orientador"]
        pix = _get_pix(orientador)
        embed, components = paineis.get_partida_painel(
            tipo=partida["tipo"], valor=partida["valor"],
            thread_id=thread_id,
            user1=partida["user1"], user2=partida["user2"],
            orientador=orientador, pix_orientador=pix
        )
        usar_v2 = _usar_v2()
        if usar_v2:
            await thread.send(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            await thread.send(embed=embed, components=components)

    # ─────────────────────────────────────────────────────────────────────────
    # Select de ações da partida
    # ─────────────────────────────────────────────────────────────────────────
    async def _handle_acoes_partida(self, inter: disnake.MessageInteraction, thread_id: str):
        partidas = _get_partidas()
        partida  = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return
        if str(inter.author.id) != partida["orientador"]:
            await inter.response.send_message(f"{emoji.wrong} Apenas o orientador pode usar isto.", ephemeral=True)
            return

        acao = inter.values[0]

        if acao == "painelcall":
            call_existe = self._call_existe(inter.guild, inter.channel.name)
            embed, components = paineis.get_painel_chamada(thread_id, call_existe)
            usar_v2 = _usar_v2()
            if usar_v2:
                await inter.response.send_message(
                    components=components,
                    flags=disnake.MessageFlags(is_components_v2=True),
                    ephemeral=True
                )
            else:
                await inter.response.send_message(embed=embed, components=components, ephemeral=True)

        elif acao == "chamaranalista":
            await self._chamar_analista(inter, thread_id, partida)

        elif acao == "definirvencedor":
            await inter.response.send_message(
                content="Selecione o vencedor:",
                components=paineis.get_vencedor_select(thread_id),
                ephemeral=True
            )

        elif acao == "veranexo":
            await self._ver_anexo(inter, thread_id, partida)

        elif acao == "finalizar":
            orientador = partida["orientador"]
            # Deletar call se existir
            await self._deletar_call_se_existir(inter.guild, inter.channel.name)
            # Recolocar mediador em serviço
            mediadores = _get_mediadores()
            if orientador not in mediadores:
                mediadores.append(orientador)
                _save_mediadores(mediadores)
            await self._atualizar_painel_mediadores(inter.guild)

            await inter.response.send_message("🔔 Tópico sendo deletado em 5 segundos...")
            partidas.pop(thread_id, None)
            _save_partidas(partidas)
            await asyncio.sleep(5)
            try:
                await inter.channel.delete()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Modelo Servidor Apostado — recriação completa + auto-sync do bot
    # ─────────────────────────────────────────────────────────────────────────
    async def _executar_modelo_servidor(self, inter: disnake.MessageInteraction):
        guild    = inter.guild
        msg      = inter.message   # mensagem do painel para editar progresso

        async def _update(texto: str):
            try:
                await msg.edit(
                    components=paineis.get_painel_modelo_progresso(texto),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception:
                pass

        # ── 1. Ler modelo ─────────────────────────────────────────────────
        try:
            with open(SERVER_MODEL_PATH, "r", encoding="utf-8") as f:
                model = json.load(f)
        except Exception as e:
            await _update(f"{emoji.wrong} Erro ao ler o modelo salvo:\n```{e}```\nVerifique se o arquivo existe em `{SERVER_MODEL_PATH}`.")
            return

        await _update("🗑️ **Etapa 1/5** — Apagando canais existentes...")

        # ── 2. Apagar canais (exceto o canal atual do painel) ─────────────
        for channel in list(guild.channels.cache.values()):
            if channel.id == inter.channel_id:
                continue
            try:
                await channel.delete()
                await asyncio.sleep(0.3)
            except Exception:
                pass

        await _update("🗑️ **Etapa 2/5** — Apagando cargos existentes...")

        # ── 3. Apagar cargos (exceto @everyone e acima do bot) ────────────
        bot_top = guild.me.roles[-1].position
        for role in list(guild.roles):
            if role.id == guild.id:            # @everyone
                continue
            if role.position >= bot_top:       # acima/igual ao bot
                continue
            try:
                await role.delete()
                await asyncio.sleep(0.3)
            except Exception:
                pass

        await _update("🔨 **Etapa 3/5** — Recriando cargos...")

        # ── 4. Recriar cargos ─────────────────────────────────────────────
        role_map: dict[str, disnake.Role] = {}   # nome → Role criado
        for r in sorted(model.get("roles", []), key=lambda x: x.get("position", 0)):
            try:
                new_role = await guild.create_role(
                    name=r["name"],
                    color=disnake.Colour(int(r.get("color", 0))),
                    permissions=disnake.Permissions(int(r.get("permissions", 0))),
                    hoist=r.get("hoist", False),
                    mentionable=r.get("mentionable", False),
                )
                role_map[r["name"]] = new_role
                await asyncio.sleep(0.4)
            except Exception:
                pass

        await _update("📁 **Etapa 4/5** — Recriando categorias e canais...")

        # ── 5. Recriar categorias ─────────────────────────────────────────
        category_map: dict[str, disnake.CategoryChannel] = {}
        for c in sorted(model.get("categories", []), key=lambda x: x.get("position", 0)):
            try:
                new_cat = await guild.create_category(
                    name=c["name"],
                    position=c.get("position", 0),
                )
                category_map[c["name"]] = new_cat
                await asyncio.sleep(0.4)
            except Exception:
                pass

        # ── 6. Recriar canais ─────────────────────────────────────────────
        # Mapeamento de IDs antigos (do JSON) → novos IDs de cargos criados
        # Os overwrites do JSON podem referenciar IDs antigos de cargos;
        # tentamos resolver pelo nome se disponível, senão mantemos o ID.
        old_id_to_role: dict[str, disnake.Role] = {}
        for r_data in model.get("roles", []):
            if "id" in r_data and r_data["name"] in role_map:
                old_id_to_role[str(r_data["id"])] = role_map[r_data["name"]]

        created_channels: dict[str, disnake.abc.GuildChannel] = {}  # nome → canal

        CHANNEL_TYPES = {0: disnake.ChannelType.text, 2: disnake.ChannelType.voice}

        for ch in sorted(model.get("channels", []), key=lambda x: x.get("position", 0)):
            try:
                parent = category_map.get(ch.get("parent")) if ch.get("parent") else None

                overwrites: dict[disnake.abc.Snowflake, disnake.PermissionOverwrite] = {}
                for po in ch.get("permissionOverwrites", []):
                    po_id   = str(po["id"])
                    allow   = disnake.Permissions(int(po.get("allow", 0)))
                    deny    = disnake.Permissions(int(po.get("deny",  0)))
                    ow_obj  = disnake.PermissionOverwrite.from_pair(allow, deny)
                    po_type = po.get("type", 0)

                    if po_type == 1:  # membro específico
                        target = guild.get_member(int(po_id))
                    else:             # cargo (type=0)
                        # Tenta resolver pelo mapeamento de IDs antigos primeiro
                        target = old_id_to_role.get(po_id)
                        if target is None:
                            # Pode ser o @everyone (mesmo ID do servidor)
                            if po_id == str(guild.id):
                                target = guild.default_role
                            else:
                                target = guild.get_role(int(po_id))

                    if target is not None:
                        overwrites[target] = ow_obj

                ch_type = ch.get("type", 0)
                if ch_type == 2:
                    new_ch = await guild.create_voice_channel(
                        name=ch["name"],
                        category=parent,
                        position=ch.get("position", 0),
                        overwrites=overwrites,
                    )
                else:
                    new_ch = await guild.create_text_channel(
                        name=ch["name"],
                        category=parent,
                        position=ch.get("position", 0),
                        overwrites=overwrites,
                    )
                created_channels[ch["name"]] = new_ch
                await asyncio.sleep(0.4)
            except Exception:
                pass

        await _update("⚙️ **Etapa 5/5** — Sincronizando configurações do bot...")

        # ── 7. Auto-sync do bot com base nos canais/cargos criados ──────────
        # Mapeamentos esperados do modelo Apostado:
        #   canal_logs          ← canal "logs-partidas"
        #   canal_mediadores    ← canal "💼・iniciar・serviço"
        #   categoria_apostas   ← categoria "Apostas"
        #   cargo_mediador      ← cargo "/Mediador"

        config = _get_config()

        # Canal de logs de partidas
        ch_logs = created_channels.get("logs-partidas")
        if ch_logs:
            config["canal_logs"] = str(ch_logs.id)

        # Canal de mediadores (painel de serviço)
        ch_med = created_channels.get("💼・iniciar・serviço")
        if ch_med:
            config["canal_mediadores"] = str(ch_med.id)

        # Categoria de apostas (para criação de calls de voz)
        cat_apostas = category_map.get("Apostas")
        if cat_apostas:
            config["categoria_apostas"] = str(cat_apostas.id)

        # Cargo de mediador
        role_mediador = role_map.get("/Mediador")
        if role_mediador:
            config["cargo_mediador"] = str(role_mediador.id)

        _save_config(config)

        # ── 8. Enviar painel de mediadores no canal configurado ────────────
        if ch_med:
            try:
                await ch_med.send(
                    components=paineis.get_painel_mediadores(_get_mediadores()),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception:
                pass

        # ── 9. Resultado final ────────────────────────────────────────────
        linhas = [f"{emoji.correct} **Servidor recriado com sucesso!**\n"]
        linhas.append(f"**Cargos criados:** {len(role_map)}")
        linhas.append(f"**Categorias criadas:** {len(category_map)}")
        linhas.append(f"**Canais criados:** {len(created_channels)}")
        linhas.append("")
        linhas.append("**Configurações sincronizadas:**")
        linhas.append(f"・**Canal Logs:** {ch_logs.mention if ch_logs else '`não encontrado`'}")
        linhas.append(f"・**Canal Mediadores:** {ch_med.mention if ch_med else '`não encontrado`'}")
        linhas.append(f"・**Categoria Apostas:** `{'Apostas' if cat_apostas else 'não encontrado'}`")
        linhas.append(f"・**Cargo Mediador:** {role_mediador.mention if role_mediador else '`não encontrado`'}")
        linhas.append("\n-# Ative o sistema e as filas pelo painel principal.")

        try:
            await msg.edit(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"#  Modelo Aplicado\n-# Painel > ApostadoFF > Modelo Servidor\n\n"
                            + "\n".join(linhas)
                        ),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Voltar ao Painel", style=disnake.ButtonStyle.blurple,
                                          custom_id="ApostadoFF_PainelPrincipal"),
                    ),
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        except Exception:
            pass

    async def _ver_anexo(self, inter: disnake.MessageInteraction, thread_id: str, partida: dict):
        nomes = {"1v1": "1 x 1", "2x2": "2 x 2", "4x4": "4 x 4"}
        tipo  = partida["tipo"]
        embed = disnake.Embed(title="📎 Anexo da Partida", color=disnake.Color.green())
        embed.description = (
            f"**Formato: ``{nomes.get(tipo, tipo.upper())}``**\n"
            f"**Valor: ``R${partida['valor']}``**\n"
            f"**Jogadores:**\n"
            f"<@{partida['user1']}>"
            + (f" | {partida['user1_gel']}" if partida.get("user1_gel") else "")
            + f"\n<@{partida['user2']}>"
            + (f" | {partida['user2_gel']}" if partida.get("user2_gel") else "")
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Call de voz
    # ─────────────────────────────────────────────────────────────────────────
    def _call_existe(self, guild: disnake.Guild, nome_thread: str) -> bool:
        return any(c.name == f"📞・{nome_thread}" for c in guild.voice_channels)

    async def _deletar_call_se_existir(self, guild: disnake.Guild, nome_thread: str):
        vc = disnake.utils.get(guild.voice_channels, name=f"📞・{nome_thread}")
        if vc:
            try:
                await vc.delete()
            except Exception:
                pass

    async def _criar_call(self, inter: disnake.MessageInteraction, thread_id: str):
        config   = _get_config()
        categoria_id = config.get("categoria_apostas")
        partidas = _get_partidas()
        partida  = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return

        user1 = partida["user1"]
        user2 = partida["user2"]
        categoria = inter.guild.get_channel(int(categoria_id)) if categoria_id else None

        ow = {
            inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False, connect=False),
            inter.guild.me: disnake.PermissionOverwrite(view_channel=True, connect=True),
        }
        for uid in [str(inter.author.id), user1, user2]:
            member = inter.guild.get_member(int(uid))
            if member:
                ow[member] = disnake.PermissionOverwrite(
                    view_channel=True, connect=True, send_messages=True
                )

        try:
            await inter.guild.create_voice_channel(
                name=f"📞・{inter.channel.name}",
                category=categoria,
                overwrites=ow
            )
            embed, components = paineis.get_painel_chamada(thread_id, True)
            usar_v2 = _usar_v2()
            if usar_v2:
                await inter.response.edit_message(
                    components=components,
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            else:
                await inter.response.edit_message(embed=embed, components=components)
        except Exception as e:
            await inter.response.send_message(f"Erro ao criar call: {e}", ephemeral=True)

    async def _deletar_call(self, inter: disnake.MessageInteraction, thread_id: str):
        await self._deletar_call_se_existir(inter.guild, inter.channel.name)
        embed, components = paineis.get_painel_chamada(thread_id, False)
        usar_v2 = _usar_v2()
        if usar_v2:
            await inter.response.edit_message(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            await inter.response.edit_message(embed=embed, components=components)

    # ─────────────────────────────────────────────────────────────────────────
    # Definir vencedor / pontuação
    # ─────────────────────────────────────────────────────────────────────────
    async def _handle_set_vencedor(self, inter: disnake.MessageInteraction, thread_id: str):
        partidas = _get_partidas()
        partida  = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return
        if str(inter.author.id) != partida["orientador"]:
            await inter.response.send_message(f"{emoji.wrong} Apenas o orientador pode definir o vencedor.", ephemeral=True)
            return

        vencedor = inter.values[0]
        partida["vencedor"] = vencedor
        _save_partidas(partidas)

        await inter.response.edit_message(
            content=f"Vencedor: <@{vencedor}>. Agora selecione a pontuação:",
            components=paineis.get_pontuacao_select(thread_id)
        )

    async def _handle_set_pontos(self, inter: disnake.MessageInteraction, thread_id: str):
        partidas = _get_partidas()
        partida  = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return
        if str(inter.author.id) != partida["orientador"]:
            await inter.response.send_message(f"{emoji.wrong} Apenas o orientador pode definir pontos.", ephemeral=True)
            return

        pontos   = int(inter.values[0])
        vencedor = partida.get("vencedor")
        if not vencedor:
            await inter.response.send_message("Vencedor não definido.", ephemeral=True)
            return

        perdedor  = partida["user2"] if vencedor == partida["user1"] else partida["user1"]
        orientador = partida["orientador"]

        await stats.adicionar_vitoria(vencedor, pontos)
        await stats.adicionar_derrota(perdedor)

        # ── Coins: recompensar mediador ───────────────────────────────────
        coins_cfg   = _coins.get_cfg()
        coins_valor = int(coins_cfg.get("coins_por_ap_mediador", 10))
        dados_med   = _coins.add_coins(orientador, coins_valor, tipo="ap")
        emj_coin    = coins_cfg.get("emoji_moeda", "🪙")
        nome_coin   = coins_cfg.get("nome_moeda", "Coin")

        # Verificar e aplicar Cargo UPs para o mediador
        med_member = inter.guild.get_member(int(orientador))
        novos_ups  = []
        if med_member:
            novos_ups = await _coins.verificar_cargo_ups(med_member, inter.guild, tipo="mediador")

        # ── Log ───────────────────────────────────────────────────────────
        config = _get_config()
        canal_logs_id = config.get("canal_logs")
        if canal_logs_id:
            canal_logs = inter.guild.get_channel(int(canal_logs_id))
            if canal_logs:
                embed_log = disnake.Embed(title="Partida Finalizada", color=disnake.Color.green())
                embed_log.add_field(name="Vencedor",    value=f"<@{vencedor}>")
                embed_log.add_field(name="Perdedor",    value=f"<@{perdedor}>")
                embed_log.add_field(name="Valor",       value=f"R$ {partida['valor']}")
                embed_log.add_field(name="Pontos",      value=str(pontos))
                embed_log.add_field(name="Tipo",        value=partida["tipo"])
                embed_log.add_field(name="Mediador",    value=f"<@{orientador}>")
                embed_log.add_field(
                    name=f"{emj_coin} Coins (med)",
                    value=f"+{dados_med['saldo'] - (dados_med['saldo'] - coins_valor)} → saldo `{dados_med['saldo']}`"
                )
                if novos_ups:
                    embed_log.add_field(name="🏅 Cargo UP", value=", ".join(novos_ups), inline=False)
                await canal_logs.send(embed=embed_log)

        # Recolocar mediador em serviço
        mediadores = _get_mediadores()
        if orientador not in mediadores:
            mediadores.append(orientador)
            _save_mediadores(mediadores)
        await self._atualizar_painel_mediadores(inter.guild)

        # Montar texto extra de coins para a mensagem final
        ups_txt   = f"\n🏅 **Cargo UP desbloqueado:** {', '.join(novos_ups)}" if novos_ups else ""
        coins_txt = f"\n{emj_coin} **{med_member.display_name if med_member else 'Mediador'}** recebeu `{coins_valor} {nome_coin}s` (saldo: `{dados_med['saldo']}`){ups_txt}"

        embed_final = disnake.Embed(title="🏆 Partida Encerrada!", color=disnake.Color.gold())
        embed_final.description = (
            f"**Vencedor:** <@{vencedor}> (+{pontos} ponto{'s' if pontos > 1 else ''})\n"
            f"**Derrotado:** <@{perdedor}>\n"
            f"{coins_txt}\n\n"
            "Tópico sendo deletado em 5 segundos."
        )
        await inter.response.edit_message(content="", embeds=[embed_final], components=[])
        await inter.channel.send("🔔 Tópico sendo deletado em 5 segundos...")

        await self._deletar_call_se_existir(inter.guild, inter.channel.name)
        partidas.pop(thread_id, None)
        _save_partidas(partidas)

        await asyncio.sleep(5)
        try:
            await inter.channel.delete()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Analistas — entrar/sair de serviço
    # ─────────────────────────────────────────────────────────────────────────
    async def _check_analista(self, inter: disnake.MessageInteraction) -> bool:
        config   = _get_config()
        cargo_id = config.get("cargo_analista")
        if not cargo_id:
            await inter.response.send_message("Cargo de analista não configurado.", ephemeral=True)
            return False
        role = inter.guild.get_role(int(cargo_id))
        if not role or role not in inter.author.roles:
            await inter.response.send_message("Você não possui o cargo de analista.", ephemeral=True)
            return False
        return True

    async def _entrar_analista(self, inter: disnake.MessageInteraction):
        if not await self._check_analista(inter):
            return
        uid       = str(inter.author.id)
        analistas = _get_analistas()
        if uid in analistas:
            await inter.response.send_message("Você já está em serviço.", ephemeral=True)
            return
        analistas.append(uid)
        _save_analistas(analistas)
        await inter.response.edit_message(
            components=paineis.get_painel_analistas(analistas),
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        await inter.followup.send(f"{emoji.correct} Você entrou em serviço como analista!", ephemeral=True)

    async def _sair_analista(self, inter: disnake.MessageInteraction):
        uid       = str(inter.author.id)
        analistas = _get_analistas()
        if uid not in analistas:
            await inter.response.send_message("Você não está em serviço.", ephemeral=True)
            return
        analistas.remove(uid)
        _save_analistas(analistas)
        await inter.response.edit_message(
            components=paineis.get_painel_analistas(analistas),
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        await inter.followup.send(f"{emoji.correct} Você saiu de serviço.", ephemeral=True)

    async def _enviar_painel_analistas(self, inter: disnake.MessageInteraction):
        config   = _get_config()
        canal_id = config.get("canal_analistas")
        if not canal_id:
            await inter.response.send_message("Canal de analistas não configurado.", ephemeral=True)
            return
        canal = inter.guild.get_channel(int(canal_id))
        if not canal:
            await inter.response.send_message("Canal não encontrado.", ephemeral=True)
            return
        await canal.send(
            components=paineis.get_painel_analistas(_get_analistas()),
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        await inter.response.send_message(f"{emoji.correct} Painel enviado em {canal.mention}!", ephemeral=True)

    async def _atualizar_painel_analistas(self, guild: disnake.Guild):
        config   = _get_config()
        canal_id = config.get("canal_analistas")
        if not canal_id:
            return
        canal = guild.get_channel(int(canal_id))
        if not canal:
            return
        try:
            async for msg in canal.history(limit=20):
                if msg.author == guild.me and msg.components:
                    await msg.edit(
                        components=paineis.get_painel_analistas(_get_analistas()),
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                    break
        except Exception as e:
            print(f"[ApostadoFF] Erro ao atualizar painel analistas: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Chamar analista na partida + veredicto
    # ─────────────────────────────────────────────────────────────────────────
    async def _chamar_analista(self, inter: disnake.MessageInteraction, thread_id: str, partida: dict):
        analistas = _get_analistas()
        if not analistas:
            await inter.response.send_message(
                f"{emoji.wrong} Nenhum analista em serviço no momento.", ephemeral=True
            )
            return

        # Pega o primeiro analista disponível (FIFO) e remove da fila
        analista_id = analistas.pop(0)
        _save_analistas(analistas)
        await self._atualizar_painel_analistas(inter.guild)

        # Adiciona o analista ao tópico
        analista_member = inter.guild.get_member(int(analista_id))
        if analista_member:
            try:
                await inter.channel.add_user(analista_member)
            except Exception:
                pass

        # Salva analista na partida
        partidas = _get_partidas()
        if thread_id in partidas:
            partidas[thread_id]["analista"] = analista_id
            _save_partidas(partidas)

        # Envia painel de análise no tópico
        embed, components = paineis.get_painel_analise(thread_id, partida)
        usar_v2 = _usar_v2()
        mencao  = f"<@{analista_id}> foi chamado para analisar esta partida!"
        if usar_v2:
            await inter.response.send_message(
                content=mencao,
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            await inter.response.send_message(
                content=mencao, embed=embed, components=components
            )

    async def _handle_analista_veredicto(self, inter: disnake.MessageInteraction,
                                          thread_id: str, veredicto: str):
        partidas  = _get_partidas()
        partida   = partidas.get(thread_id)
        if not partida:
            await inter.response.send_message("Partida não encontrada.", ephemeral=True)
            return

        analista_id = partida.get("analista")
        if str(inter.author.id) != analista_id:
            await inter.response.send_message(
                f"{emoji.wrong} Apenas o analista designado pode emitir o veredicto.", ephemeral=True
            )
            return

        # ── Recompensar analista com coins ────────────────────────────────
        coins_cfg   = _coins.get_cfg()
        coins_valor = int(coins_cfg.get("coins_por_ap_analista", 5))
        dados_ana   = _coins.add_coins(analista_id, coins_valor, tipo="analise")
        emj_coin    = coins_cfg.get("emoji_moeda", "🪙")
        nome_coin   = coins_cfg.get("nome_moeda", "Coin")

        ana_member = inter.guild.get_member(int(analista_id))
        novos_ups  = []
        if ana_member:
            novos_ups = await _coins.verificar_cargo_ups(ana_member, inter.guild, tipo="analista")

        # Recolocar analista em serviço
        analistas = _get_analistas()
        if analista_id not in analistas:
            analistas.append(analista_id)
            _save_analistas(analistas)
        await self._atualizar_painel_analistas(inter.guild)

        VEREDICTS = {
            "limpo":        ("✅ Limpo",             disnake.Color.green()),
            "hack":         ("🚩 Suspeito de Hack",  disnake.Color.red()),
            "inconclusivo": ("⚠️ Inconclusivo",       disnake.Color.orange()),
        }
        titulo_v, cor_v = VEREDICTS.get(veredicto, ("?", disnake.Color.greyple()))
        ups_txt  = f"\n🏅 Cargo UP desbloqueado: **{', '.join(novos_ups)}**" if novos_ups else ""
        nome_ana = ana_member.display_name if ana_member else "Analista"

        embed_v = disnake.Embed(
            title=f"🔍 Veredicto: {titulo_v}",
            color=cor_v,
            description=(
                f"**Analista:** <@{analista_id}>\n"
                f"**Resultado:** {titulo_v}\n\n"
                f"{emj_coin} `+{coins_valor} {nome_coin}s` para {nome_ana} "
                f"(saldo: `{dados_ana['saldo']}`){ups_txt}"
            )
        )
        # Desabilitar os botões editando a mensagem original
        await inter.response.edit_message(embeds=[embed_v], components=[])

        # Logar
        config = _get_config()
        canal_logs_id = config.get("canal_logs")
        if canal_logs_id:
            canal_logs = inter.guild.get_channel(int(canal_logs_id))
            if canal_logs:
                await canal_logs.send(embed=embed_v)

    # ─────────────────────────────────────────────────────────────────────────
    # Criar Fila Personalizada — enviar painel estático no canal
    # ─────────────────────────────────────────────────────────────────────────
    async def _enviar_painel_criar_fila(self, inter: disnake.MessageInteraction):
        config   = _get_config()
        # Usa qualquer canal configurado de fila, ou o canal atual
        all_cfg  = db.get_document("apostadoff_filas_cfg") or {}
        canais   = []
        for fc in all_cfg.values():
            canais.extend(fc.get("canais", []))
        canais = list(dict.fromkeys(canais))  # deduplicar

        targets = canais if canais else [str(inter.channel.id)]
        usar_v2 = _usar_v2()
        await inter.response.defer(ephemeral=True)

        for cid_str in targets:
            canal = inter.guild.get_channel(int(cid_str))
            if not canal:
                continue
            resultado = paineis.get_painel_criar_fila()
            try:
                if usar_v2 and isinstance(resultado, list):
                    await canal.send(components=resultado,
                                     flags=disnake.MessageFlags(is_components_v2=True))
                elif isinstance(resultado, tuple):
                    embed, comps = resultado
                    await canal.send(embed=embed, components=comps)
                else:
                    await canal.send(components=resultado,
                                     flags=disnake.MessageFlags(is_components_v2=True))
            except Exception as e:
                print(f"[ApostadoFF] Erro ao enviar painel criar fila em {cid_str}: {e}")

        await inter.followup.send(f"{emoji.correct} Painel de criar fila enviado!", ephemeral=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Modal callbacks — Coins edit, CargoUp, CriarFila
    # ─────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener("on_modal_submit")
    async def handle_modals(self, inter: disnake.ModalInteraction):
        cid = inter.data.custom_id

        # ── Editar config coins ────────────────────────────────────────────
        if cid == "ApostadoFF_CoinsEditModal":
            try:
                cfg = _coins.get_cfg()
                cfg["nome_moeda"]    = inter.text_values["nome_moeda"].strip()
                cfg["emoji_moeda"]   = inter.text_values["emoji_moeda"].strip()
                cfg["multiplicador"] = float(inter.text_values["multiplicador"].replace(",", "."))
                _coins.save_cfg(cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_coins_config(cfg),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception as e:
                await inter.response.send_message(f"Erro: {e}", ephemeral=True)

        # ── Coins por AP — Mediador ────────────────────────────────────────
        elif cid == "ApostadoFF_MedCoinsModal":
            try:
                valor = int(inter.text_values["valor"].strip())
                cfg   = _coins.get_cfg()
                cfg["coins_por_ap_mediador"] = valor
                _coins.save_cfg(cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_mediadores_admin(_get_config(), inter.guild, cfg),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception as e:
                await inter.response.send_message(f"Erro: {e}", ephemeral=True)

        # ── Coins por análise — Analista ───────────────────────────────────
        elif cid == "ApostadoFF_AnaCoinsModal":
            try:
                valor = int(inter.text_values["valor"].strip())
                cfg   = _coins.get_cfg()
                cfg["coins_por_ap_analista"] = valor
                _coins.save_cfg(cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_config_analistas(_get_config(), inter.guild, cfg),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception as e:
                await inter.response.send_message(f"Erro: {e}", ephemeral=True)

        # ── Cargo UP — Mediador ────────────────────────────────────────────
        elif cid.startswith("ApostadoFF_MedCargoUpModal:"):
            idx = int(cid.split(":")[1])
            try:
                cargo_id      = inter.text_values["cargo_id"].strip()
                nome_rank     = inter.text_values["nome_rank"].strip()
                min_coins_tot = int(inter.text_values.get("min_coins_total", "0") or "0")
                min_aps       = int(inter.text_values.get("min_aps", "0") or "0")

                cfg  = _coins.get_cfg()
                ups  = cfg.get("cargo_ups_mediador", [])
                novo = {
                    "cargo_id": cargo_id, "nome_rank": nome_rank,
                    "min_coins_total": min_coins_tot, "min_aps": min_aps,
                }
                if idx == -1:
                    ups.append(novo)
                else:
                    ups[idx] = novo
                cfg["cargo_ups_mediador"] = ups
                _coins.save_cfg(cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_med_cargo_ups(cfg),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception as e:
                await inter.response.send_message(f"Erro: {e}", ephemeral=True)

        # ── Cargo UP — Analista ────────────────────────────────────────────
        elif cid.startswith("ApostadoFF_AnaCargoUpModal:"):
            idx = int(cid.split(":")[1])
            try:
                cargo_id      = inter.text_values["cargo_id"].strip()
                nome_rank     = inter.text_values["nome_rank"].strip()
                min_coins_tot = int(inter.text_values.get("min_coins_total", "0") or "0")
                min_analises  = int(inter.text_values.get("min_analises", "0") or "0")

                cfg  = _coins.get_cfg()
                ups  = cfg.get("cargo_ups_analista", [])
                novo = {
                    "cargo_id": cargo_id, "nome_rank": nome_rank,
                    "min_coins_total": min_coins_tot, "min_analises": min_analises,
                }
                if idx == -1:
                    ups.append(novo)
                else:
                    ups[idx] = novo
                cfg["cargo_ups_analista"] = ups
                _coins.save_cfg(cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_ana_cargo_ups(cfg),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception as e:
                await inter.response.send_message(f"Erro: {e}", ephemeral=True)

        # ── Criar Fila Personalizada ───────────────────────────────────────
        elif cid == "ApostadoFF_CriarFilaAdminModal":
            try:
                # Lê valores do modal (StringSelect via resolved_values + TextInput via text_values)
                rv        = inter.resolved_values
                formato   = rv.get("fila_formato")
                plat      = rv.get("fila_plataforma")
                valor_raw = inter.text_values.get("fila_valor", "").strip().replace("R$", "").strip()

                # Normalizar selects (podem vir como lista)
                if isinstance(formato, (list, tuple)):
                    formato = formato[0] if formato else None
                if isinstance(plat, (list, tuple)):
                    plat = plat[0] if plat else None

                formato = (formato or "").strip().lower()
                plat    = (plat    or "ambos").strip().lower()

                if formato not in ("1v1", "2x2", "3x3", "4x4"):
                    await inter.response.send_message(
                        f"{emoji.wrong} Formato inválido. Selecione uma opção válida.", ephemeral=True
                    )
                    return
                if plat not in ("mobile", "emulador", "ambos"):
                    plat = "ambos"

                float(valor_raw.replace(",", "."))  # valida valor

                tipo = f"{formato}_{plat}"
                all_cfg = _get_filas_cfg()
                if tipo in all_cfg:
                    await inter.response.send_message(
                        f"{emoji.wrong} A fila `{tipo}` já existe! Gerencie-a pelo painel de filas.",
                        ephemeral=True
                    )
                    return

                nova_cfg = {
                    "ativo": False,
                    "gelo_infinito": True,
                    "gelo_normal": True,
                    "canais": [],
                    "modo": "Clássico",
                    "valor": valor_raw,
                    "aparencia": {},
                }
                all_cfg[tipo] = nova_cfg
                _save_filas_cfg(all_cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_gerenciar_fila(tipo, nova_cfg, inter.guild),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Valor inválido. Use formato `10,00`.", ephemeral=True)
            except Exception as e:
                await inter.response.send_message(f"{emoji.wrong} Erro ao criar fila: {e}", ephemeral=True)

        # ── Aparência da fila ──────────────────────────────────────────────
        elif cid.startswith("ApostadoFF_FilaAparenciaModal:"):
            tipo = cid.split(":")[1]
            try:
                fila_cfg = _get_fila_cfg(tipo)
                apar = fila_cfg.get("aparencia", {})
                apar["titulo"]       = inter.text_values.get("titulo", "").strip()
                apar["texto_extra"]  = inter.text_values.get("texto_extra", "").strip()
                apar["cor_hex"]      = inter.text_values.get("cor_hex", "").strip()
                apar["label_entrar"] = inter.text_values.get("label_entrar", "").strip()
                apar["label_sair"]   = inter.text_values.get("label_sair", "").strip()
                fila_cfg["aparencia"] = apar
                _save_fila_cfg(tipo, fila_cfg)
                await inter.response.edit_message(
                    components=paineis.get_painel_fila_aparencia(tipo, fila_cfg),
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            except Exception as e:
                await inter.response.send_message(f"{emoji.wrong} Erro: {e}", ephemeral=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Comando de prefixo: {prefix}p [@usuario]
    # ─────────────────────────────────────────────────────────────────────────
    @commands.command(name="p")
    async def cmd_perfil(self, ctx: commands.Context, membro: disnake.Member = None):
        """Exibe o perfil e estatísticas de um jogador. Uso: {prefix}p [@usuario]"""
        from functions.prefix import get_prefix
        from .functions import stats as _stats_mod
        member     = membro or ctx.author
        stats_data = db.get_document(_stats_mod.APOSTADOFF_STATS_KEY) or {}
        data       = stats_data.get(str(member.id), {"vitorias": 0, "derrotas": 0, "pontos": 0, "partidas": 0})
        await ctx.send(
            components=paineis.get_painel_perfil(member, data),
            flags=disnake.MessageFlags(is_components_v2=True)
        )




def setup(bot):
    bot.add_cog(ApostadoFFCog(bot))