"""Roteiro em dupla: previsao *real* do MET Norway gerada na hora da renderizacao."""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml

FUSO = ZoneInfo("America/Sao_Paulo")
REGIOES = [
    ("Metropolitana e Vales", "porto_alegre"),
    ("Serra e Campos de Cima", "caxias_do_sul"),
    ("Litoral Norte", "tramandai"),
    ("Sul e Campanha", "pelotas"),
    ("Centro e Fronteira", "santa_maria"),
    ("Norte e Noroeste", "passo_fundo"),
]

def montar(snapshot, saida):
    agora = dt.datetime.now(FUSO)
    gerado = dt.datetime.fromisoformat(snapshot["generated_at"].replace("Z","+00:00"))
    if gerado.tzinfo is None:
        raise ValueError("Snapshot sem fuso e procedencia")
    if (agora - gerado.astimezone(FUSO)).total_seconds() > 10800:
        raise ValueError("Previsao com mais de 3 horas: nao renderizar")
    met = [s for s in snapshot.get("sources",[]) if "met_no" in s.get("name","").lower() or "met norway" in s.get("name","").lower()]
    if not met or not any(s.get("status") in ("ok","success","partial") for s in met):
        raise ValueError("MET Norway indisponivel: nao substituir por numeros ficticios")
    dia = snapshot["forecast"].get("tomorrow") or {}
    data = dt.date.fromisoformat(dia["date"])
    if data != agora.date() + dt.timedelta(days=1):
        raise ValueError(f"Data incorreta: esperado amanha, recebido {data}")
    por_id = {l["id"]:l for l in dia["locations"]}
    cidades=[]
    for regiao, ident in REGIOES:
        l = por_id.get(ident)
        if not l or l.get("min_c") is None or l.get("max_c") is None or l.get("rain_mm") is None:
            raise ValueError(f"Dados insuficientes em {regiao}: abortar o video")
        cidades.append(dict(regiao=regiao,nome=l["name"],
                           mi=round(float(l["min_c"])),ma=round(float(l["max_c"])),
                           mm=round(float(l["rain_mm"]),1)))

    nome_dia=["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"][data.weekday()]
    # A primeira frase JÁ é previsão; nada de "olá", nomes ou explicação do canal.
    # A estética de abertura do HyperFrames permanece, mas com informação útil.
    falas=[]
    for i,c in enumerate(cidades):
        mm=c["mm"]
        chuva = (f"{mm:g} milímetros de chuva" if mm>=0.5
                 else "sem chuva significativa")
        falas.append({
            "cena":"abertura" if i == 0 else "numero",
            "quem":"bia" if i%2==0 else "bira",
            "icone":"chuva" if mm>=0.5 else "sol",
            "numero":f'{c["ma"]}°C',
            "sub":c["nome"].upper(),
            "local":f'MÍN {c["mi"]}°C · CHUVA {mm:g} mm',
            "fala":(f'{c["nome"]} terá mínima de {c["mi"]} e máxima de {c["ma"]} graus, '
                    + (f'com previsão de {mm:g} milímetros de chuva.' if mm>=0.5 else 'sem chuva significativa.'))
                   if i == 0 else f'{c["nome"]}: de {c["mi"]} a {c["ma"]} graus, {chuva}.'
        })
    destaque=max(cidades,key=lambda c:c["mm"])
    if destaque["mm"]>=1:
        falas.append({
            "cena":"frase","quem":"bia",
            "fala":f'Maior chuva entre esses pontos: {destaque["nome"]}, {destaque["mm"]:g} milímetros previstos.'
        })
    falas.append({"cena":"cta","quem":"bira","chamada":"PREVISÃO RS",
                  "sub":"@previsaors · Rio Grande do Sul",
                  "fala":"Compartilhe esta previsão e siga o Previsão RS!"})
    titulo="PREVISÃO DO RS"
    report=f"Previsão para {data.isoformat()} • atualização {agora:%d/%m/%Y %H:%M}\n"
    report+="Fonte: MET Norway, previsão por ponto; não é aviso oficial de tempo severo\n"
    report+="\n".join(f'{c["regiao"]}: {c["nome"]} {c["mi"]}° a {c["ma"]}° · {c["mm"]:g} mm' for c in cidades)
    saida.parent.mkdir(parents=True,exist_ok=True)
    doc={
      "tipo":"aviso","apresenta":"bia","validade":(agora+dt.timedelta(hours=4)).isoformat(),
      "titulo":titulo,"etiquetas":[f"AMANHÃ · {data.day:02d}/{data.month:02d}","DADOS REAIS · MET NORWAY"],
      "selo":"PREVISÃO RS","ceu":"nublado","trilha":True,
      "fonte":"MET Norway — previsão consultada no dia da renderização (CC BY 4.0)",
      "ticker":[f'{c["nome"].upper()}: {c["mi"]}° A {c["ma"]}° · {c["mm"]:g} MM' for c in cidades[:3]],
      "falas":falas,
      "legenda":f"🌦️ Previsão para {nome_dia}, {data:%d/%m/%Y} no Rio Grande do Sul.\n"+report+"\n\n@previsaors #PrevisaoRS #TempoRS"
    }
    saida.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=110),encoding="utf-8")
    saida.with_suffix(".txt").write_text(report+"\n",encoding="utf-8")
    print(report)
    print(f"Roteiro preparado: {saida}")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="output/snapshot.json")
    p.add_argument("--out",default="output/piloto_rs.yaml")
    a=p.parse_args()
    montar(json.loads(Path(a.snapshot).read_text(encoding="utf-8")),Path(a.out))
