"""Consulta os avisos do INMET válidos no RS; produz relatório, nunca publica."""
import json, os
from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
TZ=ZoneInfo("America/Sao_Paulo")
URL="https://apiprevmet3.inmet.gov.br/avisos/ativos"
IDAP="https://idapfile.mdr.gov.br/idap/api/rss/cap"
PORTAL="https://defesacivil.rs.gov.br/avisos-e-boletins"
NS="{urn:oasis:names:tc:emergency:cap:1.2}"
# Tudo o que o INMET emite e afeta o RS: temporal, granizo, chuva volumosa,
# alagamento/inundação, vento (incl. tornado e ciclone), frio, calor e mar.
PALAVRAS=("tempestade","temporal","chuva","acumulado","granizo","inunda","alaga","enchente","deslizamento",
          "vendaval","ventos costeiros","tornado","ciclone","ressaca","geada","onda de frio","declínio de temperatura",
          "declinio de temperatura","onda de calor","baixa umidade","neve")
def lista(v):
    if isinstance(v,list):return [str(s).strip() for s in v]
    return [s.strip() for s in str(v or "").split(",") if s.strip()]
def instante(data,hora):
    if not data or not hora:return None
    try:return datetime.fromisoformat(str(data)[:10]+"T"+str(hora)[:5]).replace(tzinfo=TZ)
    except ValueError:return None
def normalizar(payload,agora=None):
    if not isinstance(payload,dict) or not isinstance(payload.get("hoje"),list) or not isinstance(payload.get("futuro"),list):
        raise ValueError("Esquema do INMET mudou; publicação bloqueada")
    agora=agora or datetime.now(TZ)
    por_id={}
    for a in payload["hoje"]+payload["futuro"]:
        if not isinstance(a,dict):continue
        id_=str(a.get("id_aviso") or a.get("id") or "")
        if id_ and (id_ not in por_id or int(a.get("id_sequencia") or 0)>int(por_id[id_].get("id_sequencia") or 0)):
            por_id[id_]=a
    out=[]
    for id_,a in por_id.items():
        if a.get("encerrado"):continue
        ibges=[c for c in lista(a.get("geocodes")) if c.startswith("43")]
        if not ibges:continue
        ini,fim=instante(a.get("data_inicio"),a.get("hora_inicio")),instante(a.get("data_fim"),a.get("hora_fim"))
        if not ini or not fim or not agora<fim or ini>agora+timedelta(hours=24) or ini>=fim:continue
        tipo=str(a.get("descricao") or "")
        if not any(s in tipo.lower() for s in PALAVRAS):continue
        out.append({"id_aviso":id_,"id_sequencia":int(a.get("id_sequencia") or 0),"tipo":tipo,"severidade":a.get("severidade"),
                    "inicio":ini.isoformat(),"fim":fim.isoformat(),
                    "municipios_rs":len(ibges),"geocodes_rs":ibges,"municipios_texto":str(a.get("municipios") or ""),
                    "riscos":a.get("riscos"),"instrucoes":a.get("instrucoes"),"fonte":URL,"orgao":"INMET"})
    return out
def normalizar_cap(raw, agora):
    root=ET.fromstring(raw)
    alertas=list(root.iter(NS+"alert"))
    if not alertas and root.tag not in ("{http://www.w3.org/2005/Atom}feed","rss"):
        raise ValueError("Formato IDAP não reconhecido")
    out=[]
    for a in alertas:
        def campo(n): return (a.findtext(NS+n) or "").strip()
        if campo("status")!="Actual" or campo("scope")!="Public" or campo("msgType") not in ("Alert","Update"):
            continue
        for info in a.findall(NS+"info"):
            def d(n): return (info.findtext(NS+n) or "").strip()
            if "defesa civil" not in (d("senderName")+" "+campo("sender")).casefold():
                continue
            tipo=d("event")
            if not any(k in tipo.casefold() for k in PALAVRAS): continue
            sev={"Minor":"Perigo potencial","Moderate":"Perigo potencial","Severe":"Perigo","Extreme":"Grande perigo"}.get(d("severity"))
            if not sev: continue
            try:
                ini=datetime.fromisoformat(d("onset") or d("effective") or campo("sent"))
                fim=datetime.fromisoformat(d("expires"))
                if not ini.tzinfo or not fim.tzinfo or not agora<fim or ini>=fim or ini>agora+timedelta(hours=24): continue
            except ValueError: continue
            codes=set()
            for area in info.findall(NS+"area"):
                for geo in area.findall(NS+"geocode"):
                    nome=(geo.findtext(NS+"valueName") or "").casefold()
                    val=(geo.findtext(NS+"value") or "").strip()
                    if ("ibge" in nome or "brasil" in nome) and re.fullmatch(r"43\d{5}",val):
                        codes.add(val)
            if not codes or not campo("identifier"): continue
            out.append(dict(id_aviso="idap:"+campo("identifier"),tipo=tipo,severidade=sev,
                inicio=ini.astimezone(TZ).isoformat(),fim=fim.astimezone(TZ).isoformat(),
                municipios_rs=len(codes),geocodes_rs=sorted(codes),municipios_texto="",
                riscos=d("description"),instrucoes=d("instruction"),fonte=IDAP,orgao="Defesa Civil"))
    return out

def consultar_defesa_civil(agora):
    resultado={"portal":PORTAL,"feed":IDAP,"status":"indisponivel","avisos":[]}
    try:
        req=Request(IDAP,headers={"User-Agent":"previsaors/1.0"})
        with urlopen(req,timeout=35) as response:
            raw=response.read(30_000_001)
            if len(raw)>30_000_000: raise ValueError("Feed excedeu limite")
        resultado.update(status="ok",avisos=normalizar_cap(raw,agora))
    except Exception as e:
        resultado["erro"]=type(e).__name__
    try:
        req=Request(PORTAL,headers={"User-Agent":"previsaors/1.0"})
        with urlopen(req,timeout=25) as response:
            body=response.read(2_000_000).decode("utf-8",errors="replace")
        from html.parser import HTMLParser
        from urllib.parse import urljoin
        class Links(HTMLParser):
            def __init__(self): super().__init__(); self.links=[]
            def handle_starttag(self,tag,attrs):
                href=dict(attrs).get("href","")
                if tag=="a" and "aviso" in href.casefold() and ".pdf" in href.casefold():
                    u=urljoin(PORTAL,href)
                    if urlparse(u).hostname in ("defesacivil.rs.gov.br","www.defesacivil.rs.gov.br","admin.defesacivil.rs.gov.br"):
                        self.links.append(u)
        parser=Links();parser.feed(body)
        resultado["boletins_para_revisao"]=list(dict.fromkeys(parser.links))[:8]
        resultado["portal_status"]="ok"
    except Exception as e: resultado["portal_status"]="indisponivel"
    return resultado

def main():
    req=Request(URL,headers={"User-Agent":"previsaors/1.0 (github.com/pabloramoa-dev/previsao-rs)"})
    with urlopen(req,timeout=35) as r:payload=json.load(r)
    now=datetime.now(TZ)
    avisos=normalizar(payload,now)
    defesa=consultar_defesa_civil(now)
    avisos+=defesa["avisos"]
    out=Path("output/alertas_rs.json");out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"consultado_em":now.isoformat(),"avisos":avisos,"autopublicacao":"ver alerta_auto_rs","defesa_civil":defesa,"verificacao_hidrologica":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"## Monitoramento de alertas RS — {now:%d/%m/%Y %H:%M}","",f"- Fonte: [INMET]({URL})",f"- Avisos oficiais vigentes ou iniciando em até 24h no RS: **{len(avisos)}**",f"- Defesa Civil (IDAP): {defesa['status']}; portal: {defesa.get('portal_status')}; avisos CAP com IBGE RS: {len(defesa['avisos'])}",f"- Boletins estaduais para revisão: {PORTAL}","- Publicação: decidida por scripts/alerta_auto_rs.py (só aviso oficial inédito)",""]
    lines += [f"- {a['tipo']} — {a['severidade']} — {a['municipios_rs']} municípios — até {a['fim']}" for a in avisos]
    if defesa["status"]!="ok": lines.append("ATENÇÃO: fonte IDAP indisponível; ausência de alertas não confirmada.")
    if not avisos:lines.append("Nenhum aviso elegível nas fontes consultadas; não é garantia de ausência de perigo. Boletins estaduais não estruturados exigem revisão.")
    txt="\n".join(lines)+"\n"
    print(txt)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:f.write(txt)
if __name__=="__main__":main()
