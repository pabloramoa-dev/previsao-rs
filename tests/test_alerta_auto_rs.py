from datetime import datetime
from zoneinfo import ZoneInfo
from scripts.alerta_auto_rs import escolher, roteiro, nivel

AGORA = datetime(2026, 11, 23, 12, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))


def aviso(id_, sev="Perigo", tipo="Tempestade", n=40):
    return {"id_aviso": id_, "tipo": tipo, "severidade": sev,
            "inicio": "2026-11-23T10:00:00-03:00", "fim": "2026-11-24T10:00:00-03:00",
            "municipios_rs": n, "geocodes_rs": ["4314902"],
            "municipios_texto": "Porto Alegre - RS (4314902), Canoas - RS (4304606)",
            "riscos": "Granizo e queda de árvores. Corte de energia elétrica.",
            "instrucoes": "Em caso de rajadas de vento, não se abrigue debaixo de árvores."}


def test_escolhe_mais_severo_e_nao_repete():
    a, b = aviso("1", "Perigo potencial"), aviso("2", "Grande Perigo")
    assert escolher([a, b], {"registros": []})["id_aviso"] == "2"
    hist = {"registros": [{"id_aviso": "2", "nivel": 3}, {"id_aviso": "1", "nivel": 1}]}
    assert escolher([a, b], hist) is None


def test_republica_se_severidade_sobe():
    hist = {"registros": [{"id_aviso": "1", "nivel": 1}]}
    assert escolher([aviso("1", "Perigo")], hist)["id_aviso"] == "1"


def test_roteiro_so_com_dados_oficiais():
    a = aviso("1")
    r = roteiro(a, [a, aviso("9", tipo="Acumulado de Chuva")], AGORA)
    assert r["falas"][0]["cena"] == "abertura" and r["falas"][-1]["cena"] == "cta"
    assert "{arroba}" in r["legenda"] and "Porto Alegre" in r["legenda"]
    assert r["validade"] == "2026-11-24T10:00"
    assert nivel("Grande Perigo") == 3
