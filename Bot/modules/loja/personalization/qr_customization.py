"""
Sistema de personalização de QR Code
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
import aiohttp
import io
import json
from PIL import Image, ImageDraw, ImageFont


class QRCustomizationModal(disnake.ui.Modal):
    def __init__(self):
        data = db.get_document("loja_qr_customization")
        corner_style = data.get("corner_style", "square")

        components = [
            disnake.ui.Label(
                text="Cor do QR Code (Hex)",
                component=disnake.ui.TextInput(
                    custom_id="color",
                    value=data.get("color", "#000000"),
                    placeholder="Ex: #000000 para preto",
                    max_length=7,
                    required=True,
                    style=disnake.TextInputStyle.short,
                ),
                description="Cor principal dos módulos do QR Code.",
            ),
            disnake.ui.Label(
                text="Cor de Fundo (Hex)",
                component=disnake.ui.TextInput(
                    custom_id="background_color",
                    value=data.get("background_color", "#FFFFFF"),
                    placeholder="Ex: #FFFFFF para branco",
                    max_length=7,
                    required=True,
                    style=disnake.TextInputStyle.short,
                ),
                description="Cor do fundo do QR Code.",
            ),
            disnake.ui.Label(
                text="Estilo dos Módulos",
                component=disnake.ui.StringSelect(
                    custom_id="corner_style",
                    placeholder="Selecione o estilo dos módulos",
                    options=[
                        disnake.SelectOption(label="Quadrado",  value="square",  description="Módulos quadrados (padrão)",  default=corner_style == "square"),
                        disnake.SelectOption(label="Arredondado", value="rounded", description="Módulos com cantos arredondados", default=corner_style == "rounded"),
                        disnake.SelectOption(label="Pontos",    value="dots",    description="Módulos em formato de pontos", default=corner_style == "dots"),
                    ],
                    required=True,
                ),
                description="Formato visual dos módulos do QR Code.",
            ),
            disnake.ui.Label(
                text="Logo (opcional)",
                component=disnake.ui.FileUpload(
                    custom_id="logo_file",
                    required=False,
                ),
                description="Imagem PNG/JPG que será inserida no centro do QR Code.",
            ),
            disnake.ui.Label(
                text="Tamanho do Logo (0.1 a 0.5)",
                component=disnake.ui.TextInput(
                    custom_id="logo_size",
                    value=str(data.get("logo_size", 0.3)),
                    placeholder="0.3 = 30% do tamanho do QR",
                    max_length=3,
                    required=False,
                    style=disnake.TextInputStyle.short,
                ),
                description="Proporção do logo em relação ao QR Code.",
            ),
        ]

        super().__init__(title="Personalizar QR Code", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        valores = inter.resolved_values

        # Validar cores hex
        color    = (inter.text_values.get("color") or "").strip()
        bg_color = (inter.text_values.get("background_color") or "").strip()

        if not color.startswith("#") or len(color) != 7:
            await inter.followup.send(
                f"{emoji.wrong} Cor do QR inválida! Use formato hex: #000000",
                ephemeral=True,
            )
            return

        if not bg_color.startswith("#") or len(bg_color) != 7:
            await inter.followup.send(
                f"{emoji.wrong} Cor de fundo inválida! Use formato hex: #FFFFFF",
                ephemeral=True,
            )
            return

        # Validar tamanho do logo
        try:
            logo_size_raw = inter.text_values.get("logo_size", "0.3") or "0.3"
            logo_size = float(logo_size_raw)
            if logo_size < 0.1 or logo_size > 0.5:
                raise ValueError
        except ValueError:
            await inter.followup.send(
                f"{emoji.wrong} Tamanho do logo inválido! Use valores entre 0.1 e 0.5",
                ephemeral=True,
            )
            return

        # Estilo dos cantos via select
        corner_style_val = valores.get("corner_style")
        if isinstance(corner_style_val, (list, tuple)):
            corner_style_val = corner_style_val[0] if corner_style_val else "square"
        corner_style = corner_style_val or "square"

        # Processar upload do logo
        data = db.get_document("loja_qr_customization")
        logo_url = data.get("logo_url", "")

        logo_file = valores.get("logo_file")
        if isinstance(logo_file, (list, tuple)):
            logo_file = logo_file[0] if logo_file else None

        if logo_file:
            try:
                allowed_exts = (".png", ".jpg", ".jpeg", ".webp")
                if not logo_file.filename.lower().endswith(allowed_exts):
                    await inter.followup.send(
                        f"{emoji.wrong} Formato de logo inválido! Use PNG, JPG ou WEBP.",
                        ephemeral=True,
                    )
                    return

                from pathlib import Path
                import base64

                base_dir = Path(__file__).resolve().parents[3] / "database" / "loja" / "qr_logos"
                base_dir.mkdir(parents=True, exist_ok=True)
                ext       = Path(logo_file.filename).suffix.lower()
                save_path = base_dir / f"logo_{inter.author.id}{ext}"
                file_data = await logo_file.read()
                save_path.write_bytes(file_data)

                # Converte para data URI para uso direto na API do qrcode-monkey
                mime = "image/png" if ext == ".png" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/webp")
                b64  = base64.b64encode(file_data).decode()
                logo_url = f"data:{mime};base64,{b64}"

            except Exception as exc:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao processar o logo: {exc}",
                    ephemeral=True,
                )
                return

        # Salvar configurações
        data["color"]            = color
        data["background_color"] = bg_color
        data["logo_url"]         = logo_url
        data["logo_size"]        = logo_size
        data["corner_style"]     = corner_style
        data["enabled"]          = True

        db.save_document("loja_qr_customization", data)

        await inter.followup.send(
            f"{emoji.correct} Personalização de QR Code salva com sucesso!\n"
            f"-# As novas configurações serão aplicadas aos próximos QR Codes gerados.",
            ephemeral=True,
        )


class QRCodeGenerator:
    """Gerador de QR Code personalizado"""
    
    @staticmethod
    def _add_watermark(image_bytes: bytes, text: str = "amethys.solutions") -> bytes:
        """Adiciona texto de watermark abaixo do QR Code"""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        qr_w, qr_h = img.size

        # Altura extra para o texto
        padding = 6
        font_size = max(12, qr_w // 22)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        # Calcular largura do texto
        dummy = Image.new("RGBA", (1, 1))
        draw_dummy = ImageDraw.Draw(dummy)
        bbox = draw_dummy.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        extra_h = text_h + padding * 2
        new_img = Image.new("RGBA", (qr_w, qr_h + extra_h), (255, 255, 255, 255))
        new_img.paste(img, (0, 0))

        draw = ImageDraw.Draw(new_img)
        x = (qr_w - text_w) // 2
        y = qr_h + padding
        draw.text((x, y), text, font=font, fill=(120, 120, 120, 255))

        out = io.BytesIO()
        new_img.convert("RGB").save(out, format="PNG")
        return out.getvalue()

    @staticmethod
    async def generate_custom_qr(data: str) -> bytes:
        """
        Gera um QR Code personalizado usando a API qrcode-monkey
        """
        config = db.get_document("loja_qr_customization")
        
        if not config.get("enabled"):
            # Se não estiver habilitado, usar QR simples
            return await QRCodeGenerator.generate_simple_qr(data)
        
        # Preparar configurações para a API
        qr_config = {
            "data": data,
            "config": {
                "body": config.get("corner_style", "square"),
                "eye": "frame0",
                "eyeBall": "ball0",
                "erf1": [],
                "erf2": [],
                "erf3": [],
                "brf1": [],
                "brf2": [],
                "brf3": [],
                "bodyColor": config.get("color", "#000000"),
                "bgColor": config.get("background_color", "#FFFFFF"),
                "eye1Color": config.get("color", "#000000"),
                "eye2Color": config.get("color", "#000000"),
                "eye3Color": config.get("color", "#000000"),
                "eyeBall1Color": config.get("color", "#000000"),
                "eyeBall2Color": config.get("color", "#000000"),
                "eyeBall3Color": config.get("color", "#000000"),
                "gradientColor1": "",
                "gradientColor2": "",
                "gradientType": "linear",
                "gradientOnEyes": False
            },
            "size": 300,
            "download": False,
            "file": "png"
        }
        
        # Adicionar logo se configurado
        if config.get("logo_url"):
            qr_config["config"]["logo"] = config["logo_url"]
            qr_config["config"]["logoMode"] = "clean"
            
        try:
            # Criar connector SSL que ignora verificação de certificado
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    "https://api.qrcode-monkey.com/qr/custom",
                    json=qr_config,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        # Se retornou imagem diretamente
                        if 'image' in content_type:
                            raw = await response.read()
                            return QRCodeGenerator._add_watermark(raw)
                        
                        # Se retornou JSON com URL da imagem
                        try:
                            result = await response.json()
                            if "imageUrl" in result:
                                async with session.get(result["imageUrl"]) as img_response:
                                    if img_response.status == 200:
                                        raw = await img_response.read()
                                        return QRCodeGenerator._add_watermark(raw)
                        except:
                            # Se falhou ao parsear JSON, tentar ler como bytes
                            raw = await response.read()
                            return QRCodeGenerator._add_watermark(raw)
        except Exception as e:
            print(f"Erro ao gerar QR personalizado: {e}")
        
        # Fallback para QR simples se houver erro
        return await QRCodeGenerator.generate_simple_qr(data)
    
    @staticmethod
    async def generate_simple_qr(data: str) -> bytes:
        """
        Gera um QR Code simples usando API alternativa
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={data}"
                ) as response:
                    if response.status == 200:
                        raw = await response.read()
                        return QRCodeGenerator._add_watermark(raw)
        except Exception as e:
            print(f"Erro ao gerar QR simples: {e}")
        
        return None
    
    @staticmethod
    def panel(inter: disnake.Interaction) -> dict:
        """Painel de personalização de QR Code"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            return QRCodeGenerator._panel_components(inter)
        return QRCodeGenerator._panel_embed(inter)
    
    @staticmethod
    def _panel_components(inter: disnake.Interaction) -> dict:
        data = db.get_document("loja_qr_customization")
        
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        # Status
        status = f"{emoji.on} Ativado" if data.get("enabled") else f"{emoji.off} Desativado"
        
        config_text = (
            f"**Status:** {status}\n"
            f"**Cor Principal:** {data.get('color', '#000000')}\n"
            f"**Cor de Fundo:** {data.get('background_color', '#FFFFFF')}\n"
            f"**Estilo dos Cantos:** {data.get('corner_style', 'square')}\n"
            f"**Logo:** {'Configurado' if data.get('logo_url') else 'Não configurado'}"
        )
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > Personalizar > **QR Code**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Personalize a aparência dos QR Codes de pagamento.\n"
                    "Adicione cores, logo e estilos personalizados."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(config_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Configurar",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.config,
                        custom_id="Loja_QRCode_Config"
                    ),
                    disnake.ui.Button(
                        label="Ativar" if not data.get("enabled") else "Desativar",
                        style=disnake.ButtonStyle.green if not data.get("enabled") else disnake.ButtonStyle.red,
                        emoji=emoji.on if not data.get("enabled") else emoji.off,
                        custom_id="Loja_QRCode_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Testar",
                        style=disnake.ButtonStyle.grey,
                        emoji="🧪",
                        custom_id="Loja_QRCode_Test"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Personalizar"
                )
            )
        ]}
    
    @staticmethod
    def _panel_embed(inter: disnake.Interaction):
        data = db.get_document("loja_qr_customization")
        
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Personalização de QR Code",
            description="Configure a aparência dos QR Codes",
            color=disnake.Color.from_rgb(0, 202, 164)
        )
        
        embed.add_field(
            name="Status",
            value=f"{emoji.on if data.get('enabled') else emoji.off} {'Ativado' if data.get('enabled') else 'Desativado'}",
            inline=True
        )
        
        embed.add_field(
            name="Cores",
            value=f"Principal: {data.get('color', '#000000')}\nFundo: {data.get('background_color', '#FFFFFF')}",
            inline=True
        )
        
        embed.add_field(
            name="Estilo",
            value=data.get("corner_style", "square"),
            inline=True
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.config,
                    custom_id="Loja_QRCode_Config"
                ),
                disnake.ui.Button(
                    label="Ativar" if not data.get("enabled") else "Desativar",
                    style=disnake.ButtonStyle.green if not data.get("enabled") else disnake.ButtonStyle.red,
                    emoji=emoji.on if not data.get("enabled") else emoji.off,
                    custom_id="Loja_QRCode_Toggle"
                ),
                disnake.ui.Button(
                    label="Testar",
                    style=disnake.ButtonStyle.grey,
                    emoji="🧪",
                    custom_id="Loja_QRCode_Test"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Personalizar"
                )
            )
        ]
        
        return embed, components
