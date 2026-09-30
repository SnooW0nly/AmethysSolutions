"""
paineis.py — Embeds, componentes e painéis do ApostadoFF
"""
import disnake
import disnake.ui as ui
from functions.emoji import emoji
from functions.database import database as db


# ─── helpers ──────────────────────────────────────────────────────────────────
def _ck():
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _usar_v2() -> bool:
    """Retorna se o servidor usa Components V2 (Container) — lido da config global."""
    config = db.get_document("apostadoff_config") or {}
    return bool(config.get("usar_v2", False))


# ─── Modals ────────────────────────────────────────────────────────────────────
class TaxaModal(disnake.ui.Modal):
    def __init__(self):
        config = db.get_document("apostadoff_config") or {}
        super().__init__(
            title="Configurar Taxa de Serviço",
            custom_id="ApostadoFF_TaxaModal",
            components=[
                disnake.ui.TextInput(
                    label="Taxa (R$)", custom_id="taxa",
                    placeholder="Ex: 1.80", style=disnake.TextInputStyle.short,
                    max_length=10, required=True,
                    value=str(config.get("taxa_servico", "1.80"))
                )
            ]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            taxa = float(inter.text_values["taxa"].replace(",", "."))
        except Exception:
            await inter.response.send_message("Valor inválido.", ephemeral=True)
            return
        config = db.get_document("apostadoff_config") or {}
        config["taxa_servico"] = taxa
        db.save_document("apostadoff_config", config)
        await inter.response.edit_message(
            components=get_painel_taxa(config),
            flags=disnake.MessageFlags(is_components_v2=True)
        )


class PixModal(disnake.ui.Modal):
    """Modal para o mediador configurar o PIX."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        pix = db.get_document(f"apostadoff_pix_{user_id}") or {}
        super().__init__(
            title="Configurar sua Chave PIX",
            custom_id=f"ApostadoFF_PixModal:{user_id}",
            components=[
                disnake.ui.TextInput(
                    label="Chave PIX", custom_id="chave",
                    placeholder="Ex: 999.999.999-99 / email / telefone",
                    style=disnake.TextInputStyle.short,
                    max_length=60, required=True, value=pix.get("Chave", "")
                ),
                disnake.ui.TextInput(
                    label="Tipo (CPF / CNPJ / Email / Telefone)", custom_id="tipo",
                    placeholder="Ex: CPF", style=disnake.TextInputStyle.short,
                    max_length=15, required=True, value=pix.get("Type", "")
                ),
            ]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        chave = inter.text_values["chave"].strip()
        tipo  = inter.text_values["tipo"].strip()
        db.save_document(f"apostadoff_pix_{self.user_id}", {"Chave": chave, "Type": tipo})
        await inter.response.send_message(
            f"{emoji.correct} PIX configurado com sucesso!\n> **Chave:** `{chave}`\n> **Tipo:** `{tipo}`",
            ephemeral=True
        )


# ─── Painel Principal ──────────────────────────────────────────────────────────
def get_painel_principal(config: dict) -> list:
    ativo  = config.get("ativo", False)
    s_icon = emoji.correct if ativo else emoji.wrong
    s_text = "Ativo" if ativo else "Inativo"
    usar_v2 = config.get("usar_v2", False)

    cat_txt  = f"<#{config['categoria_apostas']}>" if config.get("categoria_apostas") else "`Não configurado`"
    logs_txt = f"<#{config['canal_logs']}>"      if config.get("canal_logs")      else "`Não configurado`"
    taxa     = config.get("taxa_servico", 1.80)

    def _ts(v): return disnake.ButtonStyle.green if v else disnake.ButtonStyle.grey
    def _tl(l, v): return f"{l}: {'Ativo' if v else 'Inativo'}"

    _rows_main = [
        ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Painel > **ApostadoFF**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay("Sistema de apostas Free Fire.\nGerencie filas, partidas e mediadores."),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            f"**Status:** {s_icon} `{s_text}`\n\n"
            f"**Categoria Apostas:** {cat_txt}\n"
            f"**Canal Logs:** {logs_txt}\n"
            f"**Taxa de Serviço:** R$ {taxa:.2f}\n"
            f"**Modo Container (V2):** {f'{emoji.on}' if usar_v2 else f'{emoji.off}'}"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        # Toggles do sistema
        ui.ActionRow(
            ui.Button(
                label="Desativar" if ativo else "Ativar",
                style=disnake.ButtonStyle.red if ativo else disnake.ButtonStyle.green,
                emoji=emoji.wrong if ativo else emoji.correct,
                custom_id="ApostadoFF_Toggle"
            ),
            ui.Button(label=_tl("Container", usar_v2), style=_ts(usar_v2),
                      emoji=emoji.on if usar_v2 else emoji.off,
                      custom_id="ApostadoFF_ToggleV2"),
        ),
        # Configurações gerais
        ui.ActionRow(
            ui.Button(label="Canais", style=disnake.ButtonStyle.grey,
                      emoji=emoji.edit, custom_id="ApostadoFF_Canais"),
            ui.Button(label="Taxa",   style=disnake.ButtonStyle.grey,
                      emoji=emoji.edit, custom_id="ApostadoFF_Taxa"),
        ),
        # Módulos
        ui.ActionRow(
            ui.Button(label="Mediadores", style=disnake.ButtonStyle.blurple,
                      custom_id="ApostadoFF_PainelMediadores", emoji=emoji.sword),
            ui.Button(label="Analistas", style=disnake.ButtonStyle.blurple,
                      custom_id="ApostadoFF_PainelAnalistasAdmin", emoji=emoji.sword),
            ui.Button(label="Coins", style=disnake.ButtonStyle.blurple,
                      custom_id="ApostadoFF_CoinsConfig", emoji=emoji.coin),
        ),
        # Ferramentas
        ui.ActionRow(
            ui.Button(label="Configurar Filas", style=disnake.ButtonStyle.green,
                      emoji=emoji.edit, custom_id="ApostadoFF_ConfigFilas"),
            ui.Button(label="Ranking", style=disnake.ButtonStyle.grey,
                      custom_id="ApostadoFF_VerRanking", emoji=emoji.king),
        ),
        # Zona de perigo
        ui.ActionRow(
            ui.Button(label="Modelo Servidor Apostado", style=disnake.ButtonStyle.red,
                      custom_id="ApostadoFF_ModeloServidor", emoji=emoji.embed),
        ),
    ]

    return [
        ui.Container(*_rows_main, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="PainelInicial"),
        ),
    ]


# ─── Painel Canais ─────────────────────────────────────────────────────────────
def get_painel_canais(config: dict, guild: disnake.Guild) -> list:
    categoria_id = config.get("categoria_apostas")
    logs_id      = config.get("canal_logs")
    cat_opts = [
        disnake.SelectOption(label=c.name[:100], value=str(c.id),
                             default=(str(c.id) == str(categoria_id)))
        for c in guild.categories[:25]
    ]
    log_opts = [
        disnake.SelectOption(label=f"#{c.name[:97]}", value=str(c.id),
                             default=(str(c.id) == str(logs_id)))
        for c in guild.text_channels[:25]
    ]
    cat_txt  = f"<#{categoria_id}>" if categoria_id else "`Não configurado`"
    logs_txt = f"<#{logs_id}>"      if logs_id      else "`Não configurado`"

    rows = [
        ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Painel > ApostadoFF > **Canais**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            f"**Categoria Apostas:** {cat_txt}\n"
            f"*(usada apenas para canal de voz — tópicos abrem no canal da fila)*\n"
            f"**Canal Logs:** {logs_txt}"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]
    if cat_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelectCategoria",
            placeholder="Selecione a categoria (para calls de voz)...", options=cat_opts
        )))
    if log_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelectCanalLogs",
            placeholder="Selecione o canal de logs...", options=log_opts
        )))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
        ),
    ]


# ─── Painel Taxa ───────────────────────────────────────────────────────────────
def get_painel_taxa(config: dict) -> list:
    taxa = config.get("taxa_servico", 1.80)
    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > ApostadoFF > **Taxa**"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(f"**Taxa de Serviço:** R$ {taxa:.2f}"),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(label="Editar Taxa", style=disnake.ButtonStyle.blurple,
                          emoji=emoji.edit, custom_id="ApostadoFF_EditarTaxa"),
            ),
            **_ck(),
        ),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
        ),
    ]


# ─── Painel Mediadores Admin ───────────────────────────────────────────────────
def get_painel_mediadores_admin(config: dict, guild: disnake.Guild, coins_cfg: dict) -> list:
    """Painel administrativo completo de mediadores."""
    canal_med_id = config.get("canal_mediadores")
    cargo_med_id = config.get("cargo_mediador")
    canal_txt    = f"<#{canal_med_id}>"  if canal_med_id  else "`Não configurado`"
    cargo_txt    = f"<@&{cargo_med_id}>" if cargo_med_id  else "`Não configurado`"
    coins_por_ap = coins_cfg.get("coins_por_ap_mediador", 10)
    emj          = coins_cfg.get("emoji_moeda", "🪙")
    nome_coin    = coins_cfg.get("nome_moeda", "Coin")

    canal_opts = [
        disnake.SelectOption(label=f"#{c.name[:97]}", value=str(c.id),
                             default=(str(c.id) == str(canal_med_id)))
        for c in guild.text_channels[:25]
    ]
    cargo_opts = [
        disnake.SelectOption(label=r.name[:100], value=str(r.id),
                             default=(str(r.id) == str(cargo_med_id)))
        for r in reversed([r for r in guild.roles if r.name != "@everyone"][-24:])
    ]

    rows = [
        ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Painel > ApostadoFF > **Mediadores**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            f"**Canal dos Mediadores:** {canal_txt}\n"
            f"**Cargo de Mediador:** {cargo_txt}\n"
            f"**{emj} Coins por AP:** `{coins_por_ap} {nome_coin}`\n\n"
            f"-# Configure o canal onde o painel de mediadores será publicado e o cargo necessário."
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]
    if canal_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelectCanalMediadores",
            placeholder="Selecione o canal de mediadores...", options=canal_opts
        )))
    if cargo_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelectCargoMediador",
            placeholder="Selecione o cargo de mediador...", options=cargo_opts
        )))
    action_btns = []
    if canal_med_id:
        action_btns.append(
            ui.Button(label="Enviar Painel de Mediadores", style=disnake.ButtonStyle.green,
                      emoji=emoji.plus, custom_id="ApostadoFF_EnviarPainelMediadores")
        )
    action_btns += [
        ui.Button(label="Editar Coins por AP", style=disnake.ButtonStyle.blurple,
                  emoji=emoji.edit, custom_id="ApostadoFF_MedEditarCoins"),
        ui.Button(label="Cargo UPs Mediador", style=disnake.ButtonStyle.grey,
                  emoji=emoji.role, custom_id="ApostadoFF_MedCargoUps"),
    ]
    rows.append(ui.ActionRow(*action_btns))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
        ),
    ]


# ─── Modal: Editar coins por AP do mediador ────────────────────────────────────
class MedCoinsModal(disnake.ui.Modal):
    def __init__(self, valor_atual: int):
        super().__init__(
            title="Coins por AP — Mediador",
            custom_id="ApostadoFF_MedCoinsModal",
            components=[
                disnake.ui.TextInput(
                    label="Coins por AP mediado", custom_id="valor",
                    placeholder="Ex: 10",
                    style=disnake.TextInputStyle.short, max_length=6, required=True,
                    value=str(valor_atual),
                ),
            ],
        )


# ─── Painel: Cargo UPs do Mediador ────────────────────────────────────────────
def get_painel_med_cargo_ups(coins_cfg: dict) -> list:
    ups  = coins_cfg.get("cargo_ups_mediador", [])
    emj  = coins_cfg.get("emoji_moeda", "🪙")
    nome = coins_cfg.get("nome_moeda", "Coin")

    if ups:
        linhas = []
        for i, up in enumerate(ups):
            reqs = []
            if up.get("min_coins_total", 0): reqs.append(f"`{up['min_coins_total']} {nome} ganhos`")
            if up.get("min_aps",         0): reqs.append(f"`{up['min_aps']} APs`")
            req_txt = "  ·  ".join(reqs) if reqs else "`sem requisitos`"
            linhas.append(
                f"**`{i+1}.`** <@&{up['cargo_id']}> — **{up.get('nome_rank','?')}**\n"
                f"-# {req_txt}"
            )
        corpo = "\n\n".join(linhas)
    else:
        corpo = "> Nenhum Cargo UP configurado para mediadores."

    botoes_ups = []
    for i in range(min(len(ups), 5)):
        botoes_ups.append(ui.Button(
            label=f"Editar #{i+1}", style=disnake.ButtonStyle.grey,
            custom_id=f"ApostadoFF_MedCargoUpEditar_{i}"
        ))

    rows = [
        ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Painel > ApostadoFF > Mediadores > **Cargo UPs**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            "Cargos concedidos automaticamente ao mediador ao atingir requisitos.\n"
            "Requisitos avaliados ao fim de cada AP mediado."
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(corpo),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.ActionRow(
            ui.Button(label="Adicionar Cargo UP", style=disnake.ButtonStyle.green,
                      custom_id="ApostadoFF_MedCargoUpAdicionar", emoji=emoji.plus),
            *(botoes_ups),
        ),
    ]
    if ups:
        rows.append(ui.ActionRow(
            ui.Button(label="Remover último", style=disnake.ButtonStyle.red,
                      custom_id="ApostadoFF_MedCargoUpRemover", emoji=emoji.delete),
        ))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelMediadores"),
        ),
    ]


# ─── Modal: Cargo UP de Mediador ──────────────────────────────────────────────
class MedCargoUpModal(disnake.ui.Modal):
    def __init__(self, idx: int = -1, up: dict = None):
        up = up or {}
        self.idx = idx
        super().__init__(
            title="Cargo UP — Mediador",
            custom_id=f"ApostadoFF_MedCargoUpModal:{idx}",
            components=[
                disnake.ui.TextInput(
                    label="ID do Cargo", custom_id="cargo_id",
                    placeholder="ID numérico do cargo Discord",
                    style=disnake.TextInputStyle.short, max_length=25, required=True,
                    value=str(up.get("cargo_id", "")),
                ),
                disnake.ui.TextInput(
                    label="Nome do Rank", custom_id="nome_rank",
                    placeholder="Ex: Mediador Ouro",
                    style=disnake.TextInputStyle.short, max_length=40, required=True,
                    value=up.get("nome_rank", ""),
                ),
                disnake.ui.TextInput(
                    label="Coins totais ganhos (mínimo, 0=ignorar)", custom_id="min_coins_total",
                    placeholder="Ex: 100",
                    style=disnake.TextInputStyle.short, max_length=10, required=False,
                    value=str(up.get("min_coins_total", 0)),
                ),
                disnake.ui.TextInput(
                    label="APs mediados (mínimo, 0=ignorar)", custom_id="min_aps",
                    placeholder="Ex: 10",
                    style=disnake.TextInputStyle.short, max_length=10, required=False,
                    value=str(up.get("min_aps", 0)),
                ),
            ],
        )



# ─── Painel de Mediadores (publicado no canal público) ─────────────────────────
def get_painel_mediadores(mediadores: list) -> list:
    if mediadores:
        texto = "\n".join(f"> **`{i+1}°`** | <@{uid}>" for i, uid in enumerate(mediadores))
    else:
        texto = "> Nenhum mediador em serviço."

    return [
        ui.Container(
            ui.TextDisplay(
                "# Painel de Mediadores\n"
                "-# Entre em serviço para mediar apostas."
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(f"**Mediadores em serviço ({len(mediadores)}):**\n{texto}"),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(label="Entrar em serviço", style=disnake.ButtonStyle.secondary,
                          emoji="<:membro_bots:1362616511281365203>",
                          custom_id="ApostadoFF_EntrarFilaMediador"),
                ui.Button(label="Sair de serviço", style=disnake.ButtonStyle.secondary,
                          emoji="<:exit_StorM:1362616686594752692>",
                          custom_id="ApostadoFF_SairFilaMediador"),
                ui.Button(label="Config PIX", style=disnake.ButtonStyle.blurple,
                          emoji=emoji.pix, custom_id="ApostadoFF_ConfigPix"),
            ),
            **_ck(),
        ),
    ]


# ─── Painel: Modelo Servidor Apostado ─────────────────────────────────────────
def get_painel_modelo_servidor() -> list:
    """Painel de confirmação antes de recriar o servidor pelo modelo salvo."""
    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > ApostadoFF > **Modelo Servidor**"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(
                "⚠️ **ATENÇÃO — Esta ação é irreversível!**\n\n"
                "Ao confirmar, o bot irá:\n"
                "- Apagar **todos** os canais (exceto o atual)\n"
                "- Apagar **todos** os cargos recriáveis\n"
                "- Recriar cargos, categorias e canais conforme o modelo salvo\n"
                "- **Auto-configurar** o sistema (logs, filas, cargo de mediador, canal de serviço)\n\n"
                "Isso pode levar alguns minutos. Tem certeza que deseja continuar?"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(label="Confirmar e Recriar", style=disnake.ButtonStyle.red,
                          custom_id="ApostadoFF_ModeloServidorConfirmar", emoji=emoji.correct),
                ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey,
                          custom_id="ApostadoFF_PainelPrincipal", emoji=emoji.wrong),
            ),
            **_ck(),
        ),
    ]


def get_painel_modelo_progresso(etapa: str) -> list:
    """Painel exibido durante a execução mostrando progresso."""
    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.clock} Recriando Servidor...\n"
                f"-# Painel > ApostadoFF > **Modelo Servidor**"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(etapa),
            **_ck(),
        ),
    ]


# ─── Painel: Selecionar Fila ───────────────────────────────────────────────────
# ─── Painel: Config Filas (admin) ──────────────────────────────────────────────
def get_painel_config_filas(filas_cfg: dict) -> list:
    """
    Painel principal de gerenciamento de filas (admin).
    Lista as filas criadas + botão Criar + select para gerenciar uma.
    """
    PLAT_EMOJI = {"mobile": emoji.mobile, "emulador": emoji.controller, "ambos": "🕹️"}
    TAM_NOME   = {"1v1": "1×1", "2x2": "2×2", "3x3": "3×3", "4x4": "4×4"}

    if filas_cfg:
        linhas = []
        for tipo, cfg in filas_cfg.items():
            if "_" in tipo:
                tam, plat = tipo.split("_", 1)
            else:
                tam, plat = tipo, "ambos"
            pe   = PLAT_EMOJI.get(plat, "🕹️")
            tn   = TAM_NOME.get(tam, tam.upper())
            ativo = cfg.get("ativo", False)
            st   = f"{emoji.correct if ativo else emoji.wrong}"
            n_ch = len(cfg.get("canais", []))
            val  = cfg.get("valor", "?")
            linhas.append(f"{st} **{tn}** {pe} `{plat.title()}` — R$ `{val}` — `{n_ch}` canal(is)")
        corpo = "\n".join(linhas)
    else:
        corpo = "> Nenhuma fila criada ainda. Clique em **➕ Criar Fila** para começar."

    rows = [
        ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# Painel > ApostadoFF > **Configurar Filas**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            "Gerencie as filas de aposta. Cada fila é identificada por formato e plataforma.\n"
            "-# Crie filas, configure canais, aparência e ative/desative individualmente."
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(corpo),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.ActionRow(
            ui.Button(label="Criar Fila", style=disnake.ButtonStyle.green,
                      emoji=emoji.plus, custom_id="ApostadoFF_AdminCriarFila"),
        ),
    ]

    if filas_cfg:
        opts = []
        for tipo, cfg in filas_cfg.items():
            if "_" in tipo:
                tam, plat = tipo.split("_", 1)
            else:
                tam, plat = tipo, "ambos"
            pe  = PLAT_EMOJI.get(plat, "🕹️")
            tn  = TAM_NOME.get(tam, tam.upper())
            val = cfg.get("valor", "?")
            ativo = cfg.get("ativo", False)
            opts.append(disnake.SelectOption(
                label=f"{tn} {plat.title()} — R$ {val}",
                value=tipo,
                emoji=pe,
                description="Ativa" if ativo else "Inativa"
            ))
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelecionarFilaGerenciar",
            placeholder="Selecionar fila para gerenciar...",
            options=opts[:25]
        )))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
        ),
    ]


# ─── Modal: Criar Fila (com StringSelect V2 dentro do modal) ──────────────────
class CriarFilaAdminModal(disnake.ui.Modal):
    """Modal com StringSelect para formato/plataforma + TextInput para valor."""
    def __init__(self):
        super().__init__(
            title="Criar Nova Fila",
            custom_id="ApostadoFF_CriarFilaAdminModal",
            components=[
                disnake.ui.Label(
                    text="Formato da fila",
                    component=disnake.ui.StringSelect(
                        custom_id="fila_formato",
                        placeholder="Selecione o formato...",
                        options=[
                            disnake.SelectOption(label="1 × 1",    value="1v1"),
                            disnake.SelectOption(label="2 × 2",   value="2x2"),
                            disnake.SelectOption(label="3 × 3",    value="3x3"),
                            disnake.SelectOption(label="4 × 4",value="4x4"),
                        ],
                        min_values=1, max_values=1,
                    ),
                    description="Escolha o número de jogadores por lado.",
                ),
                disnake.ui.Label(
                    text="Plataforma",
                    component=disnake.ui.StringSelect(
                        custom_id="fila_plataforma",
                        placeholder="Selecione a plataforma...",
                        options=[
                            disnake.SelectOption(label="Mobile",            value="mobile"),
                            disnake.SelectOption(label="Emulador",          value="emulador"),
                            disnake.SelectOption(label="Ambos (Mob + Emu)", value="ambos"),
                        ],
                        min_values=1, max_values=1,
                    ),
                    description="Plataforma aceita nesta fila.",
                ),
                disnake.ui.TextInput(
                    label="Valor por jogador (R$)",
                    custom_id="fila_valor",
                    placeholder="Ex: 10,00  —  valor por jogador, sem a taxa",
                    style=disnake.TextInputStyle.short,
                    max_length=10,
                    required=True,
                ),
            ],
        )


# ─── Painel: Gerenciar Fila Específica ─────────────────────────────────────────
def get_painel_gerenciar_fila(tipo: str, fila_cfg: dict, guild: disnake.Guild) -> list:
    """
    Painel completo de gerenciamento de uma fila:
    toggle ativo/gelo, multi-select canais, botão aparência, enviar.
    """
    PLAT_EMOJI = {"mobile": emoji.mobile, "emulador": emoji.controller, "ambos": "🕹️"}
    PLAT_NOME  = {"mobile": "Mobile", "emulador": "Emulador", "ambos": "Mobile + Emulador"}
    TAM_NOME   = {"1v1": "1 × 1", "2x2": "2 × 2", "3x3": "3 × 3", "4x4": "4 × 4"}

    if "_" in tipo:
        tamanho, plataforma = tipo.split("_", 1)
    else:
        tamanho, plataforma = tipo, "ambos"

    pe      = PLAT_EMOJI.get(plataforma, "🕹️")
    pn      = PLAT_NOME.get(plataforma, plataforma.title())
    tn      = TAM_NOME.get(tamanho, tamanho.upper())
    eh_solo = tamanho == "1v1"

    ativo         = fila_cfg.get("ativo", False)
    gelo_inf      = fila_cfg.get("gelo_infinito", True)
    gelo_nor      = fila_cfg.get("gelo_normal", True)
    valor         = fila_cfg.get("valor", "10,00")
    modo          = fila_cfg.get("modo", "Clássico")
    canais_cfg    = fila_cfg.get("canais", [])

    canais_txt = " ".join(f"<#{c}>" for c in canais_cfg) if canais_cfg else "`Nenhum canal configurado`"

    def _ts(v): return disnake.ButtonStyle.green if v else disnake.ButtonStyle.grey
    def _tl(l, v): return f"{l}: {'Ativo' if v else 'Inativo'}"

    # StringSelect de canais com até 25 opções (multi-select)
    canal_opts = [
        disnake.SelectOption(
            label=f"#{c.name[:97]}", value=str(c.id),
            default=(str(c.id) in [str(x) for x in canais_cfg])
        )
        for c in guild.text_channels[:25]
    ]

    rows = [
        ui.TextDisplay(
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"- Fila — {tn} {pe}\n"
            f"-# Painel > ApostadoFF > Filas > **{tn} `{pn}`**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            f"**Plataforma:** {pe} `{pn}`  ·  **Valor:** R$ `{valor}`  ·  **Modo:** `{modo}`\n"
            f"**Canais:** {canais_txt}\n"
            f"-# O formato Container/Embed é controlado pelo toggle global no painel principal."
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        # Toggles
        ui.ActionRow(
            ui.Button(label=_tl("Fila", ativo), style=_ts(ativo),
                      emoji=emoji.on if ativo else emoji.off,
                      custom_id=f"ApostadoFF_FilaToggle_{tipo}_ativo"),
            ui.Button(label=_tl("Gelo Infinito", gelo_inf), style=_ts(gelo_inf),
                      emoji=emoji.on if gelo_inf else emoji.off,
                      custom_id=f"ApostadoFF_FilaToggle_{tipo}_gelo_infinito",
                      disabled=not eh_solo),
            ui.Button(label=_tl("Gelo Normal", gelo_nor), style=_ts(gelo_nor),
                      emoji=emoji.on if gelo_nor else emoji.off,
                      custom_id=f"ApostadoFF_FilaToggle_{tipo}_gelo_normal",
                      disabled=not eh_solo),
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]

    # Multi-select de canais
    if canal_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id=f"ApostadoFF_FilaAddCanal_{tipo}",
            placeholder="Selecionar canais onde a fila será enviada...",
            options=canal_opts,
            min_values=1,
            max_values=min(len(canal_opts), 10),
        )))

    # Botões de ação — positivos primeiro, destrutivos por último
    btns_acao = [
        ui.Button(label="Aparência", style=disnake.ButtonStyle.blurple,
                  custom_id=f"ApostadoFF_FilaAparencia_{tipo}", emoji=emoji.edit),
        ui.Button(label="Enviar nos Canais", style=disnake.ButtonStyle.green,
                  emoji=emoji.arrow, custom_id=f"ApostadoFF_FilaEnviar_{tipo}",
                  disabled=not canais_cfg),
    ]
    if canais_cfg:
        btns_acao.append(ui.Button(label="Limpar Canais",emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                    custom_id=f"ApostadoFF_FilaLimparCanais_{tipo}"))
    btns_acao.append(ui.Button(label="Excluir Fila", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                custom_id=f"ApostadoFF_FilaExcluir_{tipo}"))
    rows.append(ui.ActionRow(*btns_acao))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_ConfigFilas"),
        ),
    ]


# ─── Modal: Editar aparência da fila ──────────────────────────────────────────
class FilaAparenciaModal(disnake.ui.Modal):
    """Configura título, texto personalizado e cor do embed/container da fila."""
    def __init__(self, tipo: str, fila_cfg: dict):
        self.tipo = tipo
        apar = fila_cfg.get("aparencia", {})
        super().__init__(
            title="Aparência da Fila",
            custom_id=f"ApostadoFF_FilaAparenciaModal:{tipo}",
            components=[
                disnake.ui.TextInput(
                    label="Título personalizado (deixe vazio = padrão)",
                    custom_id="titulo",
                    placeholder="Ex: ⚔️ Apostar — 1v1 Mobile",
                    style=disnake.TextInputStyle.short,
                    max_length=80, required=False,
                    value=apar.get("titulo", ""),
                ),
                disnake.ui.TextInput(
                    label="Texto extra (exibido abaixo das info)",
                    custom_id="texto_extra",
                    placeholder="Ex: 🔥 Melhores jogadores do servidor!",
                    style=disnake.TextInputStyle.paragraph,
                    max_length=300, required=False,
                    value=apar.get("texto_extra", ""),
                ),
                disnake.ui.TextInput(
                    label="Cor do container (hex, ex: #FF5733)",
                    custom_id="cor_hex",
                    placeholder="Ex: #FF5733  (deixe vazio = cor global)",
                    style=disnake.TextInputStyle.short,
                    max_length=10, required=False,
                    value=apar.get("cor_hex", ""),
                ),
                disnake.ui.TextInput(
                    label="Label botão Entrar (1v1) / Time A (times)",
                    custom_id="label_entrar",
                    placeholder="Ex: ⚔️ Entrar  /  🔵 Time A",
                    style=disnake.TextInputStyle.short,
                    max_length=40, required=False,
                    value=apar.get("label_entrar", ""),
                ),
                disnake.ui.TextInput(
                    label="Label botão Sair / Time B",
                    custom_id="label_sair",
                    placeholder="Ex: 🚪 Sair  /  🔴 Time B",
                    style=disnake.TextInputStyle.short,
                    max_length=40, required=False,
                    value=apar.get("label_sair", ""),
                ),
            ],
        )


# ─── Painel: Preview de aparência da fila ──────────────────────────────────────
def get_painel_fila_aparencia(tipo: str, fila_cfg: dict) -> list:
    """Mostra as configurações de aparência atuais e botão para editar."""
    PLAT_EMOJI = {"mobile": emoji.mobile, "emulador": emoji.controller, "ambos": "🕹️"}
    TAM_NOME   = {"1v1": "1 × 1", "2x2": "2 × 2", "3x3": "3 × 3", "4x4": "4 × 4"}

    if "_" in tipo:
        tamanho, plataforma = tipo.split("_", 1)
    else:
        tamanho, plataforma = tipo, "ambos"

    pe   = PLAT_EMOJI.get(plataforma, "🕹️")
    tn   = TAM_NOME.get(tamanho, tamanho.upper())
    apar = fila_cfg.get("aparencia", {})

    titulo      = apar.get("titulo")     or f"{emoji.sword} Apostar — {tn} {pe}  *(padrão)*"
    texto_extra = apar.get("texto_extra") or "`(sem texto extra)`"
    cor_hex     = apar.get("cor_hex")    or "`(cor global)`"
    l_entrar    = apar.get("label_entrar") or "`(padrão)`"
    l_sair      = apar.get("label_sair")   or "`(padrão)`"

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"- {emoji.edit} Aparência — {tn} {pe}\n"
                f"-# Painel > ApostadoFF > Filas > {tn} > **Aparência**"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(
                f"**Título:** {titulo}\n"
                f"**Texto extra:**\n> {texto_extra}\n"
                f"**Cor do container:** {cor_hex}\n"
                f"**Label Entrar / Time A:** {l_entrar}\n"
                f"**Label Sair / Time B:** {l_sair}\n\n"
                f"-# Estas configurações só afetam o painel que é enviado nos canais."
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(label="Editar Aparência", style=disnake.ButtonStyle.blurple,
                          custom_id=f"ApostadoFF_FilaEditarAparencia_{tipo}", emoji=emoji.edit),
                ui.Button(label="Restaurar Padrão", style=disnake.ButtonStyle.grey,
                          custom_id=f"ApostadoFF_FilaResetarAparencia_{tipo}", emoji=emoji.reload),
            ),
            **_ck(),
        ),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id=f"ApostadoFF_GerenciarFila_{tipo}"),
        ),
    ]




# ─── Helper: barra de progresso ───────────────────────────────────────────────
def _progress_bar(current: int, total: int, width: int = 8) -> str:
    """Retorna uma barra de progresso visual. Ex: ●●●●○○○○"""
    if total <= 0:
        return "○" * width
    filled = round(current / total * width)
    return "●" * filled + "○" * (width - filled)


# ─── Embed/Container de Fila (publicado nos canais) ────────────────────────────
def get_fila_embed(tipo: str, valor: str, modo: str, jogadores: list,
                   fila_cfg: dict = None, msg_id: str = "MSGID"):
    """
    Retorna (embed_ou_None, components).
    tipo pode ser "1v1_mobile", "2x2_emulador", "3x3_ambos", etc.

    Componentes:
      - 1v1  → StringSelect  (Entrar Gelo Inf / Gelo Nor / Sair)   ← um único select
      - time → 3 botões      (Time A / Time B / Sair)
    Dispatcher em cog._handle_fila_botao detecta custom_id terminando em "_sel"
    e lê inter.values[0] como ação real.
    """
    fila_cfg  = fila_cfg or {}
    usar_v2   = _usar_v2()
    gelo_inf  = fila_cfg.get("gelo_infinito", True)
    gelo_nor  = fila_cfg.get("gelo_normal",  True)
    apar      = fila_cfg.get("aparencia", {})

    tamanho, plataforma = tipo.split("_", 1) if "_" in tipo else (tipo, "ambos")

    PLAT_EMOJI = {"mobile": emoji.mobile, "emulador": emoji.controller, "ambos": "🕹️"}
    PLAT_NOME  = {"mobile": "Mobile", "emulador": "Emulador", "ambos": "Mob + Emu"}
    TAM_NOME   = {"1v1": "1 × 1", "2x2": "2 × 2", "3x3": "3 × 3", "4x4": "4 × 4"}
    MODO_EMOJI = {"Clássico": emoji.sword, "Ranked": emoji.king, "Custom": "🎲"}

    plat_emoji = PLAT_EMOJI.get(plataforma, "🕹️")
    plat_nome  = PLAT_NOME.get(plataforma, plataforma.title())
    tamanho_n  = TAM_NOME.get(tamanho, tamanho.upper())
    modo_emoji = MODO_EMOJI.get(modo, emoji.sword)
    eh_solo    = tamanho == "1v1"
    n_slots    = {"1v1": 1, "2x2": 2, "3x3": 3, "4x4": 4}.get(tamanho, 1)
    mid        = str(msg_id)
    VAZIO      = "`○  aguardando...`"

    # ── Aparência personalizada ─────────────────────────────────────────────
    titulo_custom   = apar.get("titulo", "").strip()
    texto_extra     = apar.get("texto_extra", "").strip()
    label_entrar    = apar.get("label_entrar", "").strip()
    label_sair      = apar.get("label_sair", "").strip()
    cor_hex_custom  = apar.get("cor_hex", "").strip()

    # ── Seção de jogadores ──────────────────────────────────────────────────
    if eh_solo:
        j1 = jogadores[0] if len(jogadores) > 0 else None
        j2 = jogadores[1] if len(jogadores) > 1 else None

        def _jlinha(j, cor):
            if not j:
                return f"{cor} {VAZIO}"
            gel = f"  ╸  `{j['tipo_gel']}`" if j.get("tipo_gel") else ""
            return f"{cor} <@{j['id']}>{gel}"

        ocupados  = len(jogadores)
        bar       = _progress_bar(ocupados, 2)
        jogs_body = (
            f"{_jlinha(j1, emoji.blue)}\n"
            f"{_jlinha(j2, emoji.red)}\n\n"
            f"-# {bar}  `{ocupados} / 2`"
        )
    else:
        time_a    = [j for j in jogadores if j.get("time") == "A"]
        time_b    = [j for j in jogadores if j.get("time") == "B"]
        total     = len(time_a) + len(time_b)
        total_max = n_slots * 2

        def _slots(membros, n):
            linhas = []
            for i in range(n):
                if i < len(membros):
                    linhas.append(f"> `{i+1}.` <@{membros[i]['id']}>")
                else:
                    linhas.append(f"> `{i+1}.` {VAZIO}")
            return "\n".join(linhas)

        bar = _progress_bar(total, total_max)
        jogs_body = (
            f"{emoji.blue} **Time A** — `{len(time_a)}/{n_slots}`\n"
            f"{_slots(time_a, n_slots)}\n\n"
            f"{emoji.red} **Time B** — `{len(time_b)}/{n_slots}`\n"
            f"{_slots(time_b, n_slots)}\n\n"
            f"-# {bar}  `{total} / {total_max}`"
        )

    # ── Cálculo de valor para exibição ─────────────────────────────────────
    cfg_g   = db.get_document("apostadoff_config") or {}
    taxa    = float(cfg_g.get("taxa_servico", 1.80))
    valor_f = float(valor.replace(",", "."))
    por_jog = valor_f + taxa
    n_jogs  = n_slots * 2
    premio  = valor_f * n_jogs

    # ── Texto principal ─────────────────────────────────────────────────────
    titulo_display = titulo_custom if titulo_custom else f"## {emoji.sword}  Apostar — {tamanho_n}  {plat_emoji}"
    info_linha = (
        f"> **Fila de `R$ {valor}`**  ·  {modo_emoji} `{modo}`  ·  {plat_emoji} `{plat_nome}`\n"
        f"> -# Cada jogador paga `R$ {por_jog:.2f}` (aposta + R$ {taxa:.2f} taxa)  ·  Premiação `R$ {premio:.2f}`"
    )
    corpo = f"{titulo_display}\n{info_linha}\n\n{jogs_body}"
    if texto_extra:
        corpo += f"\n\n{texto_extra}"

    # ── Componentes ─────────────────────────────────────────────────────────
    if eh_solo:
        opcoes = []
        if gelo_inf:
            opcoes.append(disnake.SelectOption(
                label=f"{label_entrar or 'Entrar'}  ·  Gelo Infinito", value="gel_inf",
                emoji=emoji.ice, description="Entrar na fila usando Gelo Infinito"
            ))
        if gelo_nor:
            opcoes.append(disnake.SelectOption(
                label=f"{label_entrar or 'Entrar'}  ·  Gelo Normal", value="gel_nor",
                emoji=emoji.ice, description="Entrar na fila usando Gelo Normal"
            ))
        if not opcoes:
            opcoes.append(disnake.SelectOption(
                label=label_entrar or "Entrar na Fila", value="gel_nor",
                emoji=emoji.arrow, description="Entrar na fila"
            ))
        opcoes.append(disnake.SelectOption(
            label=label_sair or "Sair da Fila", value="sair",
            emoji=emoji.back, description="Remover-se desta fila"
        ))
        action_row = disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"AF_Q_{tipo}_{mid}_sel",
                placeholder="Escolha sua ação...",
                options=opcoes,
                min_values=1, max_values=1
            )
        )
    else:
        action_row = disnake.ui.ActionRow(
            disnake.ui.Button(
                label=label_entrar or "Time A", emoji=emoji.blue,
                style=disnake.ButtonStyle.primary,
                custom_id=f"AF_Q_{tipo}_{mid}_entrar_A"
            ),
            disnake.ui.Button(
                label=label_sair or "Time B", emoji=emoji.red,
                style=disnake.ButtonStyle.danger,
                custom_id=f"AF_Q_{tipo}_{mid}_entrar_B"
            ),
            disnake.ui.Button(
                label="Sair", emoji=emoji.back,
                style=disnake.ButtonStyle.secondary,
                custom_id=f"AF_Q_{tipo}_{mid}_sair"
            ),
        )

    if usar_v2:
        # Cor customizada ou fallback para cor global
        ck_fila = {}
        if cor_hex_custom:
            try:
                ck_fila["accent_colour"] = disnake.Colour(int(cor_hex_custom.replace("#", ""), 16))
            except ValueError:
                ck_fila = _ck()
        else:
            ck_fila = _ck()
        return None, [
            ui.Container(
                ui.TextDisplay(corpo),
                action_row,
                **ck_fila
            )
        ]
    else:
        embed_color = disnake.Color(0x2b2d31)
        if cor_hex_custom:
            try:
                embed_color = disnake.Color(int(cor_hex_custom.replace("#", ""), 16))
            except ValueError:
                pass
        embed = disnake.Embed(
            title=titulo_custom if titulo_custom else f"{emoji.sword}  Apostar — {tamanho_n}  {plat_emoji}",
            description=f"{info_linha}\n\n{jogs_body}" + (f"\n\n{texto_extra}" if texto_extra else ""),
            color=embed_color
        )
        return embed, [action_row]


# ─── Embed de Confirmação de Presença ──────────────────────────────────────────
def get_confirmacao_embed(tipo: str, valor: str, thread_id: str):
    nomes = {"1v1": "1 x 1", "2x2": "2 x 2", "4x4": "4 x 4"}
    usar_v2 = _usar_v2()

    desc = (
        f"**Formato: ``{nomes.get(tipo, tipo.upper())}``**\n"
        f"**Valor: ``R${valor}``**\n\n"
        "Confirme sua presença para iniciar a partida."
    )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Confirmar", emoji=emoji.correct,
                style=disnake.ButtonStyle.secondary,
                custom_id=f"AF_P_confirmar_{thread_id}",
            ),
            disnake.ui.Button(
                label="Recusar", emoji=emoji.wrong,
                style=disnake.ButtonStyle.secondary,
                custom_id=f"AF_P_recusar_{thread_id}",
            ),
        )
    ]

    if usar_v2:
        return None, [ui.Container(ui.TextDisplay(f"# {emoji.correct} Confirmação de Presença\n{desc}")), *components]
    else:
        embed = disnake.Embed(title="Confirmação de Presença", color=disnake.Color.red())
        embed.description = desc
        embed.set_footer(text="Confirme para jogar.")
        return embed, components


# ─── Painel Principal da Partida ────────────────────────────────────────────────
def get_partida_painel(tipo: str, valor: str, thread_id: str,
                       user1: str, user2: str, orientador: str,
                       pix_orientador: dict | None):
    nomes  = {"1v1": "1 x 1", "2x2": "2 x 2", "4x4": "4 x 4"}
    config = db.get_document("apostadoff_config") or {}
    taxa   = config.get("taxa_servico", 1.80)
    usar_v2 = config.get("usar_v2", False)

    valor_f        = float(valor.replace(",", "."))
    valor_com_taxa = f"{valor_f + taxa:.2f}".replace(".", ",")

    chave_pix = pix_orientador.get("Chave", "N/A") if pix_orientador else "N/A"
    tipo_pix  = pix_orientador.get("Type",  "N/A") if pix_orientador else "N/A"

    desc = (
        f"**Formato: ``{nomes.get(tipo, tipo.upper())}``**\n"
        f"**Valor: ``R${valor}``**\n"
        f"**Jogadores: <@{user1}>, <@{user2}>**\n"
        f"**Orientador: <@{orientador}>**\n\n"
        f"- **{emoji.pix}・PIX:\n```{chave_pix}```**\n"
        f"- **{emoji.receipt}・Tipo ``{tipo_pix}``**\n\n"
        f"**{emoji.dollar} Paguem o mediador!**\n"
        f"> Cada jogador deve pagar: `R$ {valor_com_taxa}` (R${valor} + taxa R${taxa:.2f})\n"
        f"> Após o pagamento, enviem o comprovante e marquem <@{orientador}>"
    )

    select = disnake.ui.StringSelect(
        custom_id=f"AF_P_acoes_{thread_id}",
        placeholder="Selecione a ação que deseja realizar.",
        options=[
            disnake.SelectOption(label="Painel de Chamada",  value="painelcall",
                                  emoji=emoji.headset, description="Gerencie calls de voz!"),
            disnake.SelectOption(label="Chamar Analista",    value="chamaranalista",
                                  emoji=emoji.search, description="Chame um analista para verificar hack!"),
            disnake.SelectOption(label="Definir Vencedor",   value="definirvencedor",
                                  emoji=emoji.king, description="Defina o vencedor da partida!"),
            disnake.SelectOption(label="Ver Anexo",          value="veranexo",
                                  emoji=emoji.image, description="Visualize o anexo da partida!"),
            disnake.SelectOption(label="Finalizar Partida",  value="finalizar",
                                  emoji=emoji.wrong, description="Deleta o tópico da partida!"),
        ]
    )
    action_row = disnake.ui.ActionRow(select)

    if usar_v2:
        return None, [ui.Container(ui.TextDisplay(f"# {emoji.controller} Bom jogo!\n{desc}")), action_row]
    else:
        embed = disnake.Embed(title=f"{emoji.controller} Bom jogo!", color=disnake.Color.red())
        embed.description = desc
        return embed, [action_row]


# ─── Painel de Chamada de Voz ──────────────────────────────────────────────────
def get_painel_chamada(thread_id: str, tem_call: bool):
    usar_v2 = _usar_v2()
    desc = "Gerencie o canal de voz da partida."
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Call", emoji=emoji.plus,
                               style=disnake.ButtonStyle.secondary,
                               custom_id=f"AF_P_criarcall_{thread_id}",
                               disabled=tem_call),
            disnake.ui.Button(label="Deletar Call", emoji=emoji.delete,
                               style=disnake.ButtonStyle.danger,
                               custom_id=f"AF_P_deletarcall_{thread_id}",
                               disabled=not tem_call),
        )
    ]
    if usar_v2:
        return None, [ui.Container(ui.TextDisplay(f"# {emoji.headset} Painel de Chamada\n{desc}")), *components]
    else:
        embed = disnake.Embed(title=f"{emoji.headset} Painel de Chamada", description=desc, color=disnake.Color.blurple())
        return embed, components


# ─── Selects de vencedor / pontuação ──────────────────────────────────────────
def get_vencedor_select(thread_id: str) -> list:
    return [
        disnake.ui.ActionRow(
            disnake.ui.UserSelectMenu(
                custom_id=f"AF_P_setvencedor_{thread_id}",
                placeholder="Escolha o vencedor!",
                min_values=1, max_values=1
            )
        )
    ]


def get_pontuacao_select(thread_id: str) -> list:
    emojis_num = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    opts = [
        disnake.SelectOption(
            label=f"Dar {p} Ponto{'s' if p > 1 else ''}!",
            value=str(p), emoji=emojis_num[p - 1]
        )
        for p in range(1, 11)
    ]
    return [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"AF_P_setpontos_{thread_id}",
                placeholder="Seleciona a pontuação!",
                max_values=1, options=opts
            )
        )
    ]


# ─── Painel de Ranking ─────────────────────────────────────────────────────────
def get_painel_ranking(stats: dict, admin: bool = False) -> list:
    """
    stats: dict {user_id: {"vitorias": int, "derrotas": int, "pontos": int, "partidas": int}}
    admin: se True, exibe botões de admin (Enviar no canal, Voltar)
    """
    medals  = ["🥇", "🥈", "🥉"]
    ranking = sorted(stats.items(), key=lambda x: (x[1].get("vitorias", 0), x[1].get("pontos", 0)), reverse=True)

    if not ranking:
        corpo = "> *Nenhuma partida registrada ainda.*"
    else:
        linhas = []
        for i, (uid, data) in enumerate(ranking[:10]):
            medal = medals[i] if i < 3 else f"`{i+1}°`"
            v  = data.get("vitorias", 0)
            d  = data.get("derrotas", 0)
            pt = data.get("pontos", 0)
            linhas.append(f"{medal} <@{uid}> — **{v}V** / {d}D · `{pt} pts`")
        corpo = "\n".join(linhas)

    botoes_admin = []
    if admin:
        botoes_admin = [
            ui.ActionRow(
                ui.Button(label="Atualizar", style=disnake.ButtonStyle.blurple,
                          emoji=emoji.reload, custom_id="ApostadoFF_RankingAtualizar"),
                ui.Button(label="Enviar no Canal", style=disnake.ButtonStyle.green,
                          emoji=emoji.arrow2, custom_id="ApostadoFF_RankingEnviar"),
                ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                          emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
            )
        ]
    else:
        botoes_admin = [
            ui.ActionRow(
                ui.Button(label="Atualizar", style=disnake.ButtonStyle.blurple,
                          emoji=emoji.reload, custom_id="ApostadoFF_RankingAtualizar"),
            )
        ]

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.king} Ranking de Partidas\n"
                "-# Top 10 jogadores com mais vitórias"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(corpo),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            **_ck(),
        ),
        *botoes_admin,
    ]


# ─── Painel de Perfil do Usuário ───────────────────────────────────────────────
def _build_perfil_desc(member: disnake.Member, data: dict) -> tuple[str, str]:
    """Retorna (desc, emblema) para reutilização nos painéis de perfil."""
    v  = data.get("vitorias", 0)
    d  = data.get("derrotas", 0)
    pt = data.get("pontos", 0)
    pm = data.get("partidas", 0)
    taxa = f"{(v / pm * 100):.1f}%" if pm > 0 else "0%"

    if v >= 50:   emblema = "💎 Lendário"
    elif v >= 25: emblema = "🔱 Diamante"
    elif v >= 10: emblema = "🏅 Ouro"
    elif v >= 5:  emblema = "🥈 Prata"
    elif v >= 1:  emblema = "🥉 Bronze"
    else:         emblema = "🪨 Iniciante"

    desc = (
        f"**Usuário:** {member.mention}\n"
        f"**Emblema:** {emblema}\n\n"
        f"> {emoji.controller} **Partidas jogadas:** `{pm}`\n"
        f"> {emoji.king} **Vitórias:** `{v}`\n"
        f"> {emoji.wrong} **Derrotas:** `{d}`\n"
        f"-# {emoji.arrow} **Pontos totais:** `{pt}`\n"
        f"-# {emoji.arrow} **Taxa de vitória:** `{taxa}`"
    )
    return desc, emblema

def get_painel_perfil(member: disnake.Member, data: dict) -> list:
    """
    data: {"vitorias": int, "derrotas": int, "pontos": int, "partidas": int}
    Exibe perfil com botão para abrir a carteira de coins.
    """
    desc, _ = _build_perfil_desc(member, data)

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.member} Perfil — {member.display_name}\n"
                f"-# ApostadoFF · Estatísticas do jogador"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(desc),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(
                    label="Carteira",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.dollar,
                    custom_id=f"ApostadoFF_VerCarteira:{member.id}",
                ),
            ),
            **_ck(),
        )
    ]


def get_painel_carteira_inline(member: disnake.Member, dados: dict, cfg: dict, data_perfil: dict) -> list:
    """
    Exibe a carteira de coins com botão para voltar ao perfil.
    Usado quando o usuário clica no botão 'Carteira' dentro do perfil.
    """
    emj  = cfg.get("emoji_moeda", "🪙")
    nome = cfg.get("nome_moeda", "Coin")

    saldo       = dados.get("saldo",       0)
    total_ganho = dados.get("total_ganho", 0)
    total_gasto = dados.get("total_gasto", 0)
    aps         = dados.get("aps",         0)
    analises    = dados.get("analises",    0)

    desc_perfil, _ = _build_perfil_desc(member, data_perfil)

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.member} Perfil — {member.display_name}\n"
                f"-# ApostadoFF · Estatísticas do jogador"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(desc_perfil),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(
                f"## {emj} Carteira\n"
                f" {emoji.dollar}**Saldo atual:** {emj} `{saldo} {nome}s`\n\n"
                f"> {emoji.arrow} **Total ganho:** `{total_ganho}`\n"
                f"> {emoji.arrow} **Total gasto:** `{total_gasto}`\n"
                f"> {emoji.arrow}  **APs mediados:** `{aps}`\n"
                f"> {emoji.arrow} **Análises feitas:** `{analises}`"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(
                    label="Fechar Carteira",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id=f"ApostadoFF_FecharCarteira:{member.id}",
                ),
            ),
            **_ck(),
        )
    ]

# ══════════════════════════════════════════════════════════════════════════════
# ─── NOVOS PAINÉIS: COINS / CARGO UP / ANALISTAS / CARTEIRA ──────────────────
# ══════════════════════════════════════════════════════════════════════════════


# ─── Modals auxiliares ────────────────────────────────────────────────────────
class CriarFilaModal(disnake.ui.Modal):
    """Modal para criar uma fila personalizada de forma dinâmica."""
    def __init__(self):
        super().__init__(
            title="Criar Fila Personalizada",
            custom_id="ApostadoFF_CriarFilaModal",
            components=[
                disnake.ui.TextInput(
                    label="Valor por jogador (R$)", custom_id="valor",
                    placeholder="Ex: 25,00",
                    style=disnake.TextInputStyle.short, max_length=10, required=True,
                ),
                disnake.ui.TextInput(
                    label="Formato", custom_id="formato",
                    placeholder="1v1  |  2x2  |  3x3  |  4x4",
                    style=disnake.TextInputStyle.short, max_length=5, required=True, value="1v1",
                ),
                disnake.ui.TextInput(
                    label="Plataforma", custom_id="plataforma",
                    placeholder="mobile  |  emulador  |  ambos",
                    style=disnake.TextInputStyle.short, max_length=10, required=True, value="ambos",
                ),
                disnake.ui.TextInput(
                    label="Modo", custom_id="modo",
                    placeholder="Clássico  |  Ranked  |  Custom",
                    style=disnake.TextInputStyle.short, max_length=10, required=False, value="Clássico",
                ),
            ],
        )


class CoinsSetModal(disnake.ui.Modal):
    """Admin: definir saldo de coins de um usuário manualmente."""
    def __init__(self, user_id: str, saldo_atual: int):
        self.user_id = user_id
        super().__init__(
            title="Definir Coins do Usuário",
            custom_id=f"ApostadoFF_CoinsSetModal:{user_id}",
            components=[
                disnake.ui.TextInput(
                    label="Novo saldo", custom_id="saldo",
                    placeholder="Ex: 500",
                    style=disnake.TextInputStyle.short, max_length=10, required=True,
                    value=str(saldo_atual),
                ),
            ],
        )


# ─── Painel: Coins — Config (admin) ──────────────────────────────────────────
def get_painel_coins_config(cfg: dict) -> list:
    nome = cfg.get("nome_moeda", "Coin")
    emj  = cfg.get("emoji_moeda", "🪙")
    mult = cfg.get("multiplicador", 1.0)

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > ApostadoFF > **Coins**"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(
                f"**Moeda:** {emj} `{nome}`\n\n"
                f"**Multiplicador global:** `×{mult:.1f}`\n"
                f"-# Coins por AP e análise são configurados em cada painel respectivo."
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(label="Editar Configurações", style=disnake.ButtonStyle.blurple,
                          emoji=emoji.edit, custom_id="ApostadoFF_CoinsEditar"),
                ui.Button(label="Ranking Coins", style=disnake.ButtonStyle.grey,
                          custom_id="ApostadoFF_CoinsRanking", emoji=emoji.king),
            ),
            **_ck(),
        ),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
        ),
    ]


class CoinsEditModal(disnake.ui.Modal):
    def __init__(self, cfg: dict):
        super().__init__(
            title="Editar Config de Coins",
            custom_id="ApostadoFF_CoinsEditModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome da moeda", custom_id="nome_moeda",
                    style=disnake.TextInputStyle.short, max_length=20,
                    required=True, value=cfg.get("nome_moeda", "Coin"),
                ),
                disnake.ui.TextInput(
                    label="Emoji da moeda", custom_id="emoji_moeda",
                    style=disnake.TextInputStyle.short, max_length=10,
                    required=True, value=cfg.get("emoji_moeda", "🪙"),
                ),
                disnake.ui.TextInput(
                    label="Multiplicador global (ex: 1.5)", custom_id="multiplicador",
                    style=disnake.TextInputStyle.short, max_length=5,
                    required=True, value=str(cfg.get("multiplicador", 1.0)),
                ),
            ],
        )


# ─── Painel: Carteira do usuário ──────────────────────────────────────────────
def get_painel_carteira(member: disnake.Member, dados: dict, cfg: dict) -> list:
    emj  = cfg.get("emoji_moeda", "🪙")
    nome = cfg.get("nome_moeda", "Coin")

    saldo       = dados.get("saldo",       0)
    total_ganho = dados.get("total_ganho", 0)
    total_gasto = dados.get("total_gasto", 0)
    aps         = dados.get("aps",         0)
    analises    = dados.get("analises",    0)

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emj} Carteira — {member.display_name}\n"
                f"-# ApostadoFF · Coins"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(
                f"**Saldo atual:** {emj} `{saldo} {nome}s`\n\n"
                f"┌ {emoji.chart} **Total ganho:** `{total_ganho}`\n"
                f"├ {emoji.minus} **Total gasto:** `{total_gasto}`\n"
                f"├ {emoji.role}  **APs mediados:** `{aps}`\n"
                f"└ {emoji.search} **Análises feitas:** `{analises}`"
            ),
            **_ck(),
        ),
    ]


# ─── Painel: Ranking de Coins ─────────────────────────────────────────────────
def get_painel_coins_ranking(ranking: list, cfg: dict, admin: bool = False) -> list:
    emj  = cfg.get("emoji_moeda", "🪙")
    nome = cfg.get("nome_moeda", "Coin")
    medals = ["🥇", "🥈", "🥉"]

    if not ranking:
        corpo = "> *Nenhuma atividade registrada ainda.*"
    else:
        linhas = []
        for i, (uid, d) in enumerate(ranking[:10]):
            medal = medals[i] if i < 3 else f"`{i+1}°`"
            linhas.append(
                f"{medal} <@{uid}> — {emj} `{d.get('saldo',0)}` saldo  "
                f"·  `{d.get('total_ganho',0)} ganhos`  "
                f"·  `{d.get('aps',0)} APs`"
            )
        corpo = "\n".join(linhas)

    botoes = [
        ui.Button(label="Atualizar", style=disnake.ButtonStyle.blurple,
                  emoji=emoji.reload, custom_id="ApostadoFF_CoinsRanking"),
    ]
    if admin:
        botoes.append(ui.Button(label="Definir Coins (user)", style=disnake.ButtonStyle.grey,
                                emoji=emoji.edit, custom_id="ApostadoFF_CoinsSetUser"))

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emj} Ranking de {nome}s\n"
                f"-# Top 10 por saldo atual"
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(corpo),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            **_ck(),
        ),
        ui.ActionRow(*botoes),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_CoinsConfig"),
        ),
    ]


# ─── Painel: Analistas em serviço (público) ───────────────────────────────────
def get_painel_analistas(analistas: list) -> list:
    if analistas:
        texto = "\n".join(f"> **`{i+1}°`** | <@{uid}>" for i, uid in enumerate(analistas))
    else:
        texto = "> Nenhum analista em serviço."

    return [
        ui.Container(
            ui.TextDisplay(
                f"# {emoji.search} Painel de Analistas\n"
                "-# Entre em serviço para analisar partidas suspeitas."
            ),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.TextDisplay(f"**Analistas em serviço ({len(analistas)}):**\n{texto}"),
            ui.Separator(spacing=disnake.SeparatorSpacing.small),
            ui.ActionRow(
                ui.Button(label="Entrar em serviço", style=disnake.ButtonStyle.secondary,
                          emoji=emoji.search, custom_id="ApostadoFF_EntrarFilaAnalista"),
                ui.Button(label="Sair de serviço", style=disnake.ButtonStyle.secondary,
                          emoji=emoji.wrong, custom_id="ApostadoFF_SairFilaAnalista"),
            ),
            **_ck(),
        ),
    ]


# ─── Painel: Config Analistas Admin (completo) ────────────────────────────────
def get_painel_config_analistas(config: dict, guild: disnake.Guild, coins_cfg: dict) -> list:
    canal_id      = config.get("canal_analistas")
    cargo_id      = config.get("cargo_analista")
    canal_txt     = f"<#{canal_id}>"  if canal_id  else "`Não configurado`"
    cargo_txt     = f"<@&{cargo_id}>" if cargo_id  else "`Não configurado`"
    coins_por_ana = coins_cfg.get("coins_por_ap_analista", 5)
    emj           = coins_cfg.get("emoji_moeda", "🪙")
    nome_coin     = coins_cfg.get("nome_moeda", "Coin")

    canal_opts = [
        disnake.SelectOption(label=f"#{c.name[:97]}", value=str(c.id),
                             default=(str(c.id) == str(canal_id)))
        for c in guild.text_channels[:25]
    ]
    cargo_opts = [
        disnake.SelectOption(label=r.name[:100], value=str(r.id),
                             default=(str(r.id) == str(cargo_id)))
        for r in reversed([r for r in guild.roles if r.name != "@everyone"][-24:])
    ]

    rows = [
        ui.TextDisplay(
            f"# {emoji.search} Analistas\n"
            "-# Painel > ApostadoFF > **Analistas**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            f"**Canal dos Analistas:** {canal_txt}\n"
            f"**Cargo de Analista:** {cargo_txt}\n"
            f"**{emj} Coins por análise:** `{coins_por_ana} {nome_coin}`\n\n"
            f"-# Analistas são chamados pelo mediador durante uma partida para verificar hacks."
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]
    if canal_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelectCanalAnalistas",
            placeholder="Selecione o canal dos analistas...", options=canal_opts
        )))
    if cargo_opts:
        rows.append(ui.ActionRow(ui.StringSelect(
            custom_id="ApostadoFF_SelectCargoAnalista",
            placeholder="Selecione o cargo de analista...", options=cargo_opts
        )))

    action_btns = []
    if canal_id:
        action_btns.append(
            ui.Button(label="Enviar Painel de Analistas", style=disnake.ButtonStyle.green,
                      emoji=emoji.arrow2, custom_id="ApostadoFF_EnviarPainelAnalistas")
        )
    action_btns += [
        ui.Button(label="Editar Coins por Análise", style=disnake.ButtonStyle.blurple,
                  emoji=emoji.edit, custom_id="ApostadoFF_AnaEditarCoins"),
        ui.Button(label="Cargo UPs Analista", style=disnake.ButtonStyle.grey,
                  emoji=emoji.role, custom_id="ApostadoFF_AnaCargoUps"),
    ]
    rows.append(ui.ActionRow(*action_btns))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelPrincipal"),
        ),
    ]


# ─── Modal: Editar coins por análise do analista ──────────────────────────────
class AnaCoinsModal(disnake.ui.Modal):
    def __init__(self, valor_atual: int):
        super().__init__(
            title="Coins por Análise — Analista",
            custom_id="ApostadoFF_AnaCoinsModal",
            components=[
                disnake.ui.TextInput(
                    label="Coins por análise feita", custom_id="valor",
                    placeholder="Ex: 5",
                    style=disnake.TextInputStyle.short, max_length=6, required=True,
                    value=str(valor_atual),
                ),
            ],
        )


# ─── Painel: Cargo UPs do Analista ────────────────────────────────────────────
def get_painel_ana_cargo_ups(coins_cfg: dict) -> list:
    ups  = coins_cfg.get("cargo_ups_analista", [])
    emj  = coins_cfg.get("emoji_moeda", "🪙")
    nome = coins_cfg.get("nome_moeda", "Coin")

    if ups:
        linhas = []
        for i, up in enumerate(ups):
            reqs = []
            if up.get("min_coins_total", 0): reqs.append(f"`{up['min_coins_total']} {nome} ganhos`")
            if up.get("min_analises",    0): reqs.append(f"`{up['min_analises']} análises`")
            req_txt = "  ·  ".join(reqs) if reqs else "`sem requisitos`"
            linhas.append(
                f"**`{i+1}.`** <@&{up['cargo_id']}> — **{up.get('nome_rank','?')}**\n"
                f"-# {req_txt}"
            )
        corpo = "\n\n".join(linhas)
    else:
        corpo = "> Nenhum Cargo UP configurado para analistas."

    botoes_ups = []
    for i in range(min(len(ups), 5)):
        botoes_ups.append(ui.Button(
            label=f"Editar #{i+1}", style=disnake.ButtonStyle.grey,
            custom_id=f"ApostadoFF_AnaCargoUpEditar_{i}"
        ))

    rows = [
        ui.TextDisplay(
            f"# {emoji.role} Cargo UPs — Analista\n"
            f"-# Painel > ApostadoFF > Analistas > **Cargo UPs**"
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(
            "Cargos concedidos automaticamente ao analista ao atingir requisitos.\n"
            "Requisitos avaliados ao fim de cada análise feita."
        ),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.TextDisplay(corpo),
        ui.Separator(spacing=disnake.SeparatorSpacing.small),
        ui.ActionRow(
            ui.Button(label="Adicionar Cargo UP", style=disnake.ButtonStyle.green,
                      custom_id="ApostadoFF_AnaCargoUpAdicionar", emoji=emoji.plus),
            *(botoes_ups),
        ),
    ]
    if ups:
        rows.append(ui.ActionRow(
            ui.Button(label="Remover último", style=disnake.ButtonStyle.red,
                      custom_id="ApostadoFF_AnaCargoUpRemover", emoji=emoji.delete),
        ))

    return [
        ui.Container(*rows, **_ck()),
        ui.ActionRow(
            ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                      emoji=emoji.back, custom_id="ApostadoFF_PainelAnalistasAdmin"),
        ),
    ]


# ─── Modal: Cargo UP de Analista ─────────────────────────────────────────────
class AnaCargoUpModal(disnake.ui.Modal):
    def __init__(self, idx: int = -1, up: dict = None):
        up = up or {}
        self.idx = idx
        super().__init__(
            title="Cargo UP — Analista",
            custom_id=f"ApostadoFF_AnaCargoUpModal:{idx}",
            components=[
                disnake.ui.TextInput(
                    label="ID do Cargo", custom_id="cargo_id",
                    placeholder="ID numérico do cargo Discord",
                    style=disnake.TextInputStyle.short, max_length=25, required=True,
                    value=str(up.get("cargo_id", "")),
                ),
                disnake.ui.TextInput(
                    label="Nome do Rank", custom_id="nome_rank",
                    placeholder="Ex: Analista Ouro",
                    style=disnake.TextInputStyle.short, max_length=40, required=True,
                    value=up.get("nome_rank", ""),
                ),
                disnake.ui.TextInput(
                    label="Coins totais ganhos (mínimo, 0=ignorar)", custom_id="min_coins_total",
                    placeholder="Ex: 50",
                    style=disnake.TextInputStyle.short, max_length=10, required=False,
                    value=str(up.get("min_coins_total", 0)),
                ),
                disnake.ui.TextInput(
                    label="Análises feitas (mínimo, 0=ignorar)", custom_id="min_analises",
                    placeholder="Ex: 5",
                    style=disnake.TextInputStyle.short, max_length=10, required=False,
                    value=str(up.get("min_analises", 0)),
                ),
            ],
        )



# ─── Painel: Analista chamado na partida ──────────────────────────────────────
def get_painel_analise(thread_id: str, partida: dict) -> tuple:
    """
    Painel enviado no tópico da partida quando o mediador chama um analista.
    Retorna (embed_ou_None, components).
    """
    usar_v2 = _usar_v2()
    tipo    = partida.get("tipo", "?")
    valor   = partida.get("valor", "?")
    u1      = partida.get("user1", "?")
    u2      = partida.get("user2", "?")

    corpo = (
        f"## {emoji.search} Análise Solicitada\n"
        f"> **Partida:** `{tipo.upper()}`  ·  Valor `R$ {valor}`\n"
        f"> **Jogadores:** <@{u1}> vs <@{u2}>\n\n"
        f"O analista deve observar o jogo e emitir o veredicto abaixo."
    )
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Limpo", style=disnake.ButtonStyle.green,
                              emoji=emoji.correct,
                              custom_id=f"AF_ANA_{thread_id}_limpo"),
            disnake.ui.Button(label="Suspeito de Hack", style=disnake.ButtonStyle.danger,
                              emoji=emoji.flag,
                              custom_id=f"AF_ANA_{thread_id}_hack"),
            disnake.ui.Button(label="Inconclusivo", style=disnake.ButtonStyle.secondary,
                              custom_id=f"AF_ANA_{thread_id}_inconclusivo"),
        )
    ]
    if usar_v2:
        return None, [ui.Container(ui.TextDisplay(corpo), **_ck()), *components]
    else:
        embed = disnake.Embed(title=f"{emoji.search} Análise Solicitada", description=corpo,
                              color=disnake.Color.orange())
        return embed, components


# ─── Painel: Criar Fila (estático, postado no canal pelo admin) ───────────────
def get_painel_criar_fila() -> list:
    usar_v2 = _usar_v2()
    corpo = (
        f"## {emoji.sword}  Criar Fila Personalizada\n"
        "> Clique no botão abaixo para criar uma fila com o valor e formato que preferir.\n"
        "> A fila ficará ativa até ser preenchida ou você sair dela."
    )
    row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Criar Fila", style=disnake.ButtonStyle.green,
                          emoji=emoji.plus, custom_id="ApostadoFF_AbrirCriarFila"),
    )
    if usar_v2:
        return [ui.Container(ui.TextDisplay(corpo), row, **_ck())]
    else:
        embed = disnake.Embed(
            title=f"{emoji.sword} Criar Fila Personalizada",
            description=corpo, color=disnake.Color(0x2b2d31)
        )
        return embed, [row]