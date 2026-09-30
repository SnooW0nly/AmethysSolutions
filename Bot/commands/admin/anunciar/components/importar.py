import re
import json
import disnake
import aiohttp
from disnake.ext import commands
from typing import Any

from functions.database import database
from functions.message import message
from functions.emoji import emoji
from functions.utils import utils
from ..anunciar import Anunciar

_LINK_RE = re.compile(
    r"https?://(?:builder\.amethys\.solutions|amethys\.solutions|amethysapplications\.com\.br|amethysapp\.vercel\.app)(?:/builder)?/s/([a-f0-9]{24})",
    re.IGNORECASE,
)

# Tipos da API do Discord
_T_ACTION_ROW    = 1
_T_BUTTON        = 2
_T_STRING_SELECT = 3
_T_TEXT_DISPLAY  = 10
_T_MEDIA_GALLERY = 12
_T_SEPARATOR     = 14
_T_CONTAINER     = 17

# Mapeamento de style numérico → string usada internamente
_BTN_STYLE_MAP = {1: "blue", 2: "gray", 3: "green", 4: "red", 5: "url"}


def _emoji_str_from_dapi(emoji_data: dict | None) -> str | None:
    """Converte objeto emoji da API do Discord em string unicode ou <:nome:id>."""
    if not emoji_data:
        return None
    eid  = emoji_data.get("id")
    name = emoji_data.get("name") or ""
    if eid:
        return f"<:{name}:{eid}>"
    return name or None


def _extract_action_row(comp: dict, buttons: list, selects: list) -> None:
    """
    Processa um ActionRow e adiciona seus filhos nas listas corretas.
    Retorna True se o row continha botões ou selects (não deve ir pro container).
    """
    inner = comp.get("components") or []
    for ic in inner:
        it = ic.get("type")

        if it == _T_BUTTON:
            style_num = ic.get("style", 2)
            style_str = _BTN_STYLE_MAP.get(style_num, "gray")
            url       = ic.get("url") or None
            label     = ic.get("label") or ""
            emoji_raw = _emoji_str_from_dapi(ic.get("emoji"))
            disabled  = bool(ic.get("disabled", False))

            if style_num == 5 and url:
                btn_type = "url"
            else:
                # Botões importados sem ação configurada começam como disabled
                btn_type = "disabled"

            buttons.append({
                "id": utils.gerar_id(),
                "label": label,
                "button": {
                    "type": btn_type,
                    "style": style_str,
                    "emoji": emoji_raw,
                    "url": url if btn_type == "url" else None,
                    "disabled": btn_type == "disabled",
                    "custom_id": ic.get("custom_id") or None,
                    "action": {},
                },
            })

        elif it == _T_STRING_SELECT:
            options_data = ic.get("options") or []
            options = []
            for o in options_data:
                opt_emoji = _emoji_str_from_dapi(o.get("emoji"))
                options.append({
                    "id": utils.gerar_id(),
                    "label": o.get("label") or "Opção",
                    "description": o.get("description") or None,
                    "emoji": opt_emoji,
                    "action": {"type": "disabled"},
                })

            min_v = max(1, min(len(options) or 1, int(ic.get("min_values") or 1)))
            max_v = max(min_v, min(len(options) or 1, int(ic.get("max_values") or 1)))

            selects.append({
                "id": utils.gerar_id(),
                "placeholder": ic.get("placeholder") or None,
                "min_values": min_v,
                "max_values": max_v,
                "options": options,
            })


def _extract_components(components_list: list[dict]) -> dict[str, Any]:
    """
    Percorre a lista de componentes no formato JSON da API do Discord e
    separa cada parte nos campos corretos:

      - container_parts : lista de componentes que ficam no campo "container"
                          (TextDisplay, Separator, MediaGallery, Container aninhado
                           — MAS sem os ActionRows de botões/selects)
      - buttons         : lista de botões no formato interno do bot
      - selects         : lista de selects no formato interno do bot
      - external_image  : URL da primeira MediaGallery encontrada no nível raiz
                          (fora de Container)

    Retorna um dict com essas chaves.
    """
    container_parts: list[dict] = []
    buttons: list[dict]         = []
    selects: list[dict]         = []
    external_image: str | None  = None

    for comp in components_list:
        t = comp.get("type")

        # ── ActionRow no nível raiz — pode conter botões ou select ───────────
        if t == _T_ACTION_ROW:
            _extract_action_row(comp, buttons, selects)
            # ActionRows com botões/selects NÃO vão pro container
            continue

        # ── MediaGallery no nível raiz → externalImage ────────────────────────
        if t == _T_MEDIA_GALLERY:
            items = comp.get("items") or []
            if items:
                url = (items[0].get("media") or {}).get("url") or None
                if url and external_image is None:
                    external_image = url
            # Não adiciona ao container_parts
            continue

        # ── Container aninhado — precisa separar botões/selects internos ──────
        if t == _T_CONTAINER:
            inner_comps = comp.get("components") or []
            clean_inner: list[dict] = []

            for ic in inner_comps:
                it = ic.get("type")
                if it == _T_ACTION_ROW:
                    # Extrai botões/selects do ActionRow interno
                    _extract_action_row(ic, buttons, selects)
                    # Não inclui o ActionRow no container limpo
                elif it == _T_MEDIA_GALLERY:
                    # MediaGallery dentro de container fica no container
                    clean_inner.append(ic)
                else:
                    clean_inner.append(ic)

            # Só adiciona o container se sobrou conteúdo depois de remover os ActionRows
            if clean_inner:
                clean_container = dict(comp)
                clean_container["components"] = clean_inner
                container_parts.append(clean_container)
            continue

        # ── TextDisplay e Separator vão pro container ─────────────────────────
        if t in (_T_TEXT_DISPLAY, _T_SEPARATOR):
            container_parts.append(comp)
            continue

        # Tipos desconhecidos são ignorados silenciosamente

    return {
        "container_parts": container_parts,
        "buttons":         buttons,
        "selects":         selects,
        "external_image":  external_image,
    }


class Importar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class ImportarModal(disnake.ui.Modal):
        def __init__(self):
            super().__init__(
                title="Importar do Amethys Builder",
                custom_id="Anunciar_ImportarModal",
                components=[
                    disnake.ui.TextInput(
                        label="Link do Builder",
                        custom_id="link",
                        placeholder="https://builder.amethys.solutions/s/...",
                        required=True,
                        style=disnake.TextInputStyle.short,
                        max_length=200,
                    )
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            link = inter.text_values.get("link", "").strip()

            match = _LINK_RE.search(link)
            if not match:
                await inter.response.send_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{emoji.wrong} **Link inválido.**\n"
                                "-# O link deve ser do formato "
                                "`https://builder.amethys.solutions/s/<id>`"
                            )
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    ephemeral=True,
                )
                return

            snippet_id = match.group(1)

            # Prioriza o novo domínio; mantém fallback para os domínios legados
            if "amethys.solutions" in link:
                api_url = f"https://amethys.solutions/api/builder/{snippet_id}"
            elif "vercel.app" in link:
                api_url = f"https://amethysapp.vercel.app/api/builder/{snippet_id}"
            else:
                api_url = f"https://amethysapplications.com.br/api/builder/{snippet_id}"

            await message.wait(inter, send=False)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_url,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 404:
                            await inter.edit_original_message(
                                components=[
                                    disnake.ui.Container(
                                        disnake.ui.TextDisplay(
                                            f"{emoji.wrong} **Link não encontrado ou expirado.**\n"
                                            "-# Links do Builder expiram em 7 dias."
                                        )
                                    ),
                                    disnake.ui.ActionRow(
                                        disnake.ui.Button(
                                            label="Voltar",
                                            emoji=emoji.back,
                                            custom_id="Anunciar_PainelInicial",
                                        )
                                    ),
                                ]
                            )
                            return

                        if not resp.ok:
                            raise ValueError(f"HTTP {resp.status}")

                        data = await resp.json()
            except Exception as e:
                await inter.edit_original_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{emoji.wrong} **Erro ao buscar o link.**\n"
                                f"-# `{e}`"
                            )
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="Voltar",
                                emoji=emoji.back,
                                custom_id="Anunciar_PainelInicial",
                            )
                        ),
                    ]
                )
                return

            raw_json = data.get("json", "")
            try:
                components_list = json.loads(raw_json)
                if not isinstance(components_list, list):
                    raise ValueError("JSON deve ser uma lista de componentes")
            except Exception as e:
                await inter.edit_original_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{emoji.wrong} **JSON inválido no link.**\n"
                                f"-# `{e}`"
                            )
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="Voltar",
                                emoji=emoji.back,
                                custom_id="Anunciar_PainelInicial",
                            )
                        ),
                    ]
                )
                return

            # ── Extrair e separar os componentes ─────────────────────────────
            extracted = _extract_components(components_list)

            container_parts = extracted["container_parts"]
            buttons         = extracted["buttons"]
            selects         = extracted["selects"]
            external_image  = extracted["external_image"]

            # Limita botões a 5 (limite do Discord)
            buttons = buttons[:5]
            # Limita selects a 3
            selects = selects[:3]

            # Container só vai pro banco se tiver conteúdo
            container_json = json.dumps(container_parts, ensure_ascii=False) if container_parts else None

            # ── Salvar no banco ───────────────────────────────────────────────
            db = database.get_document("messages_anunciar")
            db["message"]["container"]     = container_json
            db["message"]["content"]       = None
            db["message"]["externalImage"] = external_image
            db["message"]["buttons"]       = buttons
            db["message"]["selects"]       = selects
            for key in db["message"]["embed"]:
                db["message"]["embed"][key] = None
            database.save_document("messages_anunciar", {}, db)

            await inter.edit_original_message(components=Anunciar.create_buttons())

            # Resumo do que foi importado
            parts = []
            if container_parts:
                parts.append(f"`{len(container_parts)}` componente(s) de conteúdo")
            if buttons:
                parts.append(f"`{len(buttons)}` botão(ões) — **configure as ações no painel**")
            if selects:
                parts.append(f"`{len(selects)}` select(s) — **configure as ações no painel**")
            if external_image:
                parts.append("imagem externa")

            resumo = "\n".join(f"• {p}" for p in parts) if parts else "Nenhum conteúdo identificado."
            await message.success(
                inter,
                f"Importado com sucesso!\n{resumo}",
                followup=True,
            )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_ImportarDoSite":
            await inter.response.send_modal(self.ImportarModal())


def setup(bot: commands.Bot):
    bot.add_cog(Importar(bot))