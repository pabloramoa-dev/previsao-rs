"""Consulta os avisos do INMET válidos no RS; produz relatório, nunca publica."""
import json, os
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
TZ=ZoneInfo("America/Sao_Paulo")
URL="https://apiprevmet3.inmet.gov.br/avisos/ativos"
PALAVRAS=("tempestade","chuvas intensas","acumulado de chuva","ventos costeiros","vendaval","granizo","geada","onda de frio","ciclone")
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
        id_=str(a.get("id_aviso") or "")
        if id_ and (id_ not in por_id or int(a.get("id_sequencia") or 0)>int(por_id[id_].get("id_sequencia") or 0)):
            por_id[id_]=a
    out=[]
    for id_,a in por_id.items():
        if a.get("encerrado"):continue
        ibges=[c for c in lista(a.get("geocodes")) if c.startswith("43")]
        if not ibges:continue
        ini,fim=instante(a.get("data_inicio"),a.get("hora_inicio")),instante(a.get("data_fim"),a.get("hora_fim"))
        if not ini or not fim or not ini<=agora<=fim:continue
        tipo=str(a.get("descricao") or "")
        if not any(s in tipo.lower() for s in PALAVRAS):continue
        out.append({"id_aviso":id_,"tipo":tipo,"severidade":a.get("severidade"),"inicio":ini.isoformat(),"fim":fim.isoformat(),
                    "municipios_rs":len(ibges),"geocodes_rs":ibges,"fonte":URL})
    return out
def main():
    req=Request(URL,headers={"User-Agent":"previsaors/1.0 (github.com/pabloramoa-dev/previsao-rs)"})
    with urlopen(req,timeout=35) as r:payload=json.load(r)
    now=datetime.now(TZ)
    avisos=normalizar(payload,now)
    out=Path("output/alertas_rs.json");out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"consultado_em":now.isoformat(),"avisos":avisos,"autopublicacao":False,"verificacao_hidrologica":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"## Monitoramento de alertas RS — {now:%d/%m/%Y %H:%M}","",f"- Fonte: [INMET]({URL})",f"- Avisos oficiais vigentes e identificados no RS: **{len(avisos)}**","- Defesa Civil RS, ClimaRS e rios: exigem verificação editorial separada","- Publicação automática: desativada",""]
    lines += [f"- {a['tipo']} — {a['severidade']} — {a['municipios_rs']} municípios — até {a['fim']}" for a in avisos]
    if not avisos:lines.append("Nenhum aviso elegível na consulta INMET; não é garantia de ausência de perigo.")
    txt="\n".join(lines)+"\n"
    print(txt)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:f.write(txt)
if __name__=="__main__":main()
