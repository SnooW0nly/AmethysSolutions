from __future__ import annotations
import io, asyncio
from datetime import datetime
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .helpers import (
    load_config, save_config, update_config_stat,
    load_contas, save_contas, add_conta, add_contas_bulk, update_conta, contar_contas_por_status, exportar_contas_nitradas, limpar_contas_processadas, reset_contas_travadas,
    load_links, add_link, get_links_ativos, delete_link,
    load_logs, get_logs_recentes, limpar_logs, add_log, set_bot,
    decrypt_sensitive, encrypt_sensitive,
)
from .utils import validate_token, check_nitro_eligibility, NitroAPIClient, start_workers, stop_workers, get_worker_stats, workers_running

def _mode():  return db.get_document("custom_mode").get("mode","components")
def _color():
    c=db.get_document("custom_colors") or {}
    return {"color":int(c.get("primary","#5865F2").replace("#",""),16)} if c.get("primary") else {}
def _accent():
    c=db.get_document("custom_colors") or {}; h=c.get("primary")
    return {"accent_colour":disnake.Colour(int(h.replace("#",""),16))} if h else {}
async def _edit(inter,panel,mode):
    if mode=="embed": await inter.edit_original_message(content=None,**panel)
    else:
        flags=panel.pop("flags",disnake.MessageFlags(is_components_v2=True))
        await inter.edit_original_message(**panel,flags=flags)

ST_EMOJI={"pendente":"🟡","processando":"🔵","nitrada":"🟢","inelegivel":"🟠","falha":"🔴"}
LV_EMOJI={"info":"ℹ️","success":"✅","error":"❌","warn":"⚠️"}

# ── PAINEL PRINCIPAL ──────────────────────────────────────
async def _painel(mode, api=None):
    cfg=load_config(); e=cfg.get("enabled",False)
    ct=contar_contas_por_status(); st=get_worker_stats()
    api_ok=False
    if api:
        try: r=await api.health(); api_ok=r.get("ok",False)
        except: pass
    status_api=f"{f'{emoji.on}' if api_ok else f'{emoji.off}'} API"
    body=(f"{f'{emoji.on}' if e else f'{emoji.off}'} **Status:** `{'Ativo' if e else 'Inativo'}` | {status_api}\n"
          f"{emoji.settings} **Workers:** `{cfg.get('workers',2)}` rodando:`{st.get('workers',0)}` | Fila:`{st.get('fila',{}).get('na_fila',0)}`\n\n"
          f"{emoji.member} Pendentes:`{ct['pendente']}` Nitradas:`{ct['nitrada']}` Inelegíveis:`{ct['inelegivel']}` Falhas:`{ct['falha']}`\n"
          f"{emoji.link} Links/Trial ativos:`{len(get_links_ativos())}`\n\n"
          f"-# Nitradas total:`{cfg.get('total_nitradas',0)}`")
    off=not e
    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Desativar" if e else "Ativar",
                style=disnake.ButtonStyle.red if e else disnake.ButtonStyle.green,
                custom_id="Nitro_Toggle",
                emoji=emoji.power,
            ),
            disnake.ui.Button(label="Contas",  emoji=emoji.member, style=disnake.ButtonStyle.blurple, custom_id="Nitro_PainelContas", disabled=off),
            disnake.ui.Button(label="Nitros",  emoji=emoji.link, style=disnake.ButtonStyle.grey,    custom_id="Nitro_PainelLinks",  disabled=off),
            disnake.ui.Button(label="Logs",    emoji=emoji.textc, style=disnake.ButtonStyle.grey,    custom_id="Nitro_PainelLogs",   disabled=off),
        ),
    ]
    back = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                          custom_id="LojaExtensoes_Panel")
    )
    if mode == "embed":
        em = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}",
            description=f"-# Painel > Loja > Extensão > **Nitrada Automática**\n\n{body}",
            **_color()
        )
        return {"embed": em, "components": rows + [back]}
    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Extensão > **Nitrada Automática**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
            ),
            back,
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }

# ── PAINEL CONTAS ─────────────────────────────────────────
def _painel_contas(mode,page=0):
    contas=load_contas(); stats=contar_contas_por_status(); per=10
    pag=contas[page*per:(page+1)*per]; total_p=max(1,(len(contas)+per-1)//per)
    links=get_links_ativos()
    link_info=", ".join(f"{'Trial' if l.get('tipo')=='trial' else l['nome']}" for l in links) or "nenhum"
    sl=f"🟡`{stats['pendente']}` 🔵`{stats['processando']}` 🟢`{stats['nitrada']}` 🟠`{stats['inelegivel']}` 🔴`{stats['falha']}`"
    if not contas: ct="-# Nenhuma conta cadastrada."
    else:
        lines=[f"{ST_EMOJI.get(c['status'],'⚪')} `{c.get('username') or c.get('token_raw','')[:15]+'...'}` — {c['status']}" for c in pag]
        ct="\n".join(lines)+f"\n\n-# Pág {page+1}/{total_p} | Total:{len(contas)}"
    body=f"**Status:** {sl}\n**Nitros ativos:** {link_info}\n\n{ct}"
    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar",   emoji=emoji.plus,   style=disnake.ButtonStyle.green,  custom_id="Nitro_Contas_Add"),
            disnake.ui.Button(label="Upload .txt", emoji=emoji.dir,          style=disnake.ButtonStyle.blurple, custom_id="Nitro_Contas_Upload"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="◀",        style=disnake.ButtonStyle.grey, custom_id=f"Nitro_Contas_Prev:{max(0,page-1)}",        disabled=page==0),
            disnake.ui.Button(label="Atualizar", emoji=emoji.reload, style=disnake.ButtonStyle.grey, custom_id="Nitro_Contas_Refresh"),
            disnake.ui.Button(label="▶",        style=disnake.ButtonStyle.grey, custom_id=f"Nitro_Contas_Next:{min(total_p-1,page+1)}", disabled=page>=total_p-1),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Verificar Elegibilidade", emoji=emoji.search, style=disnake.ButtonStyle.grey, custom_id="Nitro_Contas_Verificar"),
            disnake.ui.Button(label="Limpar Falhas",           emoji=emoji.delete, style=disnake.ButtonStyle.red,  custom_id="Nitro_Contas_LimparFalhas"),
        ),
    ]
    back = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Nitro_PainelPrincipal")
    )
    if mode == "embed":
        return {
            "embed": disnake.Embed(title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}", description=f"-# Painel > Loja > Extensão > Nitrada Automática> **Contas**\n\n{body}", **_color()),
            "components": rows + [back],
        }
    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Extensão > Nitrada Automática > **Contas**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            back,
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }

class AddContaModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(title="Adicionar Conta",custom_id="Nitro_Contas_AddModal",components=[
            disnake.ui.TextInput(label="Token Discord",custom_id="token",style=disnake.TextInputStyle.paragraph,required=True,max_length=200,placeholder="Token da conta..."),
            disnake.ui.TextInput(label="Email (opcional)",custom_id="email",required=False,max_length=100),
            disnake.ui.TextInput(label="Senha (opcional)",custom_id="senha",required=False,max_length=100),
        ])
    async def callback(self,inter:disnake.ModalInteraction):
        token=inter.text_values["token"].strip(); email=inter.text_values.get("email","").strip(); senha=inter.text_values.get("senha","").strip()
        info=await validate_token(token)
        if not info["valid"]: await inter.response.send_message(f"{emoji.wrong} Token inválido: {info.get('erro','?')}",ephemeral=True); return
        cid=add_conta(token,email,senha)
        if not cid: await inter.response.send_message(f"{emoji.warn} Token já cadastrado.",ephemeral=True); return
        update_conta(cid,{"username":info.get("username",""),"user_id":info.get("user_id","")})
        add_log("info",f"Conta adicionada: {info.get('username','?')}")
        mode=_mode(); await (embed_message if mode=="embed" else message).wait(inter,send=False)
        await _edit(inter,_painel_contas(mode),mode)
        await inter.followup.send(f"{emoji.correct} Conta **{info.get('username','?')}** adicionada!",ephemeral=True)

# ── PAINEL NITROS/LINKS ───────────────────────────────────
def _painel_links(mode):
    links=load_links()
    body="-# Nenhum link/trial." if not links else "\n".join(
        f"{f'{emoji.on}' if l.get('ativo',True) else f'{emoji.off}'} **{l['nome']}** — {'Trial 2 semanas' if l.get('tipo')=='trial' else 'Link promocional'} | Usos:`{l.get('total_usado',0)}`" for l in links)
    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar", emoji=emoji.plus, style=disnake.ButtonStyle.green, custom_id="Nitro_Links_Add"),
            disnake.ui.Button(label="Atualizar", emoji=emoji.reload, style=disnake.ButtonStyle.grey,  custom_id="Nitro_Links_Refresh"),
        )
    ]
    back = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Nitro_PainelPrincipal")
    )
    if mode == "embed":
        return {
            "embed": disnake.Embed(title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}", description=f"-# Painel > Loja > Extensão > Nitrada Automática**Nitros**\n\n{body}", **_color()),
            "components": rows + [back],
        }
    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Extensão > Nitrada Automática > **Nitros**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
            ),
            back,
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }

class AddLinkModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(title="Adicionar Link ou Trial",custom_id="Nitro_Links_AddModal",components=[
            disnake.ui.TextInput(label="Nome",custom_id="nome",required=True,max_length=50),
            disnake.ui.TextInput(label="URL (vazio = Trial 2 semanas)",custom_id="url",required=False,max_length=500,placeholder="https://discord.com/billing/promotions/..."),
            disnake.ui.TextInput(label="Plan ID (opcional)",custom_id="plan_id",required=False,max_length=50),
            disnake.ui.TextInput(label="Duração em meses",custom_id="meses",required=False,max_length=2,value="3"),
        ])
    async def callback(self,inter:disnake.ModalInteraction):
        nome=inter.text_values["nome"].strip(); url=inter.text_values["url"].strip()
        plan_id=inter.text_values.get("plan_id","").strip(); meses=int(inter.text_values.get("meses","3") or "3")
        tipo="trial" if not url else "link"
        add_link(nome,url,"trial" if not url else "promocional",meses,plan_id,tipo)
        add_log("info",f"Nitro adicionado: {nome}")
        mode=_mode(); await inter.response.edit_message(**_painel_links(mode))
        await inter.followup.send(f"{emoji.correct} Adicionado!",ephemeral=True)

# ── PAINEL LOGS (select canal) ────────────────────────────
def _painel_logs(mode, guild: disnake.Guild = None):
    cfg=load_config(); ch_id=cfg.get("log_channel_id","")
    canal=f"{emoji.textc} Canal atual: <#{ch_id}>" if ch_id else f"{emoji.textc} Canal: _não configurado_"
    body=f"{canal}\n\n-# Selecione o canal abaixo onde os logs serão enviados automaticamente."
    options=[]
    if guild:
        for ch in sorted(guild.text_channels, key=lambda c: c.position)[:25]:
            options.append(disnake.SelectOption(label=f"#{ch.name}",value=str(ch.id),default=str(ch.id)==ch_id))
    if not options:
        options=[disnake.SelectOption(label="Nenhum canal disponível",value="none",default=False)]
    rows = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="Nitro_Logs_SelectCanal",
                placeholder="Selecione o canal de logs...",
                options=options,
            )
        )
    ]
    back = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey, custom_id="Nitro_PainelPrincipal")
    )
    if mode == "embed":
        return {
            "embed": disnake.Embed(title="{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}", description=f"-# Painel > Loja > Extensão > Nitrada Automática > **Logs**\n\n{body}", **_color()),
            "components": rows + [back],
        }
    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Extensão > Nitrada Automática > **Logs**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
            ),
            back,
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }

# ── COG PRINCIPAL ─────────────────────────────────────────
class NitroAutomaticoCog(commands.Cog):
    def __init__(self,bot):
        self.bot=bot; self.api=None; self._uploads={}

    @property
    def api_client(self): return self.api

    @commands.Cog.listener()
    async def on_ready(self):
        set_bot(self.bot)
        if self.api: await self.api.close()
        self.api=NitroAPIClient()
        reset_contas_travadas()
        if load_config().get("enabled") and not workers_running():
            try:
                h=await self.api.health()
                if h.get("ok"):
                    await start_workers(self.api); add_log("info","Workers retomados")
                else:
                    cfg=load_config(); cfg["enabled"]=False; save_config(cfg)
                    add_log("warn","API offline — sistema desativado no startup")
            except:
                cfg=load_config(); cfg["enabled"]=False; save_config(cfg)

    @commands.Cog.listener("on_button_click")
    async def on_button(self,inter:disnake.MessageInteraction):
        cid=inter.component.custom_id or ""; mode=_mode()

        if cid=="Nitro_PainelPrincipal":
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,await _painel(mode,self.api),mode)

        elif cid=="Nitro_Toggle":
            cfg=load_config(); enabling=not cfg.get("enabled",False)
            if enabling:
                try: h=await self.api.health(); api_ok=h.get("ok",False)
                except: api_ok=False
                if not api_ok:
                    await inter.response.send_message(f"{emoji.alert} A API está **offline**.\n-# contate um admin urgentemente.",ephemeral=True); return
            cfg["enabled"]=enabling; save_config(cfg)
            if enabling: await start_workers(self.api)
            else: await stop_workers()
            await inter.response.edit_message(**await _painel(mode,self.api))

        elif cid=="Nitro_PainelContas":
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_contas(mode),mode)
        elif cid=="Nitro_Contas_Add": await inter.response.send_modal(AddContaModal())
        elif cid=="Nitro_Contas_Refresh":
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_contas(mode),mode)
        elif cid.startswith("Nitro_Contas_Prev:") or cid.startswith("Nitro_Contas_Next:"):
            page=int(cid.split(":")[1])
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_contas(mode,page),mode)
        elif cid=="Nitro_Contas_Upload":
            self._uploads[inter.user.id]=True
            try:
                dm=await inter.user.create_dm()
                await dm.send("**Upload de Contas**\nEnvie `.txt` com tokens, um por linha.\nFormato: `token:email:senha` (email/senha opcionais) | Máx 5000 linhas.")
                await inter.response.send_message(f"{emoji.correct} Verifique sua DM!",ephemeral=True)
            except disnake.Forbidden:
                await inter.response.send_message(f"{emoji.wrong} Não foi possível abrir DM.",ephemeral=True); self._uploads.pop(inter.user.id,None)
        elif cid=="Nitro_Contas_Verificar":
            await inter.response.defer(ephemeral=True)
            pendentes=[c for c in load_contas() if c["status"]=="pendente"]; v=e=0
            for c in pendentes:
                try:
                    r=await check_nitro_eligibility(c.get("token_raw",""))
                    update_conta(c["id"],{"elegivel":r["elegivel"],"motivo_inelegivel":r.get("motivo",""),"status":"pendente" if r["elegivel"] else "inelegivel"})
                    v+=1; e+=r["elegivel"]; await asyncio.sleep(1)
                except: pass
            await inter.followup.send(f"{emoji.correct} {v} verificadas. 🟢 {e} elegíveis.",ephemeral=True)
        elif cid=="Nitro_Contas_LimparFalhas":
            contas=load_contas(); antes=len(contas)
            save_contas([c for c in contas if c["status"] not in ("falha","inelegivel")])
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_contas(mode),mode)
            await inter.followup.send(f"{emoji.correct} {antes-len(load_contas())} removidas.",ephemeral=True)

        elif cid=="Nitro_PainelLinks":
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_links(mode),mode)
        elif cid=="Nitro_Links_Add": await inter.response.send_modal(AddLinkModal())
        elif cid=="Nitro_Links_Refresh":
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_links(mode),mode)

        elif cid=="Nitro_PainelLogs":
            await (embed_message if mode=="embed" else message).wait(inter,send=False)
            await _edit(inter,_painel_logs(mode,inter.guild),mode)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self,inter:disnake.MessageInteraction):
        if inter.component.custom_id!="Nitro_Logs_SelectCanal": return
        val=inter.values[0]
        if val=="none": await inter.response.send_message("Nenhum canal disponível.",ephemeral=True); return
        cfg=load_config(); cfg["log_channel_id"]=val; save_config(cfg)
        add_log("info",f"Canal de logs configurado: <#{val}>")
        mode=_mode(); await inter.response.edit_message(**_painel_logs(mode,inter.guild))
        await inter.followup.send(f"{emoji.correct} Canal de logs definido para <#{val}>",ephemeral=True)

    @commands.Cog.listener("on_message")
    async def on_dm_upload(self,msg:disnake.Message):
        if msg.author.bot or not isinstance(msg.channel,disnake.DMChannel) or msg.author.id not in self._uploads: return
        if not msg.attachments: await msg.channel.send(f"{emoji.warn} Envie um `.txt`."); return
        txt=next((a for a in msg.attachments if a.filename.endswith(".txt")),None)
        if not txt: await msg.channel.send(f"{emoji.wrong} Apenas `.txt`."); return
        self._uploads.pop(msg.author.id,None)
        try:
            raw=await txt.read()
            try: content=raw.decode("utf-8")
            except: content=raw.decode("latin-1")
            lines=[l.strip() for l in content.splitlines() if l.strip()][:5000]
            tokens=[]; emails=[]; senhas=[]
            for line in lines:
                p=line.split(":",2); tokens.append(p[0]); emails.append(p[1] if len(p)>1 else ""); senhas.append(p[2] if len(p)>2 else "")
            added=add_contas_bulk(tokens,emails,senhas)
            add_log("info",f"{added} contas importadas via upload")
            await msg.channel.send(f"{emoji.correct} **{added}** adicionadas! ({len(lines)-added} duplicadas)")
        except Exception as e:
            await msg.channel.send(f"{emoji.wrong} Erro: {e}")

def setup(bot):
    bot.add_cog(NitroAutomaticoCog(bot))

async def build_main_panel_async(mode,api_client=None): return await _painel(mode,api_client)