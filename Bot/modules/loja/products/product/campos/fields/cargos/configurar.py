import disnake

from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.loja_products import container_kwargs_for_product, embed_kwargs_for_product


def _ensure_field_roles_structure(field: dict) -> dict:
    cargos = field.get("cargos") or {}
    if not isinstance(cargos, dict):
        cargos = {}
    cargos.setdefault("adicionar", [])
    cargos.setdefault("remover", [])
    cargos.setdefault("proibidos", [])
    field["cargos"] = cargos
    return field


def _role_defaults(guild: disnake.Guild, role_ids: list[int]) -> list[disnake.SelectDefaultValue]:
    defaults: list[disnake.SelectDefaultValue] = []
    if not guild:
        return defaults
    for rid in (role_ids or []):
        try:
            role = guild.get_role(int(rid))
            if role is None:
                continue
            defaults.append(disnake.SelectDefaultValue(id=role.id, type=disnake.SelectDefaultValueType.role))
        except Exception:
            continue
    return defaults


class ConfigurarCargosCampo:
    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return ConfigurarCargosCampo._panel_embed(inter, product_id, field_id)
        return ConfigurarCargosCampo._panel_components(inter, product_id, field_id)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        products = db.get_document("loja_products")
        product = (products or {}).get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id)
        if not field:
            from ..configurar import ConfigurarCampo
            return ConfigurarCampo.panel(inter, product_id, field_id)

        field = _ensure_field_roles_structure(field)
        cargos = field.get("cargos", {})

        duracao_minutos = cargos.get("duracao_minutos")
        duracao_texto = f"{duracao_minutos} minutos" if duracao_minutos else "Permanente"

        add_defaults = _role_defaults(inter.guild, [int(x) for x in (cargos.get("adicionar") or [])])
        rem_defaults = _role_defaults(inter.guild, [int(x) for x in (cargos.get("remover") or [])])
        forbidden_defaults = _role_defaults(inter.guild, [int(x) for x in (cargos.get("proibidos") or [])])

        product_name = product.get("name") or product_id

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > Campo > **Cargos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure os cargos desse produto, como adicionar, remover ou proibidos."),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Cargos para adicionar**"),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione cargos para adicionar ao comprador",
                        custom_id=f"Loja_CargosCampo_Adicionar:{product_id}:{field_id}",
                        min_values=0,
                        max_values=25,
                        default_values=add_defaults or None,
                    )
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Cargos para remover**"),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione cargos para remover do comprador",
                        custom_id=f"Loja_CargosCampo_Remover:{product_id}:{field_id}",
                        min_values=0,
                        max_values=25,
                        default_values=rem_defaults or None,
                    )
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Cargos proibidos de abrir carrinho**"),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione cargos que não podem abrir carrinho",
                        custom_id=f"Loja_CargosCampo_Proibidos:{product_id}:{field_id}",
                        min_values=0,
                        max_values=25,
                        default_values=forbidden_defaults or None,
                    )
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Duração atual:** `{duracao_texto}`"),
                **container_kwargs_for_product(product)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CargosCampo_Voltar:{product_id}:{field_id}"),
                disnake.ui.Button(label="Duração", style=disnake.ButtonStyle.primary, emoji=emoji.clock, custom_id=f"Loja_CargosCampo_Duracao:{product_id}:{field_id}")
            ),
        ]
        return {"components": components}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        products = db.get_document("loja_products")
        product = (products or {}).get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id)
        if not field:
            from ..configurar import ConfigurarCampo
            return ConfigurarCampo.panel(inter, product_id, field_id)

        field = _ensure_field_roles_structure(field)
        cargos = field.get("cargos", {})
        add_roles = cargos.get("adicionar") or []
        rem_roles = cargos.get("remover") or []
        forbidden_roles = cargos.get("proibidos") or []

        duracao_minutos = cargos.get("duracao_minutos")
        duracao_texto = f"{duracao_minutos} minutos" if duracao_minutos else "Permanente"

        product_name = product.get("name") or product_id
        desc = (
            f"-# Painel > Loja > {product_name} > Campo > **Cargos**\n\n"
            f"Defina os cargos que serão adicionados/removidos após a compra deste campo.\n\n"
            f"-# Cargos para adicionar: `{len(add_roles)}` selecionados\n"
            f"-# Cargos para remover: `{len(rem_roles)}` selecionados\n"
            f"-# Cargos proibidos de abrir carrinho: `{len(forbidden_roles)}` selecionados\n"
            f"-# Duração: `{duracao_texto}`\n"
        )

        embed = disnake.Embed(description=desc, **embed_kwargs_for_product(product))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargos para adicionar",
                    custom_id=f"Loja_CargosCampo_Adicionar:{product_id}:{field_id}",
                    min_values=0,
                    max_values=25,
                    default_values=_role_defaults(inter.guild, [int(x) for x in add_roles]) or None,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargos para remover",
                    custom_id=f"Loja_CargosCampo_Remover:{product_id}:{field_id}",
                    min_values=0,
                    max_values=25,
                    default_values=_role_defaults(inter.guild, [int(x) for x in rem_roles]) or None,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargos proibidos de abrir carrinho",
                    custom_id=f"Loja_CargosCampo_Proibidos:{product_id}:{field_id}",
                    min_values=0,
                    max_values=25,
                    default_values=_role_defaults(inter.guild, [int(x) for x in forbidden_roles]) or None,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CargosCampo_Voltar:{product_id}:{field_id}"),
                disnake.ui.Button(label="Duração", style=disnake.ButtonStyle.primary, emoji=emoji.clock, custom_id=f"Loja_CargosCampo_Duracao:{product_id}:{field_id}"),
            ),
        ]
        return {"embed": embed, "components": components}


