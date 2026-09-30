import disnake
from disnake.ext import commands

HELPER_OPTIONS = {
    "separator": {
        "nome": "Separador Horizontal",
        "component": disnake.ui.TextDisplay(
            content=(
                "1. **Separador Horizontal**\n"
                "Adiciona uma linha divisória para separar visualmente seções do anúncio.\n\n"
                "**Sintaxe:** `{{separator}}`\n"
                "**Exemplo:**\n"
                "```Bem-vindo!\n{{separator}}\nConfira as novidades abaixo.```"
            )
        ),
    },
    "accent_color": {
        "nome": "Cor de Destaque",
        "component": disnake.ui.TextDisplay(
            content=(
                "2. **Cor de Destaque**\n"
                "Define a cor de destaque do container (accent color).\n\n"
                "**Sintaxe:** `{{color: #RRGGBB}}`\n"
                "**Exemplo:**\n"
                "```{{color: #5865F2}}```"
            )
        ),
    },
    "image": {
        "nome": "Imagens, descrição e spoiler",
        "component": disnake.ui.TextDisplay(
            content=(
                "3. **Imagem, descrição e spoiler**\n"
                "Insere uma imagem grande no conteúdo e permite personalização.\n\n"
                "**Sintaxe:** `{{image url='URL' desc='Descrição opcional' spoiler}}`\n"
                "- O parâmetro `desc` é opcional e adiciona uma legenda à imagem.\n"
                "- O parâmetro `spoiler` é opcional e marca a imagem como spoiler.\n"
                "**Exemplo:**\n"
                "```{{image url='https://link.com/imagem.png' desc='Uma imagem incrível' spoiler}}```"
            )
        ),
    },
    "example": {
        "nome": "Exemplo Completo",
        "component": disnake.ui.TextDisplay(
            content=(
                "4. **Exemplo Completo**\n"
                "```\n"
                "{{color: #FF0000}}\n"
                "Bem-vindo ao nosso servidor!\n"
                "{{separator}}\n"
                "{{image url='https://cdn.discordapp.com/avatars/1193819404094423070/e6d3aa4834ce6afe06c774d804ccc475.webp' desc='Um gato fofo' spoiler}}\n"
                "{{separator}}\n"
                "Aproveite sua visita!\n"
                "```"
            )
        ),
    },
}

class Helper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def helper(option: str) -> list[disnake.ui.Container]:
        if option not in HELPER_OPTIONS:
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(content=f"Opção de ajuda não encontrada: {option}"),
                )
            ]
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(content="## Como anunciar usando Containers no Sync Pro\nOs containers permitem criar mensagens ricas e interativas usando marcadores especiais. Veja abaixo cada recurso disponível, sua função, sintaxe e exemplos."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                HELPER_OPTIONS[option]["component"],
                disnake.ui.ActionRow(
                    *[
                        disnake.ui.Button(label=HELPER_OPTIONS[opcao]["nome"], style=disnake.ButtonStyle.secondary, custom_id=f"Anunciar_HelperContainer_{opcao}", disabled=opcao == option)
                        for opcao in HELPER_OPTIONS
                    ]
                )
            )
        ]

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id.startswith("Anunciar_HelperContainer_"):
            option = inter.component.custom_id.replace("Anunciar_HelperContainer_", "")
            await inter.response.edit_message(components=self.helper(option))
        
        elif inter.component.custom_id == "Anunciar_Helper":
            await inter.response.send_message(components=self.helper(), ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True))