"""
Mensagens pré-definidas para o bot.
"""

import disnake
from functions.emoji import emoji

class message:
    @staticmethod
    async def wait(inter: disnake.MessageInteraction, send=False, ephemeral=True, followup=False) -> disnake.Message:
        components = disnake.ui.TextDisplay(f"{emoji.loading} Carregando informações...")

        if send:
            if inter.response.is_done():
                return await inter.followup.send(components=components, flags=disnake.MessageFlags(is_components_v2=True), ephemeral=ephemeral)
            return await inter.response.send_message(components=components, flags=disnake.MessageFlags(is_components_v2=True), ephemeral=ephemeral)
        
        elif followup:
            return await inter.followup.send(components=components, flags=disnake.MessageFlags(is_components_v2=True), ephemeral=ephemeral)
        
        else:
            # Comportamento padrão: editar a mensagem original
            if not inter.response.is_done():
                import traceback as _tb
                _cid = getattr(getattr(inter, 'component', None), 'custom_id', '???')
                _caller = ''.join(_tb.format_stack()[-4:-1])
                print(f"\n[DEFER LOG] custom_id='{_cid}'\n{_caller}")
                await inter.response.defer(with_message=False)
            return await inter.edit_original_message(
                embed=None,
                components=components
            )

    @staticmethod
    async def missing_perms(inter: disnake.MessageInteraction) -> disnake.Message:
        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"{emoji.wrong} Você não tem permissão para usar este comando")
            )
        ]
        return await inter.response.send_message(
            components=components,
            ephemeral=True,
            flags=disnake.MessageFlags(is_components_v2=True)
        )

    @staticmethod
    async def error(inter: disnake.MessageInteraction, message: str, send=False, followup=False, component=None) -> disnake.Message:
        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"{emoji.wrong} {message}"),
            )
        ]
        if component:
            if isinstance(component, (list, tuple)):
                components.extend(component)
            else:
                components.append(component)

        if send:
            if inter.response.is_done():
                return await inter.followup.send(
                    components=components,
                    ephemeral=True,
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return await inter.response.send_message(
                components=components,
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        elif followup:
            return await inter.followup.send(
                components=components,
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            return await inter.edit_original_message(
                embed=None,
                components=components
            )

    @staticmethod
    async def success(inter: disnake.MessageInteraction, message: str, send=False, followup=False, component=None) -> disnake.Message:
        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"{emoji.correct} {message}"),
            )
        ]
        if component:
            if isinstance(component, (list, tuple)):
                components.extend(component)
            else:
                components.append(component)

        if send:
            if inter.response.is_done():
                return await inter.followup.send(
                    components=components,
                    ephemeral=True,
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return await inter.response.send_message(
                components=components,
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        elif followup:
            return await inter.followup.send(
                components=components,
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            return await inter.edit_original_message(
                embed=None,
                components=components
            )


class embed_message:
    @staticmethod
    async def wait(inter: disnake.MessageInteraction, send=False, ephemeral=True, followup=False) -> disnake.Message:
        content = f"{emoji.loading} Carregando informações..."
        if send:
            if inter.response.is_done():
                return await inter.followup.send(content=content, ephemeral=ephemeral)
            return await inter.response.send_message(content=content, ephemeral=ephemeral)
        
        elif followup:
            return await inter.followup.send(content=content, ephemeral=ephemeral)
        
        else:
            if not inter.response.is_done():
                import traceback as _tb
                _cid = getattr(getattr(inter, 'component', None), 'custom_id', '???')
                _caller = ''.join(_tb.format_stack()[-4:-1])
                print(f"\n[DEFER LOG embed] custom_id='{_cid}'\n{_caller}")
                await inter.response.defer(with_message=False)
            embed = disnake.Embed(description=content)
            return await inter.edit_original_message(embed=embed, components=[])

    @staticmethod
    async def missing_perms(inter: disnake.MessageInteraction) -> disnake.Message:
        content = f"{emoji.wrong} Você não tem permissão para usar este comando"
        return await inter.response.send_message(content=content, ephemeral=True)

    @staticmethod
    async def error(inter: disnake.MessageInteraction, message: str, send=False, followup=False, component=None) -> disnake.Message:
        content = f"{emoji.wrong} {message}"
        if send:
            if inter.response.is_done():
                return await inter.followup.send(content=content, ephemeral=True, components=component)
            return await inter.response.send_message(content=content, ephemeral=True, components=component)
        elif followup:
            return await inter.followup.send(content=content, ephemeral=True, components=component)
        else:
            embed = disnake.Embed(description=content)
            return await inter.edit_original_message(embed=embed, components=component)

    @staticmethod
    async def success(inter: disnake.MessageInteraction, message: str, send=False, followup=False, component=None) -> disnake.Message:
        content = f"{emoji.correct} {message}"
        if send:
            if inter.response.is_done():
                return await inter.followup.send(content=content, ephemeral=True, components=component)
            return await inter.response.send_message(content=content, ephemeral=True, components=component)
        elif followup:
            return await inter.followup.send(content=content, ephemeral=True, components=component)
        else:
            embed = disnake.Embed(description=content)
            return await inter.edit_original_message(embed=embed, components=component)

    @staticmethod
    async def plain(inter: disnake.MessageInteraction, content: str, send=False, followup=False, component=None) -> disnake.Message:
        if send:
            if inter.response.is_done():
                return await inter.followup.send(content=content, ephemeral=True, components=component)
            return await inter.response.send_message(content=content, ephemeral=True, components=component)
        elif followup:
            return await inter.followup.send(content=content, ephemeral=True, components=component)
        else:
            embed = disnake.Embed(description=content)
            return await inter.edit_original_message(embed=embed, components=component)