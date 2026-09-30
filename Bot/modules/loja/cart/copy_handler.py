"""
Handler para o botão de copiar conteúdo entregue
"""
import disnake
import io
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db


class CopyProductHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Handler para copiar instruções
        if custom_id.startswith("copy_instructions:"):
            await self._handle_copy_instructions(inter)
            return
        
        # Handler para copiar conteúdo do produto
        if not custom_id.startswith("copy_delivered_content:"):
            return
        
        await self._handle_copy_content(inter)
    
    async def _handle_copy_instructions(self, inter: disnake.MessageInteraction):
        """Handler para copiar instruções completas"""
        # Formato: copy_instructions:user_id:product_id:campo_id
        parts = inter.component.custom_id.split(":")
        if len(parts) < 4:
            await inter.response.send_message(
                f"{emoji.wrong} Erro ao copiar instruções.",
                ephemeral=True
            )
            return
        
        user_id = int(parts[1])
        product_id = parts[2]
        campo_id = parts[3]
        
        # Verificar se o usuário que clicou é o mesmo que recebeu o conteúdo
        if inter.user.id != user_id:
            await inter.response.send_message(
                f"{emoji.wrong} Você não pode copiar estas instruções.",
                ephemeral=True
            )
            return
        
        # Buscar instruções completas do banco de dados
        try:
            products = db.get_document("loja_products")
            product = products.get(product_id, {})
            campo = product.get("campos", {}).get(campo_id, {})
            instructions = campo.get("instructions")
            
            if not instructions:
                await inter.response.send_message(
                    f"{emoji.wrong} Instruções não encontradas.",
                    ephemeral=True
                )
                return
            
            # Verificar se o conteúdo é maior que 2000 caracteres
            if len(instructions) > 2000:
                # Criar arquivo .txt
                file_content = io.BytesIO(instructions.encode('utf-8'))
                file = disnake.File(fp=file_content, filename="instrucoes.txt")
                
                await inter.response.send_message(
                    file=file,
                    ephemeral=True
                )
            else:
                # Enviar mensagem efêmera com apenas o conteúdo (sem code blocks)
                await inter.response.send_message(
                    instructions,
                    ephemeral=True
                )
        except Exception as e:
            print(f"[COPY HANDLER] Erro ao copiar instruções: {e}")
            await inter.response.send_message(
                f"{emoji.wrong} Erro ao copiar instruções.",
                ephemeral=True
            )
    
    async def _handle_copy_content(self, inter: disnake.MessageInteraction):
        """Handler para copiar conteúdo do produto"""
        
        # Extrair user_id do custom_id
        parts = inter.component.custom_id.split(":")
        if len(parts) < 2:
            await inter.response.send_message(
                f"{emoji.wrong} Erro ao copiar conteúdo.",
                ephemeral=True
            )
            return
        
        # Verificar se o usuário que clicou é o mesmo que recebeu o conteúdo
        user_id = int(parts[1])
        if inter.user.id != user_id:
            await inter.response.send_message(
                f"{emoji.wrong} Você não pode copiar este conteúdo.",
                ephemeral=True
            )
            return
        
        # Obter o conteúdo da mensagem original
        content_text = ""
        
        # DEBUG: Imprimir estrutura da mensagem
        print(f"[COPY HANDLER] Message components: {len(inter.message.components) if inter.message.components else 0}")
        print(f"[COPY HANDLER] Message embeds: {len(inter.message.embeds) if inter.message.embeds else 0}")
        print(f"[COPY HANDLER] Message attachments: {len(inter.message.attachments) if inter.message.attachments else 0}")
        
        # Tentar extrair do embed primeiro
        if inter.message.embeds:
            embed = inter.message.embeds[0]
            for field in embed.fields:
                # Procurar por "Seus Itens" no nome do field
                if "Seus Itens" in field.name or "Itens" in field.name:
                    content_text = field.value
                    # Limpar formatação markdown se houver
                    if content_text:
                        content_text = content_text.strip()
                        # Remover asteriscos de itálico se o texto começar com *
                        if content_text.startswith("*") and content_text.endswith("*"):
                            content_text = content_text[1:-1].strip()
                    print(f"[COPY HANDLER] Encontrado em embed: {len(content_text)} chars")
                    break
        
        # Tentar extrair do container (components v2) - ESTRUTURA CORRETA
        if not content_text and inter.message.components:
            try:
                def extract_text_from_textdisplay(item):
                    """Extrai texto de um TextDisplay de várias formas"""
                    text = ""
                    # Tentar diferentes atributos e métodos
                    attrs_to_try = ['content', 'text', '_text', '_content', 'value', 'label', 'placeholder']
                    for attr in attrs_to_try:
                        if hasattr(item, attr):
                            try:
                                val = getattr(item, attr)
                                if val:
                                    text = str(val)
                                    if text and text.strip():
                                        break
                            except:
                                pass
                    
                    # Se ainda não encontrou, tentar inspecionar todos os atributos
                    if not text:
                        try:
                            # Tentar __dict__ se disponível
                            if hasattr(item, '__dict__'):
                                for key, val in item.__dict__.items():
                                    if isinstance(val, str) and val.strip():
                                        text = val
                                        break
                        except:
                            pass
                    
                    # Se ainda não encontrou, tentar converter diretamente
                    if not text:
                        try:
                            text = str(item)
                            # Se str() retornar algo como "<TextDisplay ...>", tentar repr()
                            if '<' in text and '>' in text:
                                text = ""
                        except:
                            pass
                    
                    # Última tentativa: usar repr() e extrair strings
                    if not text:
                        try:
                            repr_str = repr(item)
                            # Tentar extrair strings do repr
                            import re
                            matches = re.findall(r'["\']([^"\']+)["\']', repr_str)
                            if matches:
                                # Pegar a string mais longa que não seja um nome de classe
                                for match in sorted(matches, key=len, reverse=True):
                                    if len(match) > 10 and "Seus Itens" in match:
                                        text = match
                                        break
                        except:
                            pass
                    
                    # DEBUG
                    if text:
                        print(f"[COPY HANDLER] TextDisplay extraído ({len(text)} chars): {text[:100]}...")
                    else:
                        print(f"[COPY HANDLER] TextDisplay não extraído. Tipo: {type(item)}, Dir: {[x for x in dir(item) if not x.startswith('_')][:10]}")
                    
                    return text
                
                def parse_items_text(text):
                    """Extrai conteúdo após 'Seus Itens' do texto"""
                    if not text:
                        return None
                    
                    # DEBUG
                    print(f"[COPY HANDLER] Parsing text: {text[:200]}...")
                    
                    # Verificar se contém "Seus Itens"
                    if "Seus Itens" not in text and "### Seus Itens" not in text:
                        return None
                    
                    lines = text.split('\n')
                    content_lines = []
                    found_items = False
                    
                    for line in lines:
                        # Pular linhas de título/header que começam com #
                        if line.strip().startswith('#'):
                            if "Seus Itens" in line:
                                found_items = True
                                # Tentar extrair da mesma linha se possível
                                parts = line.split("Seus Itens", 1)
                                if len(parts) > 1:
                                    remaining = parts[1].strip()
                                    # Remover markdown headers
                                    remaining = remaining.lstrip('#').strip()
                                    remaining = remaining.lstrip('-').strip()
                                    if remaining:
                                        content_lines.append(remaining)
                            continue
                        
                        if found_items:
                            # Adicionar linha se não estiver vazia
                            line_clean = line.strip()
                            # Remover prefixos markdown
                            line_clean = line_clean.lstrip('-').strip()
                            if line_clean:
                                content_lines.append(line_clean)
                        elif "Seus Itens" in line:
                            found_items = True
                            # Tentar extrair da mesma linha se possível
                            parts = line.split("Seus Itens", 1)
                            if len(parts) > 1:
                                remaining = parts[1].strip()
                                # Remover markdown headers
                                remaining = remaining.lstrip('#').strip()
                                remaining = remaining.lstrip('-').strip()
                                if remaining:
                                    content_lines.append(remaining)
                    
                    result = '\n'.join(content_lines) if content_lines else None
                    if result:
                        print(f"[COPY HANDLER] Parsed result: {result[:100]}...")
                    return result
                
                # ESTRUTURA: components é uma lista onde cada item pode ser Container ou ActionRow
                # No delivery.py linha 131-136, temos:
                # components = [Container(*container_items)]
                # Onde container_items inclui TextDisplay e ActionRow com botão
                
                # Iterar sobre todos os componentes
                for idx, component_row in enumerate(inter.message.components):
                    print(f"[COPY HANDLER] Component {idx}: {type(component_row).__name__}")
                    print(f"[COPY HANDLER] Is Container? {isinstance(component_row, disnake.ui.Container)}")
                    print(f"[COPY HANDLER] Has children? {hasattr(component_row, 'children')}")
                    
                    # Verificar se é Container diretamente (ESTRUTURA PRINCIPAL)
                    # Tentar múltiplas formas de verificar
                    is_container = (
                        isinstance(component_row, disnake.ui.Container) or
                        type(component_row).__name__ == 'Container' or
                        'Container' in str(type(component_row))
                    )
                    
                    if is_container:
                        children = None
                        if hasattr(component_row, 'children'):
                            children = component_row.children
                        elif hasattr(component_row, '_children'):
                            children = component_row._children
                        elif hasattr(component_row, 'items'):
                            children = component_row.items
                        
                        if children:
                            print(f"[COPY HANDLER] Container encontrado, children: {len(children)}")
                            for item_idx, item in enumerate(children):
                                print(f"[COPY HANDLER]   Item {item_idx}: {type(item).__name__}")
                                
                                # TextDisplay direto
                                is_textdisplay = (
                                    isinstance(item, disnake.ui.TextDisplay) or
                                    type(item).__name__ == 'TextDisplay' or
                                    'TextDisplay' in str(type(item))
                                )
                                
                                if is_textdisplay:
                                    print(f"[COPY HANDLER]     TextDisplay encontrado!")
                                    text = extract_text_from_textdisplay(item)
                                    print(f"[COPY HANDLER]     Text extraído: {bool(text)}")
                                    if text:
                                        parsed = parse_items_text(text)
                                        print(f"[COPY HANDLER]     Parsed: {bool(parsed)}")
                                        if parsed:
                                            content_text = parsed
                                            print(f"[COPY HANDLER] ✓ Conteúdo encontrado em TextDisplay!")
                                            break
                                else:
                                    print(f"[COPY HANDLER]     Não é TextDisplay, tentando outros métodos...")
                                    # Tentar extrair texto mesmo que não seja TextDisplay identificado
                                    try:
                                        text = extract_text_from_textdisplay(item)
                                        if text and "Seus Itens" in text:
                                            parsed = parse_items_text(text)
                                            if parsed:
                                                content_text = parsed
                                                print(f"[COPY HANDLER] ✓ Conteúdo encontrado (método alternativo)!")
                                                break
                                    except:
                                        pass
                                
                                # Verificar se é ActionRow dentro do Container
                                if isinstance(item, disnake.ui.ActionRow):
                                    print(f"[COPY HANDLER]     ActionRow encontrado dentro do Container")
                                    if hasattr(item, 'children'):
                                        for child in item.children:
                                            if isinstance(child, disnake.ui.Container):
                                                if hasattr(child, 'children'):
                                                    for sub_item in child.children:
                                                        if isinstance(sub_item, disnake.ui.TextDisplay):
                                                            text = extract_text_from_textdisplay(sub_item)
                                                            if text:
                                                                parsed = parse_items_text(text)
                                                                if parsed:
                                                                    content_text = parsed
                                                                    print(f"[COPY HANDLER] ✓ Conteúdo encontrado em ActionRow>Container>TextDisplay!")
                                                                    break
                                                        if content_text:
                                                            break
                                            if content_text:
                                                break
                                
                                # Section pode conter TextDisplay
                                elif hasattr(item, 'children') and not isinstance(item, disnake.ui.ActionRow):
                                    print(f"[COPY HANDLER]     Item com children (possível Section)")
                                    for sub_item in item.children:
                                        if isinstance(sub_item, disnake.ui.TextDisplay):
                                            text = extract_text_from_textdisplay(sub_item)
                                            if text:
                                                parsed = parse_items_text(text)
                                                if parsed:
                                                    content_text = parsed
                                                    print(f"[COPY HANDLER] ✓ Conteúdo encontrado em Section>TextDisplay!")
                                                    break
                                    if content_text:
                                        break
                                
                                if content_text:
                                    break
                        else:
                            print(f"[COPY HANDLER] Container sem children acessíveis")
                        
                        if content_text:
                            break
                    
                    # Verificar se é ActionRow (pode conter Container)
                    elif isinstance(component_row, disnake.ui.ActionRow):
                        print(f"[COPY HANDLER] ActionRow encontrado")
                        if hasattr(component_row, 'children'):
                            for child in component_row.children:
                                if isinstance(child, disnake.ui.Container):
                                    if hasattr(child, 'children'):
                                        for item in child.children:
                                            if isinstance(item, disnake.ui.TextDisplay):
                                                text = extract_text_from_textdisplay(item)
                                                if text:
                                                    parsed = parse_items_text(text)
                                                    if parsed:
                                                        content_text = parsed
                                                        print(f"[COPY HANDLER] ✓ Conteúdo encontrado em ActionRow>Container>TextDisplay!")
                                                        break
                                            if content_text:
                                                break
                                    if content_text:
                                        break
                    
                    if content_text:
                        break
                        
            except Exception as e:
                # Log do erro para debug
                print(f"[COPY HANDLER] Erro ao extrair conteúdo do container: {e}")
                import traceback
                traceback.print_exc()
                pass
        
        # Se não encontrou o conteúdo, tentar ler do arquivo anexado na mensagem atual
        if not content_text and inter.message.attachments:
            try:
                for attachment in inter.message.attachments:
                    if attachment.filename.endswith('.txt'):
                        file_content = await attachment.read()
                        content_text = file_content.decode('utf-8').strip()
                        if content_text:
                            break
            except Exception as e:
                print(f"Erro ao ler arquivo anexado: {e}")
                pass
        
        # Se ainda não encontrou, buscar em mensagens anteriores (caso arquivo tenha sido enviado separadamente)
        if not content_text:
            try:
                print(f"[COPY HANDLER] Buscando em mensagens anteriores...")
                # Buscar nas últimas 10 mensagens do canal (aumentado para garantir)
                async for message in inter.channel.history(limit=10):
                    # Verificar se é mensagem do bot
                    if message.author == self.bot.user:
                        # Primeiro tentar arquivos
                        if message.attachments:
                            for attachment in message.attachments:
                                # Aceitar qualquer arquivo .txt
                                if attachment.filename.endswith('.txt'):
                                    try:
                                        file_content = await attachment.read()
                                        content_text = file_content.decode('utf-8').strip()
                                        if content_text:
                                            print(f"[COPY HANDLER] ✓ Conteúdo encontrado em arquivo de mensagem anterior!")
                                            break
                                    except Exception as e:
                                        print(f"[COPY HANDLER] Erro ao ler arquivo: {e}")
                                        continue
                        
                        # Se não encontrou em arquivo, tentar extrair de componentes/embeds da mensagem
                        if not content_text:
                            # Tentar embeds
                            if message.embeds:
                                for embed in message.embeds:
                                    for field in embed.fields:
                                        if "Seus Itens" in field.name or "Itens" in field.name:
                                            content_text = field.value.strip()
                                            if content_text.startswith("*") and content_text.endswith("*"):
                                                content_text = content_text[1:-1].strip()
                                            if content_text:
                                                print(f"[COPY HANDLER] ✓ Conteúdo encontrado em embed de mensagem anterior!")
                                                break
                                    if content_text:
                                        break
                            
                            # Tentar componentes (mesma lógica de antes)
                            if not content_text and message.components:
                                try:
                                    for component_row in message.components:
                                        if isinstance(component_row, disnake.ui.Container):
                                            if hasattr(component_row, 'children'):
                                                for item in component_row.children:
                                                    if isinstance(item, disnake.ui.TextDisplay):
                                                        # Tentar extrair texto
                                                        text = ""
                                                        for attr in ['content', 'text', '_text', '_content', 'value']:
                                                            if hasattr(item, attr):
                                                                try:
                                                                    val = getattr(item, attr)
                                                                    if val:
                                                                        text = str(val)
                                                                        break
                                                                except:
                                                                    pass
                                                        
                                                        if text and "Seus Itens" in text:
                                                            # Extrair conteúdo após "Seus Itens"
                                                            lines = text.split('\n')
                                                            content_lines = []
                                                            found_items = False
                                                            for line in lines:
                                                                if line.strip().startswith('#'):
                                                                    if "Seus Itens" in line:
                                                                        found_items = True
                                                                        parts = line.split("Seus Itens", 1)
                                                                        if len(parts) > 1:
                                                                            remaining = parts[1].strip().lstrip('#').lstrip('-').strip()
                                                                            if remaining:
                                                                                content_lines.append(remaining)
                                                                    continue
                                                                if found_items:
                                                                    line_clean = line.strip().lstrip('-').strip()
                                                                    if line_clean:
                                                                        content_lines.append(line_clean)
                                                                elif "Seus Itens" in line:
                                                                    found_items = True
                                                                    parts = line.split("Seus Itens", 1)
                                                                    if len(parts) > 1:
                                                                        remaining = parts[1].strip().lstrip('#').lstrip('-').strip()
                                                                        if remaining:
                                                                            content_lines.append(remaining)
                                                            
                                                            if content_lines:
                                                                content_text = '\n'.join(content_lines)
                                                                print(f"[COPY HANDLER] ✓ Conteúdo encontrado em componentes de mensagem anterior!")
                                                                break
                                                    if content_text:
                                                        break
                                                if content_text:
                                                    break
                                except Exception as e:
                                    print(f"[COPY HANDLER] Erro ao processar componentes: {e}")
                                    pass
                    
                    if content_text:
                        break
            except Exception as e:
                print(f"[COPY HANDLER] Erro ao buscar em mensagens anteriores: {e}")
                import traceback
                traceback.print_exc()
                pass
        
        if not content_text:
            await inter.response.send_message(
                f"{emoji.wrong} Não foi possível encontrar o conteúdo para copiar.",
                ephemeral=True
            )
            return
        
        # Verificar se o conteúdo é maior que 2000 caracteres
        if len(content_text) > 2000:
            # Criar arquivo .txt
            file_content = io.BytesIO(content_text.encode('utf-8'))
            file = disnake.File(fp=file_content, filename="conteudo_copiado.txt")
            
            await inter.response.send_message(
                file=file,
                ephemeral=True
            )
        else:
            # Enviar mensagem efêmera com apenas o conteúdo (sem code blocks)
            await inter.response.send_message(
                content_text,
                ephemeral=True
            )


def setup(bot: commands.Bot):
    bot.add_cog(CopyProductHandler(bot))
