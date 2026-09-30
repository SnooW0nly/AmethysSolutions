import disnake

from functions.database import database
from functions.message import message
from ..anunciar import Anunciar
from ..builder import Builder
from .db_helper import get_template_by_id


async def apply_template(inter: disnake.MessageInteraction, template_id: str) -> None:
    tpl = get_template_by_id(template_id)
    if not tpl:
        await message.error(inter, "Template não encontrado.", send=False)
        return
    database.save_document("messages_anunciar", tpl.get("data") or {})
    await inter.edit_original_message(components=Anunciar.create_buttons())


async def preview_template(inter: disnake.MessageInteraction, template_id: str) -> None:
    # Defer primeiro — build pode ter download de imagem
    await inter.response.defer(ephemeral=True)
    tpl = get_template_by_id(template_id)
    if not tpl:
        await inter.followup.send("Template não encontrado.", ephemeral=True)
        return
    built = await Builder.build_from_cfg(tpl.get("data") or {})
    if built["mode"] == "v2":
        await inter.followup.send(
            components=built["components"],
            flags=built["flags"],
            ephemeral=True,
            allowed_mentions=disnake.AllowedMentions.none(),
        )
    else:
        kwargs = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
        if built.get("content") is not None:
            kwargs["content"] = built["content"]
        if built.get("embed") is not None:
            kwargs["embed"] = built["embed"]
        if built.get("components"):
            kwargs["components"] = built["components"]
        if built.get("files"):
            kwargs["files"] = built["files"]
        await inter.followup.send(**kwargs)


async def send_template(inter: disnake.MessageInteraction, template_id: str) -> None:
    await inter.response.defer(with_message=False)
    tpl = get_template_by_id(template_id)
    if not tpl:
        await message.error(inter, "Template não encontrado.", send=True)
        return
    built = await Builder.build_from_cfg(tpl.get("data") or {})
    if built["mode"] == "v2":
        await inter.channel.send(
            components=built["components"],
            flags=built["flags"],
            allowed_mentions=disnake.AllowedMentions.none(),
        )
    else:
        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
        if built.get("content") is not None:
            kwargs["content"] = built["content"]
        if built.get("embed") is not None:
            kwargs["embed"] = built["embed"]
        if built.get("components"):
            kwargs["components"] = built["components"]
        if built.get("files"):
            kwargs["files"] = built["files"]
        await inter.channel.send(**kwargs)
