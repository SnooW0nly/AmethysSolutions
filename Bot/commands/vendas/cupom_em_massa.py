import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils
from datetime import datetime, timedelta


class CupomMassaCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def _get_coupon_info_text(self, coupon: dict, code: str) -> str:
        """Gera texto formatado com informações do cupom"""
        # Verificar expiração
        if coupon.get("expiration"):
            if datetime.now().timestamp() > coupon["expiration"]:
                status = f"{emoji.wrong} Expirado"
            else:
                exp_date = datetime.fromtimestamp(coupon["expiration"])
                status = f"{emoji.time} Expira {exp_date.strftime('%d/%m %H:%M')}"
        else:
            status = f"{emoji.correct} Ativo"
        
        # Calcular desconto
        if coupon.get("discount_type") == "porcentagem":
            desconto = f"{coupon.get('discount_value', 0)}%"
        else:
            desconto = f"R$ {coupon.get('discount_value', 0):.2f}"
        
        # Usos
        max_uses = coupon.get("max_uses", 0)
        uses = coupon.get("uses", 0)
        if max_uses > 0:
            usos_text = f"{uses}/{max_uses}"
        else:
            usos_text = f"{uses}"
        
        return (
            f"**{code}**\n"
            f"{coupon.get('description', 'Sem descrição')}\n"
            f"{emoji.dollar} **Desconto:** {desconto}\n"
            f"{emoji.question} **Usos:** {usos_text}\n"
            f"{status}"
        )
    
    def CupomMassaComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        """Gera componentes V2 para visualização de cupons"""
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            try:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            except (ValueError, AttributeError):
                pass
        
        data = db.get_document("loja_mass_coupons")
        coupons = data.get("coupons", {})
        
        if not coupons:
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{emoji.wrong} Não há cupons cadastrados!"),
                **container_kwargs
            )
            return [container]
        
        # Preparar lista de cupons
        cupons_text = []
        for code, coupon in list(coupons.items())[:10]:  # Limite de 10 cupons
            cupons_text.append(self._get_coupon_info_text(coupon, code))
        
        text_content = (
            f"# {emoji.ticket}\n"
            f"-# **Cupons em Massa**\n\n"
            f"Total de cupons: **{len(coupons)}**\n\n"
            + "\n\n".join(cupons_text)
        )
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(text_content),
            **container_kwargs
        )
        
        return [container]
    
    def CupomMassaEmbed(self, inter: disnake.MessageInteraction):
        """Gera embed para visualização de cupons"""
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        data = db.get_document("loja_mass_coupons")
        coupons = data.get("coupons", {})
        
        if not coupons:
            embed = disnake.Embed(description=f"{emoji.wrong} Não há cupons cadastrados!")
            if primary_color_hex:
                try:
                    embed.color = int(primary_color_hex.replace("#", ""), 16)
                except (ValueError, AttributeError):
                    pass
            return embed, []
        
        # Preparar lista de cupons
        cupons_text = []
        for code, coupon in list(coupons.items())[:10]:  # Limite de 10 cupons
            cupons_text.append(self._get_coupon_info_text(coupon, code))
        
        embed = disnake.Embed(
            title=f"{emoji.ticket} Cupons em Massa",
            description=f"Total de cupons: **{len(coupons)}**\n\n" + "\n\n".join(cupons_text)
        )
        if primary_color_hex:
            try:
                embed.color = int(primary_color_hex.replace("#", ""), 16)
            except (ValueError, AttributeError):
                pass
        
        return embed, []
    
    @commands.slash_command(
        name="cupom_massa",
        description="Gerencia cupons de desconto em massa",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def cupom_massa(self, inter: disnake.ApplicationCommandInteraction):
        pass
    
    @cupom_massa.sub_command(
        name="criar",
        description="Cria um novo cupom em massa"
    )
    async def criar(
        self,
        inter: disnake.ApplicationCommandInteraction,
        nome: str = commands.Param(description="Nome/código do cupom", max_length=30),
        descricao: str = commands.Param(description="Descrição do cupom", max_length=100),
        tipo_desconto: str = commands.Param(
            description="Tipo de desconto",
            choices=["porcentagem", "valor_fixo"]
        ),
        valor_desconto: float = commands.Param(description="Valor do desconto (% ou R$)", min_value=0.01),
        valor_maximo_desconto: float = commands.Param(
            default=None,
            description="Valor máximo de desconto em R$ (apenas para porcentagem)",
            min_value=0
        ),
        valor_minimo_compra: float = commands.Param(
            default=0,
            description="Valor mínimo de compra para usar o cupom",
            min_value=0
        ),
        valor_maximo_compra: float = commands.Param(
            default=None,
            description="Valor máximo de compra para usar o cupom",
            min_value=0
        ),
        maximo_usos: int = commands.Param(
            default=0,
            description="Máximo de usos totais (0 = ilimitado)",
            min_value=0
        ),
        cargo_obrigatorio: disnake.Role = commands.Param(
            default=None,
            description="Cargo obrigatório para usar o cupom"
        ),
        duracao_minutos: int = commands.Param(
            default=0,
            description="Duração em minutos (0 = permanente)",
            min_value=0
        )
    ):
        await inter.response.defer(ephemeral=True)
        
        if not await perms.check(inter.user.id):
            await inter.followup.send("Você não tem permissão para usar este comando", ephemeral=True)
            return
        
        mode = db.get_document("custom_mode").get("mode")
        
        # Carregar cupons
        data = db.get_document("loja_mass_coupons")
        if "coupons" not in data:
            data["coupons"] = {}
        
        # Verificar se já existe
        nome_upper = nome.upper()
        if nome_upper in data["coupons"]:
            colors = db.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            
            if mode == "embed":
                embed = disnake.Embed(description=f"{emoji.wrong} Já existe um cupom com esse nome!")
                if primary_color_hex:
                    try:
                        embed.color = int(primary_color_hex.replace("#", ""), 16)
                    except (ValueError, AttributeError):
                        pass
                await inter.edit_original_response(content=None, embed=embed, components=[])
            else:
                container_kwargs = {}
                if primary_color_hex:
                    try:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    except (ValueError, AttributeError):
                        pass
                
                await inter.edit_original_response(
                    content=None,
                    components=[disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} Já existe um cupom com esse nome!"),
                        **container_kwargs
                    )],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return
        
        # Calcular expiração
        expiration = None
        if duracao_minutos > 0:
            expiration = (datetime.now() + timedelta(minutes=duracao_minutos)).timestamp()
        
        # Criar cupom
        coupon_data = {
            "code": nome_upper,
            "description": descricao,
            "discount_type": tipo_desconto,
            "discount_value": valor_desconto,
            "max_discount": valor_maximo_desconto,
            "min_purchase": valor_minimo_compra,
            "max_purchase": valor_maximo_compra,
            "max_uses": maximo_usos,
            "uses": 0,
            "required_role": cargo_obrigatorio.id if cargo_obrigatorio else None,
            "expiration": expiration,
            "created_at": datetime.now().timestamp(),
            "created_by": inter.author.id,
            "used_by": []
        }
        
        data["coupons"][nome_upper] = coupon_data
        db.save_document("loja_mass_coupons", data)
        
        # Preparar informações
        if tipo_desconto == "porcentagem":
            desconto_text = f"{valor_desconto}%"
            if valor_maximo_desconto:
                desconto_text += f" (máx R$ {valor_maximo_desconto:.2f})"
        else:
            desconto_text = f"R$ {valor_desconto:.2f}"
        
        info_lines = [
            f"{emoji.dollar} **Desconto:** {desconto_text}",
            f"{emoji.information} **Descrição:** {descricao}"
        ]
        
        if valor_minimo_compra > 0:
            info_lines.append(f"{emoji.chart} **Compra Mínima:** R$ {valor_minimo_compra:.2f}")
        
        if valor_maximo_compra:
            info_lines.append(f"{emoji.chart} **Compra Máxima:** R$ {valor_maximo_compra:.2f}")
        
        if maximo_usos > 0:
            info_lines.append(f"{emoji.question} **Máximo de Usos:** {maximo_usos}")
        
        if cargo_obrigatorio:
            info_lines.append(f"{emoji.role} **Cargo Obrigatório:** {cargo_obrigatorio.mention}")
        
        if expiration:
            exp_date = datetime.fromtimestamp(expiration).strftime("%d/%m/%Y %H:%M")
            info_lines.append(f"{emoji.time} **Expira em:** {exp_date}")
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.correct} Cupom Criado!",
                description=f"Cupom **{nome_upper}** criado com sucesso!\n\n" + "\n".join(info_lines)
            )
            if primary_color_hex:
                try:
                    embed.color = int(primary_color_hex.replace("#", ""), 16)
                except (ValueError, AttributeError):
                    pass
            await inter.edit_original_response(content=None, embed=embed, components=[])
        else:
            container_kwargs = {}
            if primary_color_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except (ValueError, AttributeError):
                    pass
            
            await inter.edit_original_response(
                content=None,
                components=[disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.correct}\n"
                        f"-# **Cupom Criado!**\n\n"
                        f"Cupom **{nome_upper}** criado com sucesso!\n\n"
                        + "\n".join(info_lines)
                    ),
                    **container_kwargs
                )],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
    
    @cupom_massa.sub_command(
        name="remover",
        description="Remove um cupom em massa"
    )
    async def remover(
        self,
        inter: disnake.ApplicationCommandInteraction,
        nome: str = commands.Param(description="Nome do cupom", autocomplete=True)
    ):
        await inter.response.defer(ephemeral=True)
        
        if not await perms.check(inter.user.id):
            await inter.followup.send("Você não tem permissão para usar este comando", ephemeral=True)
            return
        
        mode = db.get_document("custom_mode").get("mode")
        
        # Carregar cupons
        data = db.get_document("loja_mass_coupons")
        
        nome_upper = nome.upper()
        if nome_upper not in data.get("coupons", {}):
            colors = db.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            
            if mode == "embed":
                embed = disnake.Embed(description=f"{emoji.wrong} Cupom não encontrado!")
                if primary_color_hex:
                    try:
                        embed.color = int(primary_color_hex.replace("#", ""), 16)
                    except (ValueError, AttributeError):
                        pass
                await inter.edit_original_response(content=None, embed=embed, components=[])
            else:
                container_kwargs = {}
                if primary_color_hex:
                    try:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    except (ValueError, AttributeError):
                        pass
                
                await inter.edit_original_response(
                    content=None,
                    components=[disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} Cupom não encontrado!"),
                        **container_kwargs
                    )],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return
        
        # Remover cupom
        coupon_data = data["coupons"][nome_upper]
        del data["coupons"][nome_upper]
        db.save_document("loja_mass_coupons", data)
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.correct} Cupom Removido!",
                description=f"Cupom **{nome_upper}** removido com sucesso!\n\n{emoji.question} **Usos totais:** {coupon_data.get('uses', 0)}"
            )
            if primary_color_hex:
                try:
                    embed.color = int(primary_color_hex.replace("#", ""), 16)
                except (ValueError, AttributeError):
                    pass
            await inter.edit_original_response(content=None, embed=embed, components=[])
        else:
            container_kwargs = {}
            if primary_color_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except (ValueError, AttributeError):
                    pass
            
            await inter.edit_original_response(
                content=None,
                components=[disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.correct}\n"
                        f"-# **Cupom Removido!**\n\n"
                        f"Cupom **{nome_upper}** removido com sucesso!\n\n"
                        f"{emoji.question} **Usos totais:** {coupon_data.get('uses', 0)}"
                    ),
                    **container_kwargs
                )],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
    
    @cupom_massa.sub_command(
        name="ver",
        description="Lista todos os cupons em massa"
    )
    async def ver(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        
        if not await perms.check(inter.user.id):
            await inter.followup.send("Você não tem permissão para usar este comando", ephemeral=True)
            return
        
        mode = db.get_document("custom_mode").get("mode")
        
        if mode == "embed":
            embed, components = self.CupomMassaEmbed(inter)
            await inter.edit_original_response(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_response(
                components=self.CupomMassaComponents(inter),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
    
    @remover.autocomplete("nome")
    async def cupom_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str):
        data = db.get_document("loja_mass_coupons")
        coupons = data.get("coupons", {})
        
        choices = []
        for code in coupons.keys():
            if string.upper() in code:
                choices.append(disnake.OptionChoice(name=code, value=code))
                if len(choices) >= 25:
                    break
        
        return choices
    
    @staticmethod
    def validate_coupon(code: str, user_id: int, purchase_value: float, guild: disnake.Guild) -> tuple[bool, str, float]:
        """
        Valida um cupom em massa
        Returns: (is_valid, error_message, discount_amount)
        """
        data = db.get_document("loja_mass_coupons")
        coupons = data.get("coupons", {})
        
        code_upper = code.upper()
        if code_upper not in coupons:
            return False, "Cupom inválido", 0
        
        coupon = coupons[code_upper]
        
        # Verificar expiração
        if coupon.get("expiration"):
            if datetime.now().timestamp() > coupon["expiration"]:
                return False, "Cupom expirado", 0
        
        # Verificar máximo de usos
        if coupon.get("max_uses", 0) > 0:
            if coupon.get("uses", 0) >= coupon["max_uses"]:
                return False, "Cupom esgotado", 0
        
        # Verificar se usuário já usou
        if user_id in coupon.get("used_by", []):
            return False, "Você já usou este cupom", 0
        
        # Verificar valor mínimo
        if coupon.get("min_purchase", 0) > 0:
            if purchase_value < coupon["min_purchase"]:
                return False, f"Compra mínima: R$ {coupon['min_purchase']:.2f}", 0
        
        # Verificar valor máximo
        if coupon.get("max_purchase"):
            if purchase_value > coupon["max_purchase"]:
                return False, f"Compra máxima: R$ {coupon['max_purchase']:.2f}", 0
        
        # Verificar cargo obrigatório
        if coupon.get("required_role"):
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(coupon["required_role"])
                if role and role not in member.roles:
                    return False, f"Cargo obrigatório: {role.name}", 0
            else:
                return False, "Membro não encontrado", 0
        
        # Calcular desconto
        if coupon.get("discount_type") == "porcentagem":
            discount = purchase_value * (coupon.get("discount_value", 0) / 100)
            if coupon.get("max_discount"):
                discount = min(discount, coupon["max_discount"])
        else:
            discount = coupon.get("discount_value", 0)
        
        # Não deixar desconto maior que o valor da compra
        discount = min(discount, purchase_value)
        
        return True, "", discount
    
    @staticmethod
    def use_coupon(code: str, user_id: int):
        """Marca o cupom como usado"""
        data = db.get_document("loja_mass_coupons")
        code_upper = code.upper()
        
        if code_upper in data.get("coupons", {}):
            data["coupons"][code_upper]["uses"] = data["coupons"][code_upper].get("uses", 0) + 1
            if user_id not in data["coupons"][code_upper].get("used_by", []):
                data["coupons"][code_upper].setdefault("used_by", []).append(user_id)
            db.save_document("loja_mass_coupons", data)


def setup(bot: commands.Bot):
    bot.add_cog(CupomMassaCommand(bot))
