import disnake

class ContainerUtils:
    @staticmethod
    def parse_hex_to_colour(value: str | None) -> disnake.Colour | None:
        if not value:
            return None
        try:
            s = str(value).strip().lower()
            if s.startswith("0x"):
                s = s[2:]
            if s.startswith("#"):
                s = s[1:]
            if len(s) != 6:
                return None
            return disnake.Colour(int(s, 16))
        except Exception:
            return None

    @staticmethod
    def montar_container(
        conteudo: str | None, 
        imagem_url: str | None = None, 
        cor_hex: str | None = None, 
        extra_children: list | None = None,
        thumbnail_url: str | None = None
    ) -> disnake.ui.Container:
        children = []
        
        # Lidar com a Seção (Conteúdo e Thumbnail)
        thumbnail_accessory = None
        if thumbnail_url and (thumbnail_url.startswith("http://") or thumbnail_url.startswith("https://")):
            thumbnail_accessory = disnake.ui.Thumbnail(media=thumbnail_url)

        if conteudo:
            if thumbnail_accessory:
                children.append(disnake.ui.Section(
                    disnake.ui.TextDisplay(conteudo),
                    accessory=thumbnail_accessory
                ))
            else:
                children.append(disnake.ui.TextDisplay(conteudo))
        elif thumbnail_accessory:
             children.append(disnake.ui.Section(
                accessory=thumbnail_accessory
            ))


        # Lidar com a Imagem Principal
        if imagem_url and (imagem_url.startswith("http://") or imagem_url.startswith("https://")):
            try:
                if children:
                    children.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
                
                children.append(
                    disnake.ui.MediaGallery(
                        disnake.MediaGalleryItem(media=imagem_url)
                    )
                )
            except Exception:
                pass
        
        if extra_children:
            if children:
                children.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
            children.extend(extra_children)

        cor_container = ContainerUtils.parse_hex_to_colour(cor_hex)
        return disnake.ui.Container(*children, accent_colour=cor_container) if cor_container else disnake.ui.Container(*children)
