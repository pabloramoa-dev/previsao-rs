"""Alerta automático do RS (12h30): aviso oficial do INMET -> comunicado Bira + Bia.

Lê `output/alertas_rs.json` (gerado por `scripts.monitor_alertas_rs`) e decide
se há aviso INÉDITO para publicar. Só usa o que o INMET publicou: tipo,
severidade, validade, municípios, riscos e instruções. Nada é inventado: sem
aviso oficial vigente, não há Reel.

    python -m scripts.alerta_auto_rs decidir --alertas output/alertas_rs.json \
        --historico data/alertas_publicados.json --out comunicados/auto/alerta.yaml
    python -m scripts.alerta_auto_rs registrar --historico data/alertas_publicados.json \
        --decisao output/alerta_decisao.json --media-id 123

Contra repetição: o histórico guarda cada `id_aviso` já publicado. A mesma
ameaça só volta ao ar se o INMET subir a severidade (ex.: amarelo -> laranja).
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

TZ = ZoneInfo("America/Sao_Paulo")
ROOT = Path(__file__).resolve().parents[1]

NIVEL = {"perigo potencial": 1, "perigo": 2, "grande perigo": 3}
COR = {1: "AVISO AMARELO", 2: "AVISO LARANJA", 3: "AVISO VERMELHO"}
CEU = (("granizo", "tempestade"), ("tempestade", "tempestade"), ("temporal", "tempestade"),
       ("tornado", "tempestade"), ("vendaval", "tempestade"), ("ciclone", "tempestade"),
       ("chuva", "chuva"), ("acumulado", "chuva"), ("inunda", "chuva"), ("alaga", "chuva"),
       ("geada", "frio"), ("frio", "frio"), ("declínio", "frio"), ("declinio", "frio"),
       ("calor", "calor"), ("umidade", "calor"))


# ~2,5 palavras/s na voz da dupla + vinhetas: 95 palavras cabem em ~55 s.
MAX_PALAVRAS_ALERTA = 95


def nivel(sev) -> int:
    return NIVEL.get(str(sev or "").strip().casefold(), 1)


def _lista(v) -> list[str]:
    if isinstance(v, list):
        itens = v
    else:
        itens = re.split(r"[\n;]|(?<=\.)\s+", str(v or ""))
    out = []
    for i in itens:
        i = re.sub(r"\s+", " ", str(i)).strip(" -•.")
        if i:
            out.append(i)
    return out


def _unidades_para_fala(texto: str) -> str:
    texto = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)(?=\s*(?:mm|km)\s*/\s*h\b)",
                   r"de \1 a \2", texto, flags=re.IGNORECASE)
    texto = re.sub(r"(?<=\d)\s*mm\s*/\s*h\b", " milímetros por hora", texto, flags=re.IGNORECASE)
    return re.sub(r"(?<=\d)\s*km\s*/\s*h\b", " quilômetros por hora", texto, flags=re.IGNORECASE)


def nomes_ibge() -> dict[str, str]:
    """IBGE -> nome, a partir das cidades cadastradas do canal."""
    txt = (ROOT / "config" / "locais.yaml").read_text(encoding="utf-8")
    dados = yaml.safe_load(txt)
    cadastro = ROOT / 'data' / 'municipios_rs.json'
    out: dict[str, str] = json.loads(cadastro.read_text(encoding='utf-8'))['municipios'] if cadastro.exists() else {}

    def varrer(x):
        if isinstance(x, dict):
            if x.get("ibge") and x.get("name"):
                out[str(x["ibge"])] = str(x["name"])
            for v in x.values():
                varrer(v)
        elif isinstance(x, list):
            for v in x:
                varrer(v)
    varrer(dados)
    return out


def prioridades_rs(agora=None) -> set[str]:
    path = ROOT / 'config' / 'riscos_rs.json'
    if not path.exists():
        return set()
    cfg = json.loads(path.read_text(encoding='utf-8'))
    agora = agora or datetime.now(TZ)
    return set(cfg['prioridade_ibge']) if agora.date().isoformat() <= cfg['prioridade_temporaria_ate'] else set()


def municipios(aviso: dict) -> list[str]:
    """Nomes dos municípios do RS no aviso (texto do INMET; senão, cidades cadastradas)."""
    txt = aviso.get("municipios_texto") or ""
    nomes = [n.strip() for n in re.findall(r"([^,()]+?)\s*-\s*RS\s*\(\s*43\d{5}\s*\)", txt)]
    mapa = nomes_ibge()
    codigos = {str(c) for c in aviso.get('geocodes_rs', [])}
    if codigos:
        # Não mencionar município fora dos geocodes oficiais.
        nomes = [mapa[c] for c in sorted(codigos) if c in mapa]
    prioridades = prioridades_rs()
    nomes_prioritarios = {mapa[c].casefold() for c in codigos & prioridades if c in mapa}
    nomes.sort(key=lambda n: (n.casefold() not in nomes_prioritarios, n.casefold()))
    vistos, out = set(), []
    for n in nomes:
        if n.casefold() not in vistos:
            vistos.add(n.casefold())
            out.append(n)
    return out


def _hora(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{d:%Hh%M}".replace("h00", "h")


def _dia(iso: str, agora: datetime) -> str:
    d = datetime.fromisoformat(iso).date()
    if d == agora.date():
        return "hoje"
    if (d - agora.date()).days == 1:
        return "amanhã"
    return f"{d:%d/%m}"


def ceu(tipo: str) -> str:
    t = tipo.casefold()
    for chave, c in CEU:
        if chave in t:
            return c
    return "nublado"


def escolher(avisos: list[dict], historico: dict) -> dict | None:
    """Aviso mais severo (e mais amplo) ainda não publicado nesse nível."""
    feitos = {}
    for r in historico.get("registros", []):
        if r.get("media_id") or "reel_status" not in r:
            k=str(r["id_aviso"]); feitos[k]=max(feitos.get(k,0),int(r.get("nivel",1)))
    novos = [a for a in avisos if nivel(a.get("severidade")) > feitos.get(str(a["id_aviso"]), 0)]
    if not novos:
        pendentes = {(str(r["id_aviso"]), int(r.get("nivel",1))) for r in historico.get("registros",[]) if r.get("story_status")=="pending"}
        novos = [a for a in avisos if (str(a["id_aviso"]),nivel(a.get("severidade"))) in pendentes]
        if not novos: return None
    prioridades = prioridades_rs()
    return max(novos, key=lambda a: (nivel(a.get('severidade')), len({str(c) for c in a.get('geocodes_rs', [])} & prioridades), a.get('municipios_rs', 0)))


def roteiro(aviso: dict, todos: list[dict], agora: datetime) -> dict:
    orgao = aviso.get("orgao") or "INMET"
    tipo = str(aviso["tipo"]).strip()
    tipo_up = tipo.upper()
    n = nivel(aviso.get("severidade"))
    sev = str(aviso.get("severidade") or "Perigo potencial")
    nomes = municipios(aviso)
    qtd = int(aviso.get("municipios_rs") or len(nomes))
    fim_h, fim_d = _hora(aviso["fim"]), _dia(aviso["fim"], agora)
    ate = f"até as {fim_h} de {fim_d}"
    inicio = datetime.fromisoformat(aviso["inicio"])
    if inicio > agora:
        ate = f"das {_hora(aviso['inicio'])} de {_dia(aviso['inicio'],agora)} {ate}"
    exemplos = nomes[:3]
    detalhe = " · ".join(exemplos) if exemplos else f"{qtd} MUNICÍPIOS"
    if exemplos:
        cidades_fala = ", ".join(exemplos[:-1]) + (" e " if len(exemplos) > 1 else "") + exemplos[-1]
        onde = f"{qtd} municípios gaúchos, entre eles {cidades_fala}" if qtd > len(exemplos) else cidades_fala
    else:
        onde = f"{qtd} municípios gaúchos"
    riscos = _lista(aviso.get("riscos"))[:2]
    riscos_falados = [_unidades_para_fala(risco) for risco in riscos]
    instr = _lista(aviso.get("instrucoes"))
    instr_falada = _unidades_para_fala(instr[0]) + "." if instr else ""
    outros = sorted({str(a["tipo"]).strip() for a in todos if a is not aviso and a["tipo"] != aviso["tipo"]})

    # Orçamento de fala: avisos do INMET trazem riscos e instruções longos e o
    # alerta passava de 50 s. Cortamos primeiro o que é opcional (outros avisos,
    # instrução, segundo risco); abertura, validade, telefones e CTA ficam.
    def _palavras(lista):
        return sum(len(f["fala"].split()) for f in lista)

    falas = [
        {"cena": "abertura",
         "fala": f"Atenção, Rio Grande do Sul! Há {COR[n].lower()} de {tipo.lower()}, segundo {orgao}."},
        {"cena": "alerta", "titulo": tipo_up[:28], "detalhe": detalhe,
         "fala": f"O aviso vale {ate} para {onde}."},
    ]
    if riscos:
        falas.append({"cena": "frase",
                      "fala": f"Riscos apontados por {orgao}: " + "; ".join(
                          r.rstrip(".").lower() if i else r.rstrip(".")[0].lower() + r.rstrip(".")[1:]
                          for i, r in enumerate(riscos_falados)) + "."})
    if outros:
        falas.append({"cena": "frase",
                      "fala": "Também há aviso oficial de " + ", ".join(o.lower() for o in outros[:3]) + " no estado."})
    if instr_falada:
        falas.append({"cena": "frase", "fala": instr_falada})
    falas.append({"cena": "frase", "continua": True,
                  "fala": "Em emergência, ligue 199 para a Defesa Civil ou 193 para os Bombeiros."})
    falas.append({"cena": "cta", "chamada": "MANDE ESTE ALERTA", "sub": "{arroba} · aviso oficial",
                  "fala": "Manda esse alerta pra quem mora no Rio Grande do Sul."})
    for marca in ("Também há aviso oficial", "__instr__", "Riscos apontados"):
        if _palavras(falas) <= MAX_PALAVRAS_ALERTA:
            break
        for i, f in enumerate(falas):
            texto = f["fala"]
            alvo = (marca == "__instr__" and texto == instr_falada) or texto.startswith(marca)
            if f["cena"] == "frase" and not f.get("continua") and alvo:
                if marca == "Riscos apontados" and len(riscos) > 1:
                    primeiro_risco = riscos_falados[0]
                    f["fala"] = f"Riscos apontados por {orgao}: {primeiro_risco[0].lower() + primeiro_risco[1:]}."
                    if _palavras(falas) <= MAX_PALAVRAS_ALERTA:
                        break
                    continue
                del falas[i]
                break

    mostrados = nomes[:15]
    lista_legenda = ", ".join(mostrados) + (f" e mais {qtd - len(mostrados)}" if qtd > len(mostrados) and mostrados else "")
    leg = [f"⚠️ {COR[n]} · {orgao.upper()} — {tipo_up} no RS",
           f"🕒 Válido {ate}",
           f"📍 {qtd} municípios" + (f": {lista_legenda}" if nomes else "")]
    leg += [f"• {r}" for r in riscos]
    if outros:
        leg.append("Outros avisos vigentes no RS: " + ", ".join(outros))
    leg += ["", "Defesa Civil: 199 · Bombeiros: 193",
            "Manda pra quem mora no RS! {arroba}",
            "", "#AlertaRS #TempoRS #PrevisaoRS"]

    return {
        "tipo": "alerta",
        "apresenta": "bia",
        "validade": datetime.fromisoformat(aviso["fim"]).strftime("%Y-%m-%dT%H:%M"),
        "titulo": ("ALERTA DE " + tipo_up)[:32],
        "etiquetas": [f"{COR[n]} · {orgao.upper()}", f"{fim_d.upper()} · ATÉ {fim_h.upper()}"],
        "ceu": ceu(tipo),
        "trilha": False,
        "fonte": f"{orgao} — {sev.lower()} de {tipo.lower()} (aviso {aviso['id_aviso']})",
        "ticker": [tipo_up[:24], f"{qtd} MUNICÍPIOS", f"ATÉ {fim_h.upper()}", "DEFESA CIVIL 199"],
        "falas": falas,
        "legenda": "\n".join(leg) + "\n",
    }


def _ler(p: Path, padrao):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else padrao


def decidir(a) -> None:
    agora = datetime.now(TZ)
    dados = _ler(Path(a.alertas), {"avisos": []})
    historico = _ler(Path(a.historico), {"versao": 1, "registros": []})
    avisos = [v for v in dados.get("avisos", []) if datetime.fromisoformat(v["fim"]) > agora]
    if os.getenv("RS_ALERTA_SEVERO_APENAS") == "true":
        avisos = [v for v in avisos if nivel(v.get("severidade")) >= 2]
    aviso = escolher(avisos, historico)
    decisao = {"consultado_em": dados.get("consultado_em"), "avisos_vigentes": len(avisos), "seguir": "nao"}
    if aviso:
        rot = roteiro(aviso, avisos, agora)
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(rot, allow_unicode=True, sort_keys=False), encoding="utf-8")
        decisao.update(seguir="sim", roteiro=str(out), id_aviso=str(aviso["id_aviso"]),
                       nivel=nivel(aviso.get("severidade")), tipo=aviso["tipo"],
                       severidade=aviso.get("severidade"), fim=aviso["fim"])
    else:
        decisao["motivo"] = "nenhum aviso oficial vigente" if not avisos else "avisos vigentes já publicados"
    Path(a.decisao).parent.mkdir(parents=True, exist_ok=True)
    Path(a.decisao).write_text(json.dumps(decisao, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decisao, ensure_ascii=False))
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"seguir={decisao['seguir']}\n")
            if aviso:
                f.write(f"roteiro={a.out}\n")


def registrar(a) -> None:
    decisao = _ler(Path(a.decisao), {})
    if decisao.get("seguir") != "sim":
        return
    p = Path(a.historico)
    hist = _ler(p, {"versao": 1, "registros": []})
    hist["registros"].append({
        "id_aviso": decisao["id_aviso"], "nivel": decisao["nivel"], "tipo": decisao["tipo"],
        "severidade": decisao.get("severidade"), "fim": decisao.get("fim"),
        "media_id": a.media_id, "publicado_em": datetime.now(TZ).isoformat(timespec="seconds")})
    hist["registros"] = hist["registros"][-200:]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decidir")
    d.add_argument("--alertas", default="output/alertas_rs.json")
    d.add_argument("--historico", default="data/alertas_publicados.json")
    d.add_argument("--out", default="comunicados/auto/alerta_rs.yaml")
    d.add_argument("--decisao", default="output/alerta_decisao.json")
    r = sub.add_parser("registrar")
    r.add_argument("--historico", default="data/alertas_publicados.json")
    r.add_argument("--decisao", default="output/alerta_decisao.json")
    r.add_argument("--media-id", required=True)
    a = ap.parse_args()
    decidir(a) if a.cmd == "decidir" else registrar(a)


if __name__ == "__main__":
    main()
